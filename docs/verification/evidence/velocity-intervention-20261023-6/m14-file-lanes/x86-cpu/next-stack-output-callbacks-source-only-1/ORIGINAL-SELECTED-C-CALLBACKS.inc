void x86_stack_frame_log_bridge(unsigned long ip, unsigned long sp,
		unsigned long fp)
{
	kprintf("IP: %016lx, SP: %016lx, FP: %016lx\n", ip, sp, fp);
}

void x86_print_stack_bridge(void *rbp, unsigned long first)
{
	__print_stack(rbp, first);
}
