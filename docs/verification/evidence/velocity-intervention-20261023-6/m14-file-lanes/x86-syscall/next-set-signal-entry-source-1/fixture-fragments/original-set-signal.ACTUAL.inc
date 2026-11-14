void
set_signal(int sig, void *regs0, siginfo_t *info)
{
	struct x86_user_context *regs = regs0;
	struct thread *thread = get_this_cpu_local_var()->current;

	if (thread == NULL || thread->proc->pid == 0)
		return;

        if (!interrupt_from_user(regs)) {
		ihk_mc_debug_show_interrupt_context(regs);
                panic("panic: kernel mode signal");
        }

	if ((__sigmask(sig) & thread->sigmask.__val[0])) {
		coredump(thread, regs0, sig);
		terminate(0, sig | 0x80);
	}
	do_kill(thread, thread->proc->pid, thread->tid, sig, info, 0);
}
