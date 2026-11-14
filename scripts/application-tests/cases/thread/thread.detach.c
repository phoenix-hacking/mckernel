#define _GNU_SOURCE

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

static _Atomic int started, completed;
static _Atomic long worker_tid;
static void *worker(void *unused) {
    (void)unused; atomic_store(&worker_tid, (long)syscall(SYS_gettid));
    atomic_store(&started, 1); atomic_store(&completed, 1); return NULL;
}

int main(void) {
    pthread_attr_t attr; pthread_t tid;
    if (pthread_attr_init(&attr) != 0 || pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED) != 0 ||
        pthread_create(&tid, &attr, worker, NULL) != 0) return EXIT_FAILURE;
    pthread_attr_destroy(&attr);
    for (int i = 0; i < 100000 && !atomic_load(&completed); ++i) sched_yield();
    struct timespec pause = {0, 1000000L}; nanosleep(&pause, NULL);
    printf("detached=1 started=%d completed=%d tid_recorded=%d\n", atomic_load(&started),
           atomic_load(&completed), atomic_load(&worker_tid) > 0);
    return (atomic_load(&started) == 1 && atomic_load(&completed) == 1 && atomic_load(&worker_tid) > 0)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
