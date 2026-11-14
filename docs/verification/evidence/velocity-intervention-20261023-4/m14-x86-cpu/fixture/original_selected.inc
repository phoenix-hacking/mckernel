void original_selected_init_pstate_and_turbo(void)
{
	x86_init_pstate_turbo_body_result(no_turbo, MSR_PLATFORM_INFO,
			MSR_NHM_TURBO_RATIO_LIMIT, MSR_IA32_PERF_CTL,
			MSR_IA32_ENERGY_PERF_BIAS, x86_running_on_kvm_bridge,
			x86_cpuid6_bridge, x86_read_msr_bridge,
			x86_write_msr_bridge);
}
