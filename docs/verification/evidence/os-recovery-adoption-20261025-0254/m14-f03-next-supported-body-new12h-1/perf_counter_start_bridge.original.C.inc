static int
perf_counter_start_bridge(unsigned long counter_mask)
{
	return ihk_mc_perfctr_start(counter_mask);
}
