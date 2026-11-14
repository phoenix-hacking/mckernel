/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source fragment only: no main/driver/cohort. This records the full callback
 * signature. It never dereferences frame/IP/SP/FP values or executes stack walks.
 * Future assembly includes original selected C renamed to original_* followed
 * by the two actual extracted Rust bodies, using the existing kprintf ABI.
 */
#include <stdarg.h>
extern int strcmp(const char *, const char *);
extern void x86_stack_frame_log_bridge(unsigned long, unsigned long, unsigned long);
extern void x86_print_stack_bridge(void *, unsigned long);
extern void original_x86_stack_frame_log_bridge(unsigned long, unsigned long, unsigned long);
extern void original_x86_print_stack_bridge(void *, unsigned long);
struct output_tape {
    unsigned long a, b, c;
    void *frame;
    unsigned long first;
    unsigned int log_calls, stack_calls, format_mismatch;
};
static struct output_tape observed;
static int logger_result;
int kprintf(const char *fmt, ...)
{
    va_list ap;
    observed.log_calls++;
    observed.format_mismatch += strcmp(fmt, "IP: %016lx, SP: %016lx, FP: %016lx\n") != 0;
    va_start(ap, fmt);
    observed.a = va_arg(ap, unsigned long);
    observed.b = va_arg(ap, unsigned long);
    observed.c = va_arg(ap, unsigned long);
    va_end(ap);
    return logger_result;
}
/* Controlled observation replaces only the downstream already accepted body.
 * Native __print_stack/current kernel stack memory are NOTEXECUTED here. */
void __print_stack(void *frame, unsigned long first)
{
    observed.stack_calls++;
    observed.frame = frame;
    observed.first = first;
}
/* An outer fixture will compare scalar fields individually, never struct
 * padding; matrix uses 0/1/bit31/bit32/bit63/~0 and logger returns INT_MIN/-1/0/1/
 * INT_MAX, requiring exactly one correct log or stack callback respectively.
 * Full real-header selected TU supplies compatible function-pointer assertions;
 * hosted recorder intentionally owns no invented production context layout. */
static unsigned int same_tape(const struct output_tape *a, const struct output_tape *b)
{
    return a->a == b->a && a->b == b->b && a->c == b->c &&
        a->frame == b->frame && a->first == b->first &&
        a->log_calls == b->log_calls && a->stack_calls == b->stack_calls &&
        a->format_mismatch == b->format_mismatch;
}
