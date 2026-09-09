/* SPDX-License-Identifier: GPL-2.0-only */
/* Linux supervisor inside the pinned guest. Its fork is not a McKernel test. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static int log_fd = -1, guest;
static pid_t owned_child = -1;
static const char *case_name;
static unsigned char captured[2][4096];
static size_t captured_size[2];

static long long milliseconds(void)
{
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value)) return -1;
    return (long long)value.tv_sec * 1000 + value.tv_nsec / 1000000;
}

static void report_streams(void)
{
    for (unsigned stream = 0; stream < 2; ++stream) {
        char hex[sizeof captured[stream] * 2 + 1];
        for (size_t i = 0; i < captured_size[stream]; ++i)
            snprintf(hex + i * 2, 3, "%02x", captured[stream][i]);
        hex[captured_size[stream] * 2] = '\0';
        dprintf(log_fd, "NATIVE_SIGNAL_STREAM guest=%d case=%s stream=%s bytes=%zu hex=%s\n",
                guest, case_name ? case_name : "argument", stream ? "stderr" : "stdout", captured_size[stream], hex);
    }
}

static void cleanup(void)
{
    if (owned_child <= 0) return;
    kill(owned_child, SIGKILL);
    int status;
    long long deadline = milliseconds() + 5000;
    do {
        pid_t result = waitpid(owned_child, &status, WNOHANG);
        if (result == owned_child || (result < 0 && errno == ECHILD)) {
            owned_child = -1;
            return;
        }
        struct timespec pause = {0, 10000000};
        nanosleep(&pause, NULL);
    } while (milliseconds() < deadline);
    dprintf(log_fd, "NATIVE_SIGNAL_CONTROL FAIL cleanup pid=%d\n", owned_child);
}

static void failure(int line)
{
    int saved_errno = errno;
    report_streams();
    dprintf(log_fd, "NATIVE_SIGNAL_CONTROL FAIL line=%d errno=%d guest=%d case=%s\n",
            line, saved_errno, guest, case_name ? case_name : "argument");
    exit(1);
}

#define CHECK(test) do { if (!(test)) failure(__LINE__); } while (0)

static pid_t blocked_reader(pid_t pid, char *observed, size_t length)
{
    char path[128];
    snprintf(path, sizeof path, "/proc/%d/task", pid);
    DIR *directory = opendir(path);
    if (!directory) return -1;
    pid_t found = -1;
    struct dirent *entry;
    while ((entry = readdir(directory))) {
        char *end;
        long tid = strtol(entry->d_name, &end, 10);
        if (*end || tid <= 0) continue;
        snprintf(path, sizeof path, "/proc/%d/task/%ld/syscall", pid, tid);
        FILE *input = fopen(path, "r");
        if (!input) continue;
        char line[256];
        long number;
        unsigned long fd, address, bytes;
        if (fgets(line, sizeof line, input) &&
            sscanf(line, "%ld %lx %lx %lx", &number, &fd, &address, &bytes) == 4 &&
            number == 0 && fd == 0 && bytes == 1) {
            if (found != -1) { fclose(input); closedir(directory); return -2; }
            found = (pid_t)tid;
            snprintf(observed, length, "%s", line);
        }
        fclose(input);
    }
    closedir(directory);
    return found;
}

int main(int argc, char **argv)
{
    log_fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
    if (log_fd < 0) return 125;
    CHECK(signal(SIGPIPE, SIG_IGN) != SIG_ERR);
    CHECK(atexit(cleanup) == 0);
    guest = argc == 5 && !strcmp(argv[1], "--guest");
    CHECK(guest || (argc == 4 && !strcmp(argv[1], "--linux-reference")));
    case_name = argv[argc - 1];
    int restart = !strcmp(case_name, "fp-restart");
    CHECK(restart || !strcmp(case_name, "mask-context") || !strcmp(case_name, "fp-return"));
    CHECK(dprintf(log_fd, "NATIVE_SIGNAL_BEGIN guest=%d case=%s\n", guest, case_name) > 0);

    char expected_stdout[256];
    int expected_length = snprintf(expected_stdout, sizeof expected_stdout,
            "%sNATIVE_SIGNAL_ABI PASS %s\n", restart ? "NATIVE_SIGNAL_RESTART_READY\n" : "", case_name);
    CHECK(expected_length > 0 && (size_t)expected_length < sizeof expected_stdout);
    /* The unchanged launcher emits these exact diagnostics before the payload
     * in the minimal guest (also present in the accepted baseline). Retain
     * the complete combined stream; no arbitrary warning filtering. The
     * payload stderr contract remains empty, or the exact restart ACK. */
    const char *launcher_stderr = guest ?
        "objdump /proc/self/exe: 2\nwarning: did not set LD_PRELOAD\n" : "";
    const char *payload_stderr = restart ? "NATIVE_SIGNAL_RESTART_HANDLED\n" : "";
    char expected_stderr[256];
    int stderr_length = snprintf(expected_stderr, sizeof expected_stderr,
                                  "%s%s", launcher_stderr, payload_stderr);
    CHECK(stderr_length >= 0 && (size_t)stderr_length < sizeof expected_stderr);
    const char *expected[2] = {expected_stdout, expected_stderr};
    size_t expected_sizes[2] = {(size_t)expected_length, strlen(expected[1])};
    int pipes[3][2], files[2];
    for (unsigned i = 0; i < 3; ++i) CHECK(pipe2(pipes[i], O_CLOEXEC) == 0);
    for (unsigned i = 0; i < 2; ++i) {
        char path[128];
        snprintf(path, sizeof path, "/signal-%s-%s.%s", guest ? "guest" : "linux", case_name,
                 i ? "stderr" : "stdout");
        files[i] = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
        CHECK(files[i] >= 0);
    }
    owned_child = fork();
    CHECK(owned_child >= 0);
    if (owned_child == 0) {
        if (dup2(pipes[0][0], 0) != 0 || dup2(pipes[1][1], 1) != 1 ||
            dup2(pipes[2][1], 2) != 2) _exit(125);
        for (unsigned i = 0; i < 3; ++i) { close(pipes[i][0]); close(pipes[i][1]); }
        if (guest) execl(argv[2], argv[2], "-t", "1", "0", argv[3], case_name, (char *)0);
        else execl(argv[2], argv[2], case_name, (char *)0);
        _exit(126);
    }
    pid_t child_pid = owned_child, worker = -1;
    close(pipes[0][0]); close(pipes[1][1]); close(pipes[2][1]);
    if (!restart) { close(pipes[0][1]); pipes[0][1] = -1; }
    struct pollfd pollers[2] = {{pipes[1][0], POLLIN, 0}, {pipes[2][0], POLLIN, 0}};
    for (unsigned i = 0; i < 2; ++i)
        CHECK(fcntl(pollers[i].fd, F_SETFL, O_NONBLOCK) == 0);
    long long deadline = milliseconds() + 45000;
    int eof[2] = {0, 0}, reaped = 0, status = 0, sent = 0, input_sent = 0;
    while (!reaped || !eof[0] || !eof[1]) {
        CHECK(milliseconds() < deadline);
        int ready = poll(pollers, 2, 10);
        CHECK(ready >= 0 || errno == EINTR);
        for (unsigned i = 0; i < 2; ++i) {
            if (eof[i]) continue;
            CHECK(!(pollers[i].revents & (POLLERR | POLLNVAL)));
            for (;;) {
                unsigned char bytes[512];
                ssize_t count = read(pollers[i].fd, bytes, sizeof bytes);
                if (count < 0) { CHECK(errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR); break; }
                if (count == 0) { eof[i] = 1; close(pollers[i].fd); pollers[i].fd = -1; break; }
                CHECK(captured_size[i] + (size_t)count <= sizeof captured[i]);
                memcpy(captured[i] + captured_size[i], bytes, (size_t)count);
                captured_size[i] += (size_t)count;
                CHECK(write(files[i], bytes, (size_t)count) == count);
                CHECK(captured_size[i] <= expected_sizes[i] &&
                      !memcmp(captured[i], expected[i], captured_size[i]));
            }
        }
        if (!reaped) {
            pid_t result = waitpid(owned_child, &status, WNOHANG);
            CHECK(result >= 0);
            if (result) { CHECK(result == child_pid); reaped = 1; owned_child = -1; }
        }
        if (restart && !sent && captured_size[0] >= 28 && !reaped) {
            char observed[256] = {0};
            worker = blocked_reader(child_pid, observed, sizeof observed);
            CHECK(worker != -2);
            if (worker > 0) {
                CHECK(dprintf(log_fd, "NATIVE_SIGNAL_BLOCKED guest=%d case=%s pid=%d tid=%d syscall=%s",
                              guest, case_name, child_pid, worker, observed) > 0);
                CHECK(kill(child_pid, SIGUSR1) == 0);
                sent = 1;
            }
        }
        if (restart && sent && !input_sent && captured_size[1] == expected_sizes[1]) {
            CHECK(!reaped);
            CHECK(dprintf(log_fd, "NATIVE_SIGNAL_HANDLED_BEFORE_INPUT guest=%d case=%s pid=%d tid=%d input=a5\n",
                          guest, case_name, child_pid, worker) > 0);
            unsigned char input = 0xa5;
            CHECK(write(pipes[0][1], &input, 1) == 1);
            close(pipes[0][1]); pipes[0][1] = -1; input_sent = 1;
        }
    }
    report_streams();
    CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 37 && status == (37 << 8));
    for (unsigned i = 0; i < 2; ++i) {
        CHECK(captured_size[i] == expected_sizes[i]);
        CHECK(close(files[i]) == 0);
    }
    CHECK(!restart || (sent && input_sent));
    CHECK(dprintf(log_fd, "NATIVE_SIGNAL_CONTROL PASS guest=%d case=%s pid=%d tid=%d raw_status=%d exit=37\n",
                  guest, case_name, child_pid, worker, status) > 0);
    CHECK(close(log_fd) == 0);
    return 0;
}
