#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
extern void x86_clear_range_top_log_bridge(int event, void *pt,
		unsigned long start, unsigned long end, int free_physical);
#else
X86_MEMORY_PUBLIC_BRIDGE void x86_clear_range_top_log_bridge(int event, void *pt,
		unsigned long start, unsigned long end, int free_physical)
{
	switch (event) {
	case X86_CLEAR_TOP_LOG_INVALID:
		ekprintf("clear_range(%p,%p,%p,%x):"
				"invalid start and/or end.\n",
				pt, (void *)start, (void *)end, free_physical);
		break;
	case X86_CLEAR_TOP_LOG_ALLOC_FAILED:
		ekprintf("%s: error: allocating address array\n", "clear_range");
		break;
	default:
		break;
	}
}
#endif
