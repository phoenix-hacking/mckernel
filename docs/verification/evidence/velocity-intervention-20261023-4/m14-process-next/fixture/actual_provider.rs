#![no_std]
#![allow(dead_code)]
#[path="abi.ACTUAL.rs"] mod abi;
#[path="rbtree.ACTUAL.rs"] mod rbtree;
use core::ffi::c_void;
use core::ptr::null_mut;
use abi::{CInt,ProcessVm,VmRange};
use rbtree::{RbNode,RbRoot,rb_link_node,rb_insert_color};
const EINVAL:CInt=22;
const EFAULT:CInt=14;
const PROCESS_VM_RANGE_INSERT_LOG_OVERLAP:CInt=1;
const PROCESS_VM_RANGE_INSERT_LOG_SUCCESS:CInt=2;
type ProcessVmRangeInsertLogFn=unsafe extern "C" fn(CInt,*mut c_void,*mut VmRange,*mut VmRange);
type ProcessVmRangeInsertDumpFn=unsafe extern "C" fn(*mut c_void);
unsafe extern "C" {
    fn vm_range_insert_log_bridge(
        event: CInt,
        vm: *mut c_void,
        newrange: *mut VmRange,
        range: *mut VmRange,
    );
    fn vm_range_insert_dump_bridge(vm: *mut c_void);
}
unsafe fn vm_range_rb_node(range: *mut VmRange) -> *mut RbNode {
    (&raw mut (*range).vm_rb_node).cast::<RbNode>()
}
unsafe fn vm_range_from_rb_node(node: *mut RbNode) -> *mut VmRange {
    node.cast::<VmRange>()
}
#[no_mangle]
pub unsafe extern "C" fn process_vm_range_insert_log_result(
    event: CInt,
    vm: *mut c_void,
    newrange: *mut VmRange,
    range: *mut VmRange,
    log_fn: Option<ProcessVmRangeInsertLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, vm, newrange, range);
    0
}
#[no_mangle]
pub unsafe extern "C" fn process_vm_range_insert_dump_result(
    vm: *mut c_void,
    dump_fn: Option<ProcessVmRangeInsertDumpFn>,
) -> CInt {
    let Some(dump) = dump_fn else {
        return 0;
    };

    dump(vm);
    0
}
#[no_mangle]
pub unsafe extern "C" fn process_vm_range_insert_result(
    root: *mut RbRoot,
    newrange: *mut VmRange,
    vm: *mut c_void,
    log_fn: Option<ProcessVmRangeInsertLogFn>,
    dump_fn: Option<ProcessVmRangeInsertDumpFn>,
) -> CInt {
    if root.is_null() || newrange.is_null() {
        return -EINVAL;
    }

    let mut link: *mut *mut RbNode = &raw mut (*root).rb_node;
    let mut parent: *mut RbNode = null_mut();

    while !(*link).is_null() {
        let current = *link;
        let range = vm_range_from_rb_node(current);

        parent = current;
        if (*newrange).end <= (*range).start {
            link = &raw mut (*current).rb_left;
        } else if (*newrange).start >= (*range).end {
            link = &raw mut (*current).rb_right;
        } else {
            let _ = process_vm_range_insert_log_result(
                PROCESS_VM_RANGE_INSERT_LOG_OVERLAP,
                vm,
                newrange,
                range,
                log_fn,
            );
            return -EFAULT;
        }
    }

    let _ = process_vm_range_insert_log_result(
        PROCESS_VM_RANGE_INSERT_LOG_SUCCESS,
        vm,
        newrange,
        null_mut(),
        log_fn,
    );
    let _ = process_vm_range_insert_dump_result(vm, dump_fn);

    let node = vm_range_rb_node(newrange);
    rb_link_node(node, parent, link);
    rb_insert_color(node, root);

    0
}
/// Own the selected process.c insertion entry in Rust. The caller holds the
/// existing VM range exclusion and supplies a live ProcessVm, exactly as for
/// the former C wrapper; the helper retains all tree mutation and error order.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert(
    vm: *mut ProcessVm,
    newrange: *mut VmRange,
) -> CInt {
    process_vm_range_insert_result(
        (&raw mut (*vm).vm_range_tree).cast::<RbRoot>(),
        newrange,
        vm.cast(),
        Some(vm_range_insert_log_bridge),
        Some(vm_range_insert_dump_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn fixture_rust_layout(out:*mut usize) {
    let values=[core::mem::size_of::<ProcessVm>(),core::mem::size_of::<VmRange>(),
        core::mem::offset_of!(ProcessVm,vm_range_tree),core::mem::offset_of!(VmRange,vm_rb_node),
        core::mem::offset_of!(VmRange,start),core::mem::offset_of!(VmRange,end),
        core::mem::size_of::<CInt>()];
    core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
