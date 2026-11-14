// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Only the existing five-event C diagnostic formatter is retired by this fragment.
// Reuse the existing policy MOVE_PAGES_LOG_* constants, CInt/CULong, and kprintf ABI.
// Numeric messages retain the original space before LF. Unknown events emit nothing.
#[no_mangle]
pub unsafe extern "C" fn move_pages_log_bridge(event: CInt, value: CULong, _error: CInt) {
    match event {
        MOVE_PAGES_LOG_UNSUPPORTED_PID => {
            kprintf(
                c"%s: ERROR: only self (pid == 0) is supported\n".as_ptr().cast(),
                c"sys_move_pages".as_ptr(),
            );
        }
        MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL => {
            kprintf(
                c"%s: ERROR: MPOL_MF_MOVE_ALL not supported\n".as_ptr().cast(),
                c"sys_move_pages".as_ptr(),
            );
        }
        MOVE_PAGES_LOG_INIT_MALLOC => {
            kprintf(c"%s: init malloc: %lu \n".as_ptr().cast(), c"sys_move_pages".as_ptr(), value);
        }
        MOVE_PAGES_LOG_INIT_VERIFY => {
            kprintf(c"%s: init verify: %lu \n".as_ptr().cast(), c"sys_move_pages".as_ptr(), value);
        }
        MOVE_PAGES_LOG_PARALLEL => {
            kprintf(c"%s: parallel: %lu \n".as_ptr().cast(), c"sys_move_pages".as_ptr(), value);
        }
        _ => {}
    }
}
