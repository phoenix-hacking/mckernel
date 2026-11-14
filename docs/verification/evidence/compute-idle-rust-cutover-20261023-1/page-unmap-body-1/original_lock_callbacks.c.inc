static unsigned long page_hash_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

static void page_hash_unlock_bridge(unsigned long lock_addr,
		unsigned long flags)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, flags);
}

