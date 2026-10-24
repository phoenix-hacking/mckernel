static int page_hash_count_pages(void)
{
	return page_hash_count_pages_body_result((unsigned long)page_hash,
			(unsigned long)page_hash_locks, PHYS_PAGE_HASH_SIZE,
			sizeof(page_hash[0]), sizeof(page_hash_locks[0]),
			page_hash_lock_bridge, page_hash_unlock_bridge,
			page_hash_count_all_result);
}
