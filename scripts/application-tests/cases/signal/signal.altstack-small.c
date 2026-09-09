#define _GNU_SOURCE

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    stack_t before, after;
    if (sigaltstack(NULL, &before) != 0) return EXIT_FAILURE;
    size_t too_small = MINSIGSTKSZ > 0 ? (size_t)MINSIGSTKSZ - 1 : 0;
    void *storage = malloc(too_small ? too_small : 1);
    if (!storage) return EXIT_FAILURE;
    stack_t requested = {.ss_sp = storage, .ss_size = too_small, .ss_flags = 0};
    errno = 0; int rc = sigaltstack(&requested, NULL); int saved_errno = errno;
    if (sigaltstack(NULL, &after) != 0) return EXIT_FAILURE;
    int unchanged = before.ss_sp == after.ss_sp && before.ss_size == after.ss_size && before.ss_flags == after.ss_flags;
    printf("rc=%d errno=%d enomem=%d unchanged=%d\n", rc, saved_errno, saved_errno == ENOMEM, unchanged);
    free(storage);
    return (rc == -1 && saved_errno == ENOMEM && unchanged) ? EXIT_SUCCESS : EXIT_FAILURE;
}
