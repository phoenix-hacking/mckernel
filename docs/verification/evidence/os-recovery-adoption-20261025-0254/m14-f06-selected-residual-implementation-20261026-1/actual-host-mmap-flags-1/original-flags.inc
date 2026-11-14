
int
arch_mmap_supported_flags_bridge(void)
{
	return 0
		| MAP_SHARED
		| MAP_PRIVATE
		| MAP_FIXED
		| MAP_ANONYMOUS
		| MAP_LOCKED
		| MAP_POPULATE
		| MAP_HUGETLB
		| (0x3FU << MAP_HUGE_SHIFT);
}
int
arch_mmap_ignored_flags_bridge(void)
{
	return 0
#ifdef USE_NOCACHE_MMAP
		| MAP_32BIT
#endif
		| MAP_DENYWRITE
		| MAP_NORESERVE
		| MAP_STACK;
}
int
arch_mmap_error_flags_bridge(void)
{
	return 0
#ifndef USE_NOCACHE_MMAP
		| MAP_32BIT
#endif
		| MAP_GROWSDOWN
		| MAP_EXECUTABLE
		| MAP_NONBLOCK;
}
