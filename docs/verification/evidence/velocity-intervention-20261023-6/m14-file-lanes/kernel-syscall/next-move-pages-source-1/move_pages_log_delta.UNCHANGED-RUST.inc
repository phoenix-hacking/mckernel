unsafe fn move_pages_log_delta(
    log_fn: Option<MovePagesLogFn>,
    rdtsc_fn: Option<SyscallRdtscFn>,
    event: CInt,
    start: CULong,
) -> CULong {
    let now = rdtsc_fn.map_or(start, |rdtsc| rdtsc());
    if let Some(log) = log_fn {
        log(event, now.wrapping_sub(start), 0);
    }
    now
}
