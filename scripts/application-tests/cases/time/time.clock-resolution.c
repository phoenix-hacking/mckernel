#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(void) {
    struct timespec mono, real; int m = clock_getres(CLOCK_MONOTONIC, &mono), r = clock_getres(CLOCK_REALTIME, &real);
    int valid = m == 0 && r == 0 && mono.tv_sec >= 0 && real.tv_sec >= 0 && mono.tv_nsec > 0 && mono.tv_nsec < 1000000000L && real.tv_nsec > 0 && real.tv_nsec < 1000000000L;
    printf("mono_rc=%d mono_sec=%lld mono_nsec=%ld real_rc=%d real_sec=%lld real_nsec=%ld valid=%d\n", m, (long long)mono.tv_sec, mono.tv_nsec, r, (long long)real.tv_sec, real.tv_nsec, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
