/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact pinned Linux timeout validators, with a fixed initial-namespace clock. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
typedef int64_t s64;
typedef uint32_t u32;
typedef int64_t ktime_t;
struct timespec64 { int64_t tv_sec, tv_nsec; };
#define NSEC_PER_SEC 1000000000L
#define KTIME_MAX INT64_MAX
#define KTIME_SEC_MAX (KTIME_MAX / NSEC_PER_SEC)
#define unlikely(x) (x)
#define FUTEX_WAIT 0
#define FUTEX_LOCK_PI 6
#define FUTEX_CLOCK_REALTIME 256
#define CLOCK_MONOTONIC 1
#define ktime_add_unsafe(a,b) ((int64_t)((uint64_t)(a) + (uint64_t)(b)))
static ktime_t fixed_now;
static ktime_t ktime_get(void) { return fixed_now; }
static ktime_t timens_ktime_to_host(int clock_id, ktime_t value)
{
    assert(clock_id == CLOCK_MONOTONIC);
    return value;
}
#include "linux-time-bodies.h"
int main(int argc, char **argv)
{
    assert(argc == 2);
    FILE *input = fopen(argv[1], "rb");
    assert(input);
    int64_t vector[5];
    unsigned index = 0;
    while (fread(vector, sizeof vector, 1, input) == 1) {
        struct timespec64 requested = { vector[1], vector[2] };
        struct timespec64 now = { vector[3], vector[4] };
        assert(timespec64_valid(&now));
        fixed_now = timespec64_to_ktime(now);
        ktime_t deadline = 0;
        int result = futex_init_timeout(vector[0], 0, &requested, &deadline);
        uint64_t remaining = !result && deadline > fixed_now ? (uint64_t)(deadline - fixed_now) : 0;
        printf("%u %d %llu\n", index++, result, (unsigned long long)remaining);
    }
    assert(feof(input));
    assert(fclose(input) == 0);
    return 0;
}
