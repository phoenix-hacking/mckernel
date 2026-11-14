static int __set_pt_page(struct page_table *pt, void *virt, unsigned long phys,
                         enum ihk_mc_pt_attribute attr)
{
	int in_kernel = x86_pt_kernel_lock_needed_result((unsigned long)virt);
	unsigned long init_pt_lock_flags;
	int ret;

	init_pt_lock_flags = 0;	/* for avoidance of warning */
	if (in_kernel) {
		init_pt_lock_flags = ihk_mc_spinlock_lock(&init_pt_lock);
	}

	ret = x86_pt_set_page_body_result(pt, init_pt, (unsigned long)virt,
			phys, attr, ATTR_MASK, x86_pt_alloc_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_pt_set_page_log_bridge);

	if (in_kernel) {
		ihk_mc_spinlock_unlock(&init_pt_lock, init_pt_lock_flags);
	}
	return ret;
}

static struct page_table *__alloc_new_pt(ihk_mc_ap_flag ap_flag)
{
	return x86_pt_alloc_zeroed_result(ap_flag, x86_pt_alloc_pages_bridge);
}

static void *x86_split_alloc_new_pt_bridge(int nr_pages, int ap_flag)
{
	if (nr_pages != 1)
		return NULL;
	return __alloc_new_pt((ihk_mc_ap_flag)ap_flag);
}

static void x86_split_page_map_bridge(void *page)
{
	page_map(page);
}
static int x86_split_page_unmap_bridge(void *page)
{
	return page_unmap(page);
}
