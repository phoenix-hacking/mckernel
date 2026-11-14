#define _GNU_SOURCE

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static pthread_mutex_t mutex;
static _Atomic int started, entered;
static void *worker(void *unused) {
    (void)unused; atomic_store(&started, 1);
    if (pthread_mutex_lock(&mutex) == 0) { atomic_store(&entered, 1); pthread_mutex_unlock(&mutex); }
    return NULL;
}

int main(void) {
    pthread_mutexattr_t attr; pthread_t tid;
    if (pthread_mutexattr_init(&attr) != 0 || pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE) != 0 ||
        pthread_mutex_init(&mutex, &attr) != 0) return EXIT_FAILURE;
    int lock1 = pthread_mutex_lock(&mutex), lock2 = pthread_mutex_lock(&mutex);
    if (pthread_create(&tid, NULL, worker, NULL) != 0) return EXIT_FAILURE;
    while (!atomic_load(&started)) sched_yield();
    int unlock1 = pthread_mutex_unlock(&mutex), before = atomic_load(&entered);
    int unlock2 = pthread_mutex_unlock(&mutex); pthread_join(tid, NULL);
    int after = atomic_load(&entered);
    pthread_mutex_destroy(&mutex); pthread_mutexattr_destroy(&attr);
    printf("lock1=%d lock2=%d unlock1=%d unlock2=%d entered_before_final=%d entered_after=%d\n",
           lock1, lock2, unlock1, unlock2, before, after);
    return (lock1 == 0 && lock2 == 0 && unlock1 == 0 && unlock2 == 0 &&
            before == 0 && after == 1) ? EXIT_SUCCESS : EXIT_FAILURE;
}
