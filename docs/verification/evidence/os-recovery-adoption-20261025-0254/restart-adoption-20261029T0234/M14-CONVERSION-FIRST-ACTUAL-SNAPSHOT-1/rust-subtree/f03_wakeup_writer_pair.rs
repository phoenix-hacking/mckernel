//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Paired IRQ-saving MCS writer callbacks use the existing lock provider.
use core::ffi::c_void;
use core::mem::{align_of, size_of};
use crate::abi::CULong;
use crate::lock_helpers::{self, McsRwlockLock, McsRwlockNodeIrqsave};

const _: () = {
    assert!(size_of::<CULong>() == 8);
    assert!(size_of::<McsRwlockLock>() == 64 && align_of::<McsRwlockLock>() == 64);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64 && align_of::<McsRwlockNodeIrqsave>() == 64);
};

/// Acquire the caller's IRQ-saving writer lock and save flags in its node.
///
/// # Safety
/// The caller provides the original live, 64-byte-aligned lock and exclusive,
/// writable IRQ-save node, follows existing lock ordering and IRQ context, and
/// retains both objects until the matching release completes.
#[no_mangle]
pub unsafe extern "C" fn ptrace_wakeup_update_lock_bridge(lock_addr: CULong, node: *mut c_void) {
    // SAFETY: The selected x86 lock and IRQ-save node have the provider's C
    // representation; raw casts preserve their addresses and caller ownership.
    unsafe { lock_helpers::__mcs_rwlock_writer_lock(lock_addr as *mut McsRwlockLock, node.cast::<McsRwlockNodeIrqsave>()) };
}

/// Release the matching writer acquisition and restore its saved IRQ flags.
///
/// # Safety
/// The caller owns the matching acquisition and provides the same live lock
/// and node without concurrent node reuse until this release has completed.
#[no_mangle]
pub unsafe extern "C" fn ptrace_wakeup_update_unlock_bridge(lock_addr: CULong, node: *mut c_void) {
    // SAFETY: The original lock and saved node are passed to the paired provider;
    // it performs the release and restores the original saved interrupt state.
    unsafe { lock_helpers::__mcs_rwlock_writer_unlock(lock_addr as *mut McsRwlockLock, node.cast::<McsRwlockNodeIrqsave>()) };
}

type WriterCallback = unsafe extern "C" fn(CULong, *mut c_void);
const _: WriterCallback = ptrace_wakeup_update_lock_bridge;
const _: WriterCallback = ptrace_wakeup_update_unlock_bridge;
