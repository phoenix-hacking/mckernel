#[no_mangle]
pub extern "C" fn signalfd4_sigsetsize_result(
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
) -> CInt {
    if sigsetsize != expected_sigset_size {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn signalfd4_flags_result(flags: CInt) -> CInt {
    if (flags & !(SFD_NONBLOCK | SFD_CLOEXEC)) != 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn signalfd4_body_result(
    fd: CInt,
    mask_addr: CULong,
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
    flags: CInt,
    thread: *mut c_void,
    syscall_nr: CInt,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    create_fn: Option<SyscallSignalfdCreateFn>,
    publish_fn: Option<SyscallSignalfdPublishFn>,
) -> CLong {
    let error = signalfd4_sigsetsize_result(sigsetsize, expected_sigset_size);
    if error != 0 {
        return error as CLong;
    }
    let Some(copy_from) = copy_from_fn else {
        return -(EFAULT as CLong);
    };
    let mut mask: CULong = 0;
    if mask_addr == 0
        || copy_from(
            (&mut mask as *mut CULong).cast::<u8>(),
            mask_addr,
            size_of::<CULong>(),
        ) != 0
    {
        return -(EFAULT as CLong);
    }
    let error = signalfd4_flags_result(flags);
    if error != 0 {
        return error as CLong;
    }
    if thread.is_null() {
        return -(EINVAL as CLong);
    }
    let Some(publish) = publish_fn else {
        return -(EINVAL as CLong);
    };

    let mut out_fd = fd;
    let mut create = 0;
    if fd == -1 {
        let Some(create_fd) = create_fn else {
            return -(EINVAL as CLong);
        };
        let created = create_fd(syscall_nr, flags);
        if created < 0 {
            return created;
        }
        out_fd = created as CInt;
        create = 1;
    }

    publish(thread, out_fd, &mask as *const CULong, create)
}

unsafe fn current_thread_ptr() -> *mut Thread {
    let cpu = get_this_cpu_local_var();
    if cpu.is_null() {
        null_mut()
    } else {
        (*cpu).current
    }
}

#[no_mangle]
pub unsafe extern "C" fn sys_signalfd4(_n: CInt, ctx: *mut X86UserContext) -> CLong {
    if ctx.is_null() {
        return -(EFAULT as CLong);
    }

    signalfd4_body_result(
        (*ctx).gpr.rdi as CInt,
        (*ctx).gpr.rsi,
        (*ctx).gpr.rdx as SizeT,
        size_of::<SigSet>(),
        (*ctx).gpr.r10 as CInt,
        current_thread_ptr().cast::<c_void>(),
        SYS_SIGNALFD4,
        Some(syscall_copy_from_user_bridge),
        Some(syscall_signalfd_create_bridge),
        Some(syscall_signalfd_publish_bridge),
    )
}
