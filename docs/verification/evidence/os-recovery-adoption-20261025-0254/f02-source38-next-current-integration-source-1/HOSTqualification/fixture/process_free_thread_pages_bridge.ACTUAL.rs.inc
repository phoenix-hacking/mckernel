    #[no_mangle]
    pub unsafe extern "C" fn process_free_thread_pages_bridge(thread: *mut c_void) {
        // SAFETY: Original tracked free operation exactly once; the existing
        // backend owns null handling, tracking, locking and actual page release.
        unsafe {
            crate::mem_helpers::_ihk_mc_free_pages(
                thread, super::KERNEL_STACK_NR_PAGES as CInt, 0,
                process_tracked_allocator_source_file.cast_mut(),
                process_free_thread_pages_source_line,
            );
        }
    }
