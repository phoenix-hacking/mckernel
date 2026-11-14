#[no_mangle]
pub unsafe extern "C" fn sys_swapout(_n: CInt, ctx: *mut X86UserContext) -> CLong {
    if ctx.is_null() {
        return -(EFAULT as CLong);
    }
    let filename = (*ctx).gpr.rdi as *const c_void;
    let workarea = (*ctx).gpr.rsi as *mut c_void;
    let size = (*ctx).gpr.rdx as SizeT;
    let flag = (*ctx).gpr.r10 as CInt;
    let mut linux_ctx = MaybeUninit::<X86UserContext>::uninit();

    syscall_swapout_log_bridge(filename, workarea, size, flag);
    swapout_body_result(
        filename,
        workarea,
        size,
        flag,
        SYS_SWAPOUT,
        linux_ctx.as_mut_ptr().cast::<c_void>(),
        Some(do_pageout),
        Some(do_pagein),
        Some(syscall_policy_forward_context_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn sys_linux_mlock(_n: CInt, ctx: *mut X86UserContext) -> CLong {
    if ctx.is_null() {
        return -(EFAULT as CLong);
    }

    let addr = (*ctx).gpr.rdi;
    let len = (*ctx).gpr.rsi as SizeT;
    syscall_linux_mlock_log_bridge(addr, len);
    linux_mlock_body_result(
        addr,
        len,
        SYS_LINUX_MLOCK,
        Some(syscall_policy_do_syscall2_bridge),
    )
}
