#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    pid_t child = fork();
    if (child < 0) return EXIT_FAILURE;
    if (child == 0) _exit(23);
    int status = 0; pid_t reaped = waitpid(child, &status, 0);
    printf("child_pid_positive=%d reaped_match=%d exited=%d code=%d\n", child > 0,
           reaped == child, WIFEXITED(status), WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    return (child > 0 && reaped == child && WIFEXITED(status) && WEXITSTATUS(status) == 23)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
