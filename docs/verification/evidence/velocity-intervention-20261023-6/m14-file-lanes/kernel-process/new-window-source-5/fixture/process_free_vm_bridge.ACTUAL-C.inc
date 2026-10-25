void process_free_vm_bridge(void *vm)
{
	kfree_tracked(vm, __FILE__, __LINE__);
}
