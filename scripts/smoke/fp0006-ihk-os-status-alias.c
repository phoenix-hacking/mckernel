// SPDX-License-Identifier: GPL-2.0
/*
 * Produce the bounded legacy side of the FP-0006 OS-status alias witness.
 *
 * This program only issues read-only status ioctls against a caller-supplied
 * live /dev/mcos0.  It is a capture producer, not a result authority, and it
 * cannot award gate or tracker credit.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define IHK_OS_QUERY_STATUS 0x00112a03UL
#define IHK_OS_STATUS 0x00112a14UL
#define IHK_OS_STATUS_RUNNING 5L
#define VECTOR_COUNT 4U

struct vector {
	const char *id;
	unsigned long request;
	unsigned long argument;
};

static const struct vector vectors[VECTOR_COUNT] = {
	{"query-status-arg0", IHK_OS_QUERY_STATUS, 0UL},
	{"query-status-arg-u64-max", IHK_OS_QUERY_STATUS, UINT64_MAX},
	{"status-alias-arg0", IHK_OS_STATUS, 0UL},
	{"status-alias-arg-u64-max", IHK_OS_STATUS, UINT64_MAX},
};

static const char raw_records[] =
	"{\"argument\":0,\"request\":1124867,\"sequence\":0,"
	"\"vector_id\":\"query-status-arg0\"}\n"
	"{\"argument\":18446744073709551615,\"request\":1124867,"
	"\"sequence\":1,\"vector_id\":\"query-status-arg-u64-max\"}\n"
	"{\"argument\":0,\"request\":1124884,\"sequence\":2,"
	"\"vector_id\":\"status-alias-arg0\"}\n"
	"{\"argument\":18446744073709551615,\"request\":1124884,"
	"\"sequence\":3,\"vector_id\":\"status-alias-arg-u64-max\"}\n";

static int write_all(int descriptor, const char *data, size_t length)
{
	while (length != 0) {
		ssize_t written = write(descriptor, data, length);

		if (written < 0) {
			if (errno == EINTR)
				continue;
			return -1;
		}
		if (written == 0) {
			errno = EIO;
			return -1;
		}
		data += (size_t)written;
		length -= (size_t)written;
	}
	return 0;
}

static int write_member(int directory, const char *name,
			const char *data, size_t length)
{
	struct stat metadata;
	int descriptor;
	int saved_errno;

	descriptor = openat(directory, name,
			    O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW,
			    0400);
	if (descriptor < 0)
		return -1;
	if (fchmod(descriptor, 0444) < 0 ||
	    write_all(descriptor, data, length) < 0 ||
	    fsync(descriptor) < 0 || fstat(descriptor, &metadata) < 0 ||
	    !S_ISREG(metadata.st_mode) || metadata.st_nlink != 1 ||
	    (metadata.st_mode & 07777) != 0444 ||
	    metadata.st_size != (off_t)length) {
		saved_errno = errno != 0 ? errno : EIO;
		close(descriptor);
		errno = saved_errno;
		return -1;
	}
	if (close(descriptor) < 0)
		return -1;
	return 0;
}

static int append_result(char *output, size_t capacity, size_t *used,
			 unsigned int sequence, long interface_return,
			 int saved_errno)
{
	int length;

	length = snprintf(output + *used, capacity - *used,
		"{\"errno\":%d,\"interface_return\":%ld,"
		"\"normalized_return\":%ld,\"sequence\":%u,"
		"\"surface\":\"legacy-live-ioctl\",\"vector_id\":\"%s\"}\n",
		saved_errno, interface_return, interface_return,
		sequence, vectors[sequence].id);
	if (length < 0 || (size_t)length >= capacity - *used) {
		errno = EOVERFLOW;
		return -1;
	}
	*used += (size_t)length;
	return 0;
}

static int append_ledger(char *output, size_t capacity, size_t *used,
			 unsigned int sequence, const char *phase, long status)
{
	int length;

	length = snprintf(output + *used, capacity - *used,
		"{\"minor\":0,\"phase\":\"%s\",\"sequence\":%u,"
		"\"status\":%ld,\"status_name\":\"RUNNING\","
		"\"surface\":\"legacy-live-ioctl\",\"vector_id\":\"%s\"}\n",
		phase, sequence, status, vectors[sequence].id);
	if (length < 0 || (size_t)length >= capacity - *used) {
		errno = EOVERFLOW;
		return -1;
	}
	*used += (size_t)length;
	return 0;
}

static int observe_running(int descriptor, long *status)
{
	int saved_errno;
	long value;

	errno = 0;
	value = ioctl(descriptor, IHK_OS_STATUS, 0UL);
	saved_errno = errno;
	if (value != IHK_OS_STATUS_RUNNING || saved_errno != 0) {
		errno = saved_errno != 0 ? saved_errno : EPROTO;
		return -1;
	}
	*status = value;
	return 0;
}

int main(int argc, char **argv)
{
	char ledger_records[4096];
	char result_records[2048];
	long before[VECTOR_COUNT];
	long after[VECTOR_COUNT];
	long returns[VECTOR_COUNT];
	int errnos[VECTOR_COUNT];
	struct stat named_device;
	struct stat open_device;
	size_t ledger_used = 0;
	size_t result_used = 0;
	unsigned int index;
	int device = -1;
	int output = -1;

	if (argc == 2 && strcmp(argv[1], "--describe") == 0) {
		fputs("{\"contract_id\":\"fp-0006-ihk-os-status-alias-v1\","
		      "\"gate_pass\":false,\"legacy_runtime_executed\":false,"
		      "\"surface\":\"legacy-live-ioctl\","
		      "\"tracker_credit\":false}\n", stdout);
		return 0;
	}
	if (argc != 3 || strcmp(argv[1], "/dev/mcos0") != 0) {
		fprintf(stderr, "usage: %s /dev/mcos0 OUTPUT_DIRECTORY\n", argv[0]);
		return 64;
	}
	if (lstat(argv[1], &named_device) < 0 ||
	    S_ISLNK(named_device.st_mode) || !S_ISCHR(named_device.st_mode)) {
		fputs("live /dev/mcos0 is unavailable or is not a character device\n",
		      stderr);
		return 1;
	}
	device = open(argv[1], O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (device < 0 || fstat(device, &open_device) < 0 ||
	    !S_ISCHR(open_device.st_mode) ||
	    named_device.st_dev != open_device.st_dev ||
	    named_device.st_ino != open_device.st_ino ||
	    named_device.st_rdev != open_device.st_rdev) {
		fputs("live /dev/mcos0 identity changed while opening\n", stderr);
		if (device >= 0)
			close(device);
		return 1;
	}
	output = open(argv[2], O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
	if (output < 0) {
		fputs("capture output directory is unavailable\n", stderr);
		close(device);
		return 1;
	}

	for (index = 0; index < VECTOR_COUNT; ++index) {
		if (observe_running(device, &before[index]) < 0) {
			fputs("OS did not remain RUNNING before status vector\n", stderr);
			close(output);
			close(device);
			return 1;
		}
		errno = 0;
		returns[index] = ioctl(device, vectors[index].request,
				       vectors[index].argument);
		errnos[index] = errno;
		if (observe_running(device, &after[index]) < 0 ||
		    returns[index] != IHK_OS_STATUS_RUNNING ||
		    errnos[index] != 0 || before[index] != after[index] ||
		    append_result(result_records, sizeof(result_records),
				  &result_used, index, returns[index],
				  errnos[index]) < 0 ||
		    append_ledger(ledger_records, sizeof(ledger_records),
				  &ledger_used, index, "before",
				  before[index]) < 0 ||
		    append_ledger(ledger_records, sizeof(ledger_records),
				  &ledger_used, index, "after",
				  after[index]) < 0) {
			fputs("status vector or state ledger differs from the contract\n",
			      stderr);
			close(output);
			close(device);
			return 1;
		}
	}
	if (close(device) < 0) {
		fputs("cannot close /dev/mcos0 capture descriptor\n", stderr);
		close(output);
		return 1;
	}

	if (write_member(output, "raw.jsonl", raw_records,
			 sizeof(raw_records) - 1) < 0 ||
	    write_member(output, "result.jsonl", result_records,
			 result_used) < 0 ||
	    write_member(output, "state-ledger.jsonl", ledger_records,
			 ledger_used) < 0 || fsync(output) < 0) {
		fputs("capture publication failed\n", stderr);
		close(output);
		return 1;
	}
	if (close(output) < 0) {
		fputs("cannot close capture output directory\n", stderr);
		return 1;
	}
	return 0;
}
