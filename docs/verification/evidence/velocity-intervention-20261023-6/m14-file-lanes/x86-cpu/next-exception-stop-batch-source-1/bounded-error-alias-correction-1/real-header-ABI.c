/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */

#include "gpe-real-header-ABI.c.inc"

#include "int3-real-header-ABI.c.inc"

#include "debug-real-header-ABI.c.inc"

extern void arch_cpu_stop(void);
typedef void(*StopEntry)(void);
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_cpu_stop),StopEntry),"actual existing panic caller void(void) ABI");

/* Existing real C anonymous-union alias; Rust uses its existing orig_rax name. */
_Static_assert(__builtin_offsetof(struct x86_basic_regs,error)==__builtin_offsetof(struct x86_basic_regs,orig_rax),"real interrupt error/syscall orig_rax alias offset");
_Static_assert(sizeof(((struct x86_basic_regs*)0)->error)==sizeof(((struct x86_basic_regs*)0)->orig_rax)&&sizeof(((struct x86_basic_regs*)0)->error)==8,"unchanged actual unsigned-long alias width");
