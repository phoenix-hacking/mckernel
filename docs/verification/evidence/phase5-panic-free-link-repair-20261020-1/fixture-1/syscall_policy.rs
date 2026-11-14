use core::ffi::c_void;
use crate::abi::CInt;const WNOWAIT:i32=0x01000000;

pub extern "C" fn wait_reap_needed_result(options: CInt) -> CInt {
    if (options & WNOWAIT) == 0 {
        1
    } else {
        0
    }
}

use crate::abi::*;use core::ptr::{read_volatile,write_volatile};
const NS_PER_SEC:i64=1000000000;const EINVAL:i32=22;
type WaitLockUnlockFn=unsafe extern "C" fn(*mut core::ffi::c_void,*mut core::ffi::c_void);
type WaitListDetachFn=unsafe extern "C" fn(*mut core::ffi::c_void);
type WaitThreadSideEffectFn=unsafe extern "C" fn(*mut core::ffi::c_void);

#[repr(C)]
pub struct WaitZombieOffsets {
    pub thread_ptrace_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_ppid_parent_offset: SizeT,
    pub proc_parent_offset: SizeT,
    pub proc_status_offset: SizeT,
    pub proc_group_exit_status_offset: SizeT,
    pub proc_nowait_offset: SizeT,
    pub proc_update_lock_offset: SizeT,
    pub proc_children_lock_offset: SizeT,
    pub proc_threads_lock_offset: SizeT,
    pub proc_siblings_list_offset: SizeT,
    pub proc_children_list_offset: SizeT,
    pub proc_main_thread_offset: SizeT,
    pub proc_stime_offset: SizeT,
    pub proc_utime_offset: SizeT,
    pub proc_stime_children_offset: SizeT,
    pub proc_utime_children_offset: SizeT,
    pub proc_maxrss_offset: SizeT,
    pub proc_maxrss_children_offset: SizeT,
}

unsafe fn field_ptr<T>(base: *mut u8, offset: SizeT) -> *mut T {
    base.add(offset).cast::<T>()
}

pub extern "C" fn getrusage_maxrss_kb_result(maxrss: CLong) -> CLong {
    maxrss / 1024
}

pub unsafe extern "C" fn getrusage_fill_timespec_result(
    usage: *mut RUsage,
    utime_sec: CLong,
    utime_nsec: CLong,
    stime_sec: CLong,
    stime_nsec: CLong,
    maxrss: CLong,
) {
    (*usage).ru_utime.tv_sec = utime_sec;
    (*usage).ru_utime.tv_usec = utime_nsec / 1000;
    (*usage).ru_stime.tv_sec = stime_sec;
    (*usage).ru_stime.tv_usec = stime_nsec / 1000;
    (*usage).ru_maxrss = getrusage_maxrss_kb_result(maxrss);
}

unsafe fn read_timespec(base: *mut u8, offset: SizeT) -> TimeSpec {
    let ts = field_ptr::<TimeSpec>(base, offset);
    TimeSpec {
        tv_sec: read_volatile(&(*ts).tv_sec),
        tv_nsec: read_volatile(&(*ts).tv_nsec),
    }
}

unsafe fn write_timespec(base: *mut u8, offset: SizeT, value: &TimeSpec) {
    let ts = field_ptr::<TimeSpec>(base, offset);
    write_volatile(&mut (*ts).tv_sec, value.tv_sec);
    write_volatile(&mut (*ts).tv_nsec, value.tv_nsec);
}

fn timespec_add(dst: &mut TimeSpec, src: &TimeSpec) {
    dst.tv_sec += src.tv_sec;
    dst.tv_nsec += src.tv_nsec;
    while dst.tv_nsec >= NS_PER_SEC {
        dst.tv_sec += 1;
        dst.tv_nsec -= NS_PER_SEC;
    }
}

unsafe fn wait_process_fill_rusage(
    child_proc: *mut u8,
    usage: *mut c_void,
    offsets: &WaitZombieOffsets,
) {
    if usage.is_null() {
        return;
    }
    let utime = read_timespec(child_proc, offsets.proc_utime_offset);
    let stime = read_timespec(child_proc, offsets.proc_stime_offset);
    let maxrss = read_volatile(field_ptr::<CLong>(child_proc, offsets.proc_maxrss_offset));
    getrusage_fill_timespec_result(
        usage.cast::<RUsage>(),
        utime.tv_sec,
        utime.tv_nsec,
        stime.tv_sec,
        stime.tv_nsec,
        maxrss,
    );
}

unsafe fn wait_process_accumulate_child_rusage(
    parent_proc: *mut u8,
    child_proc: *mut u8,
    offsets: &WaitZombieOffsets,
) {
    let mut stime_children = read_timespec(parent_proc, offsets.proc_stime_children_offset);
    let child_stime = read_timespec(child_proc, offsets.proc_stime_offset);
    let child_stime_children = read_timespec(child_proc, offsets.proc_stime_children_offset);
    timespec_add(&mut stime_children, &child_stime);
    timespec_add(&mut stime_children, &child_stime_children);
    write_timespec(
        parent_proc,
        offsets.proc_stime_children_offset,
        &stime_children,
    );

    let mut utime_children = read_timespec(parent_proc, offsets.proc_utime_children_offset);
    let child_utime = read_timespec(child_proc, offsets.proc_utime_offset);
    let child_utime_children = read_timespec(child_proc, offsets.proc_utime_children_offset);
    timespec_add(&mut utime_children, &child_utime);
    timespec_add(&mut utime_children, &child_utime_children);
    write_timespec(
        parent_proc,
        offsets.proc_utime_children_offset,
        &utime_children,
    );

    let maxrss_ptr = field_ptr::<CLong>(parent_proc, offsets.proc_maxrss_children_offset);
    let mut maxrss_children = read_volatile(maxrss_ptr);
    let child_maxrss = read_volatile(field_ptr::<CLong>(child_proc, offsets.proc_maxrss_offset));
    if child_maxrss > maxrss_children {
        maxrss_children = child_maxrss;
        write_volatile(maxrss_ptr, maxrss_children);
    }
    let child_maxrss_children = read_volatile(field_ptr::<CLong>(
        child_proc,
        offsets.proc_maxrss_children_offset,
    ));
    if child_maxrss_children > maxrss_children {
        write_volatile(maxrss_ptr, child_maxrss_children);
    }
}

// Exact changed production wait branch. The legacy fallback is deliberately
// excluded: these tests cover only the typed owned-child branch above it.
pub unsafe fn actual_owned_wait_branch(thread:*mut core::ffi::c_void,parent_proc:*mut core::ffi::c_void,
 child_proc:*mut core::ffi::c_void,child_pid:i32,options:i32,ret:i32,rusage:*mut core::ffi::c_void,
 offsets:&WaitZombieOffsets,parent_children_lock:*mut core::ffi::c_void,parent_children_lock_node:*mut core::ffi::c_void,
 parent_update_lock_node:*mut core::ffi::c_void,lock_fn:WaitLockUnlockFn,unlock_fn:WaitLockUnlockFn,
 list_detach_fn:WaitListDetachFn,release_process_fn:WaitThreadSideEffectFn)->i32{
 let parent=parent_proc.cast::<u8>();let child=child_proc.cast::<u8>();
    let owned_reap=crate::fork_control_guest::runnable::prepare_wait_reap(
        thread.cast(),parent_proc.cast(),child_proc.cast(),child_pid,options,ret,
    );
    if let crate::fork_control_guest::runnable::WaitReap::Retained(error)=owned_reap {
        unlock_fn(parent_children_lock,parent_children_lock_node);return error;
    }
    if let crate::fork_control_guest::runnable::WaitReap::Prepared(handle)=owned_reap {
        if parent_update_lock_node.is_null(){
            crate::fork_control_guest::runnable::finish_wait_reap(handle,-EINVAL);
            unlock_fn(parent_children_lock,parent_children_lock_node);return -EINVAL;
        }
        let parent_update_lock=field_ptr::<c_void>(parent,offsets.proc_update_lock_offset);
        lock_fn(parent_update_lock,parent_update_lock_node);
        wait_process_accumulate_child_rusage(parent,child,offsets);
        wait_process_fill_rusage(child,rusage,offsets);
        unlock_fn(parent_update_lock,parent_update_lock_node);
        let siblings=field_ptr::<crate::abi::AbiListHead>(child,offsets.proc_siblings_list_offset);
        list_detach_fn(siblings.cast());
        (*siblings).next=siblings;(*siblings).prev=siblings;
        unlock_fn(parent_children_lock,parent_children_lock_node);
        let removed=crate::process_helpers::unpublish_waited_process(child_proc.cast());
        if removed==0{release_process_fn(child_proc);}
        crate::fork_control_guest::runnable::finish_wait_reap(handle,removed);
        return ret;
    }


 -22 // not an owned consuming wait; original fallback not projected
}
