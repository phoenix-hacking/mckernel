#define _GNU_SOURCE

#include <errno.h>
#include <linux/futex.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

static long long ns(const struct timespec *t) {
    return (long long)t->tv_sec * 1000000000LL + t->tv_nsec;
}

int main(void) {
    uint32_t word = 0;
    struct timespec start, deadline, finish;
    if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) return EXIT_FAILURE;
    deadline = start;
    deadline.tv_nsec += 20000000L;
    if (deadline.tv_nsec >= 1000000000L) {
        ++deadline.tv_sec;
        deadline.tv_nsec -= 1000000000L;
    }
    errno = 0;
    long rc = syscall(SYS_futex, &word, FUTEX_WAIT_BITSET, 0, &deadline,
                      NULL, FUTEX_BITSET_MATCH_ANY);
    int saved_errno = errno;
    if (clock_gettime(CLOCK_MONOTONIC, &finish) != 0) return EXIT_FAILURE;
    long long elapsed = ns(&finish) - ns(&start);
    printf("rc=%ld errno=%d unchanged=%d elapsed_ns=%lld\n", rc, saved_errno,
           word == 0, elapsed);
    return (rc == -1 && saved_errno == ETIMEDOUT && word == 0)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
