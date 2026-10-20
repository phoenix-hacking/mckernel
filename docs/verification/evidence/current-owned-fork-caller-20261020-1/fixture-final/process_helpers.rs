use core::ffi::c_void;
use core::mem::offset_of;
use core::sync::atomic::{AtomicI32,Ordering};
use crate::abi::{CInt,CULong,Thread,IhkAtomic,AbiListHead};
use core::ptr::write_volatile;
const EINVAL:i32=22;
unsafe extern "C" fn process_release_thread_profile_bridge(_: *mut c_void, _: *mut c_void){crate::unexpected_destructor();}
unsafe extern "C" fn process_procfs_delete_thread_bridge(_: *mut c_void){crate::unexpected_destructor();}
unsafe extern "C" fn process_destroy_thread_bridge(_: *mut c_void){crate::unexpected_destructor();}
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