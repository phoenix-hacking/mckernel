#define _GNU_SOURCE

#include <errno.h>
#include <linux/futex.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <unistd.h>

static _Atomic int word, started, signals;
static long wait_result;
static int wait_errno;
static void handler(int signo) { (void)signo; atomic_fetch_add(&signals, 1); }
static void *waiter(void *unused) {
    (void)unused; atomic_store(&started, 1); errno = 0;
    wait_result = syscall(SYS_futex, (int *)&word, FUTEX_WAIT, 0, NULL, NULL, 0);
    wait_errno = errno;
    return NULL;
}

int main(void) {
    struct sigaction sa = {0};
    sa.sa_handler = handler;
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGUSR1, &sa, NULL) != 0) return EXIT_FAILURE;
    pthread_t t;
    if (pthread_create(&t, NULL, waiter, NULL) != 0) return EXIT_FAILURE;
    for (int i = 0; i < 100000 && !atomic_load(&started); ++i) sched_yield();
    if (pthread_kill(t, SIGUSR1) != 0) return EXIT_FAILURE;
    pthread_join(t, NULL);
    long wake_after = syscall(SYS_futex, (int *)&word, FUTEX_WAKE, 1, NULL, NULL, 0);
    printf("wait_result=%ld errno=%d signals=%d wake_after=%ld word=%d\n",
           wait_result, wait_errno, atomic_load(&signals), wake_after,
           atomic_load(&word));
    return (wait_result == -1 && wait_errno == EINTR && atomic_load(&signals) == 1 &&
            wake_after == 0 && atomic_load(&word) == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
