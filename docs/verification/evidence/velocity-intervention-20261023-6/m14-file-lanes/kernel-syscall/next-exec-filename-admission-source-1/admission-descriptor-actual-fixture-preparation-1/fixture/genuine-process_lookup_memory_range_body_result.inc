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
