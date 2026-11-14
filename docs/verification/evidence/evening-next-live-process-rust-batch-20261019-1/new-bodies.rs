
const _: () = {
    assert!(offset_of!(Process, hash_list) == 0);
    assert!(offset_of!(Process, parent) == 272);
    assert!(offset_of!(Process, children_lock) == 320);
    assert!(offset_of!(Process, siblings_list) == 384);
    assert!(offset_of!(Process, pid) == 456);
    assert!(offset_of!(ResourceSet, process_hash) == 24);
    assert!(offset_of!(ProcessHash, lock) == 1216);
    assert!(size_of::<McsRwlockLock>() == 64);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(PROCESS_HASH_SIZE == 73);
};

/// Detach this final-release process from its resource-set hash under its bucket
/// writer lock. Both arguments and the selected hash/bucket remain live; pid is
/// nonnegative, and the caller excludes changes to this membership check until
/// lock acquisition. The existing list helper poisons the detached entry, which
/// must not be passed again. The cached hash and lock node match the C lifetime.
#[no_mangle]
pub unsafe extern "C" fn process_release_hash_detach_bridge(
    resource_set_arg: *mut c_void, proc_arg: *mut c_void,
) {
    let resource_set = resource_set_arg.cast::<ResourceSet>();
    let proc = proc_arg.cast::<Process>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        let entry = core::ptr::addr_of_mut!((*proc).hash_list);
        if process_list_is_linked_result(entry) != 0 {
            let phash = (*resource_set).process_hash;
            let hash = process_hash((*proc).pid);
            let lock_addr = core::ptr::addr_of_mut!((*phash).lock)
                .cast::<McsRwlockLock>().add(hash as usize) as CULong;
            process_mcs_writer_lock_bridge(lock_addr, lock.as_mut_ptr().cast());
            process_list_detach_result(entry);
            process_mcs_writer_unlock_bridge(lock_addr, lock.as_mut_ptr().cast());
        }
    }
}

/// Detach the final-release process from its parent's child list under the
/// existing parent children writer lock. Process, cached parent, list neighbors
/// and lock storage remain live for both synchronous callbacks; the caller owns
/// this one-time release and supplies initialized list membership. No reference
/// is acquired or freed here, and the parent's lifetime remains the caller's.
#[no_mangle]
pub unsafe extern "C" fn process_release_sibling_detach_bridge(proc_arg: *mut c_void) {
    let proc = proc_arg.cast::<Process>();
    let parent = unsafe { (*proc).parent };
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        let lock_addr = core::ptr::addr_of_mut!((*parent).children_lock) as CULong;
        process_mcs_writer_lock_bridge(lock_addr, lock.as_mut_ptr().cast());
        process_list_detach_result(core::ptr::addr_of_mut!((*proc).siblings_list));
        process_mcs_writer_unlock_bridge(lock_addr, lock.as_mut_ptr().cast());
    }
}
