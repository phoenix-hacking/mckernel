// M14-F03: retire the selected signalfd host-FD request/admission callback.
// Supported x86 IHK_DMA_ALIGN is empty; SyscallRequest retains its repr(C)
// natural alignment. The synchronous do_syscall ownership contract is unchanged.
#[no_mangle]
pub unsafe extern "C" fn syscall_signalfd_create_bridge(
    syscall_nr: CInt,
    flags: CInt,
) -> CLong {
    let mut request = MaybeUninit::<SyscallRequest>::zeroed();
    let requestp = request.as_mut_ptr();
    (*requestp).number = syscall_nr as CULong;
    (*requestp).args[0] = 0;
    (*requestp).args[1] = flags as CULong;
    let cpu = ihk_mc_get_processor_id();
    do_syscall(requestp, cpu)
}
