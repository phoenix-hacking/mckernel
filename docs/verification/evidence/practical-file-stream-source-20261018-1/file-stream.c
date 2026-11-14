#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

/* copy-check INPUT NEW_OUTPUT: binary-safe streaming copy with FNV-1a64,
 * close/reopen verification, and removal of an incomplete owned destination.
 * Existing destinations are never replaced. The input must remain stable.
 * FNV is an integrity checksum, not a cryptographic authentication mechanism.
 */
static int write_all(int fd, const unsigned char *data, size_t length)
{
    while (length) {
        ssize_t n = write(fd, data, length);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { if (n == 0) errno = EIO; return -1; }
        data += (size_t)n;
        length -= (size_t)n;
    }
    return 0;
}

static int problem(const char *operation, int error, int result)
{
    const char *name = error == ENOENT ? "ENOENT" : error == EEXIST ? "EEXIST" :
                       error == EISDIR ? "EISDIR" : "ERROR";
    (void)fprintf(stderr, "file-stream: %s failed: %s\n", operation, name);
    return result;
}

/* No close retry on EINTR: Linux may already have released the descriptor.
 * A failed close makes the whole operation fail. Ownership is cleared first.
 */
static int close_owned(int *fd)
{
    if (*fd < 0) return 0;
    int owned = *fd;
    *fd = -1;
    return close(owned);
}

static int stream(int fd, int destination, uint64_t *length, uint64_t *hash)
{
    unsigned char buffer[4096];
    *length = 0;
    *hash = UINT64_C(14695981039346656037);
    for (;;) {
        ssize_t n = read(fd, buffer, sizeof(buffer));
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) return 1;
        if (n == 0) return 0;
        if (*length > UINT64_MAX - (uint64_t)n) { errno = EOVERFLOW; return 3; }
        if (destination >= 0 && write_all(destination, buffer, (size_t)n)) return 2;
        *length += (uint64_t)n;
        for (ssize_t i = 0; i < n; ++i) {
            *hash ^= buffer[i];
            *hash *= UINT64_C(1099511628211);
        }
    }
}

int main(int argc, char **argv)
{
    if (argc != 4 || strcmp(argv[1], "copy-check")) {
        (void)fputs("usage: file-stream copy-check INPUT NEW_OUTPUT\n", stderr);
        return 64;
    }
    int input = -1, output = -1, verify = -1, created = 0, result = 0;
    uint64_t length = 0, hash = 0, actual_length = 0, actual_hash = 0;
    input = open(argv[2], O_RDONLY);
    if (input < 0) return problem("input open", errno, 65);
    output = open(argv[3], O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (output < 0) { result = problem("output open", errno, 66); goto done; }
    created = 1;
    int streamed = stream(input, output, &length, &hash);
    if (streamed) {
        result = problem(streamed == 2 ? "copy write" : "copy read", errno, 67);
        goto done;
    }
    if (close_owned(&output)) { result = problem("output close", errno, 68); goto done; }
    verify = open(argv[3], O_RDONLY);
    if (verify < 0) { result = problem("verify open", errno, 69); goto done; }
    if (stream(verify, -1, &actual_length, &actual_hash)) {
        result = problem("verify read", errno, 70); goto done;
    }
    if (length != actual_length || hash != actual_hash) {
        result = problem("verify checksum", EIO, 71); goto done;
    }
done:
    if (close_owned(&input)) result = problem("input close", errno, 72);
    if (close_owned(&output)) result = problem("output close", errno, 72);
    if (close_owned(&verify)) result = problem("verify close", errno, 72);
    if (!result) {
        char summary[128];
        int size = snprintf(summary, sizeof(summary), "file-stream: bytes=%" PRIu64
                            " fnv1a64=%016" PRIx64 " verified\n", length, hash);
        if (size < 0 || (size_t)size >= sizeof(summary))
            result = problem("summary format", EOVERFLOW, 73);
        else if (write_all(STDOUT_FILENO, (const unsigned char *)summary, (size_t)size))
            result = problem("summary write", errno, 73);
    }
    if (result && created && unlink(argv[3]))
        result = problem("cleanup unlink", errno, 74);
    return result;
}
