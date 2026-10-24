static struct page_table *__alloc_new_pt(ihk_mc_ap_flag ap_flag)
{
	return x86_pt_alloc_zeroed_result(ap_flag, x86_pt_alloc_pages_bridge);
}
