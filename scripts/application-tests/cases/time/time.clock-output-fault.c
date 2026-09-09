#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>

int main(void) {
    unsigned char *p = mmap(NULL, 8192, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0); if (p == MAP_FAILED) return EXIT_FAILURE;
    p[4096] = 0xa5; if (mprotect(p, 4096, PROT_NONE) != 0) return EXIT_FAILURE;
    errno = 88; int rc = clock_gettime(CLOCK_MONOTONIC, (struct timespec *)p); int saved_errno = errno; int adjacent = p[4096] == 0xa5;
    printf("rc=%d errno=%d adjacent_unchanged=%d\n", rc, saved_errno, adjacent);
    mprotect(p, 4096, PROT_READ | PROT_WRITE); munmap(p, 8192);
    return (rc == -1 && saved_errno == EFAULT && adjacent) ? EXIT_SUCCESS : EXIT_FAILURE;
}
