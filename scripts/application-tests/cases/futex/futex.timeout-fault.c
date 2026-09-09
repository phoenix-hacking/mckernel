#define _GNU_SOURCE

#include <errno.h>
#include <linux/futex.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

int main(void) {
    uint32_t word = 0;
    struct timespec *bad = mmap(NULL, 4096, PROT_NONE,
                                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (bad == MAP_FAILED) return EXIT_FAILURE;
    errno = 0;
    long rc = syscall(SYS_futex, &word, FUTEX_WAIT, 0, bad, NULL, 0);
    int saved_errno = errno;
    int unmapped = munmap(bad, 4096) == 0;
    printf("rc=%ld errno=%d unchanged=%d unmapped=%d\n", rc, saved_errno,
           word == 0, unmapped);
    return (rc == -1 && saved_errno == EFAULT && word == 0 && unmapped)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
