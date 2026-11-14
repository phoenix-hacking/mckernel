#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { N = 1000000, MAX_THREADS = 4 };
struct part { int begin, end; uint64_t sum; };
static void *sum_part(void *arg) { struct part *p = arg; p->sum = 0; for (int i = p->begin; i < p->end; ++i) p->sum += (uint64_t)i; return NULL; }
static uint64_t threaded_sum(int threads) {
    pthread_t ids[MAX_THREADS]; struct part p[MAX_THREADS]; int chunk = N / threads;
    for (int t = 0; t < threads; ++t) { p[t].begin = t * chunk; p[t].end = t == threads - 1 ? N : (t + 1) * chunk; if (pthread_create(&ids[t], NULL, sum_part, &p[t]) != 0) return UINT64_MAX; }
    uint64_t total = 0; for (int t = 0; t < threads; ++t) { pthread_join(ids[t], NULL); total += p[t].sum; } return total;
}
int main(void) {
    uint64_t scalar = (uint64_t)(N - 1) * N / 2; int ok = 1;
    for (int threads = 1; threads <= MAX_THREADS; threads *= 2) if (threaded_sum(threads) != scalar) ok = 0;
    printf("scalar=%llu threads=1,2,4 expected=%llu equal=%d valid=%d\n", (unsigned long long)scalar, (unsigned long long)scalar, ok, ok);
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
