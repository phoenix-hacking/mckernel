void *process_alloc_bridge(unsigned long size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}
