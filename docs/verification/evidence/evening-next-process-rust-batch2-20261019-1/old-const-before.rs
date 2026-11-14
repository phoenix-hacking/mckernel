const _: () = {
    assert!(offset_of!(Thread, hash_list) == 0);
    assert!(offset_of!(Thread, tid) == 20);
    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);
    assert!(offset_of!(ResourceSet, thread_hash) == 32);
    assert!(offset_of!(ThreadHash, lock) == 1216);
    assert!(size_of::<ThreadHash>() == 5888);
    assert!(PROCESS_HASH_SIZE == 73);
};
