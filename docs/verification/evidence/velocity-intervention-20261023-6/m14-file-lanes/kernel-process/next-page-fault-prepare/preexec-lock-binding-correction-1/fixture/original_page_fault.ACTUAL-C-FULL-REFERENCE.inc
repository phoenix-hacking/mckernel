int page_fault_process_memory_range(struct process_vm *vm,
				    struct vm_range *range,
				    uintptr_t fault_addr, uint64_t reason)
{
	int error;
	pte_t *ptep;
	void *pgaddr;
	size_t pgsize;
	int p2align;
	enum ihk_mc_pt_attribute attr;
	uintptr_t phys;
	struct page *page = NULL;
	unsigned long memobj_flag = 0;
	int private_range, patching_to_rdonly;
	int devfile_or_hugetlbfs_or_premap, regfile_or_shm;

	if (get_this_cpu_local_var()->current->profile) {
		dkprintf("%s: 0x%lx @ %s\n",
				__func__, fault_addr,
				range->memobj && range->memobj->path ?
				range->memobj->path :
				range->private_data ? "XPMEM" : "<unknown>");
	}

	dkprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx)\n", vm, range->start, range->end, range->flag, fault_addr, reason);
	ihk_mc_spinlock_lock_noirq(&vm->page_table_lock);
	/*****/
	ptep = ihk_mc_pt_lookup_pte(vm->address_space->page_table,
			(void *)fault_addr, range->pgshift, &pgaddr, &pgsize,
			&p2align);
	if (!(reason & (PF_PROT | PF_PATCH)) && ptep && !pte_is_null(ptep)
			&& !pte_is_fileoff(ptep, pgsize)) {
		if (!pte_is_present(ptep)) {
			error = -EFAULT;
			kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):PROT_NONE. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
			goto out;
		}
		error = 0;
		goto out;
	}
	if ((reason & PF_PROT) && (!ptep || !pte_is_present(ptep))) {
		flush_tlb_single(fault_addr);
		error = 0;
		goto out;
	}
	/*****/
	dkprintf("%s: pgaddr=%lx,range->start=%lx,range->end=%lx,pgaddr+pgsize=%lx\n", __FUNCTION__, pgaddr, range->start, range->end, pgaddr + pgsize);
	while (((uintptr_t)pgaddr < range->start)
			|| (range->end < ((uintptr_t)pgaddr + pgsize))) {
		ptep = NULL;
		error = arch_get_smaller_page_size(NULL, pgsize, &pgsize, &p2align);
		if (error) {
			kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(pte) failed. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
			goto out;
		}
		pgaddr = (void *)(fault_addr & ~(pgsize - 1));
	}

	arch_adjust_allocate_page_size(vm->address_space->page_table,
				       fault_addr, ptep, &pgaddr, &pgsize);

	/*****/
	dkprintf("%s: ptep=%lx,pte_is_null=%d,pte_is_fileoff=%d\n", __FUNCTION__, ptep, ptep ? pte_is_null(ptep) : -1, ptep ? pte_is_fileoff(ptep, pgsize) : -1);
	if (!ptep || pte_is_null(ptep) || pte_is_fileoff(ptep, pgsize)) {
		phys = NOPHYS;
		if (range->memobj) {
			off_t off;

			if (!ptep || !pte_is_fileoff(ptep, pgsize)) {
				off = range->objoff + ((uintptr_t)pgaddr - range->start);
			}
			else {
				off = pte_get_off(ptep, pgsize);
			}
			error = memobj_get_page(range->memobj, off, p2align,
                                       &phys, &memobj_flag, fault_addr);
			if (error) {
				struct memobj *obj;

				if (zeroobj_create(&obj)) {
					panic("PFPMR: zeroobj_crate");
				}

				if (range->memobj != obj) {
					goto out;
				}
			}
			// memory_stat_rss_add() is called downstream, i.e. memobj_get_page() to check page->count
		}
		if (phys == NOPHYS) {
			void *virt = NULL;
			size_t npages;

retry:
			npages = pgsize / PAGE_SIZE;
			virt = _ihk_mc_alloc_aligned_pages_node(npages, p2align, IHK_MC_AP_NOWAIT |
					((range->flag & VR_AP_USER) ? IHK_MC_AP_USER : 0), -1, IHK_MC_PG_USER, fault_addr, __FILE__, __LINE__);
			if (!virt && !range->pgshift && (pgsize != PAGE_SIZE)) {
				error = arch_get_smaller_page_size(NULL, pgsize, &pgsize, &p2align);
				if (error) {
					kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(anon) failed. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
					goto out;
				}
				ptep = NULL;
				pgaddr = (void *)(fault_addr & ~(pgsize - 1));
				goto retry;
			}
			if (!virt) {
				error = -ENOMEM;
				kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):cannot allocate new page. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
				goto out;
			}
			dkprintf("%s: clearing 0x%lx:%lu\n",
					__FUNCTION__, pgaddr, pgsize);
#ifdef PROFILE_ENABLE
			profile_event_add(PROFILE_page_fault_anon_clr, pgsize);
#endif // PROFILE_ENABLE
			memset(virt, 0, pgsize);
			phys = virt_to_phys(virt);
			if (phys_to_page(phys)) {
				dkprintf("%s: NOPHYS,phys=%lx,vmr(%lx-%lx),flag=%x,fa=%lx,reason=%x\n",
						 __FUNCTION__, page_to_phys(page),
						 range->start, range->end, range->flag, fault_addr, reason);
				
				page_map(phys_to_page(phys));
			}
		}
	}
	else {
		phys = pte_get_phys(ptep);
	}

	page = phys_to_page(phys);

	attr = arch_vrflag_to_ptattr(range->flag | memobj_flag, reason, ptep);

	/* Copy on write */

	private_range = (range->flag & VR_PRIVATE);
	patching_to_rdonly =
		((reason & PF_PATCH) && !(range->flag & VR_PROT_WRITE));

	/* device file map, hugetlbfs file map, pre-mapped file map */
	devfile_or_hugetlbfs_or_premap =
		(!page &&
		 (range->memobj && !(range->memobj->flags | MF_ZEROOBJ)));

	/* regular file map, Sys V shared memory map */
	regfile_or_shm =
		(page &&
		 (page_is_in_memobj(page) || page_is_multi_mapped(page)));

	if ((private_range || patching_to_rdonly) &&
	    (devfile_or_hugetlbfs_or_premap || regfile_or_shm)) {

		if (!(attr & PTATTR_DIRTY)) {
			attr &= ~PTATTR_WRITABLE;
		}
		else {
			void *virt;
			size_t npages;

			if (!page) {
				kprintf("%s: WARNING: cow on non-struct-page-managed page\n", __FUNCTION__);
			}

			npages = pgsize / PAGE_SIZE;
			virt = _ihk_mc_alloc_aligned_pages_node(npages, p2align, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_USER, fault_addr, __FILE__, __LINE__);
			if (!virt) {
				error = -ENOMEM;
				kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):cannot allocate copy page. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
				goto out;
			}
			dkprintf("%s: cow,copying virt:%lx<-%lx,phys:%lx<-%lx,pgsize=%lu\n",
					 __FUNCTION__, virt, phys_to_virt(phys), virt_to_phys(virt), phys, pgsize);
			memcpy(virt, phys_to_virt(phys), pgsize);

			/* Count COW-source pointed-to by only fileobj
			 *  The steps in test/rusage/005:
			 *  (1) Private-map regular file
			 *  (2) Don't touch the page
			 *  (3) Fork and then the child touches the page
			 *  (4) Page-in the COW-source
			 *  (5) Reach here
			 */
			if (rusage_memory_stat_add(range, phys, pgsize, pgsize)) {
				dkprintf("%lx+,%s: COW-source pointed-to by only fileobj, calling memory_stat_rss_add(),pgsize=%ld\n",
						phys, __FUNCTION__, pgsize);
			}
			if (page) {
				if (page_unmap(page)) {
					dkprintf("%lx-,%s: cow,calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n", phys, __FUNCTION__, pgsize, pgsize);
					rusage_memory_stat_sub(range->memobj, pgsize, pgsize); 
				}
			}
			phys = virt_to_phys(virt);
			page = phys_to_page(phys);
		}
	}
	else if (!(range->flag & VR_PRIVATE)) { /*VR_SHARED*/
		if (!(attr & PTATTR_DIRTY)) {
			if (!(range->flag & VR_STACK)) {
				attr &= ~PTATTR_WRITABLE;
			}
		}
	}

	/*****/
	if (ptep && !pgsize_is_contiguous(pgsize)) {
		if (!(reason & PF_PATCH) &&
		    rusage_memory_stat_add(range, phys, pgsize, pgsize)) {
			/* on-demand paging, phys pages are obtained by ihk_mc_alloc_aligned_pages_user() or get_page() */
			dkprintf("%lx+,%s: (on-demand paging && first map) || cow,calling memory_stat_rss_add(),phys=%lx,pgsize=%ld\n",
					 phys, __FUNCTION__, phys, pgsize);
		} else {
			dkprintf("%s: !calling memory_stat_rss_add(),phys=%lx,pgsize=%ld\n",
					 __FUNCTION__, phys, pgsize);
		}

		dkprintf("%s: attr=%x\n", __FUNCTION__, attr);
		error = ihk_mc_pt_set_pte(vm->address_space->page_table, ptep,
		                          pgsize, phys, attr);
		if (error) {
			kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):set_pte failed. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
			goto out;
		}
		dkprintf("%s: non-NULL pte,page=%lx,page_is_in_memobj=%d,page->count=%d\n", __FUNCTION__, page, page ? page_is_in_memobj(page) : 0, page ? ihk_atomic_read(&page->count) : 0);
	}
	else {
		error = ihk_mc_pt_set_range(vm->address_space->page_table, vm,
		                            pgaddr, pgaddr + pgsize, phys,
					    attr, range->pgshift, range, 1);
		if (error) {
			kprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):set_range failed. %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
			goto out;
		}
		// memory_stat_rss_add() is called in downstream with !memobj check
	}
	flush_tlb_single(fault_addr);

	error = 0;
	page = NULL;

out:
	ihk_mc_spinlock_unlock_noirq(&vm->page_table_lock);
	if (page) {
		/* Unmap stray struct page */
		dkprintf("%s: out,phys=%lx,vmr(%lx-%lx),flag=%x,fa=%lx,reason=%x\n",
				 __FUNCTION__, page_to_phys(page),
				 range->start, range->end, range->flag, fault_addr, reason);
		if (page_unmap(page)) {
			dkprintf("%lx-,%s: out,calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n", page_to_phys(page), __FUNCTION__, pgsize, pgsize);
			rusage_memory_stat_sub(range->memobj, pgsize, pgsize); 
		}
	}
	dkprintf("page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx): %d\n", vm, range->start, range->end, range->flag, fault_addr, reason, error);
	return error;
}
