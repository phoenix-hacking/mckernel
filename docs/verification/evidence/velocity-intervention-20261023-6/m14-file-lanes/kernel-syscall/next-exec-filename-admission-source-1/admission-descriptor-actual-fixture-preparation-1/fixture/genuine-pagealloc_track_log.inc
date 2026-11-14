#[inline(always)]
unsafe fn pagealloc_track_log(
    log_fn: Option<MemPageallocTrackLogFn>,
    event: CInt,
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    npages: CInt,
) {
    if let Some(log) = log_fn {
        log(event, ptr, file, line, npages);
    }
}
