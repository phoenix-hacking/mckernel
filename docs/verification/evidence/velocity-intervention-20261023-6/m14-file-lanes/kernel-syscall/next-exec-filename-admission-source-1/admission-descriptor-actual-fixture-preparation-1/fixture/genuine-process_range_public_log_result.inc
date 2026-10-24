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
