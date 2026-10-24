void ihk_mc_print_user_context(ihk_mc_user_context_t *uctx)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_print_user_context_body_result(uctx, x86_context_line_log_bridge);
#else
	kprintf("CS:RIP = %04lx:%16lx\n", uctx->gpr.cs, uctx->gpr.rip);
	kprintf("%16lx %16lx %16lx %16lx\n%16lx %16lx %16lx\n",
	        uctx->gpr.rax, uctx->gpr.rbx, uctx->gpr.rcx, uctx->gpr.rdx,
	        uctx->gpr.rsi, uctx->gpr.rdi, uctx->gpr.rsp);
#endif
}
