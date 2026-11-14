#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

static volatile sig_atomic_t handled;
static void handler(int signo) { (void)signo; ++handled; }

int main(void) {
    struct sigaction install = {0}, after;
    install.sa_handler = handler; install.sa_flags = SA_RESETHAND; sigemptyset(&install.sa_mask);
    if (sigaction(SIGUSR1, &install, NULL) != 0 || raise(SIGUSR1) != 0 || sigaction(SIGUSR1, NULL, &after) != 0) return EXIT_FAILURE;
    int reset_default = after.sa_handler == SIG_DFL;
    printf("handled=%d reset_default=%d flags=%d\n", handled, reset_default, after.sa_flags);
    return (handled == 1 && reset_default) ? EXIT_SUCCESS : EXIT_FAILURE;
}
