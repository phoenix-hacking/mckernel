static void
munmap_all_free_ranges_bridge(void *vm)
{
	free_process_memory_ranges(vm);
}

static void
munmap_all_log_bridge(unsigned long addr, size_t size, int error)
{
	kprintf("munmap_all():do_munmap(%p,%lx) failed. %d\n",
			(void *)addr, size, error);
}

static void munmap_all(void)
{
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process_vm *vm = thread->vm;

	munmap_all_body_result(vm, &vm->memory_range_lock, &vm->region,
			offsetof(struct vm_range, start),
			offsetof(struct vm_range, end),
			offsetof(struct vm_regions, map_start),
			offsetof(struct vm_regions, map_end),
			munmap_write_lock_bridge, munmap_write_unlock_bridge,
			mprotect_lookup_bridge, mprotect_next_bridge,
			munmap_do_bridge, munmap_all_free_ranges_bridge,
			munmap_all_log_bridge);
} /* munmap_all() */
