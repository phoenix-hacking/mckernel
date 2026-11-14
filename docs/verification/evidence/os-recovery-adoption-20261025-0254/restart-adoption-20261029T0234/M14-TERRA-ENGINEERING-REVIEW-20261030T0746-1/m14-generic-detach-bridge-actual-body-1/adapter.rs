unsafe extern "C" fn f06_ptrace_report_signal_kill(
    thread: *mut c_void, pid: CInt, tid: CInt, sig: CInt,
    info: *const SigInfo, ptracecont: CInt,
) -> CLong {
    // The old C adapter implicitly converted do_kill's unsigned long to long.
    // Keep its exact bits; the signal body deliberately ignores the return.
    unsafe {
        f06_ptrace_report_signal_do_kill(
            thread.cast::<Thread>(), pid, tid, sig, info.cast_mut(), ptracecont,
        ) as CLong
    }
}
