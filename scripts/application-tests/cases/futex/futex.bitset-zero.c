#define _GNU_SOURCE

#include <errno.h>
#include <linux/futex.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(void) {
    uint32_t word = 0;
    errno = 0;
    long rc = syscall(SYS_futex, &word, FUTEX_WAIT_BITSET, 0, NULL, NULL, 0);
    int saved_errno = errno;
    long wake = syscall(SYS_futex, &word, FUTEX_WAKE, 1, NULL, NULL, 0);
    printf("rc=%ld errno=%d unchanged=%d wake_after=%ld\n", rc, saved_errno,
           word == 0, wake);
    return (rc == -1 && saved_errno == EINVAL && word == 0 && wake == 0)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
