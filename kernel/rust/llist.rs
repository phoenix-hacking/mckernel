use core::ptr::{null_mut, read_volatile};
use core::sync::atomic::{AtomicPtr, Ordering};

#[repr(C)]
pub struct LListHead {
    first: *mut LListNode,
}

#[repr(C)]
pub struct LListNode {
    next: *mut LListNode,
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<LListHead>() == 8);
    assert!(align_of::<LListHead>() == 8);
    assert!(offset_of!(LListHead, first) == 0);
    assert!(size_of::<LListNode>() == 8);
    assert!(align_of::<LListNode>() == 8);
    assert!(offset_of!(LListNode, next) == 0);
};

#[inline(always)]
unsafe fn head_first(head: *mut LListHead) -> &'static AtomicPtr<LListNode> {
    AtomicPtr::from_ptr(&raw mut (*head).first)
}

#[no_mangle]
pub unsafe extern "C" fn llist_add_batch(
    new_first: *mut LListNode,
    new_last: *mut LListNode,
    head: *mut LListHead,
) -> bool {
    let first_slot = head_first(head);
    let mut first = first_slot.load(Ordering::Acquire);

    loop {
        (*new_last).next = first;
        match first_slot.compare_exchange(first, new_first, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(_) => return first.is_null(),
            Err(actual) => first = actual,
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn llist_del_first(head: *mut LListHead) -> *mut LListNode {
    let first_slot = head_first(head);
    let mut entry = first_slot.load(Ordering::Acquire);

    loop {
        if entry.is_null() {
            return null_mut();
        }

        let old_entry = entry;
        let next = read_volatile(&(*entry).next);
        match first_slot.compare_exchange(old_entry, next, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(_) => return old_entry,
            Err(actual) => entry = actual,
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn llist_reverse_order(mut head: *mut LListNode) -> *mut LListNode {
    let mut new_head = null_mut();

    while !head.is_null() {
        let tmp = head;
        head = (*head).next;
        (*tmp).next = new_head;
        new_head = tmp;
    }

    new_head
}
