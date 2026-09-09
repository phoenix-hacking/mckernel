#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

static volatile sig_atomic_t handled;
static void handler(int signo) { (void)signo; ++handled; }

int main(void) {
    struct sigaction sa = {0}; sigset_t set, pending;
    sa.sa_handler = handler; sigemptyset(&sa.sa_mask);
    if (sigaction(SIGUSR1, &sa, NULL) != 0 || sigemptyset(&set) != 0 || sigaddset(&set, SIGUSR1) != 0 ||
        sigprocmask(SIG_BLOCK, &set, NULL) != 0) return EXIT_FAILURE;
    if (raise(SIGUSR1) != 0 || sigpending(&pending) != 0) return EXIT_FAILURE;
    int pending_before = sigismember(&pending, SIGUSR1);
    if (sigprocmask(SIG_UNBLOCK, &set, NULL) != 0) return EXIT_FAILURE;
    sigpending(&pending); int pending_after = sigismember(&pending, SIGUSR1);
    printf("pending_before=%d pending_after=%d handled=%d\n", pending_before, pending_after, handled);
    return (pending_before == 1 && pending_after == 0 && handled == 1) ? EXIT_SUCCESS : EXIT_FAILURE;
}
