/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "../candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l4_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"complete walker export ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l4_callback),int(*const)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"immutable actual C callback ABI");
#endif
