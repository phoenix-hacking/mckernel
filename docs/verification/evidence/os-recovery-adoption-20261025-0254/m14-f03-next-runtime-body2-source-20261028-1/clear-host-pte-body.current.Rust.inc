#[no_mangle]
pub unsafe extern "C" fn clear_host_pte_body_result(
    vm: *mut c_void,
    addr: CULong,
    len: SizeT,
    holding_memory_range_lock: CInt,
    vm_lock_taken_offset: SizeT,
    cpu: CInt,
    syscall_nr: CInt,
    forward_fn: Option<SyscallDoSyscall3Fn>,
    log_fn: Option<ClearHostPteLogFn>,
) -> CLong {
    if holding_memory_range_lock != 0 {
        *field_ptr::<CInt>(vm.cast::<u8>(), vm_lock_taken_offset) = cpu;
    }

    let lerror = if let Some(forward) = forward_fn {
        forward(syscall_nr, addr, len as CULong, 0)
    } else {
        (-EINVAL) as CLong
    };

    if holding_memory_range_lock != 0 {
        *field_ptr::<CInt>(vm.cast::<u8>(), vm_lock_taken_offset) = -1;
    }
    if lerror != 0 {
        if let Some(log) = log_fn {
            log(lerror);
        }
    }
    lerror
}
