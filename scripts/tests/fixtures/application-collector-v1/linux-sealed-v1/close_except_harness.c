#define _GNU_SOURCE
#include <errno.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>

static long fake_close_range(unsigned first, unsigned last, unsigned flags);
static int fake_getrlimit(int resource, struct rlimit *limit);
static int fake_close(int fd);

#define COLLECTOR_CLOSE_RANGE_CALL fake_close_range
#define COLLECTOR_GETRLIMIT_CALL fake_getrlimit
#define COLLECTOR_CLOSE_CALL fake_close
#define main collector_program_main
#include "collector.c"
#undef main

struct range_result { int result, error; };
static struct range_result ranges[3];
static unsigned range_count, range_index, range_first[3], range_last[3];
static int limit_result, limit_error;
static struct rlimit fake_limit;
static bool descriptors[4097];
static int close_error_fd, close_error;
static unsigned assertion_count;

static void require(bool value)
{
    assertion_count++;
    if (!value) { fprintf(stderr, "assertion %u\n", assertion_count); exit(1); }
}

static void reset(void)
{
    range_count = range_index = 0;
    for (unsigned i = 0; i < 3; ++i) ranges[i] = (struct range_result){ 0, 0 };
    limit_result = limit_error = 0;
    fake_limit.rlim_cur = fake_limit.rlim_max = 16;
    close_error_fd = -1; close_error = 0;
    for (unsigned i = 0; i < sizeof descriptors / sizeof descriptors[0]; ++i)
        descriptors[i] = false;
}

static long fake_close_range(unsigned first, unsigned last, unsigned flags)
{
    require(flags == 0 && range_index < range_count);
    range_first[range_index] = first; range_last[range_index] = last;
    struct range_result result = ranges[range_index++];
    if (result.result != 0) errno = result.error;
    else {
        unsigned stop = last < 4096 ? last : 4096;
        for (unsigned fd = first; fd <= stop; ++fd) descriptors[fd] = false;
    }
    return result.result;
}

static int fake_getrlimit(int resource, struct rlimit *limit)
{
    require(resource == RLIMIT_NOFILE);
    if (limit_result != 0) { errno = limit_error; return -1; }
    *limit = fake_limit; return 0;
}

static int fake_close(int fd)
{
    if (fd == close_error_fd) { errno = close_error; return -1; }
    if (fd < 0 || (unsigned)fd >= sizeof descriptors / sizeof descriptors[0] || !descriptors[fd]) {
        errno = EBADF; return -1;
    }
    descriptors[fd] = false; return 0;
}

static void fallback_case(unsigned failed, int error)
{
    reset(); range_count = 3; ranges[failed] = (struct range_result){ -1, error };
    descriptors[3] = descriptors[4] = descriptors[6] = descriptors[8] = true;
    fake_limit.rlim_cur = 6; fake_limit.rlim_max = 16;
    require(close_except(4, 6));
    require(range_index == failed + 1);
    require(!descriptors[3] && descriptors[4] && descriptors[6] && !descriptors[8]);
}

static void unexpected_fast_error(unsigned failed)
{
    reset(); range_count = 3; ranges[failed] = (struct range_result){ -1, EIO };
    require(!close_except(4, 6) && errno == EIO && range_index == failed + 1);
}

int main(void)
{
    reset(); range_count = 3;
    require(close_except(5, 7));
    require(range_index == 3 && range_first[0] == 3 && range_last[0] == 4 &&
            range_first[1] == 6 && range_last[1] == 6 && range_first[2] == 8 && range_last[2] == UINT_MAX);

    reset(); range_count = 1; require(close_except(3, 4));
    require(range_index == 1 && range_first[0] == 5);
    reset(); range_count = 2; require(close_except(5, 4));
    require(range_first[0] == 3 && range_last[0] == 3 && range_first[1] == 6);
    require(!close_except(2, 4) && errno == EINVAL);
    require(!close_except(-1, 4) && errno == EINVAL);
    require(!close_except(4, 4) && errno == EINVAL);

    for (unsigned failed = 0; failed < 3; ++failed) {
        fallback_case(failed, ENOSYS);
        fallback_case(failed, EPERM);
    }
    unexpected_fast_error(0); unexpected_fast_error(1); unexpected_fast_error(2);

    reset(); range_count = 1; ranges[0] = (struct range_result){ -1, EPERM };
    limit_result = -1; limit_error = EMFILE;
    require(!close_except(4, 5) && errno == EMFILE);
    reset(); range_count = 1; ranges[0] = (struct range_result){ -1, EPERM };
    fake_limit.rlim_max = RLIM_INFINITY;
    require(!close_except(4, 5) && errno == EOVERFLOW);
    reset(); range_count = 1; ranges[0] = (struct range_result){ -1, EPERM };
    fake_limit.rlim_max = 4097;
    require(!close_except(4, 5) && errno == EOVERFLOW);
    reset(); range_count = 1; ranges[0] = (struct range_result){ -1, EPERM };
    descriptors[3] = descriptors[4] = descriptors[5] = true;
    close_error_fd = 3; close_error = EIO;
    require(!close_except(4, 5) && errno == EIO && descriptors[4] && descriptors[5]);

    puts("PASS close-except");
    return 0;
}
