#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
mod rbtree {
use crate::abi::CULong;
#[repr(C)]
pub struct RbNode {
    pub(crate) __rb_parent_color: CULong,
    pub(crate) rb_right: *mut RbNode,
    pub(crate) rb_left: *mut RbNode,
}
}
use core::ffi::c_void;
use abi::{CInt,ProcessVm,VmRange};
use rbtree::RbNode;
unsafe extern "C" {
    fn kprintf(format:*const i8,...)->CInt;
    static process_dump_tree_enabled:CInt;
}
unsafe fn vm_range_from_rb_node(node: *mut RbNode) -> *mut VmRange {
    node.cast::<VmRange>()
}
// Same synchronous in-order diagnostic traversal as the displaced dtree.
// The existing VM/range exclusion keeps every visited node live. Field reads
// and the right-child load remain after left traversal and the logger call.
unsafe fn process_dump_tree_node(node: *mut RbNode, level: CInt) {
    if node.is_null() {
        return;
    }
    let range = vm_range_from_rb_node(node);
    process_dump_tree_node((*node).rb_left, level.wrapping_add(1));
    let _ = kprintf(
        b"dtree: %0*d, %p: %lx-%lx\n\0".as_ptr().cast(),
        level,
        0 as CInt,
        range,
        (*range).start,
        (*range).end,
    );
    process_dump_tree_node((*node).rb_right, level.wrapping_add(1));
}

/// Preserve DEBUG_PRINT_PROCESS gating without retaining C dump computation.
/// Disabled dumping never dereferences vm. Enabled dumping logs the header
/// before loading the root, then synchronously visits the borrowed live tree.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert_dump_bridge(vm: *mut c_void) {
    if core::ptr::read_volatile(core::ptr::addr_of!(process_dump_tree_enabled)) == 0 {
        return;
    }
    let _ = kprintf(b"dump_tree %p\n\0".as_ptr().cast(), vm);
    let root = (*vm.cast::<ProcessVm>()).vm_range_tree.rb_node.cast::<RbNode>();
    process_dump_tree_node(root, 1);
}
