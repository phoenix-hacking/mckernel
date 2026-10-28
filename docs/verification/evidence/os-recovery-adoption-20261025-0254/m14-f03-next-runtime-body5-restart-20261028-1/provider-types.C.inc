typedef void *(*syscall_policy_alloc_fn_t)(size_t size, unsigned long flags);
typedef void (*syscall_mckfd_free_fn_t)(void *fdp);
typedef void (*sync_child_atomic64_set_fn_t)(void *count, long value);
typedef unsigned long (*perf_event_map_fn_t)(unsigned long config);
typedef int (*perf_event_validate_fn_t)(unsigned long hw_config);
typedef int (*perf_extra_reg_id_fn_t)(unsigned long hw_config,
		unsigned long hw_config_ext);
typedef unsigned int (*perf_extra_reg_msr_fn_t)(int id);
typedef int (*perf_extra_reg_idx_fn_t)(int id);
typedef int (*perf_hw_event_init_fn_t)(void *event);
