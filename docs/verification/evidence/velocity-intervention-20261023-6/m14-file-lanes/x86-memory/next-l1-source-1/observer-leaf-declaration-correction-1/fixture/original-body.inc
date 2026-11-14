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
			x86_clear_memobj_flush_bridge,
			x86_clear_phys_to_virt_bridge,
			x86_clear_free_pages_user_bridge,
			x86_clear_page_unmap_bridge, x86_clear_rss_sub_bridge,
			x86_clear_memobj_rss_sub_bridge,
			x86_clear_effect_log_bridge);
}
