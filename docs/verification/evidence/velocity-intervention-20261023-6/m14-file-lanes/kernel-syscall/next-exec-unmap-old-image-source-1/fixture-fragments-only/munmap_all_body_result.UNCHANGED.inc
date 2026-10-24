#[no_mangle]
pub unsafe extern "C" fn munmap_all_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    region: *mut c_void,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    region_map_start_offset: SizeT,
    region_map_end_offset: SizeT,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    next_fn: Option<MsyncNextRangeFn>,
    do_munmap_fn: Option<MunmapDoFn>,
    free_ranges_fn: Option<MunmapAllFreeRangesFn>,
    log_fn: Option<MunmapAllLogFn>,
) {
    if let Some(lock) = lock_fn {
        lock(range_lock);
    }

    let mut next = if let Some(lookup) = lookup_fn {
        lookup(vm, 0, CULong::MAX)
    } else {
        core::ptr::null_mut()
    };

    while !next.is_null() {
        let range = next;
        next = if let Some(next_range) = next_fn {
            next_range(vm, range)
        } else {
            core::ptr::null_mut()
        };

        let start = *field_ptr::<CULong>(range.cast::<u8>(), range_start_offset);
        let end = *field_ptr::<CULong>(range.cast::<u8>(), range_end_offset);
        let size = end.wrapping_sub(start) as SizeT;
        let error = if let Some(do_munmap) = do_munmap_fn {
            do_munmap(start as *mut c_void, size, 1)
        } else {
            -EINVAL
        };
        if error != 0 {
            if let Some(log) = log_fn {
                log(start, size, error);
            }
        }
    }

    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }

    if let Some(free_ranges) = free_ranges_fn {
        free_ranges(vm);
    }

    let map_start = *field_ptr::<CULong>(region.cast::<u8>(), region_map_start_offset);
    *field_ptr::<CULong>(region.cast::<u8>(), region_map_end_offset) = map_start;
}
