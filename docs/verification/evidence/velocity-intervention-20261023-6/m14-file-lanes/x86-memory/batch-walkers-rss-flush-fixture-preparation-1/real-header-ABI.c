/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-memobj-flush-source-only-1/candidate/arch/x86_64/kernel/memory.c"
#include <rusage_private.h>
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l1_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"complete walker ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l2_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"complete walker ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l3_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"complete walker ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_rss_sub_bridge),void(*)(size_t,size_t)),"RSS callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_memobj_rss_sub_bridge),void(*)(void*,size_t,size_t)),"memobj RSS callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_memobj_flush_bridge),void(*)(void*,unsigned long,size_t)),"memobj flush callback ABI");
_Static_assert(sizeof(size_t)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"accounting argument conversion ABI");
_Static_assert(sizeof(struct memobj)==56 && __builtin_offsetof(struct memobj,flags)==8 && __builtin_offsetof(struct memobj_ops,flush_page)==24,"actual object dispatch ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l2_child_walk),x86_clear_child_walk_fn_t const),"L1 child identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_child_walk),x86_clear_child_walk_fn_t const),"L2 child identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l3_callback),x86_clear_child_walk_fn_t const),"L3 child identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_rss_sub),x86_clear_rss_sub_fn_t const),"RSS immutable identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_rss_sub),x86_clear_memobj_rss_sub_fn_t const),"memobj RSS immutable identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_flush),x86_clear_flush_memobj_fn_t const),"flush immutable identity");
#endif
