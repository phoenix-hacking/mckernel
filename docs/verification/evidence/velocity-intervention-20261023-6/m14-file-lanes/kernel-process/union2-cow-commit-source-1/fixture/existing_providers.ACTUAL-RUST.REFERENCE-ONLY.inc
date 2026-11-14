#[no_mangle]
pub unsafe extern "C" fn rusage_memory_stat_add(
    range: *mut VmRange,
    phys: CULong,
    size: CULong,
    pgsize: CInt,
) -> CInt {
    #[cfg(enable_rusage)]
    {
        rusage_memory_stat_add_body(
            range,
            phys,
            size,
            pgsize,
            core::ptr::null_mut(),
            true,
            MF_DEV_FILE | MF_REG_FILE | MF_HUGETLBFS,
            RUSAGE_MEMORY_STAT_ADD_NAME.as_ptr().cast(),
        )
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (range, phys, size, pgsize);
        0
    }
}
#[no_mangle]
pub unsafe extern "C" fn rusage_memory_stat_sub(memobj: *mut Memobj, size: CULong, pgsize: CInt) {
    #[cfg(enable_rusage)]
    {
        if ((*memobj).flags & (MF_SHM as u32)) != 0 {
            memory_stat_rss_sub(size, pgsize);
        } else {
            rusage_memory_stat_mapped_file_sub(size, pgsize);
        }
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (memobj, size, pgsize);
    }
}
#[no_mangle]
pub unsafe extern "C" fn page_unmap(page: *mut Page) -> CInt {
    page_unmap_body_result(
        page,
        core::ptr::addr_of!(page_hash_locks) as usize,
        page_unmap_hash_shift,
        page_unmap_hash_mask,
        page_unmap_lock_stride,
        Some(page_hash_lock_bridge),
        Some(page_hash_unlock_bridge),
        Some(page_unmap_orchestrate_result),
        Some(page_unmap_log_bridge),
    )
}
