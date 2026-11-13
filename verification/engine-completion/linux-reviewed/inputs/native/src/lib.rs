//! R18 research adapter over a mature synchronous Rust codec; not product code.
use std::{ffi::c_void, panic::{AssertUnwindSafe, catch_unwind}, ptr, slice};
const MAX: usize = 4 * 1024 * 1024;
#[repr(C)]
pub struct Buffer { owner: *mut c_void, data: *const u8, length: usize }
impl Default for Buffer {
    fn default() -> Self { Self { owner: ptr::null_mut(), data: ptr::null(), length: 0 } }
}

/// Caller supplies a writable aligned output and valid input range for this call.
/// No borrowed input survives return. A successful owner must be released once.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_codec_run(input: *const u8, length: usize, mode: u32, output: *mut Buffer) -> u32 {
    if output.is_null() { return 1; }
    unsafe { output.write(Buffer::default()); }
    if length > MAX || (input.is_null() && length != 0) || mode > 1 { return 1; }
    let result = catch_unwind(AssertUnwindSafe(|| {
        let bytes = if length == 0 { &[] } else { unsafe { slice::from_raw_parts(input, length) } };
        let owned = match mode {
            0 => miniz_oxide::deflate::compress_to_vec_zlib(bytes, 6),
            _ => match miniz_oxide::inflate::decompress_to_vec_zlib_with_limit(bytes, MAX) {
                Ok(value) => value,
                Err(_) => return 2,
            },
        };
        let boxed = Box::new(owned);
        let data = boxed.as_ptr(); let length = boxed.len();
        let owner = Box::into_raw(boxed).cast();
        unsafe { output.write(Buffer { owner, data, length }); }
        0
    }));
    result.unwrap_or(3)
}

/// A trusted live owner from this module; use-after-free/forgery is outside this C ABI.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn nw_codec_release(owner: *mut c_void) {
    if !owner.is_null() { drop(unsafe { Box::from_raw(owner.cast::<Vec<u8>>()) }); }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn native_roundtrip_and_empty() {
        for data in [&b""[..], &b"source-driven native codec"[..]] {
            let c=miniz_oxide::deflate::compress_to_vec_zlib(data,6);
            assert_eq!(miniz_oxide::inflate::decompress_to_vec_zlib_with_limit(&c,MAX).unwrap(),data);
        }
    }
    #[test] fn rejected_output_is_empty() {
        let mut out=Buffer::default();
        assert_eq!(unsafe {nw_codec_run(ptr::null(),1,0,&mut out)},1);
        assert!(out.owner.is_null() && out.data.is_null() && out.length==0);
        assert_eq!(unsafe {nw_codec_run(ptr::null(),0,7,&mut out)},1);
        assert_eq!(unsafe {nw_codec_run(ptr::null(),MAX+1,0,&mut out)},1);
    }
    #[test] fn malformed_and_bomb_rejected() {
        let mut out=Buffer::default(); let bad=[0,1,2];
        assert_eq!(unsafe {nw_codec_run(bad.as_ptr(),bad.len(),1,&mut out)},2);
        assert!(out.owner.is_null());
        let large=vec![0;MAX+1]; let compressed=miniz_oxide::deflate::compress_to_vec_zlib(&large,6);
        assert_eq!(unsafe {nw_codec_run(compressed.as_ptr(),compressed.len(),1,&mut out)},2);
        assert!(out.owner.is_null());
    }
}
