struct vm_range *process_add_range_alloc_bridge(unsigned long size)
{
	return kmalloc_tracked(size, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
}
