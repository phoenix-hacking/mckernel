#[cfg_attr(f03_ptrace_io_find_selected_candidate,no_mangle)]
pub unsafe extern "C" fn f03_ptrace_io_find(tgid: CInt, tid: CInt) -> CULong {
    unsafe { crate::process_helpers::find_thread(tgid, tid) as CULong }
}
