#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void x86_cpu_ulong_log_bridge(int event, unsigned long value);
#else
static void
x86_cpu_ulong_log_bridge(int event, unsigned long value)
{
	switch (event) {
	case 1:
		kprintf("Trampoline area: 0x%lx \n", value);
		break;
	case 2:
		kprintf("# of cpus : %lu\n", value);
		break;
	case 15:
		kprintf("arch_save_panic_regs: in user-space: %p\n",
				(void *)value);
		break;
	}
}

#endif