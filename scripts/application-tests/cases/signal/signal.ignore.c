#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <time.h>

int main(void) {
    if (signal(SIGUSR1, SIG_IGN) == SIG_ERR) return 1;
    fputs("ready\n", stdout); fflush(stdout);
    struct timespec delay = {1, 0}; nanosleep(&delay, NULL);
    fputs("completed=1\n", stdout); fflush(stdout);
    return 0;
}
