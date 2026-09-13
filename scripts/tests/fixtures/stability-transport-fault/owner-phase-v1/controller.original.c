/* SPDX-License-Identifier: GPL-2.0-only */
/* Linux collection utility. A zero exit is NOT transport/OS acceptance. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>
#include "uprotocol.h"

#define STREAM_LIMIT 65536u
#define UART_LIMIT 16384u
#define EVENT_LIMIT (8u * 1024u * 1024u)
#define NS_PER_MS UINT64_C(1000000)
static const char ready[] = "NATIVE_FAILURE_READY\n";
static const char complete[] = "NATIVE_FAILURE_READY\nNATIVE_FAILURE_PASS\n";
static char *const child_env[] = {
    "LANG=C", "LC_ALL=C", "TZ=UTC", "PATH=/bin:/usr/bin", NULL
};
struct sink {
    int fd;
    uint64_t seen, stored, limit;
    bool truncated;
};
struct stream {
    int fd;
    bool eof;
    struct sink sink;
    unsigned char bytes[STREAM_LIMIT];
};
struct sample {
    char raw[512];
    long nr;
    unsigned long arg[8];
    int parsed, error, raw_length;
};
static struct stream streams[2] = {{.fd = -1}, {.fd = -1}};
static struct sink events = {.fd = -1}, tx = {.fd = -1}, rx = {.fd = -1};
static int attempt_fd = -1, tty_fd = -1, input_fd = -1, report_fd = -1;
static pid_t launcher = -1, worker = -1;
static uint64_t launcher_ticks, worker_ticks, started_ns, overall_deadline;
static uint64_t input_ns, ret_entry_ns, ret_left_ns, wait_after_read_ns;
static uint64_t post_ack_ns, quiet_ack_ns;
static uint64_t first_failure_ns, emergency_ack_ns;
static bool launcher_done, launcher_reaped, launcher_kill_sent, cleanup_complete;
static bool ret_entry_seen, ret_left_seen, wait_after_read_seen, worker_gone;
static bool ack_pending, ack_received, request_written, guest, terminal_mode;
static bool emergency_attempted, emergency_capture_confirmed;
static bool emergency_uart_mode, uart_discard_until_newline;
static bool failed;
static int first_errno, raw_wait, admission_result, admission_errno;
static bool admission_observed;
static const char *first_failure = "none", *mode = "linux-reference", *nonce;
static const char *active_phase = "SETUP", *first_failure_phase = "none";
static unsigned sequence, ack_count, uart_protocol_errors;
static char ack_prefix[384], ack_digest[65], ack_line[512];
static size_t ack_length;
static volatile sig_atomic_t interrupted;

static uint64_t now_ns(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) < 0) _exit(124);
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}

static void fail(const char *reason, int error)
{
    if (!failed) {
        failed = true;
        first_failure = reason;
        first_errno = error;
        first_failure_ns = now_ns();
        first_failure_phase = active_phase;
        dprintf(2, "STF1 COLLECTION_FAILURE reason=%s errno=%d monotonic_ns=%" PRIu64 "\n",
                reason, error, first_failure_ns);
    }
}

static bool put_all(int fd, const void *bytes, size_t length)
{
    const unsigned char *p = bytes;
    while (length) {
        ssize_t n = write(fd, p, length);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return false;
        p += n;
        length -= (size_t)n;
    }
    return true;
}

static void retain(struct sink *s, const void *data, size_t length)
{
    size_t keep = length;
    s->seen += length;
    if (keep > s->limit - s->stored) keep = (size_t)(s->limit - s->stored);
    const unsigned char *bytes = data;
    size_t written = 0;
    while (written < keep) {
        ssize_t n = write(s->fd, bytes + written, keep - written);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { fail("artifact-write", n < 0 ? errno : EIO); return; }
        written += (size_t)n;
        s->stored += (size_t)n;
    }
    if (keep != length) {
        s->truncated = true;
        fail("artifact-limit", EFBIG);
    }
}

static void event(const char *format, ...)
{
    if (events.fd < 0) return;
    char body[2048], line[2176];
    va_list args;
    va_start(args, format);
    int n = vsnprintf(body, sizeof body, format, args);
    va_end(args);
    if (n < 0 || (size_t)n >= sizeof body) { fail("event-format", EOVERFLOW); return; }
    n = snprintf(line, sizeof line, "{\"monotonic_ns\":%" PRIu64 ",%s}\n", now_ns(), body);
    if (n < 0 || (size_t)n >= sizeof line) { fail("event-format", EOVERFLOW); return; }
    retain(&events, line, (size_t)n);
}

static void as_hex(const unsigned char *p, size_t n, char *out)
{
    static const char h[] = "0123456789abcdef";
    for (size_t i = 0; i < n; ++i) { out[2*i] = h[p[i] >> 4]; out[2*i+1] = h[p[i] & 15]; }
    out[2*n] = 0;
}

static bool lower_hex(const char *s, size_t n)
{
    if (strlen(s) != n) return false;
    for (size_t i = 0; i < n; ++i)
        if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f'))) return false;
    return true;
}

static int new_file(const char *name)
{
    return openat(attempt_fd, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
}

static bool start_sink(struct sink *s, const char *name, uint64_t limit)
{
    s->fd = new_file(name);
    s->limit = limit;
    if (s->fd < 0) { fail("artifact-create", errno); return false; }
    return true;
}

static uint64_t phase_deadline(unsigned ms)
{
    uint64_t d = now_ns() + (uint64_t)ms * NS_PER_MS;
    return d < overall_deadline ? d : overall_deadline;
}

/* Virtual procfs files have size zero. Read a bounded complete record. */
static int read_small(const char *path, char *out, size_t cap)
{
    int fd = open(path, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    size_t used = 0;
    int error = 0;
    while (used < cap - 1) {
        ssize_t n = read(fd, out + used, cap - 1 - used);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { error = errno; break; }
        if (n == 0) break;
        used += (size_t)n;
    }
    if (!error && used == cap - 1) {
        char extra;
        ssize_t n;
        do { n = read(fd, &extra, 1); } while (n < 0 && errno == EINTR);
        if (n != 0) error = n < 0 ? errno : EOVERFLOW;
    }
    close(fd);
    if (error) { errno = error; return -1; }
    out[used] = 0;
    return (int)used;
}

static bool task_ticks(pid_t tgid, pid_t tid, uint64_t *ticks)
{
    char path[128], raw[4096];
    snprintf(path, sizeof path, "/proc/%d/task/%d/stat", tgid, tid);
    if (read_small(path, raw, sizeof raw) < 0) return false;
    char *tail = strrchr(raw, ')'), *save = NULL;
    if (!tail || tail[1] != ' ') { errno = EPROTO; return false; }
    char *token = strtok_r(tail + 2, " \n", &save);
    for (unsigned field = 3; token; ++field, token = strtok_r(NULL, " \n", &save)) {
        if (field == 22) {
            char *end;
            errno = 0;
            unsigned long long value = strtoull(token, &end, 10);
            if (errno || *end || token[0] < '0' || token[0] > '9') { errno = EPROTO; return false; }
            *ticks = (uint64_t)value;
            return true;
        }
    }
    errno = EPROTO;
    return false;
}

static struct sample task_sample(pid_t tid, bool record)
{
    struct sample s = {.nr = -1};
    char path[128];
    snprintf(path, sizeof path, "/proc/%d/task/%d/syscall", launcher, tid);
    int n = read_small(path, s.raw, sizeof s.raw);
    if (n < 0) s.error = errno;
    else {
        s.raw_length = n;
        char extra;
        s.parsed = sscanf(s.raw, "%ld %lx %lx %lx %lx %lx %lx %lx %lx %c",
                          &s.nr, &s.arg[0], &s.arg[1], &s.arg[2], &s.arg[3],
                          &s.arg[4], &s.arg[5], &s.arg[6], &s.arg[7], &extra);
    }
    if (record) {
        char hex[1025];
        as_hex((const unsigned char *)s.raw, (size_t)s.raw_length, hex);
        event("\"event\":\"worker-syscall\",\"tgid\":%d,\"tid\":%d,\"errno\":%d,\"raw_hex\":\"%s\"",
              launcher, tid, s.error, hex);
    }
    return s;
}

static bool is_read16(const struct sample *s)
{
    return !s->error && s->parsed == 9 && s->nr == SYS_read && s->arg[0] == 0 && s->arg[2] == 16;
}

static bool is_ioctl(const struct sample *s, unsigned long command)
{
    return !s->error && s->parsed == 9 && s->nr == SYS_ioctl && s->arg[1] == command;
}

static pid_t find_reader(void)
{
    char path[128];
    snprintf(path, sizeof path, "/proc/%d/task", launcher);
    DIR *dir = opendir(path);
    if (!dir) { if (errno != ENOENT) fail("task-directory", errno); return -1; }
    pid_t found = -1;
    struct dirent *entry;
    unsigned scanned = 0;
    while ((entry = readdir(dir))) {
        if (++scanned > 512) { fail("task-scan-limit", EOVERFLOW); break; }
        char *end;
        long id = strtol(entry->d_name, &end, 10);
        if (*end || id <= 0 || id > INT_MAX) continue;
        struct sample s = task_sample((pid_t)id, false);
        if (!is_read16(&s)) continue;
        if (found > 0) { fail("ambiguous-blocked-reader", EPROTO); found = -1; break; }
        found = (pid_t)id;
    }
    closedir(dir);
    return found;
}

static void check_launcher(void)
{
    if (launcher <= 0 || launcher_reaped || launcher_done) return;
    siginfo_t si;
    memset(&si, 0, sizeof si);
    if (waitid(P_PID, (id_t)launcher, &si, WEXITED | WNOHANG | WNOWAIT) < 0) {
        fail("launcher-waitid", errno);
        return;
    }
    if (si.si_pid == launcher) {
        launcher_done = true;
        event("\"event\":\"launcher-waitable\",\"pid\":%d,\"si_code\":%d,\"si_status\":%d",
              launcher, si.si_code, si.si_status);
    }
}

static void drain_stream(struct stream *s)
{
    if (s->fd < 0 || s->eof) return;
    for (unsigned turn = 0; turn < 8; ++turn) {
        unsigned char bytes[4096];
        ssize_t n = read(s->fd, bytes, sizeof bytes);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) return;
        if (n < 0) { fail("stream-read", errno); return; }
        if (!n) { s->eof = true; close(s->fd); s->fd = -1; return; }
        size_t keep = (size_t)n;
        if (keep > STREAM_LIMIT - s->sink.stored) keep = (size_t)(STREAM_LIMIT - s->sink.stored);
        memcpy(s->bytes + s->sink.stored, bytes, keep);
        retain(&s->sink, bytes, (size_t)n);
    }
}

static void uart_reject(const char *reason)
{
    ++uart_protocol_errors;
    fail(reason, EPROTO);
    event("\"event\":\"uart-protocol-rejected\",\"reason\":\"%s\",\"count\":%u", reason, uart_protocol_errors);
}

static bool uart_bad_frame(const char *reason, bool at_newline)
{
    uart_reject(reason);
    if (!emergency_uart_mode) return false;
    /* The failed normal attempt stays failed. A late old frame must not prevent
     * a later exact emergency ACK from confirming independently saved evidence. */
    ack_length = 0;
    uart_discard_until_newline = !at_newline;
    return true;
}

static void receive_uart(void)
{
    if (tty_fd < 0) return;
    for (unsigned turn = 0; turn < 8; ++turn) {
        char bytes[512];
        ssize_t n = read(tty_fd, bytes, sizeof bytes);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) return;
        if (n < 0) { fail("uart-read", errno); return; }
        if (!n) return; /* raw nonblocking UART has VMIN=0 */
        retain(&rx, bytes, (size_t)n);
        for (ssize_t i = 0; i < n; ++i) {
            if (emergency_uart_mode && uart_discard_until_newline) {
                if (bytes[i] == '\n') uart_discard_until_newline = false;
                continue;
            }
            if (!ack_pending || !request_written) {
                if (uart_bad_frame("unsolicited-uart-data", bytes[i] == '\n')) continue;
                return;
            }
            if (!bytes[i] || ack_length + 1 >= sizeof ack_line) {
                if (uart_bad_frame("ack-framing", bytes[i] == '\n')) continue;
                return;
            }
            ack_line[ack_length++] = bytes[i];
            if (bytes[i] != '\n') continue;
            ack_line[ack_length] = 0;
            size_t prefix = strlen(ack_prefix);
            if (!ack_pending || ack_received || ack_length != prefix + 64 + strlen(" CONTINUED\n") ||
                memcmp(ack_line, ack_prefix, prefix) || strcmp(ack_line + prefix + 64, " CONTINUED\n")) {
                if (uart_bad_frame("ack-identity-or-phase", true)) continue;
                return;
            }
            memcpy(ack_digest, ack_line + prefix, 64);
            ack_digest[64] = 0;
            if (!lower_hex(ack_digest, 64)) {
                if (uart_bad_frame("ack-capture-digest", true)) continue;
                return;
            }
            ack_received = true;
            ack_pending = false;
            ++ack_count;
            ack_length = 0;
            event("\"event\":\"host-ack\",\"sequence\":%u,\"capture_sha256\":\"%s\"", sequence, ack_digest);
        }
    }
}

static void pump(unsigned ms)
{
    struct pollfd fds[3] = {
        {.fd = streams[0].fd, .events = POLLIN},
        {.fd = streams[1].fd, .events = POLLIN},
        {.fd = tty_fd, .events = POLLIN}
    };
    int result = poll(fds, 3, (int)ms);
    if (result < 0 && errno != EINTR) fail("poll", errno);
    for (unsigned i = 0; i < 3; ++i)
        if (fds[i].revents & POLLNVAL) fail("invalid-polled-fd", EBADF);
    drain_stream(&streams[0]);
    drain_stream(&streams[1]);
    receive_uart();
    check_launcher();
    if (interrupted) fail("controller-interrupted", (int)interrupted);
}

static bool before(uint64_t deadline)
{
    if (failed) return false;
    if (now_ns() >= deadline) { fail("phase-deadline", ETIMEDOUT); return false; }
    return true;
}

static bool capture(const char *phase)
{
    active_phase = phase;
    char request[384];
    if (ack_pending || ack_length) { fail("unsolicited-uart-data", EPROTO); return false; }
    ++sequence;
    int n = snprintf(request, sizeof request, "STF1 REQ %s %u %s %s %d %d %" PRIu64 "\n",
                     nonce, sequence, phase, mode, launcher, worker, worker_ticks);
    int a = snprintf(ack_prefix, sizeof ack_prefix, "STF1 ACK %s %u %s %s %d %d %" PRIu64 " ",
                     nonce, sequence, phase, mode, launcher, worker, worker_ticks);
    if (n <= 0 || (size_t)n >= sizeof request || a <= 0 || (size_t)a >= sizeof ack_prefix) {
        fail("request-format", EOVERFLOW); return false;
    }
    uint64_t deadline = phase_deadline(10000);
    ack_pending = true;
    ack_received = false;
    request_written = false;
    size_t sent = 0;
    event("\"event\":\"capture-request\",\"phase\":\"%s\",\"sequence\":%u", phase, sequence);
    while (sent < (size_t)n && before(deadline)) {
        ssize_t written = write(tty_fd, request + sent, (size_t)n - sent);
        if (written < 0 && errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK) {
            fail("uart-write", errno); break;
        }
        if (written > 0) {
            retain(&tx, request + sent, (size_t)written); sent += (size_t)written;
            request_written = sent == (size_t)n;
        }
        pump(5);
    }
    while (!ack_received && before(deadline)) pump(5);
    if (now_ns() >= deadline && !failed) fail("late-host-ack", ETIMEDOUT);
    return !failed && ack_received && sent == (size_t)n;
}

/* Failure is already latched. Do not use before(), which correctly rejects a
 * failed normal phase. This independent window preserves the live launcher
 * and pipe ownership until the host confirms retained emergency evidence or
 * thirty seconds expire. It never clears or upgrades the original failure. */
static void emergency_capture(void)
{
    if (!guest || !input_ns || emergency_attempted) return;
    emergency_attempted = true;
    active_phase = "EMERGENCY_CAPTURE";
    char request[512];
    ++sequence;
    int n = snprintf(request, sizeof request, "STF1 FAIL %s %u %s %s %d %d %" PRIu64 " %s %d\n",
                     nonce, sequence, first_failure_phase, mode, launcher, worker, worker_ticks,
                     first_failure, first_errno);
    int a = snprintf(ack_prefix, sizeof ack_prefix,
                     "STF1 ACK %s %u EMERGENCY_CAPTURED %s %d %d %" PRIu64 " ",
                     nonce, sequence, mode, launcher, worker, worker_ticks);
    if (n <= 0 || (size_t)n >= sizeof request || a <= 0 || (size_t)a >= sizeof ack_prefix || tty_fd < 0) {
        event("\"event\":\"emergency-request-unavailable\",\"capture_confirmed\":false");
        return;
    }
    /* Previously consumed bytes remain in uart.rx. Start a new explicit frame;
     * never flush the UART or claim a partial old ACK confirms this request. */
    event("\"event\":\"emergency-window-start\",\"sequence\":%u,\"failed_phase\":\"%s\",\"failure\":\"%s\",\"first_failure_ns\":%" PRIu64 ",\"previous_partial_ack_bytes\":%zu,\"launcher_reaped\":%s,\"limit_ms\":30000",
          sequence, first_failure_phase, first_failure, first_failure_ns, ack_length,
          launcher_reaped ? "true" : "false");
    ack_length = 0;
    ack_pending = true;
    ack_received = false;
    request_written = false;
    emergency_uart_mode = true;
    uart_discard_until_newline = false;
    size_t sent = 0;
    uint64_t deadline = now_ns() + UINT64_C(30000) * NS_PER_MS;
    while (sent < (size_t)n && now_ns() < deadline) {
        ssize_t written = write(tty_fd, request + sent, (size_t)n - sent);
        if (written < 0 && errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK) {
            event("\"event\":\"emergency-uart-write-error\",\"errno\":%d", errno);
            break;
        }
        if (written > 0) {
            retain(&tx, request + sent, (size_t)written);
            sent += (size_t)written;
            request_written = sent == (size_t)n;
        }
        pump(5);
    }
    while (!ack_received && now_ns() < deadline) pump(5);
    uint64_t observed = now_ns();
    emergency_capture_confirmed = sent == (size_t)n && ack_received && observed < deadline &&
        !rx.truncated && !tx.truncated;
    if (emergency_capture_confirmed) emergency_ack_ns = observed;
    event("\"event\":\"emergency-window-end\",\"sequence\":%u,\"capture_confirmed\":%s,\"deadline_ns\":%" PRIu64 ",\"observed_ns\":%" PRIu64 ",\"expired\":%s,\"request_bytes_sent\":%zu",
          sequence, emergency_capture_confirmed ? "true" : "false", deadline, observed,
          observed >= deadline ? "true" : "false", sent);
    ack_pending = false;
    emergency_uart_mode = false;
}

static bool setup_uart(void)
{
    tty_fd = open("/dev/ttyS1", O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
    if (tty_fd < 0) { fail("uart-open", errno); return false; }
    struct termios t;
    if (tcgetattr(tty_fd, &t) < 0) { fail("uart-getattr", errno); return false; }
    cfmakeraw(&t);
    t.c_cflag |= CLOCAL | CREAD;
    t.c_cflag &= ~CRTSCTS;
    t.c_cc[VMIN] = 0;
    t.c_cc[VTIME] = 0;
    if (cfsetispeed(&t, B115200) < 0 || cfsetospeed(&t, B115200) < 0 || tcsetattr(tty_fd, TCSANOW, &t) < 0) {
        fail("uart-configure", errno); return false;
    }
    /* Do not flush: stale bytes must remain evidence and fail the handshake. */
    receive_uart();
    if (ack_length) fail("unsolicited-uart-data", EPROTO);
    return !failed;
}

static bool close_extra_fds(void)
{
    DIR *dir = opendir("/proc/self/fd");
    if (!dir) return false;
    int keep = dirfd(dir);
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        char *end;
        long fd = strtol(entry->d_name, &end, 10);
        if (!*end && fd >= 3 && fd <= INT_MAX && fd != keep) close((int)fd);
    }
    return closedir(dir) == 0;
}

static void on_signal(int number) { interrupted = number; }

static bool start_child(char *launcher_path, char *payload_path)
{
    int pipes[3][2] = {{-1, -1}, {-1, -1}, {-1, -1}};
    for (unsigned i = 0; i < 3; ++i) {
        if (pipe2(pipes[i], O_CLOEXEC) < 0) { fail("pipe-create", errno); goto bad; }
    }
    char *guest_argv[] = {launcher_path, "-t", "1", "0", payload_path, NULL};
    char *linux_argv[] = {payload_path, NULL};
    char **args = guest ? guest_argv : linux_argv;
    int argv_fd = new_file("argv.nul"), env_fd = new_file("env.nul");
    if (argv_fd < 0 || env_fd < 0) {
        if (argv_fd >= 0) close(argv_fd);
        if (env_fd >= 0) close(env_fd);
        fail("execution-metadata-create", errno); goto bad;
    }
    for (size_t i = 0; args[i]; ++i)
        if (!put_all(argv_fd, args[i], strlen(args[i]) + 1)) fail("argv-write", errno);
    for (size_t i = 0; child_env[i]; ++i)
        if (!put_all(env_fd, child_env[i], strlen(child_env[i]) + 1)) fail("env-write", errno);
    close(argv_fd); close(env_fd);
    if (failed) goto bad;
    event("\"event\":\"launch-request\",\"cwd\":\"/case/work\",\"stdin\":\"owned-pipe\",\"stdout\":\"stdout.bin\",\"stderr\":\"stderr.bin\",\"umask_octal\":\"0022\"");
    launcher = fork();
    if (launcher < 0) { fail("fork", errno); goto bad; }
    if (!launcher) {
        signal(SIGINT, SIG_DFL); signal(SIGTERM, SIG_DFL); signal(SIGPIPE, SIG_DFL);
        if (setsid() < 0 || dup2(pipes[0][0], 0) != 0 || dup2(pipes[1][1], 1) != 1 ||
            dup2(pipes[2][1], 2) != 2 || chdir("/case/work") < 0 || !close_extra_fds()) {
            dprintf(2, "STF1 CHILD_SETUP_ERROR errno=%d\n", errno); _exit(125);
        }
        umask(0022);
        execve(guest ? launcher_path : payload_path, args, child_env);
        dprintf(2, "STF1 CHILD_EXEC_ERROR errno=%d\n", errno);
        _exit(126);
    }
    close(pipes[0][0]); close(pipes[1][1]); close(pipes[2][1]);
    input_fd = pipes[0][1]; streams[0].fd = pipes[1][0]; streams[1].fd = pipes[2][0];
    int fds[3] = {input_fd, streams[0].fd, streams[1].fd};
    for (unsigned i = 0; i < 3; ++i) {
        int flags = fcntl(fds[i], F_GETFL);
        if (flags < 0 || fcntl(fds[i], F_SETFL, flags | O_NONBLOCK) < 0) fail("pipe-nonblock", errno);
    }
    if (!task_ticks(launcher, launcher, &launcher_ticks)) fail("launcher-identity", errno);
    event("\"event\":\"launcher-created\",\"tgid\":%d,\"start_ticks\":%" PRIu64, launcher, launcher_ticks);
    return !failed;
bad:
    for (unsigned i = 0; i < 3; ++i) for (unsigned j = 0; j < 2; ++j)
        if (pipes[i][j] >= 0) close(pipes[i][j]);
    return false;
}

static bool prepare_read(void)
{
    uint64_t deadline = phase_deadline(10000);
    while (before(deadline)) {
        pump(5);
        size_t prefix = (size_t)streams[0].sink.stored;
        if (prefix > sizeof ready - 1) prefix = sizeof ready - 1;
        if (memcmp(streams[0].bytes, ready, prefix)) { fail("ready-bytes", EPROTO); break; }
        if (launcher_done || streams[0].eof) { fail("exit-before-blocked-read", ECHILD); break; }
        if (streams[0].sink.stored < sizeof ready - 1) continue;
        worker = find_reader();
        if (worker <= 0) continue;
        if (!task_ticks(launcher, worker, &worker_ticks)) { fail("worker-identity", errno); break; }
        struct sample s = task_sample(worker, true);
        if (!is_read16(&s)) { fail("blocked-read-changed", EPROTO); break; }
        event("\"event\":\"ULTRA_FAULT_BLOCKED\",\"launcher_tgid\":%d,\"linux_worker_tid\":%d,\"worker_start_ticks\":%" PRIu64,
              launcher, worker, worker_ticks);
        return !failed;
    }
    return false;
}

static bool release_input(void)
{
    uint64_t ticks;
    if (!task_ticks(launcher, worker, &ticks) || ticks != worker_ticks) { fail("pre-input-worker-identity", errno); return false; }
    struct sample s = task_sample(worker, true);
    if (!is_read16(&s)) { fail("pre-input-read-changed", EPROTO); return false; }
    unsigned char bytes[16];
    memset(bytes, 0xa5, sizeof bytes);
    input_ns = now_ns(); /* observation bound begins no later than input syscall */
    ssize_t n = write(input_fd, bytes, sizeof bytes);
    int error = n < 0 ? errno : 0;
    event("\"event\":\"ULTRA_FAULT_INPUT\",\"write_result\":%zd,\"errno\":%d,\"bytes_hex\":\"a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5\",\"begin_ns\":%" PRIu64, n, error, input_ns);
    /* One <= PIPE_BUF write. Never retry a partial or interrupted injection. */
    if (n != (ssize_t)sizeof bytes) { fail("input-write", error); return false; }
    close(input_fd); input_fd = -1;
    return true;
}

static bool observe_return(void)
{
    uint64_t deadline = input_ns + UINT64_C(15000) * NS_PER_MS;
    if (deadline > overall_deadline) deadline = overall_deadline;
    while (before(deadline)) {
        pump(5);
        uint64_t ticks;
        if (!task_ticks(launcher, worker, &ticks)) {
            int error = errno;
            event("\"event\":\"worker-stat-unavailable\",\"errno\":%d", error);
            if (error != ENOENT && error != ESRCH) { fail("worker-stat", error); break; }
            worker_gone = true;
            if (ret_entry_seen) { ret_left_seen = true; ret_left_ns = now_ns(); }
            return before(deadline);
        }
        if (ticks != worker_ticks) { fail("worker-identity-changed", EPROTO); break; }
        struct sample s = task_sample(worker, true);
        if (s.error && s.error != ENOENT && s.error != ESRCH) { fail("worker-syscall-read", s.error); break; }
        if (is_ioctl(&s, MCEXEC_UP_RET_SYSCALL)) {
            if (!ret_entry_seen) { ret_entry_seen = true; ret_entry_ns = now_ns(); }
        } else if (ret_entry_seen) {
            /* A successful different sample or disappearance proves it left the sampled RET.
             * This does not expose ioctl's return value or errno. */
            ret_left_seen = true; ret_left_ns = now_ns();
            return before(deadline);
        }
        if (is_ioctl(&s, MCEXEC_UP_WAIT_SYSCALL)) {
            wait_after_read_seen = true; wait_after_read_ns = now_ns();
            return before(deadline);
        }
        if (launcher_done) return before(deadline);
    }
    return false;
}

/* Only this controller's children are ever signalled/reaped. The launcher is
 * held waitable (WNOWAIT), so its process-group number cannot be recycled. */
static bool cleanup_owned(void)
{
    uint64_t deadline = now_ns() + UINT64_C(15000) * NS_PER_MS;
    if (input_fd >= 0) { close(input_fd); input_fd = -1; }
    if (launcher > 0 && !launcher_reaped) {
        uint64_t ticks;
        bool identity_ok = task_ticks(launcher, launcher, &ticks) && ticks == launcher_ticks;
        if (!identity_ok) fail("cleanup-launcher-identity", errno);
        pid_t group = getpgid(launcher);
        if (identity_ok && group == launcher) {
            if (kill(-launcher, SIGKILL) < 0 && errno != ESRCH) fail("cleanup-owned-group-kill", errno);
            if (!launcher_done) launcher_kill_sent = true;
        } else {
            /* Setup can fail before setsid; never signal the controller's group. */
            if (kill(launcher, SIGKILL) < 0 && errno != ESRCH) fail("cleanup-owned-child-kill", errno);
            if (!launcher_done) launcher_kill_sent = true;
        }
    }
    while (now_ns() < deadline) {
        char path[128], children[8192];
        snprintf(path, sizeof path, "/proc/self/task/%d/children", getpid());
        if (read_small(path, children, sizeof children) < 0) { fail("cleanup-child-list", errno); return false; }
        char *save = NULL, *token = strtok_r(children, " \n", &save);
        unsigned count = 0;
        while (token) {
            char *end;
            long pid = strtol(token, &end, 10);
            if (*end || pid <= 0 || pid > INT_MAX || ++count > 512) { fail("cleanup-child-list-format", EPROTO); return false; }
            /* A direct child remains owned and unreaped here; no concurrent waiter exists. */
            if (kill((pid_t)pid, SIGKILL) < 0 && errno != ESRCH) fail("cleanup-child-kill", errno);
            token = strtok_r(NULL, " \n", &save);
        }
        for (;;) {
            int status;
            pid_t reaped = waitpid(-1, &status, WNOHANG);
            if (reaped < 0 && errno == EINTR) continue;
            if (reaped <= 0) break;
            if (reaped == launcher) { raw_wait = status; launcher_reaped = true; }
            event("\"event\":\"owned-child-reaped\",\"pid\":%d,\"raw_wait_status\":%d,\"exited\":%s,\"exit_code\":%d,\"signaled\":%s,\"signal\":%d",
                  reaped, status, WIFEXITED(status) ? "true" : "false", WIFEXITED(status) ? WEXITSTATUS(status) : -1,
                  WIFSIGNALED(status) ? "true" : "false", WIFSIGNALED(status) ? WTERMSIG(status) : -1);
        }
        pump(5);
        /* ECHILD is an actual census after adoption/reaping; EOF independently
         * excludes a surviving pipe holder outside the observed child list. */
        int status;
        pid_t extra = waitpid(-1, &status, WNOHANG);
        if (extra > 0) {
            if (extra == launcher) { raw_wait = status; launcher_reaped = true; }
            event("\"event\":\"owned-child-reaped\",\"pid\":%d,\"raw_wait_status\":%d", extra, status);
        } else if (extra < 0 && errno == ECHILD && streams[0].eof && streams[1].eof) {
            cleanup_complete = true;
            return true;
        }
    }
    fail("owned-cleanup-deadline", ETIMEDOUT);
    return false;
}

/* Probe in its own owned child, since a broken ioctl must not stop the controller
 * deadline. This records new admission, NOT the accepted RET's return errno. */
static bool probe_admission(void)
{
    struct admission { int result, error; } answer;
    int pipefd[2];
    if (pipe2(pipefd, O_CLOEXEC | O_NONBLOCK) < 0) { fail("admission-pipe", errno); return false; }
    pid_t child = fork();
    if (child < 0) { fail("admission-fork", errno); close(pipefd[0]); close(pipefd[1]); return false; }
    if (!child) {
        close(pipefd[0]);
        int fd = open("/dev/mcos0", O_RDWR | O_CLOEXEC);
        answer.result = -2; answer.error = errno;
        if (fd >= 0) {
            errno = 0;
            answer.result = ioctl(fd, MCEXEC_UP_CREATE_PPD, NULL);
            answer.error = answer.result < 0 ? errno : 0;
            close(fd);
        }
        bool stored = put_all(pipefd[1], &answer, sizeof answer);
        _exit(stored ? 0 : 127);
    }
    close(pipefd[1]);
    uint64_t deadline = phase_deadline(5000);
    bool have_answer = false, reaped = false;
    int status = 0;
    while (before(deadline)) {
        if (!have_answer) {
            ssize_t n = read(pipefd[0], &answer, sizeof answer);
            if (n == (ssize_t)sizeof answer) have_answer = true;
            else if (n > 0 || (n < 0 && errno != EAGAIN && errno != EINTR)) { fail("admission-result-read", errno); break; }
        }
        pid_t result = waitpid(child, &status, WNOHANG);
        if (result == child) { reaped = true; break; }
        if (result < 0 && errno != EINTR) { fail("admission-wait", errno); break; }
        pump(5);
    }
    if (reaped && !have_answer) {
        ssize_t n = read(pipefd[0], &answer, sizeof answer);
        if (n == (ssize_t)sizeof answer) have_answer = true;
    }
    if (now_ns() >= deadline && !failed) fail("late-admission-observation", ETIMEDOUT);
    close(pipefd[0]);
    if (!reaped) {
        if (kill(child, SIGKILL) < 0 && errno != ESRCH) fail("admission-kill", errno);
        uint64_t cleanup_deadline = now_ns() + UINT64_C(15000) * NS_PER_MS;
        while (now_ns() < cleanup_deadline) {
            if (waitpid(child, &status, WNOHANG) == child) { reaped = true; break; }
            pump(5);
        }
        if (!reaped) { cleanup_complete = false; fail("admission-cleanup-deadline", ETIMEDOUT); }
    }
    event("\"event\":\"admission-probe\",\"pid\":%d,\"reaped\":%s,\"raw_wait_status\":%d,\"result_received\":%s,\"ioctl_command\":%lu",
          child, reaped ? "true" : "false", reaped ? status : -1, have_answer ? "true" : "false", (unsigned long)MCEXEC_UP_CREATE_PPD);
    if (!reaped || !have_answer || !WIFEXITED(status) || WEXITSTATUS(status) != 0) { fail("admission-probe-incomplete", EPROTO); return false; }
    admission_observed = true;
    admission_result = answer.result; admission_errno = answer.error;
    event("\"event\":\"new-admission-result\",\"result\":%d,\"errno\":%d", admission_result, admission_errno);
    int expected = !strcmp(mode, "permanent-backpressure") ? ETIMEDOUT : EIO;
    if (admission_result != -1 || admission_errno != expected) { fail("new-admission-oracle", EPROTO); return false; }
    return !failed;
}

static void write_report(void)
{
    if (report_fd < 0) return;
    char report[4096];
    int n = snprintf(report, sizeof report,
        "{\n\"schema_version\":1,\"application_acceptance\":false,\"transport_acceptance\":false,"
        "\"collection_status\":\"%s\",\"failure\":\"%s\",\"failure_errno\":%d,\"mode\":\"%s\","
        "\"first_failure_phase\":\"%s\",\"first_failure_ns\":%" PRIu64 ",\"emergency_capture_attempted\":%s,\"emergency_capture_confirmed\":%s,\"emergency_ack_ns\":%" PRIu64 ","
        "\"nonce\":\"%s\",\"launcher_tgid\":%d,\"launcher_start_ticks\":%" PRIu64 ",\"linux_worker_tid\":%d,\"worker_start_ticks\":%" PRIu64 ","
        "\"payload_guest_identity\":null,\"payload_identity_evidence\":\"external-typed-observer-required\","
        "\"started_ns\":%" PRIu64 ",\"finished_ns\":%" PRIu64 ",\"input_begin_ns\":%" PRIu64 ","
        "\"ret_entry_observed\":%s,\"ret_entry_ns\":%" PRIu64 ",\"ret_left_observed\":%s,\"ret_left_ns\":%" PRIu64 ","
        "\"post_read_wait_observed\":%s,\"post_read_wait_ns\":%" PRIu64 ",\"worker_disappearance_observed\":%s,"
        "\"accepted_ret_result\":null,\"accepted_ret_errno\":null,\"accepted_ret_evidence\":\"external-typed-observer-required\","
        "\"post_ret_ack_ns\":%" PRIu64 ",\"quiet_ack_ns\":%" PRIu64 ",\"host_ack_count\":%u,"
        "\"launcher_reaped\":%s,\"raw_wait_status\":%d,\"launcher_kill_sent\":%s,\"owned_linux_cleanup_complete\":%s,"
        "\"normal_mckernel_cleanup_verified\":false,\"quarantine_verified\":false,"
        "\"new_admission_observed\":%s,\"new_admission_result\":%d,\"new_admission_errno\":%d,"
        "\"stdout\":{\"bytes_seen\":%" PRIu64 ",\"bytes_stored\":%" PRIu64 ",\"truncated\":%s,\"eof\":%s},"
        "\"stderr\":{\"bytes_seen\":%" PRIu64 ",\"bytes_stored\":%" PRIu64 ",\"truncated\":%s,\"eof\":%s},"
        "\"uart_tx\":{\"bytes_seen\":%" PRIu64 ",\"bytes_stored\":%" PRIu64 ",\"truncated\":%s},"
        "\"uart_rx\":{\"bytes_seen\":%" PRIu64 ",\"bytes_stored\":%" PRIu64 ",\"truncated\":%s},"
        "\"events\":{\"bytes_seen\":%" PRIu64 ",\"bytes_stored\":%" PRIu64 ",\"truncated\":%s}\n}\n",
        failed ? "FAIL" : "COMPLETE", first_failure, first_errno, mode,
        first_failure_phase, first_failure_ns, emergency_attempted ? "true" : "false",
        emergency_capture_confirmed ? "true" : "false", emergency_ack_ns, nonce,
        launcher, launcher_ticks, worker, worker_ticks, started_ns, now_ns(), input_ns,
        ret_entry_seen ? "true" : "false", ret_entry_ns, ret_left_seen ? "true" : "false", ret_left_ns,
        wait_after_read_seen ? "true" : "false", wait_after_read_ns, worker_gone ? "true" : "false",
        post_ack_ns, quiet_ack_ns, ack_count, launcher_reaped ? "true" : "false", launcher_reaped ? raw_wait : -1,
        launcher_kill_sent ? "true" : "false", cleanup_complete ? "true" : "false",
        admission_observed ? "true" : "false", admission_result, admission_errno,
        streams[0].sink.seen, streams[0].sink.stored, streams[0].sink.truncated ? "true" : "false", streams[0].eof ? "true" : "false",
        streams[1].sink.seen, streams[1].sink.stored, streams[1].sink.truncated ? "true" : "false", streams[1].eof ? "true" : "false",
        tx.seen, tx.stored, tx.truncated ? "true" : "false", rx.seen, rx.stored, rx.truncated ? "true" : "false",
        events.seen, events.stored, events.truncated ? "true" : "false");
    if (n < 0 || (size_t)n >= sizeof report || !put_all(report_fd, report, (size_t)n)) fail("report-write", errno);
}

int main(int argc, char **argv)
{
    /* --guest MODE NONCE ATTEMPT_DIR MCEEXEC PAYLOAD
     * --linux-reference NONCE ATTEMPT_DIR PAYLOAD */
    guest = argc == 7 && !strcmp(argv[1], "--guest");
    bool reference = argc == 5 && !strcmp(argv[1], "--linux-reference");
    if (!guest && !reference) { dprintf(2, "STF1 invalid arguments\n"); return 2; }
    if (guest) mode = argv[2];
    if (guest && strcmp(mode, "prepublish-hard") && strcmp(mode, "postpublish-notify") &&
        strcmp(mode, "recoverable-backpressure") && strcmp(mode, "permanent-backpressure")) return 2;
    nonce = argv[guest ? 3 : 2];
    char *attempt = argv[guest ? 4 : 3], *payload = argv[guest ? 6 : 4];
    char *mcexec = guest ? argv[5] : payload;
    if (!lower_hex(nonce, 32) || attempt[0] != '/' || payload[0] != '/' || mcexec[0] != '/' ||
        strlen(attempt) >= PATH_MAX || strlen(payload) >= PATH_MAX || strlen(mcexec) >= PATH_MAX) return 2;
    terminal_mode = guest && strcmp(mode, "recoverable-backpressure");
    started_ns = now_ns(); overall_deadline = started_ns + UINT64_C(90000) * NS_PER_MS;
    for (int fd = 0; fd < 3; ++fd)
        if (fcntl(fd, F_GETFD) < 0) { fail("controller-standard-fd", errno); return 1; }
    signal(SIGPIPE, SIG_IGN); signal(SIGCHLD, SIG_DFL);
    signal(SIGINT, on_signal); signal(SIGTERM, on_signal);
    if (prctl(PR_SET_CHILD_SUBREAPER, 1) < 0) { fail("subreaper", errno); return 1; }
    if (mkdir(attempt, 0700) < 0) { fail("fresh-attempt-directory", errno); return 1; }
    attempt_fd = open(attempt, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (attempt_fd < 0) { fail("attempt-directory-open", errno); return 1; }
    report_fd = new_file("report.json");
    if (report_fd < 0) { fail("report-create", errno); return 1; }
    if (!start_sink(&events, "events.jsonl", EVENT_LIMIT) ||
        !start_sink(&streams[0].sink, "stdout.bin", STREAM_LIMIT) ||
        !start_sink(&streams[1].sink, "stderr.bin", STREAM_LIMIT) ||
        !start_sink(&tx, "uart.tx", UART_LIMIT) || !start_sink(&rx, "uart.rx", UART_LIMIT)) goto finish;
    event("\"event\":\"controller-start\",\"pid\":%d,\"uid\":%u,\"euid\":%u,\"gid\":%u,\"egid\":%u,\"mode\":\"%s\",\"overall_limit_ms\":90000,\"cleanup_limit_ms\":15000",
          getpid(), getuid(), geteuid(), getgid(), getegid(), mode);
    gid_t groups[512];
    int ngroups = getgroups(512, groups);
    if (ngroups < 0) { fail("identity-groups", errno); goto finish; }
    for (int i = 0; i < ngroups; ++i) event("\"event\":\"supplementary-group\",\"index\":%d,\"gid\":%u", i, groups[i]);
    if (guest && !setup_uart()) goto finish;
    active_phase = "BLOCKED_READ";
    if (!start_child(mcexec, payload) || !prepare_read()) goto cleanup;
    if (guest && !capture("PRE_INPUT")) goto cleanup;
    active_phase = "INPUT";
    if (!release_input()) goto cleanup;
    active_phase = "OBSERVE_RET";
    if (guest && !observe_return()) goto cleanup;
    if (guest) {
        if (!capture("POST_RET")) goto cleanup;
        post_ack_ns = now_ns();
    }
    if (terminal_mode) {
        active_phase = "QUIET_INTERVAL";
        uint64_t quiet_until = post_ack_ns + UINT64_C(5000) * NS_PER_MS;
        while (now_ns() < quiet_until && before(overall_deadline)) pump(5);
        if (failed || !capture("QUIET")) goto cleanup;
        quiet_ack_ns = now_ns();
    } else {
        active_phase = "NORMAL_COMPLETION";
        uint64_t deadline = input_ns + UINT64_C(15000) * NS_PER_MS;
        if (deadline > overall_deadline) deadline = overall_deadline;
        while ((!launcher_done || !streams[0].eof || !streams[1].eof) && before(deadline)) pump(5);
        if (now_ns() >= deadline && !failed) fail("late-normal-completion", ETIMEDOUT);
    }
cleanup:
    if (failed) emergency_capture();
    active_phase = "OWNED_CLEANUP";
    if (launcher > 0) cleanup_owned();
    if (!failed && !terminal_mode) {
        if (launcher_kill_sent || !launcher_reaped || !WIFEXITED(raw_wait) || WEXITSTATUS(raw_wait) != 37 ||
            streams[0].sink.stored != sizeof complete - 1 || memcmp(streams[0].bytes, complete, sizeof complete - 1) ||
            streams[1].sink.stored != 0 || !streams[0].eof || !streams[1].eof) fail("normal-byte-and-raw-exit-oracle", EPROTO);
    }
    active_phase = "NEW_ADMISSION";
    if (!failed && terminal_mode) probe_admission();
finish:
    if (failed) emergency_capture();
    event("\"event\":\"collection-finish\",\"collection_status\":\"%s\",\"failure\":\"%s\",\"errno\":%d,\"application_acceptance\":false,\"transport_acceptance\":false",
          failed ? "FAIL" : "COMPLETE", first_failure, first_errno);
    write_report();
    return failed ? 1 : 0;
}
