#define process_create_thread_alloc_pages_bridge reference_process_create_thread_alloc_pages_bridge
#line 785 "/src/kernel/process.c"
void *process_create_thread_alloc_pages_bridge(int npages,
					      unsigned long flags)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, flags, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}

#undef process_create_thread_alloc_pages_bridge
#define process_free_range_pages_bridge reference_process_free_range_pages_bridge
#line 1871 "/src/kernel/process.c"
static void process_free_range_pages_bridge(void *addr, unsigned long pages)
{
	_ihk_mc_free_pages(addr, pages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

#undef process_free_range_pages_bridge
#define process_split_range_alloc_bridge reference_process_split_range_alloc_bridge
#line 1625 "/src/kernel/process.c"
struct vm_range *process_split_range_alloc_bridge(unsigned long size,
		unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}
#undef process_split_range_alloc_bridge
#define process_free_thread_pages_bridge reference_process_free_thread_pages_bridge
#line 3499 "/src/kernel/process.c"
static void free_thread_pages(struct thread *thread)
{
	_ihk_mc_free_pages(thread, KERNEL_STACK_NR_PAGES, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

void process_free_thread_pages_bridge(void *thread)
{
	free_thread_pages(thread);
}

#undef process_free_thread_pages_bridge
int fixture_original_anon_allocate(struct process_vm *vm, struct vm_range *range,
        uintptr_t fault_addr,uint64_t reason,pte_t **po,void **bo,size_t *so,
        int *ao,void **vo,int *eo)
{
    pte_t *ptep=*po;void *pgaddr=*bo;size_t pgsize=*so;int p2align=*ao;
    void *virt=*vo;int error=*eo;
#line 3053 "/src/kernel/process.c"
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

#line 1 "anon-allocation-fixture-fragment"
    *po=ptep;*bo=pgaddr;*so=pgsize;*ao=p2align;*vo=virt;*eo=error;return 0;
out:
    *po=ptep;*bo=pgaddr;*so=pgsize;*ao=p2align;*vo=virt;*eo=error;return 1;
}
