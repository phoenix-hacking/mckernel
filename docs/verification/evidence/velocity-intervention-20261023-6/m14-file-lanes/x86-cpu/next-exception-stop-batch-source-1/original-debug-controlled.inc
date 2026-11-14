void original_debug_controlled(struct x86_user_context *regs)
{
	unsigned long db6;
	int si_code = 0;
	struct siginfo info;

	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_U2K : CPUTIME_MODE_K2K_IN);
#ifdef DEBUG_PRINT_CPU
	kprintf("debug exception (err: %lx, %lx:%lx)\n",
	        regs->gpr.error, regs->gpr.cs, regs->gpr.rip);
	arch_show_interrupt_context(regs);
#endif

	db6 = fixture_debug_register_read(6);
	if (db6 & DB6_BS) {
	        regs->gpr.rflags &= ~RFLAGS_TF;
		si_code = TRAP_TRACE;
	} else if (db6 & (DB6_B3|DB6_B2|DB6_B1|DB6_B0)) {
		si_code = TRAP_HWBKPT;
	}

	memset(&info, '\0', sizeof info);
	info.si_code = si_code;
	set_signal(SIGTRAP, regs, &info);
	interrupt_exit(regs);
	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_K2U : CPUTIME_MODE_K2K_OUT);
}
