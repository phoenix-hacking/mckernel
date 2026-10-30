//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private x86 ENABLE_PERF entry specialization. The generic exported ABI and
//! generic callback ownership contracts remain unchanged. Requires the exact
//! selected allocator, counter, group and tracked-free providers in RESULT.json.
use super::*;

unsafe fn perf_entry_body_with_group_cleanup(
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
    // This private specialization is bound to the x86 Mckfd layout below.
    // Reject a mismatched allocator extent before allocating an event or issuing
    // the host request; no out-of-bounds field initialization is permitted.
    if mckfd_size != core::mem::size_of::<Mckfd>() {
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
        // The selected group helper has not published the fresh event on any
        // error return; the selected counter provider only scanned its map.
        // The matching tracked free consumes this still-private allocation.
        // Preserve the group error and leave all later failure paths alone.
        unsafe { super::perf_event_alloc_free_bridge(event) };
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
        // Only a standalone event is still private: its leader points to
        // itself and no sibling/descriptor published it. The selected counter
        // provider has only scanned the allocation map, and the host helper
        // returns before setting that map on this branch. Grouped events need
        // a separately reviewed leader/reader lifetime and are left unchanged.
        if group_fd == -1 {
            unsafe { super::perf_event_alloc_free_bridge(event) };
        }
        return fd;
    }

    let sfd = mckfd_alloc(mckfd_size, mckfd_alloc_flags);
    if sfd.is_null() {
        return -ENOMEM as CLong;
    }

    // Fresh private allocation, not yet visible in the process descriptor list.
    // kmalloc is not zeroing. Initialize the two fields that the publisher does
    // not assign, without borrowing or changing the C sig_no slot.
    let descriptor = sfd.cast::<Mckfd>();
    core::ptr::addr_of_mut!((*descriptor).opt).write(core::ptr::null_mut());
    core::ptr::addr_of_mut!((*descriptor).dup_cb).write(core::ptr::null_mut());

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

pub(super) unsafe fn perf_entry_with_group_cleanup(
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

    perf_entry_body_with_group_cleanup(
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

// Paired C assertions bind these offsets to the selected x86 C header.
const _: () = {
    assert!(core::mem::size_of::<Mckfd>() == 80);
    assert!(core::mem::align_of::<Mckfd>() == 8);
    assert!(core::mem::offset_of!(Mckfd, opt) == 24);
    assert!(core::mem::offset_of!(Mckfd, dup_cb) == 72);
};

#[cfg(test)]
#[path = "f03_perf_descriptor_init_tests.rs"]
mod f03_perf_descriptor_init_tests;
