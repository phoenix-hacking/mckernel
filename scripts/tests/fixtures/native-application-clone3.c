/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact pinned Linux validators; substituted bounded user-copy providers. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <errno.h>
#include <assert.h>
#include <stdlib.h>
#include <stdbool.h>

typedef uint64_t u64;
typedef uint32_t u32;
typedef int pid_t;
#define __user
#define __aligned_u64 uint64_t __attribute__((aligned(8)))
#define __must_check
#undef __always_inline
#define __always_inline inline __attribute__((always_inline))
#define unlikely(value) (value)
#define noinline __attribute__((noinline))
#define min(a, b) ((a) < (b) ? (a) : (b))
#define max(a, b) ((a) > (b) ? (a) : (b))
#define WARN_ON_ONCE(value) (value)
#define BUILD_BUG_ON(value) _Static_assert(!(value), #value)
#define offsetofend(type, member) (offsetof(type, member) + sizeof(((type *)0)->member))
#define PAGE_SIZE 4096
#define MAX_PID_NS_LEVEL 32
#define CSIGNAL 0xff
#define valid_signal(signal) ((signal) <= 64)
#define u64_to_user_ptr(value) ((void *)(uintptr_t)(value))

static uint64_t origin, readable;
static unsigned char payload[4096];
static int access_ok(const void *pointer, uint64_t length)
{
    uint64_t address = (uintptr_t)pointer;
    return address >= 0x1000 && address < 0x800000000000ULL &&
        length <= 0x800000000000ULL - address;
}
static unsigned long copy_from_user(void *target, const void *source, size_t count)
{
    uint64_t address = (uintptr_t)source;
    if (!access_ok(source, count) || address < origin || address - origin > readable ||
        count > readable - (address - origin)) return count ? count : 1;
    memcpy(target, payload + (address - origin), count);
    return 0;
}
static int check_zeroed_user(const void *source, size_t count)
{
    unsigned char byte;
    for (size_t offset = 0; offset < count; ++offset) {
        if (copy_from_user(&byte, (const char *)source + offset, 1)) return -EFAULT;
        if (byte) return 0;
    }
    return 1;
}

#include "linux-clone3-reference.h"

int main(int argc, char **argv)
{
    assert(argc == 2);
    FILE *input = fopen(argv[1], "rb");
    assert(input);
    uint64_t header[4];
    unsigned index = 0;
    while (fread(header, sizeof(header), 1, input) == 1) {
        assert(fread(payload, sizeof(payload), 1, input) == 1);
        origin = header[0]; readable = header[2];
        struct kernel_clone_args args = {0};
        pid_t set_tid[MAX_PID_NS_LEVEL] = {0};
        args.set_tid = set_tid;
        int result = copy_clone_args_from_user(&args, (void *)(uintptr_t)origin, header[1]);
        if (!result && !clone3_args_valid(&args)) result = -EINVAL;
        printf("%u %d %llu %llu %llu %llu %llu\n", index++, result,
            (unsigned long long)(args.flags | args.exit_signal),
            (unsigned long long)args.stack, (unsigned long long)(uintptr_t)args.parent_tid,
            (unsigned long long)(uintptr_t)args.child_tid, (unsigned long long)args.tls);
    }
    assert(feof(input));
    assert(fclose(input) == 0);
    return 0;
}
