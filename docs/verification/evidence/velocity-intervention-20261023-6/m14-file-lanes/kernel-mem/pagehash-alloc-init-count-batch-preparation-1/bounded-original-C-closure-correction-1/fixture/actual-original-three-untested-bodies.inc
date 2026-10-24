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

static int original_page_hash_count_pages(void)
{
	return page_hash_count_pages_body_result((unsigned long)page_hash,
			(unsigned long)page_hash_locks, PHYS_PAGE_HASH_SIZE,
			sizeof(page_hash[0]), sizeof(page_hash_locks[0]),
			page_hash_lock_bridge, page_hash_unlock_bridge,
			page_hash_count_all_result);
}
