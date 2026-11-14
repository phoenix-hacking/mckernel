static int x86_clear_page_unmap_bridge(void *page)
{
	return page_unmap(page);
}
