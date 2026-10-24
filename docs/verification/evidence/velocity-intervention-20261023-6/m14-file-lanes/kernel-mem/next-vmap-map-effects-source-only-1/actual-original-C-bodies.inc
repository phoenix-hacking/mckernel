int original_mem_pt_set_page_bridge(page_table_t pt, void *virt,
		unsigned long phys, enum ihk_mc_pt_attribute attr)
{
	return ihk_mc_pt_set_page(pt, virt, phys, attr);
}

int original_mem_pt_clear_page_bridge(page_table_t pt, void *virt)
{
	return ihk_mc_pt_clear_page(pt, virt);
}

void original_mem_flush_tlb_single_bridge(unsigned long addr)
{
	flush_tlb_single(addr);
}

void original_mem_barrier_bridge(void)
{
	barrier();
}
