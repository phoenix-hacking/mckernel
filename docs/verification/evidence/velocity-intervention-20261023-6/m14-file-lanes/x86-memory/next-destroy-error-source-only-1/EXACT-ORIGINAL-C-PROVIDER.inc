X86_MEMORY_PUBLIC_BRIDGE void x86_pt_destroy_panic_bridge(int reason)
{
	if (reason == X86_PT_DESTROY_PANIC_LEVEL) {
		panic("destroy_page_table: level is out of range");
	}
	if (reason == X86_PT_DESTROY_PANIC_NULL) {
		panic("destroy_page_table: pt is NULL");
	}
}
