#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_PERF_PROVIDER_NEXT3_BRIDGES)
extern int perf_counter_extra_set_bridge(void *event);
#else
#line 20498
static int
perf_counter_extra_set_bridge(void *event)
{
	return ihk_mc_perfctr_set_extra((struct mc_perf_event *)event);
}
#endif
#line 20503
