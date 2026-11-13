//! R03/R04 executable fixture. Not the accepted production ABI.
//! Raw handles must originate here, remain live for each call and be destroyed once.
//! Arbitrary invalid/stale pointers are outside this C ABI's safety contract.
#![deny(unsafe_op_in_unsafe_fn)]
use std::{alloc::Global, ffi::c_void, mem::{align_of,offset_of,size_of,DropGuard},
    panic::{catch_unwind,AssertUnwindSafe}, ptr,
    sync::atomic::{AtomicBool,AtomicUsize,Ordering}, time::{Duration,Instant}};
const OK:u32=0; const INVALID:u32=1; const LIMIT:u32=2; const PANIC:u32=3;
const MAX_BYTES:usize=1024*1024;
// Test instrumentation only: not a framework-wide runtime/allocator/handle table.
static LIVE:AtomicUsize=AtomicUsize::new(0);
static ENTERED:AtomicBool=AtomicBool::new(false);
static RELEASE:AtomicBool=AtomicBool::new(false);
fn release_admission(_:()){LIVE.fetch_sub(1,Ordering::SeqCst);}
struct OwnedBuffer {
    data:Vec<u8,Global>,
    // Declared after data, so its destruction follows the backing allocation.
    _admission:DropGuard<(),fn(())>,
}
#[repr(C)]
pub struct Sample { tag:u8, count:u32, value:u64 }
#[repr(C)]
pub struct AbiInfo {
    version:u32, struct_size:u32, pointer_size:u32, max_bytes:u32,
    sample_size:u32, sample_align:u32, count_offset:u32, value_offset:u32,
}
fn boundary(f:impl FnOnce()->Result<(),u32>)->u32 {
    match catch_unwind(AssertUnwindSafe(f)){Ok(Ok(()))=>OK,Ok(Err(e))=>e,Err(_)=>PANIC}
}
/// # Safety
/// out is null or points to aligned writable storage of at least out_size bytes.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_abi_info(out:*mut AbiInfo,out_size:usize)->u32 {
    if out.is_null() || out_size<size_of::<AbiInfo>(){return INVALID}
    unsafe {out.write(AbiInfo{version:1,struct_size:size_of::<AbiInfo>() as u32,
        pointer_size:size_of::<usize>() as u32,max_bytes:MAX_BYTES as u32,
        sample_size:size_of::<Sample>() as u32,sample_align:align_of::<Sample>() as u32,
        count_offset:offset_of!(Sample,count) as u32,value_offset:offset_of!(Sample,value) as u32});}
    OK
}
/// # Safety
/// out is null or valid writable pointer storage; it is cleared before fallible work.
/// fail_mode=1 deliberately injects a contained panic before publishing an owner.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_buffer_new(len:usize,fail_mode:u32,out:*mut *mut c_void)->u32 {
    if out.is_null(){return INVALID}
    unsafe{out.write(ptr::null_mut());}
    if len>MAX_BYTES{return LIMIT}
    if fail_mode>1{return INVALID}
    boundary(||{
        LIVE.fetch_add(1,Ordering::SeqCst);
        let admission=DropGuard::new((),release_admission as fn(()));
        let mut data=Vec::new_in(Global);
        data.try_reserve_exact(len).map_err(|_|LIMIT)?;
        data.extend((0..len).map(|i|(i%251) as u8));
        if fail_mode==1{panic!("intentional unpublished-allocation failure")}
        // Box's small control allocation may abort on OOM; catch_unwind is not an OOM guarantee.
        let owner=Box::new(OwnedBuffer{data,_admission:admission});
        unsafe{out.write(Box::into_raw(owner).cast());}
        Ok(())
    })
}
/// # Safety
/// p is null or a live owned handle from nw_buffer_new, not already released.
/// No calls/borrows may remain. The managed facade supplies SafeHandle call leases.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_buffer_drop(p:*mut c_void){
    if !p.is_null(){unsafe{drop(Box::from_raw(p.cast::<OwnedBuffer>()));}}
}
/// # Safety
/// p is a live same-module handle; out points to writable u64. Reads may overlap;
/// destruction may not overlap any call. There is no mutable query/aliasing promise.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_buffer_sum(p:*const c_void,out:*mut u64)->u32 {
    if p.is_null()||out.is_null(){return INVALID}
    let b=unsafe{&*p.cast::<OwnedBuffer>()};
    unsafe{out.write(b.data.iter().map(|x|u64::from(*x)).sum());}
    OK
}
#[unsafe(no_mangle)]
pub extern "C" fn nw_live_buffers()->usize{LIVE.load(Ordering::SeqCst)}
#[unsafe(no_mangle)]
pub extern "C" fn nw_hold_reset(){ENTERED.store(false,Ordering::Release);RELEASE.store(false,Ordering::Release);}
#[unsafe(no_mangle)]
pub extern "C" fn nw_hold_entered()->u32{u32::from(ENTERED.load(Ordering::Acquire))}
#[unsafe(no_mangle)]
pub extern "C" fn nw_hold_release(){RELEASE.store(true,Ordering::Release);}
/// # Safety
/// Same pointer rules as nw_buffer_sum. Test-only bounded blocking call; not production cancellation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_buffer_sum_held(p:*const c_void,out:*mut u64)->u32 {
    if p.is_null()||out.is_null(){return INVALID}
    ENTERED.store(true,Ordering::Release);
    let until=Instant::now()+Duration::from_secs(10);
    while !RELEASE.load(Ordering::Acquire){
        if Instant::now()>until{return LIMIT}
        std::thread::sleep(Duration::from_millis(1));
    }
    unsafe{nw_buffer_sum(p,out)}
}
/// # Safety
/// Callback and out must remain valid for this synchronous call. Callback must not
/// unwind, throw a managed exception or retain any borrowed pointer. No async use.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_callback_apply(value:u32,context:usize,
    callback:Option<unsafe extern "C" fn(u32,usize)->u32>,out:*mut u32)->u32 {
    if out.is_null(){return INVALID}
    unsafe{out.write(0);}
    let Some(cb)=callback else{return INVALID};
    unsafe{out.write(cb(value,context));}
    OK
}
#[cfg(test)]
mod tests {
    use super::*;
    // Serialized runner avoids interference between explicitly global test counters.
    #[test]fn layout(){assert_eq!(size_of::<AbiInfo>(),32);assert_eq!(offset_of!(Sample,count),4);assert_eq!(offset_of!(Sample,value),8);}
    #[test]fn owned_buffer_and_empty(){unsafe{for n in [0,1,256]{let mut p=ptr::null_mut();assert_eq!(nw_buffer_new(n,0,&mut p),OK);let mut sum=0;assert_eq!(nw_buffer_sum(p,&mut sum),OK);assert_eq!(sum,(0..n).map(|i|(i%251)as u64).sum());nw_buffer_drop(p);}assert_eq!(nw_live_buffers(),0);}}
    #[test]fn bad_inputs_and_rollback(){unsafe{let mut p=1usize as *mut c_void;assert_eq!(nw_buffer_new(MAX_BYTES+1,0,&mut p),LIMIT);assert!(p.is_null());assert_eq!(nw_buffer_new(10,1,&mut p),PANIC);assert!(p.is_null());assert_eq!(nw_live_buffers(),0);assert_eq!(nw_buffer_new(10,0,ptr::null_mut()),INVALID);assert_eq!(nw_abi_info(ptr::null_mut(),32),INVALID);}}
    #[test]fn synchronous_callback(){unsafe extern "C" fn cb(x:u32,c:usize)->u32{x+c as u32}unsafe{let mut out=0;assert_eq!(nw_callback_apply(4,3,Some(cb),&mut out),OK);assert_eq!(out,7);assert_eq!(nw_callback_apply(4,3,None,&mut out),INVALID);}}
}
