/// Existing synchronous range-sync failure notification. No pointer is
/// dereferenced or retained; caller lock/ref/notification ordering is unchanged.
#[no_mangle]
pub unsafe extern "C" fn process_sync_range_log_bridge(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    error: CInt,
) {
    let _ = kprintf(
        b"sync_process_memory_range(%p,%p,%#lx,%#lx):visit failed%d\n\0".as_ptr().cast(),
        vm, range, start, end, error,
    );
}
