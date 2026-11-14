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
