#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    stack_t before, after;
    if (sigaltstack(NULL, &before) != 0) return EXIT_FAILURE;
    /* The selected McKernel x86_64 ABI minimum is 2048, not libc SIGSTKSZ. */
    const size_t kernel_minimum = 2048;
    size_t too_small = kernel_minimum - 1;
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
