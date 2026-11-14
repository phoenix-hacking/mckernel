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
