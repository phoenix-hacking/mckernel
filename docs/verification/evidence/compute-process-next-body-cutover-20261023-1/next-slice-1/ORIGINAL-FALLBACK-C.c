void spin_sleep_or_schedule(void)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct cpu_local_var *v;
	int do_schedule = 0;
	int woken = 0;
	long irqstate;

	/* Spinning disabled explicitly */
	if (idle_halt) {
		dkprintf("%s: idle_halt -> schedule()\n", __FUNCTION__);
		goto out_schedule;
	}

	/* Try to spin sleep */
	irqstate = ihk_mc_spinlock_lock(&thread->spin_sleep_lock);
	if (thread->spin_sleep == 0) {
		dkprintf("%s: caught a lost wake-up!\n", __FUNCTION__);
	}
	ihk_mc_spinlock_unlock(&thread->spin_sleep_lock, irqstate);

	for (;;) {
		/* Check if we need to reschedule */
		irqstate = cpu_disable_interrupt_save();
		ihk_mc_spinlock_lock_noirq(
			&(get_this_cpu_local_var()->runq_lock));
		v = get_this_cpu_local_var();

		if (v->flags & CPU_FLAG_NEED_RESCHED || v->runq_len > 1) {
			v->flags &= ~CPU_FLAG_NEED_RESCHED;
			do_schedule = 1;
		}

		ihk_mc_spinlock_unlock_noirq(&v->runq_lock);
		cpu_restore_interrupt(irqstate);

		/* Check if we were woken up */
		irqstate = ihk_mc_spinlock_lock(&thread->spin_sleep_lock);
		if (thread->spin_sleep == 0) {
			woken = 1;
		}

		/* Indicate that we are not spinning any more */
		if (do_schedule) {
			thread->spin_sleep = 0;
		}
		ihk_mc_spinlock_unlock(&thread->spin_sleep_lock, irqstate);

		if ((!list_empty(&thread->sigpending) ||
		     !list_empty(&thread->sigcommon->sigpending)) &&
		    hassigpending(thread)) {
			woken = 1;
		}

		if (woken) {
			dkprintf("%s: woken while spinning, cpu: %d, do_schedule: %d\n",
				 __func__, ihk_ikc_get_processor_id(), do_schedule);
			if (do_schedule) {
				irqstate = ihk_mc_spinlock_lock(&v->runq_lock);
				v->flags |= CPU_FLAG_NEED_RESCHED;
				ihk_mc_spinlock_unlock(&v->runq_lock, irqstate);
			}
			return;
		}

		if (do_schedule) {
			break;
		}

		ihk_numa_zero_free_pages(ihk_mc_get_numa_node_by_distance(0));
		cpu_pause();
	}

out_schedule:
	schedule();
	dkprintf("%s: woken while sleeping, cpu: %d\n",
		 __func__, ihk_ikc_get_processor_id());
}
