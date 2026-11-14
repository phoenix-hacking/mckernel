    // Existing selected providers; aliases introduce no new exported helper.
    #[link_name = "interrupt_from_user"]
    fn x86_gpe_from_user(regs: *mut c_void) -> CInt;
    #[link_name = "set_cputime"]
    fn x86_gpe_set_cputime(mode: CUInt);
    #[link_name = "arch_show_interrupt_context"]
    fn x86_gpe_show_context(regs: *const c_void);
    #[link_name = "set_signal"]
    fn x86_gpe_set_signal(sig: CInt, regs: *mut c_void, info: *mut crate::abi::SigInfo);
    #[link_name = "interrupt_exit"]
    fn x86_gpe_interrupt_exit(regs: *mut X86UserContext);
    #[link_name = "panic"]
    fn x86_gpe_panic(message: *const i8) -> !;
