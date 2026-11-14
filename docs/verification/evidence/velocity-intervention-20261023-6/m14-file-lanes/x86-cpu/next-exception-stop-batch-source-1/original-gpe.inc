void gpe_handler(struct x86_user_context *regs)
{
	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_U2K : CPUTIME_MODE_K2K_IN);
	kprintf("General protection fault (err: %lx, %lx:%lx)\n",
	        regs->gpr.error, regs->gpr.cs, regs->gpr.rip);
	arch_show_interrupt_context(regs);
	if ((regs->gpr.cs & 3) == 0) {
		panic("gpe_handler");
	}
	set_signal(SIGSEGV, regs, NULL);
	interrupt_exit(regs);
	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_K2U : CPUTIME_MODE_K2K_OUT);
	panic("GPF");
}
