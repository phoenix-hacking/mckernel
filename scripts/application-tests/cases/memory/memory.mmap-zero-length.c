#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

int main(void) {
    errno = 41;
    void *p = mmap(NULL, 0, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    int saved_errno = errno;
    printf("failed=%d errno=%d\n", p == MAP_FAILED ? 1 : 0, saved_errno);
    return (p == MAP_FAILED && saved_errno == EINVAL) ? EXIT_SUCCESS : EXIT_FAILURE;
}
