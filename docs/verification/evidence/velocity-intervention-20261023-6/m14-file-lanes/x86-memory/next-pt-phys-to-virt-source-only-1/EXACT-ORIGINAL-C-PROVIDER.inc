X86_MEMORY_PUBLIC_BRIDGE void *x86_pt_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}
