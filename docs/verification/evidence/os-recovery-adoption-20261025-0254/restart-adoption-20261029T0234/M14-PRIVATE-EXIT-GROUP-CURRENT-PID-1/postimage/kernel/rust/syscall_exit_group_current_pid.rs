//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Existing raw current-process PID callback; private source-only successor.

use super::{current_thread_ptr, CInt};
use crate::abi::{Process, Thread};
use core::mem::{offset_of, size_of};

// Reuse the exact existing abi.rs/process_helpers.rs assertions, not a new layout.
const _: () = {
    assert!(size_of::<CInt>() == 4);
    assert!(offset_of!(Thread, proc) == 4304);
    assert!(offset_of!(Process, pid) == 456);
};

/// Same no-argument C int callback as the original raw C getter.
///
/// # Safety
/// Existing syscall-entry invariant: the local current thread and its proc are
/// live, non-null, correctly aligned and readable for this callback. Reuse the
/// existing accessor and scheduler/preemption/lifetime context. This getter does
/// not schedule, acquire ownership, add null handling, or extend either lifetime.
#[no_mangle]
pub(super) unsafe extern "C" fn exit_group_current_pid_bridge() -> CInt {
    // SAFETY: the unchanged caller's raw current/proc invariant above is exactly
    // the original C getter's precondition. No Rust reference is constructed.
    unsafe { (*(*current_thread_ptr()).proc).pid }
}
