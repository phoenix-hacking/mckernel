#ifdef MCKERNEL_RUST_PROCESS_HELPERS
            /* A successful pointer passes to the existing zero/map tail.
             * Error1 passes to the existing out: unlock, with no page. */
            if (process_page_fault_anon_allocate_body_result(vm, range,
                    fault_addr, reason, &ptep, &pgaddr, &pgsize, &p2align,
                    &virt, &error))
                goto out;
#else
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
#endif
