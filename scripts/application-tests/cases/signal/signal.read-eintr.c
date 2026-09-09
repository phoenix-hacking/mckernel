#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int pipefd[2]; static unsigned char buffer[4] = {0xa5, 0xa5, 0xa5, 0xa5};
static _Atomic int started, handled; static ssize_t read_rc; static int read_errno;
static void handler(int signo) { (void)signo; atomic_fetch_add(&handled, 1); }
static void *reader(void *unused) {
    (void)unused; atomic_store(&started, 1); errno = 0;
    read_rc = read(pipefd[0], buffer, sizeof(buffer)); read_errno = errno; return NULL;
}

int main(void) {
    struct sigaction sa = {0}; sa.sa_handler = handler; sigemptyset(&sa.sa_mask);
    if (pipe(pipefd) != 0 || sigaction(SIGUSR1, &sa, NULL) != 0) return EXIT_FAILURE;
    pthread_t tid; if (pthread_create(&tid, NULL, reader, NULL) != 0) return EXIT_FAILURE;
    while (!atomic_load(&started)) sched_yield();
    if (pthread_kill(tid, SIGUSR1) != 0) return EXIT_FAILURE;
    pthread_join(tid, NULL); int untouched = buffer[0] == 0xa5 && buffer[1] == 0xa5 && buffer[2] == 0xa5 && buffer[3] == 0xa5;
    close(pipefd[1]); close(pipefd[0]);
    printf("rc=%zd errno=%d eintr=%d handled=%d untouched=%d\n", read_rc, read_errno, read_errno == EINTR, atomic_load(&handled), untouched);
    return (read_rc == -1 && read_errno == EINTR && atomic_load(&handled) == 1 && untouched) ? EXIT_SUCCESS : EXIT_FAILURE;
}
