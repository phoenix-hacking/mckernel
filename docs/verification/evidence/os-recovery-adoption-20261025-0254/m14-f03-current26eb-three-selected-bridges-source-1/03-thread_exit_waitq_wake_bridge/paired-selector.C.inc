#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_EXIT_WAITQ_WAKE)
extern void f03_exit_notify_wake(void *);
#define thread_exit_waitq_wake_bridge f03_exit_notify_wake
#else
static void
thread_exit_waitq_wake_bridge(void *waitq)
{
	waitq_wakeup((waitq_t *)waitq);
}
#endif
#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)
#line 4490
#else
#line 4499
#endif
