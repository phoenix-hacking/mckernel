#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

static volatile sig_atomic_t handled, observed_blocked;
static void handler(int signo) {
    (void)signo; sigset_t current;
    if (sigprocmask(SIG_SETMASK, NULL, &current) == 0 && sigismember(&current, SIGUSR2) == 1) observed_blocked = 1;
    ++handled;
}

int main(void) {
    struct sigaction sa = {0}; sigset_t required, baseline, after;
    sigemptyset(&sa.sa_mask); sigaddset(&sa.sa_mask, SIGUSR2); sa.sa_handler = handler;
    if (sigprocmask(SIG_SETMASK, NULL, &baseline) != 0 || sigaction(SIGUSR1, &sa, NULL) != 0 || raise(SIGUSR1) != 0 ||
        sigprocmask(SIG_SETMASK, NULL, &after) != 0) return EXIT_FAILURE;
    sigemptyset(&required);
    int restored = sigismember(&baseline, SIGUSR1) == sigismember(&after, SIGUSR1) &&
                   sigismember(&baseline, SIGUSR2) == sigismember(&after, SIGUSR2);
    printf("handled=%d observed_blocked=%d restored=%d\n", handled, observed_blocked, restored);
    return (handled == 1 && observed_blocked == 1 && restored) ? EXIT_SUCCESS : EXIT_FAILURE;
}
