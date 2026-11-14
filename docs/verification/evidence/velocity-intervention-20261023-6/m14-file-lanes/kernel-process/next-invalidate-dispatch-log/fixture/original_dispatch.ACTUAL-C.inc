int process_memobj_invalidate_page_bridge(struct memobj *memobj,
						 uintptr_t phys,
						 size_t pgsize)
{
	return memobj_invalidate_page(memobj, phys, pgsize);
}
