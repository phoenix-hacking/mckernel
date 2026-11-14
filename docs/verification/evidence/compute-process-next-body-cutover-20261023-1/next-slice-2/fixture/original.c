void original_sched_request_migrate(int cpu_id, struct thread *thread)
{
	struct cpu_local_var *v = get_cpu_local_var(cpu_id);
	struct migrate_request req;
	waitq_entry_t entry;

	waitq_init_locked_entry(&entry, get_this_cpu_local_var()->current);

	/*
	 * NOTES:
	 * - migration queue lock must be held before runqueue lock.
	 * - the lock must be held until migration request is added
	 *   and the target core is notified, otherwise an interrupt
	 *   may deschedule this thread and leave it hanging in
	 *   uninterruptible state forever.
	 */
	sched_request_migrate_body_result(cpu_id, (unsigned long)v,
			(unsigned long)&req, (unsigned long)&entry,
			(unsigned long)thread, ihk_mc_get_processor_id(),
			PS_UNINTERRUPTIBLE, CPU_FLAG_NEED_RESCHED,
			CPU_FLAG_NEED_MIGRATE, CPU_STATUS_RUNNING, IHK_GV_IKC,
			&process_sched_migrate_offsets,
			process_spin_lock_bridge, process_spin_unlock_bridge,
			process_sched_noirq_lock_bridge,
			process_sched_noirq_unlock_bridge,
			process_sched_waitq_init_bridge,
			process_sched_waitq_prepare_bridge,
			process_sched_waitq_finish_bridge,
			process_sched_vector_bridge, process_sched_interrupt_bridge,
			process_sched_schedule_bridge,
			process_sched_migrate_log_bridge);
}
