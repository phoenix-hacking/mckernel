SYSCALL_POLICY_HELPER_SCOPE long
perf_event_alloc_init_body_result(void *event, const void *attr,
		size_t event_size, size_t attr_size,
		size_t event_attr_offset, size_t group_entry_offset,
		size_t sibling_list_offset, size_t sample_freq_offset,
		size_t nr_siblings_offset, size_t count_offset,
		size_t child_count_total_offset, size_t parent_offset,
		size_t hw_sample_period_offset, size_t hw_last_period_offset,
		size_t hw_period_left_offset, size_t use_invariant_tsc_offset,
		unsigned long attr_type, unsigned long attr_config,
		int attr_freq, unsigned long attr_sample_freq,
		unsigned long attr_sample_period, unsigned long hardware_type,
		unsigned long ref_cpu_cycles_config,
		sync_child_atomic64_set_fn_t atomic_set_fn)
{
	char *event_base = event;
	struct list_head *group_entry;
	struct list_head *sibling_list;
	unsigned long sample_period;

	if (!event || !attr || !atomic_set_fn) {
		return -EINVAL;
	}

	memset(event, 0, event_size);
	memcpy(event_base + event_attr_offset, attr, attr_size);

	group_entry = (struct list_head *)(event_base + group_entry_offset);
	group_entry->next = group_entry;
	group_entry->prev = group_entry;
	sibling_list = (struct list_head *)(event_base + sibling_list_offset);
	sibling_list->next = sibling_list;
	sibling_list->prev = sibling_list;

	*(unsigned long *)(event_base + sample_freq_offset) = attr_sample_freq;
	*(int *)(event_base + nr_siblings_offset) = 0;
	atomic_set_fn(event_base + count_offset, 0);
	*(unsigned long *)(event_base + child_count_total_offset) = 0;
	*(void **)(event_base + parent_offset) = NULL;

	sample_period = attr_sample_period;
	if (attr_freq && attr_sample_freq) {
		sample_period = 1;
	}
	*(unsigned long *)(event_base + hw_sample_period_offset) = sample_period;
	*(unsigned long *)(event_base + hw_last_period_offset) = sample_period;
	atomic_set_fn(event_base + hw_period_left_offset, sample_period);

	if (attr_type == hardware_type && attr_config == ref_cpu_cycles_config) {
		*(int *)(event_base + use_invariant_tsc_offset) = 1;
		return 1;
	}

	return 0;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_alloc_map_body_result(void **event_out, void *event,
		size_t hw_config_offset, size_t hw_config_ext_offset,
		size_t extra_reg_config_offset, size_t extra_reg_reg_offset,
		size_t extra_reg_idx_offset, unsigned long attr_type,
		unsigned long attr_config, unsigned long hardware_type,
		unsigned long hw_cache_type, unsigned long raw_type,
		perf_event_map_fn_t hw_event_map_fn,
		perf_event_map_fn_t hw_cache_event_map_fn,
		perf_event_map_fn_t hw_cache_extra_reg_map_fn,
		perf_event_map_fn_t raw_event_map_fn,
		perf_event_validate_fn_t validate_event_fn,
		perf_extra_reg_id_fn_t extra_reg_id_fn,
		perf_extra_reg_msr_fn_t extra_reg_msr_fn,
		perf_extra_reg_idx_fn_t extra_reg_idx_fn,
		perf_hw_event_init_fn_t hw_event_init_fn)
{
	char *event_base = event;
	unsigned long val;
	unsigned long extra_config = 0;
	int ereg_id;
	int ret;

	if (!event_out || !event || !validate_event_fn || !extra_reg_id_fn ||
			!extra_reg_msr_fn || !extra_reg_idx_fn ||
			!hw_event_init_fn) {
		return -EINVAL;
	}

	if (attr_type == hardware_type) {
		if (!hw_event_map_fn) {
			return -EINVAL;
		}
		val = hw_event_map_fn(attr_config);
	}
	else if (attr_type == hw_cache_type) {
		if (!hw_cache_event_map_fn || !hw_cache_extra_reg_map_fn) {
			return -EINVAL;
		}
		val = hw_cache_event_map_fn(attr_config);
		extra_config = hw_cache_extra_reg_map_fn(attr_config);
	}
	else if (attr_type == raw_type) {
		if (!raw_event_map_fn) {
			return -EINVAL;
		}
		val = raw_event_map_fn(attr_config);
	}
	else {
		return -EINVAL;
	}

	if (!validate_event_fn(val)) {
		return -ENOENT;
	}

	*(unsigned long *)(event_base + hw_config_offset) = val;
	*(unsigned long *)(event_base + hw_config_ext_offset) = extra_config;

	ereg_id = extra_reg_id_fn(val, extra_config);
	if (ereg_id >= 0) {
		*(unsigned long *)(event_base + extra_reg_config_offset) =
			extra_config;
		*(unsigned int *)(event_base + extra_reg_reg_offset) =
			extra_reg_msr_fn(ereg_id);
		*(int *)(event_base + extra_reg_idx_offset) =
			extra_reg_idx_fn(ereg_id);
	}

	ret = hw_event_init_fn(event);
	if (!ret) {
		*event_out = event;
	}
	return ret;
}

SYSCALL_POLICY_HELPER_SCOPE long
perf_event_alloc_body_result(void **event_out, const void *attr,
		size_t event_size, size_t attr_size, unsigned long alloc_flags,
		size_t event_attr_offset, size_t group_entry_offset,
		size_t sibling_list_offset, size_t sample_freq_offset,
		size_t nr_siblings_offset, size_t count_offset,
		size_t child_count_total_offset, size_t parent_offset,
		size_t hw_sample_period_offset, size_t hw_last_period_offset,
		size_t hw_period_left_offset, size_t use_invariant_tsc_offset,
		size_t hw_config_offset, size_t hw_config_ext_offset,
		size_t extra_reg_config_offset, size_t extra_reg_reg_offset,
		size_t extra_reg_idx_offset, unsigned long attr_type,
		unsigned long attr_config, int attr_freq,
		unsigned long attr_sample_freq, unsigned long attr_sample_period,
		unsigned long hardware_type, unsigned long hw_cache_type,
		unsigned long raw_type, unsigned long ref_cpu_cycles_config,
		syscall_policy_alloc_fn_t alloc_fn,
		syscall_mckfd_free_fn_t free_fn,
		sync_child_atomic64_set_fn_t atomic_set_fn,
		perf_event_map_fn_t hw_event_map_fn,
		perf_event_map_fn_t hw_cache_event_map_fn,
		perf_event_map_fn_t hw_cache_extra_reg_map_fn,
		perf_event_map_fn_t raw_event_map_fn,
		perf_event_validate_fn_t validate_event_fn,
		perf_extra_reg_id_fn_t extra_reg_id_fn,
		perf_extra_reg_msr_fn_t extra_reg_msr_fn,
		perf_extra_reg_idx_fn_t extra_reg_idx_fn,
		perf_hw_event_init_fn_t hw_event_init_fn)
{
	void *event;
	long ret;

	if (!event_out || !attr || !alloc_fn || !free_fn) {
		return -EINVAL;
	}

	event = alloc_fn(event_size, alloc_flags);
	if (!event) {
		return -ENOMEM;
	}

	ret = perf_event_alloc_init_body_result(event, attr, event_size,
			attr_size, event_attr_offset, group_entry_offset,
			sibling_list_offset, sample_freq_offset,
			nr_siblings_offset, count_offset,
			child_count_total_offset, parent_offset,
			hw_sample_period_offset, hw_last_period_offset,
			hw_period_left_offset, use_invariant_tsc_offset,
			attr_type, attr_config, attr_freq, attr_sample_freq,
			attr_sample_period, hardware_type,
			ref_cpu_cycles_config, atomic_set_fn);
	if (ret < 0) {
		free_fn(event);
		return ret;
	}
	if (ret > 0) {
		*event_out = event;
		return 0;
	}

	ret = perf_event_alloc_map_body_result(event_out, event,
			hw_config_offset, hw_config_ext_offset,
			extra_reg_config_offset, extra_reg_reg_offset,
			extra_reg_idx_offset, attr_type, attr_config,
			hardware_type, hw_cache_type, raw_type,
			hw_event_map_fn, hw_cache_event_map_fn,
			hw_cache_extra_reg_map_fn, raw_event_map_fn,
			validate_event_fn, extra_reg_id_fn, extra_reg_msr_fn,
			extra_reg_idx_fn, hw_event_init_fn);
	if (ret) {
		free_fn(event);
	}
	return ret;
}
