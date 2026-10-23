/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact existing C caller. */
void
sched_request_migrate_bridge(int cpu_id, unsigned long thread_addr)
{
	sched_request_migrate(cpu_id, (struct thread *)thread_addr);
}
