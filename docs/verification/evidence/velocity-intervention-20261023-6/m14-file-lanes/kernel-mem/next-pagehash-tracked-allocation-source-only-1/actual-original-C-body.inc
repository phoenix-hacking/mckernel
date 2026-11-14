static struct page *page_hash_alloc_bridge(unsigned long size, int flag)
{
	return kmalloc_tracked(size, flag, __FILE__, __LINE__);
}
