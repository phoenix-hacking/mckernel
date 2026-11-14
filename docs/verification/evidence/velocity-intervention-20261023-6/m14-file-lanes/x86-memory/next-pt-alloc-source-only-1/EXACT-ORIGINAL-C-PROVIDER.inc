X86_MEMORY_PUBLIC_BRIDGE void *x86_pt_alloc_pages_bridge(int nr_pages, int ap_flag)
{
	return _ihk_mc_alloc_aligned_pages_node(nr_pages, PAGE_P2ALIGN, (ihk_mc_ap_flag)ap_flag, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}
