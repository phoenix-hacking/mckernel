use core::ffi::c_void;
use core::ptr::null_mut;
use core::mem::offset_of;
use core::sync::atomic::{AtomicI32,Ordering};
use crate::abi::*;
use crate::rbtree::{rb_first,rb_erase,RbRoot,RbNode};
const EINVAL:CInt=22;

type ProcessCurrentResourceSetFn = unsafe extern "C" fn() -> *mut c_void;

type ProcessDetachAddressSpaceFn = unsafe extern "C" fn(*mut c_void, CInt);

type ProcessFreeFn = unsafe extern "C" fn(*mut c_void);

type ProcessMckfdCloseFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;

type ProcessMckfdFreeFn = unsafe extern "C" fn(*mut c_void);

type ProcessPolicyFreeFn = unsafe extern "C" fn(*mut c_void);

type ProcessProcessActionFn = unsafe extern "C" fn(*mut c_void);

type ProcessRefDecAndTestFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;

type ProcessReleaseProcessFn = unsafe extern "C" fn(*mut c_void);

type ProcessResourceProcessActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void);

type ProcessResourceSetActionFn = unsafe extern "C" fn(*mut c_void);

type ProcessSpinLockFn = unsafe extern "C" fn(CULong) -> CULong;

type ProcessSpinUnlockFn = unsafe extern "C" fn(CULong, CULong);

type ProcessThreadActionFn = unsafe extern "C" fn(*mut c_void);

type ProcessVmActionFn = unsafe extern "C" fn(*mut c_void);

type ProcessVmFreeCallback = unsafe extern "C" fn(*mut c_void, *mut c_void);

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

pub unsafe extern "C" fn process_free_callback_result(
    ptr: *mut c_void,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    #[cfg(f03_perf_owner_protocol)]
    unsafe { crate::f03_perf_owner::retire_process_before_free(ptr.cast()); }
    free(ptr);
    0
}

pub extern "C" fn process_release_vm_should_run_free_cb_result(free_cb_addr: CULong) -> CInt {
    (free_cb_addr != 0) as CInt
}

pub unsafe extern "C" fn process_mckfd_pop_head_result(headp: *mut *mut c_void) -> *mut c_void {
    if headp.is_null() {
        return core::ptr::null_mut();
    }

    let current = *headp;
    if current.is_null() {
        return core::ptr::null_mut();
    }

    let next_slot = current.cast::<*mut c_void>();
    *headp = *next_slot;
    *next_slot = core::ptr::null_mut();
    current
}

pub unsafe extern "C" fn process_mckfd_close_all_result(
    head: *mut c_void,
    next_offset: CULong,
    close_offset: CULong,
) -> CInt {
    let mut current=head;
    let mut closed=0;
    while !current.is_null(){
        let base=current.cast::<u8>();
        #[cfg(f03_perf_owner_protocol)]
        {
            match unsafe{crate::f03_perf_owner::vm_mark_close_locked(current.cast())}{
                Ok(true)=>{closed+=1;current=*(base.add(next_offset as usize).cast::<*mut c_void>());continue;},
                Ok(false)=>{},Err(error)=>return error,
            }
        }
        let close_cb=*(base.add(close_offset as usize).cast::<Option<ProcessMckfdCloseFn>>());
        if let Some(close_cb)=close_cb{let _=close_cb(current,null_mut());closed+=1;}
        current=*(base.add(next_offset as usize).cast::<*mut c_void>());
    }
    closed
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

pub unsafe extern "C" fn process_mckfd_free_result(
    fdp: *mut c_void,
    free_fn: Option<ProcessMckfdFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return 0;
    };

    #[cfg(f03_perf_owner_protocol)]
    match crate::f03_perf_owner::retire_process_descriptor(fdp.cast::<crate::abi::Mckfd>(), free) {
        Ok(true) => return 1, // logically drained; last real pin owns final free
        Ok(false) => {},     // original unregistered/nonperf callback path
        Err(error) => return error, // keep the actual managed outcome retained
    }
    free(fdp);
    1
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

pub unsafe extern "C" fn process_vm_free_cb_result(
    vm: *mut c_void,
    opt: *mut c_void,
    free_cb: Option<ProcessVmFreeCallback>,
) -> CInt {
    let Some(free_cb) = free_cb else {
        return 0;
    };

    free_cb(vm, opt);
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

    #[cfg(f03_perf_owner_protocol)]
    unsafe { crate::f03_perf_owner::retire_process_before_free(proc.cast()); }

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

unsafe fn field_ptr(base: *mut c_void, offset: CULong) -> *mut c_void {
    *(base
        .cast::<u8>()
        .wrapping_add(offset as usize)
        .cast::<*mut c_void>())
}

pub unsafe extern "C" fn process_release_vm_body_result(
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
    release_process_fn: Option<ProcessReleaseProcessFn>,
    policy_free_fn: Option<ProcessPolicyFreeFn>,
    free_vm_fn: Option<ProcessFreeFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(flush_fn) = flush_fn else {
        return -EINVAL;
    };
    let Some(free_ranges_fn) = free_ranges_fn else {
        return -EINVAL;
    };
    let Some(free_vm_fn) = free_vm_fn else {
        return -EINVAL;
    };

    if process_ref_release_should_destroy_result(process_ref_dec_and_test_result(
        vm,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let proc = field_ptr(vm, proc_offset);
    if proc.is_null() {
        return -EINVAL;
    }

    let lock_addr = (proc as CULong).wrapping_add(proc_mckfd_lock_offset);
    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mckfd_head = field_ptr(proc, proc_mckfd_offset);
    let close_result=process_mckfd_close_all_result(mckfd_head,mckfd_next_offset,mckfd_close_offset);
    let _ = process_spin_unlock_result(lock_addr,irqstate,Some(unlock_fn));
    #[cfg(f03_perf_owner_protocol)]
    if close_result<0{return close_result;} // retain exact final-VM debt; no callback/free/retry
    #[cfg(not(f03_perf_owner_protocol))]
    let _=close_result;

    let free_cb_slot = vm
        .cast::<u8>()
        .wrapping_add(vm_free_cb_offset as usize)
        .cast::<Option<ProcessVmFreeCallback>>();
    let free_cb = *free_cb_slot;
    if process_release_vm_should_run_free_cb_result(free_cb.map_or(0, |f| f as usize as CULong))
        != 0
    {
        let opt = field_ptr(vm, vm_opt_offset);
        let _ = process_vm_free_cb_result(vm, opt, free_cb);
    }

    let _ = process_vm_action_result(vm, Some(flush_fn));
    let _ = process_vm_action_result(vm, Some(free_ranges_fn));

    process_release_vm_detach_process_result(
        vm,
        vm_address_space_offset,
        proc_offset,
        proc_pid_offset,
        proc_vm_offset,
        detach_fn,
        release_process_fn,
    );

    let policy_root = vm
        .cast::<u8>()
        .wrapping_add(vm_policy_tree_offset as usize)
        .cast::<RbRoot>();
    process_vm_policy_drain_free_result(policy_root, policy_node_offset, policy_free_fn);
    let _ = process_free_callback_result(vm, Some(free_vm_fn));
    1
}

include!("../process_lower_bindings.rs");
