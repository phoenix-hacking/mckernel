		dkprintf("%s: non-NULL pte,page=%lx,page_is_in_memobj=%d,page->count=%d\n", __FUNCTION__, page, page ? page_is_in_memobj(page) : 0, page ? ihk_atomic_read(&page->count) : 0);
