// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Compile-time witnesses only; no storage, runtime call or alternate provider.
use core::ffi::c_void;
use crate::abi::{CInt, CULong, Thread};
use crate::lock_helpers::{McsRwlockLock, McsRwlockNodeIrqsave};

const _: unsafe extern "C" fn(*mut McsRwlockLock, *mut McsRwlockNodeIrqsave) =
    crate::lock_helpers::__mcs_rwlock_reader_lock;
const _: unsafe extern "C" fn(*mut McsRwlockLock, *mut McsRwlockNodeIrqsave) =
    crate::lock_helpers::__mcs_rwlock_reader_unlock;
const _: unsafe extern "C" fn(CInt, CInt) -> *mut Thread =
    crate::process_helpers::find_thread;
const _: unsafe extern "C" fn(*mut Thread) = crate::process_helpers::thread_unlock;
const _: unsafe extern "C" fn(*mut c_void, *mut c_void) =
    super::f06_clone_reader_lock::arch_clone_reader_lock_bridge;
const _: unsafe extern "C" fn(*mut c_void, *mut c_void) =
    super::f06_clone_reader_unlock::arch_clone_reader_unlock_bridge;
const _: unsafe extern "C" fn(CInt, CInt) -> CULong =
    super::f06_ptrace_find_thread::arch_ptrace_find_thread_bridge;
const _: unsafe extern "C" fn(CULong) =
    super::f06_ptrace_thread_unlock::arch_ptrace_thread_unlock_bridge;

const _: () = {
    assert!(core::mem::size_of::<CInt>() == 4);
    assert!(core::mem::size_of::<CULong>() == 8);
    assert!(core::mem::size_of::<*mut c_void>() == 8);
    assert!(core::mem::size_of::<McsRwlockLock>() == 64);
    assert!(core::mem::align_of::<McsRwlockLock>() == 64);
    assert!(core::mem::size_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(core::mem::align_of::<McsRwlockNodeIrqsave>() == 64);
    // The irqsave offset-zero witness is asserted unconditionally in
    // lock_helpers.rs, inside the defining module's existing const block.
};
