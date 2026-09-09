#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static pthread_mutex_t mutex;
static _Atomic int started, release_now, after_ok;
static int try_rc;
static void *worker(void *unused) {
    (void)unused; atomic_store(&started, 1);
    try_rc = pthread_mutex_trylock(&mutex);
    while (!atomic_load(&release_now)) sched_yield();
    if (pthread_mutex_lock(&mutex) == 0) {
        atomic_store(&after_ok, 1);
        pthread_mutex_unlock(&mutex);
    }
    return NULL;
}

int main(void) {
    pthread_t tid;
    if (pthread_mutex_init(&mutex, NULL) != 0 || pthread_mutex_lock(&mutex) != 0) return EXIT_FAILURE;
    if (pthread_create(&tid, NULL, worker, NULL) != 0) return EXIT_FAILURE;
    while (!atomic_load(&started)) sched_yield();
    for (int i = 0; i < 100000 && try_rc == 0; ++i) sched_yield();
    pthread_mutex_unlock(&mutex); atomic_store(&release_now, 1);
    pthread_join(tid, NULL); pthread_mutex_destroy(&mutex);
    printf("try_rc=%d busy=%d after_release=%d\n", try_rc, try_rc == EBUSY,
           atomic_load(&after_ok));
    return (try_rc == EBUSY && atomic_load(&after_ok) == 1) ? EXIT_SUCCESS : EXIT_FAILURE;
}
