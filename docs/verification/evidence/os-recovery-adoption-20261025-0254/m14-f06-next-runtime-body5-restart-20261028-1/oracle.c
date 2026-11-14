/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Mock output only; original C body and real ekprintf macro remain unchanged. */
#include <types.h>
#include <ihk/debug.h>
#include <stdarg.h>
extern int vsnprintf(char *, size_t, const char *, va_list);
struct fixture_record {
    char format[128];
    char rendered[128];
    int has_argument;
    int argument;
    int printer_return;
    int rendered_length;
};
struct fixture_trace { unsigned long calls; struct fixture_record records[8]; };
static struct fixture_trace trace;
static int configured_return;

void fixture_reset(int printer_return)
{
    unsigned char *p = (unsigned char *)&trace;
    for (size_t i = 0; i < sizeof(trace); i++) p[i] = 0;
    configured_return = printer_return;
}

int fixture_kprintf(const char *format, ...)
{
    unsigned long index = trace.calls++;
    if (index >= 8) return configured_return;
    struct fixture_record *record = &trace.records[index];
    size_t length = 0;
    while (format[length] && length < 127) {
        record->format[length] = format[length];
        if (format[length] == '%' && format[length + 1] == 'd') record->has_argument = 1;
        length++;
    }
    record->format[length] = 0;
    va_list arguments, render_arguments;
    va_start(arguments, format);
    va_copy(render_arguments, arguments);
    if (record->has_argument) record->argument = va_arg(arguments, int);
    record->rendered_length = vsnprintf(record->rendered, sizeof(record->rendered), format, render_arguments);
    va_end(render_arguments);
    va_end(arguments);
    record->printer_return = configured_return;
    return configured_return;
}

/* The Rust production module resolves this HOST mock symbol, never kernel I/O. */
int kprintf(const char *format, ...)
{
    /* This wrapper preserves arguments to the same capture without reformatting.
     * The test's production formats have either zero or one int32 argument. */
    int has_argument = 0;
    for (size_t i = 0; format[i]; i++)
        if (format[i] == '%' && format[i + 1] == 'd') has_argument = 1;
    if (has_argument) {
        va_list arguments;
        va_start(arguments, format);
        int error = va_arg(arguments, int);
        va_end(arguments);
        return fixture_kprintf(format, error);
    }
    return fixture_kprintf(format);
}

void fixture_read_trace(struct fixture_trace *out) { *out = trace; }
#include "original-event-defines.c.inc"
#define arch_vdso_setup_log_bridge original_arch_vdso_setup_log_bridge
#define kprintf fixture_kprintf
#include "original-vdso-setup-log.c.inc"
#undef kprintf
#undef arch_vdso_setup_log_bridge
