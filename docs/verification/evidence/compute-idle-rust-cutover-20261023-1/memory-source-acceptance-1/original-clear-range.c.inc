static int clear_range_old_action(struct clear_range_args *args, pte_t old,
		size_t pgsize, unsigned long *physp, struct page **pagep,
		int *fileoffp)
{
	int is_fileoff;
	int is_dirty;
	int has_page;
	int page_in_memobj;
	unsigned int memobj_flags = args->memobj ? args->memobj->flags : 0;

	x86_clear_range_old_entry_result(old, pgsize, physp, &is_fileoff,
			&is_dirty);
	if (fileoffp)
		*fileoffp = is_fileoff;

	*pagep = NULL;
	if (!is_fileoff)
		*pagep = phys_to_page(*physp);

	has_page = *pagep != NULL;
	page_in_memobj = has_page && page_is_in_memobj(*pagep);

	return x86_clear_range_old_action_result(is_fileoff,
			args->free_physical, has_page, page_in_memobj,
			is_dirty, args->memobj != NULL,
			memobj_flags & (MF_ZEROFILL | MF_PRIVATE),
			memobj_flags & MF_XPMEM);
}

static int x86_clear_old_action_bridge(void *args0, unsigned long old,
		size_t pgsize, unsigned long *physp, void **pagep,
		int *fileoffp)
{
	struct page *page = NULL;
	int ret;

	ret = clear_range_old_action(args0, old, pgsize, physp, &page,
			fileoffp);
	if (pagep)
		*pagep = page;

	return ret;
}
