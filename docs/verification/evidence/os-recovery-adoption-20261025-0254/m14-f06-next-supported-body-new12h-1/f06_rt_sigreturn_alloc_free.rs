// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_void;
use core::ptr::addr_of;

use crate::abi::{CInt, CULong, SizeT};

unsafe extern "C" {
    // Immutable NUL-terminated C TU __FILE__; metadata proposal pending Root review.
    static f06_rt_sigreturn_source_file: u8;
}

/// # Safety
/// Preserve the tracked allocator's CPU/context and flags contract. Caller owns
/// the returned allocation, with the original NULL/OOM behavior unchanged.
#[cfg(f06_rt_sigreturn_alloc_candidate)]
#[no_mangle]
pub unsafe extern "C" fn arch_rt_sigreturn_alloc_bridge(
    size: SizeT,
    flags: CULong,
) -> *mut c_void {
    // SAFETY: same provider, original narrowing/flags and immutable C filename.
    unsafe {
        crate::mem_helpers::kmalloc_tracked(
            size as CInt,
            flags,
            addr_of!(f06_rt_sigreturn_source_file).cast_mut().cast(),
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
    // the filename is immutable and lives for the entire kernel image lifetime.
    unsafe {
        crate::mem_helpers::kfree_tracked(
            pointer,
            addr_of!(f06_rt_sigreturn_source_file).cast_mut().cast(),
            391,
        );
    }
}
