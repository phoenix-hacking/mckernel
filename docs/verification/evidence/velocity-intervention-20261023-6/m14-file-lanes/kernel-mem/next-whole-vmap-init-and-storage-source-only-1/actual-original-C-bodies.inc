void *mem_vmap_allocator_bridge(void)
{
	return vmap_allocator;
}

static void virtual_allocator_init(void)
{
#ifdef MCKERNEL_RUST_MEM_HELPERS
	mem_virtual_allocator_init_body_result((void **)&vmap_allocator,
			MAP_VMAP_START, MAP_VMAP_SIZE, PAGE_SIZE,
			IHK_MC_PT_FIRST_LEVEL, mem_vmap_init_bridge,
			mem_pt_prepare_map_bridge);
#else
	vmap_allocator = ihk_pagealloc_init(MAP_VMAP_START,
	                                    MAP_VMAP_SIZE, PAGE_SIZE);
	/* Make sure that kernel first-level page table copying works */
	ihk_mc_pt_prepare_map(NULL, (void *)MAP_VMAP_START, MAP_VMAP_SIZE,
	                      IHK_MC_PT_FIRST_LEVEL);
#endif
}
