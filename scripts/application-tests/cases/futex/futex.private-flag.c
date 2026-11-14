#define _GNU_SOURCE

#include <errno.h>
#include <linux/futex.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <unistd.h>

static _Atomic int word, started, completed;
static long wait_result;
static void *waiter(void *unused) {
    (void)unused; atomic_store(&started, 1); errno = 0;
    wait_result = syscall(SYS_futex, (int *)&word,
                          FUTEX_WAIT | FUTEX_PRIVATE_FLAG, 0, NULL, NULL, 0);
    if (wait_result == 0) atomic_store(&completed, 1);
    return NULL;
}

int main(void) {
    pthread_t t;
    if (pthread_create(&t, NULL, waiter, NULL) != 0) return EXIT_FAILURE;
    for (int i = 0; i < 100000 && !atomic_load(&started); ++i) sched_yield();
    atomic_store(&word, 1);
    long wake = syscall(SYS_futex, (int *)&word,
                        FUTEX_WAKE | FUTEX_PRIVATE_FLAG, 1, NULL, NULL, 0);
    pthread_join(t, NULL);
    printf("wake=%ld completed=%d wait_result=%ld word=%d\n", wake,
           atomic_load(&completed), wait_result, atomic_load(&word));
    return (wake == 1 && atomic_load(&completed) == 1 && wait_result == 0 &&
            atomic_load(&word) == 1) ? EXIT_SUCCESS : EXIT_FAILURE;
}
