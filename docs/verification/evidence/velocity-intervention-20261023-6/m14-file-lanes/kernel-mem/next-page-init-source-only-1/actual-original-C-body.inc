static void page_init(void)
{
	page_hash_tables_init_body_result((unsigned long)page_hash,
			(unsigned long)page_hash_locks, PHYS_PAGE_HASH_SIZE,
			sizeof(page_hash[0]), sizeof(page_hash_locks[0]),
			page_hash_lock_init_bridge, page_hash_bucket_init_result);
}
