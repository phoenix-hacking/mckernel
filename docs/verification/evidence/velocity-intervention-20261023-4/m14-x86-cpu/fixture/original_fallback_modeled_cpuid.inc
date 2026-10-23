void original_fallback_init_pstate_and_turbo(void)
{
	uint64_t value;
	uint64_t eax, ecx;

	if (running_on_kvm()) return;

	x86_cpuid6_bridge(&eax, &ecx);
	if (!(ecx & 0x01)) {
		/* P-states and/or Turbo Boost are not supported. */
		return;
	}

	/* Query and set max pstate value: 
	 *
	 * IA32_PERF_CTL (0x199H) bit 15:0:
	 * Target performance State Value
	 *
	 * The base operating ratio can be read 
	 * from MSR_PLATFORM_INFO[15:8].
	 */
	value = rdmsr(MSR_PLATFORM_INFO);
	value &= 0xFF00;

	/* Turbo boost setting:
	 * Bit 1 of EAX in Leaf 06H (i.e. CPUID.06H:EAX[1]) indicates opportunistic 
	 * processor performance operation, such as IDA, has been enabled by BIOS.
	 *
	 * IA32_PERF_CTL (0x199H) bit 32: IDA (i.e., turbo boost) Engage. (R/W)
	 * When set to 1: disengages IDA
	 * When set to 0: enables IDA
	 */
	if ((eax & (1 << 1))) {
		if (!no_turbo) {
			uint64_t turbo_value;

			turbo_value = rdmsr(MSR_NHM_TURBO_RATIO_LIMIT);
			turbo_value &= 0xFF;
			value = turbo_value << 8;

			/* Enable turbo boost */
			value &= ~((uint64_t)1 << 32);
		}
		/* Turbo boost feature is supported, but requested to be turned off */
		else {
			/* Disable turbo boost */
			value |= (uint64_t)1 << 32; 
		}
	}

	wrmsr(MSR_IA32_PERF_CTL, value);

	/* IA32_ENERGY_PERF_BIAS (0x1B0H) bit 3:0:
	 * (The processor supports this capability if CPUID.06H:ECX.SETBH[bit 3] is set.)
	 * Power Policy Preference:
	 * 0 indicates preference to highest performance.
	 * 15 indicates preference to maximize energy saving.
	 *
	 * Set energy/perf bias to high performance 
	 */ 
	if (ecx & (1 << 3)) {
		wrmsr(MSR_IA32_ENERGY_PERF_BIAS, 0);
	}
	
	//print_msr(MSR_IA32_MISC_ENABLE);
	//print_msr(MSR_IA32_PERF_CTL);
	//print_msr(MSR_IA32_ENERGY_PERF_BIAS);
}
