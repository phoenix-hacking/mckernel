int sync_one_page(void *arg0, page_table_t pt, pte_t *ptep,
		  void *pgaddr, int pgshift)
{
	struct sync_args *args = arg0;
	const size_t pgsize = (size_t)1 << pgshift;
	int error;
	uintptr_t phys;

	dkprintf("sync_one_page(%p,%p,%p %#lx,%p,%d)\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift);
	if (pte_is_null(ptep) || pte_is_fileoff(ptep, pgsize)
			|| !pte_is_dirty(ptep, pgsize)) {
		error = 0;
		goto out;
	}

	pte_clear_dirty(ptep, pgsize);
	flush_tlb_single((uintptr_t)pgaddr);	/* XXX: TLB flush */

	phys = pte_get_phys(ptep);
	if (args->memobj->flags & MF_ZEROFILL) {
		error = 0;
		goto out;
	}

	error = memobj_flush_page(args->memobj, phys, pgsize);
	if (error) {
		ekprintf("sync_one_page(%p,%p,%p %#lx,%p,%d):"
				"flush failed. %d\n",
				arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
		pte_set_dirty(ptep, pgsize);
		goto out;
	}

	error = 0;
out:
	dkprintf("sync_one_page(%p,%p,%p %#lx,%p,%d):%d\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
	return error;
}
