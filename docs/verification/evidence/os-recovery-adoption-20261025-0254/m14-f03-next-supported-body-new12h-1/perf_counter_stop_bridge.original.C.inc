static int
perf_counter_stop_bridge(unsigned long counter_mask, int flags)
{
	return ihk_mc_perfctr_stop(counter_mask, flags);
}
