/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "../candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l2),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L2 callback ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l2_child_walk),x86_clear_child_walk_fn_t const),"exact retained L1 child walker ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_flush),x86_clear_flush_memobj_fn_t const),"reused memobj flush callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_rss_sub),x86_clear_rss_sub_fn_t const),"reused RSS callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_rss_sub),x86_clear_memobj_rss_sub_fn_t const),"reused memobj RSS callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_range_log),x86_clear_range_log_fn_t const),"reused range log callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"reused effect log callback ABI");
#endif
_Static_assert(PTL2_SHIFT==21 && PTL2_SIZE==(1UL<<21) && PFL2_SIZE==((pte_t)0x80),"exact x86 L2 geometry");
_Static_assert(sizeof(pte_t)==sizeof(unsigned long) && sizeof(pte_t)==8,"actual x86 PTE width");
