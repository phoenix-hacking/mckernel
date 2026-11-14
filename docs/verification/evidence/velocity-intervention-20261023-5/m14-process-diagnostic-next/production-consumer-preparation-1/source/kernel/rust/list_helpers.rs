#![allow(non_snake_case)]

use core::ptr::{read_volatile, write_volatile};

use crate::abi::CInt;

#[repr(C)]
pub struct ListHead {
    pub next: *mut ListHead,
    pub prev: *mut ListHead,
}

const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<ListHead>() == 16);
    assert!(align_of::<ListHead>() == 8);
    assert!(offset_of!(ListHead, next) == 0);
    assert!(offset_of!(ListHead, prev) == 8);
};

#[inline(always)]
unsafe fn list_next(list: *const ListHead) -> *mut ListHead {
    read_volatile(&(*list).next)
}

#[inline(always)]
unsafe fn list_prev(list: *const ListHead) -> *mut ListHead {
    read_volatile(&(*list).prev)
}

#[inline(always)]
unsafe fn set_next(list: *mut ListHead, value: *mut ListHead) {
    write_volatile(&mut (*list).next, value);
}

#[inline(always)]
unsafe fn set_prev(list: *mut ListHead, value: *mut ListHead) {
    write_volatile(&mut (*list).prev, value);
}

#[no_mangle]
pub unsafe extern "C" fn INIT_LIST_HEAD(list: *mut ListHead) {
    set_next(list, list);
    set_prev(list, list);
}

#[no_mangle]
pub unsafe extern "C" fn __list_add(new: *mut ListHead, prev: *mut ListHead, next: *mut ListHead) {
    set_prev(next, new);
    set_next(new, next);
    set_prev(new, prev);
    set_next(prev, new);
}

#[no_mangle]
pub unsafe extern "C" fn list_add(new: *mut ListHead, head: *mut ListHead) {
    __list_add(new, head, list_next(head));
}

#[no_mangle]
pub unsafe extern "C" fn list_add_tail(new: *mut ListHead, head: *mut ListHead) {
    __list_add(new, list_prev(head), head);
}

#[no_mangle]
pub unsafe extern "C" fn __list_del(prev: *mut ListHead, next: *mut ListHead) {
    set_prev(next, prev);
    set_next(prev, next);
}

#[no_mangle]
pub unsafe extern "C" fn __list_del_entry(entry: *mut ListHead) {
    __list_del(list_prev(entry), list_next(entry));
}

#[no_mangle]
pub unsafe extern "C" fn list_del(entry: *mut ListHead) {
    __list_del_entry(entry);
    set_next(entry, LIST_POISON1 as *mut ListHead);
    set_prev(entry, LIST_POISON2 as *mut ListHead);
}

#[no_mangle]
pub unsafe extern "C" fn list_replace(old: *mut ListHead, new: *mut ListHead) {
    let next = list_next(old);
    let prev = list_prev(old);

    set_next(new, next);
    set_prev(next, new);
    set_prev(new, prev);
    set_next(prev, new);
}

#[no_mangle]
pub unsafe extern "C" fn list_replace_init(old: *mut ListHead, new: *mut ListHead) {
    list_replace(old, new);
    INIT_LIST_HEAD(old);
}

#[no_mangle]
pub unsafe extern "C" fn list_del_init(entry: *mut ListHead) {
    __list_del_entry(entry);
    INIT_LIST_HEAD(entry);
}

#[no_mangle]
pub unsafe extern "C" fn list_move(list: *mut ListHead, head: *mut ListHead) {
    __list_del_entry(list);
    list_add(list, head);
}

#[no_mangle]
pub unsafe extern "C" fn list_move_tail(list: *mut ListHead, head: *mut ListHead) {
    __list_del_entry(list);
    list_add_tail(list, head);
}

#[no_mangle]
pub unsafe extern "C" fn list_is_last(list: *const ListHead, head: *const ListHead) -> CInt {
    (list_next(list) == head as *mut ListHead) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn list_empty(head: *const ListHead) -> CInt {
    (list_next(head) == head as *mut ListHead) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn list_empty_careful(head: *const ListHead) -> CInt {
    let next = list_next(head);

    (next == head as *mut ListHead && next == list_prev(head)) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn list_rotate_left(head: *mut ListHead) {
    if list_empty(head) == 0 {
        let first = list_next(head);
        list_move_tail(first, head);
    }
}

#[no_mangle]
pub unsafe extern "C" fn list_is_singular(head: *const ListHead) -> CInt {
    (list_empty(head) == 0 && list_next(head) == list_prev(head)) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn __list_cut_position(
    list: *mut ListHead,
    head: *mut ListHead,
    entry: *mut ListHead,
) {
    let new_first = list_next(entry);

    set_next(list, list_next(head));
    set_prev(list_next(list), list);
    set_prev(list, entry);
    set_next(entry, list);
    set_next(head, new_first);
    set_prev(new_first, head);
}

#[no_mangle]
pub unsafe extern "C" fn list_cut_position(
    list: *mut ListHead,
    head: *mut ListHead,
    entry: *mut ListHead,
) {
    if list_empty(head) != 0 {
        return;
    }
    if list_is_singular(head) != 0 && list_next(head) != entry && head != entry {
        return;
    }
    if entry == head {
        INIT_LIST_HEAD(list);
    } else {
        __list_cut_position(list, head, entry);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __list_splice(
    list: *const ListHead,
    prev: *mut ListHead,
    next: *mut ListHead,
) {
    let first = list_next(list);
    let last = list_prev(list);

    set_prev(first, prev);
    set_next(prev, first);
    set_next(last, next);
    set_prev(next, last);
}

#[no_mangle]
pub unsafe extern "C" fn list_splice(list: *const ListHead, head: *mut ListHead) {
    if list_empty(list) == 0 {
        __list_splice(list, head, list_next(head));
    }
}

#[no_mangle]
pub unsafe extern "C" fn list_splice_tail(list: *mut ListHead, head: *mut ListHead) {
    if list_empty(list) == 0 {
        __list_splice(list, list_prev(head), head);
    }
}

#[no_mangle]
pub unsafe extern "C" fn list_splice_init(list: *mut ListHead, head: *mut ListHead) {
    if list_empty(list) == 0 {
        __list_splice(list, head, list_next(head));
        INIT_LIST_HEAD(list);
    }
}

#[no_mangle]
pub unsafe extern "C" fn list_splice_tail_init(list: *mut ListHead, head: *mut ListHead) {
    if list_empty(list) == 0 {
        __list_splice(list, list_prev(head), head);
        INIT_LIST_HEAD(list);
    }
}
