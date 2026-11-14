do_munmap_body_result(void *vm, void *proc, unsigned long addr, size_t len,
		int holding_memory_range_lock,
		size_t proc_straight_va_offset,
		size_t proc_straight_len_offset,
		do_munmap_void_fn_t begin_fn,
		do_munmap_remove_range_fn_t remove_range_fn,
		do_munmap_clear_host_fn_t clear_host_pte_fn,
		mprotect_set_host_vma_fn_t set_host_vma_fn,
		do_munmap_void_fn_t finish_fn, do_munmap_log_fn_t log_fn)
{
	unsigned long straight_va;
	size_t straight_len;
	int ro_freed = 0;
	int error;

	if (begin_fn)
		begin_fn();

	error = remove_range_fn ? remove_range_fn(vm, addr, addr + len,
			&ro_freed) : -EINVAL;

	straight_va = *(unsigned long *)syscall_offset_ptr(proc,
			proc_straight_va_offset);
	straight_len = *(size_t *)syscall_offset_ptr(proc,
			proc_straight_len_offset);
	if (!straight_va || addr < straight_va ||
			addr + len > straight_va + straight_len) {
		if (error || !ro_freed) {
			if (clear_host_pte_fn) {
				long clear_error = clear_host_pte_fn(addr, len,
						holding_memory_range_lock);
				if (!error)
					error = (int)clear_error;
			}
		}
		else {
			error = set_host_vma_fn ? set_host_vma_fn(addr, len,
					PROT_READ | PROT_WRITE | PROT_EXEC,
					holding_memory_range_lock) : -EINVAL;
		}
	}

	if (finish_fn)
		finish_fn();
	if (log_fn)
		log_fn(addr, len, error);
	return error;
}
