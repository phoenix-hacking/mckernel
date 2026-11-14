static int original_clear_range_l4(void *args0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	//dkprintf("%s: %lx,%lx,%lx\n", __FUNCTION__, base, start, end);

	return x86_clear_range_root_body_result(args0, ptep, base, start, end,
			x86_clear_phys_to_virt_bridge,
			x86_clear_range_walk_l3_bridge);
}
