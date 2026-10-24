/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */

#include "gpe-real-header-ABI.c.inc"

#include "int3-real-header-ABI.c.inc"

#include "debug-real-header-ABI.c.inc"

extern void arch_cpu_stop(void);
typedef void(*StopEntry)(void);
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_cpu_stop),StopEntry),"actual existing panic caller void(void) ABI");
