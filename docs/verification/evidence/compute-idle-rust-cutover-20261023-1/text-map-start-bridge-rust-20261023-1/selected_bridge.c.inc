#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
/* Declarative build geometry: CMake resolves this value from the host kernel.
 * Rust owns the getter; this immutable data witness contains no C execution. */
const unsigned long x86_map_kernel_start_geometry = MAP_KERNEL_START;
#else
X86_MEMORY_PUBLIC_BRIDGE unsigned long x86_init_text_map_kernel_start_bridge(void)
{
	return MAP_KERNEL_START;
}
#endif
