/* SPDX-License-Identifier: GPL-2.0-only
 * Separate PID-1 lifecycle diagnostic collector, not a general-purpose init.
 * The host-only tests include this exact supervisor and serializer.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/klog.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#if defined(ND_FUTEX)
#define STREAM_LIMIT 4096u
#define FRAME_LIMIT 8192u
#else
#define STREAM_LIMIT 1024u
#define FRAME_LIMIT 4096u
#endif
/* This variant retains the original simple argv payload and host byte oracle.
 * Broader payload profiles require a separately reviewed lifecycle contract. */
#if !defined(ND_CORE_THREADS) || defined(ND_FUTEX) || defined(ND_CORE_MEMORY) || defined(ND_CORE_FILES) || defined(ND_CORE_SIGNALS)
#error "this private lifecycle composition requires the unchanged typed AVX threads argv"
#endif
#define MS 1000000ull
#define COLLECTOR_SECONDS 120u
/* native-boot contains two mandatory ten-second capture_pause calls. Allow
 * forty additional seconds for startup/service work, without lengthening
 * ordinary module helpers. The shared outer budget includes every phase. */
#define BOOT_TIMEOUT_MS 60000u
#define HELPER_TIMEOUT_MS 10000u
static uint64_t collector_deadline;
struct stream {
    unsigned char data[4096];
    size_t limit;
    size_t kept;
    uint64_t observed, eof_ns;
    int eof;
};
struct result {
    pid_t pid;
    struct stream out, err;
    int status, fault, timeout, clean;
    int child_stage, child_errno;
    uint64_t started, reaped, finished;
};
struct child_fault { int stage, number; };
#if defined(ND_CORE_CASE)
#error "ND_CORE_CASE is obsolete; use one ND_CORE_* presence flag"
#endif
#if (defined(ND_CORE_MEMORY) + defined(ND_CORE_FILES) + \
     defined(ND_CORE_THREADS) + defined(ND_CORE_SIGNALS)) > 1
#error "select at most one ND_CORE_* profile"
#endif
#if defined(ND_FUTEX) && (defined(ND_CORE_MEMORY) || defined(ND_CORE_FILES) || \
                          defined(ND_CORE_THREADS) || defined(ND_CORE_SIGNALS))
#error "ND_FUTEX is mutually exclusive with ND_CORE_* profiles"
#endif
#if defined(ND_CORE_MEMORY)
static const char nd_core_case[] = "memory";
#elif defined(ND_CORE_FILES)
static const char nd_core_case[] = "files";
#elif defined(ND_CORE_THREADS)
static const char nd_core_case[] = "threads";
#elif defined(ND_CORE_SIGNALS)
static const char nd_core_case[] = "signals";
#endif
#if defined(ND_CORE_MEMORY) || defined(ND_CORE_FILES) || \
    defined(ND_CORE_THREADS) || defined(ND_CORE_SIGNALS)
static char *const payload_argv[] = {
    "/bin/mcexec", "-t", "1", "0", "app", (char *)nd_core_case, NULL
};
#elif defined(ND_FUTEX)
static char *const payload_argv[] = {
    "/bin/mcexec", "-t", "1", "0", "/apps/app", NULL
};
#else
static char *const payload_argv[] = {
    "/bin/mcexec", "-t", "1", "0", "app", "A", "", "B", NULL
};
#endif
static char *const payload_env[] = {"PATH=/usr/bin:/bin", "COKERNEL_PATH=/apps", NULL};
static char *const helper_env[] = {"PATH=/bin:/sbin:/usr/bin:/usr/sbin", "LC_ALL=C", NULL};
#if defined(ND_FUTEX) || defined(ND_CORE_THREADS)
static char *const futex_boot_argv[] = {
    "/bin/native-boot", "hidos", "allow_oversubscribe", NULL
};
#endif

static uint64_t now_ns(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return 0;
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}

static unsigned helper_timeout_ms(const char *path)
{
    return !strcmp(path, "/bin/native-boot") ? BOOT_TIMEOUT_MS : HELPER_TIMEOUT_MS;
}

static uint64_t bounded_deadline(uint64_t deadline, uint64_t reserve)
{
    if (collector_deadline && deadline > collector_deadline - reserve)
        return collector_deadline - reserve;
    return deadline;
}

static void outer_expired(int number)
{
    (void)number;
    /* End all collection/publication at the outer limit, even if a setup or
     * filesystem syscall stalls. PID1 remains alive; the host's independently
     * bounded QEMU owner must reject missing shutdown and retire the guest.
     * No fallback poweroff can convert this incomplete run into acceptance. */
    for (;;) pause();
}

/* Promote each end above stdio before any dup2. All six pipe ends are
 * distinct even when descriptors 0, 1, or 2 were closed by the caller. */
static int make_pipe(int p[2])
{
    if (pipe2(p, O_CLOEXEC)) return -1;
    for (int i = 0; i != 2; ++i) {
        if (p[i] < 3) {
            int n = fcntl(p[i], F_DUPFD_CLOEXEC, 3);
            if (n < 0) { close(p[0]); close(p[1]); return -1; }
            close(p[i]); p[i] = n;
        }
    }
    int flags = fcntl(p[0], F_GETFL);
    if (flags < 0 || fcntl(p[0], F_SETFL, flags | O_NONBLOCK)) {
        close(p[0]); close(p[1]); return -1;
    }
    return 0;
}

static void child_abort(int fd, int stage)
{
    struct child_fault f = {stage, errno};
    ssize_t n;
    do { n = write(fd, &f, sizeof f); } while (n < 0 && errno == EINTR);
    _exit(126);
}

/* At most four reads per stream per turn: an infinite writer cannot starve
 * its peer, wait observation, or the monotonic deadline. */
static int drain(int fd, struct stream *s, uint64_t deadline)
{
    unsigned char b[512];
    for (int i = 0; i != 4 && !s->eof; ++i) {
        uint64_t now = now_ns();
        if (!now) return -1;
        if (now >= deadline) break;
        ssize_t n = read(fd, b, sizeof b);
        if (n > 0) {
            size_t keep = (size_t)n;
            if (keep > s->limit - s->kept) keep = s->limit - s->kept;
            memcpy(s->data + s->kept, b, keep); s->kept += keep;
            if (UINT64_MAX - s->observed < (uint64_t)n) return -1;
            s->observed += (uint64_t)n;
        } else if (!n) { s->eof = 1; s->eof_ns = now_ns(); }
        else if (errno == EAGAIN || errno == EWOULDBLOCK) break;
        else if (errno != EINTR) return -1;
    }
    return 0;
}

static int signal_owned(pid_t p, int sig)
{
    /* The unreaped leader pins the process-group number through the last
     * signal. Direct signal also covers an early setpgid/setup failure. */
    int bad = 0;
    if (kill(-p, sig) && errno != ESRCH) bad = 1;
    if (kill(p, sig) && errno != ESRCH) bad = 1;
    return bad ? -1 : 0;
}

static void supervise(const char *path, char *const av[], char *const env[],
                      const char *cwd, unsigned timeout_ms, struct result *r)
{
    int pipes[3][2] = {{-1,-1},{-1,-1},{-1,-1}};
    pid_t child = -1;
    unsigned char setup[sizeof(struct child_fault) + 1];
    size_t setup_n = 0;
    int setup_eof = 0, stopping = 0, killed = 0, leader_ready = 0;
    uint64_t stop_at = 0, limit;
    memset(r, 0, sizeof *r); r->status = -1;
    r->out.limit = r->err.limit = !strcmp(path, "/bin/native-resource-release-probe") ? 4096 : STREAM_LIMIT;
    r->started = now_ns();
    if (!r->started) { r->fault = 1; goto done; }
    limit = r->started + (uint64_t)timeout_ms * MS;
    limit = bounded_deadline(limit, 2000 * MS); /* Reserve TERM/KILL/reap time. */
    if (limit <= r->started) { r->fault = r->timeout = 1; goto done; }
    for (int i = 0; i != 3; ++i) {
        if (make_pipe(pipes[i])) { r->fault = 1; goto done; }
    }
    child = fork();
    if (child < 0) { r->fault = 1; goto done; }
    if (child > 0) r->pid = child;
    if (!child) {
        if (setpgid(0, 0)) child_abort(pipes[2][1], 1);
        if (dup2(pipes[0][1], 1) < 0 || dup2(pipes[1][1], 2) < 0)
            child_abort(pipes[2][1], 2);
        for (int i = 0; i != 3; ++i) {
            close(pipes[i][0]);
            if (i != 2) close(pipes[i][1]);
        }
        int nullfd = open("/dev/null", O_RDONLY | O_CLOEXEC);
        if (nullfd < 0 || dup2(nullfd, 0) < 0) child_abort(pipes[2][1], 3);
        if (nullfd != 0) close(nullfd);
        else if (fcntl(0, F_SETFD, 0)) child_abort(pipes[2][1], 3);
        if (cwd && chdir(cwd)) child_abort(pipes[2][1], 4);
        execve(path, av, env);
        child_abort(pipes[2][1], 5);
    }
    for (int i = 0; i != 3; ++i) { close(pipes[i][1]); pipes[i][1] = -1; }
    if (setpgid(child, child) && errno != EACCES && errno != ESRCH) r->fault = 1;
    for (;;) {
        uint64_t now = now_ns();
        if (!now) {
            r->fault = 1;
            /* A failed clock cannot support further timed supervision.
             * Stop the pinned group immediately and report uncertain reap. */
            (void)signal_owned(child, SIGKILL);
            break;
        }
        if (!leader_ready) {
            siginfo_t si; memset(&si, 0, sizeof si);
            if (waitid(P_PID, child, &si, WEXITED | WNOHANG | WNOWAIT)) {
                if (errno != EINTR) r->fault = 1;
            } else leader_ready = si.si_pid == child;
        }
        if (!stopping && (leader_ready || now >= limit || r->fault)) {
            r->timeout = !leader_ready && now >= limit;
            stopping = 1; stop_at = now;
            if (signal_owned(child, SIGTERM)) r->fault = 1;
        }
        if (stopping && !killed && now - stop_at >= 100 * MS) {
            if (signal_owned(child, SIGKILL)) r->fault = 1;
            killed = 1;
        }
        if (stopping && now - stop_at >= 2000 * MS) { r->fault = 1; break; }
        uint64_t drain_end = stopping ? stop_at + 2000 * MS : limit;
        if (drain(pipes[0][0], &r->out, drain_end) ||
            drain(pipes[1][0], &r->err, drain_end)) r->fault = 1;
        if (!setup_eof) {
            ssize_t n = read(pipes[2][0], setup + setup_n, sizeof setup - setup_n);
            if (n > 0) { setup_n += (size_t)n; if (setup_n == sizeof setup) r->fault = 1; }
            else if (!n) setup_eof = 1;
            else if (errno != EAGAIN && errno != EINTR) r->fault = 1;
        }
        /* No process-group signalling after this point: the leader may now
         * be reaped. PID1 (or the test subreaper) owns orphan descendants. */
        if (killed) {
            pid_t p; int status;
            while ((p = waitpid(-1, &status, WNOHANG)) > 0) {
                if (p == child) { r->status = status; r->reaped = now_ns(); }
            }
            if (p < 0 && errno == ECHILD) r->clean = 1;
            else if (p < 0 && errno != EINTR) r->fault = 1;
            if (r->clean && r->out.eof && r->err.eof && setup_eof) break;
        }
        struct pollfd pf[3];
        for (int i = 0; i != 3; ++i) pf[i] = (struct pollfd){pipes[i][0], POLLIN, 0};
        if (poll(pf, 3, 5) < 0 && errno != EINTR) r->fault = 1;
    }
    if (setup_n == sizeof(struct child_fault)) {
        struct child_fault f; memcpy(&f, setup, sizeof f);
        r->child_stage = f.stage; r->child_errno = f.number; r->fault = 1;
    } else if (setup_n || !setup_eof) r->fault = 1;
done:
    for (int i = 0; i != 3; ++i) for (int j = 0; j != 2; ++j)
        if (pipes[i][j] >= 0) close(pipes[i][j]);
    r->finished = now_ns();
}

static int retired_at(const char *path)
{
    DIR *d = opendir(path);
    if (!d) return -1; /* A missing/unreadable procfs is not retirement. */
    struct dirent *e; int empty = 1;
    errno = 0;
    while ((e = readdir(d))) {
        if (e->d_name[0] >= '0' && e->d_name[0] <= '9') empty = 0;
    }
    if (errno) empty = -1;
    if (closedir(d)) empty = -1;
    return empty;
}

static int append(char *b, size_t *n, const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt);
    int z = vsnprintf(b + *n, FRAME_LIMIT - *n, fmt, ap); va_end(ap);
    if (z < 0 || (size_t)z >= FRAME_LIMIT - *n) return -1;
    *n += (size_t)z; return 0;
}

static int stream_json(char *b, size_t *n, const struct stream *s)
{
    char h[STREAM_LIMIT * 2 + 1];
    const char *hex = "0123456789abcdef";
    for (size_t i = 0; i != s->kept; ++i) {
        h[2*i] = hex[s->data[i] >> 4]; h[2*i+1] = hex[s->data[i] & 15];
    }
    h[2*s->kept] = 0;
    return append(b, n, "{\"hex\":\"%s\",\"eof\":%s,\"truncated\":%s,"
                  "\"observed\":%llu,\"retained\":%zu,\"discarded\":%llu,"
                  "\"limit\":%zu,\"eof_ns\":%llu}", h, s->eof ? "true" : "false",
                  s->observed != s->kept ? "true" : "false",
                  (unsigned long long)s->observed, s->kept,
                  (unsigned long long)(s->observed - s->kept), s->limit,
                  (unsigned long long)s->eof_ns);
}

static int frame(char *b, const struct result *r, int empty)
{
    size_t n = 0;
#if defined(ND_CORE_MEMORY) || defined(ND_CORE_FILES) || \
    defined(ND_CORE_THREADS) || defined(ND_CORE_SIGNALS)
    const char *const argv_case = nd_core_case;
    if (append(b, &n, "ND_PAYLOAD {\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\","
               "\"app\",\"%s\"],\"cwd\":\"/case/work\","
               "\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"},"
               "\"raw_wait_status\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,"
               "\"finished_ns\":%llu,\"streams\":{\"stdout\":", argv_case, r->status,
               (unsigned long long)r->started, (unsigned long long)r->reaped,
               (unsigned long long)r->finished) ||
#elif defined(ND_FUTEX)
    if (append(b, &n, "ND_PAYLOAD {\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\",\"/apps/app\"],\"cwd\":\"/case/work\","
               "\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"},"
               "\"raw_wait_status\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,"
               "\"finished_ns\":%llu,\"streams\":{\"stdout\":", r->status,
               (unsigned long long)r->started, (unsigned long long)r->reaped,
               (unsigned long long)r->finished) ||
#else
    if (append(b, &n, "ND_PAYLOAD {\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\","
               "\"app\",\"A\",\"\",\"B\"],\"cwd\":\"/case/work\","
               "\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"},"
               "\"raw_wait_status\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,"
               "\"finished_ns\":%llu,\"streams\":{\"stdout\":", r->status,
               (unsigned long long)r->started, (unsigned long long)r->reaped,
               (unsigned long long)r->finished) ||
#endif
        stream_json(b, &n, &r->out) || append(b, &n, ",\"stderr\":") ||
        stream_json(b, &n, &r->err) ||
        append(b, &n, "},\"procfs_empty\":%s}\n",
               empty && r->clean && !r->fault && !r->timeout ? "true" : "false")) return -1;
    return (int)n;
}

static int write_all(int fd, const void *data, size_t len);

/* One attempted record write. The ordinary profiles remain a single
 * PIPE_BUF-sized atomic write; the futex profile is larger and uses the
 * bounded write_all path below. In the guest, all children have been reaped,
 * their outputs were piped, and printk console output is suppressed; this is
 * the sole userspace console writer. */
static int publish(int fd, const struct result *r, int empty)
{
    char b[FRAME_LIMIT];
    int n = frame(b, r, empty);
    if (n < 0) {
        struct result failed = *r;
        failed.fault = 1; failed.out.kept = 0; failed.err.kept = 0;
        n = frame(b, &failed, 0);
    }
#if defined(ND_FUTEX)
    if (n <= 0 || (unsigned)n > FRAME_LIMIT) return -1;
    return write_all(fd, b, (size_t)n);
#else
    if (n <= 0 || n > (int)PIPE_BUF) return -1;
    ssize_t written;
    do { written = write(fd, b, (size_t)n); } while (written < 0 && errno == EINTR);
    return written == n ? 0 : -1;
#endif
}

static int write_all(int fd, const void *data, size_t len)
{
    const unsigned char *p = data;
    uint64_t start = now_ns();
    if (!start) return -1;
    uint64_t deadline = bounded_deadline(start + 2000 * MS, 0);
    while (len) {
        uint64_t current = now_ns();
        if (!current || current >= deadline) break;
        ssize_t n = write(fd, p, len);
        if (n > 0) { p += n; len -= (size_t)n; }
        else if (n < 0 && (errno == EINTR || errno == EAGAIN)) {
            struct pollfd f = {fd, POLLOUT, 0};
            if (poll(&f, 1, 5) < 0 && errno != EINTR) return -1;
        } else return -1;
    }
    return len ? -1 : 0;
}

static int save_file(const char *path, const void *p, size_t n)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) return -1;
    int bad = write_all(fd, p, n);
    if (close(fd)) bad = -1;
    return bad;
}

static int helper_capture(const char *tag, const char *path, char *const av[],
                          int *safe, struct result *captured)
{
    struct result r; char name[128], record[256];
    supervise(path, av, helper_env, NULL, helper_timeout_ms(path), &r);
    if (!r.clean) *safe = 0;
    int bad = r.fault || r.timeout || !r.clean || r.status != 0 ||
              !r.out.eof || !r.err.eof || r.out.observed != r.out.kept ||
              r.err.observed != r.err.kept;
    if (!strcmp(tag, "boot")) {
        int log_n = snprintf(record, sizeof record,
                "<6>NATIVE_BOOT_HELPER raw_wait_status=%d fault=%d timeout=%d clean=%d child_stage=%d child_errno=%d\n",
                r.status, r.fault, r.timeout, r.clean, r.child_stage, r.child_errno);
        int log_fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
        if (log_fd < 0) bad = 1;
        else {
            if (log_n <= 0 || (size_t)log_n >= sizeof record ||
                write_all(log_fd, record, (size_t)log_n)) bad = 1;
            if (close(log_fd)) bad = 1;
        }
    }
    snprintf(name, sizeof name, "/case/evidence/%s.stdout", tag);
    if (save_file(name, r.out.data, r.out.kept)) bad = 1;
    snprintf(name, sizeof name, "/case/evidence/%s.stderr", tag);
    if (save_file(name, r.err.data, r.err.kept)) bad = 1;
    int n = snprintf(record, sizeof record, "status=%d fault=%d timeout=%d clean=%d stage=%d errno=%d\n",
                     r.status, r.fault, r.timeout, r.clean, r.child_stage, r.child_errno);
    snprintf(name, sizeof name, "/case/evidence/%s.status", tag);
    if (n < 0 || (size_t)n >= sizeof record || save_file(name, record, (size_t)n)) bad = 1;
    if (captured) *captured = r;
    return bad ? -1 : 0;
}

static int helper(const char *tag, const char *path, char *const av[], int *safe)
{
    return helper_capture(tag, path, av, safe, NULL);
}

/* A transport-complete successful payload and empty procfs permit the probe.
 * Payload stdout/stderr bytes still require the unchanged host oracle. */
static int lifecycle_after_payload(const struct result *payload, int good,
                                   int *safe, int empty, int *attempted,
                                   struct result *capture)
{
    *attempted = 0;
    if (!good || !*safe || empty != 1 || !payload->clean || payload->fault ||
        payload->timeout || payload->status != 0 || !payload->out.eof ||
        !payload->err.eof || payload->out.observed != payload->out.kept ||
        payload->err.observed != payload->err.kept)
        return -1;
    *attempted = 1;
    /* The frozen probe accepts decimal minor0, constructing /dev/mcos0 itself. */
    return helper_capture("lifecycle", "/bin/native-lifecycle-probe",
                          (char *const[]){"/bin/native-lifecycle-probe", "0", NULL},
                          safe, capture);
}

/* Three bounded records export the exact captured helper result and bytes.
 * Each stream record fits PIPE_BUF at STREAM_LIMIT1024. A missing, partial or
 * duplicate record must fail the separately reviewed host lifecycle oracle;
 * ND_PAYLOAD retains its existing schema and independent payload oracle. */
static int publish_lifecycle_stream(int console, const char *name,
                                    const struct stream *stream, int final_phase)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    const char *prefix=final_phase ? "ND_FINAL_LIFECYCLE_STREAM" : "ND_LIFECYCLE_STREAM";
    if (append(b, &n, "%s {\"name\":\"%s\",\"capture\":", prefix, name) ||
        stream_json(b, &n, stream) || append(b, &n, "}\n") || n > PIPE_BUF)
        return -1;
    return write_all(console, b, n);
}

static int publish_lifecycle(int console, const struct result *r, int helper_rc, int final_phase)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    const char *prefix=final_phase ? "ND_FINAL_LIFECYCLE" : "ND_LIFECYCLE";
    if (append(b, &n, "%s {\"argv\":[\"/bin/native-lifecycle-probe\",\"0\"],"
               "\"helper_result\":%d,\"raw_wait_status\":%d,\"fault\":%d,"
               "\"timeout\":%d,\"clean\":%d,\"child_stage\":%d,\"child_errno\":%d,"
               "\"started_ns\":%llu,\"reaped_ns\":%llu,\"finished_ns\":%llu}\n",
               prefix, helper_rc, r->status, r->fault, r->timeout, r->clean,
               r->child_stage, r->child_errno, (unsigned long long)r->started,
               (unsigned long long)r->reaped, (unsigned long long)r->finished) ||
        n > PIPE_BUF || write_all(console, b, n) ||
        publish_lifecycle_stream(console, "stdout", &r->out, final_phase) ||
        publish_lifecycle_stream(console, "stderr", &r->err, final_phase))
        return -1;
    return 0;
}

/* Case-specific destructive guest helper admission. Exact payload and strict
 * lifecycle success are required before the first resource ioctl can occur. */
/* Admission mirrors the frozen typed parser4bb20 grammar and capability gates.
 * Dynamic feature fields remain observed; no accepted-capture bytes are an oracle.
 * Host still applies unchanged typed parser, lifecycle and resource consumers. */
static int typed_avx_stdout(const unsigned char *data, size_t count)
{
    static const char *const labels[] = {
        "ENABLED_CPUID1 ecx=", " edx=", "\nENABLED_XCR0 hi=", " lo=",
        "\nENABLED_CPUIDD0 eax=", " ebx=", " ecx=", " edx=",
        "\nENABLED_CPUID7 ebx=", " ecx=", " edx=",
        "\nENABLED_AUXV hwcap=", " hwcap2="
    };
    static const char suffix[] =
        "\nENABLED_REQUIRED_XCR0=0000000000000007\n"
        "ENABLED_SYSCALL_PASS\nENABLED_FUTEX_PASS\n"
        "ENABLED_SIGNAL_PASS\nENABLED_PROFILE_PASS\n";
    uint64_t values[13]; size_t cursor=0;
    if (count != 380) return 0;
    for (size_t field=0; field<13; ++field) {
        size_t length=strlen(labels[field]), width=field<11 ? 8 : 16;
        if (cursor+length+width > count || memcmp(data+cursor,labels[field],length))
            return 0;
        cursor+=length; values[field]=0;
        for (size_t digit=0; digit<width; ++digit) {
            unsigned char ch=data[cursor++]; unsigned int n;
            if (ch>='0' && ch<='9') n=ch-'0';
            else if (ch>='a' && ch<='f') n=ch-'a'+10;
            else return 0;
            values[field]=(values[field]<<4)|n;
        }
    }
    if (count-cursor != sizeof suffix-1 || memcmp(data+cursor,suffix,sizeof suffix-1))
        return 0;
    uint64_t xcr0=(values[2]<<32)|values[3];
    uint64_t supported=values[4]|(values[7]<<32);
    return (values[0]&0x1c000000u)==0x1c000000u && (xcr0&7)==7 &&
        !(xcr0&~supported) && values[5]>=832 && values[5]<=values[6];
}

static int resource_prerequisites(const struct result *payload,
                                  const struct result *lifecycle, int good,
                                  int safe, int lifecycle_rc)
{
    if (!good || !safe || lifecycle_rc || payload->fault || payload->timeout ||
        !payload->clean || payload->status || !payload->out.eof ||
        !payload->err.eof || payload->out.observed != 380 ||
        payload->out.kept != 380 || payload->err.observed ||
        !typed_avx_stdout(payload->out.data, payload->out.kept) ||
        lifecycle->fault || lifecycle->timeout || !lifecycle->clean ||
        lifecycle->status || !lifecycle->out.eof || !lifecycle->err.eof ||
        lifecycle->out.observed != lifecycle->out.kept || lifecycle->err.observed)
        return 0;
    int descriptor = -1, consumed = 0;
    char text[1025], expected[1025];
    if (lifecycle->out.kept >= sizeof text) return 0;
    memcpy(text, lifecycle->out.data, lifecycle->out.kept);
    text[lifecycle->out.kept] = 0;
    if (sscanf(text, "{\"operation\":\"open\",\"request\":0,\"return\":%d,%n",
               &descriptor, &consumed) != 1 || consumed <= 0 || descriptor < 0)
        return 0;
    int n = snprintf(expected, sizeof expected,
        "{\"operation\":\"open\",\"request\":0,\"return\":%d,\"errno\":0,\"linux_result\":%d}\n"
        "{\"operation\":\"status_before\",\"request\":1124867,\"return\":5,\"errno\":0,\"linux_result\":5}\n"
        "{\"operation\":\"shutdown\",\"request\":1124866,\"return\":0,\"errno\":0,\"linux_result\":0}\n"
        "{\"operation\":\"status_after\",\"request\":1124867,\"return\":0,\"errno\":0,\"linux_result\":0}\n"
        "{\"operation\":\"close\",\"request\":0,\"return\":0,\"errno\":0,\"linux_result\":0}\n"
        "{\"result\":\"PASS\",\"transition_observed\":true,\"resource_restoration_verified\":false}\n",
        descriptor, descriptor);
    return n > 0 && (size_t)n == lifecycle->out.kept &&
           (size_t)n < sizeof expected && !memcmp(text, expected, (size_t)n);
}

static int resource_after_lifecycle(const struct result *payload,
                                  const struct result *lifecycle, int good,
                                  int *safe, int lifecycle_rc, int *attempted,
                                  struct result *captured)
{
    *attempted = 0;
    if (!resource_prerequisites(payload, lifecycle, good, *safe, lifecycle_rc))
        return -1;
    *attempted = 1;
    return helper_capture("resource-release", "/bin/native-resource-release-probe",
        (char *const[]){"/bin/native-resource-release-probe", NULL}, safe, captured);
}

/* Complete 4096-byte streams are serialized as ordered 512-byte hex chunks.
 * Every record remains below PIPE_BUF. Missing records fail the host decoder. */
static int publish_resource_stream(int console, const char *name,
                                   const struct stream *s, int final_phase)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    const char *prefix=final_phase ? "ND_FINAL_RESOURCE_STREAM" : "ND_RESOURCE_STREAM";
    const char *chunk=final_phase ? "ND_FINAL_RESOURCE_CHUNK" : "ND_RESOURCE_CHUNK";
    if (append(b, &n, "%s {\"name\":\"%s\",\"eof\":%s,"
        "\"observed\":%llu,\"retained\":%zu,\"discarded\":%llu,\"limit\":%zu,"
        "\"eof_ns\":%llu}\n", prefix, name, s->eof ? "true" : "false",
        (unsigned long long)s->observed, s->kept,
        (unsigned long long)(s->observed - s->kept), s->limit,
        (unsigned long long)s->eof_ns) || n > PIPE_BUF || write_all(console, b, n))
        return -1;
    for (size_t offset = 0; offset < s->kept; offset += 512) {
        size_t count = s->kept - offset;
        if (count > 512) count = 512;
        char hex[1025]; const char *digits = "0123456789abcdef";
        for (size_t i = 0; i < count; ++i) {
            hex[2*i] = digits[s->data[offset+i] >> 4];
            hex[2*i+1] = digits[s->data[offset+i] & 15];
        }
        hex[2*count] = 0; n = 0;
        if (append(b, &n, "%s {\"name\":\"%s\",\"offset\":%zu,\"hex\":\"%s\"}\n",
                   chunk, name, offset, hex) || n > PIPE_BUF || write_all(console, b, n))
            return -1;
    }
    return 0;
}

static int publish_resource(int console, const struct result *r, int rc, int final_phase)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    const char *prefix=final_phase ? "ND_FINAL_RESOURCE" : "ND_RESOURCE";
    if (append(b, &n, "%s {\"argv\":[\"/bin/native-resource-release-probe\"],"
        "\"helper_result\":%d,\"raw_wait_status\":%d,\"fault\":%d,\"timeout\":%d,"
        "\"clean\":%d,\"child_stage\":%d,\"child_errno\":%d,\"started_ns\":%llu,"
        "\"reaped_ns\":%llu,\"finished_ns\":%llu}\n", prefix, rc, r->status,
        r->fault, r->timeout, r->clean, r->child_stage, r->child_errno,
        (unsigned long long)r->started, (unsigned long long)r->reaped,
        (unsigned long long)r->finished) || n > PIPE_BUF || write_all(console, b, n) ||
        publish_resource_stream(console, "stdout", &r->out, final_phase) ||
        publish_resource_stream(console, "stderr", &r->err, final_phase)) return -1;
    return 0;
}

#define REBOOT_LOG_LIMIT 262144u
struct reboot_capture {
    struct result boot;
    unsigned char before[REBOOT_LOG_LIMIT], after[REBOOT_LOG_LIMIT];
    int before_n, after_n, before_errno, after_errno;
    int boot_attempted, helper_rc;
    uint64_t resource_finished;
};

static int reboot_snapshot(const char *name, unsigned char *bytes,
                            int *count, int *error)
{
    errno = 0;
    *count = klogctl(3, (char *)bytes, REBOOT_LOG_LIMIT);
    *error = errno;
    if (*count < 0 || *count > (int)REBOOT_LOG_LIMIT) return -1;
    int bad = *count == (int)REBOOT_LOG_LIMIT;
    if (save_file(name, bytes, (size_t)*count)) bad = 1;
    return bad ? -1 : 0;
}

static int reboot_after_resource(const struct result *resource, int resource_rc,
                                 int good, int *safe, int *attempted,
                                 struct reboot_capture *r)
{
    *attempted = 0;
    memset(r, 0, sizeof *r);
    r->boot.status = r->helper_rc = r->before_n = r->after_n = -1;
    if (!good || !*safe || resource_rc || resource->status || resource->fault ||
        resource->timeout || !resource->clean || !resource->out.eof ||
        !resource->err.eof || resource->out.observed != resource->out.kept ||
        resource->err.observed != resource->err.kept)
        return -1;
    *attempted = 1;
    r->resource_finished = resource->finished;
    if (reboot_snapshot("/case/evidence/reboot-before.kmsg", r->before,
                        &r->before_n, &r->before_errno)) return -1;
    r->boot_attempted = 1;
    r->helper_rc = helper_capture("second-boot", "/bin/native-boot",
        (char *const[]){"/bin/native-boot", NULL}, safe, &r->boot);
    /* Retain the failed helper's new log too; never retry or recycle markers. */
    int log_rc = reboot_snapshot("/case/evidence/reboot-after.kmsg", r->after,
                                &r->after_n, &r->after_errno);
    return r->helper_rc || log_rc ? -1 : 0;
}

static int reboot_chunks(int console, const char *name,
                          const unsigned char *bytes, size_t size)
{
    for (size_t offset = 0; offset < size; offset += 512) {
        size_t count = size - offset;
        if (count > 512) count = 512;
        char hex[1025], b[FRAME_LIMIT]; size_t n = 0;
        const char *digits = "0123456789abcdef";
        for (size_t i = 0; i < count; ++i) {
            hex[2*i] = digits[bytes[offset+i] >> 4];
            hex[2*i+1] = digits[bytes[offset+i] & 15];
        }
        hex[2*count] = 0;
        if (append(b, &n, "ND_REBOOT_CHUNK {\"name\":\"%s\",\"offset\":%zu,\"hex\":\"%s\"}\n",
                   name, offset, hex) || n > PIPE_BUF || write_all(console, b, n))
            return -1;
    }
    return 0;
}

static int reboot_stream(int console, const char *name, const struct stream *s)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    if (append(b, &n, "ND_REBOOT_STREAM {\"name\":\"%s\",\"eof\":%s,"
        "\"observed\":%llu,\"retained\":%zu,\"discarded\":%llu,\"limit\":%zu,"
        "\"eof_ns\":%llu}\n", name, s->eof ? "true" : "false",
        (unsigned long long)s->observed, s->kept,
        (unsigned long long)(s->observed - s->kept), s->limit,
        (unsigned long long)s->eof_ns) || n > PIPE_BUF || write_all(console, b, n))
        return -1;
    return reboot_chunks(console, name, s->data, s->kept);
}

static int reboot_log(int console, const char *name,
                       const unsigned char *bytes, int count, int error)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    if (append(b, &n, "ND_REBOOT_LOG {\"name\":\"%s\",\"count\":%d,\"errno\":%d,\"limit\":%u}\n",
               name, count, error, REBOOT_LOG_LIMIT) || n > PIPE_BUF ||
        write_all(console, b, n)) return -1;
    if (count < 0 || count > (int)REBOOT_LOG_LIMIT) return 0;
    return reboot_chunks(console, name, bytes, (size_t)count);
}

static int publish_reboot(int console, const struct reboot_capture *r, int rc)
{
    const struct result *b = &r->boot;
    char line[FRAME_LIMIT]; size_t n = 0;
    if (append(line, &n, "ND_REBOOT {\"argv\":[\"/bin/native-boot\"],"
        "\"result\":%d,\"boot_attempted\":%d,\"helper_result\":%d,"
        "\"raw_wait_status\":%d,\"fault\":%d,\"timeout\":%d,\"clean\":%d,"
        "\"child_stage\":%d,\"child_errno\":%d,\"resource_finished_ns\":%llu,"
        "\"started_ns\":%llu,\"reaped_ns\":%llu,\"finished_ns\":%llu}\n",
        rc, r->boot_attempted, r->helper_rc, b->status, b->fault, b->timeout,
        b->clean, b->child_stage, b->child_errno,
        (unsigned long long)r->resource_finished, (unsigned long long)b->started,
        (unsigned long long)b->reaped, (unsigned long long)b->finished) ||
        n > PIPE_BUF || write_all(console, line, n) ||
        reboot_stream(console, "stdout", &b->out) ||
        reboot_stream(console, "stderr", &b->err) ||
        reboot_log(console, "before", r->before, r->before_n, r->before_errno) ||
        reboot_log(console, "after", r->after, r->after_n, r->after_errno))
        return -1;
    return 0;
}

/* No second-generation application is launched. Stop only after successful
 * reboot, transport-complete helper retirement and genuinely empty procfs. */
static int final_lifecycle_after_reboot(const struct reboot_capture *reboot,
    int reboot_rc, int good, int *safe, int *attempted, struct result *capture)
{
    const struct result *r=&reboot->boot;
    *attempted=0;
    if (!good || !*safe || reboot_rc || !reboot->boot_attempted || reboot->helper_rc ||
        r->status || r->fault || r->timeout || !r->clean || !r->out.eof ||
        !r->err.eof || r->out.observed!=r->out.kept || r->err.observed ||
        retired_at("/proc/mcos0")!=1) return -1;
    *attempted=1;
    return helper_capture("final-lifecycle", "/bin/native-lifecycle-probe",
        (char *const[]){"/bin/native-lifecycle-probe","0",NULL},safe,capture);
}

static int final_resource_after_lifecycle(const struct result *payload,
    const struct result *lifecycle, int lifecycle_rc, int good, int *safe,
    int *attempted, struct result *capture)
{
    *attempted=0;
    if (!resource_prerequisites(payload,lifecycle,good,*safe,lifecycle_rc)) return -1;
    *attempted=1;
    return helper_capture("final-resource-release", "/bin/native-resource-release-probe",
        (char *const[]){"/bin/native-resource-release-probe",NULL},safe,capture);
}

static int mount_one(const char *type, const char *path)
{
    /* PID1's initramfs owns these mounts; EBUSY is not blindly accepted. */
    return mount(type, path, type, 0, NULL);
}

static void remain_pid1(void)
{
    for (;;) { struct timespec t = {1, 0}; nanosleep(&t, NULL); }
}

static void poweroff_forever(int console)
{
    struct result r;
    supervise("/poweroff", (char *const[]){"/poweroff", NULL}, helper_env, NULL, 2000, &r);
    /* Successful guest poweroff does not return. Any return (even status 0)
     * invalidates the preceding report through the existing failure scanner. */
    const char message[] = "native diagnostic teardown error: poweroff returned\n";
    if (console >= 0) (void)write_all(console, message, sizeof message - 1);
    /* Remain alive so host QMP shutdown cannot falsely accept a failed
     * poweroff even if its diagnostic console write was lost. */
    remain_pid1();
}

static int fp_debug_enable(void)
{
    static const char path[] = "/sys/class/mcos/mcos0/sys/kernel/debug/dynamic_debug/control";
    static const char *const controls[] = {
        "func release_fp_regs +p\n",
        "func mem_pagealloc_track_log_bridge +p\n"
    };
    int fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return -1;
    int bad = 0;
    for (size_t i = 0; i < sizeof controls / sizeof controls[0]; i++) {
        size_t length = strlen(controls[i]);
        ssize_t n = write(fd, controls[i], length);
        /* No short-write continuation: sysfs store is one command. */
        if (n < 0 || (size_t)n != length) { bad = 1; break; }
    }
    if (close(fd)) bad = 1;
    if (bad) return -1;
    static const char receipt[] =
        "func release_fp_regs +p\nfunc mem_pagealloc_track_log_bridge +p\n";
    return save_file("/case/evidence/fp-debug-control-writes", receipt, sizeof receipt - 1);
}


/* Public IHK OS_READ_KMSG ABI: direct buffer, non-shifting raw byte count.
 * This disposable Linux collector does not format, filter or NUL-terminate it.
 * Compatible native OS_FOPS module and exact runtime release are prerequisites. */
#define FP_KMSG_CAP ((4u << 20) - 4096u)
#define FP_IHK_OS_READ_KMSG 0x00112a20ul
static unsigned char fp_kmsg_buffer[FP_KMSG_CAP];
/* Linux collector-only ASCII transport; existing serial cap is unchanged. */
#define FP_EXPORT_RAW_MAX (256u * 1024u)
static int fp_export_bytes(int console, const char *name,
                           const unsigned char *data, size_t size, size_t cap)
{
    char line[1200];
    const char *hex = "0123456789abcdef";
    if (console < 0 || size > cap) return -1;
    int n = snprintf(line, sizeof line, "ND_MCKERNEL_BEGIN name=%s bytes=%zu\n", name, size);
    if (n < 0 || (size_t)n >= sizeof line || write_all(console,line,(size_t)n)) return -1;
    for (size_t offset=0; offset<size;) {
        size_t count = size-offset < 512 ? size-offset : 512;
        n=snprintf(line,sizeof line,"ND_MCKERNEL_DATA name=%s offset=%zu hex=",name,offset);
        if (n<0 || (size_t)n+2*count+1>=sizeof line) return -1;
        for (size_t j=0;j<count;j++) {
            line[n+2*j]=hex[data[offset+j]>>4];line[n+2*j+1]=hex[data[offset+j]&15];
        }
        line[n+2*count]='\n';
        if (write_all(console,line,(size_t)n+2*count+1)) return -1;
        offset+=count;
    }
    n=snprintf(line,sizeof line,"ND_MCKERNEL_END name=%s bytes=%zu\n",name,size);
    return n<0 || (size_t)n>=sizeof line || write_all(console,line,(size_t)n) ? -1 : 0;
}
static int fp_export_file(int console,const char *name,const char *path,size_t cap)
{
    static unsigned char data[FP_EXPORT_RAW_MAX+1];
    struct stat before={0},after={0};
    if (cap>FP_EXPORT_RAW_MAX) return -1;
    int fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0)return -1;
    int bad=fstat(fd,&before) || !S_ISREG(before.st_mode) || before.st_nlink!=1 ||
        before.st_size<0 || (uint64_t)before.st_size>cap;
    size_t used=0;
    while(!bad) {
        ssize_t count=read(fd,data+used,cap+1-used);
        if(count<0){if(errno==EINTR)continue;bad=1;break;}
        if(!count)break;
        used+=(size_t)count;if(used>cap){bad=1;break;}
    }
    if(fstat(fd,&after) || before.st_dev!=after.st_dev || before.st_ino!=after.st_ino ||
       before.st_size!=after.st_size || before.st_mtim.tv_sec!=after.st_mtim.tv_sec ||
       before.st_mtim.tv_nsec!=after.st_mtim.tv_nsec || before.st_ctim.tv_sec!=after.st_ctim.tv_sec ||
       before.st_ctim.tv_nsec!=after.st_ctim.tv_nsec || used!=(size_t)before.st_size)bad=1;
    if(close(fd))bad=1;
    return bad ? -1 : fp_export_bytes(console,name,data,used,cap);
}
static int fp_export_saved(int console)
{
    int raw=fp_export_file(console,"raw","/case/evidence/mckernel-kmsg.raw",FP_EXPORT_RAW_MAX)!=0;
    int status=fp_export_file(console,"status","/case/evidence/mckernel-kmsg.status",512)!=0;
    int control=fp_export_file(console,"control","/case/evidence/fp-debug-control-writes",128)!=0;
    if(raw || status || control) {
        char line[128];
        int n=snprintf(line,sizeof line,"ND_MCKERNEL_FAULT raw_export=%d status_export=%d control_export=%d\n",raw,status,control);
        if(n>0 && (size_t)n<sizeof line)(void)write_all(console,line,(size_t)n);
        return -1;
    }
    return 0;
}

static int fp_ring_capture(void)
{
    int bad = 0, open_error = 0, ioctl_error = 0, close_error = 0;
    int raw_saved = 0, raw_error = 0, result = -1;
    int fd = open("/dev/mcos0", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) { open_error = errno; bad = 1; }
    else {
        errno = 0;
        result = ioctl(fd, FP_IHK_OS_READ_KMSG, (unsigned long)fp_kmsg_buffer);
        if (result < 0) { ioctl_error = errno; bad = 1; }
        if (close(fd)) { close_error = errno; bad = 1; }
        if (result >= 0 && (unsigned int)result < FP_KMSG_CAP) {
            if (save_file("/case/evidence/mckernel-kmsg.raw", fp_kmsg_buffer, (size_t)result)) {
                raw_error = errno; bad = 1;
            } else raw_saved = 1;
        } else bad = 1;
    }
    char status[512];
    int n = snprintf(status, sizeof status,
        "transport=%s device=/dev/mcos0 request=0x00112a20 cap=%u ioctl_return=%d "
        "open_errno=%d ioctl_errno=%d close_errno=%d raw_saved=%d raw_errno=%d "
        "raw_bytes=%u nonshifting=1 added_terminator=0 semantic_acceptance=0\n",
        bad ? "FAIL" : "PASS", FP_KMSG_CAP, result, open_error, ioctl_error,
        close_error, raw_saved, raw_error,
        result >= 0 && (unsigned int)result < FP_KMSG_CAP ? (unsigned int)result : 0u);
    if (n < 0 || (size_t)n >= sizeof status ||
        save_file("/case/evidence/mckernel-kmsg.status", status, (size_t)n)) bad = 1;
    return bad ? -1 : 0;
}

int main(void)
{
    struct result payload; memset(&payload, 0, sizeof payload); payload.status = -1;
    int console = -1, good = 1, safe = 1, loaded = 0, empty = 0;
    int saved_level = -1, booted = 0, lifecycle_attempted = 0, lifecycle_rc = -1;
    struct result lifecycle;
    struct result resource;
    int resource_attempted = 0, resource_rc = -1;
    static struct reboot_capture reboot;
    int reboot_attempted = 0, reboot_rc = -1;
    struct result final_lifecycle, final_resource;
    int final_lifecycle_attempted=0, final_resource_attempted=0;
    int final_lifecycle_rc=-1, final_resource_rc=-1;
    if (getpid() != 1 || geteuid() != 0) return 125;
    uint64_t beginning = now_ns();
    if (!beginning) remain_pid1();
    collector_deadline = beginning + COLLECTOR_SECONDS * 1000ull * MS;
    struct sigaction alarm_action; memset(&alarm_action, 0, sizeof alarm_action);
    alarm_action.sa_handler = outer_expired;
    if (sigemptyset(&alarm_action.sa_mask) || sigaction(SIGALRM, &alarm_action, NULL))
        remain_pid1();
    alarm(COLLECTOR_SECONDS);
    if (mount_one("proc", "/proc") || mount_one("sysfs", "/sys") ||
        mount_one("devtmpfs", "/dev") ||
        mount_one("debugfs", "/sys/kernel/debug")) { good = 0; goto finish; }
    console = open("/dev/console", O_WRONLY | O_CLOEXEC | O_NONBLOCK);
    if (console < 0) { good = 0; goto finish; }
    /* Keep stdout/stderr private: helpers only see their capture pipes. */
    if (mkdir("/case/evidence", 0700) && errno != EEXIST) { good = 0; goto finish; }
    int fd = open("/proc/sys/kernel/printk", O_RDONLY | O_CLOEXEC);
    char levels[128]; ssize_t count = fd < 0 ? -1 : read(fd, levels, sizeof levels - 1);
    if (fd >= 0 && close(fd)) count = -1;
    if (count <= 0) { good = 0; goto finish; }
    levels[count] = 0;
    if (sscanf(levels, "%d", &saved_level) != 1 || saved_level < 1 || saved_level > 8 ||
        klogctl(6, NULL, 0)) { saved_level = -1; good = 0; goto finish; }
    if (save_file("/case/evidence/printk.original", levels, (size_t)count)) { good = 0; goto finish; }
    if (helper("load-ihk", "/sbin/insmod", (char *const[]){"insmod","/modules/ihk.ko",NULL}, &safe)) { good = 0; goto finish; }
    loaded = 1;
    if (helper("load-smp", "/sbin/insmod", (char *const[]){"insmod","/modules/ihk-smp-x86_64.ko","ihk_trampoline=524288",NULL}, &safe)) { good = 0; goto finish; }
    loaded = 2;
    if (helper("load-mcctrl", "/sbin/insmod", (char *const[]){"insmod","/modules/mcctrl.ko",NULL}, &safe)) { good = 0; goto finish; }
    loaded = 3;
#if defined(ND_FUTEX) || defined(ND_CORE_THREADS)
    if (helper("boot", "/bin/native-boot", futex_boot_argv, &safe)) { good = 0; goto finish; }
#else
    if (helper("boot", "/bin/native-boot", (char *const[]){"/bin/native-boot",NULL}, &safe)) { good = 0; goto finish; }
#endif
    booted = 1;
    if (fp_debug_enable()) { good = 0; goto finish; }
    supervise("/bin/mcexec", payload_argv, payload_env, "/case/work", 10000, &payload);
    if (!payload.clean) safe = 0;
    if (save_file("/case/evidence/payload.stdout", payload.out.data, payload.out.kept) ||
        save_file("/case/evidence/payload.stderr", payload.err.data, payload.err.kept)) good = 0;
    uint64_t begin_retirement = now_ns();
    uint64_t end = bounded_deadline(begin_retirement + 5000 * MS, 0);
    while (begin_retirement) {
        uint64_t current = now_ns();
        if (!current || current >= end) break;
        int state = retired_at("/proc/mcos0");
        if (state == 1) { empty = 1; break; }
        if (state < 0) break;
        struct timespec t = {0, 10000000}; nanosleep(&t, NULL);
    }
    /* Capture first-generation McKernel ring before strict stop/destroy. */
    if (fp_ring_capture()) good = 0;
    if (!typed_avx_stdout(payload.out.data, payload.out.kept)) good = 0;
    lifecycle_rc = lifecycle_after_payload(&payload, good, &safe, empty,
                                           &lifecycle_attempted, &lifecycle);
    if (lifecycle_rc) good = 0;
    resource_rc = resource_after_lifecycle(&payload, &lifecycle, good, &safe,
        lifecycle_rc, &resource_attempted, &resource);
    if (resource_rc) good = 0;
    reboot_rc = reboot_after_resource(&resource, resource_rc, good, &safe,
                                      &reboot_attempted, &reboot);
    if (reboot_rc) good = 0;
    final_lifecycle_rc=final_lifecycle_after_reboot(&reboot,reboot_rc,good,&safe,
        &final_lifecycle_attempted,&final_lifecycle);
    if(final_lifecycle_rc) good=0;
    final_resource_rc=final_resource_after_lifecycle(&payload,&final_lifecycle,
        final_lifecycle_rc,good,&safe,&final_resource_attempted,&final_resource);
    if(final_resource_rc) good=0;
finish:;
    /* Second strict stop and final public destroy/release follow the reboot.
     * Modules remain until VM shutdown. No physical-frame/mapping/callback/ref
     * or generation restoration is inferred from public inventory alone. */
    char teardown[160];
    int length = snprintf(teardown, sizeof teardown,
                          "modules_loaded=%d processes_reaped=%d procfs_empty=%d resource_probe_attempted=%d\n",
                          loaded, safe, empty, resource_attempted);
    if (length < 0 || (size_t)length >= sizeof teardown ||
        save_file("/case/evidence/teardown", teardown, (size_t)length)) good = 0;
    static char kernel_log[262144];
    int n = klogctl(3, kernel_log, sizeof kernel_log);
    if (n < 0 || n == (int)sizeof kernel_log) good = 0;
    else if (save_file("/case/evidence/kernel.log", kernel_log, (size_t)n) ||
             console < 0 || write_all(console, kernel_log, (size_t)n) ||
             write_all(console, "\n", 1)) good = 0;
    /* Exercise restoration before publication so a restoration failure is
     * represented by procfs_empty=false; suppress again for the one write. */
    if (saved_level < 0 || klogctl(8, NULL, saved_level) || klogctl(6, NULL, 0)) good = 0;
    int evidence_fd = open("/case/evidence", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (evidence_fd < 0) good = 0;
    else { if (syncfs(evidence_fd)) good = 0; if (close(evidence_fd)) good = 0; }
    if (booted && fp_export_saved(console)) good = 0;
    if (!good || !safe) payload.fault = 1;
    payload.finished = now_ns();
    if (console >= 0 && safe) {
        if (lifecycle_attempted && publish_lifecycle(console, &lifecycle, lifecycle_rc, 0))
            payload.fault = 1;
        if (resource_attempted && publish_resource(console, &resource, resource_rc, 0))
            payload.fault = 1;
        if (reboot_attempted && publish_reboot(console, &reboot, reboot_rc))
            payload.fault = 1;
        if (final_lifecycle_attempted && publish_lifecycle(console, &final_lifecycle, final_lifecycle_rc, 1))
            payload.fault=1;
        if (final_resource_attempted && publish_resource(console, &final_resource, final_resource_rc, 1))
            payload.fault=1;
        int publication = publish(console, &payload, empty);
        if (publication) payload.fault = 1;
    }
    if (saved_level >= 0 && klogctl(8, NULL, saved_level)) {
        const char message[] = "native diagnostic teardown error: printk restoration\n";
        if (console >= 0) (void)write_all(console, message, sizeof message - 1);
        remain_pid1(); /* Host deadline rejects the uncompleted teardown. */
    }
    poweroff_forever(console);
    return 125; /* unreachable */
}
