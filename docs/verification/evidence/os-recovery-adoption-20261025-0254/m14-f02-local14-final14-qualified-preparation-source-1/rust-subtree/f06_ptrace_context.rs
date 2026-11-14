// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing adapter; current-stack/allocation/VM ownership remains with provider.
use core::ffi::c_void;

use crate::abi::{Thread, X86UserContext};

unsafe extern "C" {
    #[link_name = "lookup_user_context"]
    fn f06_ptrace_lookup_context(thread: *mut Thread) -> *mut X86UserContext;
}

/// # Safety
/// Exact lookup_user_context thread/current-CPU lifetime and state contract.
/// Returned context is borrowed; no reference, allocation or ownership is added.
#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_lookup_user_context_bridge(
    thread: *mut c_void,
) -> *mut c_void {
    // SAFETY: unchanged CPU provider still owns context validation/materialization.
    unsafe { f06_ptrace_lookup_context(thread.cast()).cast() }
}
