#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

static volatile sig_atomic_t handled;
static void handler(int signo) { (void)signo; ++handled; }

int main(void) {
    struct sigaction sa = {0}; sigset_t set;
    sa.sa_handler = handler; sigemptyset(&sa.sa_mask);
    if (sigaction(SIGUSR1, &sa, NULL) != 0 || sigemptyset(&set) != 0 || sigaddset(&set, SIGUSR1) != 0 ||
        sigprocmask(SIG_BLOCK, &set, NULL) != 0 || raise(SIGUSR1) != 0) return EXIT_FAILURE;
    int received = 0; int wait_rc = sigwait(&set, &received);
    printf("wait_rc=%d signal=%d expected=%d handler=%d\n", wait_rc, received, SIGUSR1, handled);
    return (wait_rc == 0 && received == SIGUSR1 && handled == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
