#define _GNU_SOURCE

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    void *sentinel = (void *)(uintptr_t)0x13579bdfu;
    void *result = sentinel;
    errno = 123;
    int before = errno;
    int rc = posix_memalign(&result, 3, 64);
    printf("rc=%d\n", rc);
    printf("pointer_unchanged=%d\n", result == sentinel ? 1 : 0);
    printf("errno_before=%d errno_after=%d\n", before, errno);
    return (rc == EINVAL && result == sentinel) ? EXIT_SUCCESS : EXIT_FAILURE;
}
