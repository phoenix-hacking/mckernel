
// Preserve the existing optional dynamic-debug event, including its format bytes.
#[used]
#[link_section = "__verbose"]
static mut REPLACE_TID_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"process_replace_tid_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};

unsafe extern "C" fn process_replace_tid_log_bridge(
    tid: CInt, thread: *mut c_void, new_tid: CInt,
) {
    let flags = unsafe {
        core::ptr::read_volatile(core::ptr::addr_of!(REPLACE_TID_DEBUG.line_flags)) >> 24
    };
    if flags != 0 {
        unsafe {
            kprintf(
                b"%s: tid %d (thread %p) has been relaced with tid %d\n\0".as_ptr().cast(),
                b"__find_and_replace_tid\0".as_ptr().cast::<i8>(), tid, thread, new_tid,
            );
        }
    }
}

const _: () = {
    assert!(offset_of!(Process, tids) == 256);
    assert!(offset_of!(Process, nr_tids) == 264);
    assert!(offset_of!(Thread, tid) == 20);
    assert!(size_of::<crate::abi::McexecTid>() == 16);
    assert!(offset_of!(crate::abi::McexecTid, tid) == 0);
    assert!(offset_of!(crate::abi::McexecTid, thread) == 8);
};

/// Replace the first slot owned by this live thread while threads_lock is held.
/// The caller keeps process, thread and its positive-count TID array live and
/// excludes concurrent or reentrant slot changes. Null tables are permitted.
/// The existing helper clears the matched pointer before writing the new numeric
/// TID, then logs; it never changes thread.tid or frees/references thread storage.
/// Unmatched entries, slot padding and later duplicate pointers are preserved.
#[no_mangle]
pub unsafe extern "C" fn __find_and_replace_tid(
    proc: *mut Process, thread: *mut Thread, new_tid: CInt,
) {
    let _ = unsafe {
        process_replace_tid_body_result(
            (*proc).tids, (*proc).nr_tids,
            size_of::<crate::abi::McexecTid>() as CULong,
            offset_of!(crate::abi::McexecTid, tid) as CULong,
            offset_of!(crate::abi::McexecTid, thread) as CULong,
            thread.cast(), (*thread).tid, new_tid, Some(process_replace_tid_log_bridge),
        )
    };
}
