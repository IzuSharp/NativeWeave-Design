// Deliberate callback shape mismatch for isolated failure classification only.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_uc_invoke(callback: extern "C" fn(u16) -> u8) -> i32 {
    i32::from(callback(120))
}
