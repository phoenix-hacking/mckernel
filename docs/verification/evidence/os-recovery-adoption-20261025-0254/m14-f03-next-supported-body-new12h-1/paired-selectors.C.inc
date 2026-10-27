#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES)
extern int perf_counter_mask_check_bridge(unsigned long counter_mask);
#else
#line 20761
static int
perf_counter_mask_check_bridge(unsigned long counter_mask)
{
	return ihk_mc_perf_counter_mask_check(counter_mask);
}
#endif
#line 20766

#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES)
extern int perf_counter_start_bridge(unsigned long counter_mask);
#else
#line 20781
static int
perf_counter_start_bridge(unsigned long counter_mask)
{
	return ihk_mc_perfctr_start(counter_mask);
}
#endif
#line 20786

#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES)
extern int perf_counter_stop_bridge(unsigned long counter_mask, int flags);
#else
#line 20787
static int
perf_counter_stop_bridge(unsigned long counter_mask, int flags)
{
	return ihk_mc_perfctr_stop(counter_mask, flags);
}
#endif
#line 20792
