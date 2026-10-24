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

