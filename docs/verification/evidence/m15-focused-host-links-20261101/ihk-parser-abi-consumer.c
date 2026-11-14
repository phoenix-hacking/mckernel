/* Nonshipped HOST consumer of the actual exported libihk parser ABI.
 * Real recovered headers, real shared library and libc; no project providers.
 * Valid pure CPU parser/formatter calls only, with no OS/device operations.
 */
#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ihk/ihklib.h>
#include <ihk/ihklib_private.h>

_Static_assert(__builtin_types_compatible_p(__typeof__(&cpu_str2count),
    int (*)(char *)), "actual parser count ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&cpu_str2req),
    int (*)(char *, int, struct ihk_cpu_req *)), "actual parser request ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&cpu_req2str),
    char *(*)(struct ihk_cpu_req *)), "actual formatter ABI");

static void check(const int *cpus, int count, const char *expected)
{
    struct ihk_cpu_req input = { .cpus = (int *)cpus, .num_cpus = count };
    char *text = cpu_req2str(&input);
    assert(text != NULL);
    assert(strcmp(text, expected) == 0);
    if (count != 0) {
        int parsed_count = cpu_str2count(text);
        assert(parsed_count == count);
        int *values = calloc((size_t)count, sizeof(*values));
        assert(values != NULL);
        struct ihk_cpu_req output = { .cpus = values, .num_cpus = 0 };
        assert(cpu_str2req(text, count, &output) == count);
        assert(output.num_cpus == count);
        assert(memcmp(values, cpus, (size_t)count * sizeof(*values)) == 0);
        free(values);
    }
    free(text);
}

int main(void)
{
    Dl_info loaded;
    void *formatter_provider = dlsym(RTLD_DEFAULT, "cpu_req2str");
    assert(formatter_provider != NULL);
    assert(dladdr(formatter_provider, &loaded) != 0);
    assert(strcmp(loaded.dli_fname, CONSUMER_LIBRARY) == 0);
    printf("Actual formatter provider: %s\n", loaded.dli_fname);
    /* Build the independent expected string from maximal membership runs. */
    for (unsigned bits = 1; bits < 256; ++bits) {
        int cpus[8], count = 0;
        char expected[64] = {0};
        size_t offset = 0;
        for (int cpu = 0; cpu < 8; ++cpu)
            if (bits & (1u << cpu)) cpus[count++] = cpu;
        for (int first = 0; first < 8;) {
            if (!(bits & (1u << first))) { ++first; continue; }
            int last = first;
            while (last + 1 < 8 && (bits & (1u << (last + 1)))) ++last;
            int written = snprintf(expected + offset, sizeof(expected) - offset,
                                   "%s%d", offset ? "," : "", first);
            assert(written > 0 && (size_t)written < sizeof(expected) - offset);
            offset += (size_t)written;
            if (last != first) {
                written = snprintf(expected + offset, sizeof(expected) - offset,
                                   "-%d", last);
                assert(written > 0 && (size_t)written < sizeof(expected) - offset);
                offset += (size_t)written;
            }
            first = last + 1;
        }
        check(cpus, count, expected);
    }
    const int zero_gap[] = {0, 2};
    check(zero_gap, 2, "0,2");
    check(NULL, 0, "");
    int sparse[64];
    char expected[512] = {0};
    size_t offset = 0;
    for (int i = 0; i < 64; ++i) {
        sparse[i] = i * 2;
        int written = snprintf(expected + offset, sizeof(expected) - offset,
                               "%s%d", i ? "," : "", sparse[i]);
        assert(written > 0 && (size_t)written < sizeof(expected) - offset);
        offset += (size_t)written;
    }
    assert(offset > 64);
    check(sparse, 64, expected);
    puts("PASS actual libihk exported C ABI: 255 nonempty CPU subsets, explicit CPU0-gap, empty output, and sparse buffer growth; 257 parser/formatter round trips; no device APIs");
    return 0;
}
