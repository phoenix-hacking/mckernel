void process_sync_range_log_bridge(struct process_vm *vm,
				   struct vm_range *range, unsigned long start,
				   unsigned long end, int error)
{
	ekprintf("sync_process_memory_range(%p,%p,%#lx,%#lx):"
			"visit failed%d\n", vm, range, start, end, error);
}
