#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

int main(void) {
    struct timespec out = {(time_t)0x11223344, 0x55667788}; struct timespec before = out;
    errno = 99; int rc = clock_gettime((clockid_t)-1, &out); int saved_errno = errno;
    printf("rc=%d errno=%d unchanged=%d\n", rc, saved_errno, memcmp(&out, &before, sizeof(out)) == 0);
    return (rc == -1 && saved_errno == EINVAL && memcmp(&out, &before, sizeof(out)) == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
