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
