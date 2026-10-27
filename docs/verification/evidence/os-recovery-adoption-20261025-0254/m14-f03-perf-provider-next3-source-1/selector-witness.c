/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Typed scalar/pointer ABI witness; no actual PMU or atomic read executes. */
struct mc_perf_event;
typedef struct { long counter64; } ihk_atomic64_t;
int ihk_mc_perfctr_set_extra(struct mc_perf_event *);
int ihk_mc_perfctr_init_raw(int, unsigned int, int);
long ihk_atomic64_read(const ihk_atomic64_t *);
#include "paired-selectors.C.inc"
int (*f03_selected_extra)(void *) = perf_counter_extra_set_bridge;
int (*f03_selected_init)(int,unsigned long,int) = perf_counter_init_raw_bridge;
long (*f03_selected_atomic)(void *) = perf_event_atomic64_read_bridge;
_Static_assert(__builtin_types_compatible_p(__typeof__(&perf_counter_extra_set_bridge),int (*)(void *)),"extra callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&perf_counter_init_raw_bridge),int (*)(int,unsigned long,int)),"original full-width public init callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&perf_event_atomic64_read_bridge),long (*)(void *)),"atomic callback signed-long ABI");
