int page_unmap(struct page *page)
{
	return page_unmap_body_result(page,
			(unsigned long)page_hash_locks, PAGE_SHIFT,
			PHYS_PAGE_HASH_MASK, sizeof(page_hash_locks[0]),
			page_hash_lock_bridge, page_hash_unlock_bridge,
			page_unmap_orchestrate_result, page_unmap_log_bridge);
}
