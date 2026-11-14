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
    unsigned char storage[4097] = {0}; struct clone_args *args = (struct clone_args *)storage;
    errno = 0; long rc = syscall(SYS_clone3, args, sizeof(storage)); int saved_errno = errno;
    if (rc > 0) { int status; waitpid((pid_t)rc, &status, 0); }
    printf("rc=%ld errno=%d e2big=%d child_created=%d\n", rc, saved_errno, saved_errno == E2BIG, rc > 0);
    return (rc == -1 && saved_errno == E2BIG) ? EXIT_SUCCESS : EXIT_FAILURE;
}
