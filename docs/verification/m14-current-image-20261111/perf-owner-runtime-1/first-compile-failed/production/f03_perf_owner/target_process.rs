// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private perf protocol candidate. This file is not wired into a selected target.
// Genuine remote-Process hash borrow and positive reference have distinct owners.

use core::ffi::c_void;
use core::ptr::addr_of_mut;
use core::sync::atomic::{AtomicI32, Ordering};
use crate::abi::{CInt, CLong, Process};

pub(super) type FindProcess = unsafe extern "C" fn(CInt, *mut c_void) -> *mut c_void;
pub(super) type UnlockProcess = unsafe extern "C" fn(*mut c_void, *mut c_void);
const EINVAL: CInt = 22;

/// Own BOTH the actual hash-reader borrow and one strictly positive Process edge.
/// Destruction order is fixed: release hash borrow, THEN consume the reference.
/// No monitor/event retains a permanent Process edge through this guard.
struct HashHeldTarget {
    process: *mut Process,
    node: *mut c_void,
    unlock: UnlockProcess,
    positive_edge: bool,
    hash_held: bool,
}

impl Drop for HashHeldTarget {
    fn drop(&mut self) {
        // SAFETY: A successful genuine find_process returned this exact Process
        // with its matching hash/IRQ node. This object is never copied, and
        // owns the single matching unlock. The positive edge (if any) prevents
        // destruction until AFTER the hash reader has actually been released.
        unsafe {
            if self.hash_held {
                (self.unlock)(self.process.cast(), self.node);
                self.hash_held = false;
            }
            if self.positive_edge {
                self.positive_edge = false;
                crate::process_helpers::release_process(self.process);
            }
        }
    }
}

/// Acquire without resurrecting a still-hashed zero-count Process.
///
/// # Safety
/// `process` is the actual Process protected by the genuine current hash-reader
/// borrow. Its repr(C) IhkAtomic counter is the same storage already used by
/// process_helpers::process_ref_atomic_at. This code does NOT alter that
/// existing global helper's unconditional hold semantics.
unsafe fn retain_positive(process: *mut Process) -> bool {
    let counter = unsafe { AtomicI32::from_ptr(addr_of_mut!((*process).refcount.counter)) };
    let mut old = counter.load(Ordering::SeqCst);
    loop {
        if old <= 0 { return false; }
        let Some(next) = old.checked_add(1) else { return false; };
        match counter.compare_exchange_weak(old, next, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(_) => return true,
            Err(observed) => old = observed,
        }
    }
}

/// Run the actual remote-monitor publication while a positive target is owned.
///
/// # Safety
/// `find` and `unlock` are the exact selected C ABI pair, with `node` holding its
/// genuine aligned stack IRQ/hash-reader state until this call finishes. `body`
/// runs after the genuine hash/IRQ unlock and only publishes the finite perf-owned weak monitor association; it must not
/// retain the raw Process beyond the terminal-hook contract or release this edge.
/// Both normal return and unwinding unlock BEFORE possibly-final release.
/// A miss or dying/overflowed target reports the existing invalid-target error.
pub(super) unsafe fn with_remote_target(
    pid: CInt,
    node: *mut c_void,
    find: FindProcess,
    unlock: UnlockProcess,
    body: impl FnOnce(*mut Process) -> CLong,
) -> Result<CLong, CInt> {
    if pid <= 0 || node.is_null() { return Err(-EINVAL); }
    let process = unsafe { find(pid, node) }.cast::<Process>();
    if process.is_null() { return Err(-EINVAL); }
    // The genuine miss path releases its reader itself. Only the nonnull path
    // transfers the reader borrow here. Create its guard BEFORE fallible work.
    let mut held = HashHeldTarget { process, node, unlock, positive_edge: false, hash_held: true };
    if !unsafe { retain_positive(process) } { return Err(-EINVAL); }
    held.positive_edge = true;
    // A real positive reference now owns lifetime independently of the hash
    // borrow. Release hash/IRQ BEFORE allocator/setup/offload or R acquisition.
    unsafe { (held.unlock)(held.process.cast(), held.node) };
    held.hash_held = false;
    let result = body(process);
    drop(held);
    Ok(result)
}
