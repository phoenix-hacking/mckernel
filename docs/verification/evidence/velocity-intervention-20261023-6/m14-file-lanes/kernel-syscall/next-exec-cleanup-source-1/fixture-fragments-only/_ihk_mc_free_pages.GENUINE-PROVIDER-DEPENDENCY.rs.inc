#[no_mangle]
pub unsafe extern "C" fn _ihk_mc_free_pages(
    ptr: *mut c_void,
    npages: CInt,
    is_user: CInt,
    file: *mut i8,
    line: CInt,
) {
    let _ = pagealloc_track_free_result(
        ptr,
        npages,
        is_user,
        file,
        line,
        MEMDEBUG,
        PAGEALLOC_TRACK_INITIALIZED,
        pagealloc_track_hash_ptr(),
        pagealloc_track_locks_ptr(),
        pagealloc_addr_hash_ptr(),
        pagealloc_addr_locks_ptr(),
        Some(mem_pagealloc_track_base_free_bridge),
        Some(mem_pagealloc_track_meta_alloc_bridge),
        Some(mem_pagealloc_track_meta_free_bridge),
        Some(mem_pagealloc_track_lock_bridge),
        Some(mem_pagealloc_track_unlock_bridge),
        Some(mem_pagealloc_track_noirq_lock_bridge),
        Some(mem_pagealloc_track_noirq_unlock_bridge),
        Some(mem_pagealloc_invalid_free_bridge),
        Some(mem_pagealloc_invalid_size_bridge),
        Some(mem_pagealloc_track_log_bridge),
    );
}
