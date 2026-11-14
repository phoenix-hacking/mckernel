#define _GNU_SOURCE

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

static volatile sig_atomic_t handled;
static void handler(int signo) { (void)signo; ++handled; }

int main(void) {
    struct sigaction sa = {0}; sigset_t blocked, empty, after;
    sa.sa_handler = handler; sigemptyset(&sa.sa_mask);
    if (sigaction(SIGUSR1, &sa, NULL) != 0 || sigemptyset(&blocked) != 0 || sigaddset(&blocked, SIGUSR1) != 0 ||
        sigprocmask(SIG_BLOCK, &blocked, NULL) != 0 || raise(SIGUSR1) != 0 || sigemptyset(&empty) != 0) return EXIT_FAILURE;
    errno = 0; int rc = sigsuspend(&empty); int saved_errno = errno;
    if (sigprocmask(SIG_SETMASK, NULL, &after) != 0) return EXIT_FAILURE;
    int restored = sigismember(&after, SIGUSR1) == 1;
    printf("rc=%d errno=%d eintr=%d handled=%d restored=%d\n", rc, saved_errno, saved_errno == EINTR, handled, restored);
    return (rc == -1 && saved_errno == EINTR && handled == 1 && restored) ? EXIT_SUCCESS : EXIT_FAILURE;
}
