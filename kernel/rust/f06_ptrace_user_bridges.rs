// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact selected adapters; existing Rust ptrace providers retain all behavior/ownership.
use crate::abi::{CLong,CULong,Thread};

/// # Safety
/// Caller retains the existing ptrace provider's target lifetime/exclusion and
/// output-pointer contract. This adapter only casts the original LP64 thread
/// bits to the genuine nominal type, then forwards arguments/result unchanged.
/// No reference, validation, allocation, locking or ownership change is added.
#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_read_user_bridge(
    thread_addr:CULong,
    address:CLong,
    value:*mut CULong,
) -> CLong {
    // SAFETY: same raw target/output pointers and provider contract as original C.
    unsafe { crate::syscall_policy::ptrace_read_user(thread_addr as *mut Thread,address,value) }
}

/// # Safety
/// The unchanged Rust write provider owns target access, errors and exclusion.
/// Raw thread/value bits and signed offset/return retain the original C ABI;
/// the adapter neither dereferences nor retains the target pointer.
#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_write_user_bridge(
    thread_addr:CULong,
    address:CLong,
    value:CULong,
) -> CLong {
    // SAFETY: caller supplies the original target lifetime/provider obligations.
    unsafe { crate::syscall_policy::ptrace_write_user(thread_addr as *mut Thread,address,value) }
}
