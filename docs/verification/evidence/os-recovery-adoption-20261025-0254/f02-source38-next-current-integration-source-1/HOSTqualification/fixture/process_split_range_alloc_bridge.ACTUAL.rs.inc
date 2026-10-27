    #[no_mangle]
    pub unsafe extern "C" fn process_split_range_alloc_bridge(
        size: CULong, flags: CULong,
    ) -> *mut VmRange {
        unsafe {
            crate::mem_helpers::kmalloc_tracked(
                size as CInt, flags, process_tracked_allocator_source_file.cast_mut(),
                process_split_range_alloc_source_line,
            ).cast()
        }
    }
