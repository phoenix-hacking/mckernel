static void *x86_split_alloc_new_pt_bridge(int nr_pages, int ap_flag)
{
	if (nr_pages != 1)
		return NULL;
	return __alloc_new_pt((ihk_mc_ap_flag)ap_flag);
}
