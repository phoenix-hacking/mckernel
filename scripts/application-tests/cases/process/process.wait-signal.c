#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    pid_t child = fork(); if (child < 0) return EXIT_FAILURE;
    if (child == 0) for (;;) pause();
    if (kill(child, SIGTERM) != 0) return EXIT_FAILURE;
    int status = 0; pid_t reaped = waitpid(child, &status, 0);
    printf("reaped_match=%d signaled=%d signal=%d sigterm=%d\n", reaped == child,
           WIFSIGNALED(status), WIFSIGNALED(status) ? WTERMSIG(status) : 0,
           WIFSIGNALED(status) && WTERMSIG(status) == SIGTERM);
    return (reaped == child && WIFSIGNALED(status) && WTERMSIG(status) == SIGTERM)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
