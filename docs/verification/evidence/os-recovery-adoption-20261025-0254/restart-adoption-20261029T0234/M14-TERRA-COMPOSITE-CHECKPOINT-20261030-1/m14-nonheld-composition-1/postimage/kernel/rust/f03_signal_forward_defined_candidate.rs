//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Signal-forwarding six-slot wire contract; selector is default OFF.
use core::{ffi::c_void, mem::MaybeUninit, ptr::{addr_of, addr_of_mut}};
use crate::abi::{CInt, CLong, CULong, KSigAction, X86UserContext};

/// Forward the existing custom signal-mask payload with approved unused zeroes.
///
/// # Safety
/// Original current-thread, endpoint and synchronous transport contracts apply.
/// Only the six argument fields are initialized; no whole-context reference is
/// valid, and the context remains live until generic forwarding completes.
#[no_mangle]
pub unsafe extern "C" fn syscall_forward_rt_sigprocmask_bridge(sigmask: CULong) -> CLong {
    let mut storage = MaybeUninit::<X86UserContext>::uninit();
    let ctx = storage.as_mut_ptr();
    // SAFETY: Each pointer addresses the naturally aligned live raw field. The
    // first volatile write exactly retains original setter0; remaining fields
    // implement the explicitly approved transmitted zero slots.
    unsafe {
        addr_of_mut!((*ctx).gpr.rdi).write_volatile(sigmask);
        addr_of_mut!((*ctx).gpr.rsi).write(0);
        addr_of_mut!((*ctx).gpr.rdx).write(0);
        addr_of_mut!((*ctx).gpr.r10).write(0);
        addr_of_mut!((*ctx).gpr.r8).write(0);
        addr_of_mut!((*ctx).gpr.r9).write(0);
        super::syscall_generic_forwarding(14, ctx)
    }
}

/// Forward original ordered action fields with approved unused zeroes.
///
/// # Safety
/// The action points to the original live aligned initialized action for the
/// original handler/flags reads; caller retains validation, update ordering and
/// endpoint/lifetime contracts. No whole-context reference or zero is formed.
#[no_mangle]
pub unsafe extern "C" fn syscall_forward_sigaction_update_bridge(sig: CInt, action: *const c_void) -> CLong {
    let mut storage = MaybeUninit::<X86UserContext>::uninit();
    let ctx = storage.as_mut_ptr();
    let action = action.cast::<KSigAction>();
    // SAFETY: Match original volatile setter order, including reading handler
    // after arg0 and flags after arg1. Signed sig converts modulo 2^64, as C.
    unsafe {
        addr_of_mut!((*ctx).gpr.rdi).write_volatile(sig as CULong);
        let handler = addr_of!((*action).sa.sa_handler).read() as CULong;
        addr_of_mut!((*ctx).gpr.rsi).write_volatile(handler);
        let flags = addr_of!((*action).sa.sa_flags).read();
        addr_of_mut!((*ctx).gpr.rdx).write_volatile(flags);
        addr_of_mut!((*ctx).gpr.r10).write(0);
        addr_of_mut!((*ctx).gpr.r8).write(0);
        addr_of_mut!((*ctx).gpr.r9).write(0);
        super::syscall_generic_forwarding(13, ctx)
    }
}
const _: unsafe extern "C" fn(CULong) -> CLong = syscall_forward_rt_sigprocmask_bridge;
const _: unsafe extern "C" fn(CInt, *const c_void) -> CLong = syscall_forward_sigaction_update_bridge;
