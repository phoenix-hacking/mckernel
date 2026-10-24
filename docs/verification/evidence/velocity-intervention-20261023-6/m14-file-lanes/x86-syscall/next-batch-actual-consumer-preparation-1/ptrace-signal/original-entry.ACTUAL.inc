void ptrace_report_signal(struct thread *thread, int sig)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	static const struct ptrace_report_signal_offsets offsets = {
		.thread_proc_offset = __builtin_offsetof(struct thread, proc),
		.thread_tid_offset = __builtin_offsetof(struct thread, tid),
		.thread_status_offset =
			__builtin_offsetof(struct thread, status),
		.thread_exit_status_offset =
			__builtin_offsetof(struct thread, exit_status),
		.thread_signal_flags_offset =
			__builtin_offsetof(struct thread, signal_flags),
		.thread_ptrace_offset =
			__builtin_offsetof(struct thread, ptrace),
		.thread_ptrace_debugreg_offset =
			__builtin_offsetof(struct thread, ptrace_debugreg),
		.thread_report_proc_offset =
			__builtin_offsetof(struct thread, report_proc),
		.proc_pid_offset = __builtin_offsetof(struct process, pid),
		.proc_parent_offset =
			__builtin_offsetof(struct process, parent),
		.proc_main_thread_offset =
			__builtin_offsetof(struct process, main_thread),
		.proc_status_offset =
			__builtin_offsetof(struct process, status),
		.proc_update_lock_offset =
			__builtin_offsetof(struct process, update_lock),
		.proc_waitpid_q_offset =
			__builtin_offsetof(struct process, waitpid_q),
	};
	struct mcs_rwlock_node_irqsave lock;

	ptrace_report_signal_body_result(thread, sig,
			get_this_cpu_local_var()->current, &offsets, &lock,
			arch_ptrace_signal_lock_bridge,
			arch_ptrace_signal_unlock_bridge,
			arch_ptrace_save_debugreg_bridge,
			arch_ptrace_waitq_wake_bridge,
			arch_ptrace_do_kill_bridge,
			arch_ptrace_schedule_bridge,
			arch_ptrace_signal_log_bridge);
#else
	struct mcs_rwlock_node_irqsave lock;
	struct process *proc = thread->proc;
	int parent_pid;
	int wake_parent = 0;
	struct siginfo info;

	dkprintf("ptrace_report_signal, tid=%d, pid=%d\n", thread->tid, thread->proc->pid);

	mcs_rwlock_writer_lock(&proc->update_lock, &lock);	
	if (!(thread->ptrace & PT_TRACED)) {
		mcs_rwlock_writer_unlock(&proc->update_lock, &lock);
		return;
	}

	/* Transition thread state */
	thread->exit_status = sig;
	thread->status = PS_TRACED;
	thread->ptrace &= ~PT_TRACE_SYSCALL;
	save_debugreg(thread->ptrace_debugreg);
	if (sig == SIGSTOP || sig == SIGTSTP ||
	    sig == SIGTTIN || sig == SIGTTOU) {
		thread->signal_flags |= SIGNAL_STOP_STOPPED;
	}
	else {
		thread->signal_flags &= ~SIGNAL_STOP_STOPPED;
	}

	if (thread == proc->main_thread) {
		/* Avoid delayed wakeup from the context-switch path while
		 * schedule() still holds the runqueue lock. */
		proc->status = PS_TRACED;
		wake_parent = 1;
		parent_pid = proc->parent->pid;
	}
	else {
		parent_pid = thread->report_proc->pid;
		waitq_wakeup(&thread->report_proc->waitpid_q);
	}
	mcs_rwlock_writer_unlock(&proc->update_lock, &lock);

	if (wake_parent) {
		waitq_wakeup(&proc->parent->waitpid_q);
	}

	memset(&info, '\0', sizeof info);
	info.si_signo = SIGCHLD;
	info.si_code = CLD_TRAPPED;
	info._sifields._sigchld.si_pid = thread->tid;
	info._sifields._sigchld.si_status = thread->exit_status;
	do_kill(get_this_cpu_local_var()->current, parent_pid, -1, SIGCHLD, &info, 0);

	dkprintf("ptrace_report_signal,sleeping\n");
	/* Sleep */
	schedule();
	dkprintf("ptrace_report_signal,wake up\n");
#endif
}
