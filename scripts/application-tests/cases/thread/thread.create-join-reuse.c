#define _GNU_SOURCE

#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static _Atomic int jobs, unique_jobs;
static void *worker(void *arg) {
    int expected = *(int *)arg;
    if (expected >= 0) atomic_fetch_add(&jobs, 1);
    return NULL;
}

int main(void) {
    atomic_store(&jobs, 0); atomic_store(&unique_jobs, 0);
    for (int i = 0; i < 32; ++i) {
        pthread_t tid; int id = i;
        if (pthread_create(&tid, NULL, worker, &id) != 0) return EXIT_FAILURE;
        void *result = NULL;
        if (pthread_join(tid, &result) != 0 || result != NULL) return EXIT_FAILURE;
        atomic_fetch_add(&unique_jobs, 1);
    }
    printf("jobs=%d unique_jobs=%d\n", atomic_load(&jobs), atomic_load(&unique_jobs));
    return (atomic_load(&jobs) == 32 && atomic_load(&unique_jobs) == 32)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
