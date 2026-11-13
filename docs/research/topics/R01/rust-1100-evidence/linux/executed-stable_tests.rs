//! R01 research fixtures, not production or performance acceptance.
#![deny(unsafe_op_in_unsafe_fn)]
use std::{alloc::{Allocator, AllocError, Global, Layout}, cell::Cell, ptr::NonNull,
    mem::DropGuard, sync::{Arc,atomic::{AtomicUsize,Ordering}},
    panic::{catch_unwind,AssertUnwindSafe}};

struct Counts { live: Cell<usize>, allocations: Cell<usize>, max_single: usize }
impl Counts {
    fn new(max: usize) -> Self {
        Self { live: Cell::new(0), allocations: Cell::new(0), max_single: max }
    }
}
// SAFETY: Global supplies aligned disjoint blocks. All bookkeeping is non-panicking.
// Deallocation forwards the exact caller-provided pointer/layout to the same owner.
// This counts requested bytes for a test, NOT all process memory or a production budget.
unsafe impl Allocator for Counts {
    fn allocate(&self, l: Layout) -> Result<NonNull<[u8]>, AllocError> {
        if l.size() > self.max_single { return Err(AllocError); }
        let p = Global.allocate(l)?;
        self.live.set(self.live.get().saturating_add(l.size()));
        self.allocations.set(self.allocations.get().saturating_add(1));
        Ok(p)
    }
    unsafe fn deallocate(&self, p: NonNull<u8>, l: Layout) {
        self.live.set(self.live.get().saturating_sub(l.size()));
        unsafe { Global.deallocate(p,l); }
    }
}
struct Tracked<'a>(&'a AtomicUsize);
impl Drop for Tracked<'_> {
    fn drop(&mut self) { self.0.fetch_add(1,Ordering::SeqCst); }
}
#[test]
fn never_and_infallible_alias() {
    fn a() -> Result<u32,!> { Ok(7) }
    let r: Result<u32,std::convert::Infallible> = a();
    let Ok(v) = r;
    assert_eq!(v,7);
}
#[test]
fn vec_allocator_release_and_failed_growth() {
    let a = Counts::new(64);
    {
        let mut v: Vec<u8,_> = Vec::new_in(&a);
        v.try_reserve_exact(16).unwrap(); v.extend([1,2,3]);
        let ptr = v.as_ptr();
        assert!(v.try_reserve_exact(1000).is_err());
        assert_eq!(v.as_ptr(),ptr); assert_eq!(&v[..],&[1,2,3]);
    }
    assert_eq!(a.live.get(),0);
}
#[test]
fn raw_parts_preserve_allocator() {
    let a = Counts::new(128);
    let b = Box::new_in(42_u64,&a);
    let (p,owner) = Box::into_raw_with_allocator(b);
    // SAFETY: exact pointer, unchanged T/layout, retained original allocator, once.
    let b = unsafe { Box::from_raw_in(p,owner) };
    assert_eq!(*b,42); drop(b); assert_eq!(a.live.get(),0);
    let mut v = Vec::new_in(&a); v.extend([1_u32,2,3]);
    let (p,len,cap,owner) = v.into_raw_parts_with_allocator();
    // SAFETY: all four parts came from the same live Vec, reconstructed once.
    let v = unsafe { Vec::from_raw_parts_in(p,len,cap,owner) };
    assert_eq!(v.len(),3); drop(v); assert_eq!(a.live.get(),0);
}
#[test]
fn guard_runs_once() {
    let n = AtomicUsize::new(0);
    { let _g = DropGuard::new(4, |v| { n.fetch_add(v,Ordering::SeqCst); }); }
    assert_eq!(n.load(Ordering::SeqCst),4);
}
#[test]
fn guard_dismiss_drops_captured_resources() {
    let calls = AtomicUsize::new(0); let drops = AtomicUsize::new(0);
    let t = Tracked(&drops);
    let g = DropGuard::new(5, |v| { drop(t); calls.fetch_add(v,Ordering::SeqCst); });
    assert_eq!(DropGuard::dismiss(g),5);
    assert_eq!(calls.load(Ordering::SeqCst),0); assert_eq!(drops.load(Ordering::SeqCst),1);
}
#[test]
fn guard_runs_during_unwind() {
    let n = AtomicUsize::new(0);
    assert!(catch_unwind(|| {
        let _g = DropGuard::new((), |_| { n.fetch_add(1,Ordering::SeqCst); });
        panic!("intentional");
    }).is_err());
    assert_eq!(n.load(Ordering::SeqCst),1);
}
#[test]
fn box_map_equal_layout_observation() {
    let a = Counts::new(128); let b = Box::new_in(7_u64,&a);
    let before = (&*b as *const u64) as usize;
    let b = Box::map(b,|v| v as i64 + 1);
    assert_eq!(*b,8);
    // Observes this pinned implementation, not a stable address guarantee.
    assert_eq!((&*b as *const i64) as usize,before);
    assert_eq!(a.allocations.get(),1); drop(b); assert_eq!(a.live.get(),0);
}
#[test]
fn box_map_changed_layout_and_panic_cleanup() {
    let a = Counts::new(128); let b = Box::new_in(7_u8,&a);
    let b = Box::map(b,|v| [v;16]);
    assert_eq!(*b,[7;16]); assert_eq!(a.allocations.get(),2);
    drop(b); assert_eq!(a.live.get(),0);
    assert!(catch_unwind(AssertUnwindSafe(|| {
        let b = Box::new_in(2_u64,&a);
        let _b: Box<u64,_> = Box::map(b, |_| panic!("intentional"));
    })).is_err());
    assert_eq!(a.live.get(),0);
}
#[test]
fn arc_map_unique_observation() {
    let a = Arc::new(7_u64); let p = Arc::as_ptr(&a) as usize;
    let b = Arc::map(a,|v| *v as i64 + 1);
    assert_eq!(*b,8); assert_eq!(Arc::as_ptr(&b) as usize,p);
}
#[test]
fn arc_map_shared_is_not_in_place_update() {
    let a = Arc::new(7_u64); let other = a.clone();
    let b = Arc::map(a,|v| *v + 1);
    assert_eq!(*other,7); assert_eq!(*b,8);
    assert_ne!(Arc::as_ptr(&b),Arc::as_ptr(&other));
}
#[test]
fn arc_map_with_weak_has_distinct_identity() {
    let a = Arc::new(7_u64); let weak = Arc::downgrade(&a);
    let p = Arc::as_ptr(&a) as usize;
    let b = Arc::map(a,|v| *v + 1);
    assert_eq!(*b,8); assert!(weak.upgrade().is_none());
    assert_ne!(Arc::as_ptr(&b) as usize,p);
}
#[test]
fn arc_allocator_delegation_is_stable() {
    let a = Arc::new(Counts::new(128));
    { let mut v: Vec<u8,_> = Vec::new_in(a.clone()); v.try_reserve(16).unwrap(); v.push(1); }
    assert_eq!(a.live.get(),0);
}
#[test]
fn vec_from_fn_zero_order_and_unwind() {
    let mut calls = 0;
    let v: Vec<u8> = Vec::from_fn(0, |_| { calls += 1; 0 });
    assert!(v.is_empty()); assert_eq!(calls,0);
    assert_eq!(Vec::from_fn(4,|i| i*2),[0,2,4,6]);
    let n = AtomicUsize::new(0);
    assert!(catch_unwind(|| {
        let _v = Vec::from_fn(8,|i| { if i==3 { panic!("intentional"); } Tracked(&n) });
    }).is_err());
    assert_eq!(n.load(Ordering::SeqCst),3);
}
