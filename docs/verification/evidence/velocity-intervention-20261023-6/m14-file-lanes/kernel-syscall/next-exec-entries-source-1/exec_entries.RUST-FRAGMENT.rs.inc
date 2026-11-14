// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete live sys_execve/sys_execveat entries; existing C exec lifecycle is debt.
extern "C" {
    #[link_name = "syscall_execveat_bridge"]
    fn f03_execveat_existing_C_provider(
        ctx: *mut c_void, dirfd: CInt, filename: *const c_void,
        argv: *mut *mut c_void, envp: *mut *mut c_void, flags: CInt,
    ) -> CInt;
}

/// # Safety
/// The original current-thread user-context and exec-provider lifetime/ownership
/// contract applies. No new context copy, argument initialization or null guard.
#[no_mangle]
pub unsafe extern "C" fn sys_execve(_n: CInt, ctx: *mut X86UserContext) -> CLong {
    execve_body_result(
        ctx.cast::<c_void>(),
        crate::x86_cpu_helpers::ihk_mc_syscall_arg0(ctx) as *const c_void,
        crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx) as *mut *mut c_void,
        crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx) as *mut *mut c_void,
        Some(f03_execveat_existing_C_provider),
    )
}

/// # Safety
/// In addition to the original exec context/provider contract, filename must
/// permit the original first-byte read even when flags/dirfd will be rejected.
/// This preserves the existing pre-policy read; no invalid-pointer EFAULT proof.
#[no_mangle]
pub unsafe extern "C" fn sys_execveat(_n: CInt, ctx: *mut X86UserContext) -> CLong {
    let dirfd = crate::x86_cpu_helpers::ihk_mc_syscall_arg0(ctx) as CInt;
    let filename = crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx) as *const c_void;
    let flags = crate::x86_cpu_helpers::ihk_mc_syscall_arg4(ctx) as CInt;
    execveat_body_result(
        ctx.cast::<c_void>(), dirfd, filename,
        crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx) as *mut *mut c_void,
        crate::x86_cpu_helpers::ihk_mc_syscall_arg3(ctx) as *mut *mut c_void,
        flags, *filename.cast::<i8>() as CInt,
        Some(f03_execveat_existing_C_provider),
    )
}
