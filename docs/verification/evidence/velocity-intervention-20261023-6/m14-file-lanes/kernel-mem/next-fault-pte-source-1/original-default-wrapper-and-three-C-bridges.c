#ifdef MCKERNEL_RUST_MEM_HELPERS
static pte_t *mem_lookup_fault_pte_bridge(page_table_t pt, void *virt,
		int pgshift, void **basep, size_t *sizep, int *p2alignp)
{
	return ihk_mc_pt_lookup_pte(pt, virt, pgshift, basep, sizep, p2alignp);
}

static int mem_page_fault_process_vm_bridge(struct process_vm *vm,
		void *virt, unsigned long reason)
{
	return page_fault_process_vm(vm, virt, reason);
}

static void mem_lookup_fault_log_bridge(void *virt)
{
	kprintf("%s: successfully faulted 0x%lx\n",
			"ihk_mc_pt_lookup_fault_pte", (unsigned long)virt);
}
#endif

pte_t *ihk_mc_pt_lookup_fault_pte(struct process_vm *vm, void *virt,
		int pgshift, void **basep, size_t *sizep, int *p2alignp)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	return mem_pt_lookup_fault_pte_body_result(vm, virt, pgshift, basep,
			sizep, p2alignp,
			__builtin_offsetof(struct process_vm, address_space),
			__builtin_offsetof(struct address_space, page_table),
			mem_lookup_fault_pte_bridge,
			mem_page_fault_process_vm_bridge,
			mem_lookup_fault_log_bridge);
#else
	int faulted = 0;
	pte_t *ptep;

retry:
	ptep = ihk_mc_pt_lookup_pte(vm->address_space->page_table,
			virt, pgshift, basep, sizep, p2alignp);
	if (!faulted && (!ptep || !pte_is_present(ptep))) {
		page_fault_process_vm(vm, virt, PF_POPULATE | PF_USER);
		faulted = 1;
		goto retry;
	}

	if (faulted && ptep && pte_is_present(ptep)) {
		kprintf("%s: successfully faulted 0x%lx\n", __FUNCTION__, virt);
	}

	return ptep;
#endif
}

