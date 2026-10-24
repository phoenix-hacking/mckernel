#[no_mangle]
pub extern "C" fn sigsuspend_pending_matches(pending_mask: CULong, suspend_mask: CULong) -> CInt {
    if (pending_mask & suspend_mask) == 0 {
        1
    } else {
        0
    }
}
