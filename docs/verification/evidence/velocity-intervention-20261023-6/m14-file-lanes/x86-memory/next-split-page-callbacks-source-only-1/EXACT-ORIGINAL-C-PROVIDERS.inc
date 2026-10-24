static void x86_split_page_map_bridge(void *page)
{
	page_map(page);
}
static int x86_split_page_unmap_bridge(void *page)
{
	return page_unmap(page);
}
