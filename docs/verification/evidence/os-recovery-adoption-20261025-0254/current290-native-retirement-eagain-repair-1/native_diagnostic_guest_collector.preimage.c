/* SPDX-License-Identifier: GPL-2.0-only
 * Fixed PID-1 diagnostic collector, not a general-purpose init.
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
#define MS 1000000ull
#define COLLECTOR_SECONDS 120u
/* native-boot contains two mandatory ten-second capture_pause calls. Allow
 * forty additional seconds for startup/service work, without lengthening
 * ordinary module helpers. The shared outer budget includes every phase. */
#define BOOT_TIMEOUT_MS 60000u
#define HELPER_TIMEOUT_MS 10000u
static uint64_t collector_deadline;
struct stream {
    unsigned char data[STREAM_LIMIT];
    size_t kept;
    uint64_t observed, eof_ns;
    int eof;
};
struct result {
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
#if defined(ND_FUTEX)
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
            if (keep > STREAM_LIMIT - s->kept) keep = STREAM_LIMIT - s->kept;
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
                  "\"limit\":%u,\"eof_ns\":%llu}", h, s->eof ? "true" : "false",
                  s->observed != s->kept ? "true" : "false",
                  (unsigned long long)s->observed, s->kept,
                  (unsigned long long)(s->observed - s->kept), STREAM_LIMIT,
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

static int helper(const char *tag, const char *path, char *const av[], int *safe)
{
    struct result r; char name[128], record[256];
    supervise(path, av, helper_env, NULL, helper_timeout_ms(path), &r);
    if (!r.clean) *safe = 0;
    int bad = r.fault || r.timeout || !r.clean || r.status != 0 ||
              !r.out.eof || !r.err.eof || r.out.observed != r.out.kept ||
              r.err.observed != r.err.kept;
    snprintf(name, sizeof name, "/case/evidence/%s.stdout", tag);
    if (save_file(name, r.out.data, r.out.kept)) bad = 1;
    snprintf(name, sizeof name, "/case/evidence/%s.stderr", tag);
    if (save_file(name, r.err.data, r.err.kept)) bad = 1;
    int n = snprintf(record, sizeof record, "status=%d fault=%d timeout=%d clean=%d stage=%d errno=%d\n",
                     r.status, r.fault, r.timeout, r.clean, r.child_stage, r.child_errno);
    snprintf(name, sizeof name, "/case/evidence/%s.status", tag);
    if (n < 0 || (size_t)n >= sizeof record || save_file(name, record, (size_t)n)) bad = 1;
    return bad ? -1 : 0;
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

int main(void)
{
    struct result payload; memset(&payload, 0, sizeof payload); payload.status = -1;
    int console = -1, good = 1, safe = 1, loaded = 0, empty = 0;
    int saved_level = -1;
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
#if defined(ND_FUTEX)
    if (helper("boot", "/bin/native-boot", futex_boot_argv, &safe)) { good = 0; goto finish; }
#else
    if (helper("boot", "/bin/native-boot", (char *const[]){"/bin/native-boot",NULL}, &safe)) { good = 0; goto finish; }
#endif
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
finish:;
    /* native-boot deliberately retains the nested OS. Its modules/resources
     * remain until this disposable Linux guest powers off; never rmmod the
     * active SMP module. The host backend separately owns QEMU retirement. */
    char teardown[160];
    int length = snprintf(teardown, sizeof teardown,
                          "modules_loaded=%d processes_reaped=%d procfs_empty=%d nested_os_retained=1\n",
                          loaded, safe, empty);
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
    if (!good || !safe) payload.fault = 1;
    payload.finished = now_ns();
    if (console >= 0 && safe) {
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
