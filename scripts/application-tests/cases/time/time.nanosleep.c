#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static long long ns(struct timespec t) { return (long long)t.tv_sec * 1000000000LL + t.tv_nsec; }

int main(void) {
    struct timespec req = {0, 10000000}, before, after; if (clock_gettime(CLOCK_MONOTONIC, &before) != 0) return EXIT_FAILURE;
    int rc = nanosleep(&req, NULL); if (clock_gettime(CLOCK_MONOTONIC, &after) != 0) return EXIT_FAILURE;
    long long elapsed = ns(after) - ns(before); printf("rc=%d elapsed_ns=%lld\n", rc, elapsed);
    return (rc == 0 && elapsed >= 10000000LL) ? EXIT_SUCCESS : EXIT_FAILURE;
}
