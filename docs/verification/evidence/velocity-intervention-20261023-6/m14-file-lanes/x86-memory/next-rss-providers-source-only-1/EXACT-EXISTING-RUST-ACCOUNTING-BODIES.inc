pub unsafe extern "C" fn memory_stat_rss_sub(size: CULong, pgsize: CInt) {
    #[cfg(enable_rusage)]
    {
        let rusage_ptr = &raw mut RUSAGE;
        let slot = (*rusage_ptr)
            .memory_stat_rss
            .as_mut_ptr()
            .add(rusage_pgsize_to_pgtype(pgsize as SizeT) as usize);
        rusage_atomic_add_long(slot, (size as CLong).wrapping_neg());
    }

    #[cfg(not(enable_rusage))]
    {
        let _ = (size, pgsize);
    }
}

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
