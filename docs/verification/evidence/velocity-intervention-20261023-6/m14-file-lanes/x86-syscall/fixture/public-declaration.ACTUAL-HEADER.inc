struct thread;
long arch_ptrace_syscall_event(struct thread *thread,
			       ihk_mc_user_context_t *ctx, long setret);
