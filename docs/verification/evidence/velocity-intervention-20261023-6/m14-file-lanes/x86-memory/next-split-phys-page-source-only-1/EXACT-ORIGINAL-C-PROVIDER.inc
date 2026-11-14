static void *x86_split_phys_to_page_bridge(unsigned long phys)
{
	return phys_to_page(phys);
}
