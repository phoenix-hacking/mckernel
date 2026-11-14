/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <assert.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "actual-logger-abi-snippet.h"
_Static_assert(sizeof(void *) == 8 && sizeof(unsigned long) == 8 && sizeof(int) == 4,
               "selected x86_64 C callback and varargs ABI");
_Static_assert(X86_CLEAR_TOP_LOG_INVALID == 6 && X86_CLEAR_TOP_LOG_ALLOC_FAILED == 7,
               "actual shared event IDs");
static const char invalid_format[] = "clear_range(%p,%p,%p,%x):invalid start and/or end.\n";
static const char allocation_format[] = "%s: error: allocating address array\n";
struct observation {
    unsigned calls;
    char format[128], output[256], string_arg[32];
    uintptr_t pointers[3];
    unsigned free_bits;
};
static struct observation observed;
static int logging_return;
int kprintf(const char *format, ...)
{
    va_list args, rendered, inspected;
    ++observed.calls;
    assert(observed.calls == 1);
    assert(strlen(format) < sizeof(observed.format));
    strcpy(observed.format, format);
    va_start(args, format);
    va_copy(rendered, args);
    va_copy(inspected, args);
    int count = vsnprintf(observed.output, sizeof(observed.output), format, rendered);
    assert(count >= 0 && (size_t)count < sizeof(observed.output));
    if (strcmp(format, invalid_format) == 0) {
        for (unsigned i = 0; i < 3; ++i)
            observed.pointers[i] = (uintptr_t)va_arg(inspected, void *);
        observed.free_bits = va_arg(inspected, unsigned int);
    } else {
        assert(strcmp(format, allocation_format) == 0);
        const char *value = va_arg(inspected, const char *);
        assert(strcmp(value, "clear_range") == 0);
        strcpy(observed.string_arg, value);
    }
    va_end(inspected);
    va_end(rendered);
    va_end(args);
    return logging_return;
}
#define X86_MEMORY_PUBLIC_BRIDGE static
#define x86_clear_range_top_log_bridge original_top_log
#include "original-top-log.c.inc"
#undef x86_clear_range_top_log_bridge
#undef X86_MEMORY_PUBLIC_BRIDGE
extern void x86_clear_range_top_log_bridge(int, void *, unsigned long, unsigned long, int);
static void independent_expected(int event, uintptr_t pt, unsigned long start,
                                 unsigned long end, int requested_free)
{
    char expected[256] = {0};
    if (event == 6) {
        assert(observed.calls == 1 && strcmp(observed.format, invalid_format) == 0);
        assert(observed.pointers[0] == pt && observed.pointers[1] == start && observed.pointers[2] == end);
        assert(observed.free_bits == (unsigned)requested_free);
        snprintf(expected, sizeof(expected), invalid_format,
                 (void *)pt, (void *)start, (void *)end, (unsigned)requested_free);
    } else if (event == 7) {
        assert(observed.calls == 1 && strcmp(observed.format, allocation_format) == 0);
        assert(strcmp(observed.string_arg, "clear_range") == 0);
        snprintf(expected, sizeof(expected), allocation_format, "clear_range");
    } else {
        assert(observed.calls == 0 && observed.format[0] == 0);
    }
    assert(strcmp(observed.output, expected) == 0);
}
int main(void)
{
    const unsigned long pointers[] = {0UL, 1UL, 0x1000UL, 0x7fffffffffffffffUL,
        0x8000000000000000UL, 0xfffffffffe800000UL, 0xfffffffffffffffeUL, ~0UL};
    const int events[] = {INT_MIN, -7, -1, 0, 5, 6, 7, 8, 9, INT_MAX};
    const int free_values[] = {INT_MIN, -7, -1, 0, 1, 2, INT_MAX};
    const int returns[] = {INT_MIN, -37, 0, 8, INT_MAX};
    unsigned long pairs = 0;
    for (unsigned a = 0; a < sizeof(pointers)/sizeof(pointers[0]); ++a)
    for (unsigned b = 0; b < sizeof(pointers)/sizeof(pointers[0]); ++b)
    for (unsigned c = 0; c < sizeof(pointers)/sizeof(pointers[0]); ++c)
    for (unsigned e = 0; e < sizeof(events)/sizeof(events[0]); ++e)
    for (unsigned f = 0; f < sizeof(free_values)/sizeof(free_values[0]); ++f)
    for (unsigned r = 0; r < sizeof(returns)/sizeof(returns[0]); ++r) {
        logging_return = returns[r];
        memset(&observed, 0, sizeof(observed));
        original_top_log(events[e], (void *)pointers[a], pointers[b], pointers[c], free_values[f]);
        independent_expected(events[e], pointers[a], pointers[b], pointers[c], free_values[f]);
        struct observation original = observed;
        memset(&observed, 0, sizeof(observed));
        x86_clear_range_top_log_bridge(events[e], (void *)pointers[a], pointers[b], pointers[c], free_values[f]);
        independent_expected(events[e], pointers[a], pointers[b], pointers[c], free_values[f]);
        assert(memcmp(&original, &observed, sizeof(original)) == 0);
        ++pairs;
    }
    assert(pairs == 179200UL);
    printf("PASS actual-original-C/full-Rust top-log pairs=%lu raw-varargs+format+vsnprintf+event-oracle\n", pairs);
    return 0;
}
