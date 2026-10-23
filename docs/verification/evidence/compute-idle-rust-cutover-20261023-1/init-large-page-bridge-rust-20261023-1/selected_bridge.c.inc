#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
X86_MEMORY_PUBLIC_BRIDGE int x86_init_normal_set_large_bridge(void *pt, unsigned long virt,
		unsigned long phys, unsigned long attr)
{
	return set_pt_large_page(pt, (void *)virt, phys,
			(enum ihk_mc_pt_attribute)attr);
}
#endif
