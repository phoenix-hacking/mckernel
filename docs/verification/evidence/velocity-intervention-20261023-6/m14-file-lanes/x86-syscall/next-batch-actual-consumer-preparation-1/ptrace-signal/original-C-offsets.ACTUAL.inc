struct ptrace_report_signal_offsets {
	size_t thread_proc_offset;
	size_t thread_tid_offset;
	size_t thread_status_offset;
	size_t thread_exit_status_offset;
	size_t thread_signal_flags_offset;
	size_t thread_ptrace_offset;
	size_t thread_ptrace_debugreg_offset;
	size_t thread_report_proc_offset;
	size_t proc_pid_offset;
	size_t proc_parent_offset;
	size_t proc_main_thread_offset;
	size_t proc_status_offset;
	size_t proc_update_lock_offset;
	size_t proc_waitpid_q_offset;
};
