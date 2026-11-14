	if (sig == SIGCONT || ptracecont == 1) {
		/* Wake up the target only when stopped by SIGSTOP */
		if (sched_wakeup_thread(tthread, PS_STOPPED) == 0) {
			struct siginfo info;

			tthread->proc->main_thread->signal_flags =
							SIGNAL_STOP_CONTINUED;
			tthread->proc->status = PS_RUNNING;
			memset(&info, '\0', sizeof(info));
			info.si_signo = SIGCHLD;
			info.si_code = CLD_CONTINUED;
			info._sifields._sigchld.si_pid = tthread->proc->pid;
			info._sifields._sigchld.si_status = 0x0000ffff;
			do_kill(tthread, tthread->proc->parent->pid, -1,
							SIGCHLD, &info, 0);
			tthread->proc->status = PS_RUNNING;
			if (thread != tthread) {
				ihk_mc_interrupt_cpu(tthread->cpu_id,
						ihk_mc_get_vector(IHK_GV_IKC));
			}
			doint = 0;
		}
	}
	if (doint && !(mask & tthread->sigmask.__val[0])) {
		int status = tthread->status;

		if (thread != tthread) {
			dkprintf("do_kill,ipi,pid=%d,cpu_id=%d\n",
				 tproc->pid, tthread->cpu_id);
			ihk_mc_interrupt_cpu(tthread->cpu_id,
					ihk_mc_get_vector(IHK_GV_IKC));
		}

		if (status != PS_RUNNING) {
			if(sig == SIGKILL){
				/* Wake up the target only when stopped by ptrace-reporting */
				sched_wakeup_thread(tthread, PS_TRACED | PS_STOPPED | PS_INTERRUPTIBLE);
			}
			else {
				sched_wakeup_thread(tthread, PS_INTERRUPTIBLE);
			}
		}
	}
	release_thread(tthread);
	return rc;
