// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact nominal adapters; existing Rust general-register providers retain behavior.
use core::ffi::c_void;
use crate::abi::{CLong,CULong,Thread,UserRegsStruct};

/// # Safety
/// Caller keeps the existing provider's target lifetime/exclusion and writable
/// register-buffer contract. Raw LP64 thread bits and register address retain
/// their original meanings; no reference, validation or resource owner is added.
#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_read_gpregs_bridge(
    thread_addr:CULong,
    registers:*mut c_void,
) -> CLong {
    // SAFETY: exact original nominal casts, provider obligations and signed result.
    unsafe {
        crate::syscall_policy::ptrace_read_gpregs(
            thread_addr as *mut Thread,registers.cast::<UserRegsStruct>(),
        )
    }
}

/// # Safety
/// Target and readable const register-buffer lifetime/exclusion remain with the
/// unchanged Rust provider/caller. This adapter neither reads nor mutates them;
/// it preserves the exact provider result and all partial effects on the target.
#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_write_gpregs_bridge(
    thread_addr:CULong,
    registers:*const c_void,
) -> CLong {
    // SAFETY: original borrowed target/const-input contract; no new ownership.
    unsafe {
        crate::syscall_policy::ptrace_write_gpregs(
            thread_addr as *mut Thread,registers.cast::<UserRegsStruct>(),
        )
    }
}
