    // Existing providers; the Rust-local alias adds no exported C helper.
    fn interrupt_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "cpu_enable_interrupt"]
    fn x86_interrupt_exit_enable_interrupt();
    fn check_sig_pending();
    fn check_need_resched();
    fn check_signal(rc: CULong, regs: *mut c_void, num: CInt);
