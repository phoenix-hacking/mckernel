static int selected_walk_l2(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l2(pt, base, start, end, &clear_range_l2, args);
}
