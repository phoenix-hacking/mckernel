static unsigned long
ptrace_wakeup_find_thread_bridge(int tgid, int tid)
{
	return (unsigned long)find_thread(tgid, tid);
}
