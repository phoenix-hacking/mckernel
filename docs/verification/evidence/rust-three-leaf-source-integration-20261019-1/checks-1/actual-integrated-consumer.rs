#![no_std]
#[path="/home/holden/mckernel/kernel/rust/abi.rs"] mod abi;
use core::ffi::c_void;
use core::mem::{offset_of,size_of,MaybeUninit};
use abi::{AbiListHead,AddressSpace,CInt,CULong,Thread,ThreadHash,ResourceSet,CpuLocalVar,Process,ProcessVm,SigPending,PROCESS_HASH_SIZE};
mod debug { #[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
 }
mod lock_helpers {use crate::abi::CULong; #[repr(C, align(64))]
pub struct McsRwlockNodeIrqsave {
    irqsave: CULong,
}}
use lock_helpers::McsRwlockNodeIrqsave;
const HASH_SIZE:CInt=PROCESS_HASH_SIZE as CInt;
const LIST_POISON1:usize=0x0010_0129;const LIST_POISON2:usize=0x0020_0229;
type ProcessMcsRwlockFn = unsafe extern "C" fn(CULong, *mut c_void);
type ProcessOptionalFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessReleaseFpRegsFn = unsafe extern "C" fn(*mut c_void);
type ProcessSpinLockFn = unsafe extern "C" fn(CULong) -> CULong;
type ProcessSpinUnlockFn = unsafe extern "C" fn(CULong, CULong);
type ProcessThreadActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessThreadProcActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessThreadTidActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CInt);
type ProcessTidLogFn = unsafe extern "C" fn(CInt, *mut c_void, CInt);
extern "C" {    fn process_mcs_writer_lock_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_mcs_writer_unlock_bridge(lock_addr: CULong, node: *mut c_void);
    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    fn process_destroy_thread_release_tid_bridge(proc: *mut c_void, thread: *mut c_void);
    fn process_destroy_thread_replace_tid_bridge(
        proc: *mut c_void,
        thread: *mut c_void,
        new_tid: CInt,
    );
fn process_spin_lock_bridge(lock_addr: CULong) -> CULong;
fn process_spin_unlock_bridge(lock_addr: CULong, irqstate: CULong);
    fn process_optional_free_bridge(ptr: *mut c_void);
    fn release_fp_regs(thread: *mut c_void);
fn process_release_sigcommon_bridge(sigcommon: *mut c_void);
    fn process_free_thread_pages_bridge(thread: *mut c_void);
fn process_destroy_thread_body_result(
    thread: *mut c_void,
    thread_proc_offset: CULong,
    thread_vm_offset: CULong,
    thread_cpu_id_offset: CULong,
    thread_siblings_list_offset: CULong,
    thread_uti_state_offset: CULong,
    thread_uti_refill_tid_offset: CULong,
    thread_sigpending_offset: CULong,
    thread_sigcommon_offset: CULong,
    proc_threads_lock_offset: CULong,
    proc_tids_offset: CULong,
    proc_main_thread_offset: CULong,
    vm_address_space_offset: CULong,
    address_space_cpu_set_offset: CULong,
    address_space_cpu_set_lock_offset: CULong,
    pending_list_offset: CULong,
    debugreg_offset: CULong,
    recvsig_offset: CULong,
    sendsig_offset: CULong,
    fp_regs_offset: CULong,
    coredump_regs_offset: CULong,
    cpu_set_bits: CInt,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    hash_detach_fn: Option<ProcessThreadActionFn>,
    time_account_fn: Option<ProcessThreadActionFn>,
    release_tid_fn: Option<ProcessThreadProcActionFn>,
    replace_tid_fn: Option<ProcessThreadTidActionFn>,
    cpu_lock_fn: Option<ProcessSpinLockFn>,
    cpu_unlock_fn: Option<ProcessSpinUnlockFn>,
    free_fn: Option<ProcessOptionalFreeFn>,
    release_fp_fn: Option<ProcessReleaseFpRegsFn>,
    release_sigcommon_fn: Option<ProcessThreadActionFn>,
    free_thread_pages_fn: Option<ProcessThreadActionFn>,
) -> CInt;
#[link_name="num_processors"] static mut PROCESS_NUM_PROCESSORS:CInt;
}
#[no_mangle]
pub unsafe extern "C" fn process_tid_index_for_thread_result(
    tids: *const c_void,
    nr_tids: CInt,
    entry_stride: CULong,
    thread_offset: CULong,
    thread_addr: CULong,
) -> CInt {
    if tids.is_null() || nr_tids <= 0 || entry_stride == 0 || thread_addr == 0 {
        return -1;
    }

    let base = tids.cast::<u8>();
    let stride = entry_stride as usize;
    let offset = thread_offset as usize;

    for index in 0..(nr_tids as usize) {
        let entry = base.add(index.saturating_mul(stride).saturating_add(offset));
        let stored = *(entry.cast::<CULong>());
        if stored == thread_addr {
            return index as CInt;
        }
    }

    -1
}
#[no_mangle]
pub extern "C" fn process_tid_index_found_result(index: CInt) -> CInt {
    (index >= 0) as CInt
}
fn checked_entry_addr(
    base: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    member_offset: CULong,
) -> Option<*mut u8> {
    if base.is_null() || index < 0 || entry_stride == 0 {
        return None;
    }

    let offset = (index as usize)
        .checked_mul(entry_stride as usize)?
        .checked_add(member_offset as usize)?;
    Some(base.cast::<u8>().wrapping_add(offset))
}
#[no_mangle]
pub unsafe extern "C" fn process_tid_release_slot_result(
    tids: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    thread_offset: CULong,
) -> CInt {
    let Some(thread_slot) = checked_entry_addr(tids, index, entry_stride, thread_offset) else {
        return 0;
    };

    *(thread_slot.cast::<CULong>()) = 0;
    1
}
#[no_mangle]
pub unsafe extern "C" fn process_release_tid_body_result(
    tids: *mut c_void,
    nr_tids: CInt,
    tid_stride: CULong,
    tid_thread_offset: CULong,
    thread: *mut c_void,
    thread_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    if tids.is_null() || thread.is_null() {
        return 0;
    }

    let index = process_tid_index_for_thread_result(
        tids,
        nr_tids,
        tid_stride,
        tid_thread_offset,
        thread as CULong,
    );
    if process_tid_index_found_result(index) == 0 {
        return 0;
    }
    if process_tid_release_slot_result(tids, index, tid_stride, tid_thread_offset) == 0 {
        return 0;
    }

    let _ = process_tid_log_result(thread_tid, thread, 0, log_fn);
    1
}
#[no_mangle]
pub unsafe extern "C" fn process_tid_log_result(
    old_tid: CInt,
    thread: *mut c_void,
    new_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(old_tid, thread, new_tid);
    1
}
#[no_mangle]
pub extern "C" fn thread_hash(tid: CInt) -> CInt {
    tid % HASH_SIZE
}
#[no_mangle]
pub unsafe extern "C" fn process_list_is_linked_result(entry: *const AbiListHead) -> CInt {
    if entry.is_null() {
        return 0;
    }

    let next = (*entry).next;
    (!next.is_null() && next != entry.cast_mut()) as CInt
}
unsafe fn list_detach(entry: *mut AbiListHead) -> bool {
    if entry.is_null() {
        return false;
    }

    let prev = (*entry).prev;
    let next = (*entry).next;
    if prev.is_null() || next.is_null() || next == entry {
        return false;
    }

    (*next).prev = prev;
    (*prev).next = next;
    (*entry).next = LIST_POISON1 as *mut AbiListHead;
    (*entry).prev = LIST_POISON2 as *mut AbiListHead;
    true
}
#[no_mangle]
pub unsafe extern "C" fn process_list_detach_result(entry: *mut AbiListHead) {
    let _ = list_detach(entry);
}

// This private callback preserves the existing optional dynamic-debug event.
#[used]
#[link_section = "__verbose"]
static mut RELEASE_TID_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"process_release_tid_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};

extern "C" {
    fn kprintf(format: *const i8, ...) -> CInt;
}

unsafe extern "C" fn process_release_tid_log_bridge(
    tid: CInt, thread: *mut c_void, _new_tid: CInt,
) {
    let flags = unsafe {
        core::ptr::read_volatile(core::ptr::addr_of!(RELEASE_TID_DEBUG.line_flags)) >> 24
    };
    if flags != 0 {
        unsafe {
            kprintf(
                b"%s: tid %d has been released by %p\n\0".as_ptr().cast(),
                b"__release_tid\0".as_ptr().cast::<i8>(), tid, thread,
            );
        }
    }
}

const _: () = {
    assert!(offset_of!(Process, tids) == 256);
    assert!(offset_of!(Process, nr_tids) == 264);
    assert!(offset_of!(Thread, tid) == 20);
    assert!(size_of::<crate::abi::McexecTid>() == 16);
    assert!(offset_of!(crate::abi::McexecTid, thread) == 8);
};

/// Release the first slot referring to this live thread under threads_lock.
///
/// Both pointers must be valid and live through the call. The caller holds the
/// owning process's threads_lock and excludes concurrent/reentrant slot changes.
/// `tids` is null or covers `nr_tids` entries when that count is positive.
/// The helper clears only the matched thread pointer, retaining the numeric TID,
/// and invokes diagnostics after the clear. This does not free thread storage.
#[no_mangle]
pub unsafe extern "C" fn __release_tid(proc: *mut Process, thread: *mut Thread) {
    let _ = unsafe {
        process_release_tid_body_result(
            (*proc).tids, (*proc).nr_tids,
            size_of::<crate::abi::McexecTid>() as CULong,
            offset_of!(crate::abi::McexecTid, thread) as CULong,
            thread.cast(), (*thread).tid, Some(process_release_tid_log_bridge),
        )
    };
}

// Reuse existing exported time operations; aliases avoid leaf-batch name clashes.
extern "C" {
    #[link_name = "tsc_to_ts"]
    fn process_teardown_tsc_to_ts(tsc: CULong, ts: *mut crate::abi::TimeSpec);
    #[link_name = "ts_add"]
    fn process_teardown_ts_add(dst: *mut crate::abi::TimeSpec, src: *const crate::abi::TimeSpec);
}

const _: () = {
    assert!(offset_of!(Thread, proc) == 4304);
    assert!(offset_of!(Thread, system_tsc) == 5040);
    assert!(offset_of!(Thread, user_tsc) == 5048);
    assert!(offset_of!(Process, update_lock) == 64);
    assert!(offset_of!(Process, stime) == 1296);
    assert!(offset_of!(Process, utime) == 1312);
    assert!(size_of::<crate::abi::TimeSpec>() == 16);
};

/// Accumulate both live thread clocks under the existing process update lock.
/// The thread and owning process remain valid and stable through synchronous
/// lock/time callbacks; this callback acquires and releases the same lock once.
/// Existing initialized clock-rate and timespec arithmetic preconditions apply.
#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_time_account_bridge(thread_arg: *mut c_void) {
    let thread = thread_arg.cast::<Thread>();
    let proc = unsafe { (*thread).proc };
    let mut updatelock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let mut ats = MaybeUninit::<crate::abi::TimeSpec>::uninit();
    unsafe {
        process_mcs_writer_lock_bridge(
            core::ptr::addr_of_mut!((*proc).update_lock) as CULong,
            updatelock.as_mut_ptr().cast(),
        );
        process_teardown_tsc_to_ts((*thread).system_tsc, ats.as_mut_ptr());
        process_teardown_ts_add(core::ptr::addr_of_mut!((*(*thread).proc).stime), ats.as_ptr());
        process_teardown_tsc_to_ts((*thread).user_tsc, ats.as_mut_ptr());
        process_teardown_ts_add(core::ptr::addr_of_mut!((*(*thread).proc).utime), ats.as_ptr());
        process_mcs_writer_unlock_bridge(
            core::ptr::addr_of_mut!((*proc).update_lock) as CULong,
            updatelock.as_mut_ptr().cast(),
        );
    }
}

const _: () = {
    assert!(offset_of!(Thread, hash_list) == 0);
    assert!(offset_of!(Thread, tid) == 20);
    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);
    assert!(offset_of!(ResourceSet, thread_hash) == 32);
    assert!(offset_of!(ThreadHash, lock) == 1216);
    assert!(size_of::<ThreadHash>() == 5888);
    assert!(PROCESS_HASH_SIZE == 73);
};

/// Remove a final-destruction thread from its existing CPU resource-set hash.
/// The caller owns this live thread's teardown and excludes concurrent mutation
/// of its list-membership test until the existing hash lock is acquired. On the
/// linked path, CPU/resource-set/hash storage stays live and CPU binding stable;
/// TID is nonnegative and selects a valid existing bucket. Adjacent list nodes
/// stay valid under the hash writer lock. This is one-time detach: poisoned
/// list entries must not be passed again. No new lock or lifetime policy is added.
#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_hash_detach_bridge(thread_arg: *mut c_void) {
    let thread = thread_arg.cast::<Thread>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        let entry = core::ptr::addr_of_mut!((*thread).hash_list);
        if process_list_is_linked_result(entry) != 0 {
            let resource_set = (*get_this_cpu_local_var()).resource_set;
            let hash = thread_hash((*thread).tid);
            let lock_addr = core::ptr::addr_of_mut!((*(*resource_set).thread_hash).lock)
                .cast::<crate::abi::McsRwlockLock>().add(hash as usize) as CULong;
            process_mcs_writer_lock_bridge(lock_addr, lock.as_mut_ptr().cast());
            process_list_detach_result(entry);
            let lock_addr = core::ptr::addr_of_mut!((*(*resource_set).thread_hash).lock)
                .cast::<crate::abi::McsRwlockLock>().add(hash as usize) as CULong;
            process_mcs_writer_unlock_bridge(lock_addr, lock.as_mut_ptr().cast());
        }
    }
}
#[no_mangle]
pub unsafe extern "C" fn destroy_thread(thread: *mut Thread) {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let _ = process_destroy_thread_body_result(
        thread.cast(),
        offset_of!(Thread, proc) as CULong,
        offset_of!(Thread, vm) as CULong,
        offset_of!(Thread, cpu_id) as CULong,
        offset_of!(Thread, siblings_list) as CULong,
        offset_of!(Thread, uti_state) as CULong,
        offset_of!(Thread, uti_refill_tid) as CULong,
        offset_of!(Thread, sigpending) as CULong,
        offset_of!(Thread, sigcommon) as CULong,
        offset_of!(Process, threads_lock) as CULong,
        offset_of!(Process, tids) as CULong,
        offset_of!(Process, main_thread) as CULong,
        offset_of!(ProcessVm, address_space) as CULong,
        offset_of!(AddressSpace, cpu_set) as CULong,
        offset_of!(AddressSpace, cpu_set_lock) as CULong,
        offset_of!(SigPending, list) as CULong,
        offset_of!(Thread, ptrace_debugreg) as CULong,
        offset_of!(Thread, ptrace_recvsig) as CULong,
        offset_of!(Thread, ptrace_sendsig) as CULong,
        offset_of!(Thread, fp_regs) as CULong,
        offset_of!(Thread, coredump_regs) as CULong,
        PROCESS_NUM_PROCESSORS,
        lock.as_mut_ptr().cast(),
        Some(process_mcs_writer_lock_bridge),
        Some(process_mcs_writer_unlock_bridge),
        Some(process_destroy_thread_hash_detach_bridge),
        Some(process_destroy_thread_time_account_bridge),
        Some(process_destroy_thread_release_tid_bridge),
        Some(process_destroy_thread_replace_tid_bridge),
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_optional_free_bridge),
        Some(release_fp_regs),
        Some(process_release_sigcommon_bridge),
        Some(process_free_thread_pages_bridge),
    );
}
