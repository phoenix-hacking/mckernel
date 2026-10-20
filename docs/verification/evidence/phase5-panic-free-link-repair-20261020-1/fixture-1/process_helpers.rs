use core::ptr::null_mut;
use core::ffi::c_void;
use core::mem::offset_of;
use core::sync::atomic::{AtomicI32,Ordering};
use crate::abi::{CInt,CULong,Thread,Process,IhkAtomic,AbiListHead,Mckfd};
use core::ptr::write_volatile;
const EINVAL:i32=22;const EBUSY:i32=16;
unsafe extern "C" fn process_release_thread_profile_bridge(_: *mut c_void, _: *mut c_void){}
unsafe extern "C" fn process_procfs_delete_thread_bridge(_: *mut c_void){}
unsafe extern "C" fn process_destroy_thread_bridge(_: *mut c_void){crate::phase5_tests::thread_final();}
unsafe extern "C" fn process_release_vm_bridge(_: *mut c_void){crate::unexpected_destructor();}
type ProcessRefDecAndTestFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;
type ProcessThreadProfileFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessThreadActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessVmActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessRefSetFn = unsafe extern "C" fn(*mut c_void, CULong, CInt);
pub extern "C" fn process_ref_release_should_destroy_result(dec_and_test: CInt) -> CInt {
    (dec_and_test != 0) as CInt
}
pub unsafe extern "C" fn process_ref_dec_and_test_result(
    object: *mut c_void,
    ref_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
) -> CInt {
    if let Some(dec) = dec_fn {
        return dec(object, ref_offset);
    }

    process_ref_dec_and_test_direct_result(object, ref_offset)
}
unsafe fn process_ref_atomic_at(
    object: *mut c_void,
    ref_offset: CULong,
) -> Option<&'static AtomicI32> {
    if object.is_null() {
        return None;
    }

    let atomic = object
        .cast::<u8>()
        .wrapping_add(ref_offset as usize)
        .cast::<IhkAtomic>();
    Some(AtomicI32::from_ptr(&raw mut (*atomic).counter))
}
pub unsafe extern "C" fn process_ref_dec_and_test_direct_result(
    object: *mut c_void,
    ref_offset: CULong,
) -> CInt {
    let Some(atomic) = process_ref_atomic_at(object, ref_offset) else {
        return -EINVAL;
    };

    (atomic.fetch_sub(1, Ordering::SeqCst) - 1 == 0) as CInt
}
unsafe fn field_ptr(base: *mut c_void, offset: CULong) -> *mut c_void {
    *(base
        .cast::<u8>()
        .wrapping_add(offset as usize)
        .cast::<*mut c_void>())
}
pub unsafe extern "C" fn process_thread_profile_result(
    thread: *mut c_void,
    process: *mut c_void,
    profile_fn: Option<ProcessThreadProfileFn>,
) -> CInt {
    let Some(profile) = profile_fn else {
        return 0;
    };

    profile(thread, process);
    0
}
pub unsafe extern "C" fn process_thread_action_result(
    thread: *mut c_void,
    action_fn: Option<ProcessThreadActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(thread);
    0
}
pub unsafe extern "C" fn process_vm_action_result(
    vm: *mut c_void,
    action_fn: Option<ProcessVmActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(vm);
    0
}
pub unsafe extern "C" fn process_release_thread_body_result(
    thread: *mut c_void,
    refcount_offset: CULong,
    vm_offset: CULong,
    proc_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    profile_fn: Option<ProcessThreadProfileFn>,
    procfs_delete_fn: Option<ProcessThreadActionFn>,
    destroy_thread_fn: Option<ProcessThreadActionFn>,
    release_vm_fn: Option<ProcessVmActionFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let Some(procfs_delete_fn) = procfs_delete_fn else {
        return -EINVAL;
    };
    let Some(destroy_thread_fn) = destroy_thread_fn else {
        return -EINVAL;
    };
    let Some(release_vm_fn) = release_vm_fn else {
        return -EINVAL;
    };

    if process_ref_release_should_destroy_result(process_ref_dec_and_test_result(
        thread,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let vm = field_ptr(thread, vm_offset);
    let proc = field_ptr(thread, proc_offset);
    let _ = process_thread_profile_result(thread, proc, profile_fn);
    let _ = process_thread_action_result(thread, Some(procfs_delete_fn));
    let _ = process_thread_action_result(thread, Some(destroy_thread_fn));
    let _ = process_vm_action_result(vm, Some(release_vm_fn));
    1
}
pub unsafe extern "C" fn release_thread(thread: *mut Thread) {
    let _ = process_release_thread_body_result(
        thread.cast(),
        offset_of!(Thread, refcount) as CULong,
        offset_of!(Thread, vm) as CULong,
        offset_of!(Thread, proc) as CULong,
        None,
        Some(process_release_thread_profile_bridge),
        Some(process_procfs_delete_thread_bridge),
        Some(process_destroy_thread_bridge),
        Some(process_release_vm_bridge),
    );
}
pub unsafe extern "C" fn process_ref_set_result(
    object: *mut c_void,
    ref_offset: CULong,
    value: CInt,
    ref_set_fn: Option<ProcessRefSetFn>,
) -> CInt {
    if let Some(ref_set) = ref_set_fn {
        ref_set(object, ref_offset, value);
        return 0;
    }

    process_ref_set_direct_result(object, ref_offset, value)
}
pub unsafe extern "C" fn process_ref_set_direct_result(
    object: *mut c_void,
    ref_offset: CULong,
    value: CInt,
) -> CInt {
    let Some(atomic) = process_ref_atomic_at(object, ref_offset) else {
        return -EINVAL;
    };

    atomic.store(value, Ordering::SeqCst);
    0
}
unsafe fn process_list_head_init(head: *mut AbiListHead) {
    if head.is_null() {
        return;
    }

    (*head).next = head;
    (*head).prev = head;
}
pub unsafe extern "C" fn process_thread_alloc_init_body_result(
    thread: *mut c_void,
    thread_size: CULong,
    refcount_offset: CULong,
    hash_list_offset: CULong,
    siblings_list_offset: CULong,
    ref_set_fn: Option<ProcessRefSetFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let mut offset = 0;
    while offset < thread_size {
        write_volatile(thread.cast::<u8>().add(offset as usize), 0);
        offset = offset.wrapping_add(1);
    }
    if process_ref_set_result(thread, refcount_offset, 2, ref_set_fn) != 0 {
        return -EINVAL;
    }
    process_list_head_init(
        thread
            .cast::<u8>()
            .add(hash_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    process_list_head_init(
        thread
            .cast::<u8>()
            .add(siblings_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    0
}
type ProcessMckfdFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessCurrentResourceSetFn = unsafe extern "C" fn() -> *mut c_void;
type ProcessResourceProcessActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessProcessActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessResourceSetActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessVmReleaseCheckedFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessSpinLockFn = unsafe extern "C" fn(CULong) -> CULong;
type ProcessSpinUnlockFn = unsafe extern "C" fn(CULong, CULong);
type ProcessFreeFn = unsafe extern "C" fn(*mut c_void);
pub unsafe extern "C" fn process_free_callback_result(
    ptr: *mut c_void,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(ptr);
    0
}

pub unsafe extern "C" fn process_mckfd_drain_free_result(
    headp: *mut *mut c_void,
    next_offset: CULong,
    free_fn: Option<ProcessMckfdFreeFn>,
) -> CInt {
    if headp.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut freed = 0;
    let mut current = *headp;
    while !current.is_null() {
        let next_slot = current
            .cast::<u8>()
            .wrapping_add(next_offset as usize)
            .cast::<*mut c_void>();
        let next = *next_slot;
        *headp = next;
        *next_slot = core::ptr::null_mut();
        freed += process_mckfd_free_result(current, Some(free_fn));
        current = next;
    }

    freed
}

pub unsafe extern "C" fn process_current_resource_set_result(
    current_resource_set_fn: Option<ProcessCurrentResourceSetFn>,
) -> *mut c_void {
    let Some(current_resource_set) = current_resource_set_fn else {
        return null_mut();
    };

    current_resource_set()
}

pub unsafe extern "C" fn process_resource_process_action_result(
    resource_set: *mut c_void,
    process: *mut c_void,
    action_fn: Option<ProcessResourceProcessActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(resource_set, process);
    0
}

pub unsafe extern "C" fn process_process_action_result(
    process: *mut c_void,
    action_fn: Option<ProcessProcessActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(process);
    0
}

pub unsafe extern "C" fn process_resource_set_action_result(
    resource_set: *mut c_void,
    action_fn: Option<ProcessResourceSetActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(resource_set);
    0
}

pub unsafe extern "C" fn process_spin_lock_result(
    lock_addr: CULong,
    lock_fn: Option<ProcessSpinLockFn>,
) -> CULong {
    let Some(lock) = lock_fn else {
        return 0;
    };

    lock(lock_addr)
}

pub unsafe extern "C" fn process_spin_unlock_result(
    lock_addr: CULong,
    irqstate: CULong,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };

    unlock(lock_addr, irqstate);
    0
}

pub unsafe extern "C" fn process_release_process_body_result(
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
) -> CInt {
    if proc.is_null() {
        return -EINVAL;
    }
    let Some(current_resource_set_fn) = current_resource_set_fn else {
        return -EINVAL;
    };
    let Some(hash_detach_fn) = hash_detach_fn else {
        return -EINVAL;
    };
    let Some(sibling_detach_fn) = sibling_detach_fn else {
        return -EINVAL;
    };
    let Some(free_thread_pages_fn) = free_thread_pages_fn else {
        return -EINVAL;
    };
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(mckfd_free_fn) = mckfd_free_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    let Some(final_cleanup_fn) = final_cleanup_fn else {
        return -EINVAL;
    };

    if process_ref_release_should_destroy_result(process_ref_dec_and_test_result(
        proc,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let resource_set = process_current_resource_set_result(Some(current_resource_set_fn));
    let _ = process_resource_process_action_result(resource_set, proc, Some(hash_detach_fn));
    let _ = process_process_action_result(proc, Some(sibling_detach_fn));

    let tids = field_ptr(proc, tids_offset);
    if !tids.is_null() {
        let _ = process_free_callback_result(tids, Some(free_fn));
    }

    if let Some(profile_fn) = profile_fn {
        let _ = process_process_action_result(proc, Some(profile_fn));
    }

    let main_thread = field_ptr(proc, main_thread_offset);
    if !main_thread.is_null() {
        let _ = process_thread_action_result(main_thread, Some(free_thread_pages_fn));
    }

    let lock_addr = (proc as CULong).wrapping_add(mckfd_lock_offset);
    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mckfd_headp = proc
        .cast::<u8>()
        .wrapping_add(mckfd_offset as usize)
        .cast::<*mut c_void>();
    process_mckfd_drain_free_result(mckfd_headp, mckfd_next_offset, Some(mckfd_free_fn));
    let _ = process_spin_unlock_result(lock_addr, irqstate, Some(unlock_fn));

    let _ = process_free_callback_result(proc, Some(free_fn));
    let _ = process_resource_set_action_result(resource_set, Some(final_cleanup_fn));
    1
}

pub unsafe extern "C" fn process_release_thread_checked_body_result(
    thread: *mut c_void,
    refcount_offset: CULong,
    vm_offset: CULong,
    proc_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    profile_fn: Option<ProcessThreadProfileFn>,
    procfs_delete_fn: Option<ProcessThreadActionFn>,
    destroy_thread_fn: Option<ProcessThreadActionFn>,
    release_vm_fn: Option<ProcessVmReleaseCheckedFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let (Some(procfs_delete_fn), Some(destroy_thread_fn), Some(release_vm_fn)) =
        (procfs_delete_fn, destroy_thread_fn, release_vm_fn)
    else {
        return -EINVAL;
    };
    // Cache both pointers before any decrement or destructive callback.
    let vm = field_ptr(thread, vm_offset);
    let proc = field_ptr(thread, proc_offset);
    if vm.is_null() || proc.is_null() {
        return -EINVAL;
    }
    match process_ref_dec_and_test_result(thread, refcount_offset, dec_fn) {
        0 => return 0,
        1 => {},
        error if error < 0 => return error,
        _ => return -EINVAL,
    }
    let _ = process_thread_profile_result(thread, proc, profile_fn);
    procfs_delete_fn(thread);
    destroy_thread_fn(thread);
    // thread is dead. Only cached vm may be passed to the checked callback;
    // vm may also become dead before the callback returns.
    match release_vm_fn(vm) {
        0 => 1,
        1 => 2,
        error if error < 0 => error,
        _ => -EINVAL,
    }
}

pub unsafe extern "C" fn release_thread_checked(thread: *mut Thread) -> CInt {
    process_release_thread_checked_body_result(
        thread.cast(),
        offset_of!(Thread, refcount) as CULong,
        offset_of!(Thread, vm) as CULong,
        offset_of!(Thread, proc) as CULong,
        None,
        Some(process_release_thread_profile_bridge),
        Some(process_procfs_delete_thread_bridge),
        Some(process_destroy_thread_bridge),
        Some(process_release_vm_checked_bridge),
    )
}

pub unsafe extern "C" fn release_process_checked(proc: *mut Process) -> CInt {
    process_release_process_body_result(
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
    )
}

unsafe extern "C" fn process_release_vm_checked_bridge(vm:*mut c_void)->CInt{crate::phase5_tests::release_vm(vm)}
unsafe extern "C" fn process_current_resource_set_bridge()->*mut c_void{1usize as *mut c_void}
unsafe extern "C" fn process_release_hash_detach_bridge(_: *mut c_void,_:*mut c_void){}
unsafe extern "C" fn process_release_sibling_detach_bridge(_: *mut c_void){}
unsafe extern "C" fn process_release_profile_bridge(_: *mut c_void){}
unsafe extern "C" fn process_free_thread_pages_bridge(_: *mut c_void){crate::phase5_tests::pages_final();}
unsafe extern "C" fn process_spin_lock_bridge(_:CULong)->CULong{0}
unsafe extern "C" fn process_spin_unlock_bridge(_:CULong,_:CULong){}
unsafe extern "C" fn process_mckfd_free_bridge(_: *mut c_void){panic!("fixture has no mckfd")}
unsafe extern "C" fn process_optional_free_bridge(_: *mut c_void){crate::phase5_tests::process_final();}
unsafe extern "C" fn process_release_final_cleanup_bridge(_: *mut c_void){}

pub unsafe extern "C" fn process_mckfd_free_result(
    fdp: *mut c_void,
    free_fn: Option<ProcessMckfdFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return 0;
    };

    free(fdp);
    1
}


use crate::abi::{ProcessVm,PROCESS_HASH_SIZE};
use crate::lock_helpers::McsRwlockNodeIrqsave;
use core::mem::MaybeUninit;
const HASH_SIZE:CInt=PROCESS_HASH_SIZE as CInt;const LIST_POISON1:usize=0x0010_0129;const LIST_POISON2:usize=0x0020_0229;
type ProcessRefIncFn=unsafe extern "C" fn(*mut c_void,CULong);
type ProcessMcsRwlockFn=unsafe extern "C" fn(CULong,*mut c_void);
unsafe fn get_this_cpu_local_var()->*mut crate::abi::CpuLocalVar{crate::cls::get_this_cpu_local_var()}
unsafe extern "C" fn process_mcs_writer_lock_bridge(_:u64,_:*mut c_void){}
unsafe extern "C" fn process_mcs_writer_unlock_bridge(_:u64,_:*mut c_void){}

pub extern "C" fn process_hash(pid: CInt) -> CInt {
    pid % HASH_SIZE
}

pub extern "C" fn thread_hash(tid: CInt) -> CInt {
    tid % HASH_SIZE
}

pub unsafe extern "C" fn process_ref_inc_direct_result(
    object: *mut c_void,
    ref_offset: CULong,
) -> CInt {
    let Some(atomic) = process_ref_atomic_at(object, ref_offset) else {
        return -EINVAL;
    };

    let _ = atomic.fetch_add(1, Ordering::SeqCst);
    0
}

pub unsafe extern "C" fn process_ref_inc_result(
    object: *mut c_void,
    ref_offset: CULong,
    inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    if let Some(inc) = inc_fn {
        inc(object, ref_offset);
        return 0;
    }

    process_ref_inc_direct_result(object, ref_offset)
}

unsafe fn list_add_tail(entry: *mut AbiListHead, head: *mut AbiListHead) -> bool {
    if entry.is_null() || head.is_null() {
        return false;
    }

    let prev = (*head).prev;
    if prev.is_null() {
        return false;
    }

    (*entry).next = head;
    (*entry).prev = prev;
    (*prev).next = entry;
    (*head).prev = entry;
    true
}

pub unsafe extern "C" fn process_list_add_tail_result(
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
) {
    let _ = list_add_tail(entry, head);
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

pub unsafe extern "C" fn process_chain_process_body_result(
    siblings_entry: *mut AbiListHead,
    children_head: *mut AbiListHead,
    children_lock_addr: CULong,
    hash_entry: *mut AbiListHead,
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
) -> CInt {
    if siblings_entry.is_null()
        || children_head.is_null()
        || hash_entry.is_null()
        || hash_head.is_null()
        || lock_node.is_null()
    {
        return -EINVAL;
    }
    let (Some(lock_fn), Some(unlock_fn)) = (lock_fn, unlock_fn) else {
        return -EINVAL;
    };

    lock_fn(children_lock_addr, lock_node);
    process_list_add_tail_result(siblings_entry, children_head);
    unlock_fn(children_lock_addr, lock_node);

    lock_fn(hash_lock_addr, lock_node);
    process_list_add_tail_result(hash_entry, hash_head);
    unlock_fn(hash_lock_addr, lock_node);
    1
}

pub unsafe extern "C" fn process_chain_thread_body_result(
    siblings_entry: *mut AbiListHead,
    threads_head: *mut AbiListHead,
    threads_lock_addr: CULong,
    hash_entry: *mut AbiListHead,
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    vm: *mut c_void,
    vm_refcount_offset: CULong,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    ref_inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    let rc = process_chain_process_body_result(
        siblings_entry,
        threads_head,
        threads_lock_addr,
        hash_entry,
        hash_head,
        hash_lock_addr,
        lock_node,
        lock_fn,
        unlock_fn,
    );
    if rc < 0 {
        return rc;
    }
    process_ref_inc_result(vm, vm_refcount_offset, ref_inc_fn)
}

pub(crate) unsafe fn chain_process_checked(proc: *mut Process) -> CInt {
    if proc.is_null() || (*proc).parent.is_null() {
        return -EINVAL;
    }

    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).resource_set.is_null() {
        return -EINVAL;
    }
    let phash = (*(*cpu).resource_set).process_hash;
    if phash.is_null() {
        return -EINVAL;
    }
    let hash = process_hash((*proc).pid);
    if hash < 0 || hash as usize >= PROCESS_HASH_SIZE {
        return -EINVAL;
    }

    let parent = (*proc).parent;
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    process_chain_process_body_result(
        &raw mut (*proc).siblings_list,
        &raw mut (*parent).children_list,
        (&raw mut (*parent).children_lock) as *mut _ as CULong,
        &raw mut (*proc).hash_list,
        &raw mut (*phash).list[hash as usize],
        (&raw mut (*phash).lock[hash as usize]) as *mut _ as CULong,
        lock.as_mut_ptr().cast(),
        Some(process_mcs_writer_lock_bridge),
        Some(process_mcs_writer_unlock_bridge),
    )
}

pub(crate) unsafe fn chain_thread_checked(thread: *mut Thread) -> CInt {
    if thread.is_null() || (*thread).proc.is_null() || (*thread).vm.is_null() {
        return -EINVAL;
    }

    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).resource_set.is_null() {
        return -EINVAL;
    }
    let thash = (*(*cpu).resource_set).thread_hash;
    if thash.is_null() {
        return -EINVAL;
    }
    let hash = thread_hash((*thread).tid);
    if hash < 0 || hash as usize >= PROCESS_HASH_SIZE {
        return -EINVAL;
    }

    let proc = (*thread).proc;
    let vm = (*thread).vm;
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    process_chain_thread_body_result(
        &raw mut (*thread).siblings_list,
        &raw mut (*proc).threads_list,
        (&raw mut (*proc).threads_lock) as *mut _ as CULong,
        &raw mut (*thread).hash_list,
        &raw mut (*thash).list[hash as usize],
        (&raw mut (*thash).lock[hash as usize]) as *mut _ as CULong,
        vm.cast(),
        offset_of!(ProcessVm, refcount) as CULong,
        lock.as_mut_ptr().cast(),
        Some(process_mcs_writer_lock_bridge),
        Some(process_mcs_writer_unlock_bridge),
        None,
    )
}

pub(crate) unsafe fn unpublish_waited_process(proc:*mut Process)->CInt {
    if proc.is_null(){return -EINVAL;}
    let local=get_this_cpu_local_var();
    if local.is_null()||(*local).resource_set.is_null(){return -EINVAL;}
    let phash=(*(*local).resource_set).process_hash;
    let hash=process_hash((*proc).pid);
    if phash.is_null()||hash<0||hash as usize>=PROCESS_HASH_SIZE{return -EINVAL;}
    let mut lock=MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let lock_addr=(&raw mut (*phash).lock[hash as usize])as CULong;
    process_mcs_writer_lock_bridge(lock_addr,lock.as_mut_ptr().cast());
    let entry=&raw mut (*proc).hash_list;
    let result=if process_list_is_linked_result(entry)==0{-EINVAL}else{
        process_list_detach_result(entry);(*entry).next=entry;(*entry).prev=entry;0
    };
    process_mcs_writer_unlock_bridge(lock_addr,lock.as_mut_ptr().cast());result
}

use crate::abi::VmRangeNumaPolicy;
use crate::rbtree::{RbRoot,RbNode};
type ProcessPolicyFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessDetachAddressSpaceFn = unsafe extern "C" fn(*mut c_void, CInt);
type ProcessVmFreeCallback = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessReleaseProcessFn = unsafe extern "C" fn(*mut c_void);
type ProcessMckfdCloseFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
enum ProcessReleaseRoute {Existing(ProcessReleaseProcessFn),FinalChecked(ProcessVmReleaseCheckedFn)}
pub(crate) unsafe fn release_thread_runtime_final_checked(thread:*mut Thread)->CInt {
    process_release_thread_checked_body_result(
        thread.cast(), offset_of!(Thread,refcount) as CULong,
        offset_of!(Thread,vm) as CULong, offset_of!(Thread,proc) as CULong,
        None, Some(process_release_thread_profile_bridge),
        Some(process_procfs_delete_thread_bridge), Some(process_destroy_thread_bridge),
        Some(process_release_vm_final_checked_bridge),
    )
}
unsafe extern "C" fn process_release_vm_final_checked_bridge(vm:*mut c_void)->CInt {
    release_process_vm_final_checked(vm.cast())
}
unsafe extern "C" fn process_release_process_final_checked_bridge(proc:*mut c_void)->CInt {
    release_process_checked(proc.cast())
}
unsafe fn release_process_vm_final_checked(vm: *mut ProcessVm) -> CInt {
    let result = process_release_vm_checked_inner(
        vm.cast(),
        offset_of!(ProcessVm, refcount) as CULong,
        offset_of!(ProcessVm, proc) as CULong,
        offset_of!(Process, mckfd) as CULong,
        offset_of!(Process, mckfd_lock) as CULong,
        offset_of!(Mckfd, next) as CULong,
        offset_of!(Mckfd, close_cb) as CULong,
        offset_of!(ProcessVm, free_cb) as CULong,
        offset_of!(ProcessVm, opt) as CULong,
        offset_of!(ProcessVm, address_space) as CULong,
        offset_of!(Process, pid) as CULong,
        offset_of!(Process, vm) as CULong,
        offset_of!(ProcessVm, vm_range_numa_policy_tree) as CULong,
        offset_of!(VmRangeNumaPolicy, policy_rb_node) as CULong,
        None,
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_flush_vm_bridge),
        Some(process_free_all_ranges_bridge),
        Some(process_detach_address_space_bridge),
        Some(ProcessReleaseRoute::FinalChecked(process_release_process_final_checked_bridge)),
        Some(process_policy_free_bridge),
        Some(process_free_vm_bridge),
    );
    match result { 0 => 0, 2 => 1, error if error < 0 => error, _ => -EBUSY }
}
unsafe fn process_release_vm_checked_inner(
    vm: *mut c_void,
    refcount_offset: CULong,
    proc_offset: CULong,
    proc_mckfd_offset: CULong,
    proc_mckfd_lock_offset: CULong,
    mckfd_next_offset: CULong,
    mckfd_close_offset: CULong,
    vm_free_cb_offset: CULong,
    vm_opt_offset: CULong,
    vm_address_space_offset: CULong,
    proc_pid_offset: CULong,
    proc_vm_offset: CULong,
    vm_policy_tree_offset: CULong,
    policy_node_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    flush_fn: Option<ProcessVmActionFn>,
    free_ranges_fn: Option<ProcessVmActionFn>,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
    release_process_fn: Option<ProcessReleaseRoute>,
    policy_free_fn: Option<ProcessPolicyFreeFn>,
    free_vm_fn: Option<ProcessFreeFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let (Some(lock_fn), Some(unlock_fn), Some(flush_fn), Some(free_ranges_fn), Some(free_vm_fn)) =
        (lock_fn, unlock_fn, flush_fn, free_ranges_fn, free_vm_fn)
    else {
        return -EINVAL;
    };
    if detach_fn.is_none() || release_process_fn.is_none() || policy_free_fn.is_none() {
        return -EINVAL;
    }
    let proc = field_ptr(vm, proc_offset);
    if proc.is_null() {
        return -EINVAL;
    }
    match process_ref_dec_and_test_result(vm, refcount_offset, dec_fn) {
        0 => return 0,
        1 => {},
        error if error < 0 => return error,
        _ => return -EINVAL,
    }
    let lock_addr = (proc as CULong).wrapping_add(proc_mckfd_lock_offset);
    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mckfd_head = field_ptr(proc, proc_mckfd_offset);
    process_mckfd_close_all_result(mckfd_head, mckfd_next_offset, mckfd_close_offset);
    let _ = process_spin_unlock_result(lock_addr, irqstate, Some(unlock_fn));

    let free_cb = *(vm.cast::<u8>().wrapping_add(vm_free_cb_offset as usize)
        .cast::<Option<ProcessVmFreeCallback>>());
    if let Some(free_cb) = free_cb {
        let opt = field_ptr(vm, vm_opt_offset);
        free_cb(vm, opt);
    }
    flush_fn(vm);
    free_ranges_fn(vm);
    let nested = match release_process_fn.unwrap() {
        ProcessReleaseRoute::Existing(release) => {
            process_release_vm_detach_process_result(
                vm, vm_address_space_offset, proc_offset, proc_pid_offset, proc_vm_offset,
                detach_fn, Some(release),
            );
            0 // Legacy callback cannot report final Process destruction.
        },
        ProcessReleaseRoute::FinalChecked(release) => process_release_vm_detach_final_checked(
            vm, vm_address_space_offset, proc_offset, proc_pid_offset, proc_vm_offset,
            detach_fn.unwrap(), release,
        ),
    };
    let policy_root = vm.cast::<u8>().wrapping_add(vm_policy_tree_offset as usize).cast::<RbRoot>();
    process_vm_policy_drain_free_result(policy_root, policy_node_offset, policy_free_fn);
    free_vm_fn(vm);
    // No read of either dead allocation follows the callbacks. Existing
    // callers retain their original 0/1 contract; only the distinct checked
    // route can report 2 for final VM AND nested Process destruction.
    if nested < 0 { nested } else if nested == 1 { 2 } else { 1 }
}
unsafe fn process_release_vm_detach_final_checked(
    vm:*mut c_void,address_space_offset:CULong,proc_offset:CULong,
    pid_offset:CULong,proc_vm_offset:CULong,detach:ProcessDetachAddressSpaceFn,
    release:ProcessVmReleaseCheckedFn,
)->CInt {
    let address_space=field_ptr(vm,address_space_offset);
    let proc=field_ptr(vm,proc_offset);
    if proc.is_null(){return -EINVAL;}
    let pid=*(proc.cast::<u8>().add(pid_offset as usize).cast::<CInt>());
    let _=process_detach_address_space_pid_result(address_space,pid,Some(detach));
    *proc.cast::<u8>().add(proc_vm_offset as usize).cast::<*mut c_void>()=core::ptr::null_mut();
    release(proc)
}
pub unsafe extern "C" fn process_release_vm_detach_process_result(
    vm: *mut c_void,
    address_space_offset: CULong,
    proc_offset: CULong,
    pid_offset: CULong,
    proc_vm_offset: CULong,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
    release_fn: Option<ProcessReleaseProcessFn>,
) -> CInt {
    if vm.is_null() {
        return 0;
    }
    let (Some(detach_fn), Some(release_fn)) = (detach_fn, release_fn) else {
        return 0;
    };

    let vm_base = vm.cast::<u8>();
    let address_space = *(vm_base
        .wrapping_add(address_space_offset as usize)
        .cast::<*mut c_void>());
    let proc = *(vm_base
        .wrapping_add(proc_offset as usize)
        .cast::<*mut c_void>());
    if proc.is_null() {
        return 0;
    }

    let proc_base = proc.cast::<u8>();
    let pid = *(proc_base.wrapping_add(pid_offset as usize).cast::<CInt>());
    let _ = process_detach_address_space_pid_result(address_space, pid, Some(detach_fn));
    *(proc_base
        .wrapping_add(proc_vm_offset as usize)
        .cast::<*mut c_void>()) = core::ptr::null_mut();
    let _ = process_release_process_action_result(proc, Some(release_fn));
    1
}
pub unsafe extern "C" fn process_detach_address_space_pid_result(
    address_space: *mut c_void,
    pid: CInt,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
) -> CInt {
    let Some(detach) = detach_fn else {
        return -EINVAL;
    };

    detach(address_space, pid);
    0
}
pub unsafe extern "C" fn process_release_process_action_result(
    process: *mut c_void,
    release_fn: Option<ProcessReleaseProcessFn>,
) -> CInt {
    let Some(release) = release_fn else {
        return -EINVAL;
    };

    release(process);
    0
}
pub unsafe extern "C" fn process_vm_policy_drain_free_result(
    root: *mut RbRoot,
    node_offset: CULong,
    free_fn: Option<ProcessPolicyFreeFn>,
) -> CInt {
    if root.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut freed = 0;
    loop {
        let node = rb_first(root);
        if node.is_null() {
            break;
        }
        let policy = node
            .cast::<u8>()
            .wrapping_sub(node_offset as usize)
            .cast::<c_void>();
        rb_erase(node, root);
        let _ = process_policy_free_result(policy, Some(free_fn));
        freed += 1;
    }

    freed
}
pub unsafe extern "C" fn process_mckfd_close_all_result(
    head: *mut c_void,
    next_offset: CULong,
    close_offset: CULong,
) -> CInt {
    let mut current = head;
    let mut closed = 0;

    while !current.is_null() {
        let base = current.cast::<u8>();
        let close_slot = base.wrapping_add(close_offset as usize);
        let close_cb = *(close_slot.cast::<Option<ProcessMckfdCloseFn>>());
        if let Some(close_cb) = close_cb {
            let _ = close_cb(current, core::ptr::null_mut());
            closed += 1;
        }

        current = *(base
            .wrapping_add(next_offset as usize)
            .cast::<*mut c_void>());
    }

    closed
}
pub unsafe extern "C" fn process_policy_free_result(
    policy: *mut c_void,
    policy_free_fn: Option<ProcessPolicyFreeFn>,
) -> CInt {
    let Some(policy_free) = policy_free_fn else {
        return -EINVAL;
    };

    policy_free(policy);
    0
}

// Explicit platform/destructor adapters. Actual ownership/checked dispatch,
// decrement/destructor/VM cascade bodies above are production projections.
unsafe fn rb_first(root:*mut RbRoot)->*mut RbNode{assert!((*root).rb_node.is_null());core::ptr::null_mut()}
unsafe fn rb_erase(_: *mut RbNode,_:*mut RbRoot){panic!("fixture has no policy nodes")}
unsafe extern "C" fn process_flush_vm_bridge(_: *mut c_void){crate::phase5_tests::cascade_event(1);}
unsafe extern "C" fn process_free_all_ranges_bridge(_: *mut c_void){crate::phase5_tests::cascade_event(2);}
unsafe extern "C" fn process_detach_address_space_bridge(_: *mut c_void,pid:CInt){assert_eq!(pid,900);crate::phase5_tests::cascade_event(3);}
unsafe extern "C" fn process_policy_free_bridge(_: *mut c_void){panic!("fixture has no policy nodes")}
unsafe extern "C" fn process_free_vm_bridge(_: *mut c_void){crate::phase5_tests::vm_final();}
