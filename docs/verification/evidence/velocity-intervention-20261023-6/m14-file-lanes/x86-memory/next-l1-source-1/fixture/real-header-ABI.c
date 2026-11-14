/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "../candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l1),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L1 callback ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_flush),x86_clear_flush_memobj_fn_t const),"reused memobj flush ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_rss_sub),x86_clear_rss_sub_fn_t const),"reused RSS ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_rss_sub),x86_clear_memobj_rss_sub_fn_t const),"reused memobj RSS ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"reused effect log ABI");
#endif
_Static_assert(PTL1_SHIFT==12 && PTL1_SIZE==(1UL<<12),"exact L1 geometry");
_Static_assert(sizeof(pte_t)==sizeof(unsigned long) && sizeof(pte_t)==8,"actual x86 PTE width");
