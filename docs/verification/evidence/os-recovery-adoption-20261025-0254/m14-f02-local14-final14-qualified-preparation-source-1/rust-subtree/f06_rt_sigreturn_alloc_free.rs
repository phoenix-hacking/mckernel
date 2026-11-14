// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_void;

use crate::abi::{CInt, CULong, SizeT};

// Derived from the hash-bound selected SDK C argv. C asserts __FILE__ equality.
// Missing producer binding is a compile error; no path fallback or normalization.
static F06_RT_SIGRETURN_ORIGIN: &str = concat!(env!("MCKERNEL_F06_RT_SIGRETURN_ORIGIN"), "\0");

/// # Safety
/// Preserve the tracked allocator's CPU/context and flags contract. Caller owns
/// the returned allocation, with the original NULL/OOM behavior unchanged.
#[cfg(f06_rt_sigreturn_alloc_candidate)]
#[no_mangle]
pub unsafe extern "C" fn arch_rt_sigreturn_alloc_bridge(
    size: SizeT,
    flags: CULong,
) -> *mut c_void {
    // SAFETY: same provider, original narrowing/flags and Rust-owned immutable original C filename.
    unsafe {
        crate::mem_helpers::kmalloc_tracked(
            size as CInt,
            flags,
            F06_RT_SIGRETURN_ORIGIN.as_ptr().cast_mut().cast(),
            385,
        )
    }
}

/// # Safety
/// Pointer must satisfy the original tracked free provider's lifetime, ownership,
/// CPU/context and allocation requirements, including its original NULL policy.
#[cfg(f06_rt_sigreturn_free_candidate)]
#[no_mangle]
pub unsafe extern "C" fn arch_rt_sigreturn_free_bridge(pointer: *mut c_void) {
    // SAFETY: pass original pointer once, without dereference or adjustment;
    // the Rust-owned filename is immutable and lives for the entire kernel image lifetime.
    unsafe {
        crate::mem_helpers::kfree_tracked(
            pointer,
            F06_RT_SIGRETURN_ORIGIN.as_ptr().cast_mut().cast(),
            391,
        );
    }
}
