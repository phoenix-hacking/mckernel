/* Functional OS/Rust only; no security testing. Exact selected/fallback declarations. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
#ifdef MCKERNEL_RUST_PAGE_HELPERS
#define PAGE_UNMAP_PUBLIC_BRIDGE
#else
#define PAGE_UNMAP_PUBLIC_BRIDGE static
#endif
#include "actual-selected-pagehash-region.inc"
_Static_assert(sizeof(ihk_spinlock_t)==4 && _Alignof(ihk_spinlock_t)==4,"locklayout");
_Static_assert(sizeof(struct page)==80 && _Alignof(struct page)==8,"PageLayout");
_Static_assert(__builtin_offsetof(struct page,offset)==64,"PageOffset");
_Static_assert(__builtin_types_compatible_p(typeof(&page_hash_lock_bridge),unsigned long(*)(unsigned long)),"lockABI");
_Static_assert(__builtin_types_compatible_p(typeof(&page_hash_unlock_bridge),void(*)(unsigned long,unsigned long)),"unlockABI");
_Static_assert(__builtin_types_compatible_p(typeof(&page_hash_lock_init_bridge),void(*)(unsigned long)),"initABI");
