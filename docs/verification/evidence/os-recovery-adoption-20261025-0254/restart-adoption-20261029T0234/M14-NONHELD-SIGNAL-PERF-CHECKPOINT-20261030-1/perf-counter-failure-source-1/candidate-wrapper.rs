unsafe extern "C" fn perf_entry_counter_alloc_or_release(
    thread: *mut c_void, event: *mut c_void,
) -> CInt {
    let result = unsafe { f03_perf_counter_allocate_v1(thread, event) };
    if result < 0 {
        unsafe { perf_event_alloc_free_bridge(event) };
    }
    result
}
