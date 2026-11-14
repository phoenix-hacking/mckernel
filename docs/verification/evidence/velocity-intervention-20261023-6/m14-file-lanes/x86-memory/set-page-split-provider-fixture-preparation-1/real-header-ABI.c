/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/set-page-split-provider-fixture-preparation-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_set_page_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long)),"existing set-page public callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__ihk_mc_spinlock_lock),unsigned long(*)(ihk_spinlock_t*)),"actual return-flags lock ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__ihk_mc_spinlock_unlock),void(*)(ihk_spinlock_t*,unsigned long)),"actual unlock flags ABI");
_Static_assert(sizeof(ihk_spinlock_t)==4 && __alignof__(ihk_spinlock_t)==4,"actual ticket-lock layout");
/* PUBLIC PP excludes __set_pt_page and C bridge definitions; fallback retains
 * both original bodies. Real selected Rust T/no self-U; preserve existing Rust
 * caller and actual remaining C allocated callback relocation when compiled.
 */

_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_alloc_new_pt_bridge),x86_pt_alloc_pages_fn_t),"split allocator actual callback ABI");
_Static_assert(sizeof(ihk_mc_ap_flag)==8 && sizeof(int)==4,"actual flag narrowing closure");
/* Original int->ihk_mc_ap_flag(unsigned long)->x86_pt_alloc_zeroed_result(int)
 * preserves the original int bits; new Rust passes that same int unchanged.
 * Real PUBLIC C whole TU must retain split_large_page's allocated callback
 * relocation and exclude only this original callback body, with Rust unique T.
 */

_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_page_map_bridge),x86_split_page_map_fn_t),"actual split map callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_page_unmap_bridge),x86_split_page_unmap_fn_t),"actual split unmap callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_map),void(*)(struct page*)),"existing real page-map endpoint");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_unmap),int(*)(struct page*)),"existing real page-unmap endpoint");
/* PUBLIC bodies excluded; existing split_large_page pointer consumers remain,
 * unique Rust providers/actual allocated relocs/partial proof must follow.
 */

_Static_assert(sizeof(struct page)==80 && __alignof__(struct page)==8,"actual page ABI");
_Static_assert(__builtin_offsetof(struct page,count)==48 && __builtin_offsetof(struct page,hash)==16,"actual page field closure");
