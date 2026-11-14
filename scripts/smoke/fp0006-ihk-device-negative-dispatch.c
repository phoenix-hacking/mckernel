// SPDX-License-Identifier: GPL-2.0
/*
 * Emit the bounded legacy side of the FP-0006 negative-dispatch witness.
 *
 * This program is a capture producer, not a gate oracle.  It performs two
 * live ioctls against a caller-selected IHK character device and records the
 * normalized results plus a /sys/class/mcos occupancy ledger.  The Python
 * reviewer owns schema validation and the still-missing independent result
 * authority owns any future gate decision.
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

#define IHK_DEVICE_DESTROY_OS 0x00112901UL
#define UNKNOWN_DEVICE_REQUEST 0xffffffffUL
#define EXPECTED_ERRNO EINVAL
#define MINOR_COUNT 64U

static const char raw_records[] =
	"{\"argument\":0,\"request\":4294967295,\"sequence\":0,"
	"\"vector_id\":\"unknown-device-request-ffffffff-arg0\"}\n"
	"{\"argument\":63,\"request\":1124609,\"sequence\":1,"
	"\"vector_id\":\"destroy-known-empty-minor63\"}\n";

static int count_bits(uint64_t value)
{
	int count = 0;

	while (value) {
		count += (int)(value & 1U);
		value >>= 1;
	}
	return count;
}

static int capture_occupied_bitmap(uint64_t *bitmap)
{
	unsigned int minor;
	uint64_t observed = 0;

	for (minor = 0; minor < MINOR_COUNT; ++minor) {
		char path[64];
		struct stat metadata;
		int length;

		length = snprintf(path, sizeof(path),
				  "/sys/class/mcos/mcos%u", minor);
		if (length < 0 || (size_t)length >= sizeof(path)) {
			errno = ENAMETOOLONG;
			return -1;
		}
		if (lstat(path, &metadata) == 0) {
			observed |= UINT64_C(1) << minor;
			continue;
		}
		if (errno != ENOENT)
			return -1;
	}
	*bitmap = observed;
	return 0;
}

static int write_all(int descriptor, const char *data, size_t length)
{
	while (length) {
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
	int descriptor;
	int saved_errno;

	descriptor = openat(directory, name,
			    O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW,
			    0400);
	if (descriptor < 0)
		return -1;
	if (fchmod(descriptor, 0444) < 0 ||
	    write_all(descriptor, data, length) < 0 ||
	    fsync(descriptor) < 0) {
		saved_errno = errno;
		close(descriptor);
		errno = saved_errno;
		return -1;
	}
	if (close(descriptor) < 0)
		return -1;
	return 0;
}

static int append_ledger(char *buffer, size_t capacity, size_t *used,
			 unsigned int sequence, const char *vector_id,
			 const char *phase, uint64_t bitmap)
{
	int length;

	length = snprintf(buffer + *used, capacity - *used,
		"{\"minor63_empty\":true,\"occupied_minor_bitmap\":"
		"\"%016" PRIx64 "\",\"occupied_minor_count\":%d,"
		"\"phase\":\"%s\",\"sequence\":%u,"
		"\"surface\":\"legacy-live-ioctl\",\"vector_id\":\"%s\"}\n",
		bitmap, count_bits(bitmap), phase, sequence, vector_id);
	if (length < 0 || (size_t)length >= capacity - *used) {
		errno = EOVERFLOW;
		return -1;
	}
	*used += (size_t)length;
	return 0;
}

static long normalized_return(long interface_return, int saved_errno)
{
	if (interface_return == -1)
		return -(long)saved_errno;
	return interface_return;
}

int main(int argc, char **argv)
{
	const char *unknown_id = "unknown-device-request-ffffffff-arg0";
	const char *destroy_id = "destroy-known-empty-minor63";
	uint64_t states[4];
	char result_records[1024];
	char ledger_records[2048];
	size_t ledger_used = 0;
	struct stat metadata;
	long returns[2];
	long normalized[2];
	int errnos[2];
	int device = -1;
	int output = -1;
	int result_length;
	int capture_matches;

	if (argc == 2 && strcmp(argv[1], "--describe") == 0) {
		fputs("{\"contract_id\":\"fp-0006-ihk-device-negative-dispatch-v1\","
		      "\"live_execution_performed\":false,"
		      "\"surface\":\"legacy-live-ioctl\","
		      "\"tracker_credit\":false}\n", stdout);
		return 0;
	}
	if (argc != 3) {
		fprintf(stderr, "usage: %s DEVICE OUTPUT_DIRECTORY\n", argv[0]);
		return 64;
	}

	device = open(argv[1], O_RDWR | O_CLOEXEC | O_NOFOLLOW);
	if (device < 0 || fstat(device, &metadata) < 0 ||
	    !S_ISCHR(metadata.st_mode)) {
		fprintf(stderr, "legacy IHK device is unavailable or not a character device\n");
		if (device >= 0)
			close(device);
		return 1;
	}
	output = open(argv[2], O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
	if (output < 0) {
		fprintf(stderr, "capture output directory is unavailable\n");
		close(device);
		return 1;
	}

	if (capture_occupied_bitmap(&states[0]) < 0 ||
	    (states[0] & (UINT64_C(1) << 63)) != 0) {
		fprintf(stderr, "minor 63 is not a known-empty capture precondition\n");
		close(output);
		close(device);
		return 1;
	}

	errno = 0;
	returns[0] = ioctl(device, UNKNOWN_DEVICE_REQUEST, 0UL);
	errnos[0] = errno;
	normalized[0] = normalized_return(returns[0], errnos[0]);
	if (capture_occupied_bitmap(&states[1]) < 0 ||
	    capture_occupied_bitmap(&states[2]) < 0 ||
	    (states[2] & (UINT64_C(1) << 63)) != 0) {
		fprintf(stderr, "cannot establish the post-unknown/pre-destroy state ledger\n");
		close(output);
		close(device);
		return 1;
	}

	errno = 0;
	returns[1] = ioctl(device, IHK_DEVICE_DESTROY_OS, 63UL);
	errnos[1] = errno;
	normalized[1] = normalized_return(returns[1], errnos[1]);
	if (capture_occupied_bitmap(&states[3]) < 0) {
		fprintf(stderr, "cannot establish the final state ledger\n");
		close(output);
		close(device);
		return 1;
	}
	close(device);

	result_length = snprintf(result_records, sizeof(result_records),
		"{\"errno\":%d,\"interface_return\":%ld,"
		"\"normalized_return\":%ld,\"sequence\":0,"
		"\"surface\":\"legacy-live-ioctl\",\"vector_id\":\"%s\"}\n"
		"{\"errno\":%d,\"interface_return\":%ld,"
		"\"normalized_return\":%ld,\"sequence\":1,"
		"\"surface\":\"legacy-live-ioctl\",\"vector_id\":\"%s\"}\n",
		errnos[0], returns[0], normalized[0], unknown_id,
		errnos[1], returns[1], normalized[1], destroy_id);
	if (result_length < 0 || (size_t)result_length >= sizeof(result_records) ||
	    append_ledger(ledger_records, sizeof(ledger_records), &ledger_used,
			  0, unknown_id, "before", states[0]) < 0 ||
	    append_ledger(ledger_records, sizeof(ledger_records), &ledger_used,
			  0, unknown_id, "after", states[1]) < 0 ||
	    append_ledger(ledger_records, sizeof(ledger_records), &ledger_used,
			  1, destroy_id, "before", states[2]) < 0 ||
	    append_ledger(ledger_records, sizeof(ledger_records), &ledger_used,
			  1, destroy_id, "after", states[3]) < 0) {
		fprintf(stderr, "capture serialization failed\n");
		close(output);
		return 1;
	}

	if (write_member(output, "raw.jsonl", raw_records,
			 sizeof(raw_records) - 1) < 0 ||
	    write_member(output, "result.jsonl", result_records,
			 (size_t)result_length) < 0 ||
	    write_member(output, "state-ledger.jsonl", ledger_records,
			 ledger_used) < 0) {
		fprintf(stderr, "capture publication failed\n");
		close(output);
		return 1;
	}
	if (fsync(output) < 0) {
		fprintf(stderr, "capture directory synchronization failed\n");
		close(output);
		return 1;
	}
	close(output);

	capture_matches =
		returns[0] == -1 && errnos[0] == EXPECTED_ERRNO &&
		normalized[0] == -EXPECTED_ERRNO &&
		returns[1] == -1 && errnos[1] == EXPECTED_ERRNO &&
		normalized[1] == -EXPECTED_ERRNO &&
		states[0] == states[1] && states[1] == states[2] &&
		states[2] == states[3] &&
		(states[3] & (UINT64_C(1) << 63)) == 0;
	if (!capture_matches) {
		fprintf(stderr, "captured legacy observation differs from the bounded vector contract\n");
		return 2;
	}
	return 0;
}
