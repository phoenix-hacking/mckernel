    // Existing provider symbols; aliases add no new C implementation.
    #[link_name = "interrupt_from_user"]
    fn x86_int3_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "set_cputime"]
    fn x86_int3_set_cputime(mode: CUInt);
    #[link_name = "arch_show_interrupt_context"]
    fn x86_int3_show_context(regs: *const c_void);
    #[link_name = "set_signal"]
    fn x86_int3_set_signal(sig: CInt, regs: *mut c_void, info: *mut crate::abi::SigInfo);
    #[link_name = "interrupt_exit"]
    fn x86_int3_interrupt_exit(regs: *mut X86UserContext);
    #[link_name = "x86_int3_debug_print_enabled"]
    static X86_INT3_DEBUG_PRINT_ENABLED: CUInt;
