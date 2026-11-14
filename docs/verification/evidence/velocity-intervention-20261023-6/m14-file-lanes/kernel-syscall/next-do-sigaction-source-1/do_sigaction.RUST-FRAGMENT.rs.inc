// M14-F03 source-only: remaining selected do_sigaction orchestration and
// public rt_sigaction callback. Existing Rust helper preserves validation,
// action copies, lock/unlock and forwarding order. C forwarding remains debt.
extern "C" {
    #[link_name = "syscall_forward_sigaction_update_bridge"]
    fn syscall_forward_sigaction_update_f03(sig: CInt, act: *const c_void) -> CLong;
}

unsafe extern "C" fn syscall_sigaction_writer_lock_f03(lock: *mut c_void, node: *mut c_void) {
    crate::lock_helpers::__mcs_rwlock_writer_lock(lock.cast(), node.cast());
}

unsafe extern "C" fn syscall_sigaction_writer_unlock_f03(lock: *mut c_void, node: *mut c_void) {
    crate::lock_helpers::__mcs_rwlock_writer_unlock(lock.cast(), node.cast());
}

#[no_mangle]
pub unsafe extern "C" fn do_sigaction(sig: CInt, act: *mut KSigAction, oact: *mut KSigAction) -> CInt {
    let thread = current_thread_ptr();
    let common = (*thread).sigcommon;
    let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    do_sigaction_body_result(
        sig, act, oact, common.cast::<c_void>(),
        offset_of!(SigCommon, action), size_of::<KSigAction>(),
        offset_of!(SigCommon, lock), node.as_mut_ptr().cast::<c_void>(),
        Some(syscall_sigaction_writer_lock_f03),
        Some(syscall_sigaction_writer_unlock_f03),
        Some(syscall_forward_sigaction_update_f03),
    )
}

#[no_mangle]
pub unsafe extern "C" fn syscall_do_sigaction_bridge(
    sig: CInt, act: *mut KSigAction, oact: *mut KSigAction,
) -> CInt {
    do_sigaction(sig, act, oact)
}
