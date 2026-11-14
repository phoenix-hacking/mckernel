// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Paired opt-in source candidate; matching image/native qualification remains open.
use core::ffi::c_void;
use core::mem::{offset_of, MaybeUninit};

use crate::abi::{CInt, CLong, Process, SigInfo, Thread};
use crate::lock_helpers::McsRwlockNodeIrqsave;

unsafe extern "C" {
    // These are existing selected Rust providers in syscall_policy.rs. Their
    // callbacks retain the original process lookup, IRQ state and release ABI.
    fn syscall_find_process_bridge(pid: CInt, lock: *mut c_void) -> *mut c_void;
    fn syscall_process_unlock_bridge(process: *mut c_void, lock: *mut c_void);
    fn f03_terminate_host_refcount_set_v1(refcount: *mut c_void, value: CInt);
    fn f03_wait_release_thread(thread: *mut c_void);
    fn f03_wait_release_process(process: *mut c_void);
    fn syscall_do_kill_thread_bridge(
        thread: *mut c_void, pid: CInt, tid: CInt, sig: CInt,
        info: *const SigInfo, ptracecont: CInt,
    ) -> CLong;
}

/// Preserve the original host-disconnect lookup, notification and cleanup path.
///
/// # Safety
/// The current CPU/thread, process lookup and optional detached thread satisfy
/// the original terminate_host contract. In particular, a detached thread's
/// process must survive its thread release. This entry grants no reference or
/// permission to reset a refcount or release the current stack. The existing
/// body captures the process before releasing the thread and performs no later
/// detached-thread access. Its long result remains ignored by this void ABI.
#[no_mangle]
pub unsafe extern "C" fn terminate_host(pid: CInt, detached_thread: *mut Thread) {
    let current = unsafe { (*crate::cls::get_this_cpu_local_var()).current };
    // find_process initializes this exact IRQ-save lock node before using it.
    // Keep it private, aligned, and live through the matching unlock callback.
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        let _ = crate::syscall_policy::terminate_host_body_result(
            pid, detached_thread.cast(), current.cast(), lock.as_mut_ptr().cast(),
            offset_of!(Process, nohost), offset_of!(Thread, proc),
            offset_of!(Thread, refcount),
            Some(syscall_find_process_bridge), Some(syscall_process_unlock_bridge),
            Some(f03_terminate_host_refcount_set_v1), Some(f03_wait_release_thread),
            Some(f03_wait_release_process), Some(syscall_do_kill_thread_bridge),
        );
    }
}
