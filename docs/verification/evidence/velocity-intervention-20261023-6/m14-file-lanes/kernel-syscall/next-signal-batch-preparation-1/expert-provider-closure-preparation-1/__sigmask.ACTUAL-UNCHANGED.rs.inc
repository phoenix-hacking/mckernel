#[no_mangle]
pub extern "C" fn __sigmask(sig: CULong) -> CULong {
    1u64.wrapping_shl((sig.wrapping_sub(1) & 63) as u32) as CULong
}
