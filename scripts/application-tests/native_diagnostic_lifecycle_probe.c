/* SPDX-License-Identifier: GPL-2.0 */
/* Linux side of an isolated native guest, after application completion.
 * This diagnostic neither destroys the OS nor proves resource restoration.
 * Run with an external timeout; each operation is attempted exactly once.
 * Build against the pinned IHK headers, never an unverified working checkout.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <ihk/ihk_host_user.h>

#if !defined(__x86_64__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "The current native ABI requires little-endian x86_64"
#endif
_Static_assert(sizeof(long) == 8 && sizeof(void *) == 8, "native LP64 ABI");
_Static_assert(IHK_OS_SHUTDOWN == 0x112a02, "frozen shutdown request");
_Static_assert(IHK_OS_QUERY_STATUS == 0x112a03, "frozen status request");
_Static_assert(IHK_OS_STATUS_NOT_BOOTED == 0, "shutdown completion status");

/* Tests replace only this syscall boundary and execute the same main below. */
#ifndef LIFECYCLE_OPEN
#define LIFECYCLE_OPEN open
#define LIFECYCLE_IOCTL ioctl
#define LIFECYCLE_CLOSE close
#endif

static int record(const char *operation, unsigned long request, int rc, int error)
{
    /* libc returns -1/errno; linux_result reconstructs the signed ABI result. */
    if (printf("{\"operation\":\"%s\",\"request\":%lu,\"return\":%d,"
               "\"errno\":%d,\"linux_result\":%d}\n",
               operation, request, rc, error, rc == -1 ? -error : rc) < 0)
        return -1;
    return fflush(stdout);
}

static int query(int fd, const char *operation, int *logged)
{
    int result, error;
    errno = 0;
    result = LIFECYCLE_IOCTL(fd, IHK_OS_QUERY_STATUS, 0UL);
    error = errno;
    *logged = record(operation, IHK_OS_QUERY_STATUS, result, error) == 0;
    return result;
}

int main(int argc, char **argv)
{
    unsigned int minor = 0;
    const unsigned char *cursor;
    char path[64];
    int fd, before, after, shutdown_rc, shutdown_error, logged, after_logged, result = 1;
    if (argc != 2 || !argv[1][0])
        goto usage;
    /* Decimal minor only: no signs, whitespace, suffixes or path traversal. */
    for (cursor = (const unsigned char *)argv[1]; *cursor; cursor++) {
        unsigned int digit;
        if (*cursor < '0' || *cursor > '9')
            goto usage;
        digit = *cursor - '0';
        if (minor > ((unsigned int)INT_MAX - digit) / 10)
            goto usage;
        minor = minor * 10 + digit;
    }
    if (snprintf(path, sizeof(path), "/dev/mcos%u", minor) >= (int)sizeof(path))
        goto usage;
    errno = 0;
    fd = LIFECYCLE_OPEN(path, O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    {
        int error = errno;
        if (record("open", 0, fd, error) != 0) {
            if (fd >= 0)
                (void)LIFECYCLE_CLOSE(fd);
            return 1;
        }
    }
    if (fd < 0)
        return 1;
    before = query(fd, "status_before", &logged);
    if (!logged || before < IHK_OS_STATUS_NOT_BOOTED || before >= IHK_OS_STATUS_COUNT)
        goto close_out;
    errno = 0;
    shutdown_rc = LIFECYCLE_IOCTL(fd, IHK_OS_SHUTDOWN, 0UL);
    shutdown_error = errno;
    logged = record("shutdown", IHK_OS_SHUTDOWN, shutdown_rc, shutdown_error) == 0;
    /* Observe post-effect failure state too; never retry a failed shutdown. */
    after = query(fd, "status_after", &after_logged);
    if (!logged || !after_logged || shutdown_rc != 0 || after != IHK_OS_STATUS_NOT_BOOTED) {
        result = 1;
        goto close_out;
    }
    result = 0;
close_out:
    errno = 0;
    {
        int close_rc = LIFECYCLE_CLOSE(fd);
        int error = errno;
        if (record("close", 0, close_rc, error) != 0 || close_rc != 0)
            result = 1;
    }
    if (result == 0) {
        /* An already NotBooted OS is an idempotent success, not a teardown. */
        if (printf("{\"result\":\"PASS\",\"transition_observed\":%s,"
                   "\"resource_restoration_verified\":false}\n",
                   before == IHK_OS_STATUS_NOT_BOOTED ? "false" : "true") < 0 ||
            fflush(stdout) != 0)
            return 1;
    }
    return result;
usage:
    fprintf(stderr, "usage: native-diagnostic-lifecycle-probe DECIMAL_OS_MINOR\n");
    return 2;
}
