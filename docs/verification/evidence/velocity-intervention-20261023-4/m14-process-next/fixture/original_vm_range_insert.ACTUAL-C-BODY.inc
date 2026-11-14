static int vm_range_insert(struct process_vm *vm, struct vm_range *newrange)
{
	return process_vm_range_insert_result(&vm->vm_range_tree, newrange, vm,
			vm_range_insert_log_bridge, vm_range_insert_dump_bridge);
}
