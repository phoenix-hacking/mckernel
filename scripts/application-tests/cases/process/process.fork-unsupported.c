#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    errno = 0; pid_t child = fork(); int saved_errno = errno;
    int child_created = child > 0, child_status = 0;
    if (child == 0) _exit(24);
    if (child_created) waitpid(child, &child_status, 0);
    printf("rc=%ld errno=%d eopnotsupp=%d child_created=%d clean=%d\n", (long)child, saved_errno,
           saved_errno == EOPNOTSUPP, child_created, !child_created || (WIFEXITED(child_status) && WEXITSTATUS(child_status) == 24));
    return (child == -1 && saved_errno == EOPNOTSUPP && !child_created) ? EXIT_SUCCESS : EXIT_FAILURE;
}
