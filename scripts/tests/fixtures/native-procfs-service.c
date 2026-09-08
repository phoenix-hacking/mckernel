/* SPDX-License-Identifier: GPL-2.0-only */
/* Linux-side verifier: reads the real McKernel procfs service in a guest. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

static unsigned int snapshots;
static int open_stat(void)
{
	for (unsigned int retry = 0; retry != 5000; ++retry) {
		int fd = open("/proc/mcos0/stat", O_RDONLY);
		if (fd >= 0) return fd;
		assert(errno == EAGAIN);
		usleep(1000);
	}
	assert(!"procfs release capacity did not return");
	return -1;
}

static void stat_contents(int fd)
{
	char data[32] = {0};
	assert(pread(fd, data, sizeof(data), 0) == 5);
	assert(memcmp(data, "cpu0\n", 5) == 0);
	++snapshots;
}

int main(void)
{
	setbuf(stdout, NULL);
	alarm(90);
	int fd = open_stat();
	struct stat st;
	assert(fstat(fd, &st) == 0 && (st.st_mode & 0777) == 0444 && st.st_uid == 0 && st.st_gid == 0);
	errno = 0;
	assert(syscall(SYS_read, fd, (void *)1, 5) == -1 && errno == EFAULT);
	assert(lseek(fd, 0, SEEK_CUR) == 0);
	char data[256] = {0};
	assert(read(fd, data, 2) == 2 && memcmp(data, "cp", 2) == 0);
	int duplicate = dup(fd);
	assert(duplicate >= 0);
	assert(read(duplicate, data, sizeof(data)) == 3 && memcmp(data, "u0\n", 3) == 0);
	assert(read(fd, data, sizeof(data)) == 0);
	stat_contents(fd);
	assert(lseek(fd, 0, SEEK_CUR) == 5);
	errno = 0;
	assert(lseek(fd, 0, SEEK_END) == -1 && errno == EINVAL);
	assert(close(fd) == 0);
	assert(pread(duplicate, data, sizeof(data), 0) == 5 && memcmp(data, "cpu0\n", 5) == 0);
	assert(close(duplicate) == 0);

	fd = open("/proc/mcos0/mckernel", O_RDONLY);
	assert(fd >= 0);
	ssize_t size = read(fd, data, sizeof(data) - 1);
	assert(size > 2 && size < (ssize_t)sizeof(data) - 1 && data[size - 1] == '\n');
	assert(memchr(data, '-', size) != NULL);
	data[size] = 0;
	printf("NATIVE_PROCFS_VERSION %s", data);
	++snapshots;
	assert(close(fd) == 0);
	usleep(100000); /* Let both previous close callbacks publish their releases. */

	int descriptors[64];
	for (unsigned int index = 0; index != 64; ++index) descriptors[index] = open_stat();
	errno = 0;
	assert(open("/proc/mcos0/stat", O_RDONLY) == -1 && errno == EAGAIN);
	for (unsigned int index = 0; index != 64; ++index) stat_contents(descriptors[index]);
	for (unsigned int index = 0; index != 64; ++index) assert(close(descriptors[index]) == 0);
	for (unsigned int index = 0; index != 128; ++index) {
		fd = open_stat();
		stat_contents(fd);
		assert(close(fd) == 0);
	}
	/* The host verifier requires an exact terminal release for every snapshot. */
	usleep(250000);
	assert(snapshots == 194);
	printf("NATIVE_PROCFS_SERVICE PASS snapshots=%u capacity=64 exhausted=1 repeated=128 copy_faults=1 partial_reads=2 shared_offset=1 applications=0\n", snapshots);
	return 0;
}
