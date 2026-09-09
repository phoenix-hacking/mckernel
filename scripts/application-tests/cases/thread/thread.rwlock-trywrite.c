#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static pthread_rwlock_t lock;
static _Atomic int release_reader, after_ok;
static int value = 11, try_rc;
static void *writer(void *unused) {
    (void)unused; try_rc = pthread_rwlock_trywrlock(&lock);
    while (!atomic_load(&release_reader)) sched_yield();
    if (pthread_rwlock_wrlock(&lock) == 0) { value = 99; atomic_store(&after_ok, 1); pthread_rwlock_unlock(&lock); }
    return NULL;
}

int main(void) {
    pthread_t tid; pthread_rwlock_init(&lock, NULL);
    if (pthread_rwlock_rdlock(&lock) != 0 || pthread_create(&tid, NULL, writer, NULL) != 0) return EXIT_FAILURE;
    for (int i = 0; i < 100000 && try_rc == 0; ++i) sched_yield();
    int before = value; pthread_rwlock_unlock(&lock); atomic_store(&release_reader, 1);
    pthread_join(tid, NULL);
    printf("try_rc=%d busy=%d before=%d after_ok=%d value=%d\n", try_rc, try_rc == EBUSY,
           before, atomic_load(&after_ok), value);
    pthread_rwlock_destroy(&lock);
    return (try_rc == EBUSY && before == 11 && atomic_load(&after_ok) == 1 && value == 99)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
