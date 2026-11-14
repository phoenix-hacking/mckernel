#define _GNU_SOURCE

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    int p[2]; if (pipe(p) != 0) return EXIT_FAILURE;
    pid_t child = fork(); if (child < 0) return EXIT_FAILURE;
    if (child == 0) { close(p[0]); write(p[1], "X", 1); _exit(24); }
    close(p[0]); close(p[1]); int status = 0; pid_t reaped = waitpid(child, &status, 0);
    printf("reaped=%d signaled=%d signal=%d sigpipe=%d\n", reaped == child, WIFSIGNALED(status),
           WIFSIGNALED(status) ? WTERMSIG(status) : 0, WIFSIGNALED(status) && WTERMSIG(status) == SIGPIPE);
    return (reaped == child && WIFSIGNALED(status) && WTERMSIG(status) == SIGPIPE) ? EXIT_SUCCESS : EXIT_FAILURE;
}
