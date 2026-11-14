/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-split-page-callbacks-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_page_map_bridge),x86_split_page_map_fn_t),"actual split map callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_page_unmap_bridge),x86_split_page_unmap_fn_t),"actual split unmap callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_map),void(*)(struct page*)),"existing real page-map endpoint");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_unmap),int(*)(struct page*)),"existing real page-unmap endpoint");
/* PUBLIC bodies excluded; existing split_large_page pointer consumers remain,
 * unique Rust providers/actual allocated relocs/partial proof must follow.
 */
