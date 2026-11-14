#[no_mangle]
pub unsafe extern "C" fn sync_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
) -> CInt {
    let memobj = if range.is_null() {
        null_mut()
    } else {
        (*range).memobj.cast::<Memobj>()
    };
    let mut args = ProcessSyncArgs { memobj };

    process_sync_memory_range_body_result(
        vm,
        range,
        start,
        end,
        (&mut args as *mut ProcessSyncArgs).cast(),
        sync_one_page as *mut c_void,
        Some(process_free_range_noirq_lock_bridge),
        Some(process_free_range_noirq_unlock_bridge),
        Some(process_visit_pte_range_bridge),
        Some(process_sync_range_log_bridge),
    )
}
