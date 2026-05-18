use core::mem::{align_of, offset_of, size_of};
use core::ptr::{read_volatile, write_volatile};

use crate::abi::CInt;

#[repr(C)]
pub(crate) struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}

#[repr(C)]
pub(crate) struct PlistHead {
    prio_list: ListHead,
    node_list: ListHead,
}

#[repr(C)]
pub(crate) struct PlistNode {
    prio: CInt,
    plist: PlistHead,
}

const PLIST_PRIO_LIST_OFFSET: usize =
    offset_of!(PlistNode, plist) + offset_of!(PlistHead, prio_list);
const PLIST_NODE_LIST_OFFSET: usize =
    offset_of!(PlistNode, plist) + offset_of!(PlistHead, node_list);

const _: () = {
    assert!(size_of::<ListHead>() == 16);
    assert!(align_of::<ListHead>() == 8);
    assert!(size_of::<PlistHead>() == 32);
    assert!(align_of::<PlistHead>() == 8);
    assert!(offset_of!(PlistHead, prio_list) == 0);
    assert!(offset_of!(PlistHead, node_list) == 16);
    assert!(size_of::<PlistNode>() == 40);
    assert!(align_of::<PlistNode>() == 8);
    assert!(offset_of!(PlistNode, prio) == 0);
    assert!(offset_of!(PlistNode, plist) == 8);
};

#[inline(always)]
unsafe fn plist_from_prio(list: *mut ListHead) -> *mut PlistNode {
    list.cast::<u8>()
        .sub(PLIST_PRIO_LIST_OFFSET)
        .cast::<PlistNode>()
}

#[inline(always)]
unsafe fn plist_from_node(list: *mut ListHead) -> *mut PlistNode {
    list.cast::<u8>()
        .sub(PLIST_NODE_LIST_OFFSET)
        .cast::<PlistNode>()
}

#[inline(always)]
unsafe fn prio_link(node: *mut PlistNode) -> *mut ListHead {
    &raw mut (*node).plist.prio_list
}

#[inline(always)]
unsafe fn node_link(node: *mut PlistNode) -> *mut ListHead {
    &raw mut (*node).plist.node_list
}

#[inline(always)]
unsafe fn init_list_head(list: *mut ListHead) {
    write_volatile(&mut (*list).next, list);
    write_volatile(&mut (*list).prev, list);
}

#[inline(always)]
unsafe fn list_empty(list: *mut ListHead) -> bool {
    read_volatile(&(*list).next) == list
}

#[inline(always)]
unsafe fn list_add_tail(new: *mut ListHead, head: *mut ListHead) {
    let prev = read_volatile(&(*head).prev);

    write_volatile(&mut (*head).prev, new);
    write_volatile(&mut (*new).next, head);
    write_volatile(&mut (*new).prev, prev);
    write_volatile(&mut (*prev).next, new);
}

#[inline(always)]
unsafe fn list_del(prev: *mut ListHead, next: *mut ListHead) {
    write_volatile(&mut (*next).prev, prev);
    write_volatile(&mut (*prev).next, next);
}

#[inline(always)]
unsafe fn list_del_init(entry: *mut ListHead) {
    list_del(read_volatile(&(*entry).prev), read_volatile(&(*entry).next));
    init_list_head(entry);
}

#[inline(always)]
unsafe fn list_move_tail(entry: *mut ListHead, head: *mut ListHead) {
    list_del(read_volatile(&(*entry).prev), read_volatile(&(*entry).next));
    list_add_tail(entry, head);
}

#[inline(always)]
unsafe fn plist_first(head: *mut PlistHead) -> *mut PlistNode {
    plist_from_node(read_volatile(&(*head).node_list.next))
}

#[no_mangle]
pub unsafe extern "C" fn plist_add(node: *mut PlistNode, head: *mut PlistHead) {
    let head_prio = &raw mut (*head).prio_list;
    let head_node = &raw mut (*head).node_list;
    let mut cursor = read_volatile(&(*head_prio).next);

    while cursor != head_prio {
        let iter = plist_from_prio(cursor);

        if (*node).prio < (*iter).prio {
            list_add_tail(prio_link(node), prio_link(iter));
            list_add_tail(node_link(node), node_link(iter));
            return;
        }

        if (*node).prio == (*iter).prio {
            let next_prio = read_volatile(&(*prio_link(iter)).next);
            let next_node = if next_prio == head_prio {
                head_node
            } else {
                node_link(plist_from_prio(next_prio))
            };

            list_add_tail(node_link(node), next_node);
            return;
        }

        cursor = read_volatile(&(*cursor).next);
    }

    list_add_tail(prio_link(node), head_prio);
    list_add_tail(node_link(node), head_node);
}

#[no_mangle]
pub unsafe extern "C" fn plist_del(node: *mut PlistNode, _head: *mut PlistHead) {
    if !list_empty(prio_link(node)) {
        let next = plist_first(&raw mut (*node).plist);

        list_move_tail(prio_link(next), prio_link(node));
        list_del_init(prio_link(node));
    }

    list_del_init(node_link(node));
}
