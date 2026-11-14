/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <sched_helpers.h>
/* Exact kernel/include/process.h declaration, hash bound in SOURCE-BINDINGS.json. */
void set_timer(int runq_locked);
_Static_assert(sizeof(unsigned long)==8,"ulong64");
_Static_assert(sizeof(int)==4,"int32");
_Static_assert(sizeof(struct timer_runtime_offsets)==120,"existing15offsets");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_timer),void (*)(int)),"set_timer ABI");
