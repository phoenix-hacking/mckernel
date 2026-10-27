#![allow(non_camel_case_types)]

use core::ffi::c_void;
use core::ptr::null_mut;

type CInt = i32;
type CULong = u64;
type RbRotate = Option<unsafe extern "C" fn(old: *mut RbNode, new: *mut RbNode)>;
type RbPropagate = Option<unsafe extern "C" fn(node: *mut RbNode, stop: *mut RbNode)>;
type RbCopy = Option<unsafe extern "C" fn(old: *mut RbNode, new: *mut RbNode)>;
type RbCond = Option<unsafe extern "C" fn(node: *mut RbNode, arg: *mut c_void) -> bool>;

const RB_RED: CULong = 0;
const RB_BLACK: CULong = 1;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct RbNode {
    pub(crate) __rb_parent_color: CULong,
    pub(crate) rb_right: *mut RbNode,
    pub(crate) rb_left: *mut RbNode,
}

#[repr(C)]
pub struct RbRoot {
    pub(crate) rb_node: *mut RbNode,
}

#[repr(C)]
pub struct RbAugmentCallbacks {
    propagate: RbPropagate,
    copy: RbCopy,
    rotate: RbRotate,
}

unsafe extern "C" {
    fn ihk_mc_chk_page_address(mem_addr: CULong) -> CInt;
    fn virt_to_phys(v: *mut c_void) -> CULong;
}

#[no_mangle]
pub unsafe extern "C" fn __rb_parent(pc: CULong) -> *mut RbNode {
    (pc & !3) as *mut RbNode
}

#[no_mangle]
pub unsafe extern "C" fn __rb_color(pc: CULong) -> CULong {
    pc & 1
}

#[no_mangle]
pub unsafe extern "C" fn __rb_is_black(pc: CULong) -> CInt {
    (__rb_color(pc) == RB_BLACK) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn __rb_is_red(pc: CULong) -> CInt {
    (__rb_color(pc) == RB_RED) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn rb_parent(rb: *const RbNode) -> *mut RbNode {
    __rb_parent((*rb).__rb_parent_color)
}

#[no_mangle]
pub unsafe extern "C" fn rb_empty_root(root: *const RbRoot) -> CInt {
    (*root).rb_node.is_null() as CInt
}

#[no_mangle]
pub unsafe extern "C" fn rb_color(rb: *const RbNode) -> CULong {
    __rb_color((*rb).__rb_parent_color)
}

#[inline(always)]
unsafe fn rb_is_red_bool(rb: *const RbNode) -> bool {
    rb_color(rb) == RB_RED
}

#[inline(always)]
unsafe fn rb_is_black_bool(rb: *const RbNode) -> bool {
    rb_color(rb) == RB_BLACK
}

#[no_mangle]
pub unsafe extern "C" fn rb_is_red(rb: *const RbNode) -> CInt {
    rb_is_red_bool(rb) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn rb_is_black(rb: *const RbNode) -> CInt {
    rb_is_black_bool(rb) as CInt
}

#[inline(always)]
unsafe fn rb_set_black(rb: *mut RbNode) {
    (*rb).__rb_parent_color |= RB_BLACK;
}

#[inline(always)]
unsafe fn rb_red_parent(red: *mut RbNode) -> *mut RbNode {
    (*red).__rb_parent_color as *mut RbNode
}

#[inline(always)]
unsafe fn rb_set_parent_internal(rb: *mut RbNode, p: *mut RbNode) {
    (*rb).__rb_parent_color = rb_color(rb) | p as CULong;
}

#[inline(always)]
unsafe fn rb_set_parent_color_internal(rb: *mut RbNode, p: *mut RbNode, color: CULong) {
    (*rb).__rb_parent_color = p as CULong | color;
}

#[no_mangle]
pub unsafe extern "C" fn rb_set_parent(rb: *mut RbNode, p: *mut RbNode) {
    rb_set_parent_internal(rb, p);
}

#[no_mangle]
pub unsafe extern "C" fn rb_set_parent_color(rb: *mut RbNode, p: *mut RbNode, color: CInt) {
    rb_set_parent_color_internal(rb, p, color as CULong);
}

#[no_mangle]
pub unsafe extern "C" fn rb_link_node(
    node: *mut RbNode,
    parent: *mut RbNode,
    rb_link: *mut *mut RbNode,
) {
    core::ptr::write_volatile(&raw mut (*node).__rb_parent_color, parent as CULong);
    core::ptr::write_volatile(&raw mut (*node).rb_left, null_mut());
    core::ptr::write_volatile(&raw mut (*node).rb_right, null_mut());
    core::ptr::write_volatile(rb_link, node);
}

#[inline(always)]
unsafe fn rb_empty_node_bool(node: *const RbNode) -> bool {
    (*node).__rb_parent_color == node as CULong
}

#[no_mangle]
pub unsafe extern "C" fn rb_empty_node(node: *const RbNode) -> CInt {
    rb_empty_node_bool(node) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn rb_clear_node(node: *mut RbNode) {
    (*node).__rb_parent_color = node as CULong;
}

#[inline(always)]
unsafe fn rb_change_child(
    old: *mut RbNode,
    new: *mut RbNode,
    parent: *mut RbNode,
    root: *mut RbRoot,
) {
    if !parent.is_null() {
        if (*parent).rb_left == old {
            (*parent).rb_left = new;
        } else {
            (*parent).rb_right = new;
        }
    } else {
        (*root).rb_node = new;
    }
}

#[no_mangle]
pub unsafe extern "C" fn __rb_change_child(
    old: *mut RbNode,
    new: *mut RbNode,
    parent: *mut RbNode,
    root: *mut RbRoot,
) {
    rb_change_child(old, new, parent, root);
}

#[inline(always)]
unsafe fn rb_rotate_set_parents(
    old: *mut RbNode,
    new: *mut RbNode,
    root: *mut RbRoot,
    color: CULong,
) {
    let parent = rb_parent(old);
    (*new).__rb_parent_color = (*old).__rb_parent_color;
    rb_set_parent_color_internal(old, new, color);
    rb_change_child(old, new, parent, root);
}

#[inline(always)]
unsafe fn call_rotate(cb: RbRotate, old: *mut RbNode, new: *mut RbNode) {
    if let Some(rotate) = cb {
        rotate(old, new);
    }
}

unsafe fn rb_insert(node: *mut RbNode, root: *mut RbRoot, augment_rotate: RbRotate) {
    let mut node = node;
    let mut parent = rb_red_parent(node);
    let mut tmp: *mut RbNode;

    loop {
        if parent.is_null() {
            rb_set_parent_color_internal(node, null_mut(), RB_BLACK);
            break;
        } else if rb_is_black_bool(parent) {
            break;
        }

        let gparent = rb_red_parent(parent);
        tmp = (*gparent).rb_right;
        if parent != tmp {
            if !tmp.is_null() && rb_is_red_bool(tmp) {
                rb_set_parent_color_internal(tmp, gparent, RB_BLACK);
                rb_set_parent_color_internal(parent, gparent, RB_BLACK);
                node = gparent;
                parent = rb_parent(node);
                rb_set_parent_color_internal(node, parent, RB_RED);
                continue;
            }

            tmp = (*parent).rb_right;
            if node == tmp {
                (*parent).rb_right = (*node).rb_left;
                tmp = (*parent).rb_right;
                (*node).rb_left = parent;
                if !tmp.is_null() {
                    rb_set_parent_color_internal(tmp, parent, RB_BLACK);
                }
                rb_set_parent_color_internal(parent, node, RB_RED);
                call_rotate(augment_rotate, parent, node);
                parent = node;
                tmp = (*node).rb_right;
            }

            (*gparent).rb_left = tmp;
            (*parent).rb_right = gparent;
            if !tmp.is_null() {
                rb_set_parent_color_internal(tmp, gparent, RB_BLACK);
            }
            rb_rotate_set_parents(gparent, parent, root, RB_RED);
            call_rotate(augment_rotate, gparent, parent);
            break;
        } else {
            tmp = (*gparent).rb_left;
            if !tmp.is_null() && rb_is_red_bool(tmp) {
                rb_set_parent_color_internal(tmp, gparent, RB_BLACK);
                rb_set_parent_color_internal(parent, gparent, RB_BLACK);
                node = gparent;
                parent = rb_parent(node);
                rb_set_parent_color_internal(node, parent, RB_RED);
                continue;
            }

            tmp = (*parent).rb_left;
            if node == tmp {
                (*parent).rb_left = (*node).rb_right;
                tmp = (*parent).rb_left;
                (*node).rb_right = parent;
                if !tmp.is_null() {
                    rb_set_parent_color_internal(tmp, parent, RB_BLACK);
                }
                rb_set_parent_color_internal(parent, node, RB_RED);
                call_rotate(augment_rotate, parent, node);
                parent = node;
                tmp = (*node).rb_left;
            }

            (*gparent).rb_right = tmp;
            (*parent).rb_left = gparent;
            if !tmp.is_null() {
                rb_set_parent_color_internal(tmp, gparent, RB_BLACK);
            }
            rb_rotate_set_parents(gparent, parent, root, RB_RED);
            call_rotate(augment_rotate, gparent, parent);
            break;
        }
    }
}

unsafe fn rb_erase_color(parent: *mut RbNode, root: *mut RbRoot, augment_rotate: RbRotate) {
    let mut parent = parent;
    let mut node: *mut RbNode = null_mut();
    let mut sibling: *mut RbNode;
    let mut tmp1: *mut RbNode;
    let mut tmp2: *mut RbNode;

    loop {
        sibling = (*parent).rb_right;
        if node != sibling {
            if rb_is_red_bool(sibling) {
                (*parent).rb_right = (*sibling).rb_left;
                tmp1 = (*parent).rb_right;
                (*sibling).rb_left = parent;
                rb_set_parent_color_internal(tmp1, parent, RB_BLACK);
                rb_rotate_set_parents(parent, sibling, root, RB_RED);
                call_rotate(augment_rotate, parent, sibling);
                sibling = tmp1;
            }
            tmp1 = (*sibling).rb_right;
            if tmp1.is_null() || rb_is_black_bool(tmp1) {
                tmp2 = (*sibling).rb_left;
                if tmp2.is_null() || rb_is_black_bool(tmp2) {
                    rb_set_parent_color_internal(sibling, parent, RB_RED);
                    if rb_is_red_bool(parent) {
                        rb_set_black(parent);
                    } else {
                        node = parent;
                        parent = rb_parent(node);
                        if !parent.is_null() {
                            continue;
                        }
                    }
                    break;
                }
                (*sibling).rb_left = (*tmp2).rb_right;
                tmp1 = (*sibling).rb_left;
                (*tmp2).rb_right = sibling;
                (*parent).rb_right = tmp2;
                if !tmp1.is_null() {
                    rb_set_parent_color_internal(tmp1, sibling, RB_BLACK);
                }
                call_rotate(augment_rotate, sibling, tmp2);
                tmp1 = sibling;
                sibling = tmp2;
            }
            (*parent).rb_right = (*sibling).rb_left;
            tmp2 = (*parent).rb_right;
            (*sibling).rb_left = parent;
            rb_set_parent_color_internal(tmp1, sibling, RB_BLACK);
            if !tmp2.is_null() {
                rb_set_parent_internal(tmp2, parent);
            }
            rb_rotate_set_parents(parent, sibling, root, RB_BLACK);
            call_rotate(augment_rotate, parent, sibling);
            break;
        } else {
            sibling = (*parent).rb_left;
            if rb_is_red_bool(sibling) {
                (*parent).rb_left = (*sibling).rb_right;
                tmp1 = (*parent).rb_left;
                (*sibling).rb_right = parent;
                rb_set_parent_color_internal(tmp1, parent, RB_BLACK);
                rb_rotate_set_parents(parent, sibling, root, RB_RED);
                call_rotate(augment_rotate, parent, sibling);
                sibling = tmp1;
            }
            tmp1 = (*sibling).rb_left;
            if tmp1.is_null() || rb_is_black_bool(tmp1) {
                tmp2 = (*sibling).rb_right;
                if tmp2.is_null() || rb_is_black_bool(tmp2) {
                    rb_set_parent_color_internal(sibling, parent, RB_RED);
                    if rb_is_red_bool(parent) {
                        rb_set_black(parent);
                    } else {
                        node = parent;
                        parent = rb_parent(node);
                        if !parent.is_null() {
                            continue;
                        }
                    }
                    break;
                }
                (*sibling).rb_right = (*tmp2).rb_left;
                tmp1 = (*sibling).rb_right;
                (*tmp2).rb_left = sibling;
                (*parent).rb_left = tmp2;
                if !tmp1.is_null() {
                    rb_set_parent_color_internal(tmp1, sibling, RB_BLACK);
                }
                call_rotate(augment_rotate, sibling, tmp2);
                tmp1 = sibling;
                sibling = tmp2;
            }
            (*parent).rb_left = (*sibling).rb_right;
            tmp2 = (*parent).rb_left;
            (*sibling).rb_right = parent;
            rb_set_parent_color_internal(tmp1, sibling, RB_BLACK);
            if !tmp2.is_null() {
                rb_set_parent_internal(tmp2, parent);
            }
            rb_rotate_set_parents(parent, sibling, root, RB_BLACK);
            call_rotate(augment_rotate, parent, sibling);
            break;
        }
    }
}

unsafe extern "C" fn dummy_propagate(_node: *mut RbNode, _stop: *mut RbNode) {}
unsafe extern "C" fn dummy_copy(_old: *mut RbNode, _new: *mut RbNode) {}
unsafe extern "C" fn dummy_rotate(_old: *mut RbNode, _new: *mut RbNode) {}

static DUMMY_CALLBACKS: RbAugmentCallbacks = RbAugmentCallbacks {
    propagate: Some(dummy_propagate),
    copy: Some(dummy_copy),
    rotate: Some(dummy_rotate),
};

unsafe fn call_propagate(
    callbacks: *const RbAugmentCallbacks,
    node: *mut RbNode,
    stop: *mut RbNode,
) {
    if let Some(propagate) = (*callbacks).propagate {
        propagate(node, stop);
    }
}

unsafe fn call_copy(callbacks: *const RbAugmentCallbacks, old: *mut RbNode, new: *mut RbNode) {
    if let Some(copy) = (*callbacks).copy {
        copy(old, new);
    }
}

unsafe fn rb_erase_augmented_impl(
    node: *mut RbNode,
    root: *mut RbRoot,
    augment: *const RbAugmentCallbacks,
) -> *mut RbNode {
    let child = (*node).rb_right;
    let mut tmp = (*node).rb_left;
    let parent: *mut RbNode;
    let rebalance: *mut RbNode;
    let pc: CULong;

    if tmp.is_null() {
        pc = (*node).__rb_parent_color;
        parent = (pc & !3) as *mut RbNode;
        rb_change_child(node, child, parent, root);
        if !child.is_null() {
            (*child).__rb_parent_color = pc;
            rebalance = null_mut();
        } else {
            rebalance = if pc & 1 != 0 { parent } else { null_mut() };
        }
        tmp = parent;
    } else if child.is_null() {
        pc = (*node).__rb_parent_color;
        (*tmp).__rb_parent_color = pc;
        parent = (pc & !3) as *mut RbNode;
        rb_change_child(node, tmp, parent, root);
        rebalance = null_mut();
        tmp = parent;
    } else {
        let mut successor = child;
        let child2: *mut RbNode;
        tmp = (*child).rb_left;
        if tmp.is_null() {
            parent = successor;
            child2 = (*successor).rb_right;
            call_copy(augment, node, successor);
        } else {
            let mut parent_mut;
            loop {
                parent_mut = successor;
                successor = tmp;
                tmp = (*tmp).rb_left;
                if tmp.is_null() {
                    break;
                }
            }
            parent = parent_mut;
            (*parent).rb_left = (*successor).rb_right;
            child2 = (*parent).rb_left;
            (*successor).rb_right = child;
            rb_set_parent_internal(child, successor);
            call_copy(augment, node, successor);
            call_propagate(augment, parent, successor);
        }

        (*successor).rb_left = (*node).rb_left;
        tmp = (*successor).rb_left;
        rb_set_parent_internal(tmp, successor);

        pc = (*node).__rb_parent_color;
        tmp = (pc & !3) as *mut RbNode;
        rb_change_child(node, successor, tmp, root);
        if !child2.is_null() {
            (*successor).__rb_parent_color = pc;
            rb_set_parent_color_internal(child2, parent, RB_BLACK);
            rebalance = null_mut();
        } else {
            let pc2 = (*successor).__rb_parent_color;
            (*successor).__rb_parent_color = pc;
            rebalance = if pc2 & 1 != 0 { parent } else { null_mut() };
        }
        tmp = successor;
    }

    call_propagate(augment, tmp, null_mut());
    rebalance
}

#[no_mangle]
pub unsafe extern "C" fn __rb_erase_color(
    parent: *mut RbNode,
    root: *mut RbRoot,
    augment_rotate: RbRotate,
) {
    rb_erase_color(parent, root, augment_rotate);
}

#[no_mangle]
pub unsafe extern "C" fn rb_insert_color(node: *mut RbNode, root: *mut RbRoot) {
    rb_insert(node, root, Some(dummy_rotate));
}

#[no_mangle]
pub unsafe extern "C" fn rb_erase(node: *mut RbNode, root: *mut RbRoot) {
    let rebalance = rb_erase_augmented_impl(node, root, &DUMMY_CALLBACKS);
    if !rebalance.is_null() {
        rb_erase_color(rebalance, root, Some(dummy_rotate));
    }
}

#[no_mangle]
pub unsafe extern "C" fn __rb_erase_augmented(
    node: *mut RbNode,
    root: *mut RbRoot,
    augment: *const RbAugmentCallbacks,
) -> *mut RbNode {
    rb_erase_augmented_impl(node, root, augment)
}

#[no_mangle]
pub unsafe extern "C" fn rb_erase_augmented(
    node: *mut RbNode,
    root: *mut RbRoot,
    augment: *const RbAugmentCallbacks,
) {
    let rebalance = rb_erase_augmented_impl(node, root, augment);
    if !rebalance.is_null() {
        rb_erase_color(rebalance, root, (*augment).rotate);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __rb_insert_augmented(
    node: *mut RbNode,
    root: *mut RbRoot,
    augment_rotate: RbRotate,
) {
    rb_insert(node, root, augment_rotate);
}

#[no_mangle]
pub unsafe extern "C" fn rb_insert_augmented(
    node: *mut RbNode,
    root: *mut RbRoot,
    augment: *const RbAugmentCallbacks,
) {
    rb_insert(node, root, (*augment).rotate);
}

#[no_mangle]
pub unsafe extern "C" fn rb_first(root: *const RbRoot) -> *mut RbNode {
    let mut n = (*root).rb_node;
    if n.is_null() {
        return null_mut();
    }
    while !(*n).rb_left.is_null() {
        n = (*n).rb_left;
    }
    n
}

unsafe fn rb_preorder_dfs(n: *mut RbNode, cond: RbCond, cond_arg: *mut c_void) -> *mut RbNode {
    if let Some(cb) = cond {
        if cb(n, cond_arg) {
            return n;
        }
    }

    if !(*n).rb_left.is_null() {
        let left_res = rb_preorder_dfs((*n).rb_left, cond, cond_arg);
        if !left_res.is_null() {
            return left_res;
        }
    }
    if !(*n).rb_right.is_null() {
        return rb_preorder_dfs((*n).rb_right, cond, cond_arg);
    }

    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn rb_preorder_dfs_search(
    root: *const RbRoot,
    cond: RbCond,
    cond_arg: *mut c_void,
) -> *mut RbNode {
    let n = (*root).rb_node;
    if n.is_null() {
        return null_mut();
    }
    rb_preorder_dfs(n, cond, cond_arg)
}

#[no_mangle]
pub unsafe extern "C" fn rb_first_safe(root: *const RbRoot) -> *mut RbNode {
    let mut n = (*root).rb_node;
    if n.is_null() {
        return null_mut();
    }

    let mut phys = virt_to_phys(n.cast::<c_void>());
    if ihk_mc_chk_page_address(phys) == -1 {
        return null_mut();
    }

    while !(*n).rb_left.is_null() {
        n = (*n).rb_left;
        phys = virt_to_phys(n.cast::<c_void>());
        if ihk_mc_chk_page_address(phys) == -1 {
            return null_mut();
        }
    }
    n
}

#[no_mangle]
pub unsafe extern "C" fn rb_last(root: *const RbRoot) -> *mut RbNode {
    let mut n = (*root).rb_node;
    if n.is_null() {
        return null_mut();
    }
    while !(*n).rb_right.is_null() {
        n = (*n).rb_right;
    }
    n
}

#[no_mangle]
pub unsafe extern "C" fn rb_next(mut node: *const RbNode) -> *mut RbNode {
    let mut parent: *mut RbNode;

    if rb_empty_node_bool(node) {
        return null_mut();
    }

    if !(*node).rb_right.is_null() {
        node = (*node).rb_right;
        while !(*node).rb_left.is_null() {
            node = (*node).rb_left;
        }
        return node as *mut RbNode;
    }

    parent = rb_parent(node);
    while !parent.is_null() && node == (*parent).rb_right {
        node = parent;
        parent = rb_parent(node);
    }

    parent
}

#[no_mangle]
pub unsafe extern "C" fn rb_next_safe(mut node: *const RbNode) -> *mut RbNode {
    let mut parent: *mut RbNode;

    if rb_empty_node_bool(node) {
        return null_mut();
    }

    if !(*node).rb_right.is_null() {
        node = (*node).rb_right;

        let mut phys = virt_to_phys((node as *mut RbNode).cast::<c_void>());
        if ihk_mc_chk_page_address(phys) == -1 {
            return null_mut();
        }

        while !(*node).rb_left.is_null() {
            node = (*node).rb_left;
            phys = virt_to_phys((node as *mut RbNode).cast::<c_void>());
            if ihk_mc_chk_page_address(phys) == -1 {
                return null_mut();
            }
        }

        return node as *mut RbNode;
    }

    parent = rb_parent(node);
    while !parent.is_null() && node == (*parent).rb_right {
        node = parent;
        parent = rb_parent(node);
    }

    parent
}

#[no_mangle]
pub unsafe extern "C" fn rb_prev(mut node: *const RbNode) -> *mut RbNode {
    let mut parent: *mut RbNode;

    if rb_empty_node_bool(node) {
        return null_mut();
    }

    if !(*node).rb_left.is_null() {
        node = (*node).rb_left;
        while !(*node).rb_right.is_null() {
            node = (*node).rb_right;
        }
        return node as *mut RbNode;
    }

    parent = rb_parent(node);
    while !parent.is_null() && node == (*parent).rb_left {
        node = parent;
        parent = rb_parent(node);
    }

    parent
}

#[no_mangle]
pub unsafe extern "C" fn rb_replace_node(victim: *mut RbNode, new: *mut RbNode, root: *mut RbRoot) {
    let parent = rb_parent(victim);

    rb_change_child(victim, new, parent, root);
    if !(*victim).rb_left.is_null() {
        rb_set_parent_internal((*victim).rb_left, new);
    }
    if !(*victim).rb_right.is_null() {
        rb_set_parent_internal((*victim).rb_right, new);
    }

    (*new).__rb_parent_color = (*victim).__rb_parent_color;
    (*new).rb_right = (*victim).rb_right;
    (*new).rb_left = (*victim).rb_left;
}

unsafe fn rb_left_deepest_node(mut node: *const RbNode) -> *mut RbNode {
    loop {
        if !(*node).rb_left.is_null() {
            node = (*node).rb_left;
        } else if !(*node).rb_right.is_null() {
            node = (*node).rb_right;
        } else {
            return node as *mut RbNode;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn rb_next_postorder(node: *const RbNode) -> *mut RbNode {
    if node.is_null() {
        return null_mut();
    }
    let parent = rb_parent(node);

    if !parent.is_null() && node == (*parent).rb_left && !(*parent).rb_right.is_null() {
        rb_left_deepest_node((*parent).rb_right)
    } else {
        parent
    }
}

#[no_mangle]
pub unsafe extern "C" fn rb_first_postorder(root: *const RbRoot) -> *mut RbNode {
    if (*root).rb_node.is_null() {
        return null_mut();
    }

    rb_left_deepest_node((*root).rb_node)
}
