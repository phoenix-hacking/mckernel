static void original_memobj_flush(void *memobj, unsigned long phys,
		size_t pgsize)
{
	memobj_flush_page(memobj, phys, pgsize);
}

static void original_rss(size_t size, size_t pgsize)
{
	memory_stat_rss_sub(size, pgsize);
}

static void original_memobj_rss(void *memobj, size_t size,
		size_t pgsize)
{
	rusage_memory_stat_sub(memobj, size, pgsize);
}

static int original_clear_range_l1(void *args0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct clear_range_args *args = args0;

	//dkprintf("%s: %lx,%lx,%lx\n", __FUNCTION__, base, start, end);

	return x86_clear_range_leaf_body_result(args0, ptep, base, start, end,
			args->vm, args->addr, &args->nr_addr,
			args->max_nr_addr, ihk_mc_get_processor_id(),
			args->free_physical, args->memobj,
			x86_clear_old_action_bridge,
			(x86_clear_remote_flush_fn_t)remote_flush_tlb_array_cpumask,
			original_memobj_flush,
			x86_clear_phys_to_virt_bridge,
			x86_clear_free_pages_user_bridge,
			x86_clear_page_unmap_bridge, original_rss,
			original_memobj_rss,
			x86_clear_effect_log_bridge);
}

static int original_clear_range_l2(void *args0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct clear_range_args *args = args0;

	//dkprintf("%s: %lx,%lx,%lx\n", __FUNCTION__, base, start, end);

	return x86_clear_range_level_body_result(args0, ptep, base, start,
			end, PTL2_SHIFT, PTL2_SIZE, PFL2_SIZE, 1,
			args->vm, args->addr, &args->nr_addr,
			args->max_nr_addr, ihk_mc_get_processor_id(),
			args->free_physical, args->memobj,
			x86_clear_old_action_bridge,
			x86_clear_phys_to_virt_bridge,
			x86_clear_range_walk_l1_bridge,
			(x86_clear_remote_flush_fn_t)remote_flush_tlb_array_cpumask,
			x86_pt_free_pages_bridge,
			original_memobj_flush,
			x86_clear_free_pages_user_bridge,
			x86_clear_page_unmap_bridge, original_rss,
			original_memobj_rss,
			x86_clear_range_log_bridge,
			x86_clear_effect_log_bridge);
}

static int original_clear_range_l3(void *args0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct clear_range_args *args = args0;

	//dkprintf("%s: %lx,%lx,%lx\n", __FUNCTION__, base, start, end);

	return x86_clear_range_level_body_result(args0, ptep, base, start,
			end, PTL3_SHIFT, PTL3_SIZE, PFL3_SIZE, use_1gb_page,
			args->vm, args->addr, &args->nr_addr,
			args->max_nr_addr, ihk_mc_get_processor_id(),
			args->free_physical, args->memobj,
			x86_clear_old_action_bridge,
			x86_clear_phys_to_virt_bridge,
			x86_clear_range_walk_l2_bridge,
			(x86_clear_remote_flush_fn_t)remote_flush_tlb_array_cpumask,
			x86_pt_free_pages_bridge,
			original_memobj_flush,
			x86_clear_free_pages_user_bridge,
			x86_clear_page_unmap_bridge, original_rss,
			original_memobj_rss,
			x86_clear_range_log_bridge,
			x86_clear_effect_log_bridge);
}

static int original_walk_l1(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l1(pt, base, start, end, &original_clear_range_l1, args);
}

static int original_walk_l2(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l2(pt, base, start, end, &original_clear_range_l2, args);
}

static int original_walk_l3(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l3(pt, base, start, end, &original_clear_range_l3, args);
}
