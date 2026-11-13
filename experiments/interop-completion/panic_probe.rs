// Process-isolated research only. Never link these intentionally fatal branches into an application.
use std::panic::{catch_unwind, panic_any};
struct BadDrop;
impl Drop for BadDrop { fn drop(&mut self) { panic!("payload-or-cleanup-drop"); } }
extern "C" fn no_unwind() { panic!("panic-in-nonunwind-ffi"); }
fn main() {
    let mode = std::env::args().nth(1).expect("mode");
    match mode.as_str() {
        "catch" => { assert!(catch_unwind(|| panic!("ordinary-panic")).is_err()); println!("CAUGHT ordinary"); }
        "payload-drop" => { let caught=catch_unwind(|| panic_any(BadDrop)); drop(caught); }
        "payload-forget" => { let caught=catch_unwind(|| panic_any(BadDrop)); std::mem::forget(caught); println!("QUARANTINED payload"); }
        "hook" => { std::panic::set_hook(Box::new(|_| panic!("hook-panic"))); panic!("first-panic"); }
        "cleanup" => { let _drop=BadDrop; panic!("first-panic"); }
        "ffi" => no_unwind(),
        _ => panic!("unknown mode"),
    }
}
