// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// SOURCE FRAGMENT ONLY, use actual current abi.rs, no model context layout.
type X86ContextLogFn=unsafe extern "C" fn(CInt,CULong,CULong,CULong,CULong);
unsafe extern "C" { fn x86_context_line_log_bridge(event:CInt,a:CULong,b:CULong,c:CULong,d:CULong); }
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

/// Retire the selected C entry while reusing its exact existing Rust core.
/// The original selected entry discarded the core result. In particular, a
/// null context retains the existing core's -EINVAL/no-log behavior; no new
/// frame or freeze/null policy is introduced. Context/log pointers do not escape.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_print_user_context(uctx: *mut X86UserContext) {
    unsafe {
        let _ = x86_print_user_context_body_result(
            uctx,
            Some(x86_context_line_log_bridge),
        );
    }
}
