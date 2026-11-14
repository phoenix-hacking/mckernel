/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <sched_helpers.h>
void spin_sleep_or_schedule(void); /* exact process.h:886 declaration */
_Static_assert(sizeof(unsigned long)==8 && sizeof(int)==4,"LP64 callback ABI");
_Static_assert(sizeof(struct sched_runqueue_offsets)==26*8,"existing26offsets");
_Static_assert(__builtin_types_compatible_p(__typeof__(&spin_sleep_or_schedule),void (*)(void)),"public ABI");
