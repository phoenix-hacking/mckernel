static int mc_perf_event_alloc(struct mc_perf_event **out,
			       struct perf_event_attr *attr)
{
	return perf_event_alloc_body_result((void **)out, attr,
			sizeof(struct mc_perf_event),
			sizeof(struct perf_event_attr),
			IHK_MC_AP_NOWAIT,
			__builtin_offsetof(struct mc_perf_event, attr),
			__builtin_offsetof(struct mc_perf_event, group_entry),
			__builtin_offsetof(struct mc_perf_event, sibling_list),
			__builtin_offsetof(struct mc_perf_event, sample_freq),
			__builtin_offsetof(struct mc_perf_event, nr_siblings),
			__builtin_offsetof(struct mc_perf_event, count),
			__builtin_offsetof(struct mc_perf_event, child_count_total),
			__builtin_offsetof(struct mc_perf_event, parent),
			__builtin_offsetof(struct mc_perf_event, hw.sample_period),
			__builtin_offsetof(struct mc_perf_event, hw.last_period),
			__builtin_offsetof(struct mc_perf_event, hw.period_left),
			__builtin_offsetof(struct mc_perf_event, use_invariant_tsc),
			__builtin_offsetof(struct mc_perf_event, hw_config),
			__builtin_offsetof(struct mc_perf_event, hw_config_ext),
			__builtin_offsetof(struct mc_perf_event, extra_reg.config),
			__builtin_offsetof(struct mc_perf_event, extra_reg.reg),
			__builtin_offsetof(struct mc_perf_event, extra_reg.idx),
			attr ? attr->type : 0, attr ? attr->config : 0,
			attr ? attr->freq : 0,
			attr ? attr->sample_freq : 0,
			attr ? attr->sample_period : 0,
			PERF_TYPE_HARDWARE, PERF_TYPE_HW_CACHE, PERF_TYPE_RAW,
			PERF_COUNT_HW_REF_CPU_CYCLES,
			perf_event_alloc_kmalloc_bridge,
			perf_event_alloc_free_bridge,
			sync_child_count_set_bridge,
			ihk_mc_hw_event_map, ihk_mc_hw_cache_event_map,
			ihk_mc_hw_cache_extra_reg_map, ihk_mc_raw_event_map,
			ihk_mc_validate_event, ihk_mc_get_extra_reg_id,
			ihk_mc_get_extra_reg_msr, ihk_mc_get_extra_reg_idx,
			perf_event_alloc_hw_init_bridge);
}

static int
perf_event_open_alloc_event_bridge(void **event_out, void *attr)
{
	return mc_perf_event_alloc((struct mc_perf_event **)event_out,
			(struct perf_event_attr *)attr);
}
