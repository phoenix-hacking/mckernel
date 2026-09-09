#define _GNU_SOURCE

#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static pthread_barrier_t barrier;
static _Atomic int arrivals, serials, errors;
static void *worker(void *unused) {
    (void)unused;
    for (int generation = 0; generation < 16; ++generation) {
        atomic_fetch_add(&arrivals, 1);
        int rc = pthread_barrier_wait(&barrier);
        if (rc == PTHREAD_BARRIER_SERIAL_THREAD) atomic_fetch_add(&serials, 1);
        else if (rc != 0) atomic_fetch_add(&errors, 1);
    }
    return NULL;
}

static int run(int n) {
    pthread_t tids[8]; atomic_store(&arrivals, 0); atomic_store(&serials, 0); atomic_store(&errors, 0);
    if (pthread_barrier_init(&barrier, NULL, (unsigned)n) != 0) return 0;
    int created = 0;
    for (; created < n; ++created)
        if (pthread_create(&tids[created], NULL, worker, NULL) != 0) break;
    for (int i = 0; i < created; ++i) pthread_join(tids[i], NULL);
    int ok = created == n && atomic_load(&arrivals) == n * 16 &&
             atomic_load(&serials) == 16 && atomic_load(&errors) == 0;
    pthread_barrier_destroy(&barrier);
    return ok;
}

int main(void) {
    int ok2 = run(2), ok4 = run(4), ok8 = run(8);
    printf("n=2 barrier_ok=%d n=4 barrier_ok=%d n=8 barrier_ok=%d\n", ok2, ok4, ok8);
    return (ok2 && ok4 && ok8) ? EXIT_SUCCESS : EXIT_FAILURE;
}
