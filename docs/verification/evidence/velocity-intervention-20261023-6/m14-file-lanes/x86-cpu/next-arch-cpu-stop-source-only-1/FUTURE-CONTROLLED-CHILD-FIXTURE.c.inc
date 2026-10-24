/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE FRAGMENT ONLY: no main/argv/queue. Run only inside a future admitted
 * isolated ordinary child. Never link the actual HLT provider into this fixture.
 */
#include <stdint.h>
#include <unistd.h>
static int record_fd;
static uint32_t stop_after, halt_count;
/* Controlled replacement for the existing void(void) provider, never ISA HLT. */
void cpu_halt(void)
{
    uint32_t ordinal = ++halt_count;
    if (write(record_fd, &ordinal, sizeof ordinal) != sizeof ordinal) _exit(120);
    if (ordinal == stop_after) _exit(0);
}
#define arch_cpu_stop original_arch_cpu_stop
#include "ORIGINAL-C-BODY.inc"
#undef arch_cpu_stop
extern void arch_cpu_stop(void);
_Static_assert(__builtin_types_compatible_p(__typeof__(&original_arch_cpu_stop),
                                          __typeof__(&arch_cpu_stop)), "void(void) ABI");
/* Future parent independently checks exact 1..N tape, EOF, exit0 and no return.
 * A normal child exit is the observation seam, no cross-language unwind/longjmp.
 */
static void controlled_stop_child(void (*selected)(void), int fd, uint32_t limit)
{
    if (!limit) _exit(119);
    record_fd = fd; stop_after = limit; halt_count = 0;
    selected();
    _exit(121);
}
