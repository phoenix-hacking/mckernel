use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::ptr::null_mut;

use crate::abi::{CInt, CpuLocalVar};
use crate::spinlock_helpers::{
    __ihk_mc_spinlock_lock_noirq, __ihk_mc_spinlock_unlock_noirq, IhkSpinlock as TicketSpinlock,
};

type CUInt = u32;
const PS_RUNNING: CInt = 0x1;
const PS_NORMAL: CInt = 0x2 | 0x4;

#[repr(C)]
pub(crate) struct IhkSpinlock {
    head_tail: CUInt,
}

#[repr(C)]
pub(crate) struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}

#[repr(C)]
pub(crate) struct Waitq {
    lock: IhkSpinlock,
    waitq: ListHead,
}

type WaitqFunc = Option<unsafe extern "C" fn(*mut WaitqEntry, CUInt, CInt, *mut c_void) -> CInt>;

#[repr(C)]
pub(crate) struct WaitqEntry {
    link: ListHead,
    private: *mut c_void,
    flags: CUInt,
    func: WaitqFunc,
}

const _: () = {
    assert!(size_of::<IhkSpinlock>() == 4);
    assert!(align_of::<IhkSpinlock>() == 4);
    assert!(offset_of!(IhkSpinlock, head_tail) == 0);
    assert!(size_of::<ListHead>() == 16);
    assert!(align_of::<ListHead>() == 8);
    assert!(offset_of!(ListHead, prev) == 8);
    assert!(size_of::<Waitq>() == 24);
    assert!(align_of::<Waitq>() == 8);
    assert!(offset_of!(Waitq, lock) == 0);
    assert!(offset_of!(Waitq, waitq) == 8);
    assert!(size_of::<WaitqEntry>() == 40);
    assert!(align_of::<WaitqEntry>() == 8);
    assert!(offset_of!(WaitqEntry, link) == 0);
    assert!(offset_of!(WaitqEntry, private) == 16);
    assert!(offset_of!(WaitqEntry, flags) == 24);
    assert!(offset_of!(WaitqEntry, func) == 32);
};

#[inline(always)]
unsafe fn init_list_head(list: *mut ListHead) {
    (*list).next = list;
    (*list).prev = list;
}

#[inline(always)]
unsafe fn list_add_between(new: *mut ListHead, prev: *mut ListHead, next: *mut ListHead) {
    (*next).prev = new;
    (*new).next = next;
    (*new).prev = prev;
    (*prev).next = new;
}

#[inline(always)]
unsafe fn list_add(new: *mut ListHead, head: *mut ListHead) {
    list_add_between(new, head, (*head).next);
}

#[inline(always)]
unsafe fn list_add_tail(new: *mut ListHead, head: *mut ListHead) {
    list_add_between(new, (*head).prev, head);
}

#[inline(always)]
unsafe fn list_del_entry(entry: *mut ListHead) {
    (*(*entry).next).prev = (*entry).prev;
    (*(*entry).prev).next = (*entry).next;
}

#[inline(always)]
unsafe fn list_del_init(entry: *mut ListHead) {
    list_del_entry(entry);
    init_list_head(entry);
}

#[inline(always)]
unsafe fn waitq_list(waitq: *mut Waitq) -> *mut ListHead {
    &raw mut (*waitq).waitq
}

#[inline(always)]
unsafe fn entry_link(entry: *mut WaitqEntry) -> *mut ListHead {
    &raw mut (*entry).link
}

#[inline(always)]
unsafe fn waitq_entry_from_link(link: *mut ListHead) -> *mut WaitqEntry {
    (link as *mut u8).sub(offset_of!(WaitqEntry, link)) as *mut WaitqEntry
}

#[inline(always)]
unsafe fn waitq_lock(waitq: *mut Waitq) -> *mut TicketSpinlock {
    &raw mut (*waitq).lock as *mut TicketSpinlock
}

#[inline(always)]
unsafe fn list_empty(head: *mut ListHead) -> bool {
    (*head).next == head
}

unsafe extern "C" {
    fn get_cpu_local_var_result(id: CInt) -> *mut CpuLocalVar;
    fn ihk_mc_get_processor_id() -> CInt;
    fn sched_wakeup_thread(thread: *mut c_void, valid_states: CInt) -> CInt;
    fn sched_wakeup_thread_locked(thread: *mut c_void, valid_states: CInt) -> CInt;
    fn schedule();
}

#[inline(always)]
unsafe fn current_thread() -> *mut c_void {
    let cpu = ihk_mc_get_processor_id();
    let v = get_cpu_local_var_result(cpu);
    (*v).current.cast::<c_void>()
}

#[no_mangle]
pub unsafe extern "C" fn default_wake_function(
    entry: *mut WaitqEntry,
    _mode: CUInt,
    _flags: CInt,
    _key: *mut c_void,
) -> CInt {
    sched_wakeup_thread((*entry).private, PS_NORMAL)
}

#[no_mangle]
pub unsafe extern "C" fn locked_wake_function(
    entry: *mut WaitqEntry,
    _mode: CUInt,
    _flags: CInt,
    _key: *mut c_void,
) -> CInt {
    sched_wakeup_thread_locked((*entry).private, PS_NORMAL)
}

#[no_mangle]
pub unsafe extern "C" fn waitq_init(waitq: *mut Waitq) {
    (*waitq).lock.head_tail = 0;
    init_list_head(waitq_list(waitq));
}

#[no_mangle]
pub unsafe extern "C" fn waitq_init_entry(entry: *mut WaitqEntry, proc: *mut c_void) {
    (*entry).private = proc;
    (*entry).flags = 0;
    (*entry).func = Some(default_wake_function);
    init_list_head(entry_link(entry));
}

#[no_mangle]
pub unsafe extern "C" fn waitq_init_locked_entry(entry: *mut WaitqEntry, proc: *mut c_void) {
    (*entry).private = proc;
    (*entry).flags = 0;
    (*entry).func = Some(locked_wake_function);
    init_list_head(entry_link(entry));
}

#[no_mangle]
pub unsafe extern "C" fn waitq_add_entry_locked(waitq: *mut Waitq, entry: *mut WaitqEntry) {
    list_add_tail(entry_link(entry), waitq_list(waitq));
}

#[no_mangle]
pub unsafe extern "C" fn waitq_remove_entry_locked(waitq: *mut Waitq, entry: *mut WaitqEntry) {
    let _ = waitq;
    list_del_init(entry_link(entry));
}

#[no_mangle]
pub unsafe extern "C" fn waitq_wake_nr_locked(waitq: *mut Waitq, nr: CInt) -> CInt {
    let head = waitq_list(waitq);
    let mut pos = (*head).next;
    let mut count: CInt = 0;

    while pos != head {
        let entry = waitq_entry_from_link(pos);

        count += 1;
        if count > nr {
            break;
        }

        if let Some(func) = (*entry).func {
            func(entry, 0, 0, null_mut());
        }

        pos = (*pos).next;
    }

    count - 1
}

#[no_mangle]
pub extern "C" fn waitq_wake_schedule_needed_result(count: CInt) -> CInt {
    (count > 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn waitq_active_result(waitq: *mut Waitq) -> CInt {
    let lock = unsafe { waitq_lock(waitq) };

    unsafe {
        __ihk_mc_spinlock_lock_noirq(lock);
    }
    let active = unsafe { !list_empty(waitq_list(waitq)) } as CInt;
    unsafe {
        __ihk_mc_spinlock_unlock_noirq(lock);
    }
    active
}

#[no_mangle]
pub unsafe extern "C" fn waitq_active(waitq: *mut Waitq) -> CInt {
    waitq_active_result(waitq)
}

#[no_mangle]
pub unsafe extern "C" fn waitq_add_entry_result(waitq: *mut Waitq, entry: *mut WaitqEntry) {
    let lock = unsafe { waitq_lock(waitq) };

    unsafe {
        __ihk_mc_spinlock_lock_noirq(lock);
        waitq_add_entry_locked(waitq, entry);
        __ihk_mc_spinlock_unlock_noirq(lock);
    }
}

#[no_mangle]
pub unsafe extern "C" fn waitq_add_entry(waitq: *mut Waitq, entry: *mut WaitqEntry) {
    waitq_add_entry_result(waitq, entry);
}

#[no_mangle]
pub unsafe extern "C" fn waitq_remove_entry_result(waitq: *mut Waitq, entry: *mut WaitqEntry) {
    let lock = unsafe { waitq_lock(waitq) };

    unsafe {
        __ihk_mc_spinlock_lock_noirq(lock);
        waitq_remove_entry_locked(waitq, entry);
        __ihk_mc_spinlock_unlock_noirq(lock);
    }
}

#[no_mangle]
pub unsafe extern "C" fn waitq_remove_entry(waitq: *mut Waitq, entry: *mut WaitqEntry) {
    waitq_remove_entry_result(waitq, entry);
}

#[no_mangle]
pub unsafe extern "C" fn waitq_prepare_to_wait_result(
    waitq: *mut Waitq,
    entry: *mut WaitqEntry,
    state: CInt,
    current: *mut c_void,
    status_offset: usize,
) {
    let lock = unsafe { waitq_lock(waitq) };

    unsafe {
        __ihk_mc_spinlock_lock_noirq(lock);
        if list_empty(entry_link(entry)) {
            list_add(entry_link(entry), waitq_list(waitq));
        }
        *((current as *mut u8).add(status_offset) as *mut CInt) = state;
        __ihk_mc_spinlock_unlock_noirq(lock);
    }
}

#[no_mangle]
pub unsafe extern "C" fn waitq_prepare_to_wait(
    waitq: *mut Waitq,
    entry: *mut WaitqEntry,
    state: CInt,
) {
    waitq_prepare_to_wait_result(
        waitq,
        entry,
        state,
        current_thread(),
        core::mem::offset_of!(crate::abi::Thread, status),
    );
}

#[no_mangle]
pub unsafe extern "C" fn waitq_finish_wait_result(
    waitq: *mut Waitq,
    entry: *mut WaitqEntry,
    current: *mut c_void,
    status_offset: usize,
    running_state: CInt,
) {
    unsafe {
        *((current as *mut u8).add(status_offset) as *mut CInt) = running_state;
        waitq_remove_entry_result(waitq, entry);
    }
}

#[no_mangle]
pub unsafe extern "C" fn waitq_finish_wait(waitq: *mut Waitq, entry: *mut WaitqEntry) {
    waitq_finish_wait_result(
        waitq,
        entry,
        current_thread(),
        core::mem::offset_of!(crate::abi::Thread, status),
        PS_RUNNING,
    );
}

#[no_mangle]
pub unsafe extern "C" fn waitq_wakeup_result(waitq: *mut Waitq) {
    let lock = unsafe { waitq_lock(waitq) };

    unsafe {
        __ihk_mc_spinlock_lock_noirq(lock);
    }

    let head = unsafe { waitq_list(waitq) };
    let mut pos = unsafe { (*head).next };
    while pos != head {
        let entry = unsafe { waitq_entry_from_link(pos) };
        if let Some(func) = unsafe { (*entry).func } {
            unsafe {
                func(entry, 0, 0, null_mut());
            }
        }
        pos = unsafe { (*pos).next };
    }

    unsafe {
        __ihk_mc_spinlock_unlock_noirq(lock);
    }
}

#[no_mangle]
pub unsafe extern "C" fn waitq_wakeup(waitq: *mut Waitq) {
    waitq_wakeup_result(waitq);
}

#[no_mangle]
pub unsafe extern "C" fn waitq_wake_nr_result(
    waitq: *mut Waitq,
    nr: CInt,
    schedule_fn: Option<unsafe extern "C" fn()>,
) -> CInt {
    let lock = unsafe { waitq_lock(waitq) };

    unsafe {
        __ihk_mc_spinlock_lock_noirq(lock);
    }
    let count = unsafe { waitq_wake_nr_locked(waitq, nr) };
    unsafe {
        __ihk_mc_spinlock_unlock_noirq(lock);
    }

    if waitq_wake_schedule_needed_result(count) != 0 {
        if let Some(schedule) = schedule_fn {
            unsafe {
                schedule();
            }
        }
    }

    count
}

#[no_mangle]
pub unsafe extern "C" fn waitq_wake_nr(waitq: *mut Waitq, nr: CInt) -> CInt {
    waitq_wake_nr_result(waitq, nr, Some(schedule))
}
