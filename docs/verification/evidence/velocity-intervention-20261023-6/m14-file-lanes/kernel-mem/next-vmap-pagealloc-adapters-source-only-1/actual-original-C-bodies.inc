static void *original_mem_vmap_init_bridge(unsigned long start, unsigned long size,
		unsigned long unit)
{
	return ihk_pagealloc_init(start, size, unit);
}

unsigned long original_mem_vmap_alloc_bridge(void *desc, int npages,
		int p2align)
{
	return ihk_pagealloc_alloc(desc, npages, p2align);
}

void original_mem_vmap_free_bridge(void *desc, unsigned long address,
		int npages)
{
	ihk_pagealloc_free(desc, address, npages);
}
