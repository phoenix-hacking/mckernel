long
arch_ptrace_xstate_copy_from_bridge(unsigned long thread_addr,
		unsigned long user_addr, size_t bytes)
{
	struct thread *thread = (struct thread *)thread_addr;

	if (thread->fp_regs == NULL) {
		return -ENOMEM;
	}
	return copy_from_user(thread->fp_regs, (void *)user_addr, bytes);
}
