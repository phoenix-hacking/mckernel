#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
void reset_cputime(void);
void set_cputime(enum set_cputime_mode mode);
#else
void
reset_cputime()
{
	struct thread *thread;

	if(clv == NULL)
		return;

	if(!(thread = get_this_cpu_local_var()->current))
		return;

	thread->base_tsc = 0;
}

void
set_cputime(enum set_cputime_mode mode)
{
	struct thread *thread;
	unsigned long tsc;	
	struct cpu_local_var *v;
	struct ihk_os_cpu_monitor *monitor;
	unsigned long irq_flags = 0;

	if(clv == NULL)
		return;

	v = get_this_cpu_local_var();
	if(!(thread = v->current))
		return;
	if(thread == &v->idle)
		return;
	monitor = v->monitor;
	if (mode == CPUTIME_MODE_K2U) {
		monitor->status = IHK_OS_MONITOR_USER;
	}
	else if (mode == CPUTIME_MODE_U2K) {
		monitor->counter++;
		monitor->status = IHK_OS_MONITOR_KERNEL;
	}

	if(!gettime_local_support){
		thread->times_update = 1;
		return;
	}

	irq_flags = cpu_disable_interrupt_save();
	tsc = rdtsc();
	if(thread->base_tsc != 0){
		unsigned long dtsc = tsc - thread->base_tsc;
		struct timespec dts;

		tsc_to_ts(dtsc, &dts);
		if (mode == CPUTIME_MODE_U2K) {
			thread->user_tsc += dtsc;
			v->rusage->user_tsc += dtsc;
			ts_add(&thread->itimer_virtual_value, &dts);
			ts_add(&thread->itimer_prof_value, &dts);
		}
		else{
			thread->system_tsc += dtsc;
			v->rusage->system_tsc += dtsc;
			ts_add(&thread->itimer_prof_value, &dts);
		}
	}

	thread->base_tsc = tsc;

	thread->times_update = 1;
	thread->in_kernel = (int)mode;

	if(thread->itimer_enabled){
		struct timeval tv;
		int ev = 0;

		if(thread->itimer_virtual.it_value.tv_sec != 0 ||
		   thread->itimer_virtual.it_value.tv_usec){
			ts_to_tv(&tv, &thread->itimer_virtual_value);
			tv_sub(&tv, &thread->itimer_virtual.it_value);
			if(tv.tv_sec > 0 ||
			   (tv.tv_sec == 0 &&
			    tv.tv_usec > 0)){
				thread->itimer_virtual_value.tv_sec = 0;
				thread->itimer_virtual_value.tv_nsec = 0;
				thread->itimer_virtual.it_value.tv_sec =
				    thread->itimer_virtual.it_interval.tv_sec;
				thread->itimer_virtual.it_value.tv_usec =
				    thread->itimer_virtual.it_interval.tv_usec;
				do_kill(thread, thread->proc->pid, thread->tid,
				        SIGVTALRM, NULL, 0);
				ev = 1;
			}
		}

		if(thread->itimer_prof.it_value.tv_sec != 0 ||
		   thread->itimer_prof.it_value.tv_usec){
			ts_to_tv(&tv, &thread->itimer_prof_value);
			tv_sub(&tv, &thread->itimer_prof.it_value);
			if(tv.tv_sec > 0 ||
			   (tv.tv_sec == 0 &&
			    tv.tv_usec > 0)){
				thread->itimer_prof_value.tv_sec = 0;
				thread->itimer_prof_value.tv_nsec = 0;
				thread->itimer_prof.it_value.tv_sec =
				    thread->itimer_prof.it_interval.tv_sec;
				thread->itimer_prof.it_value.tv_usec =
				    thread->itimer_prof.it_interval.tv_usec;
				do_kill(thread, thread->proc->pid, thread->tid,
				        SIGPROF, NULL, 0);
				ev = 1;
			}
		}
		if(ev){
			if(thread->itimer_virtual.it_value.tv_sec == 0 &&
			   thread->itimer_virtual.it_value.tv_usec == 0 &&
			   thread->itimer_prof.it_value.tv_sec == 0 &&
			   thread->itimer_prof.it_value.tv_usec == 0){
				thread->itimer_enabled = 0;
				set_timer(0);
			}
		}
	}
	cpu_restore_interrupt(irq_flags);
}
#endif
