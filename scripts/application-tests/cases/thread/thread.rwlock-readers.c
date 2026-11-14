#define _GNU_SOURCE

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static pthread_rwlock_t lock;
static _Atomic int ready, release_readers, old_reads, writer_done;
static int value = 7;
static void *reader(void *unused) {
    (void)unused; pthread_rwlock_rdlock(&lock);
    if (value == 7) atomic_fetch_add(&old_reads, 1);
    atomic_fetch_add(&ready, 1);
    while (!atomic_load(&release_readers)) sched_yield();
    pthread_rwlock_unlock(&lock); return NULL;
}
static void *writer(void *unused) {
    (void)unused; while (atomic_load(&ready) != 2) sched_yield();
    pthread_rwlock_wrlock(&lock); value = 42; atomic_store(&writer_done, 1);
    pthread_rwlock_unlock(&lock); return NULL;
}

int main(void) {
    pthread_t r0, r1, w; pthread_rwlock_init(&lock, NULL);
    if (pthread_create(&r0, NULL, reader, NULL) != 0 || pthread_create(&r1, NULL, reader, NULL) != 0 || pthread_create(&w, NULL, writer, NULL) != 0) return EXIT_FAILURE;
    while (atomic_load(&ready) != 2) sched_yield();
    for (int i = 0; i < 10000 && atomic_load(&writer_done); ++i) sched_yield();
    int before = atomic_load(&writer_done); atomic_store(&release_readers, 1);
    pthread_join(r0, NULL); pthread_join(r1, NULL); pthread_join(w, NULL);
    printf("old_reads=%d writer_before_release=%d writer_done=%d value=%d\n",
           atomic_load(&old_reads), before, atomic_load(&writer_done), value);
    pthread_rwlock_destroy(&lock);
    return (atomic_load(&old_reads) == 2 && before == 0 && atomic_load(&writer_done) == 1 && value == 42)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
