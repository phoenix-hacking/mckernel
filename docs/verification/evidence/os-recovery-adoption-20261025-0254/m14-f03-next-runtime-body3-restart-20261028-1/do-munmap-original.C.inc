int do_munmap(void *addr, size_t len, int holding_memory_range_lock)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return do_munmap_body_result(thread->vm, thread->proc,
			(uintptr_t)addr, len, holding_memory_range_lock,
			offsetof(struct process, straight_va),
			offsetof(struct process, straight_len),
			do_munmap_begin_bridge, do_munmap_remove_range_bridge,
			do_munmap_clear_host_bridge, do_munmap_set_host_bridge,
			do_munmap_finish_bridge, do_munmap_log_bridge);
}
