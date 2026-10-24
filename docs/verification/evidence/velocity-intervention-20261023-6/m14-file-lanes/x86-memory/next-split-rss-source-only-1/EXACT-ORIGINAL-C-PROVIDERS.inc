static void x86_split_rss_add_bridge(size_t size, size_t pgsize)
{
	memory_stat_rss_add(size, pgsize);
}
static void x86_split_rss_sub_bridge(size_t size, size_t pgsize)
{
	memory_stat_rss_sub(size, pgsize);
}
