#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <linux/futex.h>
#include <unistd.h>

static _Atomic int word, started, completed;
static void *waiter(void *unused) {
    (void)unused; atomic_store(&started, 1);
    long rc = syscall(SYS_futex, (int *)&word, FUTEX_WAIT, 0, NULL, NULL, 0);
    if (rc == 0) atomic_fetch_add(&completed, 1); return (void *)(rc == 0 ? 0 : 1);
}

int main(void) {
    pthread_t t; if (pthread_create(&t, NULL, waiter, NULL) != 0) return EXIT_FAILURE;
    for (int i = 0; i < 100000 && !atomic_load(&started); ++i) sched_yield();
    int wake_one = 0; atomic_store(&word, 1);
    for (int i = 0; i < 1000 && wake_one == 0; ++i) { long n = syscall(SYS_futex, (int *)&word, FUTEX_WAKE, 1, NULL, NULL, 0); if (n > 0) wake_one = (int)n; else sched_yield(); }
    void *result = NULL; pthread_join(t, &result); long wake_after = syscall(SYS_futex, (int *)&word, FUTEX_WAKE, 1, NULL, NULL, 0);
    printf("wake_one=%d completed=%d thread_ok=%d wake_after=%ld\n", wake_one, atomic_load(&completed), result == NULL, wake_after);
    return (wake_one == 1 && atomic_load(&completed) == 1 && result == NULL && wake_after == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
