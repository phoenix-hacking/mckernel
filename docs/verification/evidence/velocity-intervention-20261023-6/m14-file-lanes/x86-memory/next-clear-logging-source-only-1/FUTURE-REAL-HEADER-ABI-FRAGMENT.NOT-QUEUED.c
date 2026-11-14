/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source fragment only. Existing complete selected GCC9 header/config flags.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/next-clear-logging-source-only-1/candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_effect_log_bridge),x86_clear_effect_log_fn_t),"actual complete effect logger ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_log_bridge),x86_clear_range_log_fn_t),"actual complete range logger ABI");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8,"actual descriptor ABI");
_Static_assert(__builtin_offsetof(struct ddebug,file)==0 && __builtin_offsetof(struct ddebug,func)==8 && __builtin_offsetof(struct ddebug,fmt)==16,"actual debug pointer fields");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"retained immutable effect identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_range_log),x86_clear_range_log_fn_t const),"retained immutable range identity");
#endif
