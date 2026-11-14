static long
perf_event_atomic64_read_bridge(void *value)
{
	return ihk_atomic64_read((ihk_atomic64_t *)value);
}
