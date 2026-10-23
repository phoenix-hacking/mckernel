void original_spin_sleep_or_schedule(void)
{
	sched_spin_sleep_or_schedule_body_result(
			(unsigned long)get_this_cpu_local_var()->current,
			(unsigned long)get_this_cpu_local_var(),
			ihk_ikc_get_processor_id(), idle_halt,
			CPU_FLAG_NEED_RESCHED,
			&process_sched_runqueue_offsets,
			process_sched_irq_save_bridge,
			process_sched_irq_restore_bridge,
			process_spin_lock_bridge,
			process_spin_unlock_bridge,
			process_sched_noirq_lock_bridge,
			process_sched_noirq_unlock_bridge,
			process_sched_schedule_bridge,
			process_sched_zero_free_bridge,
			process_sched_pause_bridge,
			process_sched_has_signal_bridge,
			process_sched_runq_log_bridge);
}
