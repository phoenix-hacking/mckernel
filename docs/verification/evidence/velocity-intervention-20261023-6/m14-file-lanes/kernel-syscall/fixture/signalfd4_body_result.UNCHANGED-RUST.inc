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
