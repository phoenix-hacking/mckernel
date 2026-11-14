#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

int main(void) {
    unsigned char *p = mmap(NULL, 8192, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return EXIT_FAILURE;
    p[0] = 0x12; p[4096] = 0x34;
    errno = 88;
    int rc = munmap(p + 1, 4096);
    int saved_errno = errno;
    int intact = (p[0] == 0x12 && p[4096] == 0x34);
    printf("rc=%d errno=%d intact=%d\n", rc, saved_errno, intact);
    if (munmap(p, 8192) != 0) return EXIT_FAILURE;
    return (rc == -1 && saved_errno == EINVAL && intact) ? EXIT_SUCCESS : EXIT_FAILURE;
}
