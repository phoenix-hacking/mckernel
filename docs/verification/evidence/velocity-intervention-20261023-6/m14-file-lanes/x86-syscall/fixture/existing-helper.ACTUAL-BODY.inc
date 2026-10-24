#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_syscall_event_body_result(
    thread: *mut c_void,
    ctx: *mut c_void,
    setret: CLong,
    syscall_ret_offset: SizeT,
    event_fn: Option<PtraceReportSignalFn>,
) -> CLong {
    if ctx.is_null() {
        return -(EFAULT as CLong);
    }
    let retp = field_ptr::<CULong>(ctx.cast::<u8>(), syscall_ret_offset);
    write_volatile(retp, setret as CULong);
    let Some(event) = event_fn else {
        return -(EFAULT as CLong);
    };
    event(thread, 0);
    read_volatile(retp) as CLong
}
