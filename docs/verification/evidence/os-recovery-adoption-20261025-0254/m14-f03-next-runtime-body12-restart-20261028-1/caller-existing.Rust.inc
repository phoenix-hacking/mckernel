pub unsafe extern "C" fn sys_util_register_desc(_n: CInt, ctx: *mut X86UserContext) -> CLong {
    if ctx.is_null() {
        return -(EFAULT as CLong);
    }

    let desc = (*ctx).gpr.rdi;
    let thread = current_thread_ptr();
    let tid = if thread.is_null() { -1 } else { (*thread).tid };
    syscall_util_register_desc_log_bridge(tid, desc);
    util_register_desc_body_result(desc, addr_of_mut!(uti_desc))
}
