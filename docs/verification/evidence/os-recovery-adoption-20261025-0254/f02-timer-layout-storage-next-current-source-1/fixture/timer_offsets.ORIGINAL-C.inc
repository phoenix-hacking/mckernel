PROCESS_SCHED_PUBLIC_BRIDGE const struct timer_runtime_offsets process_timer_runtime_offsets = {
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_sched_list_offset = __builtin_offsetof(struct thread, sched_list),
	.thread_spin_sleep_lock_offset =
		__builtin_offsetof(struct thread, spin_sleep_lock),
	.thread_spin_sleep_offset = __builtin_offsetof(struct thread, spin_sleep),
	.thread_itimer_enabled_offset =
		__builtin_offsetof(struct thread, itimer_enabled),
	.cpu_runq_lock_offset = __builtin_offsetof(struct cpu_local_var, runq_lock),
	.cpu_runq_offset = __builtin_offsetof(struct cpu_local_var, runq),
	.cpu_runq_len_offset = __builtin_offsetof(struct cpu_local_var, runq_len),
	.cpu_current_offset = __builtin_offsetof(struct cpu_local_var, current),
	.cpu_timer_enabled_offset =
		__builtin_offsetof(struct cpu_local_var, timer_enabled),
	.cpu_backlog_list_offset =
		__builtin_offsetof(struct cpu_local_var, backlog_list),
	.timer_timeout_offset = __builtin_offsetof(struct timer, timeout),
	.timer_waitq_offset = __builtin_offsetof(struct timer, processes),
	.timer_list_offset = __builtin_offsetof(struct timer, list),
	.timer_thread_offset = __builtin_offsetof(struct timer, thread),
};
