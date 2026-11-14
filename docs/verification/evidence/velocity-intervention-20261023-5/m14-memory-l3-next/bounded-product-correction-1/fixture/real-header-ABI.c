/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "../candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l3),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L3 callback ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_child_walk),x86_clear_child_walk_fn_t const),"x86_clear_l3_child_walk ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_flush),x86_clear_flush_memobj_fn_t const),"x86_clear_l3_memobj_flush ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_rss_sub),x86_clear_rss_sub_fn_t const),"x86_clear_l3_rss_sub ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_rss_sub),x86_clear_memobj_rss_sub_fn_t const),"x86_clear_l3_memobj_rss_sub ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_range_log),x86_clear_range_log_fn_t const),"x86_clear_l3_range_log ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"x86_clear_l3_effect_log ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_use_1gb_page),const int *const),"live use1GB borrowed address ABI");
#endif

_Static_assert(PFL3_SIZE == ((pte_t)0x80),"exact C PFL3_SIZE1GB bit matches Rust");
_Static_assert(sizeof(pte_t)==sizeof(unsigned long) && sizeof(pte_t)==8,"PFL3_SIZE actual x86 ABI width");
