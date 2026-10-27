static int
perf_counter_mask_check_bridge(unsigned long counter_mask)
{
	return ihk_mc_perf_counter_mask_check(counter_mask);
}

static int
perf_counter_start_bridge(unsigned long counter_mask)
{
	return ihk_mc_perfctr_start(counter_mask);
}

static int
perf_counter_stop_bridge(unsigned long counter_mask, int flags)
{
	return ihk_mc_perfctr_stop(counter_mask, flags);
}
