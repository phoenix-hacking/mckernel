/* Functional OS/Rust only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/passed-vmap4-current-union2-production-addition-1/candidate/kernel/mem.c"
_Static_assert(__builtin_types_compatible_p(typeof(&ihk_pagealloc_init),void*(*)(unsigned long,unsigned long,unsigned long)),"publicInitABI");
_Static_assert(__builtin_types_compatible_p(typeof(&ihk_pagealloc_alloc),unsigned long(*)(void*,int,int)),"publicAllocABI");
_Static_assert(__builtin_types_compatible_p(typeof(&ihk_pagealloc_free),void(*)(void*,unsigned long,int)),"publicFreeABI");
_Static_assert(sizeof(enum ihk_mc_pt_prepare_flag)==sizeof(int),"prepareEnumWidth");
#ifdef MCKERNEL_RUST_MEM_HELPERS
_Static_assert(__builtin_types_compatible_p(typeof(&mem_vmap_init_bridge),mem_vmap_init_fn_t),"initCallbackABI");
_Static_assert(__builtin_types_compatible_p(typeof(&mem_vmap_alloc_bridge),mem_vmap_alloc_fn_t),"allocCallbackABI");
_Static_assert(__builtin_types_compatible_p(typeof(&mem_vmap_free_bridge),mem_vmap_free_fn_t),"freeCallbackABI");
_Static_assert(__builtin_types_compatible_p(typeof(&mem_pt_prepare_map_bridge),mem_pt_prepare_map_fn_t),"prepareCallbackABI");
#endif
