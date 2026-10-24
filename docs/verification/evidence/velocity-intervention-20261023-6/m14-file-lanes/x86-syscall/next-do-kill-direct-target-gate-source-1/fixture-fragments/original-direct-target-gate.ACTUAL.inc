	if(sig != SIGCONT &&
	   proc &&
	   proc->euid != 0 &&
	   proc->ruid != tproc->ruid &&
	   proc->euid != tproc->ruid &&
	   proc->ruid != tproc->suid &&
	   proc->euid != tproc->suid){
		if(tthread)
			release_thread(tthread);
		cpu_restore_interrupt(irqstate);
		return -EPERM;
	}

	if(sig == 0 || tthread == NULL || tthread->status == PS_EXITED){
		if(tthread)
			release_thread(tthread);
		cpu_restore_interrupt(irqstate);
		return 0;
	}

	/* Forward signal to Linux by interrupt_syscall mechanism */
	if (tthread->uti_state == UTI_STATE_RUNNING_IN_LINUX) {
		if (!tthread->proc->nohost) {
			interrupt_syscall(tthread, sig);
		}
		release_thread(tthread);
		return 0;
	}
