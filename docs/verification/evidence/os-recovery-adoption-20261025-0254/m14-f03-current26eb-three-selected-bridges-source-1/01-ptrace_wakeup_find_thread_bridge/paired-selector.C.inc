#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_WAKEUP_FIND)
extern unsigned long f03_ptrace_io_find(int, int);
#define ptrace_wakeup_find_thread_bridge f03_ptrace_io_find
#else
static unsigned long
ptrace_wakeup_find_thread_bridge(int tgid, int tid)
{
	return (unsigned long)find_thread(tgid, tid);
}
#endif
#line 24418
