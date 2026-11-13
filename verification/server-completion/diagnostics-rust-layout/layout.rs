// Research-only layout witness, not a NativeWeave Core ABI definition.
#[repr(C)]
struct TraceContextV1 {
    size: u32,
    version: u16,
    trace_flags: u8,
    reserved: u8,
    trace_id: [u8; 16],
    parent_span_id: [u8; 8],
}

fn main() {
    assert_eq!(std::mem::size_of::<TraceContextV1>(), 32);
    assert_eq!(std::mem::offset_of!(TraceContextV1, trace_id), 8);
    assert_eq!(std::mem::offset_of!(TraceContextV1, parent_span_id), 24);
    println!("PASS Rust TraceContextV1 size=32 trace_id=8 parent_span_id=24");
}
