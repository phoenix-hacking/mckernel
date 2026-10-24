X86_MEMORY_PUBLIC_BRIDGE void x86_pt_free_pages_bridge(void *pt, int nr_pages)
{
	_ihk_mc_free_pages(pt, nr_pages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}
