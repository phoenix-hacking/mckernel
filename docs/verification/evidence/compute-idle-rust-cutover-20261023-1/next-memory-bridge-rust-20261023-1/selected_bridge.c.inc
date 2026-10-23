#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
X86_MEMORY_PUBLIC_BRIDGE unsigned long x86_init_text_end_bridge(void)
{
	return (unsigned long)_end;
}
#endif
