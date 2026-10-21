#[no_mangle]
pub unsafe extern "C" fn act_execve_phase2(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) -> c_long {
    let size = unsafe { (*w).sr.args[2] as usize };
    let desc = unsafe { malloc(size) };
    if desc.is_null() {
        unsafe {
            mcexec_execve2_alloc_desc_failed_bridge();
            do_syscall_return(fd, cpu, -1, 0, 0, 0, 0);
        }
        return 0;
    }
    unsafe { zero_bytes(desc, size) };

    let transfer = RemoteTransfer {
        rphys: unsafe { (*w).sr.args[1] },
        userp: desc as *mut c_void,
        size: size as c_ulong,
        direction: MCEXEC_UP_TRANSFER_FROM_REMOTE,
    };
    if unsafe {
        ioctl(
            fd,
            MCEXEC_UP_TRANSFER,
            &transfer as *const RemoteTransfer as c_ulong,
        )
    } != 0
    {
        unsafe {
            mcexec_execve2_transfer_desc_failed_bridge();
            do_syscall_return(fd, cpu, EINVAL as c_long, 0, 0, 0, 0);
        }
        return 0;
    }

    unsafe { mcexec_execve2_transfer_desc_ok_bridge() };
    if unsafe { transfer_image(fd, desc as *mut c_void) } != 0 {
        unsafe { mcexec_execve2_transfer_image_failed_bridge() };
        return -1;
    }
    unsafe { mcexec_execve2_image_transferred_bridge() };

    let close_ret = unsafe { ioctl(fd, MCEXEC_UP_CLOSE_EXEC, 0 as c_ulong) };
    if close_ret != 0 {
        unsafe { mcexec_execve2_close_exec_failed_bridge(close_ret) };
        return 1;
    }

    if unsafe { close_cloexec_fds(fd) } < 0 {
        unsafe { do_syscall_return(fd, cpu, EINVAL as c_long, 0, 0, 0, 0) };
        return 0;
    }

    unsafe { do_syscall_return(fd, cpu, 0, 0, 0, 0, 0) };
    0
}
