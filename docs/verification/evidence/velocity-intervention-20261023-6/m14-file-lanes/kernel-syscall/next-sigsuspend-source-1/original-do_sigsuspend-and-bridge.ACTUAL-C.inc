static int
do_sigsuspend(struct thread *thread, const sigset_t *set)
{
	__sigset_t wset;
	__sigset_t bset;
	struct sig_pending *pending;
	struct list_head *head;
	mcs_rwlock_lock_t *lock;
	struct mcs_rwlock_node_irqsave mcs_rw_node;
	struct ihk_os_cpu_monitor *monitor = get_this_cpu_local_var()->monitor;

	monitor->status = IHK_OS_MONITOR_KERNEL_HEAVY;

	wset = sigsuspend_prepare_mask(set->__val[0]);
	bset = thread->sigmask.__val[0];
	thread->sigmask.__val[0] = wset;

	thread->sigevent = 1;
	for (;;) {
		while (thread->sigevent == 0) {
			int do_schedule = 0;
			struct cpu_local_var *v;
			long runq_irqstate;

			thread->status = PS_INTERRUPTIBLE;
			runq_irqstate = cpu_disable_interrupt_save();
			ihk_mc_spinlock_lock_noirq(
				&(get_this_cpu_local_var()->runq_lock));
			v = get_this_cpu_local_var();

			if (v->flags & CPU_FLAG_NEED_RESCHED) {
				v->flags &= ~CPU_FLAG_NEED_RESCHED;
				do_schedule = 1;
			}

			ihk_mc_spinlock_unlock_noirq(&v->runq_lock);
			cpu_restore_interrupt(runq_irqstate);
			
			if (do_schedule) {
				schedule();
			}
			else {
				cpu_pause();
			}
		}

		/*
		 * Sending signal here is detected
		 * by the following list check
		 */
		thread->sigevent = 0;

		thread->status = PS_RUNNING;
		lock = &thread->sigcommon->lock;
		head = &thread->sigcommon->sigpending;
		mcs_rwlock_writer_lock(lock, &mcs_rw_node);
		for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))){
			if(sigsuspend_pending_matches(
					pending->sigmask.__val[0], wset))
				break;
		}

		if(&pending->list == head){
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);

			lock = &thread->sigpendinglock;
			head = &thread->sigpending;
			mcs_rwlock_writer_lock(lock, &mcs_rw_node);
			for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))){
				if(sigsuspend_pending_matches(
						pending->sigmask.__val[0], wset))
					break;
			}
	}
		if(&pending->list == head){
			mcs_rwlock_writer_unlock(lock, &mcs_rw_node);
			continue;
		}

		process_list_detach_result(&pending->list);
		mcs_rwlock_writer_unlock(lock, &mcs_rw_node);
		thread->sigmask.__val[0] = bset;
		do_signal(-EINTR, NULL, thread, pending, -1);
		break;
	}
	return -EINTR;
}

long
syscall_sigsuspend_bridge(void *thread, void *set)
{
	return do_sigsuspend(thread, set);
}
