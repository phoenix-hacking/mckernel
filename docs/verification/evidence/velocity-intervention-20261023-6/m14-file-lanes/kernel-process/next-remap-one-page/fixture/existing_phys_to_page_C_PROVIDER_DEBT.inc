struct page *phys_to_page(uintptr_t phys)
{
	return phys_to_page_lookup_body_result(phys,
			(unsigned long)page_hash, (unsigned long)page_hash_locks,
			PAGE_SHIFT, PHYS_PAGE_HASH_MASK, sizeof(page_hash[0]),
			sizeof(page_hash_locks[0]), page_hash_lock_bridge,
			page_hash_unlock_bridge,
			phys_to_page_lookup_orchestrate_result);
}
