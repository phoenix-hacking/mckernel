PROCESS_SCHED_PUBLIC_BRIDGE void process_sched_migrate_log_bridge(unsigned long thread_addr,
					     int tid, int cpu_id)
{
	(void)thread_addr;
	dkprintf("%s: tid: %d -> cpu: %d\n",
		 "sched_request_migrate", tid, cpu_id);
}
