#define extend_process_region fixture_original_extend_process_region
#define __func__ "extend_process_region"
#define __FUNCTION__ "extend_process_region"
#line 3364 "held-current-COW-process.c"
unsigned long extend_process_region(struct process_vm *vm,
		unsigned long end_allocated,
		unsigned long address, unsigned long flag)
{
	unsigned long new_end_allocated;
	void *p;
	int rc;
	size_t len;
	int npages;
	struct vm_range *range;

	size_t align_size = vm->proc->heap_extension > PAGE_SIZE ?
		LARGE_PAGE_SIZE : PAGE_SIZE;
	unsigned long align_mask = vm->proc->heap_extension > PAGE_SIZE ?
		LARGE_PAGE_MASK : PAGE_MASK;
	unsigned long align_p2align = vm->proc->heap_extension > PAGE_SIZE ?
		LARGE_PAGE_P2ALIGN : PAGE_P2ALIGN;
	int align_shift = vm->proc->heap_extension > PAGE_SIZE ?
		LARGE_PAGE_SHIFT : PAGE_SHIFT;

	new_end_allocated = (address + (PAGE_SIZE - 1)) & PAGE_MASK;
	if ((new_end_allocated - end_allocated) < vm->proc->heap_extension) {
		new_end_allocated = (end_allocated + vm->proc->heap_extension +
				(align_size - 1)) & align_mask;
	}

	/* Check if the range to be extended already exists */
	range = lookup_process_memory_range(vm,
			end_allocated, new_end_allocated);
	if (range) {
		dkprintf("%s: warning: vm_range for extension already exists\n",
				__func__);
		return end_allocated;
	}

	len = new_end_allocated - end_allocated;
	npages = len >> PAGE_SHIFT;

	if (flag & VR_DEMAND_PAGING) {
		p = 0;
	}
	else {
		p = _ihk_mc_alloc_aligned_pages_node(npages, align_p2align, IHK_MC_AP_NOWAIT |
				(!(vm->proc->mpol_flags & MPOL_NO_HEAP) ?
				 IHK_MC_AP_USER : 0), -1, IHK_MC_PG_USER, end_allocated, __FILE__, __LINE__);

		if (!p) {
			dkprintf("%s: warning: failed to allocate %d contiguous pages "
					" (bytes: %lu, pgshift: %d), enabling demand paging\n",
					 __func__, npages, len, align_p2align);

			/* Give demand paging a chance */
			flag |= VR_DEMAND_PAGING;
		}
	}

	if ((rc = add_process_memory_range(vm, end_allocated, new_end_allocated,
					(p == 0 ? 0 : virt_to_phys(p)), flag, NULL, 0,
					align_shift, NULL, NULL)) != 0) {
		_ihk_mc_free_pages(p, npages, IHK_MC_PG_USER, __FILE__, __LINE__);
		return end_allocated;
	}
	// memory_stat_rss_add() is called in add_process_memory_range()

	dkprintf("%s: new_end_allocated: 0x%lx, align_size: %lu, align_mask: %lx\n",
		__FUNCTION__, new_end_allocated, align_size, align_mask);

	return new_end_allocated;
}

#undef __FUNCTION__
#undef __func__
#undef extend_process_region
