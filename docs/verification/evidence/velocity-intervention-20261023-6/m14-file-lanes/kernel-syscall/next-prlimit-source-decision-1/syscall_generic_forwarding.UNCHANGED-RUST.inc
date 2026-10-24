#[no_mangle]
pub unsafe extern "C" fn syscall_generic_forwarding(n: CInt, ctx: *mut X86UserContext) -> CLong {
    if ctx.is_null() {
        return -(EINVAL as CLong);
    }

    let cpu = ihk_mc_get_processor_id();
    #[cfg(not(mckernel_equivalence))]
    {
        let this_cpu = crate::cls::get_this_cpu_local_var();
        let thread = if this_cpu.is_null() {
            null_mut()
        } else {
            (*this_cpu).current
        };
        let process = if thread.is_null() {
            null_mut()
        } else {
            (*thread).proc
        };
        let pid = if process.is_null() {
            -1
        } else {
            (*process).pid
        };
        if syscall_owner_log_budget(&GENERIC_FORWARD_LOG_STATE, pid) {
            kprintf(
                c"mcexec_v10: generic_forwarding owner=rust cpu=%d pid=%d nr=%d\n"
                    .as_ptr()
                    .cast(),
                cpu,
                pid,
                n,
            );
        }
    }

    let mut request = MaybeUninit::<SyscallRequest>::zeroed().assume_init();
    syscall_generic_forwarding_body_result(
        addr_of_mut!(request),
        n,
        crate::x86_cpu_helpers::ihk_mc_syscall_arg0(ctx),
        crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx),
        crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx),
        crate::x86_cpu_helpers::ihk_mc_syscall_arg3(ctx),
        crate::x86_cpu_helpers::ihk_mc_syscall_arg4(ctx),
        crate::x86_cpu_helpers::ihk_mc_syscall_arg5(ctx),
        cpu,
        Some(do_syscall),
    )
}
