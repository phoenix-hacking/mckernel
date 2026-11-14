static struct vm_range *
arch_process_vm_rw_lookup_range_bridge(void *vm, unsigned long start,
		unsigned long end)
{
	return lookup_process_memory_range((struct process_vm *)vm, start, end);
}
