//! Finite research probe, not the NativeWeave product ABI.
//! The caller supplies valid pointers and externally leases each handle during FFI.
#![deny(unsafe_op_in_unsafe_fn)]
use std::sync::{Arc, Mutex, atomic::{AtomicUsize, Ordering}};

pub const OK: u32 = 0;
pub const PENDING: u32 = 1;
pub const INVALID: u32 = 2;
pub const CANCELLED: u32 = 3;
static LIVE_OPERATIONS: AtomicUsize = AtomicUsize::new(0);
static LIVE_RESULTS: AtomicUsize = AtomicUsize::new(0);
type Callback = extern "C" fn(usize, u32);
struct ResultOwner { value: u64 }
impl Drop for ResultOwner { fn drop(&mut self) { LIVE_RESULTS.fetch_sub(1, Ordering::SeqCst); } }
struct State {
    started: bool, cancelled: bool, terminal: Option<u32>, callbacks: usize,
    working: bool, retired: bool, taken: bool, result: Option<Box<ResultOwner>>,
}
struct Operation { state: Mutex<State>, callback: Callback, cookie: usize }
impl Drop for Operation { fn drop(&mut self) { LIVE_OPERATIONS.fetch_sub(1, Ordering::SeqCst); } }
type Handle = Arc<Operation>;

fn complete(op: &Operation) -> bool {
    let status = {
        let mut state = op.state.lock().unwrap();
        if state.terminal.is_some() || state.retired { return false; }
        let status = if state.cancelled { CANCELLED } else { OK };
        if status == OK {
            state.result = Some(Box::new(ResultOwner { value: 42 }));
            LIVE_RESULTS.fetch_add(1, Ordering::SeqCst);
        }
        state.terminal = Some(status);
        state.callbacks += 1;
        status
    };
    // Never call foreign code under the state mutex. The callback must not unwind.
    (op.callback)(op.cookie, status);
    op.state.lock().unwrap().callbacks -= 1;
    true
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_ic_create(callback: Callback, cookie: usize, out: *mut *mut Handle) -> u32 {
    if out.is_null() { return INVALID; }
    let op = Arc::new(Operation { state: Mutex::new(State { started: false, cancelled: false,
        terminal: None, callbacks: 0, working: false, retired: false, taken: false, result: None }), callback, cookie });
    LIVE_OPERATIONS.fetch_add(1, Ordering::SeqCst);
    unsafe { *out = Box::into_raw(Box::new(op)); }
    OK
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_ic_start(handle: *mut Handle, background: u32) -> u32 {
    if handle.is_null() || background > 1 { return INVALID; }
    let op = unsafe { &*handle };
    { let mut state = op.state.lock().unwrap();
      if state.started || state.retired { return INVALID; }
      state.started = true; state.working = true; }
    if background == 0 {
        complete(op);
        op.state.lock().unwrap().working = false;
    } else {
        let retained = op.clone();
        // Bounded one-worker test fixture. Product executors use engine-local admission.
        std::thread::spawn(move || {
            complete(&retained);
            retained.state.lock().unwrap().working = false;
        });
    }
    OK
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_ic_cancel(handle: *mut Handle) -> u32 {
    if handle.is_null() { return INVALID; }
    let mut s = unsafe { &*handle }.state.lock().unwrap();
    if s.retired { return INVALID; }
    s.cancelled = true; // request only: a previously committed terminal is immutable.
    OK
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_ic_try_retire(handle: *mut Handle) -> u32 {
    if handle.is_null() { return INVALID; }
    let mut s = unsafe { &*handle }.state.lock().unwrap();
    if s.working || s.callbacks != 0 { return PENDING; }
    if s.started && s.terminal.is_none() { return PENDING; }
    s.retired = true;
    OK
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_ic_take(handle: *mut Handle, out: *mut *mut ResultOwner) -> u32 {
    if handle.is_null() || out.is_null() { return INVALID; }
    unsafe { *out = std::ptr::null_mut(); }
    let mut s = unsafe { &*handle }.state.lock().unwrap();
    if s.terminal.is_none() || s.taken { return INVALID; }
    s.taken = true;
    if s.terminal == Some(CANCELLED) { return CANCELLED; }
    if let Some(result) = s.result.take() { unsafe { *out = Box::into_raw(result); } OK } else { INVALID }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_ic_duplicate_terminal(handle: *mut Handle) -> u32 {
    if handle.is_null() { return INVALID; }
    if complete(unsafe { &*handle }) { OK } else { INVALID }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_ic_release(handle: *mut Handle) -> u32 {
    if unsafe { nw_ic_try_retire(handle) } != OK { return PENDING; }
    // Releasing the private owner never frees an independently transferred result.
    unsafe { drop(Box::from_raw(handle)); }
    OK
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_ic_result_value(result: *const ResultOwner) -> u64 {
    if result.is_null() { 0 } else { unsafe { (*result).value } }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_ic_result_release(result: *mut ResultOwner) {
    if !result.is_null() { unsafe { drop(Box::from_raw(result)); } }
}

#[unsafe(no_mangle)]
pub extern "C" fn nw_ic_live_operations() -> usize { LIVE_OPERATIONS.load(Ordering::SeqCst) }
#[unsafe(no_mangle)]
pub extern "C" fn nw_ic_live_results() -> usize { LIVE_RESULTS.load(Ordering::SeqCst) }

#[cfg(test)]
mod tests {
    use super::*;
    static CALLS: AtomicUsize = AtomicUsize::new(0);
    extern "C" fn called(_: usize, _: u32) { CALLS.fetch_add(1, Ordering::SeqCst); }
    #[test]
    fn terminal_and_transfer_are_independent_of_operation_release() {
        unsafe {
            let mut op = std::ptr::null_mut();
            assert_eq!(nw_ic_create(called, 0, &mut op), OK);
            assert_eq!(nw_ic_start(op, 0), OK);
            assert_eq!(nw_ic_cancel(op), OK);
            assert_eq!(nw_ic_duplicate_terminal(op), INVALID);
            assert_eq!(CALLS.load(Ordering::SeqCst), 1);
            let mut result = std::ptr::null_mut();
            assert_eq!(nw_ic_take(op, &mut result), OK);
            let mut second = std::ptr::null_mut();
            assert_eq!(nw_ic_take(op, &mut second), INVALID);
            assert!(second.is_null());
            assert_eq!(nw_ic_release(op), OK);
            assert_eq!(nw_ic_result_value(result), 42);
            assert_eq!(nw_ic_live_results(), 1);
            nw_ic_result_release(result);
            assert_eq!(nw_ic_live_operations(), 0);
            assert_eq!(nw_ic_live_results(), 0);
        }
    }
}
