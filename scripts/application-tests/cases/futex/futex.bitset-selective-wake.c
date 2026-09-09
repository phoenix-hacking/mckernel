#define _GNU_SOURCE

#include <errno.h>
#include <linux/futex.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <unistd.h>

static _Atomic int word, started, completed;
static long results[2];
static void *waiter(void *arg) {
    int slot = (int)(intptr_t)arg;
    uint32_t bit = slot ? 2u : 1u;
    atomic_fetch_add(&started, 1);
    errno = 0;
    results[slot] = syscall(SYS_futex, (int *)&word, FUTEX_WAIT_BITSET,
                            0, NULL, NULL, bit);
    if (results[slot] == 0) atomic_fetch_add(&completed, 1);
    return NULL;
}

int main(void) {
    pthread_t a, b;
    if (pthread_create(&a, NULL, waiter, (void *)(intptr_t)0) != 0) return EXIT_FAILURE;
    if (pthread_create(&b, NULL, waiter, (void *)(intptr_t)1) != 0) return EXIT_FAILURE;
    for (int i = 0; i < 100000 && atomic_load(&started) != 2; ++i) sched_yield();
    atomic_store(&word, 1);
    long first = syscall(SYS_futex, (int *)&word, FUTEX_WAKE_BITSET, 1, NULL, NULL, 1u);
    for (int i = 0; i < 100000 && atomic_load(&completed) != 1; ++i) sched_yield();
    long second = syscall(SYS_futex, (int *)&word, FUTEX_WAKE_BITSET, 1, NULL, NULL, 2u);
    pthread_join(a, NULL); pthread_join(b, NULL);
    printf("first=%ld second=%ld completed=%d result0=%ld result1=%ld\n",
           first, second, atomic_load(&completed), results[0], results[1]);
    return (first == 1 && second == 1 && atomic_load(&completed) == 2 &&
            results[0] == 0 && results[1] == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
