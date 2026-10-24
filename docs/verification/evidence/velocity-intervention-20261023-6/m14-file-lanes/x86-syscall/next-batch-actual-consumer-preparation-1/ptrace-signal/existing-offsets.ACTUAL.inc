#[repr(C)]
pub struct PtraceReportSignalOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_tid_offset: SizeT,
    pub thread_status_offset: SizeT,
    pub thread_exit_status_offset: SizeT,
    pub thread_signal_flags_offset: SizeT,
    pub thread_ptrace_offset: SizeT,
    pub thread_ptrace_debugreg_offset: SizeT,
    pub thread_report_proc_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_parent_offset: SizeT,
    pub proc_main_thread_offset: SizeT,
    pub proc_status_offset: SizeT,
    pub proc_update_lock_offset: SizeT,
    pub proc_waitpid_q_offset: SizeT,
}
