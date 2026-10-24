#[no_mangle]
pub unsafe extern "C" fn lookup_process_memory_range(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
) -> *mut VmRange {
    process_lookup_memory_range_public_result(vm, start, end, Some(process_range_public_log_bridge))
}
