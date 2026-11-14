static void
thread_exit_waitq_wake_bridge(void *waitq)
{
	waitq_wakeup((waitq_t *)waitq);
}
