#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int pipefd[2]; static char buffer[4]; static _Atomic int started, handled; static ssize_t read_rc; static int read_errno;
static void handler(int signo) { (void)signo; atomic_fetch_add(&handled, 1); }
static void *reader(void *unused) {
    (void)unused; atomic_store(&started, 1); errno = 0; read_rc = read(pipefd[0], buffer, sizeof(buffer)); read_errno = errno; return NULL;
}

int main(void) {
    struct sigaction sa = {0}; sa.sa_handler = handler; sa.sa_flags = SA_RESTART; sigemptyset(&sa.sa_mask);
    if (pipe(pipefd) != 0 || sigaction(SIGUSR1, &sa, NULL) != 0) return EXIT_FAILURE;
    pthread_t tid; if (pthread_create(&tid, NULL, reader, NULL) != 0) return EXIT_FAILURE;
    while (!atomic_load(&started)) sched_yield();
    if (pthread_kill(tid, SIGUSR1) != 0) return EXIT_FAILURE;
    const char fixed[4] = {'A', 'B', 'C', 'D'}; if (write(pipefd[1], fixed, sizeof(fixed)) != (ssize_t)sizeof(fixed)) return EXIT_FAILURE;
    pthread_join(tid, NULL); close(pipefd[1]); close(pipefd[0]);
    int exact = read_rc == 4 && memcmp(buffer, fixed, sizeof(fixed)) == 0;
    printf("handled=%d rc=%zd bytes=%c%c%c%c exact=%d\n", atomic_load(&handled), read_rc, buffer[0], buffer[1], buffer[2], buffer[3], exact);
    return (atomic_load(&handled) == 1 && exact) ? EXIT_SUCCESS : EXIT_FAILURE;
}
