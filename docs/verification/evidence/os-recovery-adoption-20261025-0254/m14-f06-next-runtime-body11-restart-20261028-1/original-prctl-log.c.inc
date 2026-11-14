void
arch_prctl_log_bridge(int event, int cpu, unsigned long value)
{
	if (event == ARCH_SET_FS) {
		dkprintf("[%d] arch_prctl: ARCH_SET_FS: 0x%lX\n", cpu, value);
	}
}
