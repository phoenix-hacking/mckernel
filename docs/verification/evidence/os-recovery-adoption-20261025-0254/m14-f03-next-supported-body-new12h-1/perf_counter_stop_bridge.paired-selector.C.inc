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
