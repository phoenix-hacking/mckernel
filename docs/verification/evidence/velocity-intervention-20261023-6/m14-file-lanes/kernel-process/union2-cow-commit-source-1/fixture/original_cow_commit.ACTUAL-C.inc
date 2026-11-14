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
