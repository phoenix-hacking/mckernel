/* SPDX-License-Identifier: GPL-2.0 */
/* One process/exec/wait diagnostic. Run under an owning <=10s group supervisor.
 * Current942 native non-null CREATE_PPD is unsupported; Linux success is not
 * McKernel capability evidence. Invoke this static executable by absolute path.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;
static const char child_marker[] = "PRACTICAL_PROCESS_EXEC_CHILD\n";
static const char parent_marker[] =
    "process-exec-wait child=37 output=verified eof=1 echild=1\n";

static uint64_t monotonic_ns(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) return 0;
    return (uint64_t)now.tv_sec * 1000000000ULL + (uint64_t)now.tv_nsec;
}

static int within(uint64_t deadline)
{
    uint64_t now = monotonic_ns();
    return now && now < deadline;
}

static int write_marker(int fd, const char *bytes, size_t count, uint64_t deadline)
{
    while (count && within(deadline)) {
        ssize_t n = write(fd, bytes, count);
        if (n > 0) { bytes += n; count -= (size_t)n; }
        else if (n < 0 && errno == EINTR) continue;
        else if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            struct pollfd p = {fd, POLLOUT, 0};
            if (poll(&p, 1, 10) < 0 && errno != EINTR) return -1;
        } else return -1;
    }
    return count ? -1 : 0;
}

static int child_mode(int argc, char **argv)
{
    static const char *const expected_env[] = {
        "PATH=/usr/bin:/bin", "LC_ALL=C", "PRACTICAL_EXEC_TOKEN=fixed-v1"
    };
    if (argc != 3 || strcmp(argv[0], "process-exec-child") ||
        strcmp(argv[1], "--child") || strcmp(argv[2], "fixed-token"))
        return 90;
    for (size_t i = 0; i < sizeof expected_env / sizeof *expected_env; ++i)
        if (!environ[i] || strcmp(environ[i], expected_env[i])) return 91;
    if (environ[3]) return 92;
    uint64_t start = monotonic_ns();
    if (!start || write_marker(1, child_marker, sizeof child_marker - 1,
                               start + 2000000000ULL)) return 93;
    return 37;
}

/* The unreaped child PID pins the signal target. Never kill a reaped PID.
 * If the OS cannot retire even a killed child, report failure/uncertainty;
 * the outer owning group supervisor must reject and retire the whole run.
 */
static int retire_child(pid_t child, int *reaped, int *owned, int *status)
{
    if (*reaped) return 0;
    if (!*owned) return -1;
    if (kill(child, SIGKILL) && errno != ESRCH) return -1;
    uint64_t start = monotonic_ns();
    if (!start) return -1;
    uint64_t end = start + 2000000000ULL;
    while (within(end)) {
        pid_t got = waitpid(child, status, WNOHANG);
        if (got == child) { *reaped = 1; *owned = 0; return 0; }
        if (got < 0 && errno != EINTR) {
            if (errno == ECHILD) *owned = 0;
            return -1;
        }
        struct timespec pause = {0, 1000000};
        if (nanosleep(&pause, NULL) && errno != EINTR) return -1;
    }
    return -1;
}

int main(int argc, char **argv)
{
    if (argc != 1) return child_mode(argc, argv);
    const char *stage = "arguments";
    int saved_error = 0, pipes[2] = {-1, -1};
    int reaped = 0, owned = 0, status = -1, eof = 0;
    pid_t child = -1;
    unsigned char received[sizeof child_marker];
    size_t kept = 0;
    uint64_t start = monotonic_ns();
    if (!start || !argv[0] || argv[0][0] != '/' || strlen(argv[0]) > 4095)
        goto failure;
    uint64_t deadline = start + 6000000000ULL;
    /* The disposable process owns SIGCHLD policy; do not inherit auto-reap. */
    struct sigaction action;
    memset(&action, 0, sizeof action); action.sa_handler = SIG_DFL;
    sigset_t mask;
    stage = "SIGCHLD policy";
    if (sigemptyset(&action.sa_mask) || sigaction(SIGCHLD, &action, NULL) ||
        sigemptyset(&mask) || sigaddset(&mask, SIGCHLD) ||
        sigprocmask(SIG_UNBLOCK, &mask, NULL)) goto failure;
    stage = "stdio";
    for (int fd = 0; fd < 3; ++fd) if (fcntl(fd, F_GETFD) < 0) goto failure;
    stage = "pipe2";
    if (pipe2(pipes, O_NONBLOCK | O_CLOEXEC)) goto failure;
    stage = "fork";
    child = fork();
    if (child < 0) goto failure;
    if (!child) {
        char *const child_argv[] = {"process-exec-child", "--child", "fixed-token", NULL};
        char *const child_env[] = {
            "PATH=/usr/bin:/bin", "LC_ALL=C", "PRACTICAL_EXEC_TOKEN=fixed-v1", NULL
        };
        /* No stdio or allocator calls between fork and exec. */
        if (close(pipes[0]) || dup2(pipes[1], STDOUT_FILENO) < 0 || close(pipes[1]))
            _exit(94);
        action.sa_handler = SIG_IGN;
        if (sigaction(SIGPIPE, &action, NULL)) _exit(95);
        execve(argv[0], child_argv, child_env);
        _exit(96); /* An execve return, even zero, cannot emit the child marker. */
    }
    owned = 1;
    stage = "close parent writer";
    if (close(pipes[1])) { pipes[1] = -1; goto failure; }
    pipes[1] = -1;
    stage = "capture and waitpid";
    while (!reaped || !eof) {
        if (!within(deadline)) { errno = ETIMEDOUT; goto failure; }
        if (!eof) {
            if (kept == sizeof received) { errno = EOVERFLOW; goto failure; }
            ssize_t count = read(pipes[0], received + kept, sizeof received - kept);
            if (count > 0) kept += (size_t)count;
            else if (!count) eof = 1;
            else if (errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK)
                goto failure;
        }
        if (!reaped) {
            pid_t got = waitpid(child, &status, WNOHANG);
            if (got == child) { reaped = 1; owned = 0; }
            else if (got < 0 && errno != EINTR) {
                if (errno == ECHILD) owned = 0;
                goto failure;
            }
        }
        if (!reaped || !eof) {
            struct pollfd poller = {pipes[0], POLLIN | POLLHUP, 0};
            if (poll(&poller, 1, 10) < 0 && errno != EINTR) goto failure;
        }
    }
    stage = "child result";
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 37 ||
        kept != sizeof child_marker - 1 || memcmp(received, child_marker, kept)) {
        errno = EPROTO; goto failure;
    }
    stage = "close reader";
    if (close(pipes[0])) { pipes[0] = -1; goto failure; }
    pipes[0] = -1;
    stage = "second waitpid ECHILD";
    for (;;) {
        if (!within(deadline)) { errno = ETIMEDOUT; goto failure; }
        errno = 0;
        pid_t got = waitpid(child, &status, WNOHANG);
        if (got == -1 && errno == EINTR) continue;
        if (got != -1 || errno != ECHILD) { errno = EPROTO; goto failure; }
        break;
    }
    stage = "parent output";
    if (write_marker(1, parent_marker, sizeof parent_marker - 1, deadline)) goto failure;
    return 0;
failure:
    saved_error = errno;
    if (pipes[0] >= 0) (void)close(pipes[0]);
    if (pipes[1] >= 0) (void)close(pipes[1]);
    int retired = child < 0 || retire_child(child, &reaped, &owned, &status) == 0;
    fprintf(stderr, "process-exec-wait failure stage=%s errno=%d child_retired=%d\n",
            stage, saved_error, retired);
    return 1;
}
