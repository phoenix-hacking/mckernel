/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-split-rss-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_rss_add_bridge),x86_split_rss_fn_t),"split RSS add actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_rss_sub_bridge),x86_split_rss_fn_t),"split RSS sub actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&memory_stat_rss_add),void(*)(unsigned long,int)),"existing RSS add endpoint narrowing");
_Static_assert(__builtin_types_compatible_p(__typeof__(&memory_stat_rss_sub),void(*)(unsigned long,int)),"existing RSS sub endpoint narrowing");
_Static_assert(sizeof(size_t)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"actual conversion geometry");
/* PUBLIC old bodies excluded; same C split_large_page callback positions remain.
 * Future proof: exact Rust providers, actual C allocated pointer relocations,
 * coherent wholeTU and partial. No U or relocation invented from source alone.
 */
