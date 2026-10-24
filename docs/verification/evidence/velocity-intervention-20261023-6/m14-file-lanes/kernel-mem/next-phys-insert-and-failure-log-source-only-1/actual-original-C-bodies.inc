static void phys_to_page_insert_hash_log_bridge(uint64_t phys)
{
	(void)phys;
	kprintf("%s: error allocating page\n", "phys_to_page_insert_hash");
}

struct page *phys_to_page_insert_hash(uint64_t phys)
{
	return phys_to_page_insert_hash_body_result(phys,
			(unsigned long)page_hash, (unsigned long)page_hash_locks,
			PAGE_SHIFT, PHYS_PAGE_HASH_MASK, sizeof(page_hash[0]),
			sizeof(page_hash_locks[0]), sizeof(struct page),
			IHK_MC_AP_CRITICAL, page_hash_lock_bridge,
			page_hash_unlock_bridge, page_hash_alloc_bridge,
			phys_to_page_insert_hash_orchestrate_result,
			phys_to_page_insert_hash_log_bridge);
}
