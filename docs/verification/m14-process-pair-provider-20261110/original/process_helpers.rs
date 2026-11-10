use core::ffi::c_void;
use core::mem::offset_of;
use core::ptr::null_mut;
use crate::abi::{AbiListHead,CInt,CULong,CpuLocalVar,Process,PROCESS_HASH_SIZE};
use crate::lock_helpers::McsRwlockNodeIrqsave;
unsafe extern "C" {
    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    fn process_mcs_reader_lock_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_mcs_reader_unlock_bridge(lock_addr: CULong, node: *mut c_void);
}
const EINVAL: CInt = 22;
const HASH_SIZE: CInt = PROCESS_HASH_SIZE as CInt;
type ProcessMcsRwlockFn = unsafe extern "C" fn(CULong, *mut c_void);
#[repr(C)]
pub struct ProcessFindProcessOffsets {
    pub process_hash_list_offset: CULong,
    pub process_pid_offset: CULong,
}
#[no_mangle]
pub extern "C" fn process_hash(pid: CInt) -> CInt {
    pid % HASH_SIZE
}
#[no_mangle]
pub unsafe extern "C" fn find_process(pid: CInt, lock: *mut McsRwlockNodeIrqsave) -> *mut Process {
    if pid <= 0 || lock.is_null() {
        return null_mut();
    }

    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).resource_set.is_null() {
        return null_mut();
    }
    let phash = (*(*cpu).resource_set).process_hash;
    if phash.is_null() {
        return null_mut();
    }
    let hash = process_hash(pid);
    if hash < 0 || hash as usize >= PROCESS_HASH_SIZE {
        return null_mut();
    }

    let offsets = ProcessFindProcessOffsets {
        process_hash_list_offset: offset_of!(Process, hash_list) as CULong,
        process_pid_offset: offset_of!(Process, pid) as CULong,
    };
    process_find_process_body_result(
        &raw mut (*phash).list[hash as usize],
        (&raw mut (*phash).lock[hash as usize]) as *mut _ as CULong,
        lock.cast(),
        pid,
        &offsets,
        Some(process_mcs_reader_lock_bridge),
        Some(process_mcs_reader_unlock_bridge),
    )
    .cast::<Process>()
}
#[no_mangle]
pub unsafe extern "C" fn process_unlock(proc: *mut Process, lock: *mut McsRwlockNodeIrqsave) {
    if proc.is_null() || lock.is_null() {
        return;
    }

    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).resource_set.is_null() {
        return;
    }
    let phash = (*(*cpu).resource_set).process_hash;
    if phash.is_null() {
        return;
    }
    let hash = process_hash((*proc).pid);
    if hash < 0 || hash as usize >= PROCESS_HASH_SIZE {
        return;
    }

    let _ = process_unlock_found_process_result(
        proc.cast(),
        (&raw mut (*phash).lock[hash as usize]) as *mut _ as CULong,
        lock.cast(),
        Some(process_mcs_reader_unlock_bridge),
    );
}
#[no_mangle]
pub unsafe extern "C" fn process_find_process_body_result(
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    pid: CInt,
    offsets: *const ProcessFindProcessOffsets,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
) -> *mut c_void {
    if pid <= 0 {
        return null_mut();
    }
    if hash_head.is_null() || lock_node.is_null() || offsets.is_null() {
        return null_mut();
    }
    let (Some(lock_fn), Some(unlock_fn)) = (lock_fn, unlock_fn) else {
        return null_mut();
    };
    let offsets = &*offsets;

    lock_fn(hash_lock_addr, lock_node);
    let mut entry = (*hash_head).next;
    while !entry.is_null() && entry != hash_head {
        let process = process_list_container(entry, offsets.process_hash_list_offset);
        let proc_pid = *(process
            .cast::<u8>()
            .wrapping_add(offsets.process_pid_offset as usize)
            .cast::<CInt>());
        if proc_pid == pid {
            return process;
        }
        entry = (*entry).next;
    }

    unlock_fn(hash_lock_addr, lock_node);
    null_mut()
}
#[no_mangle]
pub unsafe extern "C" fn process_unlock_found_process_result(
    process: *mut c_void,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    unlock_fn: Option<ProcessMcsRwlockFn>,
) -> CInt {
    if process.is_null() {
        return 0;
    }
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    unlock_fn(hash_lock_addr, lock_node);
    1
}
#[inline]
unsafe fn process_list_container(entry: *mut AbiListHead, list_offset: CULong) -> *mut c_void {
    entry
        .cast::<u8>()
        .wrapping_sub(list_offset as usize)
        .cast::<c_void>()
}
mod remaining_process_lock_and_tid_providers {
    use core::ffi::c_void;
    use core::mem::{align_of,offset_of,size_of};
    use crate::abi::{CULong,McsRwlockLock};
    const _: () = {
        assert!(size_of::<McsRwlockLock>() == 64);
        assert!(align_of::<McsRwlockLock>() == 64);
        assert!(offset_of!(McsRwlockLock, slock) == 0);
        assert!(size_of::<crate::lock_helpers::McsRwlockLock>() == 64);
        assert!(align_of::<crate::lock_helpers::McsRwlockLock>() == 64);
        assert!(size_of::<crate::lock_helpers::McsRwlockNodeIrqsave>() == 64);
        assert!(align_of::<crate::lock_helpers::McsRwlockNodeIrqsave>() == 64);
    };
    #[no_mangle]
    pub unsafe extern "C" fn process_mcs_reader_lock_bridge(lock_addr: CULong, node: *mut c_void) {
        // SAFETY: Preserve the existing typed C representation and actual reader
        // provider selection, including its IRQ handling and synchronization.
        unsafe {
            crate::lock_helpers::__mcs_rwlock_reader_lock(
                lock_addr as *mut crate::lock_helpers::McsRwlockLock,
                node.cast::<crate::lock_helpers::McsRwlockNodeIrqsave>(),
            );
        }
    }
    #[no_mangle]
    pub unsafe extern "C" fn process_mcs_reader_unlock_bridge(lock_addr: CULong, node: *mut c_void) {
        // SAFETY: Actual provider restores the same saved state from the same
        // caller node. No guard lifetime, lock count or pointer value changes.
        unsafe {
            crate::lock_helpers::__mcs_rwlock_reader_unlock(
                lock_addr as *mut crate::lock_helpers::McsRwlockLock,
                node.cast::<crate::lock_helpers::McsRwlockNodeIrqsave>(),
            );
        }
    }
}
