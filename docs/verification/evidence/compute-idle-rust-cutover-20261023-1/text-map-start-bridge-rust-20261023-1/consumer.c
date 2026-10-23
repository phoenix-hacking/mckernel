/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <arch-memory.h>
_Static_assert(sizeof(unsigned long)==8 && sizeof(void *)==8,"actual header address ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
#define X86_MEMORY_PUBLIC_BRIDGE
#else
#define X86_MEMORY_PUBLIC_BRIDGE static
#endif
#include "selected_bridge.c.inc"
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
extern unsigned long x86_init_text_map_kernel_start_bridge(void);
#endif
unsigned long actual_selection_consumer(void) {
 return x86_init_text_map_kernel_start_bridge();
}
