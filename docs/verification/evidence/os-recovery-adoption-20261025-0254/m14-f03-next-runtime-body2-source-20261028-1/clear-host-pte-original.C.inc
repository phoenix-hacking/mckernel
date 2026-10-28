long clear_host_pte(uintptr_t addr, size_t len, int holding_memory_range_lock)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return clear_host_pte_body_result(thread->vm, addr, len,
			holding_memory_range_lock,
			offsetof(struct process_vm, is_memory_range_lock_taken),
			ihk_mc_get_processor_id(), __NR_munmap,
			syscall_do_syscall3_bridge, clear_host_pte_log_bridge);
}
