static int
perf_counter_attr_flags_bridge(const void *attr, int *exclude_kernel,
			       int *exclude_user)
{
	const struct perf_event_attr *perf_attr = attr;

	if (!perf_attr || !exclude_kernel || !exclude_user) {
		return -EINVAL;
	}

	*exclude_kernel = perf_attr->exclude_kernel;
	*exclude_user = perf_attr->exclude_user;
	return 0;
}
