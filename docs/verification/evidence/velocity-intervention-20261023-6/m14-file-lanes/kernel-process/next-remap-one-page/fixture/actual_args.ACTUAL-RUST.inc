#[repr(C)]
struct ProcessRemapArgs {
    off: OffT,
    start: CULong,
    memobj: *mut Memobj,
}
