    unsafe extern "C" fn free_pages(addr: *mut c_void, pages: CULong) {
        unsafe { crate::mem_helpers::_ihk_mc_free_pages(addr, pages as CInt, 0,
            process_tracked_allocator_source_file.cast_mut(),
            process_free_range_pages_source_line); }
    }
