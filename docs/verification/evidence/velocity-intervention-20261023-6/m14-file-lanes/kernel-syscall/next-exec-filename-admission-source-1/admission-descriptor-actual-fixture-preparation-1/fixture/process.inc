use crate::abi::{CInt,CULong,VmRange,ProcessVm};
use crate::rbtree::RbNode;use core::ffi::c_void;use core::ptr::null_mut;
const PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER:CInt=1;const PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT:CInt=2;
type ProcessRangePublicLogFn=unsafe extern "C" fn(CInt,*mut c_void,*mut VmRange,CULong,CULong,CInt);
extern "C" {fn process_range_public_log_bridge(event:CInt,vm:*mut c_void,range:*mut VmRange,start:CULong,end:CULong,error:CInt);}
#[inline(always)]
unsafe fn vm_range_from_rb_node(node: *mut RbNode) -> *mut VmRange {
    node.cast::<VmRange>()
}
#[no_mangle]
pub extern "C" fn process_range_cache_hit_result(
    cache_start: CULong,
    cache_end: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    (cache_start <= start && cache_end >= end) as CInt
}
#[no_mangle]
pub extern "C" fn process_lookup_range_relation_result(
    start: CULong,
    end: CULong,
    range_start: CULong,
    range_end: CULong,
) -> CInt {
    if end <= range_start {
        -1
    } else if start >= range_end {
        1
    } else if start < range_start {
        -2
    } else {
        0
    }
}
#[no_mangle]
pub unsafe extern "C" fn process_range_cache_store_result(
    cache: *mut *mut c_void,
    count: CInt,
    indexp: *mut CInt,
    match_range: *mut c_void,
) -> CInt {
    if cache.is_null() || count <= 0 || indexp.is_null() || match_range.is_null() {
        return -EINVAL;
    }

    let new_index = unsafe { (*indexp - 1 + count) % count };
    unsafe {
        *indexp = new_index;
        *cache.add(new_index as usize) = match_range;
    }
    new_index
}
#[no_mangle]
pub unsafe extern "C" fn process_lookup_memory_range_body_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
) -> *mut VmRange {
    if vm.is_null() || end <= start {
        return null_mut();
    }

    let mut i = 0;
    let cache_base = (&raw mut (*vm).range_cache).cast::<*mut VmRange>();
    while i < crate::abi::VM_RANGE_CACHE_SIZE as CInt {
        let c_i = (i + (*vm).range_cache_ind) % crate::abi::VM_RANGE_CACHE_SIZE as CInt;
        let cached = *cache_base.add(c_i as usize);
        if !cached.is_null()
            && process_range_cache_hit_result((*cached).start, (*cached).end, start, end) != 0
        {
            return cached;
        }
        i += 1;
    }

    let mut node = (*vm).vm_range_tree.rb_node.cast::<RbNode>();
    let mut matched: *mut VmRange = null_mut();
    while !node.is_null() {
        let range = vm_range_from_rb_node(node);
        let relation =
            process_lookup_range_relation_result(start, end, (*range).start, (*range).end);
        if relation < -1 {
            matched = range;
            node = (*node).rb_left;
        } else if relation < 0 {
            node = (*node).rb_left;
        } else if relation > 0 {
            node = (*node).rb_right;
        } else {
            matched = range;
            break;
        }
    }

    if !matched.is_null() && end > (*matched).start {
        let cache = (&raw mut (*vm).range_cache).cast::<*mut c_void>();
        process_range_cache_store_result(
            cache,
            crate::abi::VM_RANGE_CACHE_SIZE as CInt,
            &raw mut (*vm).range_cache_ind,
            matched.cast(),
        );
    }

    matched
}
#[no_mangle]
pub unsafe extern "C" fn process_range_public_log_result(
    event: CInt,
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    error: CInt,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> CInt {
    if let Some(log_fn) = log_fn {
        log_fn(event, vm.cast(), range, start, end, error);
    }
    0
}
#[no_mangle]
pub unsafe extern "C" fn process_lookup_memory_range_public_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> *mut VmRange {
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER,
        vm,
        null_mut(),
        start,
        end,
        0,
        log_fn,
    );
    let matched = process_lookup_memory_range_body_result(vm, start, end);
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT,
        vm,
        matched,
        start,
        end,
        0,
        log_fn,
    );
    matched
}
#[no_mangle]
pub unsafe extern "C" fn lookup_process_memory_range(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
) -> *mut VmRange {
    process_lookup_memory_range_public_result(vm, start, end, Some(process_range_public_log_bridge))
}
