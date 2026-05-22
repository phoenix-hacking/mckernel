use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::ptr::null_mut;

use crate::abi::CInt;

type CUInt = u32;

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

unsafe extern "C" {
    fn default_wake_function(
        entry: *mut WaitqEntry,
        mode: CUInt,
        flags: CInt,
        key: *mut c_void,
    ) -> CInt;
}

#[no_mangle]
pub unsafe extern "C" fn waitq_init(waitq: *mut Waitq) {
    (*waitq).lock.head_tail = 0;
    init_list_head(waitq_list(waitq));
}

#[no_mangle]
pub unsafe extern "C" fn waitq_init_entry(entry: *mut WaitqEntry, proc: *mut c_void) {
    (*entry).private = proc;
    (*entry).func = Some(default_wake_function);
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
