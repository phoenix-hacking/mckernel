static void x86_clear_effect_log_bridge(int event, unsigned long base,
		unsigned long phys, size_t pgsize)
{
	switch (event) {
	case X86_CLEAR_EFFECT_FREE_ANON:
		dkprintf("%lx-,%s: freed anonymous page,base=%lx,size=%ld,pgsize=%ld\n",
				phys, __FUNCTION__, base, pgsize, pgsize);
		break;
	case X86_CLEAR_EFFECT_XPMEM_KEEP:
		dkprintf("%s: XPMEM attach,phys=%lx\n", __FUNCTION__, phys);
		break;
	case X86_CLEAR_EFFECT_FREE_UNMAPPED:
		dkprintf("%lx-,%s: freed unmapped memobj page,base=%lx,size=%ld,pgsize=%ld\n",
				phys, __FUNCTION__, base, pgsize, pgsize);
		break;
	case X86_CLEAR_EFFECT_CHILD_FREE:
		dkprintf("%s: freed child page table at base=%lx,size=%ld\n",
				__FUNCTION__, base, pgsize);
		break;
	default:
		break;
	}
}
