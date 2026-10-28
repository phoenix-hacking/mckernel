// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete selected xstate write callback; reuse the existing Rust user-copy provider.
use core::ptr::{addr_of, read};

use crate::abi::{CLong, CULong, SizeT, Thread};

/// Update borrowed target FP state through the existing user-copy implementation.
///
/// # Safety
/// `thread_addr` names a live, properly aligned Thread whose fp_regs field is
/// readable under the caller's existing ptrace/thread exclusion. A nonnull FP
/// allocation remains live and writable for the provider call. The caller keeps
/// the original user-copy address/count and target lifetime/exclusion contract.
/// No thread reference, lock, allocation, mapping or FP-state ownership changes.
/// Null/invalid thread addresses remain outside the original C defined domain.
/// No Rust reference is formed over target state or user memory. Partial writes
/// and provider errors pass through, with original signed-int32 result widening.
#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_xstate_copy_from_bridge(
    thread_addr: CULong,
    user_addr: CULong,
    bytes: SizeT,
) -> CLong {
    let thread = thread_addr as *const Thread;
    // SAFETY: unchanged ordinary raw read of the borrowed FP-state pointer.
    let fp_regs = unsafe { read(addr_of!((*thread).fp_regs)) };
    if fp_regs.is_null() {
        return -12; // unchanged -ENOMEM; no copy or state write on this branch.
    }
    // SAFETY: caller retains write exclusion and existing provider obligations.
    unsafe {
        crate::x86_memory_helpers::copy_from_user(
            fp_regs,
            user_addr as *const core::ffi::c_void,
            bytes,
        ) as CLong
    }
}
