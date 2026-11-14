#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_WAKEUP_UNLOCK)
extern void f03_ptrace_io_unlock(unsigned long);
#define ptrace_wakeup_thread_unlock_bridge f03_ptrace_io_unlock
#else
static void
ptrace_wakeup_thread_unlock_bridge(unsigned long thread_addr)
{
	thread_unlock((struct thread *)thread_addr);
}
#endif
#line 24424
