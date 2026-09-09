#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(void) {
    struct timespec previous = {0, 0}; size_t bad = 1024; int order_bad = 0;
    for (size_t i = 0; i < 1024; ++i) {
        struct timespec now; if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) return EXIT_FAILURE;
        if (now.tv_nsec < 0 || now.tv_nsec >= 1000000000L) { bad = i; break; }
        if (i && (now.tv_sec < previous.tv_sec || (now.tv_sec == previous.tv_sec && now.tv_nsec < previous.tv_nsec))) { order_bad = 1; bad = i; break; }
        previous = now;
    }
    printf("count=1024 bad_index=%zu order_bad=%d last_sec=%lld last_nsec=%ld\n", bad == 1024 ? (size_t)1024 : bad, order_bad, (long long)previous.tv_sec, previous.tv_nsec);
    return (bad == 1024 && !order_bad) ? EXIT_SUCCESS : EXIT_FAILURE;
}
