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
    (void)unused; atomic_fetch_add(&started, 1); long rc = syscall(SYS_futex, (int *)&word, FUTEX_WAIT, 0, NULL, NULL, 0);
    if (rc == 0) atomic_fetch_add(&completed, 1); return (void *)(rc == 0 ? 0 : 1);
}

static int wake_until_one(void) {
    for (int i = 0; i < 1000; ++i) { long n = syscall(SYS_futex, (int *)&word, FUTEX_WAKE, 1, NULL, NULL, 0); if (n == 1) return 1; if (n == 0) sched_yield(); else return -1; }
    return 0;
}

int main(void) {
    pthread_t a, b; if (pthread_create(&a, NULL, waiter, NULL) != 0 || pthread_create(&b, NULL, waiter, NULL) != 0) return EXIT_FAILURE;
    for (int i = 0; i < 100000 && atomic_load(&started) != 2; ++i) sched_yield();
    atomic_store(&word, 1); int first = wake_until_one(); int second = wake_until_one(); void *ra = NULL, *rb = NULL; pthread_join(a, &ra); pthread_join(b, &rb);
    long after = syscall(SYS_futex, (int *)&word, FUTEX_WAKE, 1, NULL, NULL, 0);
    printf("started=%d first=%d second=%d completed=%d threads_ok=%d wake_after=%ld\n", atomic_load(&started), first, second, atomic_load(&completed), ra == NULL && rb == NULL, after);
    return (first == 1 && second == 1 && atomic_load(&completed) == 2 && ra == NULL && rb == NULL && after == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
