/* SPDX-License-Identifier: GPL-2.0-only */
/* Linux controller for the opt-in real McKernel sysfs verification image. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define BASE "/sys/class/mcos/mcos0/sys/test/"
#define ROOT BASE "native/"
#define ITEMS ROOT "items/"
#define CHECK(x) do { if (!(x)) { \
    fprintf(stderr, "NATIVE_GUEST_SYSFS_USER FAIL line=%d errno=%d\n", __LINE__, errno); \
    exit(1); \
} } while (0)

static double deadline;

static double now(void)
{
    struct timespec value;
    CHECK(clock_gettime(CLOCK_MONOTONIC, &value) == 0);
    return value.tv_sec + value.tv_nsec / 1e9;
}

static void pause_poll(void)
{
    CHECK(now() < deadline);
    CHECK(usleep(1000) == 0);
}

static ssize_t io(const char *path, bool writing, void *buffer, size_t size)
{
    int fd = open(path, writing ? O_WRONLY : O_RDONLY);
    if (fd < 0)
        return -errno;
    ssize_t result = writing ? write(fd, buffer, size) : read(fd, buffer, size);
    int error = errno;
    CHECK(close(fd) == 0);
    return result < 0 ? -error : result;
}

static void expect_bytes(const char *path, const char *expected, size_t size)
{
    char actual[8192];
    CHECK(size <= sizeof(actual));
    CHECK(io(path, false, actual, sizeof(actual)) == (ssize_t)size);
    CHECK(memcmp(actual, expected, size) == 0);
}

static void expect_text(const char *path, const char *expected)
{
    expect_bytes(path, expected, strlen(expected));
}

struct state {
    unsigned phase, releases, forbidden, reads, stores;
};

static struct state status(void)
{
    char text[128] = {0};
    struct state value;
    ssize_t count = io(ROOT "status", false, text, sizeof(text) - 1);
    CHECK(count > 0 && count < (ssize_t)sizeof(text));
    CHECK(sscanf(text, "%u %u %u %u %u", &value.phase, &value.releases,
                 &value.forbidden, &value.reads, &value.stores) == 5);
    CHECK(value.forbidden == 0);
    return value;
}

static void specials(void)
{
    uint64_t wide = UINT64_C(0xf123456789abcde0);
    uint32_t narrow = (uint32_t)wide;
    char expected[512];
    CHECK(snprintf(expected, sizeof(expected), "%" PRId32 "\n", (int32_t)narrow) > 0);
    expect_text(BASE "remote/d32", expected);
    CHECK(snprintf(expected, sizeof(expected), "%" PRId64 "\n", (int64_t)wide) > 0);
    expect_text(BASE "remote/d64", expected);
    CHECK(snprintf(expected, sizeof(expected), "%" PRIu32 "\n", narrow) > 0);
    expect_text(BASE "remote/u32", expected);
    CHECK(snprintf(expected, sizeof(expected), "%" PRIu64 "\n", wide) > 0);
    expect_text(BASE "remote/u64", expected);
    CHECK(snprintf(expected, sizeof(expected), "%" PRIu32 "K\n", narrow >> 10) > 0);
    expect_text(BASE "remote/u32K", expected);
    expect_text(BASE "remote/s", "string(remote)\n");
    CHECK(snprintf(expected, sizeof(expected), "%02x,%08x\n",
                   (unsigned)((wide >> 32) & 255), narrow) > 0);
    expect_text(BASE "remote/pb", expected);
    size_t used = 0;
    for (unsigned bit = 0; bit < 40; ++bit) {
        if (!(wide & (UINT64_C(1) << bit)))
            continue;
        unsigned first = bit;
        while (bit + 1 < 40 && (wide & (UINT64_C(1) << (bit + 1))))
            ++bit;
        int n = snprintf(expected + used, sizeof(expected) - used,
                         "%s%u", used ? "," : "", first);
        CHECK(n > 0 && (size_t)n < sizeof(expected) - used);
        used += n;
        if (bit != first) {
            n = snprintf(expected + used, sizeof(expected) - used, "-%u", bit);
            CHECK(n > 0 && (size_t)n < sizeof(expected) - used);
            used += n;
        }
    }
    CHECK(used + 1 < sizeof(expected));
    expected[used++] = '\n';
    expect_bytes(BASE "remote/pbl", expected, used);
    char mask[4096];
    for (int group = 0; group < 455; ++group) {
        CHECK(snprintf(mask + group * 9, sizeof(mask) - group * 9,
                       "%08x%c", UINT32_MAX, group == 454 ? '\n' : ',') == 9);
    }
    expect_bytes(ITEMS "full-mask", mask, 4095);
    CHECK(io(ITEMS "full-mask", true, "x", 1) == -ENOSPC);
}

struct worker {
    unsigned index;
};

static void *values(void *argument)
{
    unsigned index = ((struct worker *)argument)->index;
    char path[256], expected[64];
    CHECK(snprintf(path, sizeof(path), ITEMS "value%u", index) > 0);
    expect_text(path, "0\n");
    for (unsigned round = 0; round < 64; ++round) {
        uint64_t value = (index + 1) * UINT64_C(1000000) + round;
        int count = snprintf(expected, sizeof(expected), "%" PRIu64 "\n", value);
        CHECK(count > 0 && count < (int)sizeof(expected));
        CHECK(io(path, true, expected, count) == count);
        expect_text(path, expected);
    }
    return NULL;
}

int main(void)
{
    CHECK(geteuid() == 0);
    deadline = now() + 90;
    alarm(100);
    while (access(ROOT "control", F_OK) != 0) {
        CHECK(errno == ENOENT);
        pause_poll();
    }
    struct state state = status();
    CHECK(state.phase == 0 && state.releases == 0 && state.reads == 0 && state.stores == 0);
    struct stat link, target;
    CHECK(stat(ROOT "link", &link) == 0 && stat(ROOT "target", &target) == 0);
    CHECK(S_ISDIR(link.st_mode) && link.st_dev == target.st_dev && link.st_ino == target.st_ino);
    CHECK(access(ROOT "temporary", F_OK) < 0 && errno == ENOENT);
    CHECK(access(ROOT "stale-prefix", F_OK) < 0 && errno == ENOENT);
    specials();
    CHECK(io(ROOT "control", true, "bad\n", 4) == -EINVAL);
    pthread_t tasks[4];
    struct worker workers[4];
    for (unsigned index = 0; index < 4; ++index) {
        workers[index].index = index;
        CHECK(pthread_create(&tasks[index], NULL, values, &workers[index]) == 0);
    }
    for (unsigned index = 0; index < 4; ++index)
        CHECK(pthread_join(tasks[index], NULL) == 0);
    expect_text(ITEMS "readonly", "readonly\n");
    /* The guest's absent remote callback uses EIO; snooping above uses ENOSPC. */
    CHECK(io(ITEMS "readonly", true, "x", 1) == -EIO);
    char bytes[8192];
    CHECK(io(ITEMS "error", false, bytes, sizeof(bytes)) == -EINVAL);
    CHECK(io(ITEMS "error", true, "x", 1) == -EINVAL);
    CHECK(io(ITEMS "bad-count", false, bytes, sizeof(bytes)) == -EOVERFLOW);
    CHECK(io(ITEMS "bad-count", true, "x", 1) == -EOVERFLOW);
    memset(bytes, 'z', 4095);
    expect_bytes(ITEMS "boundary", bytes, 4095);
    memset(bytes, 'k', 4096);
    CHECK(io(ITEMS "boundary", true, bytes, 4096) == 4096);
    state = status();
    CHECK(state.phase == 0 && state.releases == 0 && state.reads == 260 && state.stores == 256);
    CHECK(io(ROOT "control", true, "advance\n", 8) == 8);
    do {
        state = status();
        CHECK(state.phase == 1 || state.phase == 2);
        if (state.phase != 2)
            pause_poll();
    } while (state.phase != 2);
    CHECK(state.releases == 8 && state.reads == 260 && state.stores == 256);
    CHECK(access(ROOT "items", F_OK) < 0 && errno == ENOENT);
    CHECK(io(ROOT "control", true, "finish\n", 7) == 7);
    while (access(BASE "native", F_OK) == 0)
        pause_poll();
    CHECK(errno == ENOENT);
    const char *names[] = {"d32", "d64", "u32", "u64", "s", "pbl", "pb", "u32K"};
    for (size_t index = 0; index < sizeof(names) / sizeof(names[0]); ++index) {
        char path[256];
        CHECK(snprintf(path, sizeof(path), BASE "remote/%s", names[index]) > 0);
        while (access(path, F_OK) == 0)
            pause_poll();
        CHECK(errno == ENOENT);
    }
    CHECK(stat(BASE "remote", &target) == 0 && S_ISDIR(target.st_mode));
    printf("NATIVE_GUEST_SYSFS_USER PASS special_reads=9 value_reads=260 value_stores=256 "
           "remote_releases=8 callback_errors=6 snoop_store_errors=1 full_read=4095 full_store=4096\n");
    return 0;
}
