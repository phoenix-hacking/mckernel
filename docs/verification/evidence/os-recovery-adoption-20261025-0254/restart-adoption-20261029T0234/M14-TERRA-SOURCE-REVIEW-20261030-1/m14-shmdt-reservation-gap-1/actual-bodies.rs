unsafe fn field_ptr<T>(base: *mut u8, offset: SizeT) -> *mut T {
    base.add(offset).cast::<T>()
}

unsafe fn memlock_range_ulong(range: *mut c_void, offset: SizeT) -> CULong {
    *field_ptr::<CULong>(range.cast::<u8>(), offset)
}

unsafe fn memlock_range_ptr(range: *mut c_void, offset: SizeT) -> *mut c_void {
    *field_ptr::<*mut c_void>(range.cast::<u8>(), offset)
}

unsafe fn shmdt_log(log_fn: Option<ShmdtLogFn>, event: CInt, addr: CULong, error: CInt) {
    if let Some(log) = log_fn {
        log(event, addr, error);
    }
}

pub unsafe extern "C" fn shmdt_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    shmaddr: CULong,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_memobj_offset: SizeT,
    memobj_flags_offset: SizeT,
    shmdt_ok_flag: CULong,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    do_munmap_fn: Option<MunmapDoFn>,
    log_fn: Option<ShmdtLogFn>,
) -> CInt {
    shmdt_log(log_fn, SHMDT_LOG_ENTER, shmaddr, 0);

    if let Some(lock) = lock_fn {
        lock(range_lock);
    }

    let mut error = -EINVAL;
    let mut invalid = true;

    if let Some(lookup) = lookup_fn {
        let range = lookup(vm, shmaddr, shmaddr.wrapping_add(1));
        if !range.is_null() {
            let start = memlock_range_ulong(range, range_start_offset);
            let end = memlock_range_ulong(range, range_end_offset);
            let memobj = memlock_range_ptr(range, range_memobj_offset);
            if start == shmaddr && !memobj.is_null() {
                let flags = *field_ptr::<u32>(memobj.cast::<u8>(), memobj_flags_offset) as CULong;
                if (flags & shmdt_ok_flag) != 0 {
                    invalid = false;
                    error = if let Some(do_munmap) = do_munmap_fn {
                        do_munmap(start as *mut c_void, end.wrapping_sub(start) as SizeT, 1)
                    } else {
                        -EINVAL
                    };
                }
            }
        }
    }

    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }

    if invalid {
        shmdt_log(log_fn, SHMDT_LOG_INVALID, shmaddr, -EINVAL);
    } else {
        shmdt_log(log_fn, SHMDT_LOG_EXIT, shmaddr, error);
    }

    error
}
