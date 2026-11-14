static int mem_pt_prepare_map_bridge(page_table_t pt, void *virt,
		unsigned long size, enum ihk_mc_pt_prepare_flag flag)
{
	return ihk_mc_pt_prepare_map(pt, virt, size, flag);
}
