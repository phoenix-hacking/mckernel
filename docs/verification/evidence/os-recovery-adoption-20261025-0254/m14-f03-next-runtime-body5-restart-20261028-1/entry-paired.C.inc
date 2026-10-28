#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_SYNC_CHILD_EVENT)
/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
struct f03_perf_allocation_binding {
    unsigned long alloc_flags,hardware_type,cache_type,raw_type,reference_cycles;
    syscall_policy_alloc_fn_t allocate;
    syscall_mckfd_free_fn_t release;
    sync_child_atomic64_set_fn_t atomic_set;
    perf_event_map_fn_t hardware_map,cache_map,cache_extra_map,raw_map;
    perf_event_validate_fn_t validate;
    perf_extra_reg_id_fn_t extra_id;
    perf_extra_reg_msr_fn_t extra_msr;
    perf_extra_reg_idx_fn_t extra_index;
    perf_hw_event_init_fn_t initialize;
};
const struct f03_perf_allocation_binding f03_perf_allocation_binding_v1={
    .alloc_flags=IHK_MC_AP_NOWAIT,.hardware_type=PERF_TYPE_HARDWARE,.cache_type=PERF_TYPE_HW_CACHE,
    .raw_type=PERF_TYPE_RAW,.reference_cycles=PERF_COUNT_HW_REF_CPU_CYCLES,
    .allocate=perf_event_alloc_kmalloc_bridge,.release=perf_event_alloc_free_bridge,
    .atomic_set=sync_child_count_set_bridge,.hardware_map=ihk_mc_hw_event_map,
    .cache_map=ihk_mc_hw_cache_event_map,.cache_extra_map=ihk_mc_hw_cache_extra_reg_map,
    .raw_map=ihk_mc_raw_event_map,.validate=ihk_mc_validate_event,.extra_id=ihk_mc_get_extra_reg_id,
    .extra_msr=ihk_mc_get_extra_reg_msr,.extra_index=ihk_mc_get_extra_reg_idx,
    .initialize=perf_event_alloc_hw_init_bridge,
};
extern int f03_perf_event_allocate_v1(void **,void *);
#define perf_event_open_alloc_event_bridge f03_perf_event_allocate_v1
#else
#line 21419
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
#endif
#line 21464
