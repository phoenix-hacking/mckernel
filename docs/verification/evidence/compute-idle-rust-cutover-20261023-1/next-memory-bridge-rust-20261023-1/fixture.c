/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <arch-memory.h>
extern int printf(const char *, ...);
extern void abort(void);
/* Use the real ELF linker end boundary. No new C data/provider is invented. */
extern char _end[];
_Static_assert(sizeof(unsigned long)==8 && sizeof(void *)==8,"actual x86_64 address ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
#define X86_MEMORY_PUBLIC_BRIDGE
#else
#define X86_MEMORY_PUBLIC_BRIDGE static
#endif
#include "selected_bridge.c.inc"
#define x86_init_text_end_bridge original_reference
#include "original_bridge.c.inc"
#undef x86_init_text_end_bridge
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
extern unsigned long x86_init_text_end_bridge(void);
#endif
int main(void) {
 unsigned long original=original_reference();
 unsigned long actual=x86_init_text_end_bridge();
 if(actual!=original || actual!=(unsigned long)_end || (void*)actual!=(void*)_end || actual==0)abort();
 printf("PASS original-C/selected-provider real_ELF_end=%016lx ulong=%lu pointer=%lu address_only=1\n",actual,(unsigned long)sizeof(unsigned long),(unsigned long)sizeof(void*));
 return 0;
}
