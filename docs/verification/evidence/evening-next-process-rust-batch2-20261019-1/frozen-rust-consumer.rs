#[no_mangle]
pub unsafe extern "C" fn release_process(proc: *mut Process) {
    let _ = process_release_process_body_result(
        proc.cast(),
        offset_of!(Process, refcount) as CULong,
        offset_of!(Process, tids) as CULong,
        offset_of!(Process, main_thread) as CULong,
        offset_of!(Process, mckfd) as CULong,
        offset_of!(Process, mckfd_lock) as CULong,
        offset_of!(Mckfd, next) as CULong,
        None,
        Some(process_current_resource_set_bridge),
        Some(process_release_hash_detach_bridge),
        Some(process_release_sibling_detach_bridge),
        Some(process_release_profile_bridge),
        Some(process_free_thread_pages_bridge),
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_mckfd_free_bridge),
        Some(process_optional_free_bridge),
        Some(process_release_final_cleanup_bridge),
    );
}
