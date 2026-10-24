#[no_mangle]
pub unsafe extern "C" fn move_pages_body_result(
    pid: CInt,
    count: CULong,
    user_virt_addr_addr: CULong,
    user_nodes_addr: CULong,
    user_status_addr: CULong,
    flags: CInt,
    vm: *mut ProcessVm,
    page_table_lock: *mut c_void,
    cpu_set: *mut c_void,
    proc: *mut c_void,
    alloc_flags: CULong,
    ptr_size: SizeT,
    int_size: SizeT,
    pte_size: SizeT,
    ulong_size: SizeT,
    verify_fn: Option<MovePagesVerifyFn>,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    alloc_fn: Option<SyscallPolicyAllocFn>,
    free_fn: Option<SyscallMckfdFreeFn>,
    get_nr_nodes_fn: Option<MovePagesGetNrNodesFn>,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    smp_call_fn: Option<MovePagesSmpCallFn>,
    handler_fn: Option<MovePagesSmpHandlerFn>,
    rdtsc_fn: Option<SyscallRdtscFn>,
    log_fn: Option<MovePagesLogFn>,
) -> CLong {
    let policy_error = move_pages_policy_result(pid, flags);
    if policy_error != 0 {
        if let Some(log) = log_fn {
            if pid != 0 {
                log(MOVE_PAGES_LOG_UNSUPPORTED_PID, 0, policy_error);
            } else if (flags & MPOL_MF_MOVE_ALL) != 0 {
                log(MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL, 0, policy_error);
            }
        }
        return policy_error as CLong;
    }

    let (
        Some(alloc),
        Some(verify),
        Some(copy_to),
        Some(get_nr_nodes),
        Some(lock),
        Some(unlock),
        Some(smp_call),
        Some(handler),
    ) = (
        alloc_fn,
        verify_fn,
        copy_to_fn,
        get_nr_nodes_fn,
        lock_fn,
        unlock_fn,
        smp_call_fn,
        handler_fn,
    )
    else {
        return -(EFAULT as CLong);
    };

    if vm.is_null() || page_table_lock.is_null() || cpu_set.is_null() || proc.is_null() {
        return -(EFAULT as CLong);
    }

    let count_size = count as SizeT;
    let ptr_bytes = ptr_size.wrapping_mul(count_size);
    let int_bytes = int_size.wrapping_mul(count_size);
    let pte_bytes = pte_size.wrapping_mul(count_size);
    let ulong_bytes = ulong_size.wrapping_mul(count_size);
    let mut start = rdtsc_fn.map_or(0, |rdtsc| rdtsc());

    let virt_addr = alloc(ptr_bytes, alloc_flags);
    if virt_addr.is_null() {
        return -(ENOMEM as CLong);
    }
    let nr_pages = alloc(int_bytes, alloc_flags);
    if nr_pages.is_null() {
        move_pages_free_arrays(
            free_fn,
            virt_addr,
            nr_pages,
            null_mut(),
            null_mut(),
            null_mut(),
            null_mut(),
        );
        return -(ENOMEM as CLong);
    }
    let nodes = alloc(int_bytes, alloc_flags);
    if nodes.is_null() {
        move_pages_free_arrays(
            free_fn,
            virt_addr,
            nr_pages,
            nodes,
            null_mut(),
            null_mut(),
            null_mut(),
        );
        return -(ENOMEM as CLong);
    }
    let status = alloc(int_bytes, alloc_flags);
    if status.is_null() {
        move_pages_free_arrays(
            free_fn,
            virt_addr,
            nr_pages,
            nodes,
            status,
            null_mut(),
            null_mut(),
        );
        return -(ENOMEM as CLong);
    }
    let ptep = alloc(pte_bytes, alloc_flags);
    if ptep.is_null() {
        move_pages_free_arrays(
            free_fn,
            virt_addr,
            nr_pages,
            nodes,
            status,
            ptep,
            null_mut(),
        );
        return -(ENOMEM as CLong);
    }
    let dst_phys = alloc(ulong_bytes, alloc_flags);
    if dst_phys.is_null() {
        move_pages_free_arrays(free_fn, virt_addr, nr_pages, nodes, status, ptep, dst_phys);
        return -(ENOMEM as CLong);
    }

    start = move_pages_log_delta(log_fn, rdtsc_fn, MOVE_PAGES_LOG_INIT_MALLOC, start);

    let mut ret = 0;
    if verify(vm, user_virt_addr_addr, ptr_bytes) != 0 {
        ret = -EFAULT;
    } else if user_nodes_addr != 0 && verify(vm, user_nodes_addr, int_bytes) != 0 {
        ret = -EFAULT;
    } else if verify(vm, user_status_addr, int_bytes) != 0 {
        ret = -EFAULT;
    }

    if ret == 0 && user_nodes_addr != 0 {
        if let Some(copy_from) = copy_from_fn {
            let _ = copy_from(nodes.cast::<u8>(), user_nodes_addr, int_bytes);
            let nr_nodes = get_nr_nodes();
            let nodes_i32 = nodes.cast::<CInt>();
            let mut i = 0usize;
            while i < count_size {
                let node = read_volatile(nodes_i32.add(i));
                if node < 0 || node >= nr_nodes {
                    ret = -ENODEV;
                    break;
                }
                i += 1;
            }
        } else {
            ret = -EFAULT;
        }
    }

    start = move_pages_log_delta(log_fn, rdtsc_fn, MOVE_PAGES_LOG_INIT_VERIFY, start);

    if ret == 0 {
        let mut request = MaybeUninit::<MovePagesSmpReq>::uninit();
        lock(page_table_lock);
        ret = move_pages_smp_req_prepare_result(
            request.as_mut_ptr(),
            count,
            user_virt_addr_addr as *mut *const c_void,
            user_status_addr as *mut CInt,
            user_nodes_addr as *const CInt,
            virt_addr.cast::<*mut c_void>(),
            status.cast::<CInt>(),
            ptep.cast::<*mut c_void>(),
            nodes.cast::<CInt>(),
            nr_pages.cast::<CInt>(),
            dst_phys.cast::<CULong>(),
            proc,
        );
        if ret == 0 {
            ret = smp_call(
                cpu_set,
                Some(handler),
                request.as_mut_ptr().cast::<c_void>(),
            );
        }
        unlock(page_table_lock);
    }

    if ret == 0 {
        let _ = move_pages_log_delta(log_fn, rdtsc_fn, MOVE_PAGES_LOG_PARALLEL, start);
        if copy_to(user_status_addr, status.cast::<u8>(), int_bytes) != 0 {
            ret = -EFAULT;
        }
    }

    move_pages_free_arrays(free_fn, virt_addr, nr_pages, nodes, status, ptep, dst_phys);
    ret as CLong
}
