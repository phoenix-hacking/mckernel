#[no_mangle]
pub unsafe extern "C" fn syscall_signalfd_create_bridge(
    syscall_nr: CInt,
    flags: CInt,
) -> CLong {
    let mut request = MaybeUninit::<SyscallRequest>::uninit();
    let requestp = request.as_mut_ptr();
    // Preserve the previously defined wire vector field by field. The actual
    // prepare/send providers own rtid, ttid and valid before their first copy.
    unsafe {
        addr_of_mut!((*requestp).number).write(syscall_nr as CULong);
        addr_of_mut!((*requestp).args[0]).write(0);
        addr_of_mut!((*requestp).args[1]).write(flags as CULong);
        addr_of_mut!((*requestp).args[2]).write(0);
        addr_of_mut!((*requestp).args[3]).write(0);
        addr_of_mut!((*requestp).args[4]).write(0);
        addr_of_mut!((*requestp).args[5]).write(0);
    }
    let cpu = ihk_mc_get_processor_id();
    do_syscall(requestp, cpu)
}
