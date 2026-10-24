/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-split-alloc-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_alloc_new_pt_bridge),x86_pt_alloc_pages_fn_t),"split allocator actual callback ABI");
_Static_assert(sizeof(ihk_mc_ap_flag)==8 && sizeof(int)==4,"actual flag narrowing closure");
/* Original int->ihk_mc_ap_flag(unsigned long)->x86_pt_alloc_zeroed_result(int)
 * preserves the original int bits; new Rust passes that same int unchanged.
 * Real PUBLIC C whole TU must retain split_large_page's allocated callback
 * relocation and exclude only this original callback body, with Rust unique T.
 */
