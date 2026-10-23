/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact original C function versus the extracted actual Rust export. */
#include <arch-memory.h>
extern int printf(const char *, ...);
extern void abort(void);
#ifndef MAP_KERNEL_START
#error This geometry must be supplied as the actual build macro, never guessed.
#endif
_Static_assert(sizeof(unsigned long)==8 && sizeof(void *)==8,"x86_64 address/unsigned-long ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(MAP_KERNEL_START),unsigned long),"build geometry must retain UL type");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
#define X86_MEMORY_PUBLIC_BRIDGE
#else
#define X86_MEMORY_PUBLIC_BRIDGE static
#endif
#include "selected_bridge.c.inc"
#define x86_init_text_map_kernel_start_bridge original_reference
#include "original_bridge.c.inc"
#undef x86_init_text_map_kernel_start_bridge
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
extern unsigned long x86_init_text_map_kernel_start_bridge(void);
#endif
int main(void) {
 unsigned long original=original_reference();
 unsigned long actual=x86_init_text_map_kernel_start_bridge();
 if(actual!=original || actual!=(unsigned long)MAP_KERNEL_START ||
    (unsigned long)(void *)actual!=actual)abort();
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
 if(actual!=x86_map_kernel_start_geometry)abort();
#endif
 printf("PASS original-C/selected-provider geometry=%016lx sizeof_ulong=%lu sizeof_pointer=%lu\n",actual,(unsigned long)sizeof(unsigned long),(unsigned long)sizeof(void *));
 return 0;
}
