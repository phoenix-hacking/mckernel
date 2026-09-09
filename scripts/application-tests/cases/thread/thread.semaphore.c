#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static sem_t tokens;
static _Atomic int consumed;
static void *consumer(void *unused) {
    (void)unused;
    for (int i = 0; i < 16; ++i) if (sem_wait(&tokens) == 0) atomic_fetch_add(&consumed, 1);
    return NULL;
}
static void *producer(void *unused) {
    (void)unused;
    for (int i = 0; i < 16; ++i) sem_post(&tokens);
    return NULL;
}

int main(void) {
    pthread_t p, c; if (sem_init(&tokens, 0, 0) != 0) return EXIT_FAILURE;
    if (pthread_create(&c, NULL, consumer, NULL) != 0 || pthread_create(&p, NULL, producer, NULL) != 0) return EXIT_FAILURE;
    pthread_join(p, NULL); pthread_join(c, NULL);
    int value = 0; int extra_rc = sem_trywait(&tokens); int extra_errno = errno;
    sem_getvalue(&tokens, &value);
    printf("consumed=%d extra_rc=%d extra_errno=%d eagain=%d final_value=%d\n",
           atomic_load(&consumed), extra_rc, extra_errno, extra_errno == EAGAIN, value);
    sem_destroy(&tokens);
    return (atomic_load(&consumed) == 16 && extra_rc == -1 && extra_errno == EAGAIN && value == 0)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
