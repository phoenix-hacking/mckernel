int remap_one_page(void *arg0, page_table_t pt, pte_t *ptep,
		   void *pgaddr, int pgshift)
{
	struct rfp_args * const args = arg0;
	const size_t pgsize = (size_t)1 << pgshift;
	int error;
	off_t off;
	pte_t apte = PTE_NULL;
	uintptr_t phys;
	struct page *page;

	dkprintf("remap_one_page(%p,%p,%p %#lx,%p,%d)\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift);

	off = args->off + ((uintptr_t)pgaddr - args->start);
	pte_make_fileoff(off, 0, pgsize, &apte);

	pte_xchg(ptep, &apte);
	flush_tlb_single((uintptr_t)pgaddr);	/* XXX: TLB flush */

	if (pte_is_null(&apte) || pte_is_fileoff(&apte, pgsize)) {
		error = 0;
		goto out;
	}
	phys = pte_get_phys(&apte);

	if (pte_is_dirty(&apte, pgsize)) {
		memobj_flush_page(args->memobj, phys, pgsize);	/* XXX: in lock period */
	}

	page = phys_to_page(phys);
	if (page && page_unmap(page)) {
		_ihk_mc_free_pages(phys_to_virt(phys), pgsize/PAGE_SIZE, IHK_MC_PG_USER, __FILE__, __LINE__);
		dkprintf("%lx-,%s: calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n", phys, __FUNCTION__, pgsize, pgsize);
		rusage_memory_stat_sub(args->memobj, pgsize, pgsize); 
	}

	error = 0;
out:
	dkprintf("remap_one_page(%p,%p,%p %#lx,%p,%d): %d\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
	return error;
}
