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
