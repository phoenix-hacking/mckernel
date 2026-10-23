/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <arch-memory.h>
extern int set_pt_large_page(struct page_table *,void *,unsigned long,enum ihk_mc_pt_attribute);
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
#define X86_MEMORY_PUBLIC_BRIDGE
#else
#define X86_MEMORY_PUBLIC_BRIDGE static
#endif
#include "selected_bridge.c.inc"
#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
int fallback_consumer(void *pt,unsigned long virt,unsigned long phys,unsigned long attr) {
 return x86_init_normal_set_large_bridge(pt,virt,phys,attr);
}
#else
extern int x86_init_normal_set_large_bridge(void *,unsigned long,unsigned long,unsigned long);
int public_consumer(void *pt,unsigned long virt,unsigned long phys,unsigned long attr) {
 return x86_init_normal_set_large_bridge(pt,virt,phys,attr);
}
#endif
