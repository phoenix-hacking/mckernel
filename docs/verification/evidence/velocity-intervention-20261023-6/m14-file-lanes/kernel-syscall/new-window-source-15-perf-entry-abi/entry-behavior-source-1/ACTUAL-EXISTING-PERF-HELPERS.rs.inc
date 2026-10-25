unsafe fn field_ptr<T>(base: *mut u8, offset: SizeT) -> *mut T {
    base.add(offset).cast::<T>()
}

fn perf_event_bit_result(index: CInt) -> CULong {
    if index < 0 || index >= (size_of::<CULong>() * 8) as CInt {
        0
    } else {
        1u64 << (index as u32)
    }
}

#[no_mangle]
pub extern "C" fn perf_event_open_validate_body_result(
    cpu: CInt,
    flags: CULong,
    attr_type: CULong,
    read_format: CULong,
    freq: CInt,
    sample_period: CULong,
    raw_type: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    unsupported_read_format_mask: CULong,
    sample_period_sign_bit: CULong,
) -> CInt {
    let mut unsupported = cpu > 0 || flags > 0;

    if attr_type != raw_type && attr_type != hardware_type && attr_type != hw_cache_type {
        unsupported = true;
    }
    if (read_format & unsupported_read_format_mask) != 0 {
        unsupported = true;
    }

    if freq != 0 {
        unsupported = true;
    } else if (sample_period & sample_period_sign_bit) != 0 {
        return -EINVAL;
    }

    if unsupported {
        -ENOENT
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_group_body_result(
    event: *mut c_void,
    proc: *mut c_void,
    group_fd: CInt,
    counter_idx: CInt,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_data_offset: SizeT,
    event_group_leader_offset: SizeT,
    event_sibling_list_offset: SizeT,
    event_group_entry_offset: SizeT,
    event_nr_siblings_offset: SizeT,
    event_pmc_status_offset: SizeT,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }

    let event_base = event.cast::<u8>();
    let leader = if group_fd == -1 {
        write_volatile(
            field_ptr::<*mut c_void>(event_base, event_group_leader_offset),
            event,
        );
        write_volatile(field_ptr::<CULong>(event_base, event_pmc_status_offset), 0);
        event
    } else {
        if proc.is_null() {
            return -EINVAL as CLong;
        }

        let mut cur = read_volatile(field_ptr::<*mut c_void>(
            proc.cast::<u8>(),
            proc_mckfd_offset,
        ));
        let mut found = core::ptr::null_mut::<c_void>();
        while !cur.is_null() {
            let cur_base = cur.cast::<u8>();
            if read_volatile(field_ptr::<CInt>(cur_base, mckfd_fd_offset)) == group_fd {
                let data = read_volatile(field_ptr::<CLong>(cur_base, mckfd_data_offset));
                found = data as usize as *mut c_void;
                break;
            }
            cur = read_volatile(field_ptr::<*mut c_void>(cur_base, mckfd_next_offset));
        }
        if found.is_null() {
            return -EINVAL as CLong;
        }

        write_volatile(
            field_ptr::<*mut c_void>(event_base, event_group_leader_offset),
            found,
        );

        let leader_base = found.cast::<u8>();
        let entry = field_ptr::<AbiListHead>(event_base, event_group_entry_offset);
        let head = field_ptr::<AbiListHead>(leader_base, event_sibling_list_offset);
        let prev = read_volatile(core::ptr::addr_of!((*head).prev));
        if prev.is_null() {
            return -EINVAL as CLong;
        }
        write_volatile(core::ptr::addr_of_mut!((*entry).next), head);
        write_volatile(core::ptr::addr_of_mut!((*entry).prev), prev);
        write_volatile(core::ptr::addr_of_mut!((*prev).next), entry);
        write_volatile(core::ptr::addr_of_mut!((*head).prev), entry);

        let nr_siblings = field_ptr::<CInt>(leader_base, event_nr_siblings_offset);
        write_volatile(nr_siblings, read_volatile(nr_siblings).wrapping_add(1));
        found
    };

    let leader_base = leader.cast::<u8>();
    let pmc_status = field_ptr::<CULong>(leader_base, event_pmc_status_offset);
    write_volatile(
        pmc_status,
        read_volatile(pmc_status) | perf_event_bit_result(counter_idx),
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_counter_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    pid: CInt,
    event_pid_offset: SizeT,
    event_counter_id_offset: SizeT,
    counter_alloc_fn: Option<PerfCounterAllocFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(counter_alloc) = counter_alloc_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    write_volatile(field_ptr::<CInt>(event_base, event_pid_offset), pid);
    let counter_idx = counter_alloc(thread, event);
    if counter_idx < 0 {
        return counter_idx as CLong;
    }
    write_volatile(
        field_ptr::<CInt>(event_base, event_counter_id_offset),
        counter_idx,
    );

    counter_idx as CLong
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_linux_fd_body_result(
    request: *mut SyscallRequest,
    thread: *mut c_void,
    counter_idx: CInt,
    perf_event_open_nr: CInt,
    cpu: CInt,
    thread_pmc_alloc_map_offset: SizeT,
    syscall_fn: Option<PerfOpenSyscallFn>,
) -> CLong {
    if request.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(syscall) = syscall_fn else {
        return -EINVAL as CLong;
    };

    write_volatile(
        core::ptr::addr_of_mut!((*request).number),
        perf_event_open_nr as CULong,
    );
    write_volatile(core::ptr::addr_of_mut!((*request).args[0]), 0);
    // SAFETY: The caller owns this fresh, unpublished request. The selected
    // Linux consumer ignores these five arguments; IDs and valid remain owned
    // by the unchanged offload preparation/publication chain.
    unsafe {
        write_volatile(core::ptr::addr_of_mut!((*request).args[1]), 0);
        write_volatile(core::ptr::addr_of_mut!((*request).args[2]), 0);
        write_volatile(core::ptr::addr_of_mut!((*request).args[3]), 0);
        write_volatile(core::ptr::addr_of_mut!((*request).args[4]), 0);
        write_volatile(core::ptr::addr_of_mut!((*request).args[5]), 0);
    }
    let fd = syscall(request, cpu);
    if fd < 0 {
        return fd;
    }

    let thread_base = thread.cast::<u8>();
    let pmc_map = field_ptr::<CULong>(thread_base, thread_pmc_alloc_map_offset);
    write_volatile(
        pmc_map,
        read_volatile(pmc_map) | perf_event_bit_result(counter_idx),
    );

    fd
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_mckfd_publish_body_result(
    sfd: *mut c_void,
    event: *mut c_void,
    proc: *mut c_void,
    fd: CInt,
    proc_mckfd_lock_offset: SizeT,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_sig_no_offset: SizeT,
    mckfd_data_offset: SizeT,
    mckfd_read_cb_offset: SizeT,
    mckfd_ioctl_cb_offset: SizeT,
    mckfd_mmap_cb_offset: SizeT,
    mckfd_close_cb_offset: SizeT,
    mckfd_fcntl_cb_offset: SizeT,
    read_fn: Option<SyscallMckfdLongFn>,
    ioctl_fn: Option<SyscallMckfdIntFn>,
    mmap_fn: Option<SyscallMckfdLongFn>,
    close_fn: Option<SyscallMckfdIntFn>,
    fcntl_fn: Option<SyscallMckfdIntFn>,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    if sfd.is_null() || event.is_null() || proc.is_null() {
        return -EINVAL as CLong;
    }
    if read_fn.is_none()
        || ioctl_fn.is_none()
        || mmap_fn.is_none()
        || close_fn.is_none()
        || fcntl_fn.is_none()
    {
        return -EINVAL as CLong;
    }
    let Some(lock) = lock_fn else {
        return -EINVAL as CLong;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL as CLong;
    };

    let sfd_base = sfd.cast::<u8>();
    write_volatile(field_ptr::<CInt>(sfd_base, mckfd_fd_offset), fd);
    write_volatile(field_ptr::<CInt>(sfd_base, mckfd_sig_no_offset), -1);
    write_volatile(
        field_ptr::<CLong>(sfd_base, mckfd_data_offset),
        event as isize as CLong,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdLongFn>>(sfd_base, mckfd_read_cb_offset),
        read_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdIntFn>>(sfd_base, mckfd_ioctl_cb_offset),
        ioctl_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdLongFn>>(sfd_base, mckfd_mmap_cb_offset),
        mmap_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdIntFn>>(sfd_base, mckfd_close_cb_offset),
        close_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdIntFn>>(sfd_base, mckfd_fcntl_cb_offset),
        fcntl_fn,
    );

    let proc_base = proc.cast::<u8>();
    let lock_ptr = field_ptr::<c_void>(proc_base, proc_mckfd_lock_offset);
    let irqstate = lock(lock_ptr);
    let headp = field_ptr::<*mut c_void>(proc_base, proc_mckfd_offset);
    let old_head = read_volatile(headp);
    write_volatile(
        field_ptr::<*mut c_void>(sfd_base, mckfd_next_offset),
        old_head,
    );
    write_volatile(headp, sfd);
    unlock(lock_ptr, irqstate);

    fd as CLong
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_body_result(
    request: *mut SyscallRequest,
    thread: *mut c_void,
    proc: *mut c_void,
    attr: *mut c_void,
    pid: CInt,
    group_fd: CInt,
    perf_event_open_nr: CInt,
    cpu: CInt,
    mckfd_size: SizeT,
    mckfd_alloc_flags: CULong,
    event_pid_offset: SizeT,
    event_counter_id_offset: SizeT,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_data_offset: SizeT,
    event_group_leader_offset: SizeT,
    event_sibling_list_offset: SizeT,
    event_group_entry_offset: SizeT,
    event_nr_siblings_offset: SizeT,
    event_pmc_status_offset: SizeT,
    thread_pmc_alloc_map_offset: SizeT,
    proc_mckfd_lock_offset: SizeT,
    mckfd_sig_no_offset: SizeT,
    mckfd_read_cb_offset: SizeT,
    mckfd_ioctl_cb_offset: SizeT,
    mckfd_mmap_cb_offset: SizeT,
    mckfd_close_cb_offset: SizeT,
    mckfd_fcntl_cb_offset: SizeT,
    event_alloc_fn: Option<PerfOpenAllocEventFn>,
    counter_alloc_fn: Option<PerfCounterAllocFn>,
    syscall_fn: Option<PerfOpenSyscallFn>,
    mckfd_alloc_fn: Option<SyscallPolicyAllocFn>,
    read_fn: Option<SyscallMckfdLongFn>,
    ioctl_fn: Option<SyscallMckfdIntFn>,
    mmap_fn: Option<SyscallMckfdLongFn>,
    close_fn: Option<SyscallMckfdIntFn>,
    fcntl_fn: Option<SyscallMckfdIntFn>,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    if request.is_null() || thread.is_null() || proc.is_null() || attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(event_alloc) = event_alloc_fn else {
        return -EINVAL as CLong;
    };
    let Some(mckfd_alloc) = mckfd_alloc_fn else {
        return -EINVAL as CLong;
    };

    let mut event = core::ptr::null_mut::<c_void>();
    let mut ret = event_alloc(core::ptr::addr_of_mut!(event), attr);
    if ret != 0 {
        return ret as CLong;
    }

    let counter_idx = perf_event_open_counter_body_result(
        event,
        thread,
        pid,
        event_pid_offset,
        event_counter_id_offset,
        counter_alloc_fn,
    );
    if counter_idx < 0 {
        return counter_idx;
    }

    let group_rc = perf_event_open_group_body_result(
        event,
        proc,
        group_fd,
        counter_idx as CInt,
        proc_mckfd_offset,
        mckfd_next_offset,
        mckfd_fd_offset,
        mckfd_data_offset,
        event_group_leader_offset,
        event_sibling_list_offset,
        event_group_entry_offset,
        event_nr_siblings_offset,
        event_pmc_status_offset,
    );
    if group_rc != 0 {
        return group_rc;
    }

    let fd = perf_event_open_linux_fd_body_result(
        request,
        thread,
        counter_idx as CInt,
        perf_event_open_nr,
        cpu,
        thread_pmc_alloc_map_offset,
        syscall_fn,
    );
    if fd < 0 {
        return fd;
    }

    let sfd = mckfd_alloc(mckfd_size, mckfd_alloc_flags);
    if sfd.is_null() {
        return -ENOMEM as CLong;
    }

    ret = perf_event_open_mckfd_publish_body_result(
        sfd,
        event,
        proc,
        fd as CInt,
        proc_mckfd_lock_offset,
        proc_mckfd_offset,
        mckfd_next_offset,
        mckfd_fd_offset,
        mckfd_sig_no_offset,
        mckfd_data_offset,
        mckfd_read_cb_offset,
        mckfd_ioctl_cb_offset,
        mckfd_mmap_cb_offset,
        mckfd_close_cb_offset,
        mckfd_fcntl_cb_offset,
        read_fn,
        ioctl_fn,
        mmap_fn,
        close_fn,
        fcntl_fn,
        lock_fn,
        unlock_fn,
    ) as CInt;
    ret as CLong
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_entry_body_result(
    request: *mut SyscallRequest,
    thread: *mut c_void,
    proc: *mut c_void,
    attr: *mut c_void,
    user_attr_addr: CULong,
    attr_size: SizeT,
    attr_type_offset: SizeT,
    attr_read_format_offset: SizeT,
    attr_sample_period_offset: SizeT,
    pid: CInt,
    validation_cpu: CInt,
    group_fd: CInt,
    flags: CULong,
    linux_cpu: CInt,
    raw_type: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    unsupported_read_format_mask: CULong,
    sample_period_sign_bit: CULong,
    perf_event_open_nr: CInt,
    mckfd_size: SizeT,
    mckfd_alloc_flags: CULong,
    event_pid_offset: SizeT,
    event_counter_id_offset: SizeT,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_data_offset: SizeT,
    event_group_leader_offset: SizeT,
    event_sibling_list_offset: SizeT,
    event_group_entry_offset: SizeT,
    event_nr_siblings_offset: SizeT,
    event_pmc_status_offset: SizeT,
    thread_pmc_alloc_map_offset: SizeT,
    proc_mckfd_lock_offset: SizeT,
    mckfd_sig_no_offset: SizeT,
    mckfd_read_cb_offset: SizeT,
    mckfd_ioctl_cb_offset: SizeT,
    mckfd_mmap_cb_offset: SizeT,
    mckfd_close_cb_offset: SizeT,
    mckfd_fcntl_cb_offset: SizeT,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    attr_freq_fn: Option<PerfAttrFreqFn>,
    event_alloc_fn: Option<PerfOpenAllocEventFn>,
    counter_alloc_fn: Option<PerfCounterAllocFn>,
    syscall_fn: Option<PerfOpenSyscallFn>,
    mckfd_alloc_fn: Option<SyscallPolicyAllocFn>,
    read_fn: Option<SyscallMckfdLongFn>,
    ioctl_fn: Option<SyscallMckfdIntFn>,
    mmap_fn: Option<SyscallMckfdLongFn>,
    close_fn: Option<SyscallMckfdIntFn>,
    fcntl_fn: Option<SyscallMckfdIntFn>,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    if attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(copy_from_user) = copy_from_fn else {
        return -EINVAL as CLong;
    };
    let Some(attr_freq) = attr_freq_fn else {
        return -EINVAL as CLong;
    };

    if copy_from_user(attr.cast::<u8>(), user_attr_addr, attr_size) != 0 {
        return -EFAULT as CLong;
    }

    let attr_base = attr.cast::<u8>();
    let attr_type = read_volatile(field_ptr::<u32>(attr_base, attr_type_offset)) as CULong;
    let read_format = read_volatile(field_ptr::<CULong>(attr_base, attr_read_format_offset));
    let sample_period = read_volatile(field_ptr::<CULong>(attr_base, attr_sample_period_offset));
    let freq = attr_freq(attr.cast_const());

    let ret = perf_event_open_validate_body_result(
        validation_cpu,
        flags,
        attr_type,
        read_format,
        freq,
        sample_period,
        raw_type,
        hardware_type,
        hw_cache_type,
        unsupported_read_format_mask,
        sample_period_sign_bit,
    );
    if ret != 0 {
        return ret as CLong;
    }

    perf_event_open_body_result(
        request,
        thread,
        proc,
        attr,
        pid,
        group_fd,
        perf_event_open_nr,
        linux_cpu,
        mckfd_size,
        mckfd_alloc_flags,
        event_pid_offset,
        event_counter_id_offset,
        proc_mckfd_offset,
        mckfd_next_offset,
        mckfd_fd_offset,
        mckfd_data_offset,
        event_group_leader_offset,
        event_sibling_list_offset,
        event_group_entry_offset,
        event_nr_siblings_offset,
        event_pmc_status_offset,
        thread_pmc_alloc_map_offset,
        proc_mckfd_lock_offset,
        mckfd_sig_no_offset,
        mckfd_read_cb_offset,
        mckfd_ioctl_cb_offset,
        mckfd_mmap_cb_offset,
        mckfd_close_cb_offset,
        mckfd_fcntl_cb_offset,
        event_alloc_fn,
        counter_alloc_fn,
        syscall_fn,
        mckfd_alloc_fn,
        read_fn,
        ioctl_fn,
        mmap_fn,
        close_fn,
        fcntl_fn,
        lock_fn,
        unlock_fn,
    )
}
