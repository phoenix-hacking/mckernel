#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <stdlib.h>
#include <unistd.h>

static char alt_stack[65536];
static volatile int hits = 0;
static unsigned long hit_stack_in_alt = 0;

static void handler(int signo) {
    (void)signo;
    char marker;
    ++hits;

    const char *in_alt = (void *)&marker >= (void *)alt_stack &&
                         (void *)&marker < (void *)(alt_stack + sizeof(alt_stack))
        ? "inside"
        : "outside";

    if (in_alt[0] == 'i' && hits <= 16) {
        hit_stack_in_alt++;
    }

    printf("handler=%d in_alt=%s\n", hits, in_alt);
}

int main(void) {
    stack_t ss;
    struct sigaction sa;

    memset(&ss, 0, sizeof(ss));
    ss.ss_sp = alt_stack;
    ss.ss_size = sizeof(alt_stack);
    ss.ss_flags = 0;
    if (sigaltstack(&ss, NULL) != 0) {
        perror("sigaltstack");
        return 1;
    }

    memset(&sa, 0, sizeof(sa));
    sa.sa_flags = SA_ONSTACK;
    sa.sa_handler = handler;
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGUSR1, &sa, NULL) != 0) {
        perror("sigaction");
        return 1;
    }

    for (int i = 0; i < 16; i++) {
        if (kill(getpid(), SIGUSR1) != 0) {
            perror("kill");
            return 1;
        }
    }

    printf("delivery=%d alt_hits=%lu\n", hits, hit_stack_in_alt);
    return (hits == 16 && hit_stack_in_alt == 16) ? 0 : 1;
}
