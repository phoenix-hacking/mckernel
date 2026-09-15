/* SPDX-License-Identifier: GPL-2.0-only */
/* Ordinary Linux infrastructure only. No native/case oracle or backend release. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "../request.h"
#include "sha256.h"
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <inttypes.h>
#include <limits.h>
#include <linux/memfd.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/xattr.h>
#include <time.h>
#include <unistd.h>

#define NS UINT64_C(1000000000)
#define EXEC_LIMIT UINT64_C(1048576)
#define MANIFEST_LIMIT UINT64_C(4194304)
#define STREAM_LIMIT UINT64_C(65536)
#define OWNED_LIMIT 512U
#define SETUP_WORDS 48U
#define SETUP_PACKET (SETUP_WORDS * 8U)

struct sink {
    const char *name;
    int fd;
    int creation_errno, fd_errno;
    uint64_t limit, seen, stored;
    bool created, truncated, io_error;
    struct ac_sha256 hash;
};
struct stream { int fd; bool eof; struct sink sink; };
struct source {
    bool opened, stat_observed, after_stat_observed, stable, verified;
    struct stat before, after, backing;
    int fd, seals;
    struct sink artifact;
};
struct process {
    pid_t pid, ppid, pgid, sid;
    uint64_t ticks;
    bool recorded, reaped, kill_sent;
    int raw_wait;
};
static struct acrq_request request;
static unsigned char request_bytes[65537], setup_bytes[2 * SETUP_PACKET];
static struct sink request_artifact, manifest_artifact, argv_artifact, env_artifact, events;
static struct stream streams[3];
static struct source executable, input;
static struct process leader, owned[OWNED_LIMIT];
static unsigned owned_count;
static uint64_t owned_omitted;
static int attempt_fd = -1, cwd_fd = -1;
static struct stat cwd_identity, pipe_identity[2], devnull_identity;
static const char *status = "PREPARATION_ERROR", *failure = "none";
static int failure_errno;
static uint64_t first_failure_ns, preparation_start, preparation_deadline;
static uint64_t process_start, process_deadline, completion_observed;
static uint64_t cleanup_start, cleanup_deadline, cleanup_finished;
static bool child_created, leader_waitable, cleanup_complete, group_pinned;
static bool request_valid, observed_exec_link_complete;
static bool setup_ready, setup_error, setup_validated, exec_backing_observed;
static uint64_t setup_words[SETUP_WORDS], observed_exec_ns, observed_exec_link_ns;
static struct stat observed_exec;
static char observed_exec_link[256];
static volatile sig_atomic_t interrupted;

static uint64_t now_ns(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0 || t.tv_sec < 0 || (uint64_t)t.tv_sec > UINT64_MAX / NS) _exit(124);
    return (uint64_t)t.tv_sec * NS + (uint64_t)t.tv_nsec;
}

static bool fail(const char *new_status, const char *reason, int error)
{
    if (strcmp(failure, "none") == 0) {
        status = new_status; failure = reason; failure_errno = error; first_failure_ns = now_ns();
    }
    return false;
}

static bool preparing(void)
{
    if (interrupted) return fail("INTERRUPTED", "collector-interrupted", EINTR);
    if (now_ns() >= preparation_deadline) return fail("PREPARATION_ERROR", "preparation-deadline", ETIMEDOUT);
    return true;
}

static int high_fd(int fd)
{
    if (fd < 0 || fd >= 3) return fd;
    int copy = fcntl(fd, F_DUPFD_CLOEXEC, 3), saved = errno;
    close(fd); errno = saved;
    return copy;
}

/* Walk a literal absolute path with a pinned fd for every directory component.
 * The final component may be opened with caller-supplied flags; no symlinks. */
static int open_path(const char *path, int flags)
{
    if (path == NULL || path[0] != '/' || strlen(path) > 4095) { errno = EINVAL; return -1; }
    int parent = high_fd(open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    if (parent < 0) return -1;
    if (path[1] == 0) {
        if (!(flags & O_DIRECTORY)) { close(parent); errno = EISDIR; return -1; }
        return parent;
    }
    const char *p = path + 1;
    while (*p) {
        const char *slash = strchr(p, '/');
        size_t n = slash ? (size_t)(slash - p) : strlen(p);
        if (n == 0 || n > NAME_MAX || (n == 1 && p[0] == '.') || (n == 2 && p[0] == '.' && p[1] == '.')) {
            close(parent); errno = EINVAL; return -1;
        }
        char name[NAME_MAX + 1]; memcpy(name, p, n); name[n] = 0;
        int fd = high_fd(openat(parent, name, (slash ? O_RDONLY | O_DIRECTORY : flags) | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK));
        int saved = errno; close(parent); errno = saved;
        if (fd < 0) return -1;
        if (!slash) return fd;
        parent = fd; p = slash + 1;
        if (*p == 0) { close(parent); errno = EINVAL; return -1; }
    }
    close(parent); errno = EINVAL; return -1;
}

static bool make_attempt(const char *path)
{
    if (!path || path[0] != '/' || strlen(path) > 4095) return false;
    char copy[4096]; strcpy(copy, path);
    char *slash = strrchr(copy, '/');
    if (!slash || slash[1] == 0 || !strcmp(slash + 1, ".") || !strcmp(slash + 1, "..")) return false;
    const char *name = slash + 1;
    char leaf[NAME_MAX + 1];
    if (strlen(name) > NAME_MAX) return false;
    strcpy(leaf, name); *slash = 0;
    int parent = open_path(slash == copy ? "/" : copy, O_RDONLY | O_DIRECTORY);
    if (parent < 0) return false;
    if (mkdirat(parent, leaf, 0700) != 0) { close(parent); return false; }
    attempt_fd = high_fd(openat(parent, leaf, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    bool ok = attempt_fd >= 0 && fsync(parent) == 0;
    close(parent);
    return ok;
}

static bool new_sink(struct sink *s, const char *name, uint64_t limit)
{
    memset(s, 0, sizeof *s); s->fd = -1; s->name = name; s->limit = limit;
    ac_sha256_init(&s->hash);
    int opened = openat(attempt_fd, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (opened < 0) {
        s->creation_errno = errno;
        return fail("PREPARATION_ERROR", "artifact-create", s->creation_errno);
    }
    s->created = true; /* Record actual creation before optional fd relocation. */
    s->fd = high_fd(opened);
    if (s->fd < 0) {
        s->fd_errno = errno; s->io_error = true;
        return fail("PREPARATION_ERROR", "artifact-fd-relocation", s->fd_errno);
    }
    return true;
}

static bool retain(struct sink *s, const void *raw, size_t length)
{
    const unsigned char *bytes = raw;
    if (s->seen > UINT64_MAX - length) { s->truncated = true; return fail("COLLECTOR_ERROR", "byte-counter-overflow", EOVERFLOW); }
    s->seen += length;
    size_t keep = length;
    if (keep > s->limit - s->stored) keep = (size_t)(s->limit - s->stored);
    if (keep != length) s->truncated = true;
    size_t done = 0;
    while (done < keep) {
        ssize_t n = write(s->fd, bytes + done, keep - done);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { s->io_error = true; return fail("COLLECTOR_ERROR", "artifact-write", n < 0 ? errno : EIO); }
        if (!ac_sha256_update(&s->hash, bytes + done, (size_t)n)) { s->io_error = true; return fail("COLLECTOR_ERROR", "artifact-hash-bound", EOVERFLOW); }
        done += (size_t)n; s->stored += (uint64_t)n;
    }
    return !s->truncated;
}

static void event(const char *format, ...)
{
    if (events.fd < 0) return;
    char body[768], line[896];
    va_list args; va_start(args, format);
    int n = vsnprintf(body, sizeof body, format, args); va_end(args);
    if (n < 0 || (size_t)n >= sizeof body) { fail("COLLECTOR_ERROR", "event-format-bound", EOVERFLOW); return; }
    n = snprintf(line, sizeof line, "{\"monotonic_ns\":%" PRIu64 ",%s}\n", now_ns(), body);
    if (n < 0 || (size_t)n >= sizeof line || !retain(&events, line, (size_t)n))
        fail("COLLECTOR_ERROR", "event-retention-bound", EOVERFLOW);
}

static bool stable(const struct stat *a, const struct stat *b)
{
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino && a->st_mode == b->st_mode &&
        a->st_uid == b->st_uid && a->st_gid == b->st_gid && a->st_size == b->st_size &&
        a->st_nlink == b->st_nlink && a->st_mtim.tv_sec == b->st_mtim.tv_sec && a->st_mtim.tv_nsec == b->st_mtim.tv_nsec &&
        a->st_ctim.tv_sec == b->st_ctim.tv_sec && a->st_ctim.tv_nsec == b->st_ctim.tv_nsec;
}

static bool raw_file(const char *path, struct sink *sink, unsigned char *copy, size_t copy_cap,
                     const unsigned char *expected_hash, uint64_t *size_out)
{
    int fd = open_path(path, O_RDONLY);
    if (fd < 0) return fail("PREPARATION_ERROR", "input-open", errno);
    struct stat before, after;
    bool ok = fstat(fd, &before) == 0 && S_ISREG(before.st_mode) && before.st_size >= 0;
    if (!ok) { close(fd); return fail("PREPARATION_ERROR", "input-not-regular", EINVAL); }
    unsigned char buffer[32768];
    while (preparing()) {
        size_t want = sizeof buffer;
        uint64_t room = sink->limit + 1 - sink->seen;
        if (want > room) want = (size_t)room;
        if (!want) { ok = fail("PREPARATION_ERROR", "input-bound", EFBIG); break; }
        ssize_t n = read(fd, buffer, want);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { ok = fail("PREPARATION_ERROR", "input-read", errno); break; }
        if (!n) break;
        uint64_t offset = sink->seen;
        if (copy && offset < copy_cap) {
            size_t keep = (size_t)n;
            if (keep > copy_cap - (size_t)offset) keep = copy_cap - (size_t)offset;
            memcpy(copy + offset, buffer, keep);
        }
        if (!retain(sink, buffer, (size_t)n)) { ok = fail("PREPARATION_ERROR", "input-bound", EFBIG); break; }
    }
    if (fstat(fd, &after) != 0 || !stable(&before, &after)) ok = fail("PREPARATION_ERROR", "input-changed", ESTALE);
    close(fd);
    if (!preparing()) ok = false;
    if (sink->seen != (uint64_t)before.st_size) ok = fail("PREPARATION_ERROR", "input-size-incomplete", EIO);
    unsigned char digest[32]; ac_sha256_final(&sink->hash, digest);
    if (expected_hash && memcmp(digest, expected_hash, 32)) ok = fail("PREPARATION_ERROR", "manifest-sha256", EBADMSG);
    if (size_out) *size_out = sink->stored;
    return ok && !strcmp(failure, "none");
}

static bool write_fd(int fd, const void *raw, size_t n)
{
    const unsigned char *p = raw;
    while (n) {
        ssize_t done = write(fd, p, n);
        if (done < 0 && errno == EINTR) continue;
        if (done <= 0) return false;
        p += done; n -= (size_t)done;
    }
    return true;
}

static bool seal_source(struct source *s, const char *path, const char *name,
                        uint64_t expected_size, const unsigned char expected_hash[32], bool is_executable)
{
    uint64_t limit = is_executable ? EXEC_LIMIT : STREAM_LIMIT;
    s->fd = -1;
    if (!new_sink(&s->artifact, name, limit)) return false;
    int source = open_path(path, O_RDONLY);
    if (source < 0) return fail("PREPARATION_ERROR", "source-open", errno);
    s->opened = true;
    if (fstat(source, &s->before) != 0) {
        int saved = errno; close(source); return fail("PREPARATION_ERROR", "source-stat", saved);
    }
    s->stat_observed = true;
    if (!S_ISREG(s->before.st_mode) || s->before.st_size < 0) {
        close(source); return fail("PREPARATION_ERROR", "source-not-regular", EINVAL);
    }
    if (is_executable && (!(s->before.st_mode & 0111) || (s->before.st_mode & (S_ISUID | S_ISGID)))) {
        close(source); return fail("BLOCKED", "unsupported-executable-mode", EACCES);
    }
    if (is_executable) {
        unsigned char capability[256]; errno = 0;
        ssize_t n = fgetxattr(source, "security.capability", capability, sizeof capability);
        if (n >= 0 || (errno != ENODATA && errno != EOPNOTSUPP)) {
            close(source); return fail("BLOCKED", "file-capability-unverified-or-present", n >= 0 ? EPERM : errno);
        }
    }
    /* Original memfd ABI is supported by the actual container host kernel.
     * Do not opt out of a newer kernel's default no-exec policy: fchmod/seals
     * below must succeed, otherwise this explicit infrastructure profile blocks. */
    int mem = high_fd((int)syscall(SYS_memfd_create, is_executable ? "ac-linux-image" : "ac-linux-stdin",
                                  MFD_CLOEXEC | MFD_ALLOW_SEALING));
    if (mem < 0) { int saved = errno; close(source); return fail("BLOCKED", "memfd-exec-unavailable", saved); }
    unsigned char buffer[32768], first[64] = {0};
    while (preparing()) {
        size_t want = sizeof buffer;
        uint64_t room = limit + 1 - s->artifact.seen;
        if (want > room) want = (size_t)room;
        if (!want) { fail("PREPARATION_ERROR", "source-size-bound", EFBIG); break; }
        ssize_t n = read(source, buffer, want);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { fail("PREPARATION_ERROR", "source-read", errno); break; }
        if (!n) break;
        if (s->artifact.seen < sizeof first) {
            size_t keep = (size_t)n;
            if (keep > sizeof first - (size_t)s->artifact.seen) keep = sizeof first - (size_t)s->artifact.seen;
            memcpy(first + s->artifact.seen, buffer, keep);
        }
        if (!retain(&s->artifact, buffer, (size_t)n) || !write_fd(mem, buffer, (size_t)n)) {
            fail("PREPARATION_ERROR", "source-copy", s->artifact.truncated ? EFBIG : errno); break;
        }
    }
    if (fstat(source, &s->after) != 0) fail("PREPARATION_ERROR", "source-after-stat", errno);
    else {
        s->after_stat_observed = true;
        if (!stable(&s->before, &s->after)) fail("PREPARATION_ERROR", "source-changed", ESTALE);
        else s->stable = true;
    }
    close(source);
    unsigned char digest[32]; ac_sha256_final(&s->artifact.hash, digest);
    if (s->artifact.seen != expected_size || s->artifact.seen != (uint64_t)s->before.st_size || memcmp(digest, expected_hash, 32))
        fail("PREPARATION_ERROR", "source-size-or-sha256", EBADMSG);
    if (is_executable && (expected_size < 64 || memcmp(first, "\177ELF", 4) || first[4] != 2 || first[5] != 1 || first[6] != 1 ||
                          (first[16] != 2 && first[16] != 3) || first[17] != 0 || first[18] != 62 || first[19] != 0))
        fail("BLOCKED", "unsupported-executable-format", ENOEXEC);
    if (!preparing() || strcmp(failure, "none")) { close(mem); return false; }
    const int seals = F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE;
    if (fchmod(mem, 0500) != 0 || fcntl(mem, F_ADD_SEALS, seals) != 0) {
        int saved = errno; close(mem); return fail("BLOCKED", "immutable-memfd-unavailable", saved);
    }
    s->seals = fcntl(mem, F_GET_SEALS);
    if (s->seals < 0 || s->seals != seals) {
        int saved = s->seals < 0 ? errno : EPROTO;
        close(mem); return fail("BLOCKED", "immutable-memfd-seals-mismatch", saved);
    }
    char fdpath[64]; snprintf(fdpath, sizeof fdpath, "/proc/self/fd/%d", mem);
    s->fd = high_fd(open(fdpath, O_RDONLY | O_CLOEXEC));
    struct stat original;
    if (s->fd < 0 || fstat(mem, &original) != 0 || fstat(s->fd, &s->backing) != 0) {
        int saved = errno; close(mem); return fail("PREPARATION_ERROR", "sealed-descriptor-open-or-stat", saved);
    }
    int actual_seals = fcntl(s->fd, F_GET_SEALS);
    if (actual_seals < 0 || lseek(s->fd, 0, SEEK_SET) < 0) {
        int saved = errno; close(mem); return fail("PREPARATION_ERROR", "sealed-descriptor-seals-or-offset", saved);
    }
    bool ok = original.st_dev == s->backing.st_dev && original.st_ino == s->backing.st_ino &&
              S_ISREG(s->backing.st_mode) && (s->backing.st_mode & 07777) == 0500 &&
              s->backing.st_size >= 0 && (uint64_t)s->backing.st_size == expected_size &&
              actual_seals == seals;
    close(mem);
    if (!ok) return fail("PREPARATION_ERROR", "sealed-descriptor-identity", ESTALE);
    s->verified = true;
    return true;
}

static void caught(int number) { if (!interrupted) interrupted = number; }

static const char *literal(struct acrq_slice slice) { return request.storage + slice.offset; }

static bool proc_identity(pid_t pid, struct process *p)
{
    char path[80], bytes[4096];
    snprintf(path, sizeof path, "/proc/%ld/stat", (long)pid);
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
    if (fd < 0) return false;
    ssize_t n;
    do { n = read(fd, bytes, sizeof bytes - 1); } while (n < 0 && errno == EINTR);
    close(fd);
    if (n <= 0 || n == (ssize_t)sizeof bytes - 1) return false;
    bytes[n] = 0;
    char *end = strrchr(bytes, ')'), *save = NULL;
    if (!end || end[1] != ' ') return false;
    struct process value = { .pid = pid };
    unsigned field = 3;
    for (char *word = strtok_r(end + 2, " \n", &save); word; word = strtok_r(NULL, " \n", &save), ++field) {
        if (field == 4 || field == 5 || field == 6 || field == 22) {
            char *tail; errno = 0;
            unsigned long long v = strtoull(word, &tail, 10);
            if (errno || !*word || *tail || word[0] == '-' || (field != 22 && v > INT_MAX)) return false;
            if (field == 4) value.ppid = (pid_t)v;
            if (field == 5) value.pgid = (pid_t)v;
            if (field == 6) value.sid = (pid_t)v;
            if (field == 22) { value.ticks = (uint64_t)v; value.recorded = true; *p = value; return true; }
        }
    }
    return false;
}

/* Private child pipe, not an execution-provenance protocol. Each u64 is LE. */
static void setup_packet(int fd, uint64_t words[SETUP_WORDS])
{
    unsigned char bytes[SETUP_PACKET];
    for (size_t i = 0; i < SETUP_WORDS; ++i)
        for (unsigned j = 0; j < 8; ++j) bytes[i * 8 + j] = (unsigned char)(words[i] >> (8 * j));
    if (!write_fd(fd, bytes, sizeof bytes)) _exit(125);
}

static _Noreturn void child_error(int fd, unsigned stage, int error)
{
    uint64_t words[SETUP_WORDS] = { UINT64_C(0x314c4341), 1, 2, stage, (uint64_t)error };
    setup_packet(fd, words); _exit(stage == 2 ? 126 : 125);
}

#ifndef COLLECTOR_CLOSE_RANGE_CALL
#define COLLECTOR_CLOSE_RANGE_CALL(first, last, flags) syscall(SYS_close_range, first, last, flags)
#endif
#ifndef COLLECTOR_GETRLIMIT_CALL
#define COLLECTOR_GETRLIMIT_CALL(resource, limit) getrlimit(resource, limit)
#endif
#ifndef COLLECTOR_CLOSE_CALL
#define COLLECTOR_CLOSE_CALL(fd) close(fd)
#endif

static bool close_except(int a, int b)
{
    if (a < 3 || b < 3 || a == b) { errno = EINVAL; return false; }
    unsigned low = (unsigned)(a < b ? a : b), high = (unsigned)(a < b ? b : a);
    int saved_error = 0;
    if (low > 3 && COLLECTOR_CLOSE_RANGE_CALL(3U, low - 1U, 0U) != 0) saved_error = errno;
    if (!saved_error && high > low + 1U && COLLECTOR_CLOSE_RANGE_CALL(low + 1U, high - 1U, 0U) != 0) saved_error = errno;
    if (!saved_error && COLLECTOR_CLOSE_RANGE_CALL(high + 1U, UINT_MAX, 0U) == 0) return true;
    if (!saved_error) saved_error = errno;
    if (saved_error != ENOSYS && saved_error != EPERM) { errno = saved_error; return false; }
    struct rlimit limit;
    if (COLLECTOR_GETRLIMIT_CALL(RLIMIT_NOFILE, &limit) != 0) return false;
    if (limit.rlim_max == RLIM_INFINITY || limit.rlim_max > 4096) { errno = EOVERFLOW; return false; }
    /* Clean launch requires inherited descriptors to fit this finite hard bound. */
    for (unsigned fd = 3; fd < (unsigned)limit.rlim_max; fd++) {
        if ((int)fd == a || (int)fd == b) continue;
        if (COLLECTOR_CLOSE_CALL((int)fd) != 0 && errno != EBADF) return false;
    }
    return true;
}

static _Noreturn void child_run(int stdin_fd, int out_fd, int err_fd, int setup_fd)
{
    uint64_t words[SETUP_WORDS] = { UINT64_C(0x314c4341), 1, 1, 1, 0 };
    gid_t groups[2] = { 0, 0 };
    /* x86-64 Linux rt_sigaction ABI, including glibc-reserved signals 32/33.
     * Public sigaction silently rejects those; inherited ignored dispositions
     * must not survive this infrastructure setup. All fields mean SIG_DFL/zero. */
    const uint64_t kernel_action[4] = { 0, 0, 0, 0 };
    for (int s = 1; s <= 64; ++s) {
        if (s == SIGKILL || s == SIGSTOP) continue;
        if (syscall(SYS_rt_sigaction, s, kernel_action, NULL, 8UL) != 0) child_error(setup_fd, 1, errno);
    }
    sigset_t empty; sigemptyset(&empty);
    int inherited_count = getgroups(2, groups);
    if ((inherited_count != 1 || groups[0] != 0) && setgroups(1, (gid_t[]){0}) != 0)
        child_error(setup_fd, 1, errno);
    if (sigprocmask(SIG_SETMASK, &empty, NULL) != 0 || setsid() < 0 ||
        setresgid(0, 0, 0) != 0 || setresuid(0, 0, 0) != 0 ||
        fchdir(cwd_fd) != 0) child_error(setup_fd, 1, errno);
    umask(0022);
    if (dup2(stdin_fd, 0) != 0 || dup2(out_fd, 1) != 1 || dup2(err_fd, 2) != 2)
        child_error(setup_fd, 1, errno);
    if (!close_except(executable.fd, setup_fd)) child_error(setup_fd, 1, errno);
    char actual_cwd[4096];
    struct stat cwd, descriptors[3], exec;
    if (!getcwd(actual_cwd, sizeof actual_cwd)) child_error(setup_fd, 1, errno);
    if (strcmp(actual_cwd, literal(request.cwd))) child_error(setup_fd, 1, ESTALE);
    if (stat(".", &cwd) != 0 || fstat(executable.fd, &exec) != 0) child_error(setup_fd, 1, errno);
    int count = getgroups(2, groups);
    mode_t mask = umask(0022);
    words[5] = (uint64_t)getpid(); words[6] = (uint64_t)getppid();
    words[7] = (uint64_t)getpgrp(); words[8] = (uint64_t)getsid(0);
    words[9] = getuid(); words[10] = geteuid(); words[11] = getgid(); words[12] = getegid();
    words[13] = count < 0 ? UINT64_MAX : (uint64_t)count; words[14] = groups[0]; words[15] = mask;
    words[16] = (uint64_t)cwd.st_dev; words[17] = (uint64_t)cwd.st_ino;
    for (unsigned i = 0; i < 3; ++i) {
        if (fstat((int)i, &descriptors[i]) != 0) child_error(setup_fd, 1, errno);
        words[18 + i * 3] = descriptors[i].st_mode;
        words[19 + i * 3] = (uint64_t)descriptors[i].st_dev;
        words[20 + i * 3] = (uint64_t)descriptors[i].st_ino;
        int fl = fcntl((int)i, F_GETFL), fdfl = fcntl((int)i, F_GETFD);
        if (fl < 0 || fdfl < 0) child_error(setup_fd, 1, errno);
        words[31 + i] = (uint64_t)fl; words[34 + i] = (uint64_t)fdfl;
    }
    words[27] = (uint64_t)exec.st_dev; words[28] = (uint64_t)exec.st_ino;
    int seals = fcntl(executable.fd, F_GET_SEALS), exec_flags = fcntl(executable.fd, F_GETFD);
    if (seals < 0 || exec_flags < 0) child_error(setup_fd, 1, errno);
    words[29] = (uint64_t)seals; words[37] = (uint64_t)exec_flags;
    off_t offset = lseek(0, 0, SEEK_CUR);
    words[30] = offset < 0 ? UINT64_MAX : (uint64_t)offset;
    bool valid = words[5] == words[7] && words[5] == words[8] &&
        !words[9] && !words[10] && !words[11] && !words[12] && count == 1 && !groups[0] && mask == 0022 &&
        cwd.st_dev == cwd_identity.st_dev && cwd.st_ino == cwd_identity.st_ino &&
        exec.st_dev == executable.backing.st_dev && exec.st_ino == executable.backing.st_ino && seals == executable.seals &&
        (exec_flags & FD_CLOEXEC) && S_ISFIFO(descriptors[1].st_mode) && S_ISFIFO(descriptors[2].st_mode);
    const struct stat *in = request.stdin_mode == 1 ? &input.backing : &devnull_identity;
    valid = valid && descriptors[0].st_dev == in->st_dev && descriptors[0].st_ino == in->st_ino &&
        (request.stdin_mode == 1 ? S_ISREG(descriptors[0].st_mode) && offset == 0 :
         S_ISCHR(descriptors[0].st_mode) && descriptors[0].st_rdev == makedev(1, 3));
    for (unsigned i = 0; i < 3; ++i) {
        valid = valid && !(words[31 + i] & O_NONBLOCK) && !(words[34 + i] & FD_CLOEXEC) &&
            (words[31 + i] & O_ACCMODE) == (i == 0 ? O_RDONLY : O_WRONLY);
        if (i) valid = valid && descriptors[i].st_dev == pipe_identity[i - 1].st_dev &&
            descriptors[i].st_ino == pipe_identity[i - 1].st_ino;
    }
    if (!valid) child_error(setup_fd, 1, ESTALE);
    setup_packet(setup_fd, words);
    char *args[ACRQ_LIST_MAX + 1], *env[ACRQ_LIST_MAX + 1];
    for (unsigned i = 0; i < request.argc; ++i) args[i] = (char *)literal(request.argv[i]);
    for (unsigned i = 0; i < request.envc; ++i) env[i] = (char *)literal(request.env[i]);
    args[request.argc] = NULL; env[request.envc] = NULL;
    syscall(SYS_execveat, executable.fd, "", args, env, AT_EMPTY_PATH);
    child_error(setup_fd, 2, errno);
}

static bool make_pipe(int fds[2])
{
    if (pipe2(fds, O_CLOEXEC) != 0) return false;
    fds[0] = high_fd(fds[0]); fds[1] = high_fd(fds[1]);
    if (fds[0] < 0 || fds[1] < 0) return false;
    int flags = fcntl(fds[0], F_GETFL);
    return flags >= 0 && fcntl(fds[0], F_SETFL, flags | O_NONBLOCK) == 0;
}

static void observe_exec(void)
{
    if (exec_backing_observed || !child_created || leader.reaped) return;
    char path[80]; snprintf(path, sizeof path, "/proc/%ld/exe", (long)leader.pid);
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return;
    struct stat actual;
    bool match = fstat(fd, &actual) == 0 && actual.st_dev == executable.backing.st_dev && actual.st_ino == executable.backing.st_ino;
    close(fd);
    if (!match) return;
    observed_exec = actual; observed_exec_ns = now_ns(); exec_backing_observed = true;
    ssize_t n = readlink(path, observed_exec_link, sizeof observed_exec_link - 1);
    if (n >= 0 && n < (ssize_t)sizeof observed_exec_link - 1) {
        observed_exec_link[n] = 0; observed_exec_link_ns = now_ns(); observed_exec_link_complete = true;
    }
    event("\"event\":\"observed-sealed-exe\",\"pid\":%ld", (long)leader.pid);
}

static void pump(void)
{
    unsigned char buffer[8192];
    for (unsigned i = 0; i < 3; ++i) {
        struct stream *s = &streams[i];
        if (s->fd < 0 || s->eof) continue;
        /* Bounded work per pipe preserves time checks under continuous writers. */
        for (unsigned reads = 0; reads < 8; ++reads) {
            ssize_t n = read(s->fd, buffer, sizeof buffer);
            if (n < 0 && errno == EINTR) continue;
            if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) break;
            if (n < 0) { fail("COLLECTOR_ERROR", "pipe-read", errno); close(s->fd); s->fd = -1; break; }
            if (!n) { s->eof = true; close(s->fd); s->fd = -1; break; }
            uint64_t offset = s->sink.seen;
            if (i == 2 && offset < sizeof setup_bytes) {
                size_t keep = (size_t)n;
                if (keep > sizeof setup_bytes - (size_t)offset) keep = sizeof setup_bytes - (size_t)offset;
                memcpy(setup_bytes + offset, buffer, keep);
            }
            if (!retain(&s->sink, buffer, (size_t)n)) fail("OUTPUT_LIMIT", i == 2 ? "setup-bound" : "stream-bound", EFBIG);
        }
    }
}

static void short_poll(void)
{
    struct pollfd fds[3];
    for (unsigned i = 0; i < 3; ++i) { fds[i].fd = streams[i].fd; fds[i].events = POLLIN | POLLHUP; fds[i].revents = 0; }
    if (poll(fds, 3, 10) < 0 && errno != EINTR) fail("COLLECTOR_ERROR", "pipe-poll", errno);
}

static void check_leader(void)
{
    if (leader_waitable || leader.reaped) return;
    siginfo_t info; memset(&info, 0, sizeof info);
    if (waitid(P_PID, (id_t)leader.pid, &info, WEXITED | WNOHANG | WNOWAIT) != 0) {
        if (errno != EINTR) fail("COLLECTOR_ERROR", "leader-waitid", errno);
        return;
    }
    if (info.si_pid == leader.pid) {
        leader_waitable = true; completion_observed = now_ns();
        event("\"event\":\"leader-waitable\",\"pid\":%ld", (long)leader.pid);
        if (completion_observed >= process_deadline) fail("TIMED_OUT", "completion-observed-after-deadline", ETIMEDOUT);
    }
}

static bool same_owned(const struct process *p, struct process *current)
{
    return p->recorded && !p->reaped && proc_identity(p->pid, current) &&
        current->ticks == p->ticks && current->ppid == getpid();
}

static void kill_owned(struct process *p)
{
    struct process current;
    if (p->reaped || p->kill_sent) return;
    if (!same_owned(p, &current)) { fail("CLEANUP_ERROR", "owned-identity-unavailable", ESTALE); return; }
    if (kill(p->pid, SIGKILL) != 0 && errno != ESRCH) { fail("CLEANUP_ERROR", "owned-kill", errno); return; }
    p->kill_sent = true;
    event("\"event\":\"owned-kill-attempt\",\"pid\":%ld,\"startticks\":%" PRIu64, (long)p->pid, p->ticks);
}

static bool scan_children(void)
{
    char path[96], bytes[8192]; snprintf(path, sizeof path, "/proc/self/task/%ld/children", (long)getpid());
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
    if (fd < 0) return fail("CLEANUP_ERROR", "children-open", errno);
    ssize_t n; do { n = read(fd, bytes, sizeof bytes - 1); } while (n < 0 && errno == EINTR);
    close(fd);
    if (n < 0 || n == (ssize_t)sizeof bytes - 1) return fail("CLEANUP_ERROR", "children-read-bound", n < 0 ? errno : EFBIG);
    bytes[n] = 0; char *cursor = bytes;
    while (*cursor) {
        while (*cursor == ' ' || *cursor == '\n') ++cursor;
        if (!*cursor) break;
        char *end; errno = 0; long number = strtol(cursor, &end, 10);
        if (errno || end == cursor || number <= 0 || number > INT_MAX || (*end && *end != ' ' && *end != '\n'))
            return fail("CLEANUP_ERROR", "children-format", EINVAL);
        cursor = end; pid_t pid = (pid_t)number;
        if (pid == leader.pid) continue;
        struct process actual;
        if (!proc_identity(pid, &actual) || actual.ppid != getpid()) return fail("CLEANUP_ERROR", "adopted-identity", ESTALE);
        unsigned i;
        for (i = 0; i < owned_count; ++i) if (owned[i].pid == pid && owned[i].ticks == actual.ticks) break;
        if (i == owned_count) {
            if (owned_count == OWNED_LIMIT) { ++owned_omitted; return fail("CLEANUP_ERROR", "owned-record-bound", EFBIG); }
            owned[owned_count++] = actual;
            fail("ORPHANED_DESCENDANTS", "surviving-owned-descendant", ECHILD);
            event("\"event\":\"adopted-child\",\"pid\":%ld,\"startticks\":%" PRIu64, (long)pid, actual.ticks);
        }
    }
    return true;
}

static void reap(struct process *p)
{
    if (p->reaped) return;
    int raw; pid_t actual = waitpid(p->pid, &raw, WNOHANG);
    if (actual == 0 || (actual < 0 && errno == EINTR)) return;
    if (actual != p->pid) { fail("CLEANUP_ERROR", "owned-waitpid", actual < 0 ? errno : ECHILD); return; }
    p->raw_wait = raw; p->reaped = true;
    event("\"event\":\"actual-reap\",\"pid\":%ld,\"raw_wait_status\":%d", (long)p->pid, raw);
}

static void cleanup(void)
{
    cleanup_start = now_ns(); cleanup_deadline = cleanup_start + 15 * NS;
    bool group_handled = false;
    while (now_ns() < cleanup_deadline) {
        if (interrupted) fail("INTERRUPTED", "collector-interrupted", EINTR);
        pump();
        if (!leader.reaped && !group_handled) {
            struct process actual;
            if (same_owned(&leader, &actual)) {
                if (actual.pgid == leader.pid && actual.sid == leader.pid && actual.pgid != getpgrp()) {
                    group_pinned = true;
                    if (kill(-leader.pid, SIGKILL) == 0 || errno == ESRCH) {
                        group_handled = true;
                        event("\"event\":\"owned-group-kill-attempt\",\"pgid\":%ld,\"leader_startticks\":%" PRIu64,
                              (long)leader.pid, leader.ticks);
                    } else fail("CLEANUP_ERROR", "owned-group-kill", errno);
                } else { kill_owned(&leader); group_handled = leader.kill_sent; }
            } else {
                fail("CLEANUP_ERROR", "leader-cleanup-identity", ESTALE);
                /* This direct child has never been reaped and SIGCHLD was set
                 * to default before fork. Its fork-owned PID cannot be reused.
                 * Missing proc evidence forbids a group kill, but not bounded
                 * cleanup of that exact direct child. Never invent its ticks. */
                if (kill(leader.pid, SIGKILL) == 0 || errno == ESRCH) {
                    leader.kill_sent = true; group_handled = true;
                    event("\"event\":\"direct-unreaped-child-kill-without-proc-identity\",\"pid\":%ld", (long)leader.pid);
                }
            }
        }
        (void)scan_children();
        for (unsigned i = 0; i < owned_count; ++i) { kill_owned(&owned[i]); reap(&owned[i]); }
        /* No group signal is possible after this point: its pinned leader may be reaped. */
        if (group_handled) reap(&leader);
        siginfo_t info; memset(&info, 0, sizeof info);
        errno = 0;
        int result = waitid(P_ALL, 0, &info, WEXITED | WNOHANG | WNOWAIT);
        bool no_children = result < 0 && errno == ECHILD;
        if (result < 0 && errno != ECHILD && errno != EINTR) fail("CLEANUP_ERROR", "all-children-waitid", errno);
        pump();
        if (no_children && leader.reaped && streams[0].eof && streams[1].eof && streams[2].eof) {
            cleanup_complete = true; break;
        }
        short_poll();
    }
    cleanup_finished = now_ns();
    if (interrupted) fail("INTERRUPTED", "collector-interrupted", EINTR);
    if (!cleanup_complete || cleanup_finished >= cleanup_deadline) {
        cleanup_complete = false; fail("CLEANUP_ERROR", "owned-cleanup-deadline-or-pipe-holder", ETIMEDOUT);
    }
}

static uint64_t read_word(const unsigned char *p)
{
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) value |= (uint64_t)p[i] << (8 * i);
    return value;
}

static void validate_setup(void)
{
    const struct sink *s = &streams[2].sink;
    if (!streams[2].eof || s->seen != s->stored || s->seen == 0 || s->seen % SETUP_PACKET || s->seen > sizeof setup_bytes) {
        fail("SETUP_ERROR", "setup-pipe-incomplete", EPROTO); return;
    }
    for (size_t offset = 0; offset < s->stored; offset += SETUP_PACKET) {
        uint64_t words[SETUP_WORDS];
        for (unsigned i = 0; i < SETUP_WORDS; ++i) words[i] = read_word(setup_bytes + offset + i * 8);
        if (words[0] != UINT64_C(0x314c4341) || words[1] != 1) { fail("SETUP_ERROR", "setup-version", EPROTO); return; }
        if (words[2] == 2) {
            if (setup_error || words[3] < 1 || words[3] > 2 || words[4] == 0 || words[4] > INT_MAX ||
                (words[3] == 2 && !setup_ready) || (words[3] == 1 && setup_ready)) {
                fail("SETUP_ERROR", "setup-error-shape", EPROTO); return;
            }
            for (unsigned i = 5; i < SETUP_WORDS; ++i) if (words[i]) { fail("SETUP_ERROR", "setup-error-reserved", EPROTO); return; }
            setup_error = true;
            fail(words[3] == 2 ? "EXEC_ERROR" : "SETUP_ERROR", words[3] == 2 ? "execveat-error" : "child-setup-error", (int)words[4]);
            continue;
        }
        if (words[2] != 1 || words[3] != 1 || words[4] || setup_ready || setup_error) {
            fail("SETUP_ERROR", "setup-ready-shape", EPROTO); return;
        }
        memcpy(setup_words, words, sizeof words); setup_ready = true;
        bool valid = words[5] == (uint64_t)leader.pid && words[6] == (uint64_t)getpid() && words[5] == words[7] && words[5] == words[8] &&
            !words[9] && !words[10] && !words[11] && !words[12] && words[13] == 1 && !words[14] && words[15] == 0022 &&
            words[16] == (uint64_t)cwd_identity.st_dev && words[17] == (uint64_t)cwd_identity.st_ino &&
            words[27] == (uint64_t)executable.backing.st_dev && words[28] == (uint64_t)executable.backing.st_ino &&
            words[29] == (uint64_t)executable.seals && words[37] == FD_CLOEXEC;
        const struct stat *in = request.stdin_mode == 1 ? &input.backing : &devnull_identity;
        for (unsigned i = 0; i < 3; ++i) {
            const struct stat *expected = i ? &pipe_identity[i - 1] : in;
            valid = valid && words[18 + 3 * i] == (uint64_t)expected->st_mode &&
                words[19 + 3 * i] == (uint64_t)expected->st_dev && words[20 + 3 * i] == (uint64_t)expected->st_ino &&
                !(words[31 + i] & O_NONBLOCK) && !words[34 + i] &&
                (words[31 + i] & O_ACCMODE) == (i == 0 ? O_RDONLY : O_WRONLY);
        }
        if (request.stdin_mode == 1 && words[30] != 0) valid = false;
        for (unsigned i = 38; i < SETUP_WORDS; ++i) if (words[i]) valid = false;
        if (!valid) { fail("SETUP_ERROR", "child-observed-setup-mismatch", ESTALE); return; }
        setup_validated = true;
    }
    if (!setup_ready && !setup_error) fail("SETUP_ERROR", "setup-ready-missing", EPROTO);
}

static void json_hex(FILE *file, const void *bytes, size_t length)
{
    const unsigned char *p = bytes;
    fputc('"', file);
    for (size_t i = 0; i < length; ++i) fprintf(file, "%02x", p[i]);
    fputc('"', file);
}

static void json_stat(FILE *file, const struct stat *s)
{
    fprintf(file, "{\"device\":%ju,\"inode\":%ju,\"mode\":%ju,\"uid\":%ju,\"gid\":%ju,\"size\":%jd,\"nlink\":%ju,"
            "\"mtime_seconds\":%jd,\"mtime_nanoseconds\":%ld,\"ctime_seconds\":%jd,\"ctime_nanoseconds\":%ld}",
            (uintmax_t)s->st_dev, (uintmax_t)s->st_ino, (uintmax_t)s->st_mode, (uintmax_t)s->st_uid, (uintmax_t)s->st_gid,
            (intmax_t)s->st_size, (uintmax_t)s->st_nlink, (intmax_t)s->st_mtim.tv_sec, s->st_mtim.tv_nsec,
            (intmax_t)s->st_ctim.tv_sec, s->st_ctim.tv_nsec);
}

static const char *boolean(bool value) { return value ? "true" : "false"; }

static void json_sink(FILE *file, const struct sink *s)
{
    if (!s->name) { fputs("null", file); return; }
    unsigned char digest[32]; ac_sha256_final(&s->hash, digest);
    fprintf(file, "{\"attempted_name\":\"%s\",\"created\":%s,\"fd_available\":%s,\"creation_errno\":%d,\"fd_errno\":%d,\"path\":",
            s->name, boolean(s->created), boolean(s->fd >= 0), s->creation_errno, s->fd_errno);
    if (s->created) fprintf(file, "\"%s\"", s->name); else fputs("null", file);
    fprintf(file, ",\"limit_bytes\":%" PRIu64 ",\"seen_bytes\":%" PRIu64 ",\"stored_bytes\":%" PRIu64
            ",\"truncated\":%s,\"io_error\":%s,\"sha256\":", s->limit, s->seen, s->stored, boolean(s->truncated), boolean(s->io_error));
    if (s->created && s->fd >= 0) json_hex(file, digest, sizeof digest); else fputs("null", file);
    fputc('}', file);
}

static void json_source(FILE *file, const struct source *s)
{
    fprintf(file, "{\"opened\":%s,\"stable\":%s,\"verified\":%s,\"source_before\":", boolean(s->opened), boolean(s->stable), boolean(s->verified));
    if (s->stat_observed) json_stat(file, &s->before); else fputs("null", file);
    fputs(",\"source_after\":", file);
    if (s->after_stat_observed) json_stat(file, &s->after); else fputs("null", file);
    fputs(",\"sealed_backing\":", file);
    if (s->verified) json_stat(file, &s->backing); else fputs("null", file);
    fprintf(file, ",\"requested_memfd_flags\":%u,\"seals\":%d,\"artifact\":", MFD_CLOEXEC | MFD_ALLOW_SEALING, s->seals);
    json_sink(file, &s->artifact); fputc('}', file);
}

static void json_process(FILE *file, const struct process *p)
{
    fprintf(file, "{\"pid\":%ld,\"identity_observed\":%s,\"ppid\":%ld,\"pgid_at_observation\":%ld,\"sid_at_observation\":%ld,"
            "\"startticks\":%" PRIu64 ",\"kill_sent\":%s,\"reaped\":%s,\"raw_wait_status\":", (long)p->pid, boolean(p->recorded),
            (long)p->ppid, (long)p->pgid, (long)p->sid, p->ticks, boolean(p->kill_sent), boolean(p->reaped));
    if (!p->reaped) fputs("null,\"wait\":null}", file);
    else {
        fprintf(file, "%d,\"wait\":{\"exited\":%s,\"signaled\":%s,\"exit_code\":", p->raw_wait,
                boolean(WIFEXITED(p->raw_wait)), boolean(WIFSIGNALED(p->raw_wait)));
        if (WIFEXITED(p->raw_wait)) fprintf(file, "%d", WEXITSTATUS(p->raw_wait)); else fputs("null", file);
        fputs(",\"signal\":", file);
        if (WIFSIGNALED(p->raw_wait)) fprintf(file, "%d", WTERMSIG(p->raw_wait)); else fputs("null", file);
        fprintf(file, ",\"core_dumped\":%s}}", boolean(WIFSIGNALED(p->raw_wait) && WCOREDUMP(p->raw_wait)));
    }
}

static bool report(void)
{
    struct sink *all[] = { &request_artifact, &manifest_artifact, &argv_artifact, &env_artifact, &events,
        &executable.artifact, &input.artifact, &streams[0].sink, &streams[1].sink, &streams[2].sink };
    for (size_t i = 0; i < sizeof all / sizeof *all; ++i)
        if (all[i]->fd >= 0 && fsync(all[i]->fd) != 0) fail("COLLECTOR_ERROR", "artifact-fsync", errno);
    if (interrupted) fail("INTERRUPTED", "collector-interrupted", EINTR);
    if (!strcmp(failure, "none")) status = "COMPLETED";
    int fd = high_fd(openat(attempt_fd, "report.json", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
    if (fd < 0) return false;
    FILE *f = fdopen(fd, "w");
    if (!f) { close(fd); return false; }
    fprintf(f, "{\"schema_version\":1,\"kind\":\"linux-sealed-infrastructure-collection\","
            "\"collector_mode\":\"linux-sealed-infrastructure-v1\",\"status\":\"%s\",\"first_failure\":\"%s\","
            "\"first_failure_errno\":%d,\"first_failure_monotonic_ns\":%" PRIu64 ","
            "\"application_acceptance\":false,\"transport_acceptance\":false,\"backend_enabled\":false,"
            "\"pathname_execution\":false,\"loader_closure_verified\":false,\"native_payload\":null,"
            "\"collector_pid\":%ld,\"collector_uid\":%ju,\"collector_euid\":%ju,\"collector_interruption_signal\":%d,\"request_valid\":%s,\"desired\":",
            status, failure, failure_errno, first_failure_ns, (long)getpid(), (uintmax_t)getuid(), (uintmax_t)geteuid(), (int)interrupted, boolean(request_valid));
    if (!request_valid) fputs("null", f);
    else {
        fprintf(f, "{\"role\":%u,\"request_profile\":%u,\"uid\":%u,\"gid\":%u,\"group\":%u,\"umask\":%u,"
                "\"argc\":%u,\"envc\":%u,\"stdin_mode\":%u,\"case_id_hex\":", request.role, request.profile,
                request.uid, request.gid, request.group, request.umask_value, request.argc, request.envc, request.stdin_mode);
        json_hex(f, literal(request.case_id), request.case_id.length); fputs(",\"source_selector_hex\":", f);
        json_hex(f, literal(request.executable_path), request.executable_path.length); fputs(",\"cwd_hex\":", f);
        json_hex(f, literal(request.cwd), request.cwd.length); fputs(",\"stdin_selector_hex\":", f);
        json_hex(f, literal(request.stdin_path), request.stdin_path.length); fputs(",\"attempt_id_hex\":", f);
        json_hex(f, request.attempt_id, 16); fputs(",\"selected_inputs_sha256\":", f);
        json_hex(f, request.selected_inputs_sha256, 32); fputc('}', f);
    }
    fprintf(f, ",\"configured_execution_mechanism\":\"execveat-AT_EMPTY_PATH-sealed-memfd\",\"child_created\":%s,\"linux_child\":",
            boolean(child_created));
    if (child_created) json_process(f, &leader); else fputs("null", f);
    fprintf(f, ",\"setup_ready_record\":%s,\"setup_error_record\":%s,\"setup_validated\":%s,\"setup_words\":[",
            boolean(setup_ready), boolean(setup_error), boolean(setup_validated));
    for (unsigned i = 0; i < SETUP_WORDS; ++i) fprintf(f, "%s%" PRIu64, i ? "," : "", setup_words[i]);
    fprintf(f, "],\"post_exec_backing_observed\":%s,\"post_exec_observed_monotonic_ns\":%" PRIu64 ",\"post_exec_backing\":",
            boolean(exec_backing_observed), observed_exec_ns);
    if (exec_backing_observed) json_stat(f, &observed_exec); else fputs("null", f);
    fputs(",\"subsequent_proc_exe_link_sample\":", f);
    if (observed_exec_link_complete) {
        fprintf(f, "{\"atomic_with_backing_stat\":false,\"observed_monotonic_ns\":%" PRIu64 ",\"bytes_hex\":", observed_exec_link_ns);
        json_hex(f, observed_exec_link, strlen(observed_exec_link)); fputc('}', f);
    } else fputs("null", f);
    fprintf(f, ",\"preparation_start_ns\":%" PRIu64 ",\"preparation_deadline_ns\":%" PRIu64
            ",\"process_start_ns\":%" PRIu64 ",\"process_deadline_ns\":%" PRIu64 ",\"completion_observed_ns\":%" PRIu64
            ",\"cleanup_start_ns\":%" PRIu64 ",\"cleanup_deadline_ns\":%" PRIu64 ",\"cleanup_finished_ns\":%" PRIu64
            ",\"cleanup_complete\":%s,\"group_identity_pinned\":%s,\"owned_records_omitted\":%" PRIu64 ",\"owned_children\":[",
            preparation_start, preparation_deadline, process_start, process_deadline, completion_observed,
            cleanup_start, cleanup_deadline, cleanup_finished, boolean(cleanup_complete), boolean(group_pinned), owned_omitted);
    for (unsigned i = 0; i < owned_count; ++i) { if (i) fputc(',', f); json_process(f, &owned[i]); }
    fputs("],\"executable\":", f); json_source(f, &executable); fputs(",\"stdin\":", f); json_source(f, &input);
    fputs(",\"devnull_identity\":", f);
    if (request_valid && request.stdin_mode == 0 && devnull_identity.st_mode) json_stat(f, &devnull_identity); else fputs("null", f);
    fputs(",\"artifacts\":[", f);
    for (size_t i = 0; i < sizeof all / sizeof *all; ++i) { if (i) fputc(',', f); json_sink(f, all[i]); }
    fputs("],\"streams\":{", f);
    for (unsigned i = 0; i < 3; ++i) fprintf(f, "%s\"%s_eof\":%s", i ? "," : "", i == 0 ? "stdout" : i == 1 ? "stderr" : "setup", boolean(streams[i].eof));
    fputs("}}\n", f);
    bool ok = fflush(f) == 0 && !ferror(f) && fsync(fd) == 0;
    if (fclose(f) != 0) ok = false;
    if (fsync(attempt_fd) != 0) ok = false;
    /* A signal during final storage cannot leave a successful outer exit even
     * if the already-written inner snapshot preceded its observation. */
    if (interrupted && !strcmp(failure, "none")) {
        fail("INTERRUPTED", "collector-interrupted-during-report", EINTR); ok = false;
    }
    return ok;
}

static void close_resources(void)
{
    struct sink *all[] = { &request_artifact, &manifest_artifact, &argv_artifact, &env_artifact, &events,
        &executable.artifact, &input.artifact, &streams[0].sink, &streams[1].sink, &streams[2].sink };
    for (size_t i = 0; i < sizeof all / sizeof *all; ++i) if (all[i]->fd >= 0) close(all[i]->fd);
    for (unsigned i = 0; i < 3; ++i) if (streams[i].fd >= 0) close(streams[i].fd);
    if (executable.fd >= 0) close(executable.fd);
    if (input.fd >= 0) close(input.fd);
    if (cwd_fd >= 0) close(cwd_fd);
    if (attempt_fd >= 0) close(attempt_fd);
}

int main(int argc, char **argv)
{
    struct sink *all[] = { &request_artifact, &manifest_artifact, &argv_artifact, &env_artifact, &events,
        &executable.artifact, &input.artifact, &streams[0].sink, &streams[1].sink, &streams[2].sink };
    for (size_t i = 0; i < sizeof all / sizeof *all; ++i) all[i]->fd = -1;
    for (unsigned i = 0; i < 3; ++i) streams[i].fd = -1;
    executable.fd = input.fd = -1;
    preparation_start = now_ns(); preparation_deadline = preparation_start + 120 * NS;
    umask(0077);
    if (argc != 5) { fputs("usage: linux-collector --linux-sealed-infrastructure-v1 REQUEST INPUT_MANIFEST ATTEMPT\n", stderr); return 2; }
    if (!make_attempt(argv[4])) { fputs("fresh attempt creation failed\n", stderr); return 125; }
    if (!new_sink(&events, "events.jsonl", STREAM_LIMIT)) goto finished;
    event("\"event\":\"collector-start\",\"pid\":%ld", (long)getpid());
    if (strcmp(argv[1], "--linux-sealed-infrastructure-v1")) { fail("BLOCKED", "unsupported-collector-mode", EOPNOTSUPP); goto finished; }
#if !defined(__x86_64__)
    fail("BLOCKED", "unsupported-collector-host-architecture", EOPNOTSUPP); goto finished;
#endif
    struct sigaction action = { .sa_handler = caught }; sigemptyset(&action.sa_mask);
    if (sigaction(SIGINT, &action, NULL) != 0 || sigaction(SIGTERM, &action, NULL) != 0 || sigaction(SIGHUP, &action, NULL) != 0) {
        fail("PREPARATION_ERROR", "signal-handlers", errno); goto finished;
    }
    sigset_t handled; sigemptyset(&handled);
    sigaddset(&handled, SIGINT); sigaddset(&handled, SIGTERM); sigaddset(&handled, SIGHUP);
    if (sigprocmask(SIG_UNBLOCK, &handled, NULL) != 0) { fail("PREPARATION_ERROR", "handled-signal-mask", errno); goto finished; }
    action.sa_handler = SIG_IGN;
    if (sigaction(SIGPIPE, &action, NULL) != 0) { fail("PREPARATION_ERROR", "sigpipe-handler", errno); goto finished; }
    action.sa_handler = SIG_DFL;
    if (sigaction(SIGCHLD, &action, NULL) != 0) { fail("PREPARATION_ERROR", "sigchld-default", errno); goto finished; }
    if (!new_sink(&request_artifact, "request.bin", 65537) ||
        !raw_file(argv[2], &request_artifact, request_bytes, sizeof request_bytes, NULL, NULL)) goto finished;
    enum acrq_error decoded = acrq_decode(request_bytes, (size_t)request_artifact.stored, &request);
    if (decoded != ACRQ_OK) {
        event("\"event\":\"request-rejected\",\"decoder_error\":\"%s\"", acrq_error_name(decoded));
        fail("BLOCKED", "request-decode", EINVAL); goto finished;
    }
    request_valid = true;
    if (!new_sink(&manifest_artifact, "selected-inputs.bin", MANIFEST_LIMIT) ||
        !raw_file(argv[3], &manifest_artifact, NULL, 0, request.selected_inputs_sha256, NULL)) goto finished;
    if (request.role != 1 || request.profile != 1) { fail("BLOCKED", "unsupported-role-or-profile", EOPNOTSUPP); goto finished; }
    if (getuid() != 0 || geteuid() != 0) { fail("BLOCKED", "root-infrastructure-identity-required", EPERM); goto finished; }
    if (request.executable_size > EXEC_LIMIT || request.stdin_size > STREAM_LIMIT) {
        fail("BLOCKED", "sealed-profile-size-subset", EFBIG); goto finished;
    }
    if (!new_sink(&argv_artifact, "argv.nul", ACRQ_WIRE_MAX) || !new_sink(&env_artifact, "env.nul", ACRQ_WIRE_MAX)) goto finished;
    for (unsigned i = 0; i < request.argc; ++i) if (!retain(&argv_artifact, literal(request.argv[i]), request.argv[i].length + 1U)) goto finished;
    for (unsigned i = 0; i < request.envc; ++i) if (!retain(&env_artifact, literal(request.env[i]), request.env[i].length + 1U)) goto finished;
    if (!seal_source(&executable, literal(request.executable_path), "executable.verified.bin", request.executable_size, request.executable_sha256, true)) goto finished;
    if (request.stdin_mode == 1) {
        if (!seal_source(&input, literal(request.stdin_path), "stdin.verified.bin", request.stdin_size, request.stdin_sha256, false)) goto finished;
    } else {
        input.fd = open_path(literal(request.stdin_path), O_RDONLY);
        if (input.fd < 0 || fstat(input.fd, &devnull_identity) != 0 || !S_ISCHR(devnull_identity.st_mode) || devnull_identity.st_rdev != makedev(1, 3)) {
            fail("PREPARATION_ERROR", "devnull-identity", ENODEV); goto finished;
        }
        int flags = fcntl(input.fd, F_GETFL);
        if (flags < 0 || fcntl(input.fd, F_SETFL, flags & ~O_NONBLOCK) != 0) { fail("PREPARATION_ERROR", "stdin-flags", errno); goto finished; }
    }
    cwd_fd = open_path(literal(request.cwd), O_RDONLY | O_DIRECTORY);
    if (cwd_fd < 0 || fstat(cwd_fd, &cwd_identity) != 0 || !S_ISDIR(cwd_identity.st_mode)) { fail("PREPARATION_ERROR", "cwd-open", errno); goto finished; }
    int subreaper = 0;
    if (prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0 || prctl(PR_GET_CHILD_SUBREAPER, &subreaper, 0, 0, 0) != 0 || subreaper != 1) {
        fail("BLOCKED", "subreaper-unavailable-or-unconfirmed", errno); goto finished;
    }
    int pipes[3][2] = { {-1, -1}, {-1, -1}, {-1, -1} };
    bool pipes_ok = true;
    for (unsigned i = 0; i < 3; ++i) {
        if (!new_sink(&streams[i].sink, i == 0 ? "stdout.bin" : i == 1 ? "stderr.bin" : "setup.bin", i == 2 ? sizeof setup_bytes : STREAM_LIMIT) ||
            !make_pipe(pipes[i])) { pipes_ok = false; break; }
        if (i < 2 && fstat(pipes[i][1], &pipe_identity[i]) != 0) { pipes_ok = false; break; }
    }
    if (!pipes_ok || !preparing()) {
        fail("PREPARATION_ERROR", "pipe-setup", errno);
        for (unsigned i = 0; i < 3; ++i) for (unsigned j = 0; j < 2; ++j) if (pipes[i][j] >= 0) close(pipes[i][j]);
        goto finished;
    }
    process_start = now_ns(); process_deadline = process_start + 10 * NS;
    pid_t pid = fork();
    int fork_error = errno;
    if (pid == 0) child_run(input.fd, pipes[0][1], pipes[1][1], pipes[2][1]);
    for (unsigned i = 0; i < 3; ++i) { close(pipes[i][1]); streams[i].fd = pipes[i][0]; }
    if (pid < 0) { fail("PREPARATION_ERROR", "fork", fork_error); goto finished; }
    child_created = true; leader.pid = pid;
    if (!proc_identity(pid, &leader) || leader.ppid != getpid()) fail("COLLECTOR_ERROR", "leader-initial-identity", ESTALE);
    event("\"event\":\"child-created\",\"pid\":%ld,\"startticks\":%" PRIu64, (long)pid, leader.ticks);
    while (!strcmp(failure, "none")) {
        pump(); observe_exec(); check_leader();
        if (interrupted) { fail("INTERRUPTED", "collector-interrupted", EINTR); break; }
        if (leader_waitable) break;
        if (now_ns() >= process_deadline) { fail("TIMED_OUT", "process-deadline", ETIMEDOUT); break; }
        short_poll();
    }
    cleanup(); validate_setup();
    if (!leader_waitable && !strcmp(failure, "none")) fail("COLLECTOR_ERROR", "completion-observation-missing", EPROTO);
finished:
    if (interrupted) fail("INTERRUPTED", "collector-interrupted", EINTR);
    event("\"event\":\"collector-finish\",\"first_failure\":\"%s\"", failure);
    bool retained = report();
    int code = !retained ? 125 : !strcmp(status, "COMPLETED") ? 0 : !strcmp(status, "BLOCKED") ? 2 : 1;
    close_resources();
    if (interrupted && code == 0) code = 1;
    return code;
}
