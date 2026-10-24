pub unsafe extern "C" fn process_remap_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    off: OffT,
    arg: *mut c_void,
    visit_step_fn: *mut c_void,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    log_fn: Option<ProcessRemapRangeLogFn>,
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

    let _ = process_noirq_lock_result(lock_addr, lock_fn);
    let _ = process_memobj_ref_direct_result(memobj);

    let pgshift = AtomicI32::from_ptr(&raw mut (*range).pgshift);
    let old_pgshift =
        match pgshift.compare_exchange(0, PAGE_SHIFT as CInt, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(old) | Err(old) => old,
        };

    let error = if old_pgshift != 0 && old_pgshift != PAGE_SHIFT as CInt {
        let error = -E2BIG;
        if let Some(log) = log_fn {
            log(
                PROCESS_REMAP_RANGE_LOG_PGSHIFT,
                vm,
                range,
                start,
                end,
                off,
                old_pgshift,
                error,
            );
        }
        error
    } else {
        let error = visit(
            (*(*vm).address_space).page_table,
            start,
            end,
            (*range).pgshift,
            0,
            visit_step_fn,
            arg,
        );
        if error != 0 {
            if let Some(log) = log_fn {
                log(
                    PROCESS_REMAP_RANGE_LOG_VISIT_FAILED,
                    vm,
                    range,
                    start,
                    end,
                    off,
                    old_pgshift,
                    error,
                );
            }
        }
        error
    };

    let _ = process_memobj_unref_direct_result(memobj);
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);
    error
}
