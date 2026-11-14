void int3_handler(struct x86_user_context *regs)
{
	struct siginfo info;

	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_U2K : CPUTIME_MODE_K2K_IN);
#ifdef DEBUG_PRINT_CPU
	kprintf("int3 exception (err: %lx, %lx:%lx)\n",
	        regs->gpr.error, regs->gpr.cs, regs->gpr.rip);
	arch_show_interrupt_context(regs);
#endif

	memset(&info, '\0', sizeof info);
	info.si_code = TRAP_BRKPT;
	set_signal(SIGTRAP, regs, &info);
	interrupt_exit(regs);
	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_K2U : CPUTIME_MODE_K2K_OUT);
}
