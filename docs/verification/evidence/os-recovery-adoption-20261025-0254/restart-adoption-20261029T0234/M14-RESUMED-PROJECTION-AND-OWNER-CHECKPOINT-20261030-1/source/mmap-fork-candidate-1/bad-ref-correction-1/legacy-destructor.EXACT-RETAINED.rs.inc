pub unsafe extern "C" fn f03_clone_destroy_legacy_thread_v1(
    new:*mut Thread,proc:*mut Process,clone_flags:CInt,
    file:*const i8,origin_line:CInt,
) {
    if clone_flags & CLONE_VM==0 {
        crate::atomic_helpers::ihk_atomic_set(addr_of_mut!((*(*new).proc).refcount).cast(),1);
        crate::mem_helpers::kfree_tracked((*proc).saved_cmdline,file.cast_mut(),origin_line);
        (*proc).saved_cmdline=null_mut();
    }
    crate::atomic_helpers::ihk_atomic_set(addr_of_mut!((*new).refcount).cast(),1);
    crate::process_helpers::release_thread(new);
}
