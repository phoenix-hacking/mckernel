//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Genuine narrow policy context adapter over the already selected Rust forwarder.
use core::ffi::c_void;
use crate::abi::{CInt, CLong, X86UserContext};

#[cfg(any(not(target_arch = "x86_64"), not(native_linux_irq_work_v6_12),
    not(enable_profile), not(enable_perf), not(enable_rusage), enable_tofu,
    enable_fugaku_hacks, f03_forward_adapters_candidate))]
compile_error!("policy context bridge requires its paired qualified ordinary profile");

/// Preserve the actual CInt/opaque-context/CLong ABI and one forwarding call.
///
/// # Safety
/// The original caller owns the live x86_64 syscall context through the complete
/// synchronous operation. The cast preserves its address without forming a Rust
/// reference, modifying registers, validating new conditions or retaining it.
/// The unchanged genuine forwarder still owns its existing null handling, all
/// six argument loads, current-CPU selection, request construction, diagnostics
/// and call to the selected do_syscall implementation. No held request is run.
#[no_mangle]
pub unsafe extern "C" fn syscall_policy_forward_context_bridge(
    number: CInt, context: *mut c_void,
) -> CLong {
    unsafe {
        crate::syscall_policy::syscall_generic_forwarding(
            number, context.cast::<X86UserContext>(),
        )
    }
}

const _: unsafe extern "C" fn(CInt, *mut c_void) -> CLong =
    syscall_policy_forward_context_bridge;
