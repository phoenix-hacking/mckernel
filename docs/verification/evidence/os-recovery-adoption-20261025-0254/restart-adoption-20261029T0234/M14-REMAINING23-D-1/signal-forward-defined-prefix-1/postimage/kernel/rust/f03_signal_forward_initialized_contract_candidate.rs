//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Prefixes for an already initialized context; no original callback is selected.
use core::ptr::addr_of;
use crate::abi::{CInt, CLong, CULong, KSigAction, X86UserContext};
use crate::x86_cpu_helpers::{ihk_mc_syscall_set_arg0, ihk_mc_syscall_set_arg1, ihk_mc_syscall_set_arg2};

/// Apply the existing rt_sigprocmask forwarding prefix to supplied context.
///
/// # Safety
/// `ctx` must be an aligned live fully initialized context, writable and retained
/// through the synchronous generic forwarder. Its untouched argument slots and
/// all downstream endpoint semantics require an independently approved contract.
pub(super) unsafe fn forward_mask_on_initialized_context(ctx: *mut X86UserContext, mask: CULong) -> CLong {
    unsafe { ihk_mc_syscall_set_arg0(ctx, mask) };
    unsafe { super::syscall_generic_forwarding(14, ctx) }
}

/// Apply the existing ordered sigaction prefix to supplied context.
///
/// # Safety
/// `ctx` meets the same initialized-context contract above. `action` must remain
/// valid, aligned and initialized for the original handler and flags reads. The
/// caller retains original update ordering and process/endpoint synchronization.
pub(super) unsafe fn forward_action_on_initialized_context(ctx: *mut X86UserContext, sig: CInt, action: *const KSigAction) -> CLong {
    unsafe { ihk_mc_syscall_set_arg0(ctx, sig as CULong) };
    let handler = unsafe { addr_of!((*action).sa.sa_handler).read() } as CULong;
    unsafe { ihk_mc_syscall_set_arg1(ctx, handler) };
    let flags = unsafe { addr_of!((*action).sa.sa_flags).read() };
    unsafe { ihk_mc_syscall_set_arg2(ctx, flags) };
    unsafe { super::syscall_generic_forwarding(13, ctx) }
}
