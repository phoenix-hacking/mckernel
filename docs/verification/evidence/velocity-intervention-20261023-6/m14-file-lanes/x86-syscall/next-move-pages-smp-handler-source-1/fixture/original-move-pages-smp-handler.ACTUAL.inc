int move_pages_smp_handler(int cpu_index, int nr_cpus, void *arg)
{
	int i, i_s, i_e, phase = 1;
	struct move_pages_smp_req *mpsr =
		(struct move_pages_smp_req *)arg;
	struct process_vm *vm = mpsr->proc->vm;
	int count = mpsr->count;
	struct page_table *save_pt;
	extern struct page_table *get_init_page_table(void);

	i_s = (count / nr_cpus) * cpu_index;
	i_e = i_s + (count / nr_cpus);
	if (cpu_index == (nr_cpus - 1)) {
		i_e = count;
	}

	/* Load target process' PT so that we can access user-space */
	save_pt = get_this_cpu_local_var()->current == &get_this_cpu_local_var()->idle ?
		get_init_page_table() :
		get_this_cpu_local_var()->current->vm->address_space->page_table;

	if (save_pt != vm->address_space->page_table) {
		ihk_mc_load_page_table(vm->address_space->page_table);
	}
	else {
		save_pt = NULL;
	}

	if (nr_cpus == 1) {
		switch (cpu_index) {
			case 0:
				memcpy(mpsr->virt_addr, mpsr->user_virt_addr,
						sizeof(void *) * count);
				if (mpsr->user_nodes) {
					memcpy(mpsr->nodes, mpsr->user_nodes,
							sizeof(int) * count);
				}
				memset(mpsr->ptep, 0, sizeof(pte_t) * count);
				memset(mpsr->status, 0, sizeof(int) * count);
				memset(mpsr->nr_pages, 0, sizeof(int) * count);
				memset(mpsr->dst_phys, 0,
						sizeof(unsigned long) * count);
				mpsr->nodes_ready = 1;
				break;

			default:
				break;
		}
	}
	else if (nr_cpus > 1 && nr_cpus < 4) {
		switch (cpu_index) {
			case 0:
				memcpy(mpsr->virt_addr, mpsr->user_virt_addr,
						sizeof(void *) * count);
				if (mpsr->user_nodes) {
					memcpy(mpsr->nodes, mpsr->user_nodes,
							sizeof(int) * count);
				}
				mpsr->nodes_ready = 1;
				break;
			case 1:
				memset(mpsr->ptep, 0, sizeof(pte_t) * count);
				memset(mpsr->status, 0, sizeof(int) * count);
				memset(mpsr->nr_pages, 0, sizeof(int) * count);
				memset(mpsr->dst_phys, 0,
						sizeof(unsigned long) * count);
				break;

			default:
				break;
		}
	}
	else if (nr_cpus >= 4 && nr_cpus < 7) {
		switch (cpu_index) {
			case 0:
				memcpy(mpsr->virt_addr, mpsr->user_virt_addr,
						sizeof(void *) * count);
				break;
			case 1:
				if (mpsr->user_nodes) {
					memcpy(mpsr->nodes, mpsr->user_nodes,
							sizeof(int) * count);
				}
				mpsr->nodes_ready = 1;
				break;
			case 2:
				memset(mpsr->ptep, 0, sizeof(pte_t) * count);
				memset(mpsr->status, 0, sizeof(int) * count);
				break;
			case 3:
				memset(mpsr->nr_pages, 0, sizeof(int) * count);
				memset(mpsr->dst_phys, 0,
						sizeof(unsigned long) * count);
				break;

			default:
				break;
		}
	}
	else {
		switch (cpu_index) {
			case 0:
				memcpy(mpsr->virt_addr, mpsr->user_virt_addr,
						sizeof(void *) * (count / 2));
				break;
			case 1:
				memcpy(mpsr->virt_addr + (count / 2),
						mpsr->user_virt_addr + (count / 2),
						sizeof(void *) * (count / 2));
				break;
			case 2:
				if (mpsr->user_nodes) {
					memcpy(mpsr->nodes, mpsr->user_nodes,
							sizeof(int) * count);
				}
				mpsr->nodes_ready = 1;
				break;
			case 3:
				memset(mpsr->ptep, 0, sizeof(pte_t) * count);
				break;
			case 4:
				memset(mpsr->status, 0, sizeof(int) * count);
				break;
			case 5:
				memset(mpsr->nr_pages, 0, sizeof(int) * count);
				break;
			case 6:
				memset(mpsr->dst_phys, 0,
						sizeof(unsigned long) * count);
				break;
			default:
				break;
		}
	}

	while (!(volatile int)mpsr->nodes_ready) {
		cpu_pause();
	}

	/* NUMA verification in parallel */
	if (mpsr->user_nodes) {
		for (i = i_s; i < i_e; i++) {
			if (mpsr->nodes[i] < 0 ||
					mpsr->nodes[i] >= ihk_mc_get_nr_numa_nodes() ||
					!test_bit(mpsr->nodes[i],
						mpsr->proc->vm->numa_mask)) {
				mpsr->phase_ret = -EINVAL;
				break;
			}
		}
	}

	/* Barrier */
	ihk_atomic_inc(&mpsr->phase_done);
	while (ihk_atomic_read(&mpsr->phase_done) <
			(phase * nr_cpus)) {
		cpu_pause();
	}

	if (mpsr->phase_ret != 0) {
		goto out;
	}

	dkprintf("%s: phase %d done\n", __FUNCTION__, phase);
	++phase;

	/* PTE lookup in parallel */
	for (i = i_s; i < i_e; i++) {
		void *phys;
		size_t pgsize;
		int p2align;
		/*
		 * XXX: No page structures for anonymous mappings.
		 * Look up physical addresses by scanning page tables.
		 */
		mpsr->ptep[i] = ihk_mc_pt_lookup_pte(vm->address_space->page_table,
				(void *)mpsr->virt_addr[i], 0, &phys, &pgsize, &p2align);

		/* PTE valid? */
		if (!mpsr->ptep[i] || !pte_is_present(mpsr->ptep[i])) {
			mpsr->status[i] = -ENOENT;
			mpsr->ptep[i] = NULL;
			continue;
		}

		/* PTE is file? */
		if (pte_is_fileoff(mpsr->ptep[i], PAGE_SIZE)) {
			mpsr->status[i] = -EINVAL;
			mpsr->ptep[i] = NULL;
			continue;
		}

		dkprintf("%s: virt 0x%lx:%lu requested to be moved to node %d\n",
			__FUNCTION__, mpsr->virt_addr[i], pgsize, mpsr->nodes[i]);

		/* Large page? */
		if (pgsize > PAGE_SIZE) {
			int nr_sub_pages = (pgsize / PAGE_SIZE);
			int j;

			if (i + nr_sub_pages > count) {
				kprintf("%s: ERROR: page at index %d exceeds the region\n",
						__FUNCTION__, i);
				mpsr->status[i] = -EINVAL;
				break;
			}

			/* Is it contiguous across nr_sub_pages and all
			 * requested to be moved to the same target node? */
			for (j = 0; j < nr_sub_pages; ++j) {
				if (mpsr->virt_addr[i + j] !=
				(mpsr->virt_addr[i] + (j * PAGE_SIZE)) ||
						mpsr->nodes[i] != mpsr->nodes[i + j]) {
					kprintf("%s: ERROR: virt address or node at index %d"
							" is inconsistent\n",
							__FUNCTION__, i + j);
					mpsr->phase_ret = -EINVAL;
					goto pte_out;
				}
			}

			mpsr->nr_pages[i] = nr_sub_pages;
			i += (nr_sub_pages - 1);
		}
		else {
			mpsr->nr_pages[i] = 1;
		}
	}

pte_out:
	/* Barrier */
	ihk_atomic_inc(&mpsr->phase_done);
	while (ihk_atomic_read(&mpsr->phase_done) <
			(phase * nr_cpus)) {
		cpu_pause();
	}

	if (mpsr->phase_ret != 0) {
		goto out;
	}

	dkprintf("%s: phase %d done\n", __FUNCTION__, phase);
	++phase;

	/*
	 * When nodes array is NULL, move_pages doesn't move any pages,
	 * instead will return the node where each page
	 * currently resides by status array.
	 */
	if (!mpsr->user_nodes) {
		/* get nid in parallel */
		for (i = i_s; i < i_e; i++) {
			if (mpsr->status[i] < 0) {
				continue;
			}
			mpsr->status[i] = phys_to_nid(
					pte_get_phys(mpsr->ptep[i]));
		}
		mpsr->phase_ret = 0;
		goto out;  // return node information
	}

	/* Processing of move pages */

	if (cpu_index == 0) {
		/* Allocate new pages on target NUMA nodes */
		for (i = 0; i < count; i++) {
			int pgalign = 0;
			int j;
			void *dst;

			if (!mpsr->ptep[i] || mpsr->status[i] < 0 || !mpsr->nr_pages[i])
				continue;

			/* TODO: store pgalign info in an array as well? */
			if (mpsr->nr_pages[i] > 1) {
				if (mpsr->nr_pages[i] * PAGE_SIZE == PTL2_SIZE)
					pgalign = PTL2_SHIFT - PTL1_SHIFT;
			}

			dst = _ihk_mc_alloc_aligned_pages_node(mpsr->nr_pages[i], pgalign, IHK_MC_AP_USER, mpsr->nodes[i], IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);

			if (!dst) {
				mpsr->status[i] = -ENOMEM;
				continue;
			}

			for (j = i; j < (i + mpsr->nr_pages[i]); ++j) {
				mpsr->status[j] = mpsr->nodes[i];
			}

			mpsr->dst_phys[i] = virt_to_phys(dst);

			dkprintf("%s: virt 0x%lx:%lu to node %d, pgalign: %d,"
					" allocated phys: 0x%lx\n",
					__FUNCTION__, mpsr->virt_addr[i],
					mpsr->nr_pages[i] * PAGE_SIZE,
					mpsr->nodes[i], pgalign, mpsr->dst_phys[i]);
		}
	}

	/* Barrier */
	ihk_atomic_inc(&mpsr->phase_done);
	while (ihk_atomic_read(&mpsr->phase_done) <
			(phase * nr_cpus)) {
		cpu_pause();
	}

	if (mpsr->phase_ret != 0) {
		goto out;
	}

	dkprintf("%s: phase %d done\n", __FUNCTION__, phase);
	++phase;

	/* Copy, PTE update, memfree in parallel */
	for (i = i_s; i < i_e; ++i) {
		if (!mpsr->dst_phys[i])
			continue;

		fast_memcpy(phys_to_virt(mpsr->dst_phys[i]),
				phys_to_virt(pte_get_phys(mpsr->ptep[i])),
				mpsr->nr_pages[i] * PAGE_SIZE);

		_ihk_mc_free_pages(phys_to_virt(pte_get_phys(mpsr->ptep[i])), mpsr->nr_pages[i], IHK_MC_PG_KERNEL, __FILE__, __LINE__);

		pte_update_phys(mpsr->ptep[i], mpsr->dst_phys[i]);

		dkprintf("%s: virt 0x%lx:%lu copied and remapped to phys: 0x%lu\n",
				__FUNCTION__, mpsr->virt_addr[i],
				mpsr->nr_pages[i] * PAGE_SIZE,
				mpsr->dst_phys[i]);
	}

	/* XXX: do a separate SMP call with only CPUs running threads
	 * of this process? */
	if (get_this_cpu_local_var()->current->proc == mpsr->proc) {
		/* Invalidate all TLBs */
		for (i = 0; i < mpsr->count; i++) {
			if (!mpsr->dst_phys[i])
				continue;

			flush_tlb_single((unsigned long)mpsr->virt_addr[i]);
		}
	}

out:
	if (save_pt) {
		ihk_mc_load_page_table(save_pt);
	}

	return mpsr->phase_ret;
}
