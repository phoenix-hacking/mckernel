#define _GNU_SOURCE

#include <errno.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <time.h>
#include <linux/futex.h>
#include <unistd.h>

static long long ns(struct timespec t) { return (long long)t.tv_sec * 1000000000LL + t.tv_nsec; }

int main(void) {
    _Atomic int word = 0; struct timespec timeout = {0, 20000000}, before, after; clock_gettime(CLOCK_MONOTONIC, &before);
    long rc = syscall(SYS_futex, (int *)&word, FUTEX_WAIT, 0, &timeout, NULL, 0); int saved_errno = errno; clock_gettime(CLOCK_MONOTONIC, &after);
    long long elapsed = ns(after) - ns(before); printf("rc=%ld errno=%d unchanged=%d elapsed_ns=%lld\n", rc, saved_errno, atomic_load(&word) == 0, elapsed);
    return (rc == -1 && saved_errno == ETIMEDOUT && atomic_load(&word) == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
