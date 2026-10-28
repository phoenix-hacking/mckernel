/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Test-only mock effects around the verbatim original C body. No runtime C added. */
#include <types.h>
#include <process.h>
#include <memory.h>
#include <errno.h>

struct fixture_trace {
    unsigned long calls, dst, src, bytes;
    int result;
    unsigned int padding;
    unsigned long written;
};
static struct fixture_trace trace;
static int configured_result;
static unsigned long configured_valid_src;
static size_t configured_prefix;

void fixture_reset(int result, unsigned long valid_src, size_t prefix)
{
    trace.calls = trace.dst = trace.src = trace.bytes = trace.written = 0;
    trace.result = 0;
    trace.padding = 0;
    configured_result = result;
    configured_valid_src = valid_src;
    configured_prefix = prefix;
}

int fixture_copy_from_user(void *dst, const void *src, size_t bytes)
{
    size_t n = bytes;
    trace.calls++;
    trace.dst = (unsigned long)dst;
    trace.src = (unsigned long)src;
    trace.bytes = bytes;
    trace.result = configured_result;
    if (n > configured_prefix)
        n = configured_prefix;
    if (n > 4096)
        n = 4096;
    if (!configured_valid_src || (unsigned long)src != configured_valid_src)
        n = 0;
    for (size_t i = 0; i < n; i++)
        ((unsigned char *)dst)[i] = ((const unsigned char *)src)[i];
    trace.written = n;
    return configured_result;
}

void fixture_read_trace(struct fixture_trace *out)
{
    *out = trace;
}

/* Both renames affect names only; original body bytes are independently pinned. */
#define arch_ptrace_xstate_copy_from_bridge original_arch_ptrace_xstate_copy_from_bridge
#define copy_from_user fixture_copy_from_user
#include "original-xstate-copy-from.c.inc"
#undef copy_from_user
#undef arch_ptrace_xstate_copy_from_bridge
