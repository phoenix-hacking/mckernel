#![no_std]
#[path="/home/holden/mckernel-work/host-preparation/evening-next-process-rust-batch2-20261019-1/original/kernel/rust/abi.rs"] mod abi;
use core::ffi::c_void;use core::mem::{offset_of,size_of,MaybeUninit};
use abi::{CInt,CULong,CpuLocalVar,ResourceSet,Process,Mckfd,Thread,ThreadHash,AbiListHead,PROCESS_HASH_SIZE};
#[repr(C,align(64))] struct McsRwlockNodeIrqsave {irqsave:CULong}
unsafe extern "C" {fn get_this_cpu_local_var()->*mut CpuLocalVar;fn process_mcs_reader_lock_bridge(l:CULong,n:*mut c_void);fn process_mcs_reader_unlock_bridge(l:CULong,n:*mut c_void); }

extern "C" {
    fn hugefileobj_cleanup();
    #[cfg(enable_tofu)]
    fn tof_utofu_finalize();
}

const _: () = {
    #[cfg(not(enable_tofu))]
    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);
    #[cfg(enable_tofu)]
    assert!(offset_of!(CpuLocalVar, resource_set) == 24368);
    assert!(offset_of!(ResourceSet, pid1) == 320);
    assert!(offset_of!(Process, children_list) == 288);
    assert!(offset_of!(Process, children_lock) == 320);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
};

/// Read the current CPU's existing resource-set binding. The CPU-local pointer
/// returned by the existing ABI remains valid for this synchronous read. The
/// caller retains CPU affinity and owns the resource-set lifetime; this callback
/// neither obtains a reference nor interprets a possibly null resource-set value.
#[no_mangle]
pub unsafe extern "C" fn process_current_resource_set_bridge() -> *mut c_void {
    unsafe { (*get_this_cpu_local_var()).resource_set.cast() }
}

/// Perform existing last-child cleanup under pid1's children reader lock.
/// The resource set, pid1 process, initialized child-list head and lock storage
/// remain live, and pid1 stays stable throughout synchronous callbacks. The
/// cleanup callees retain their existing concurrency/ownership contracts. The
/// list-empty test is exactly head.next == head; no list mutation/free is added.
#[no_mangle]
pub unsafe extern "C" fn process_release_final_cleanup_bridge(resource_set_arg: *mut c_void) {
    let rset = resource_set_arg.cast::<ResourceSet>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        process_mcs_reader_lock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
        let head = core::ptr::addr_of_mut!((*(*rset).pid1).children_list);
        if (*head).next == head {
            #[cfg(enable_tofu)]
            tof_utofu_finalize();
            hugefileobj_cleanup();
        }
        process_mcs_reader_unlock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
    }
}
type ProcessRefDecAndTestFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;
type ProcessCurrentResourceSetFn = unsafe extern "C" fn() -> *mut c_void;
type ProcessResourceProcessActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessProcessActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessResourceSetActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessThreadActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessSpinLockFn = unsafe extern "C" fn(CULong) -> CULong;
type ProcessSpinUnlockFn = unsafe extern "C" fn(CULong, CULong);
type ProcessFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessMckfdFreeFn = unsafe extern "C" fn(*mut c_void);

unsafe extern "C" {
fn process_release_process_body_result(
    proc: *mut c_void,
    refcount_offset: CULong,
    tids_offset: CULong,
    main_thread_offset: CULong,
    mckfd_offset: CULong,
    mckfd_lock_offset: CULong,
    mckfd_next_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    current_resource_set_fn: Option<ProcessCurrentResourceSetFn>,
    hash_detach_fn: Option<ProcessResourceProcessActionFn>,
    sibling_detach_fn: Option<ProcessProcessActionFn>,
    profile_fn: Option<ProcessProcessActionFn>,
    free_thread_pages_fn: Option<ProcessThreadActionFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    mckfd_free_fn: Option<ProcessMckfdFreeFn>,
    free_fn: Option<ProcessFreeFn>,
    final_cleanup_fn: Option<ProcessResourceSetActionFn>,
) -> CInt;
    fn process_release_profile_bridge(proc: *mut c_void);
    fn process_free_thread_pages_bridge(thread: *mut c_void);
    fn process_mckfd_free_bridge(fdp: *mut c_void);
    fn process_optional_free_bridge(ptr: *mut c_void);
fn process_spin_lock_bridge(lock_addr: CULong) -> CULong;
fn process_spin_unlock_bridge(lock_addr: CULong, irqstate: CULong);
}
unsafe extern "C" {
 fn process_release_hash_detach_bridge(resource_set_arg: *mut c_void, proc_arg: *mut c_void);
 fn process_release_sibling_detach_bridge(proc_arg: *mut c_void);
}
#[no_mangle]
pub unsafe extern "C" fn release_process(proc: *mut Process) {
    let _ = process_release_process_body_result(
        proc.cast(),
        offset_of!(Process, refcount) as CULong,
        offset_of!(Process, tids) as CULong,
        offset_of!(Process, main_thread) as CULong,
        offset_of!(Process, mckfd) as CULong,
        offset_of!(Process, mckfd_lock) as CULong,
        offset_of!(Mckfd, next) as CULong,
        None,
        Some(process_current_resource_set_bridge),
        Some(process_release_hash_detach_bridge),
        Some(process_release_sibling_detach_bridge),
        Some(process_release_profile_bridge),
        Some(process_free_thread_pages_bridge),
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_mckfd_free_bridge),
        Some(process_optional_free_bridge),
        Some(process_release_final_cleanup_bridge),
    );
}

const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;
const HASH_SIZE: CInt = PROCESS_HASH_SIZE as CInt;
unsafe extern "C" {
    fn process_mcs_writer_lock_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_mcs_writer_unlock_bridge(lock_addr: CULong, node: *mut c_void);
}
pub extern "C" fn process_hash(pid: CInt) -> CInt {
    pid % HASH_SIZE
}

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

pub unsafe extern "C" fn process_list_detach_result(entry: *mut AbiListHead) {
    let _ = list_detach(entry);
}
#[no_mangle]
pub extern "C" fn thread_hash(tid: CInt) -> CInt {
    tid % HASH_SIZE
}
const _: () = {
    assert!(offset_of!(Thread, hash_list) == 0);
    assert!(offset_of!(Thread, tid) == 20);
    #[cfg(not(enable_tofu))]
    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);
    #[cfg(enable_tofu)]
    assert!(offset_of!(CpuLocalVar, resource_set) == 24368);
    assert!(offset_of!(ResourceSet, thread_hash) == 32);
    assert!(offset_of!(ThreadHash, lock) == 1216);
    assert!(size_of::<ThreadHash>() == 5888);
    assert!(PROCESS_HASH_SIZE == 73);
};
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
