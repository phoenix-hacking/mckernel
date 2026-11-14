void arch_cpu_stop(void)
{
	while (1) {
		cpu_halt();
	}
}
