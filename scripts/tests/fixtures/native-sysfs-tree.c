/* SPDX-License-Identifier: GPL-2.0-only */
/* Real Linux paths and callbacks for the isolated native tree module. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define ROOT "/sys/mckernel_sysfs_tree_verify"
#define TREE ROOT "/sys"
#define require(test) do { if (!(test)) { fprintf(stderr, "NATIVE_SYSFS_TREE FAIL line=%d errno=%d\n", __LINE__, errno); exit(1); } } while (0)

static ssize_t read_file(const char *path, char *buffer, size_t capacity) {
    int fd = open(path, O_RDONLY); require(fd >= 0);
    ssize_t bytes = read(fd, buffer, capacity); require(bytes >= 0);
    require(close(fd) == 0); return bytes;
}
static void value(const char *path, const char *expected) {
    char buffer[4096]; ssize_t bytes = read_file(path, buffer, sizeof(buffer));
    require((size_t)bytes == strlen(expected)); require(!memcmp(buffer, expected, bytes));
}
static long milliseconds(void) {
    struct timespec now; require(clock_gettime(CLOCK_MONOTONIC, &now) == 0);
    return now.tv_sec * 1000L + now.tv_nsec / 1000000L;
}

int main(int argc, char **argv) {
    require(argc == 2);
    char expected[4096], actual[4096];
    ssize_t expected_bytes = read_file(argv[1], expected, sizeof(expected));
    ssize_t actual_bytes = read_file(TREE "/trace", actual, sizeof(actual));
    require(expected_bytes > 0 && actual_bytes == expected_bytes && !memcmp(actual, expected, actual_bytes));
    int cases = 0; for (ssize_t i = 0; i < actual_bytes; i++) cases += actual[i] == '\n';
    struct stat status; require(stat(TREE "/live", &status) == 0 && S_ISDIR(status.st_mode));
    require(stat(TREE "/live/value", &status) == 0 && (status.st_mode & 0777) == 0644);
    require(stat(TREE "/trace", &status) == 0 && (status.st_mode & 0777) == 0444);
    value(TREE "/alias/value", "35\n");
    int fd = open(TREE "/live/value", O_WRONLY); require(fd >= 0);
    require(write(fd, "18446744073709551615\n", 21) == 21);
    require(close(fd) == 0); value(TREE "/alias/value", "18446744073709551615\n");
    char link[256]; ssize_t link_bytes = readlink(TREE "/alias", link, sizeof(link));
    require(link_bytes == 4 && !memcmp(link, "live", 4));
    errno = 0; require(open(TREE "/setup_complete", O_RDONLY) == -1 && errno == ENOENT);
    pid_t child = fork(); require(child >= 0);
    if (child == 0) { value(TREE "/live/slow", "done\n"); _exit(0); }
    long deadline = milliseconds() + 5000;
    for (;;) {
        char active[2]; require(read_file(TREE "/live/active", active, 2) == 2);
        if (active[0] == '1') break;
        require(milliseconds() < deadline); usleep(1000);
    }
    long started = milliseconds();
    require(syscall(SYS_delete_module, "mckernel_sysfs_tree_verify", 0) == 0);
    long drain = milliseconds() - started;
    int result; require(waitpid(child, &result, 0) == child && WIFEXITED(result) && WEXITSTATUS(result) == 0);
    errno = 0; require(open(ROOT, O_RDONLY) == -1 && errno == ENOENT);
    printf("NATIVE_SYSFS_TREE PASS reference_cases=%d drain_ms=%ld namespace_removed=1\n", cases, drain);
    return 0;
}
