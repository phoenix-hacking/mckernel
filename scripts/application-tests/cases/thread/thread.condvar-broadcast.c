#define _GNU_SOURCE

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static pthread_mutex_t mutex;
static pthread_cond_t cond;
static _Atomic int waiting, awakened, ready;
static void *worker(void *unused) {
    (void)unused; pthread_mutex_lock(&mutex); atomic_fetch_add(&waiting, 1);
    while (!atomic_load(&ready)) pthread_cond_wait(&cond, &mutex);
    atomic_fetch_add(&awakened, 1); pthread_mutex_unlock(&mutex); return NULL;
}

int main(void) {
    enum { N = 4 }; pthread_t tids[N];
    pthread_mutex_init(&mutex, NULL); pthread_cond_init(&cond, NULL);
    for (int i = 0; i < N; ++i) if (pthread_create(&tids[i], NULL, worker, NULL) != 0) return EXIT_FAILURE;
    while (atomic_load(&waiting) != N) sched_yield();
    pthread_mutex_lock(&mutex); atomic_store(&ready, 1); pthread_cond_broadcast(&cond); pthread_mutex_unlock(&mutex);
    for (int i = 0; i < N; ++i) pthread_join(tids[i], NULL);
    printf("waiting=%d awakened=%d ready=%d\n", atomic_load(&waiting), atomic_load(&awakened), atomic_load(&ready));
    pthread_cond_destroy(&cond); pthread_mutex_destroy(&mutex);
    return (atomic_load(&awakened) == N) ? EXIT_SUCCESS : EXIT_FAILURE;
}
