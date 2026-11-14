#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <stdlib.h>
#include <unistd.h>

static char alt_stack[65536];
static volatile int phase = 0;

static void nested_handler(int signo) {
    (void)signo;
    printf("inner=%d\n", ++phase);
}

static void outer_handler(int signo) {
    (void)signo;

    printf("outer-enter=%d\n", ++phase);
    kill(getpid(), SIGUSR2);
    printf("outer-exit=%d\n", ++phase);
}

int main(void) {
    struct sigaction sa_usr1;
    struct sigaction sa_usr2;
    stack_t ss;

    memset(&ss, 0, sizeof(ss));
    ss.ss_sp = alt_stack;
    ss.ss_size = sizeof(alt_stack);
    ss.ss_flags = 0;
    if (sigaltstack(&ss, NULL) != 0) {
        perror("sigaltstack");
        return 1;
    }

    memset(&sa_usr1, 0, sizeof(sa_usr1));
    sa_usr1.sa_flags = SA_ONSTACK;
    sa_usr1.sa_handler = outer_handler;
    sigemptyset(&sa_usr1.sa_mask);

    memset(&sa_usr2, 0, sizeof(sa_usr2));
    sa_usr2.sa_flags = SA_ONSTACK;
    sa_usr2.sa_handler = nested_handler;
    sigemptyset(&sa_usr2.sa_mask);

    if (sigaction(SIGUSR1, &sa_usr1, NULL) != 0) {
        perror("sigaction usr1");
        return 1;
    }
    if (sigaction(SIGUSR2, &sa_usr2, NULL) != 0) {
        perror("sigaction usr2");
        return 1;
    }

    kill(getpid(), SIGUSR1);

    printf("phase=%d\n", phase);
    return phase == 3 ? 0 : 1;
}
