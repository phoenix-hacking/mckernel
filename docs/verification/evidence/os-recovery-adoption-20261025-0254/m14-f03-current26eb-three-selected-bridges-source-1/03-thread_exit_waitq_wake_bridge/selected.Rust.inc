#[cfg_attr(f03_exit_waitq_wake_selected_candidate,no_mangle)]
unsafe extern "C" fn f03_exit_notify_wake(waitq: *mut c_void) {
    // SAFETY: The full helper retains the owning process and actual wait queue.
    unsafe { crate::waitq::waitq_wakeup(waitq.cast()) };
}
