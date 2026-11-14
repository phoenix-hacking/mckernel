static int selected_walk_l3(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l3(pt, base, start, end, &clear_range_l3, args);
}
