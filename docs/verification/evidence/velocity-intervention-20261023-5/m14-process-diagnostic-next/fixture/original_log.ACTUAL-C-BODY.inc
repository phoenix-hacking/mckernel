PROCESS_SCHED_PUBLIC_BRIDGE void vm_range_insert_log_bridge(int event, struct process_vm *vm,
				       struct vm_range *newrange,
				       struct vm_range *range)
{
	if (event == PROCESS_VM_RANGE_INSERT_LOG_OVERLAP) {
		ekprintf("vm_range_insert(%p,%lx-%lx %x): overlap %lx-%lx %lx\n",
				vm, newrange->start, newrange->end, newrange->flag,
				range->start, range->end, range->flag);
	}
	else if (event == PROCESS_VM_RANGE_INSERT_LOG_SUCCESS) {
		dkprintf("vm_range_insert: %p,%p: %lx-%lx %x\n", vm,
				newrange, newrange->start, newrange->end,
				newrange->flag);
	}
}
