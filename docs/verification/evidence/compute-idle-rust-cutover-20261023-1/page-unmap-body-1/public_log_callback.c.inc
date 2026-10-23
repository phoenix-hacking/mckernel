PAGE_UNMAP_PUBLIC_BRIDGE void page_unmap_log_bridge(int event, struct page *page, int ret)
{
	switch (event) {
	case PAGE_UNMAP_LOG_ENTER:
		dkprintf("page_unmap(%p %x %d)\n",
				page, page->mode, page->count);
		break;
	case PAGE_UNMAP_LOG_STILL_MAPPED:
		/* other mapping exist */
		dkprintf("page_unmap(%p %x %d): 0\n",
				page, page->mode, page->count);
		break;
	case PAGE_UNMAP_LOG_UNMAPPED:
		dkprintf("page_unmap(%p %x %d): %d\n",
				page, page->mode, page->count, ret);
		break;
	default:
		break;
	}
}
