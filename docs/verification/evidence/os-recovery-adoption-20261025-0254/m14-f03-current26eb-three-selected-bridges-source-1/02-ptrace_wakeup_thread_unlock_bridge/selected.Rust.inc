#[cfg_attr(f03_ptrace_io_unlock_selected_candidate,no_mangle)]
pub unsafe extern "C" fn f03_ptrace_io_unlock(thread: CULong) {
    unsafe { crate::process_helpers::thread_unlock(thread as *mut Thread) };
}
