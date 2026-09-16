/* SPDX-License-Identifier: GPL-2.0-only */
/* Ordinary Linux infrastructure stimulus. Never a catalog/native payload. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

static bool put(int fd, const void *raw, size_t n)
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

static bool fill(int fd, unsigned char byte, size_t n)
{
    unsigned char bytes[4096]; memset(bytes, byte, sizeof bytes);
    while (n) { size_t part = n < sizeof bytes ? n : sizeof bytes; if (!put(fd, bytes, part)) return false; n -= part; }
    return true;
}

static int literal(int argc, char **argv)
{
    if (argc != 4 || strcmp(argv[0], "literal-app") || strcmp(argv[2], "") || strcmp(argv[3], "A=B")) return 81;
    if (!environ[0] || strcmp(environ[0], "ONLY=A=B") || !environ[1] || strcmp(environ[1], "EMPTY=") ||
        !environ[2] || strncmp(environ[2], "EXPECTED_CWD=", 13) || environ[3]) return 82;
    char cwd[4096];
    if (!getcwd(cwd, sizeof cwd) || strcmp(cwd, environ[2] + 13)) return 83;
    const unsigned char expected[] = { 0, 1, 0xa5, '\n', 0xff, 0 };
    unsigned char actual[sizeof expected]; size_t used = 0;
    while (used < sizeof actual) {
        ssize_t n = read(0, actual + used, sizeof actual - used);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return 84;
        used += (size_t)n;
    }
    unsigned char extra; ssize_t n;
    do { n = read(0, &extra, 1); } while (n < 0 && errno == EINTR);
    if (n != 0 || memcmp(actual, expected, sizeof expected)) return 85;
    /* These are direct subject observations of the distinct memfd profile. */
    const char *execfn = (const char *)getauxval(AT_EXECFN);
    char link[256]; ssize_t length = readlink("/proc/self/exe", link, sizeof link - 1);
    if (!execfn || strncmp(execfn, "/dev/fd/", 8) || length <= 0 || length == (ssize_t)sizeof link - 1) return 86;
    link[length] = 0;
    if (strcmp(link, "/memfd:ac-linux-image (deleted)")) return 87;
    if (!put(1, "LITERAL_OK\n", 11) || !put(2, "LITERAL_ERR\n", 12)) return 88;
    return 37;
}

int main(int argc, char **argv)
{
    if (argc < 2) return 80;
    const char *mode = argv[1];
    if (!strcmp(mode, "stopped-rescue")) {
        pid_t child = fork();
        if (child < 0) return 91;
        if (!child) for (;;) pause();
        static const char ready[] = "READY\nSTOP_ARMED\n";
        if (!put(2, ready, sizeof ready - 1)) return 92;
        if (raise(SIGSTOP) != 0) return 93;
        for (;;) pause();
    }
    if (!strcmp(mode, "literal")) return literal(argc, argv);
    if (!strcmp(mode, "empty-env")) return environ[0] ? 82 : (put(1, "EMPTY_ENV\n", 10) ? 0 : 88);
    if (!strcmp(mode, "exit143")) return 143;
    if (!strcmp(mode, "signal-term")) { if (raise(SIGTERM) != 0) return 89; return 90; }
    if (!strcmp(mode, "interrupt-collector")) {
        if (kill(getppid(), SIGTERM) != 0) return 89;
        for (;;) pause();
    }
    if (!strcmp(mode, "replace-source")) {
        if (argc != 3) return 81;
        int fd = open(argv[2], O_WRONLY | O_TRUNC | O_NOFOLLOW);
        if (fd < 0 || !put(fd, "changed\n", 8) || close(fd) != 0) return 96;
        return put(1, "SEALED_SOURCE_UNCHANGED\n", 24) ? 0 : 88;
    }
    if (!strcmp(mode, "timeout")) { for (;;) pause(); }
    if (!strcmp(mode, "stdin-devnull")) {
        unsigned char b; return read(0, &b, 1) == 0 && put(1, "DEVNULL\n", 8) ? 0 : 84;
    }
    if (!strcmp(mode, "pressure")) {
        pid_t child = fork();
        if (child < 0) return 91;
        if (!child) _exit(fill(2, 'E', 65536) ? 0 : 88);
        if (!fill(1, 'O', 65536)) return 88;
        int raw; pid_t waited;
        do { waited = waitpid(child, &raw, 0); } while (waited < 0 && errno == EINTR);
        return waited == child && WIFEXITED(raw) && WEXITSTATUS(raw) == 0 ? 0 : 92;
    }
    if (!strcmp(mode, "stdout-over")) return fill(1, 'X', 65537) ? 0 : 88;
    if (!strcmp(mode, "stderr-over")) return fill(2, 'Y', 65537) ? 0 : 88;
    if (!strcmp(mode, "pipe-holder") || !strcmp(mode, "escaped-holder")) {
        int ready[2]; if (pipe(ready) != 0) return 91;
        pid_t child = fork();
        if (child < 0) return 91;
        if (!child) {
            close(ready[0]);
            if (!strcmp(mode, "escaped-holder") && setsid() < 0) _exit(93);
            if (!put(ready[1], "R", 1)) _exit(88);
            close(ready[1]);
            for (;;) pause();
        }
        close(ready[1]); unsigned char byte; ssize_t n;
        do { n = read(ready[0], &byte, 1); } while (n < 0 && errno == EINTR);
        close(ready[0]);
        return n == 1 && byte == 'R' ? 0 : 94;
    }
    return 95;
}
