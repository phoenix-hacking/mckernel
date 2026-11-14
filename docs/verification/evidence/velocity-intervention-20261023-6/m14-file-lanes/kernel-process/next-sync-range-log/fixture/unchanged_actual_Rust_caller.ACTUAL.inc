pub unsafe extern "C" fn process_sync_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    arg: *mut c_void,
    visit_step_fn: *mut c_void,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    log_fn: Option<ProcessSyncRangeLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() || (*vm).address_space.is_null() || (*range).memobj.is_null()
    {
        return -EINVAL;
    }
    if lock_fn.is_none() || unlock_fn.is_none() {
        return -EINVAL;
    }
    let Some(visit) = visit_fn else {
        return -EINVAL;
    };

    let memobj = (*range).memobj.cast::<Memobj>();
    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;
    let zero_fill = ((*memobj).flags & MF_ZEROFILL) != 0;

    let _ = process_noirq_lock_result(lock_addr, lock_fn);
    if !zero_fill {
        let _ = process_memobj_ref_direct_result(memobj);
    }

    let error = visit(
        (*(*vm).address_space).page_table,
        start,
        end,
        (*range).pgshift,
        VPTEF_SKIP_NULL,
        visit_step_fn,
        arg,
    );

    if !zero_fill {
        let _ = process_memobj_unref_direct_result(memobj);
    }
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);

    if error != 0 {
        if let Some(log) = log_fn {
            log(vm, range, start, end, error);
        }
    }

    error
}
