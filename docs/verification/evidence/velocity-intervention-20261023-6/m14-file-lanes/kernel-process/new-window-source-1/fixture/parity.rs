// Functional OS parity fixture source only; no security testing.
// Mock layouts exercise control/print/lock behavior, not production ABI acceptance.
#![no_std]
use core::mem::{offset_of, MaybeUninit};

type CInt = i32;
type CULong = u64;
const PROCESS_HASH_SIZE: usize = 73;

#[repr(C)]
struct AbiListHead {
    next: *mut AbiListHead,
    prev: *mut AbiListHead,
}
#[repr(C)]
struct McsRwlockLock(i32);
#[repr(C)]
struct McsRwlockNodeIrqsave(i32);
#[repr(C)]
struct IhkAtomic {
    counter: CInt,
}
#[repr(C)]
struct Process {
    hash_list: AbiListHead,
    ppid_parent: *mut Process,
    refcount: IhkAtomic,
    status: CInt,
    pid: CInt,
}
#[repr(C)]
struct Thread {
    hash_list: AbiListHead,
    proc: *mut Process,
    cpu_id: CInt,
    tid: CInt,
    status: CInt,
    in_syscall_offload: CInt,
    refcount: IhkAtomic,
    ptrace: CInt,
}
#[repr(C)]
struct ProcessHash {
    list: [AbiListHead; PROCESS_HASH_SIZE],
    lock: [McsRwlockLock; PROCESS_HASH_SIZE],
}
#[repr(C)]
struct ThreadHash {
    list: [AbiListHead; PROCESS_HASH_SIZE],
    lock: [McsRwlockLock; PROCESS_HASH_SIZE],
}
#[repr(C)]
struct ResourceSet {
    process_hash: *mut ProcessHash,
    thread_hash: *mut ThreadHash,
    pid1: *mut Process,
}
#[repr(C)]
struct CpuLocalVar {
    resource_set: *mut ResourceSet,
}

unsafe extern "C" {
    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    fn kprintf(format: *const i8, ...) -> CInt;
    fn fixture_reader_lock(lock: *mut McsRwlockLock, node: *mut McsRwlockNodeIrqsave);
    fn fixture_reader_unlock(lock: *mut McsRwlockLock, node: *mut McsRwlockNodeIrqsave);
}

mod lock_helpers {
    use super::{McsRwlockLock, McsRwlockNodeIrqsave};

    pub unsafe fn __mcs_rwlock_reader_lock(
        lock: *mut McsRwlockLock,
        node: *mut McsRwlockNodeIrqsave,
    ) {
        unsafe { super::fixture_reader_lock(lock, node) };
    }

    pub unsafe fn __mcs_rwlock_reader_unlock(
        lock: *mut McsRwlockLock,
        node: *mut McsRwlockNodeIrqsave,
    ) {
        unsafe { super::fixture_reader_unlock(lock, node) };
    }
}

include!("debug_log.ACTUAL-RUST.inc");
