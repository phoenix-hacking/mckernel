#define _GNU_SOURCE

#include <pthread.h>
#include <signal.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static volatile sig_atomic_t counts[3];
static _Thread_local int slot;
static _Atomic int ready;
static void handler(int signo) { (void)signo; ++counts[slot]; }
static void *worker(void *arg) { slot = *(int *)arg; atomic_fetch_add(&ready, 1); pause(); return NULL; }

int main(void) {
    struct sigaction sa = {0}; pthread_t tids[3]; int ids[3] = {0, 1, 2};
    sa.sa_handler = handler; sigemptyset(&sa.sa_mask);
    if (sigaction(SIGUSR1, &sa, NULL) != 0) return EXIT_FAILURE;
    for (int i = 0; i < 3; ++i) if (pthread_create(&tids[i], NULL, worker, &ids[i]) != 0) return EXIT_FAILURE;
    while (atomic_load(&ready) != 3) sched_yield();
    if (pthread_kill(tids[1], SIGUSR1) != 0) return EXIT_FAILURE;
    for (int i = 0; i < 3; ++i) pthread_cancel(tids[i]);
    for (int i = 0; i < 3; ++i) pthread_join(tids[i], NULL);
    printf("target=1 count0=%d count1=%d count2=%d\n", counts[0], counts[1], counts[2]);
    return (counts[0] == 0 && counts[1] == 1 && counts[2] == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
