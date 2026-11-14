// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing private adapter, with original provider ownership retained.
use core::ffi::c_void;

/// # Safety
/// Same lock and node as the paired successful lock, still live/exclusive for
/// node irqsave; actual provider restores the saved original interrupt state.
#[no_mangle]
pub unsafe extern "C" fn arch_clone_reader_unlock_bridge(lock: *mut c_void, node: *mut c_void) {
    // SAFETY: exact provider with no allocation, retry or lock/node lifetime change.
    unsafe { crate::lock_helpers::__mcs_rwlock_reader_unlock(lock.cast(), node.cast()) };
}
