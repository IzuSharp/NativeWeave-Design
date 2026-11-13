// Parser input only; this describes the existing research export, not a product API.
#[no_mangle]
pub extern "C" fn nw_ic_validate_extent(count: u64, width: u64, budget: u64) -> u32 { 0 }
// Deliberately unsupported syntax: omission must be caught by export-inventory checking.
#[no_mangle]
pub extern "C" fn unsupported_tuple(value: (u32, u32)) { }
