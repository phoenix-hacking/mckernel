#[no_mangle]
pub unsafe extern "C" fn pagealloc_track_alloc_result(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
    is_user: CInt,
    virt_addr: CULong,
    file: *mut i8,
    line: CInt,
    memdebug: *mut i8,
    track_initialized: CInt,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    runcount: CInt,
    base_alloc_fn: Option<MemPageallocBaseAllocFn>,
    meta_alloc_fn: Option<MemPageallocMetaAllocFn>,
    meta_free_fn: Option<MemPageallocMetaFreeFn>,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    spin_init_fn: Option<MemPageallocSpinInitFn>,
    log_fn: Option<MemPageallocTrackLogFn>,
) -> *mut c_void {
    let Some(base_alloc) = base_alloc_fn else {
        return null_mut();
    };

    let result = base_alloc(npages, p2align, flag, node, is_user, virt_addr);
    if memdebug.is_null() || track_initialized == 0 || result.is_null() {
        return result;
    }
    if file.is_null()
        || track_hash.is_null()
        || track_locks.is_null()
        || addr_hash.is_null()
        || addr_locks.is_null()
    {
        return result;
    }
    let (Some(meta_alloc), Some(meta_free), Some(lock), Some(unlock), Some(spin_init)) = (
        meta_alloc_fn,
        meta_free_fn,
        lock_fn,
        unlock_fn,
        spin_init_fn,
    ) else {
        return result;
    };

    let hash = pagealloc_track_hash(file, line);
    let track_lock = track_locks.add(hash as usize);
    let irq_flags = lock(track_lock as CULong);
    let mut entry = pagealloc_track_find_entry_result(file, line, track_hash);

    if entry.is_null() {
        entry = meta_alloc(size_of::<PageallocTrackEntry>() as CInt, IHK_MC_AP_NOWAIT)
            .cast::<PageallocTrackEntry>();
        if entry.is_null() {
            unlock(track_lock as CULong, irq_flags);
            pagealloc_track_log(
                log_fn,
                PAGEALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED,
                result,
                file,
                line,
                npages,
            );
            return result;
        }

        (*entry).line = line;
        pagealloc_track_entry_alloc_count(entry).store(1, Ordering::Relaxed);
        spin_init(pagealloc_entry_addr_list_lock(entry));
        init_list_head(&raw mut (*entry).addr_list);

        let file_len = strlen(file.cast_const()) as CInt;
        (*entry).file = meta_alloc(file_len.wrapping_add(1), IHK_MC_AP_NOWAIT).cast::<i8>();
        if (*entry).file.is_null() {
            pagealloc_track_log(
                log_fn,
                PAGEALLOC_TRACK_LOG_FILE_ALLOC_FAILED,
                result,
                file,
                line,
                npages,
            );
            meta_free(entry.cast::<c_void>());
            unlock(track_lock as CULong, irq_flags);
            return result;
        }

        strcpy((*entry).file, file.cast_const());
        init_list_head(&raw mut (*entry).hash);
        list_add_after(&raw mut (*entry).hash, track_hash.add(hash as usize));
        pagealloc_track_log(
            log_fn,
            PAGEALLOC_TRACK_LOG_ENTRY_ADDED,
            result,
            file,
            line,
            npages,
        );
    } else {
        pagealloc_track_entry_alloc_count(entry).fetch_add(1, Ordering::Relaxed);
    }
    unlock(track_lock as CULong, irq_flags);

    let addr_entry = meta_alloc(
        size_of::<PageallocTrackAddrEntry>() as CInt,
        IHK_MC_AP_NOWAIT,
    )
    .cast::<PageallocTrackAddrEntry>();
    if addr_entry.is_null() {
        pagealloc_track_log(
            log_fn,
            PAGEALLOC_TRACK_LOG_ADDR_ALLOC_FAILED,
            result,
            file,
            line,
            npages,
        );
        return result;
    }

    (*addr_entry).addr = result;
    (*addr_entry).runcount = runcount;
    (*addr_entry).entry = entry;
    (*addr_entry).npages = npages;
    init_list_head(&raw mut (*addr_entry).list);
    init_list_head(&raw mut (*addr_entry).hash);

    let irq_flags = lock(pagealloc_entry_addr_list_lock(entry));
    list_add_after(&raw mut (*addr_entry).list, &raw mut (*entry).addr_list);
    unlock(pagealloc_entry_addr_list_lock(entry), irq_flags);

    pagealloc_rehash_addr_entry(addr_entry, addr_hash, addr_locks, lock, unlock);
    pagealloc_track_log(
        log_fn,
        PAGEALLOC_TRACK_LOG_ADDR_ADDED,
        result,
        file,
        line,
        npages,
    );

    result
}
