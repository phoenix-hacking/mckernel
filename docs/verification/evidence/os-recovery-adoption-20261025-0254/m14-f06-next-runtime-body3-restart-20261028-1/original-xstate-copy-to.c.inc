long
arch_ptrace_xstate_copy_to_bridge(unsigned long thread_addr,
		unsigned long user_addr, size_t bytes)
{
	struct thread *thread = (struct thread *)thread_addr;

	if (thread->fp_regs == NULL) {
		return -ENOMEM;
	}
	return copy_to_user((void *)user_addr, thread->fp_regs, bytes);
}
