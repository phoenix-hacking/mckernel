#define _GNU_SOURCE

#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static pthread_once_t once = PTHREAD_ONCE_INIT;
static _Atomic int initializer_calls, all_seen;
static int published;
static void initialize(void) { atomic_fetch_add(&initializer_calls, 1); published = 0x51a7; }
static void *worker(void *unused) {
    (void)unused;
    for (int i = 0; i < 16; ++i)
        if (pthread_once(&once, initialize) != 0 || published != 0x51a7) return NULL;
    atomic_fetch_add(&all_seen, 1); return NULL;
}

int main(void) {
    enum { N = 8 }; pthread_t tids[N];
    for (int i = 0; i < N; ++i) if (pthread_create(&tids[i], NULL, worker, NULL) != 0) return EXIT_FAILURE;
    for (int i = 0; i < N; ++i) pthread_join(tids[i], NULL);
    printf("threads=%d initializer_calls=%d all_seen=%d published=%d\n", N,
           atomic_load(&initializer_calls), atomic_load(&all_seen), published);
    return (atomic_load(&initializer_calls) == 1 && atomic_load(&all_seen) == N && published == 0x51a7)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
