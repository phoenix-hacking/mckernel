/* SPDX-License-Identifier: GPL-2.0-only */
/* Verification artifact transport. Reads only one quiescent selected tree. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define MAX_BYTES UINT64_C(16777216)
#define MAX_ENTRIES 256u
#define MAX_PATH 1024u
#define MAX_DEPTH 64u
#define META_BYTES 64u
static int channel = -1;
static uint64_t deadline, file_bytes, files, directories, entries;
static dev_t root_device;
static unsigned char nonce[16];
static bool boundary;
static const char *failure = "none";
static int failure_errno;

static uint64_t now_ns(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) < 0) _exit(124);
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}
static bool fail(const char *reason, int error)
{
    if (!strcmp(failure, "none")) { failure = reason; failure_errno = error; }
    return false;
}
static void put32(unsigned char *p, uint32_t v)
{
    for (unsigned i = 0; i < 4; ++i) p[i] = (unsigned char)(v >> (8 * i));
}
static void put64(unsigned char *p, uint64_t v)
{
    for (unsigned i = 0; i < 8; ++i) p[i] = (unsigned char)(v >> (8 * i));
}
static uint64_t get64(const unsigned char *p)
{
    uint64_t v = 0;
    for (unsigned i = 0; i < 8; ++i) v |= (uint64_t)p[i] << (8 * i);
    return v;
}
static bool transfer(void *buffer, size_t bytes, bool writing)
{
    unsigned char *p = buffer;
    while (bytes) {
        if (now_ns() >= deadline) return fail("channel-deadline", ETIMEDOUT);
        ssize_t n = writing ? write(channel, p, bytes) : read(channel, p, bytes);
        if (n > 0) { p += n; bytes -= (size_t)n; continue; }
        if (!n && !writing) return fail("channel-eof", EPIPE);
        if (n < 0 && errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK)
            return fail("channel-io", errno);
        struct pollfd fd = {.fd = channel, .events = writing ? POLLOUT : POLLIN};
        int ready = poll(&fd, 1, 100);
        if (ready < 0 && errno != EINTR) return fail("channel-poll", errno);
        if (fd.revents & (POLLERR | POLLNVAL)) return fail("channel-poll-error", EIO);
        if ((fd.revents & POLLHUP) && !(fd.revents & (POLLIN | POLLOUT)))
            return fail("channel-hangup", EPIPE);
    }
    return true;
}
static bool send_bytes(const void *buffer, size_t bytes)
{
    return transfer((void *)buffer, bytes, true);
}
static bool name_ok(const char *name)
{
    size_t n = strlen(name);
    if (!n || !strcmp(name, ".") || !strcmp(name, "..")) return false;
    for (size_t i = 0; i < n; ++i)
        if ((unsigned char)name[i] < 32 || (unsigned char)name[i] > 126 ||
            name[i] == '/' || name[i] == '\\') return false;
    return true;
}
static bool stable(const struct stat *a, const struct stat *b)
{
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino && a->st_mode == b->st_mode &&
        a->st_nlink == b->st_nlink && a->st_size == b->st_size &&
        a->st_mtim.tv_sec == b->st_mtim.tv_sec && a->st_mtim.tv_nsec == b->st_mtim.tv_nsec &&
        a->st_ctim.tv_sec == b->st_ctim.tv_sec && a->st_ctim.tv_nsec == b->st_ctim.tv_nsec;
}
static void metadata(unsigned char out[META_BYTES], const struct stat *s)
{
    const uint64_t values[8] = {(uint64_t)s->st_mode, (uint64_t)s->st_dev,
        (uint64_t)s->st_ino, (uint64_t)s->st_size, (uint64_t)s->st_mtim.tv_sec,
        (uint64_t)s->st_mtim.tv_nsec, (uint64_t)s->st_ctim.tv_sec, (uint64_t)s->st_ctim.tv_nsec};
    for (unsigned i = 0; i < 8; ++i) put64(out + i * 8, values[i]);
}
static bool header(uint32_t kind, const char *path, uint64_t payload)
{
    unsigned char bytes[16];
    size_t n = strlen(path);
    if (n > MAX_PATH) return fail("path-limit", ENAMETOOLONG);
    put32(bytes, kind); put32(bytes + 4, (uint32_t)n); put64(bytes + 8, payload);
    boundary = false;
    return send_bytes(bytes, sizeof bytes) && send_bytes(path, n);
}
static bool object_header(uint32_t kind, const char *path, const struct stat *s, uint64_t content)
{
    unsigned char meta[META_BYTES]; metadata(meta, s);
    return header(kind, path, META_BYTES + content) && send_bytes(meta, sizeof meta);
}
static bool send_file(int parent, const char *name, const char *path, const struct stat *expected)
{
    int fd = openat(parent, name, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return fail("file-open", errno);
    bool ok = false;
    struct stat before, after;
    if (fstat(fd, &before) < 0) { fail("file-stat", errno); goto done; }
    if (!S_ISREG(before.st_mode) || before.st_nlink != 1 || before.st_dev != root_device ||
        !stable(expected, &before)) { fail("unsafe-or-changed-file", ESTALE); goto done; }
    if (before.st_size < 0 || (uint64_t)before.st_size > MAX_BYTES - file_bytes) {
        fail("content-limit", EFBIG); goto done;
    }
    if (!object_header(2, path, &before, (uint64_t)before.st_size)) goto done;
    uint64_t left = (uint64_t)before.st_size;
    unsigned char buffer[32768];
    while (left) {
        if (now_ns() >= deadline) { fail("file-deadline", ETIMEDOUT); goto done; }
        size_t want = left < sizeof buffer ? (size_t)left : sizeof buffer;
        ssize_t n = read(fd, buffer, want);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { fail("file-short-or-error", n < 0 ? errno : EIO); goto done; }
        if (!send_bytes(buffer, (size_t)n)) goto done;
        left -= (uint64_t)n;
    }
    boundary = true;
    if (fstat(fd, &after) < 0) { fail("file-restat", errno); goto done; }
    if (!stable(&before, &after)) { fail("file-changed", ESTALE); goto done; }
    file_bytes += (uint64_t)before.st_size; ++files;
    ok = true;
done:
    close(fd);
    return ok;
}
static bool walk(int fd, const char *prefix, unsigned depth, const struct stat *expected)
{
    if (depth > MAX_DEPTH) { close(fd); return fail("depth-limit", EOVERFLOW); }
    struct stat before, after;
    if (fstat(fd, &before) < 0) { close(fd); return fail("directory-stat", errno); }
    if (!stable(expected, &before)) { close(fd); return fail("directory-changed-before-walk", ESTALE); }
    DIR *dir = fdopendir(fd);
    if (!dir) { close(fd); return fail("directory-open", errno); }
    bool ok = false;
    for (;;) {
        if (now_ns() >= deadline) { fail("walk-deadline", ETIMEDOUT); goto done; }
        errno = 0;
        struct dirent *entry = readdir(dir);
        if (!entry) { if (errno) { fail("directory-read", errno); goto done; } break; }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        if (depth >= MAX_DEPTH) { fail("depth-limit", EOVERFLOW); goto done; }
        if (++entries > MAX_ENTRIES) { fail("entry-limit", EFBIG); goto done; }
        if (!name_ok(entry->d_name)) { fail("unsafe-name", EINVAL); goto done; }
        char path[MAX_PATH + 1];
        int n = snprintf(path, sizeof path, "%s%s%s", prefix, *prefix ? "/" : "", entry->d_name);
        if (n < 0 || (size_t)n >= sizeof path) { fail("path-limit", ENAMETOOLONG); goto done; }
        struct stat expected;
        if (fstatat(fd, entry->d_name, &expected, AT_SYMLINK_NOFOLLOW) < 0) { fail("entry-stat", errno); goto done; }
        if (expected.st_dev != root_device) { fail("mount-boundary", EXDEV); goto done; }
        if (S_ISREG(expected.st_mode)) {
            if (!send_file(fd, entry->d_name, path, &expected)) goto done;
        } else if (S_ISDIR(expected.st_mode)) {
            int child = openat(fd, entry->d_name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
            struct stat current;
            if (child < 0) { fail("child-directory-open", errno); goto done; }
            if (fstat(child, &current) < 0 || !stable(&expected, &current)) {
                close(child); fail("child-directory-changed", ESTALE); goto done;
            }
            if (!object_header(1, path, &current, 0)) { close(child); goto done; }
            boundary = true; ++directories;
            if (!walk(child, path, depth + 1, &current)) goto done;
        } else { fail("unsafe-entry-type", EINVAL); goto done; }
    }
    if (fstat(fd, &after) < 0) { fail("directory-restat", errno); goto done; }
    if (!stable(&before, &after)) { fail("directory-changed", ESTALE); goto done; }
    ok = true;
done:
    closedir(dir);
    return ok;
}
static int open_root(const char *path)
{
    size_t n = strlen(path);
    if (n < 2 || n > MAX_PATH || path[0] != '/' || path[n - 1] == '/') { errno = EINVAL; return -1; }
    char copy[MAX_PATH + 1]; memcpy(copy, path + 1, n);
    int fd = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) return -1;
    char *next = copy;
    while (next) {
        char *name = next, *slash = strchr(next, '/');
        if (slash) { *slash = 0; next = slash + 1; } else next = NULL;
        if (!name_ok(name)) { close(fd); errno = EINVAL; return -1; }
        int child = openat(fd, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
        if (child < 0) { int error = errno; close(fd); errno = error; return -1; }
        close(fd); fd = child;
    }
    return fd;
}
static bool parse_nonce(const char *s)
{
    if (strlen(s) != 32) return false;
    for (unsigned i = 0; i < 16; ++i) {
        unsigned value = 0;
        for (unsigned j = 0; j < 2; ++j) {
            unsigned char c = (unsigned char)s[2 * i + j];
            if (c >= '0' && c <= '9') value = value * 16 + c - '0';
            else if (c >= 'a' && c <= 'f') value = value * 16 + c - 'a' + 10;
            else return false;
        }
        nonce[i] = (unsigned char)value;
    }
    return true;
}
static bool acknowledgement(void)
{
    unsigned char ack[112];
    if (!transfer(ack, sizeof ack, false)) return false;
    if (now_ns() >= deadline) return fail("late-host-ack", ETIMEDOUT);
    if (memcmp(ack, "STAA0001", 8) || memcmp(ack + 8, nonce, 16) ||
        get64(ack + 24) != 0 || get64(ack + 32) != file_bytes || get64(ack + 40) != entries)
        return fail("invalid-or-failed-host-ack", EPROTO);
    char raw[65], manifest[65];
    for (unsigned i = 0; i < 32; ++i) {
        snprintf(raw + 2 * i, 3, "%02x", ack[48 + i]);
        snprintf(manifest + 2 * i, 3, "%02x", ack[80 + i]);
    }
    dprintf(2, "STAF EXPORT_ACK version=1 entries=%" PRIu64 " bytes=%" PRIu64 " wire_sha256=%s manifest_sha256=%s\n",
            entries, file_bytes, raw, manifest);
    return true;
}
int main(int argc, char **argv)
{
    if (argc != 4 || !parse_nonce(argv[3])) {
        dprintf(2, "usage: exporter ABSOLUTE_ATTEMPT_ROOT VIRTIO_PORT NONCE32\n"); return 2;
    }
    deadline = now_ns() + UINT64_C(60000000000);
    signal(SIGPIPE, SIG_IGN);
    int root = open_root(argv[1]);
    if (root < 0) { fail("selected-root-open", errno); goto failed; }
    struct stat root_stat, device_stat;
    if (fstat(root, &root_stat) < 0) { close(root); fail("selected-root-stat", errno); goto failed; }
    root_device = root_stat.st_dev;
    channel = open(argv[2], O_RDWR | O_NONBLOCK | O_NOCTTY | O_CLOEXEC);
    if (channel < 0 || fstat(channel, &device_stat) < 0 || !S_ISCHR(device_stat.st_mode)) {
        close(root); fail("virtio-character-device", channel < 0 ? errno : ENODEV); goto failed;
    }
    unsigned char start[48] = {0};
    memcpy(start, "STAF0001", 8); put32(start + 8, 1); put32(start + 12, 48);
    memcpy(start + 16, nonce, 16); put32(start + 32, MAX_ENTRIES);
    put32(start + 36, (uint32_t)MAX_BYTES); put32(start + 40, MAX_PATH);
    if (!send_bytes(start, sizeof start) || !object_header(4, argv[1], &root_stat, 0)) {
        close(root); goto failed;
    }
    boundary = true;
    if (!walk(root, "", 0, &root_stat)) goto failed;
    unsigned char end[32];
    put64(end, entries); put64(end + 8, directories); put64(end + 16, files); put64(end + 24, file_bytes);
    if (!header(3, "", sizeof end) || !send_bytes(end, sizeof end)) goto failed;
    boundary = true;
    if (!acknowledgement()) goto failed;
    close(channel);
    return 0;
failed:
    if (channel >= 0 && boundary && now_ns() < deadline) {
        char message[256];
        int n = snprintf(message, sizeof message, "%s errno=%d", failure, failure_errno);
        if (n > 0 && (size_t)n < sizeof message && header(127, "", (uint64_t)n))
            (void)send_bytes(message, (size_t)n);
    }
    dprintf(2, "STAF EXPORT_FAIL reason=%s errno=%d entries=%" PRIu64 " bytes=%" PRIu64 " poweroff_authorized=false\n",
            failure, failure_errno, entries, file_bytes);
    if (channel >= 0) close(channel);
    return 1;
}
