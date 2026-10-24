pub unsafe extern "C" fn x86_print_user_context_body_result(
    uctx: *const X86UserContext,
    log_fn: Option<X86ContextLogFn>,
) -> CInt {
    if uctx.is_null() {
        return -EINVAL;
    }
    let Some(log) = log_fn else {
        return -EINVAL;
    };

    unsafe {
        let regs = &(*uctx).gpr;
        log(20, regs.cs, regs.rip, 0, 0);
        log(21, regs.rax, regs.rbx, regs.rcx, regs.rdx);
        log(22, regs.rsi, regs.rdi, regs.rsp, 0);
    }
    0
}
