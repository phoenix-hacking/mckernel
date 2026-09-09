#define _GNU_SOURCE

#include <errno.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <time.h>
#include <linux/futex.h>
#include <unistd.h>

int main(void) {
    _Atomic int word = 0; struct timespec timeout = {-1, 1}; errno = 88;
    long rc = syscall(SYS_futex, (int *)&word, FUTEX_WAIT, 0, &timeout, NULL, 0); int saved_errno = errno;
    printf("rc=%ld errno=%d unchanged=%d\n", rc, saved_errno, atomic_load(&word) == 0);
    return (rc == -1 && saved_errno == EINVAL && atomic_load(&word) == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
