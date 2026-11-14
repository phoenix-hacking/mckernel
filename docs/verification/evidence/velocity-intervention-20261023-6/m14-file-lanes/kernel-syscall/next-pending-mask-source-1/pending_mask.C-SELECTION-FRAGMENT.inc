#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
unsigned long syscall_pending_mask_bridge(void *threadp);
#else
unsigned long
syscall_pending_mask_bridge(void *threadp)
{
	struct thread *thread = threadp;
	struct sig_pending *pending;
	struct list_head *head;
	mcs_rwlock_lock_t *lock;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	unsigned long mask = 0;

	lock = &thread->sigcommon->lock;
	head = &thread->sigcommon->sigpending;
	mcs_rwlock_writer_lock(lock, &mcs_rw_node);
	for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))) {
		mask |= pending->sigmask.__val[0];
	}
	mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

	lock = &thread->sigpendinglock;
	head = &thread->sigpending;
	mcs_rwlock_writer_lock(lock, &mcs_rw_node);
	for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))) {
		mask |= pending->sigmask.__val[0];
	}
	mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

	return mask;
}
#endif /* !MCKERNEL_RUST_SYSCALL_POLICY_HELPERS: retained C fallback */

