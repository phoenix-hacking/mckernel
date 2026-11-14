/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "../candidate/arch/x86_64/kernel/memory.c"
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_l4_body),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"complete L4 callback Rust ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l3_callback),int(*const)(void*,unsigned long,unsigned long,unsigned long,void*)),"immutable actual L3 callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l4_callback),int(*const)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"walkL4 borrowed callback ABI");
#else
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l4),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"fallback L4 callback ABI");
#endif
