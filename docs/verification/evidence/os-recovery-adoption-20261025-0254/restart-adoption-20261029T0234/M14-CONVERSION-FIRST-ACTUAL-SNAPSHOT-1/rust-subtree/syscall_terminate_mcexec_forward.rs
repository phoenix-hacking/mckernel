// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use crate::abi::{CInt, CLong, SyscallRequest};

/// Forward the existing request callback without inspecting its raw pointer.
///
/// # Safety
/// The request and cpu must satisfy the original caller and existing do_syscall
/// provider contracts. This function neither creates nor retains the request.
#[no_mangle]
pub unsafe extern "C" fn terminate_mcexec_do_syscall_bridge(request: *mut SyscallRequest, cpu: CInt) -> CLong {
    // SAFETY: The same pointer and CPU are passed to the original provider;
    // its exact return value is returned to the original caller.
    unsafe { super::do_syscall(request, cpu) }
}
