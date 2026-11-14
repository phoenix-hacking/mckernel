#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static long long ns(struct timespec t) { return (long long)t.tv_sec * 1000000000LL + t.tv_nsec; }

int main(void) {
    struct timespec first, second; if (clock_gettime(CLOCK_REALTIME, &first) != 0 || clock_gettime(CLOCK_REALTIME, &second) != 0) return EXIT_FAILURE;
    int valid = first.tv_nsec >= 0 && first.tv_nsec < 1000000000L && second.tv_nsec >= 0 && second.tv_nsec < 1000000000L;
    printf("first_sec=%lld first_nsec=%ld second_sec=%lld second_nsec=%ld nondecreasing=%d valid=%d\n", (long long)first.tv_sec, first.tv_nsec, (long long)second.tv_sec, second.tv_nsec, ns(second) >= ns(first), valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
