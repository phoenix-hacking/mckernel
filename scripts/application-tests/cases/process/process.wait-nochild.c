#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    pid_t child = fork(); if (child < 0) return EXIT_FAILURE;
    if (child == 0) _exit(7);
    int status = 0; if (waitpid(child, &status, 0) != child) return EXIT_FAILURE;
    errno = 0; pid_t second = waitpid(child, &status, 0); int saved_errno = errno;
    printf("first_reaped=1 second=%ld errno=%d echild=%d\n", (long)second, saved_errno, saved_errno == ECHILD);
    return (second == -1 && saved_errno == ECHILD) ? EXIT_SUCCESS : EXIT_FAILURE;
}
