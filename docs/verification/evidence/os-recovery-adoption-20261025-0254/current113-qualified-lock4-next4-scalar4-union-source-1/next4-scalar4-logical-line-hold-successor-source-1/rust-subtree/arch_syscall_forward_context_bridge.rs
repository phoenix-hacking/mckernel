// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_void;
use crate::abi::{CInt, CLong};

/// # Safety
/// Original valid kernel syscall context and selected forwarding preconditions;
/// this wrapper does not validate or retain the pointer or change its lifetime.
#[no_mangle]
pub unsafe extern "C" fn arch_syscall_forward_context_bridge(
    number: CInt, context: *mut c_void,
) -> CLong {
    // SAFETY: exact context bits delegated to the existing complete Rust forwarder.
    unsafe { super::syscall_generic_forwarding(number, context.cast()) }
}
