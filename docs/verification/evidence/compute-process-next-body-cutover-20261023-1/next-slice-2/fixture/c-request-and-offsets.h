struct migrate_request {
	struct list_head list;
	struct thread *thread;
	struct waitq wq;
};
static const struct sched_migrate_offsets process_sched_migrate_offsets = {
	.req_list_offset = __builtin_offsetof(struct migrate_request, list),
	.req_thread_offset = __builtin_offsetof(struct migrate_request, thread),
	.req_wq_offset = __builtin_offsetof(struct migrate_request, wq),
	.thread_cpu_id_offset = __builtin_offsetof(struct thread, cpu_id),
	.thread_tid_offset = __builtin_offsetof(struct thread, tid),
	.cpu_migq_lock_offset =
		__builtin_offsetof(struct cpu_local_var, migq_lock),
	.cpu_migq_offset = __builtin_offsetof(struct cpu_local_var, migq),
	.cpu_runq_lock_offset =
		__builtin_offsetof(struct cpu_local_var, runq_lock),
	.cpu_flags_offset = __builtin_offsetof(struct cpu_local_var, flags),
	.cpu_status_offset = __builtin_offsetof(struct cpu_local_var, status),
};
