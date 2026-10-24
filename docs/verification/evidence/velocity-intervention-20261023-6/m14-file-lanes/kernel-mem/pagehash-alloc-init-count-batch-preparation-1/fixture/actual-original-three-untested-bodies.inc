static struct page *original_page_hash_alloc_bridge(unsigned long size, int flag)
{
	return kmalloc_tracked(size, flag, __FILE__, __LINE__);
}

static void original_page_init(void)
{
	page_hash_tables_init_body_result((unsigned long)page_hash,
			(unsigned long)page_hash_locks, PHYS_PAGE_HASH_SIZE,
			sizeof(page_hash[0]), sizeof(page_hash_locks[0]),
			page_hash_lock_init_bridge, page_hash_bucket_init_result);
}

static int original_page_hash_count_pages(void);
#ifdef MCKERNEL_RUST_MEM_HELPERS
static int mem_query_free_node_pages_bridge(int node)
{
	int pages = 0;

	if (node < 0 || node >= ihk_mc_get_nr_numa_nodes())
		return 0;

#ifdef IHK_RBTREE_ALLOCATOR
	pages = memory_nodes[node].nr_free_pages;
#else
	{
		struct ihk_page_allocator_desc *pa_allocator;

		for (pa_allocator = ((typeof(*pa_allocator) *)((char *)((&memory_nodes[node].allocators)->next) - offsetof(typeof(*pa_allocator), list))); &pa_allocator->list != (&memory_nodes[node].allocators); pa_allocator = ((typeof(*pa_allocator) *)((char *)(pa_allocator->list.next) - offsetof(typeof(*pa_allocator), list)))) {
			int __pages = ihk_pagealloc_query_free(pa_allocator);

			kprintf("McKernel free pages in (0x%lx - 0x%lx): %d\n",
					pa_allocator->start, pa_allocator->end, __pages);
			pages += __pages;
		}
	}
#endif

	return pages;
}
