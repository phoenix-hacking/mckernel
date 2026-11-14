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

static _Atomic int a, b, started, completed;
static long result[2];
static void *waiter(void *arg) {
    int slot = (int)(intptr_t)arg;
    atomic_fetch_add(&started, 1);
    result[slot] = syscall(SYS_futex, slot == 0 ? (int *)&a : (int *)&a,
                           FUTEX_WAIT, 0, NULL, NULL, 0);
    if (result[slot] == 0) atomic_fetch_add(&completed, 1);
    return NULL;
}

int main(void) {
    pthread_t t0, t1;
    if (pthread_create(&t0, NULL, waiter, (void *)(intptr_t)0) != 0) return EXIT_FAILURE;
    if (pthread_create(&t1, NULL, waiter, (void *)(intptr_t)1) != 0) return EXIT_FAILURE;
    for (int i = 0; i < 100000 && atomic_load(&started) != 2; ++i) sched_yield();
    long requeued = syscall(SYS_futex, (int *)&a, FUTEX_CMP_REQUEUE, 0, 1,
                            (int *)&b, 0);
    long wake_a = syscall(SYS_futex, (int *)&a, FUTEX_WAKE, 1, NULL, NULL, 0);
    long wake_b = syscall(SYS_futex, (int *)&b, FUTEX_WAKE, 1, NULL, NULL, 0);
    pthread_join(t0, NULL); pthread_join(t1, NULL);
    printf("requeued=%ld wake_a=%ld wake_b=%ld completed=%d result0=%ld result1=%ld\n",
           requeued, wake_a, wake_b, atomic_load(&completed), result[0], result[1]);
    return (requeued == 1 && wake_a == 1 && wake_b == 1 &&
            atomic_load(&completed) == 2 && result[0] == 0 && result[1] == 0)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
