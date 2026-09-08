/* SPDX-License-Identifier: GPL-2.0-only */
/* Run only inside the disposable native Linux guest. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define ROOT "/proc/mckernel_procfs_verify"
#define VALUE ROOT "/child/value"

static long milliseconds(void)
{
	struct timespec ts;
	assert(clock_gettime(CLOCK_MONOTONIC, &ts) == 0);
	return ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static void expect_read(const char *path, const char *expected)
{
	char bytes[128] = {0};
	int fd = open(path, O_RDONLY);
	assert(fd >= 0);
	ssize_t count = read(fd, bytes, sizeof(bytes));
	assert(count == (ssize_t)strlen(expected));
	assert(memcmp(bytes, expected, count) == 0);
	assert(close(fd) == 0);
}

static void write_value(const char *text, int expected_errno)
{
	int fd = open(VALUE, O_WRONLY);
	assert(fd >= 0);
	errno = 0;
	ssize_t count = write(fd, text, strlen(text));
	if (expected_errno) {
		assert(count == -1 && errno == expected_errno);
	} else {
		assert(count == (ssize_t)strlen(text));
	}
	assert(close(fd) == 0);
}

int main(void)
{
	setbuf(stdout, NULL);
	struct stat st;
	assert(stat(VALUE, &st) == 0 && (st.st_mode & 0777) == 0644 && st.st_uid == 1000 && st.st_gid == 1000);
	expect_read(VALUE, "35\n");
	expect_read(ROOT "/reused/nested/value", "35\n");
	write_value("18446744073709551615\n", 0);
	expect_read(VALUE, "18446744073709551615\n");
	write_value("18446744073709551616\n", EINVAL);
	write_value("-1\n", EINVAL);
	write_value("hello\n", EINVAL);
	expect_read(VALUE, "18446744073709551615\n");
	int overflow = open(ROOT "/child/overflow", O_RDWR);
	assert(overflow >= 0);
	char bytes[128];
	errno = 0;
	assert(read(overflow, bytes, sizeof(bytes)) == -1 && errno == EOVERFLOW);
	errno = 0;
	assert(write(overflow, "1", 1) == -1 && errno == EOVERFLOW);
	assert(close(overflow) == 0);


    int fd = open(VALUE, O_RDWR);
    assert(fd >= 0);
    assert(lseek(fd, 0, SEEK_SET) == 0);
    assert(read(fd, bytes, 1) == 1 && bytes[0] == '1');
    assert(lseek(fd, 0, SEEK_CUR) == 1);
    assert(pread(fd, bytes, 1, 0) == 1 && bytes[0] == '1');
    assert(lseek(fd, 0, SEEK_CUR) == 1);
    assert(lseek(fd, -1, SEEK_CUR) == 0);
    errno = 0;
    assert(lseek(fd, 0, SEEK_END) == -1 && errno == EINVAL);
    assert(lseek(fd, 0, SEEK_CUR) == 0);
    errno = 0;
    assert(syscall(SYS_read, fd, (uintptr_t)1, 3) == -1 && errno == EFAULT);
    assert(lseek(fd, 0, SEEK_CUR) == 0);
    errno = 0;
    assert(syscall(SYS_write, fd, (uintptr_t)1, 3) == -1 && errno == EFAULT);
    assert(lseek(fd, 0, SEEK_CUR) == 0);
    assert(syscall(SYS_read, fd, (uintptr_t)1, 0) == 0);
    assert(syscall(SYS_write, fd, (uintptr_t)1, 0) == 0);
    int duplicated = dup(fd);
    assert(duplicated >= 0);
    assert(read(duplicated, bytes, 1) == 1 && bytes[0] == '1');
    assert(lseek(fd, 0, SEEK_CUR) == 1);
    assert(close(duplicated) == 0 && close(fd) == 0);
    expect_read(VALUE, "18446744073709551615\n");
    errno = 0;
    assert(open(ROOT "/child/denied", O_RDONLY) == -1 && errno == EPERM);
    fd = open(ROOT "/active", O_WRONLY);
    assert(fd >= 0);
    errno = 0;
    assert(write(fd, "1", 1) == -1 && errno == EIO);
    assert(close(fd) == 0);
    fd = open(ROOT "/child/large", O_RDONLY);
    assert(fd >= 0);
    char *large = malloc(16384);
    assert(large != NULL);
    memset(large, 0, 16384);
    assert(read(fd, large, 16384) == 4096);
    assert(read(fd, large + 4096, 12288) == 4096);
    for (int i = 0; i < 8192; ++i) assert(large[i] == 'Z');
    for (int i = 8192; i < 16384; ++i) assert(large[i] == 0);
    assert(read(fd, large, 16384) == 0);
    assert(pread(fd, large, 2, 8191) == 1 && large[0] == 'Z');
    assert(lseek(fd, 0, SEEK_CUR) == 8192);
    free(large);
    assert(close(fd) == 0);

	pid_t writers[4];
	for (unsigned worker = 0; worker < 4; ++worker) {
		writers[worker] = fork();
		assert(writers[worker] >= 0);
		if (writers[worker] == 0) {
			for (unsigned sample = 0; sample < 128; ++sample) {
				char text[64];
				int size = snprintf(text, sizeof(text), "%u\n", worker * 100000 + sample);
				assert(size > 0 && size < (int)sizeof(text));
				write_value(text, 0);
				int fd = open(VALUE, O_RDONLY);
				assert(fd >= 0);
				ssize_t count = read(fd, text, sizeof(text) - 1);
				assert(count >= 2 && count < (ssize_t)sizeof(text));
				text[count] = 0;
				char *end = NULL;
				errno = 0;
				(void)strtoull(text, &end, 10);
				assert(errno == 0 && end == text + count - 1 && *end == '\n');
				assert(close(fd) == 0);
			}
			_exit(0);
		}
	}
	for (unsigned worker = 0; worker < 4; ++worker) {
		int status;
		assert(waitpid(writers[worker], &status, 0) == writers[worker]);
		assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
	}
	write_value("35\n", 0);
	int held = open(VALUE, O_RDONLY);
	assert(held >= 0);
	assert(read(held, bytes, sizeof(bytes)) == 3);
	int held_duplicate = dup(held);
	assert(held_duplicate >= 0);

	pid_t slow = fork();
	assert(slow >= 0);
	if (slow == 0) {
		expect_read(ROOT "/child/slow", "35\n");
		_exit(0);
	}
	long deadline = milliseconds() + 10000;
	for (;;) {
		int fd = open(ROOT "/active", O_RDONLY);
		assert(fd >= 0);
		assert(read(fd, bytes, sizeof(bytes)) == 2);
		assert(close(fd) == 0);
		if (bytes[0] == '1') break;
		assert(milliseconds() < deadline);
		usleep(1000);
	}
	long before = milliseconds();
	assert(syscall(SYS_delete_module, "mckernel_procfs_objects_verify", O_NONBLOCK) == 0);
	long elapsed = milliseconds() - before;
	int status;
	assert(waitpid(slow, &status, 0) == slow);
	assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
	assert(stat(ROOT, &st) == -1 && errno == ENOENT);
	errno = 0;
    assert(read(held, bytes, sizeof(bytes)) == -1 && errno == EIO);
    errno = 0;
    assert(lseek(held, 0, SEEK_SET) == -1 && errno == EINVAL);
    errno = 0;
    assert(read(held_duplicate, bytes, sizeof(bytes)) == -1 && errno == EIO);
    assert(close(held) == 0 && close(held_duplicate) == 0);
    printf("MCKERNEL_PROCFS_USER PASS concurrent_writes=512 concurrent_reads=512 duplicate_survival=1 name_reuse=1 overcounts=2 copy_faults=2 failed_open=1 partial_bytes=8192 pread_position=1 active_drain=1 removed_read=EIO removed_seek=EINVAL drain_ms=%ld\n", elapsed);
	return 0;
}
