static int
perf_counter_extra_set_bridge(void *event)
{
	return ihk_mc_perfctr_set_extra((struct mc_perf_event *)event);
}
