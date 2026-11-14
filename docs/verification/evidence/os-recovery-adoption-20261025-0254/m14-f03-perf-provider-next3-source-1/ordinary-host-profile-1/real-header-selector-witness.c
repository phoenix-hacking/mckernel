/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "real-provider-abi.C.inc"
#include "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f03-perf-provider-next3-source-1/paired-selectors.C.inc"
int (*f03_selected_extra)(void *) = perf_counter_extra_set_bridge;
int (*f03_selected_init)(int,unsigned long,int) = perf_counter_init_raw_bridge;
long (*f03_selected_atomic)(void *) = perf_event_atomic64_read_bridge;
_Static_assert(__builtin_types_compatible_p(__typeof__(&perf_counter_extra_set_bridge),int (*)(void *)),"extra callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&perf_counter_init_raw_bridge),int (*)(int,unsigned long,int)),"original full-width public init callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&perf_event_atomic64_read_bridge),long (*)(void *)),"atomic callback signed-long ABI");
