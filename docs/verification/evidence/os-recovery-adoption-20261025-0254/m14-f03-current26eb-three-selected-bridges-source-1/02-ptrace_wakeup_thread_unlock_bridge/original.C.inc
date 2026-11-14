static void
ptrace_wakeup_thread_unlock_bridge(unsigned long thread_addr)
{
	thread_unlock((struct thread *)thread_addr);
}
