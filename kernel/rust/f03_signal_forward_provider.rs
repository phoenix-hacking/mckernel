//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Genuine narrow signal-payload and opaque-context providers for the ordinary profile.
use core::{ffi::c_void, mem::{align_of, offset_of, size_of, MaybeUninit}, ptr::addr_of};
use crate::abi::{CInt, CLong, CULong, KSigAction, SigAction, X86UserContext};

#[cfg(any(not(target_arch = "x86_64"), not(native_linux_irq_work_v6_12),
    not(enable_profile), not(enable_perf), not(enable_rusage), enable_tofu,
    enable_fugaku_hacks, f03_forward_adapters_candidate,
    f03_signal_forward_defined_candidate))]
compile_error!("signal forwarding providers require the paired ordinary profile");

/// Forward the original opaque context once, without changing or retaining it.
///
/// # Safety
/// The caller retains ownership of the original live x86 context for the full
/// synchronous offload. No reference is formed here. The selected genuine Rust
/// forwarder keeps its existing null handling, argument reads, request, CPU,
/// diagnostics and offload/lifetime behavior, including its signed long result.
#[no_mangle]
pub unsafe extern "C" fn syscall_forward_context_bridge(
    number: CInt, context: *mut c_void,
) -> CLong {
    unsafe {
        crate::syscall_policy::syscall_generic_forwarding(
            number, context.cast::<X86UserContext>(),
        )
    }
}

/// Forward the original signal-mask payload from a fully zeroed stack context.
///
/// # Safety
/// The original current-thread/CPU and synchronous endpoint contract applies.
/// All context fields are zero-valid integer fields, matching C `{ 0 }` before
/// the genuine volatile setter. Storage remains live through forwarding; no
/// reference, allocation, lock, signal operation or pointer is retained here.
#[no_mangle]
pub unsafe extern "C" fn syscall_forward_rt_sigprocmask_bridge(mask: CULong) -> CLong {
    let mut storage = MaybeUninit::<X86UserContext>::zeroed();
    let context = storage.as_mut_ptr();
    unsafe {
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg0(context, mask);
        crate::syscall_policy::syscall_generic_forwarding(14, context)
    }
}

/// Forward the original action's signal, handler bits and flags in C order.
///
/// # Safety
/// `action` is the original aligned initialized kernel action borrowed by the
/// caller. The caller finishes its original locked action copies and IRQ restore
/// before invoking this provider, and keeps the action live through return.
/// Handler and flags are read separately after their preceding setter, exactly
/// as in C; handler is an address value and is never called or dereferenced.
/// No pointer is stored, action mutated, lock taken or ownership transferred.
#[no_mangle]
pub unsafe extern "C" fn syscall_forward_sigaction_update_bridge(
    signal: CInt, action: *const c_void,
) -> CLong {
    let mut storage = MaybeUninit::<X86UserContext>::zeroed();
    let context = storage.as_mut_ptr();
    let action = action.cast::<KSigAction>();
    unsafe {
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg0(context, signal as CULong);
        let handler = addr_of!((*action).sa.sa_handler).read() as CULong;
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg1(context, handler);
        let flags = addr_of!((*action).sa.sa_flags).read();
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg2(context, flags);
        crate::syscall_policy::syscall_generic_forwarding(13, context)
    }
}

// Paired with the actual C declarations and selected architecture headers.
const _: unsafe extern "C" fn(CInt, *mut c_void) -> CLong = syscall_forward_context_bridge;
const _: unsafe extern "C" fn(CULong) -> CLong = syscall_forward_rt_sigprocmask_bridge;
const _: unsafe extern "C" fn(CInt, *const c_void) -> CLong = syscall_forward_sigaction_update_bridge;
const _: () = assert!(size_of::<CInt>() == 4 && align_of::<CInt>() == 4
    && size_of::<CLong>() == 8 && size_of::<CULong>() == 8
    && size_of::<*const c_void>() == 8);
const _: () = assert!(size_of::<X86UserContext>() == 224 && align_of::<X86UserContext>() == 8
    && offset_of!(X86UserContext, gpr) == 56);
const _: () = assert!(size_of::<KSigAction>() == 32 && align_of::<KSigAction>() == 8
    && offset_of!(KSigAction, sa) == 0 && offset_of!(SigAction, sa_handler) == 0
    && offset_of!(SigAction, sa_flags) == 8);
