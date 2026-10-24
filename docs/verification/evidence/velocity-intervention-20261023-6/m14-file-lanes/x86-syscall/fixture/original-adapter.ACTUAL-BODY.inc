static void
arch_ptrace_syscall_event_bridge(void *thread, int unused)
{
	(void)unused;
	ptrace_syscall_event((struct thread *)thread);
}
