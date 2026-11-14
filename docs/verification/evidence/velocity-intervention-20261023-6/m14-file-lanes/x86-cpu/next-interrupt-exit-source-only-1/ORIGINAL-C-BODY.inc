void interrupt_exit(struct x86_user_context *regs)
{
	if (interrupt_from_user(regs)) {
		cpu_enable_interrupt();
		check_sig_pending();
		check_need_resched();
		check_signal(0, regs, -1);
	}
}
