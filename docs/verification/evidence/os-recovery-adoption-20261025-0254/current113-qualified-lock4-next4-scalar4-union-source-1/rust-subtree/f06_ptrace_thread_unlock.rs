// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing adapter; thread_unlock retains null/final-reference release ownership.
use crate::abi::{CULong, Thread};

/// # Safety
/// Nonzero address identifies exactly the held thread reference from lookup;
/// null handling and final release remain the real provider's responsibility.
#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_thread_unlock_bridge(thread_addr: CULong) {
    // SAFETY: unchanged raw address conversion and one release-provider call.
    unsafe { crate::process_helpers::thread_unlock(thread_addr as *mut Thread) };
}
