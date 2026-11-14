int original_walk_l4(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l4(pt, base, start, end, &original_clear_range_l4, args);
}
