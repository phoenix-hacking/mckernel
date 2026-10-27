static int
perf_counter_extra_set_bridge(void *event)
{
	return ihk_mc_perfctr_set_extra((struct mc_perf_event *)event);
}

static int
perf_counter_init_raw_bridge(int counter_id, unsigned long hw_config, int mode)
{
	return ihk_mc_perfctr_init_raw(counter_id, hw_config, mode);
}

static long
perf_event_atomic64_read_bridge(void *value)
{
	return ihk_atomic64_read((ihk_atomic64_t *)value);
}
