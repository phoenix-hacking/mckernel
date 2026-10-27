static int
perf_counter_init_raw_bridge(int counter_id, unsigned long hw_config, int mode)
{
	return ihk_mc_perfctr_init_raw(counter_id, hw_config, mode);
}
