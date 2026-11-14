// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use crate::abi::{CInt, CLong, SigInfo};
use core::ffi::c_void;

/// Forward the original callback to the existing do_kill provider.
///
/// # Safety
/// Caller retains the current thread and, when non-null, info for the duration
/// of the existing provider call, following the original C callback contract.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_do_kill_bridge(
    current_thread: *mut c_void, pid: CInt, tid: CInt, sig: CInt,
    info: *const c_void, ptracecont: CInt,
) -> CLong {
    // SAFETY: Existing adapter uses the original unsigned C provider and
    // bit-preserving long conversion; raw pointers and arguments are unchanged.
    unsafe { super::f06_ptrace_report_signal_kill(
        current_thread, pid, tid, sig, info.cast::<SigInfo>(), ptracecont,
    ) }
}
