/* SPDX-License-Identifier: GPL-2.0-only */
/* Linux-only supervisor; the tested McKernel application uses real mcexec. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static int log_fd = 1;
static pid_t owned_child = -1;
#define CHECK(x) do { if (!(x)) { dprintf(log_fd, "NATIVE_FAILURE_CONTROL FAIL line=%d errno=%d\n", __LINE__, errno); if (owned_child > 0) kill(owned_child, SIGKILL); return 1; } } while (0)

static void pause_ms(unsigned ms)
{
    struct timespec t = { ms / 1000, (long)(ms % 1000) * 1000000 };
    while (nanosleep(&t, &t) && errno == EINTR) {}
}

static pid_t blocked_reader(pid_t pid, char *observed, size_t length)
{
    char path[128];
    snprintf(path, sizeof path, "/proc/%d/task", pid);
    DIR *dir = opendir(path);
    if (!dir) return -1;
    pid_t found = -1;
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        char *end;
        long tid = strtol(entry->d_name, &end, 10);
        if (*end || tid <= 0) continue;
        snprintf(path, sizeof path, "/proc/%d/task/%ld/syscall", pid, tid);
        FILE *f = fopen(path, "r");
        if (!f) continue;
        char line[256];
        long number;
        unsigned long fd, address, bytes;
        if (fgets(line, sizeof line, f) &&
            sscanf(line, "%ld %lx %lx %lx", &number, &fd, &address, &bytes) == 4 &&
            number == 0 && fd == 0 && bytes == 16) {
            if (found != -1) { fclose(f); closedir(dir); return -2; }
            found = tid;
            snprintf(observed, length, "%s", line);
        }
        fclose(f);
    }
    closedir(dir);
    return found;
}

int main(int argc, char **argv)
{
    int guest = argc == 4 && !strcmp(argv[1], "--guest");
    CHECK(guest || (argc == 3 && !strcmp(argv[1], "--linux-reference")));
    if (guest) {
        log_fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
        CHECK(log_fd >= 0);
    }
    CHECK(dprintf(log_fd, "NATIVE_FAILURE_BEGIN guest=%d\n", guest) > 0);
    int input[2], output[2];
    CHECK(pipe2(input, O_CLOEXEC) == 0 && pipe2(output, O_CLOEXEC) == 0);
    owned_child = fork();
    CHECK(owned_child >= 0);
    if (!owned_child) {
        if (dup2(input[0], 0) != 0 || dup2(output[1], 1) != 1) _exit(125);
        close(input[0]); close(input[1]); close(output[0]); close(output[1]);
        if (guest) execl(argv[2], argv[2], "-t", "1", "0", argv[3], (char *)0);
        else execl(argv[2], argv[2], (char *)0);
        _exit(126);
    }
    close(input[0]); close(output[1]);
    static const char expected[] = "NATIVE_FAILURE_READY\n";
    char line[sizeof expected];
    for (unsigned i = 0; i < sizeof expected - 1; ++i) {
        struct pollfd p = { output[0], POLLIN, 0 };
        CHECK(poll(&p, 1, 60000) == 1 && (p.revents & POLLIN));
        CHECK(read(output[0], line + i, 1) == 1);
    }
    CHECK(!memcmp(line, expected, sizeof expected - 1));
    char observed[256] = {0};
    pid_t worker = -1;
    for (unsigned tries = 0; tries < 500 && worker == -1; ++tries) {
        worker = blocked_reader(owned_child, observed, sizeof observed);
        if (worker == -1) pause_ms(10);
    }
    CHECK(worker > 0);
    CHECK(dprintf(log_fd, "NATIVE_FAILURE_BLOCKED pid=%d tid=%d syscall=%s", owned_child, worker, observed) > 0);
    /* Leave time for the independent QMP observer to capture the live queues. */
    if (guest) pause_ms(2000);
    CHECK(kill(owned_child, SIGKILL) == 0);
    int status = 0;
    pid_t reaped = 0;
    for (unsigned tries = 0; tries < 1500 && !reaped; ++tries) {
        reaped = waitpid(owned_child, &status, WNOHANG);
        CHECK(reaped >= 0);
        if (!reaped) pause_ms(10);
    }
    CHECK(reaped == owned_child && WIFSIGNALED(status) && WTERMSIG(status) == SIGKILL);
    pid_t retired_pid = owned_child;
    owned_child = -1;
    CHECK(dprintf(log_fd, "NATIVE_FAILURE_KILLED pid=%d tid=%d signal=9\n", retired_pid, worker) > 0);
    close(input[1]); close(output[0]);
    if (guest) {
        char path[128];
        snprintf(path, sizeof path, "/proc/mcos0/%d", retired_pid);
        int missing = 0;
        for (unsigned tries = 0; tries < 1500 && !missing; ++tries) {
            struct stat st;
            if (stat(path, &st) < 0) { CHECK(errno == ENOENT); missing = 1; }
            else pause_ms(10);
        }
        CHECK(missing);
        CHECK(dprintf(log_fd, "NATIVE_FAILURE_PROCESS_NODE_CLEAR pid=%d\n", retired_pid) > 0);
        CHECK(retired_pid > 300 && retired_pid < 512 && worker > 300 && worker < 512);
        int limit = open("/proc/sys/kernel/pid_max", O_WRONLY | O_CLOEXEC);
        CHECK(limit >= 0 && write(limit, "512\n", 4) == 4 && close(limit) == 0);
        unsigned pid_reused = 0, tid_reused = 0;
        for (unsigned i = 0; i < 700; ++i) {
            owned_child = fork();
            CHECK(owned_child >= 0);
            if (!owned_child) _exit(0);
            pid_reused += owned_child == retired_pid;
            tid_reused += owned_child == worker;
            CHECK(waitpid(owned_child, &status, 0) == owned_child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
            owned_child = -1;
        }
        CHECK(pid_reused > 0 && tid_reused > 0);
        pause_ms(1000);
        CHECK(dprintf(log_fd, "NATIVE_FAILURE_REUSE pid=%d tid=%d forks=700 pid_reused=%u tid_reused=%u\n", retired_pid, worker, pid_reused, tid_reused) > 0);
    }
    CHECK(dprintf(log_fd, "NATIVE_FAILURE_CONTROL PASS guest=%d pid=%d tid=%d\n", guest, retired_pid, worker) > 0);
    if (guest) close(log_fd);
    return 0;
}
