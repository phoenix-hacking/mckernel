    #[no_mangle]
    pub unsafe extern "C" fn process_create_thread_alloc_pages_bridge(
        npages: CInt, flags: CULong,
    ) -> *mut c_void {
        // SAFETY: Exact original x86 PAGE_P2ALIGN=0/IHK_MC_PG_KERNEL=0,
        // node=-1/virtual-address=-1 conversion and tracked source identity.
        // The genuine-header fixture binds the two architecture constants.
        unsafe {
            crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
                npages, 0, flags, -1, 0, CULong::MAX,
                process_tracked_allocator_source_file.cast_mut(),
                process_create_thread_alloc_pages_source_line,
            )
        }
    }
