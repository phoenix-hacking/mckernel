// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Paired opt-in source candidate; final image/provider/native proof remains open.
use core::ffi::c_void;

use crate::abi::{CInt, CLong, CULong, SigInfo, Thread};

unsafe extern "C" {
    // These are the genuine kernel/include/process.h provider signatures.
    fn do_kill(thread: *mut Thread, pid: CInt, tid: CInt, sig: CInt,
               info: *mut SigInfo, ptracecont: CInt) -> CULong;
    fn sched_wakeup_thread(thread: *mut Thread, valid_states: CInt) -> CInt;
}

/// # Safety
/// Preserve the original caller's referenced thread, signal-info lifetime,
/// locking and signal-provider contract. This synchronous bridge retains no
/// pointer and does not obtain or release any reference of its own.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_do_kill_bridge(
    current_thread: *mut c_void, pid: CInt, tid: CInt, sig: CInt,
    info: *const c_void, ptracecont: CInt,
) -> CLong {
    // The provider returns unsigned long; the existing ptrace callback returns
    // long. Preserve the x86_64 bit pattern, including encoded negative errors.
    unsafe {
        do_kill(current_thread.cast(), pid, tid, sig,
                info.cast_mut().cast(), ptracecont) as CLong
    }
}

/// # Safety
/// The thread is live under the original scheduler/wakeup caller contract.
/// The callback deliberately discards the provider's int result, like C.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_wakeup_bridge(
    thread: *mut c_void, valid_states: CInt,
) {
    unsafe { let _ = sched_wakeup_thread(thread.cast(), valid_states); }
}
