#define _POSIX_C_SOURCE 200809L

#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>

enum { BUFFER_SIZE = 1024 * 1024 };

int main(void)
{
	unsigned char *buffer;
	uint64_t sum = 0;
	struct timespec now;
	struct utsname uts;
	int fd;
	size_t i;

	buffer = malloc(BUFFER_SIZE);
	if (!buffer) {
		perror("malloc");
		return 1;
	}

	for (i = 0; i < BUFFER_SIZE; ++i) {
		buffer[i] = (unsigned char)(i * 17U + 3U);
		sum += buffer[i];
	}

	if (sum != UINT64_C(133693440)) {
		fprintf(stderr, "unexpected checksum: %llu\n",
				(unsigned long long)sum);
		free(buffer);
		return 2;
	}
	if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
		perror("clock_gettime");
		free(buffer);
		return 3;
	}
	if (uname(&uts) != 0 || uts.sysname[0] == '\0' || getpid() <= 0) {
		perror("uname/getpid");
		free(buffer);
		return 4;
	}

	fd = open("/dev/null", O_WRONLY);
	if (fd < 0 || write(fd, buffer, 4096) != 4096 || close(fd) != 0) {
		perror("delegated file I/O");
		free(buffer);
		return 5;
	}

	free(buffer);
	puts("mckernel-rust-smoke: OK bytes=1048576 sum=133693440");
	return 0;
}
