#[no_mangle]
pub extern "C" fn sigsuspend_prepare_mask(raw_mask: CULong) -> CULong {
    raw_mask & !(SIGKILL_MASK | SIGSTOP_MASK)
}
