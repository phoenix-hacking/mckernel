#ifdef MCKERNEL_RUST_PAGE_HELPERS
extern unsigned long page_hash_lock_bridge(unsigned long lock_addr);
#else
PAGE_UNMAP_PUBLIC_BRIDGE unsigned long page_hash_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}
#endif

#ifdef MCKERNEL_RUST_PAGE_HELPERS
extern void page_hash_unlock_bridge(unsigned long lock_addr,
		unsigned long flags);
#else
PAGE_UNMAP_PUBLIC_BRIDGE void page_hash_unlock_bridge(unsigned long lock_addr,
		unsigned long flags)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, flags);
}
#endif

#ifdef MCKERNEL_RUST_PAGE_HELPERS
extern void page_hash_lock_init_bridge(unsigned long lock_addr);
#else
static void page_hash_lock_init_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_init((ihk_spinlock_t *)lock_addr);
}
#endif

