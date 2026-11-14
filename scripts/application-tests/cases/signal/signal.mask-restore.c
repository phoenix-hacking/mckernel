#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif

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
    int restored = 1;
    for (int signo = 1; signo < NSIG; ++signo) {
        int before_member = sigismember(&baseline, signo);
        int after_member = sigismember(&after, signo);
        if (before_member < 0 || after_member < 0 || before_member != after_member) restored = 0;
    }
    printf("handled=%d observed_blocked=%d restored=%d\n", handled, observed_blocked, restored);
    return (handled == 1 && observed_blocked == 1 && restored) ? EXIT_SUCCESS : EXIT_FAILURE;
}
