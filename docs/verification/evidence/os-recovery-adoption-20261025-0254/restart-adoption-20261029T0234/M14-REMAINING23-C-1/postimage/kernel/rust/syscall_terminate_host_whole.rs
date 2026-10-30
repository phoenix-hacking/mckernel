use super::*;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

unsafe extern "C" fn f03_terminate_host_refcount_set_v2(value: *mut c_void, count: CInt) {
    // SAFETY: Exact initialized IhkAtomic field chosen by the unchanged helper.
    // Keep its existing detached-cleanup set-to-one operation; this is not an
    // authority to manufacture a reference or to admit arbitrary detached nodes.
    unsafe { crate::atomic_helpers::ihk_atomic_set(value.cast(), count) };
}

unsafe extern "C" fn f03_terminate_host_release_thread_v2(thread: *mut c_void) {
    // SAFETY: The original detached cleanup caller grants this genuine release.
    unsafe { crate::process_helpers::release_thread(thread.cast()) };
}

unsafe extern "C" fn f03_terminate_host_release_process_v2(proc: *mut c_void) {
    // SAFETY: Saved exact Process pointer/owned release, after thread release.
    unsafe { crate::process_helpers::release_process(proc.cast()) };
}

/// Execute the complete existing lookup/nohost/kill-or-detached-release transaction.
///
/// # Safety
/// Current CPU/thread state is live. Actual find_process/process_unlock own the
/// paired hash reader lock and same writable MCS IRQ-save node; they do not mint
/// a Process reference. A supplied detached_thread must carry the ORIGINAL caller's
/// exceptional detached Thread/Process cleanup authority, including its existing
/// refcount reset/release protocol. This entry cannot create that authority from
/// a pointer or numeric count. Actual do_kill remains a genuine C endpoint with
/// its existing signal/relationship/lifetime contract, not a completed Rust port.
#[no_mangle]
pub unsafe extern "C" fn terminate_host(pid: CInt, detached_thread: *mut Thread) {
    let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    // SAFETY: Same current-thread lookup and node preparation as the complete C entry.
    let local = unsafe { crate::cls::get_this_cpu_local_var() };
    let current = unsafe { addr_of!((*local).current).read() };
    // SAFETY: Reuse the ACTUAL complete algorithm unchanged, including missing
    // process handling, nohost1 no-op, nohost-before-unlock, and ignored kill result.
    // Genuine lookup helpers fill/release the same IRQ-save node exactly once.
    let _ = unsafe {
        terminate_host_body_result(
            pid, detached_thread.cast(), current.cast(), node.as_mut_ptr().cast(),
            offset_of!(Process, nohost), offset_of!(Thread, proc),
            offset_of!(Thread, refcount), Some(syscall_find_process_bridge),
            Some(syscall_process_unlock_bridge), Some(f03_terminate_host_refcount_set_v2),
            Some(f03_terminate_host_release_thread_v2),
            Some(f03_terminate_host_release_process_v2), Some(syscall_do_kill_thread_bridge),
        )
    };
}

const _: unsafe extern "C" fn(CInt, *mut Thread) = terminate_host;
