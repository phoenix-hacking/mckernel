/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-set-page-orchestration-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_set_page_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long)),"existing set-page public callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__ihk_mc_spinlock_lock),unsigned long(*)(ihk_spinlock_t*)),"actual return-flags lock ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__ihk_mc_spinlock_unlock),void(*)(ihk_spinlock_t*,unsigned long)),"actual unlock flags ABI");
_Static_assert(sizeof(ihk_spinlock_t)==4 && __alignof__(ihk_spinlock_t)==4,"actual ticket-lock layout");
/* PUBLIC PP excludes __set_pt_page and C bridge definitions; fallback retains
 * both original bodies. Real selected Rust T/no self-U; preserve existing Rust
 * caller and actual remaining C allocated callback relocation when compiled.
 */
