#define _GNU_SOURCE

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <linux/futex.h>
#include <unistd.h>

int main(void) {
    uint32_t *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0); if (p == MAP_FAILED) return EXIT_FAILURE;
    if (munmap(p, 4096) != 0) return EXIT_FAILURE;
    errno = 73; long rc = syscall(SYS_futex, p, FUTEX_WAIT, 0, NULL, NULL, 0); int saved_errno = errno;
    printf("rc=%ld errno=%d e_fault=%d\n", rc, saved_errno, saved_errno == EFAULT);
    return (rc == -1 && saved_errno == EFAULT) ? EXIT_SUCCESS : EXIT_FAILURE;
}
