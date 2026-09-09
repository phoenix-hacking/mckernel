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
    long rc = syscall(SYS_futex, &word, 0x7f, 0, NULL, NULL, 0);
    int saved_errno = errno;
    printf("rc=%ld errno=%d unchanged=%d\n", rc, saved_errno, word == 0);
    return (rc == -1 && saved_errno == ENOSYS && word == 0)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
