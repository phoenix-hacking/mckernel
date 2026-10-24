/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-split-phys-page-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_phys_to_page_bridge),x86_split_phys_to_page_fn_t),"actual split physical-page callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_page),struct page*(*)(uintptr_t)),"actual existing page lookup endpoint ABI");
_Static_assert(sizeof(uintptr_t)==sizeof(unsigned long),"unchanged physical address geometry");
/* PUBLIC C body absent, original C callback position unchanged. Future actual
 * Rust unique T and selected C allocated relocation required, not assumed.
 */
