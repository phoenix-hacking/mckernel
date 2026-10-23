void set_timer(int runq_locked)
{
	struct cpu_local_var *v = get_this_cpu_local_var();

	timer_set_timer_body_result((unsigned long)v, time_sharing, runq_locked,
			&process_timer_runtime_offsets,
			process_timer_spin_lock_bridge,
			process_timer_spin_unlock_bridge,
			process_timer_lapic_enable_bridge,
			process_timer_lapic_disable_bridge);
}
