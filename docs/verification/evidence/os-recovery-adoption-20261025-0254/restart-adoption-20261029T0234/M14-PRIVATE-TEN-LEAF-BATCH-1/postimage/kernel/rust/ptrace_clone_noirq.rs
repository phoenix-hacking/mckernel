//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! The x86 noirq ptrace clone callbacks delegate to the existing Rust lock pair.
use core::ffi::c_void;
use crate::abi::CULong;
use crate::lock_helpers::{self, McsRwlockLock};

/// # Safety
/// `lock_addr` is the live, aligned selected x86 MCS rwlock supplied by the
/// caller, and `node` is its live caller-owned node. Interrupt state and the
/// surrounding critical section are owned by the caller. The matching unlock
/// must receive the same lock and node after the protected operations.
#[no_mangle]
pub unsafe extern "C" fn ptrace_report_clone_noirq_lock_bridge(
    lock_addr: CULong, node: *mut c_void,
) {
    lock_helpers::__mcs_rwlock_writer_lock_noirq(lock_addr as *mut McsRwlockLock, node);
}

/// # Safety
/// The lock must be held by the matching noirq writer acquisition using this
/// same live node. This call does not restore or otherwise alter IRQ flags.
#[no_mangle]
pub unsafe extern "C" fn ptrace_report_clone_noirq_unlock_bridge(
    lock_addr: CULong, node: *mut c_void,
) {
    lock_helpers::__mcs_rwlock_writer_unlock_noirq(lock_addr as *mut McsRwlockLock, node);
}
