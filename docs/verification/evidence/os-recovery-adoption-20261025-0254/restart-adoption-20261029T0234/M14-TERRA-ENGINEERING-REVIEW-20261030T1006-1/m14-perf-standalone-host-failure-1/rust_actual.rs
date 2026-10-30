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
) -> CLong { panic!("unreachable downstream provider invoked") }
