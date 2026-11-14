#define _GNU_SOURCE

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef SS_AUTODISARM
#define SS_AUTODISARM (1U << 31)
#endif

static unsigned char storage[16384];
int main(void) {
    stack_t before, requested = {.ss_sp = storage, .ss_size = sizeof(storage), .ss_flags = SS_AUTODISARM}, after;
    if (sigaltstack(NULL, &before) != 0) return EXIT_FAILURE;
    errno = 0; int rc = sigaltstack(&requested, NULL); int saved_errno = errno;
    if (sigaltstack(NULL, &after) != 0) return EXIT_FAILURE;
    int unchanged = before.ss_sp == after.ss_sp && before.ss_size == after.ss_size && before.ss_flags == after.ss_flags;
    printf("rc=%d errno=%d einval=%d unchanged=%d\n", rc, saved_errno, saved_errno == EINVAL, unchanged);
    return (rc == -1 && saved_errno == EINVAL && unchanged) ? EXIT_SUCCESS : EXIT_FAILURE;
}
