    // Reuse existing provider symbols; no new C implementation or ABI header.
    #[link_name = "interrupt_from_user"]
    fn x86_debug_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "set_cputime"]
    fn x86_debug_set_cputime(mode: CUInt);
    #[link_name = "arch_show_interrupt_context"]
    fn x86_debug_show_context(regs: *const c_void);
    #[link_name = "set_signal"]
    fn x86_debug_set_signal(sig: CInt, regs: *mut c_void, info: *mut crate::abi::SigInfo);
    #[link_name = "interrupt_exit"]
    fn x86_debug_interrupt_exit(regs: *mut X86UserContext);
    #[link_name = "x86_debug_handler_debug_print_enabled"]
    static X86_DEBUG_HANDLER_DEBUG_PRINT_ENABLED: CUInt;
