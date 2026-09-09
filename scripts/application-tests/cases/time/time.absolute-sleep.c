#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static long long ns(struct timespec t) { return (long long)t.tv_sec * 1000000000LL + t.tv_nsec; }

int main(void) {
    struct timespec before, deadline, after; if (clock_gettime(CLOCK_MONOTONIC, &before) != 0) return EXIT_FAILURE;
    deadline = before; deadline.tv_nsec += 10000000L; if (deadline.tv_nsec >= 1000000000L) { ++deadline.tv_sec; deadline.tv_nsec -= 1000000000L; }
    int rc = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &deadline, NULL); if (clock_gettime(CLOCK_MONOTONIC, &after) != 0) return EXIT_FAILURE;
    printf("rc=%d before_ns=%lld deadline_ns=%lld after_ns=%lld reached=%d\n", rc, ns(before), ns(deadline), ns(after), ns(after) >= ns(deadline));
    return (rc == 0 && ns(after) >= ns(deadline)) ? EXIT_SUCCESS : EXIT_FAILURE;
}
