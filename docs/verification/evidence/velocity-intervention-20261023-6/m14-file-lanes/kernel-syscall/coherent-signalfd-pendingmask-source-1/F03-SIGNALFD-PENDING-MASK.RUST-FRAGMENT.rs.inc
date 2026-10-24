// M14-F03 next source slice: exact pending-mask aggregation under the two
// existing writer locks. The caller retains current Thread/SigCommon/list nodes;
// this body does not remove, consume, free or retain any pending signal node.
#[inline]
unsafe fn syscall_pending_mask_list_locked_f03(head: *mut AbiListHead) -> CULong {
    let mut mask: CULong = 0;
    let mut entry = (*head).next;
    while entry != head {
        let pending = entry
            .cast::<u8>()
            .wrapping_sub(offset_of!(crate::abi::SigPending, list))
            .cast::<crate::abi::SigPending>();
        mask |= (*pending).sigmask.val[0];
        entry = (*pending).list.next;
    }
    mask
}

#[no_mangle]
pub unsafe extern "C" fn syscall_pending_mask_bridge(threadp: *mut c_void) -> CULong {
    let thread = threadp.cast::<Thread>();
    let common = (*thread).sigcommon.cast::<SigCommon>();
    let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let common_lock = addr_of_mut!((*common).lock).cast();
    let common_head = addr_of_mut!((*common).sigpending);
    crate::lock_helpers::__mcs_rwlock_writer_lock(common_lock, node.as_mut_ptr());
    let mut mask = syscall_pending_mask_list_locked_f03(common_head);
    crate::lock_helpers::__mcs_rwlock_writer_unlock(common_lock, node.as_mut_ptr());

    let thread_lock = addr_of_mut!((*thread).sigpendinglock).cast();
    let thread_head = addr_of_mut!((*thread).sigpending);
    crate::lock_helpers::__mcs_rwlock_writer_lock(thread_lock, node.as_mut_ptr());
    mask |= syscall_pending_mask_list_locked_f03(thread_head);
    crate::lock_helpers::__mcs_rwlock_writer_unlock(thread_lock, node.as_mut_ptr());
    mask
}

// M14-F03: retire the selected signalfd host-FD request/admission callback.
// Supported x86 IHK_DMA_ALIGN is empty; SyscallRequest retains its repr(C)
// natural alignment. The synchronous do_syscall ownership contract is unchanged.
#[no_mangle]
pub unsafe extern "C" fn syscall_signalfd_create_bridge(
    syscall_nr: CInt,
    flags: CInt,
) -> CLong {
    let mut request = MaybeUninit::<SyscallRequest>::zeroed();
    let requestp = request.as_mut_ptr();
    (*requestp).number = syscall_nr as CULong;
    (*requestp).args[0] = 0;
    (*requestp).args[1] = flags as CULong;
    let cpu = ihk_mc_get_processor_id();
    do_syscall(requestp, cpu)
}
