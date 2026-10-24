pub unsafe extern "C" fn remap_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    off: OffT,
) -> CInt {
    let memobj = if range.is_null() {
        null_mut()
    } else {
        (*range).memobj.cast::<Memobj>()
    };
    let mut args = ProcessRemapArgs { off, start, memobj };

    process_remap_memory_range_body_result(
        vm,
        range,
        start,
        end,
        off,
        (&mut args as *mut ProcessRemapArgs).cast(),
        remap_one_page as *mut c_void,
        Some(process_free_range_noirq_lock_bridge),
        Some(process_free_range_noirq_unlock_bridge),
        Some(process_visit_pte_range_bridge),
        Some(process_remap_range_log_bridge),
    )
}
