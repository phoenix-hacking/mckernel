#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void x86_context_line_log_bridge(int event, unsigned long a,
		unsigned long b, unsigned long c, unsigned long d);
#else
void x86_context_line_log_bridge(int event, unsigned long a,
		unsigned long b, unsigned long c, unsigned long d)
{
	switch (event) {
	case 1:
		__kprintf("CS:RIP = %4lx:%16lx\n", a, b);
		break;
	case 2:
		__kprintf("             RAX              RBX              RCX              RDX\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 3:
		__kprintf("             RSI              RDI              RSP              RBP\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 4:
		__kprintf("              R8               R9              R10              R11\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 5:
		__kprintf("             R12              R13              R14              R15\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 6:
		__kprintf("              CS               SS           RFLAGS            ERROR\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 20:
		kprintf("CS:RIP = %04lx:%16lx\n", a, b);
		break;
	case 21:
		kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 22:
		kprintf("%16lx %16lx %16lx\n", a, b, c);
		break;
	}
}
#endif
