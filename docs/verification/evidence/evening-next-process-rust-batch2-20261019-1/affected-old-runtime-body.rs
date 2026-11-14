#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_hash_detach_bridge(thread_arg: *mut c_void) {
    let thread = thread_arg.cast::<Thread>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        let entry = core::ptr::addr_of_mut!((*thread).hash_list);
        if process_list_is_linked_result(entry) != 0 {
            let resource_set = (*get_this_cpu_local_var()).resource_set;
            let hash = thread_hash((*thread).tid);
            let lock_addr = core::ptr::addr_of_mut!((*(*resource_set).thread_hash).lock)
                .cast::<crate::abi::McsRwlockLock>().add(hash as usize) as CULong;
            process_mcs_writer_lock_bridge(lock_addr, lock.as_mut_ptr().cast());
            process_list_detach_result(entry);
            let lock_addr = core::ptr::addr_of_mut!((*(*resource_set).thread_hash).lock)
                .cast::<crate::abi::McsRwlockLock>().add(hash as usize) as CULong;
            process_mcs_writer_unlock_bridge(lock_addr, lock.as_mut_ptr().cast());
        }
    }
}
