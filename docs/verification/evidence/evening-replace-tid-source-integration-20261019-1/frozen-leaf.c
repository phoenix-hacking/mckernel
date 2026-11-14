void __find_and_replace_tid(struct process *proc, struct thread *thread, int new_tid) {
	process_replace_tid_body_result(proc->tids, proc->nr_tids,
		sizeof(proc->tids[0]),
		__builtin_offsetof(struct mcexec_tid, tid),
		__builtin_offsetof(struct mcexec_tid, thread),
		thread, thread->tid, new_tid, process_replace_tid_log_bridge);
}
