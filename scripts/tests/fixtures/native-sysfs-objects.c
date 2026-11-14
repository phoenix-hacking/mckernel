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

#define ROOT "/sys/mckernel_sysfs_verify"
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
	assert(stat(VALUE, &st) == 0 && (st.st_mode & 0777) == 0644);
	expect_read(VALUE, "35\n");
	expect_read(ROOT "/alias/value", "35\n");
	expect_read(ROOT "/reused/nested/value", "35\n");
	char link[32] = {0};
	assert(readlink(ROOT "/alias", link, sizeof(link)) == 5);
	assert(memcmp(link, "child", 5) == 0);
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
	assert(syscall(SYS_delete_module, "mckernel_sysfs_objects_verify", O_NONBLOCK) == 0);
	long elapsed = milliseconds() - before;
	int status;
	assert(waitpid(slow, &status, 0) == slow);
	assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
	assert(stat(ROOT, &st) == -1 && errno == ENOENT);
	errno = 0;
	off_t seek = lseek(held, 0, SEEK_SET);
	int removed_at_seek = seek == -1;
	assert(removed_at_seek && errno == ENODEV);
	assert(close(held) == 0);
	printf("MCKERNEL_SYSFS_USER PASS concurrent_writes=512 concurrent_reads=512 duplicate_survival=1 name_reuse=1 overcounts=2 active_drain=1 removed_fd=ENODEV removed_at_seek=%d drain_ms=%ld\n", removed_at_seek, elapsed);
	return 0;
}
