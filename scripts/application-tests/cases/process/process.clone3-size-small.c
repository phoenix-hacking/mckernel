#define _GNU_SOURCE

#include <errno.h>
#include <linux/sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef SYS_clone3
#define SYS_clone3 435
#endif
int main(void) {
    struct clone_args args = {0}; errno = 0;
    long rc = syscall(SYS_clone3, &args, 63); int saved_errno = errno;
    if (rc > 0) { int status; waitpid((pid_t)rc, &status, 0); }
    printf("rc=%ld errno=%d einval=%d child_created=%d\n", rc, saved_errno, saved_errno == EINVAL, rc > 0);
    return (rc == -1 && saved_errno == EINVAL) ? EXIT_SUCCESS : EXIT_FAILURE;
}
