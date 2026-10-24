static void x86_pt_set_page_log_bridge(unsigned long virt)
{
	kprintf("EBUSY: page table for 0x%lX is already set\n", virt);
}
