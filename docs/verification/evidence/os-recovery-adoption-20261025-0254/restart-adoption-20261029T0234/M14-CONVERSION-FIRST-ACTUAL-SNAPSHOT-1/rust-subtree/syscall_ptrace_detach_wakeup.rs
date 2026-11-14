// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::{c_int, c_void};

/// Forward the callback to the qualified existing scheduler provider.
///
/// # Safety
/// The thread and its lifetime must meet the original callback and scheduler
/// provider contracts; this callback does not acquire or release ownership.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_wakeup_bridge(thread: *mut c_void, valid_states: c_int) {
    // SAFETY: The caller supplies the same live thread and states as the C
    // callback. The original callback also discards the scheduler result.
    let _ = unsafe { crate::sched_helpers::sched_wakeup_thread(thread.cast(), valid_states) };
}
