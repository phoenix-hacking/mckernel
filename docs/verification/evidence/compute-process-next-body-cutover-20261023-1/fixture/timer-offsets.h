struct timer_runtime_offsets {
	unsigned long thread_status_offset;
	unsigned long thread_sched_list_offset;
	unsigned long thread_spin_sleep_lock_offset;
	unsigned long thread_spin_sleep_offset;
	unsigned long thread_itimer_enabled_offset;
	unsigned long cpu_runq_lock_offset;
	unsigned long cpu_runq_offset;
	unsigned long cpu_runq_len_offset;
	unsigned long cpu_current_offset;
	unsigned long cpu_timer_enabled_offset;
	unsigned long cpu_backlog_list_offset;
	unsigned long timer_timeout_offset;
	unsigned long timer_waitq_offset;
	unsigned long timer_list_offset;
	unsigned long timer_thread_offset;
};
