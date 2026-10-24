static void x86_clear_range_log_bridge(int event, void *args,
		unsigned long *ptep, unsigned long base, unsigned long start,
		unsigned long end, int error, int level_shift, unsigned long phys)
{
	const char *fn;

	switch (level_shift) {
	case PTL2_SHIFT:
		fn = "clear_range_l2";
		break;
	case PTL3_SHIFT:
		fn = "clear_range_l3";
		break;
	default:
		fn = "clear_range_l4";
		break;
	}

	switch (event) {
	case X86_CLEAR_RANGE_LOG_SPLIT:
		ekprintf("%s(%p,%p,%lx,%lx,%lx):"
				"split page. %d\n",
				fn, args, ptep, base, start, end, error);
		break;
	case X86_CLEAR_RANGE_LOG_LARGE_PHYS:
		dkprintf("%s: phys=%ld, pte_get_phys(&old),PTL3_SIZE\n",
				fn, phys);
		break;
	default:
		break;
	}
}
