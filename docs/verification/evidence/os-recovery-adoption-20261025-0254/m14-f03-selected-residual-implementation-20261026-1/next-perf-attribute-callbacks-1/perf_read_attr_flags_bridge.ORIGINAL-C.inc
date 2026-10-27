static int
perf_read_attr_flags_bridge(const void *attr, int *exclude_user,
			    int *exclude_kernel, int *inherit)
{
	const struct perf_event_attr *perf_attr = attr;

	if (!perf_attr || !exclude_user || !exclude_kernel || !inherit) {
		return -EINVAL;
	}

	*exclude_user = perf_attr->exclude_user;
	*exclude_kernel = perf_attr->exclude_kernel;
	*inherit = perf_attr->inherit;
	return 0;
}
