#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

int main(void) {
    struct timespec req = {0, 1000000000L}, rem = {(time_t)0x11223344, 0x55667788}; struct timespec before = rem;
    errno = 66; int rc = nanosleep(&req, &rem); int saved_errno = errno;
    printf("rc=%d errno=%d rem_unchanged=%d\n", rc, saved_errno, memcmp(&rem, &before, sizeof(rem)) == 0);
    return (rc == -1 && saved_errno == EINVAL) ? EXIT_SUCCESS : EXIT_FAILURE;
}
