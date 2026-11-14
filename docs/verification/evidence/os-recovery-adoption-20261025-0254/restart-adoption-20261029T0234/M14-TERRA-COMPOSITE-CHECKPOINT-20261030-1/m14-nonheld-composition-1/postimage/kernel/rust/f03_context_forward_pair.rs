//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Context callbacks delegate to the existing Rust generic forwarder.
use core::ffi::c_void;
use crate::abi::{CInt, CLong};

type ForwardContext = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;

/// Forward the syscall number and original borrowed user context.
///
/// # Safety
/// The context is the live x86 user context required by the existing forwarder;
/// the caller retains it for the full synchronous call and follows its existing
/// request and endpoint contracts. The pointer is neither retained nor inspected here.
#[no_mangle]
pub unsafe extern "C" fn syscall_forward_context_bridge(number: CInt, context: *mut c_void) -> CLong {
    // SAFETY: Preserve the original context address and callee preconditions.
    unsafe { super::syscall_generic_forwarding(number, context.cast()) }
}

/// Public policy callback for the same existing forwarding operation.
///
/// # Safety
/// Same borrowed context, lifetime and forwarding preconditions as the private
/// callback; no request, endpoint, error or null policy is added by this wrapper.
#[no_mangle]
pub unsafe extern "C" fn syscall_policy_forward_context_bridge(number: CInt, context: *mut c_void) -> CLong {
    // SAFETY: Preserve the original context address and callee preconditions.
    unsafe { super::syscall_generic_forwarding(number, context.cast()) }
}

const _: ForwardContext = syscall_forward_context_bridge;
const _: ForwardContext = syscall_policy_forward_context_bridge;
