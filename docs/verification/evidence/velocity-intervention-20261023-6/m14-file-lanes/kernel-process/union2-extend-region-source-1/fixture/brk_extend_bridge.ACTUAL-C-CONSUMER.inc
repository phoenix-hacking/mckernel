unsigned long brk_extend_bridge(void *vm, unsigned long old_end,
		unsigned long address, unsigned long vrflag)
{
	return extend_process_region((struct process_vm *)vm, old_end, address,
			vrflag);
}
