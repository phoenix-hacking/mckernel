/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <assert.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
/* Keep the actual project debug macro/record, adapting only its include dependency. */
#define __LWK_COMPILER_H
#define __aligned(x) __attribute__((aligned(x)))
#include <ihk/debug.h>
struct ddebug __attribute__((aligned(8),section("__verbose"))) f03_swapout_callback_debug_v1;
extern struct ddebug __start___verbose[], __stop___verbose[];
extern void syscall_swapout_log_bridge(const void *, void *, size_t, int);
extern void syscall_linux_mlock_log_bridge(unsigned long, unsigned long);
extern long fixture_rust_wrapper(int, unsigned long, unsigned long, unsigned long, int, int);
struct observation {
    char format[80], bytes[256], events[8];
    unsigned long slots[5], body[4];
    int used, prints, cpus, bodies, kind;
};
static struct observation observed;
static void event(char c) { assert(observed.used < 7); observed.events[observed.used++] = c; }
static void reset(void) { memset(&observed, 0, sizeof(observed)); }
int ihk_mc_get_processor_id(void) { event('C'); observed.cpus++; return 19; }
int kprintf(const char *format, ...) {
    va_list ap, render;
    event('P'); observed.prints++;
    assert(observed.prints == 1 && strlen(format) < sizeof(observed.format));
    strcpy(observed.format, format);
    va_start(ap, format); va_copy(render, ap);
    int n = vsnprintf(observed.bytes, sizeof(observed.bytes), format, render);
    va_end(render);
    assert(n >= 0 && (size_t)n < sizeof(observed.bytes));
    if (strcmp(format, "[%d]swapout(%lx,%lx,%lx,%ld)\n") == 0) {
        observed.slots[0] = (unsigned long)va_arg(ap, int);
        observed.slots[1] = va_arg(ap, unsigned long);
        observed.slots[2] = va_arg(ap, unsigned long);
        observed.slots[3] = va_arg(ap, unsigned long);
        observed.slots[4] = (unsigned long)va_arg(ap, long);
    } else {
        assert(strcmp(format, "linux_mlock: %p %ld\n") == 0);
        observed.slots[0] = (unsigned long)va_arg(ap, void *);
        observed.slots[1] = (unsigned long)va_arg(ap, long);
    }
    va_end(ap); return n;
}
long fixture_body_record(int kind, unsigned long a, unsigned long b, unsigned long c, long d) {
    event('B'); observed.bodies++; observed.kind = kind;
    observed.body[0] = a; observed.body[1] = b; observed.body[2] = c; observed.body[3] = (unsigned long)d;
    return -73;
}
void
original_swapout(const void *fname, void *buf, size_t size, int flag)
{
	dkprintf("[%d]swapout(%lx,%lx,%lx,%ld)\n",
			ihk_mc_get_processor_id(), (unsigned long)fname,
			(unsigned long)buf, (unsigned long)size, (long)flag);
}

void
original_mlock(unsigned long addr, unsigned long len)
{
	kprintf("linux_mlock: %p %ld\n", (void *)addr, len);
}

static int equal(const struct observation *a, const struct observation *b) {
    return strcmp(a->format,b->format)==0 && strcmp(a->bytes,b->bytes)==0 &&
        strcmp(a->events,b->events)==0 && memcmp(a->slots,b->slots,sizeof(a->slots))==0 &&
        memcmp(a->body,b->body,sizeof(a->body))==0 && a->used==b->used &&
        a->prints==b->prints && a->cpus==b->cpus && a->bodies==b->bodies && a->kind==b->kind;
}
static void flags(unsigned int value) {
    for (struct ddebug *p = __start___verbose; p < __stop___verbose; p++) p->flags = value;
}
int main(void) {
    const unsigned long values[] = {0, 1, LONG_MAX, (unsigned long)LONG_MAX + 1, ULONG_MAX};
    const int flag_values[] = {0, -1, INT_MIN, INT_MAX};
    const unsigned int debug_flags[] = {0, 1, 128};
    unsigned int cases = 0;
    assert(sizeof(unsigned long) == 8 && sizeof(long) == 8 && sizeof(size_t) == 8);
    assert(sizeof(struct ddebug) == 32 && _Alignof(struct ddebug) == 8);
    assert(__stop___verbose - __start___verbose == 2);
    for (unsigned int f = 0; f < 3; f++) {
        flags(debug_flags[f]);
        for (unsigned int a = 0; a < 5; a++) for (unsigned int b = 0; b < 5; b++) {
            for (unsigned int d = 0; d < 4; d++) {
                const unsigned long x = values[a], y = values[b], size = values[(a+b)%5];
                const int flag = flag_values[d];
                reset(); original_swapout((void *)x, (void *)y, size, flag);
                struct observation expected = observed;
                assert(expected.cpus == (f != 0) && expected.prints == (f != 0));
                if (f) {
                    assert(strcmp(expected.events, "CP") == 0);
                    assert(expected.slots[0] == 19 && expected.slots[1] == x);
                    assert(expected.slots[2] == y && expected.slots[3] == size);
                    assert(expected.slots[4] == (unsigned long)(long)flag);
                }
                reset(); syscall_swapout_log_bridge((void *)x, (void *)y, size, flag);
                assert(equal(&expected, &observed));
                reset(); assert(fixture_rust_wrapper(1, x, y, size, flag, 0) == -73);
                assert(strcmp(observed.events, f ? "CPB" : "B") == 0);
                assert(observed.bodies == 1 && observed.kind == 1);
                assert(observed.body[0] == x && observed.body[1] == y);
                assert(observed.body[2] == size && observed.body[3] == (unsigned long)(long)flag);
                observed.events[expected.used] = 0;
                observed.used = expected.used; observed.bodies = 0; observed.kind = 0;
                memset(observed.body, 0, sizeof(observed.body));
                assert(equal(&expected, &observed));
                cases++;
            }
            reset(); original_mlock(values[a], values[b]); struct observation expected = observed;
            assert(strcmp(expected.events, "P") == 0 && expected.cpus == 0 && expected.prints == 1);
            assert(expected.slots[0] == values[a] && expected.slots[1] == values[b]);
            reset(); syscall_linux_mlock_log_bridge(values[a], values[b]);
            assert(equal(&expected, &observed));
            reset(); assert(fixture_rust_wrapper(2, values[a], values[b], 0, 0, 0) == -73);
            assert(strcmp(observed.events, "PB") == 0 && observed.bodies == 1 && observed.kind == 2);
            assert(observed.body[0] == values[a] && observed.body[1] == values[b]);
            observed.events[expected.used] = 0; observed.used = expected.used;
            observed.bodies = 0; observed.kind = 0; memset(observed.body, 0, sizeof(observed.body));
            assert(equal(&expected, &observed)); cases++;
        }
    }
    for (int kind = 1; kind <= 2; kind++) {
        reset(); assert(fixture_rust_wrapper(kind, 0, 0, 0, 0, 1) == -14);
        struct observation empty = {0}; assert(equal(&empty, &observed));
    }
    printf("PASS controlled diagnostic parity %u vectors plus 2 null-context wrappers\n", cases);
    return 0;
}
