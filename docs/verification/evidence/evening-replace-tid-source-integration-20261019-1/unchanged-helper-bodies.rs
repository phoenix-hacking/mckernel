#[no_mangle]
pub unsafe extern "C" fn process_tid_index_for_thread_result(
    tids: *const c_void,
    nr_tids: CInt,
    entry_stride: CULong,
    thread_offset: CULong,
    thread_addr: CULong,
) -> CInt {
    if tids.is_null() || nr_tids <= 0 || entry_stride == 0 || thread_addr == 0 {
        return -1;
    }

    let base = tids.cast::<u8>();
    let stride = entry_stride as usize;
    let offset = thread_offset as usize;

    for index in 0..(nr_tids as usize) {
        let entry = base.add(index.saturating_mul(stride).saturating_add(offset));
        let stored = *(entry.cast::<CULong>());
        if stored == thread_addr {
            return index as CInt;
        }
    }

    -1
}
#[no_mangle]
pub extern "C" fn process_tid_index_found_result(index: CInt) -> CInt {
    (index >= 0) as CInt
}
fn checked_entry_addr(
    base: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    member_offset: CULong,
) -> Option<*mut u8> {
    if base.is_null() || index < 0 || entry_stride == 0 {
        return None;
    }

    let offset = (index as usize)
        .checked_mul(entry_stride as usize)?
        .checked_add(member_offset as usize)?;
    Some(base.cast::<u8>().wrapping_add(offset))
}
#[no_mangle]
pub unsafe extern "C" fn process_tid_replace_slot_result(
    tids: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    tid_offset: CULong,
    thread_offset: CULong,
    new_tid: CInt,
) -> CInt {
    let Some(tid_slot) = checked_entry_addr(tids, index, entry_stride, tid_offset) else {
        return 0;
    };
    let Some(thread_slot) = checked_entry_addr(tids, index, entry_stride, thread_offset) else {
        return 0;
    };

    *(thread_slot.cast::<CULong>()) = 0;
    *(tid_slot.cast::<CInt>()) = new_tid;
    1
}
#[no_mangle]
pub unsafe extern "C" fn process_tid_log_result(
    old_tid: CInt,
    thread: *mut c_void,
    new_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(old_tid, thread, new_tid);
    1
}
#[no_mangle]
pub unsafe extern "C" fn process_replace_tid_body_result(
    tids: *mut c_void,
    nr_tids: CInt,
    tid_stride: CULong,
    tid_offset: CULong,
    tid_thread_offset: CULong,
    thread: *mut c_void,
    old_tid: CInt,
    new_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    if tids.is_null() || thread.is_null() {
        return 0;
    }

    let index = process_tid_index_for_thread_result(
        tids,
        nr_tids,
        tid_stride,
        tid_thread_offset,
        thread as CULong,
    );
    if process_tid_index_found_result(index) == 0 {
        return 0;
    }
    if process_tid_replace_slot_result(
        tids,
        index,
        tid_stride,
        tid_offset,
        tid_thread_offset,
        new_tid,
    ) == 0
    {
        return 0;
    }

    let _ = process_tid_log_result(old_tid, thread, new_tid, log_fn);
    1
}
