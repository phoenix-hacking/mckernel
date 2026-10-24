// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete set_signal public entry; native failure/termination providers unchanged.
unsafe extern "C" {
    #[link_name = "ihk_mc_debug_show_interrupt_context"]
    fn f06_set_signal_show_context(regs: *const c_void);
    #[link_name = "panic"]
    fn f06_set_signal_kernel_panic(message: *const i8);
    #[link_name = "coredump"]
    fn f06_set_signal_coredump(thread: *mut Thread, regs: *mut c_void, sig: CInt) -> CInt;
    #[link_name = "terminate"]
    fn f06_set_signal_terminate(rc: CInt, sig: CInt);
    #[link_name = "do_kill"]
    fn f06_set_signal_do_kill(
        thread: *mut Thread, pid: CInt, tid: CInt, sig: CInt,
        info: *mut SigInfo, ptracecont: CInt,
    ) -> CULong;
}

/// Borrow the current thread, context and caller's siginfo synchronously. No
/// pending node/refcount/IRQ state is acquired by this entry. The existing
/// do_kill provider owns any eventual pending allocation/queue transfer.
#[no_mangle]
pub unsafe extern "C" fn set_signal(sig: CInt, regs: *mut c_void, info: *mut SigInfo) {
    let thread = (*crate::cls::get_this_cpu_local_var()).current;
    if thread.is_null() || (*(*thread).proc).pid == 0 {
        return;
    }
    if interrupt_from_user(regs) == 0 {
        f06_set_signal_show_context(regs.cast_const());
        f06_set_signal_kernel_panic(b"panic: kernel mode signal\0".as_ptr().cast());
        // Real native panic normally stops. Its declared C ABI is void, however:
        // preserve the original fallthrough if an explicitly controlled endpoint
        // returns; do not introduce unreachable or assume a Rust panic handler.
    }
    if __sigmask(sig as CULong) & (*thread).sigmask.val[0] != 0 {
        let _ = f06_set_signal_coredump(thread, regs, sig);
        f06_set_signal_terminate(0, sig | 0x80);
        // Likewise preserve the C void terminate contract if the provider returns.
    }
    let _ = f06_set_signal_do_kill(
        thread, (*(*thread).proc).pid, (*thread).tid, sig, info, 0,
    );
}
