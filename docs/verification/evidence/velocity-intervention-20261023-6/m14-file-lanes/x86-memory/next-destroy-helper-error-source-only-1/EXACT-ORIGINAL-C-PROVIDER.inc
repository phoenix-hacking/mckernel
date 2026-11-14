X86_MEMORY_PUBLIC_BRIDGE void x86_pt_destroy_helper_failed_panic_bridge(void)
{
	panic("destroy_page_table: helper failed");
}
