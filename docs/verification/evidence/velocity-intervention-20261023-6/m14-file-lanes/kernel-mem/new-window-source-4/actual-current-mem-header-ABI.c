/* Functional OS/Rust only; no security testing. */
#include "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/new-window-source-4/source/kernel/mem.c"
_Static_assert(__builtin_types_compatible_p(typeof(&page_hash_alloc_bridge),struct page *(*)(unsigned long,int)),"allocABI");
_Static_assert(__builtin_types_compatible_p(typeof(&page_init),void(*)(void)),"initABI");
_Static_assert(__builtin_types_compatible_p(typeof(&page_hash_count_pages),int(*)(void)),"countABI");
_Static_assert(__builtin_types_compatible_p(ihk_mc_ap_flag,unsigned long),"flagABI");
_Static_assert(sizeof(struct page)==80 && _Alignof(struct page)==8 && __builtin_offsetof(struct page,offset)==64,"PageABI");
