static int original_walk_l1(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l1(pt, base, start, end, &original_clear_range_l1, args);
}
