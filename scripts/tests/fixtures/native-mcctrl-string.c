/* SPDX-License-Identifier: GPL-2.0 */
/* Actual current-task pathname-copy UAPI, including compat and guarded faults. */
#define NATIVE_MCCTRL_EXEC_MAIN native_mcctrl_exec_reference_main
#include "native-mcctrl-exec.c"
#include "native-string-abi.h"

_Static_assert(sizeof(struct strncpy_from_user_desc) == 4 * sizeof(long), "descriptor size");
_Static_assert(__builtin_offsetof(struct strncpy_from_user_desc, result) == 3 * sizeof(long), "result offset");

static unsigned string_cases;

static void string_fill(unsigned char *bytes, unsigned length, unsigned char value)
{
    for (unsigned i = 0; i < length; ++i) bytes[i] = value;
}

static void string_copy(int fd, void *destination, void *source, unsigned long count, long result)
{
    struct {
        unsigned long before[2];
        struct strncpy_from_user_desc value;
        unsigned long after[2];
    } descriptor = {{0x13579bdf, 0x2468ace0}, {destination, source, count, 1234567},
                    {0xabcdef01, 0x87654321}};
    require(call(SYS_IOCTL, fd, MCEXEC_UP_STRNCPY_FROM_USER, (long)&descriptor.value) == 0);
    require(descriptor.before[0] == 0x13579bdf && descriptor.before[1] == 0x2468ace0);
    require(descriptor.after[0] == 0xabcdef01 && descriptor.after[1] == 0x87654321);
    require(descriptor.value.dest == destination && descriptor.value.src == source);
    require(descriptor.value.n == count && descriptor.value.result == result);
    ++string_cases;
}

int main(void)
{
    int fd = open_os(0);
    unsigned char *source = map_pages(), *destination = map_pages(), *argument = map_pages();
    string_fill(source, 8192, 'x');
    string_fill(destination, 8192, 0x6d);
    string_copy(fd, (void *)-1L, (void *)-1L, 0, 0);

    source[12] = 0;
    string_copy(fd, destination, source, 100, 12);
    for (unsigned i = 0; i < 12; ++i) require(destination[i] == 'x');
    require(destination[12] == 0 && destination[13] == 0x6d);

    string_fill(source, 8192, 'q');
    source[5000] = 0;
    string_fill(destination, 8192, 0x6d);
    string_copy(fd, destination, source, 8192, 5000);
    for (unsigned i = 0; i < 5000; ++i) require(destination[i] == 'q');
    require(destination[5000] == 0 && destination[5001] == 0x6d);

    string_fill(destination, 8192, 0x6d);
    string_copy(fd, destination, source, 4097, 4097);
    for (unsigned i = 0; i < 4097; ++i) require(destination[i] == 'q');
    require(destination[4097] == 0x6d);

    require(call(SYS_MPROTECT, (long)(source + 4096), 4096, 0) == 0);
    source[4095] = 0;
    string_fill(destination, 8192, 0x6d);
    string_copy(fd, destination, source + 4095, 8192, 0);
    require(destination[0] == 0 && destination[1] == 0x6d);
    source[4094] = 'a';
    string_copy(fd, destination, source + 4094, 8192, 1);
    require(destination[0] == 'a' && destination[1] == 0 && destination[2] == 0x6d);
    source[4095] = 'z';
    string_fill(destination, 8192, 0x6d);
    string_copy(fd, destination, source + 4095, 1, 1);
    require(destination[0] == 'z' && destination[1] == 0x6d);
    string_fill(destination, 8192, 0x6d);
    string_copy(fd, destination, source + 4095, 2, -14);
    require(destination[0] == 0x6d && destination[1] == 0x6d);

    string_fill(source, 4096, 'r');
    string_copy(fd, destination, source, 8192, -14);
    for (unsigned i = 0; i < 4096; ++i) require(destination[i] == 'r');
    require(destination[4096] == 0x6d);
    require(call(SYS_MPROTECT, (long)(source + 4096), 4096, 3) == 0);

    source[0] = 'a'; source[1] = 'b'; source[2] = 0;
    string_copy(fd, destination, (void *)-1L, 10, -14);
    string_copy(fd, (void *)-1L, source, 10, -14);
    string_copy(fd, destination, 0, 10, -14);
    string_copy(fd, 0, source, 10, -14);

    string_fill(destination, 8192, 0x6d);
    require(call(SYS_MPROTECT, (long)(destination + 4096), 4096, 0) == 0);
    string_copy(fd, destination + 4095, source, 10, -14);
    require(destination[4094] == 0x6d);
    require(call(SYS_MPROTECT, (long)(destination + 4096), 4096, 3) == 0);
    require(destination[4096] == 0x6d && destination[4097] == 0x6d);

    require(call(SYS_IOCTL, fd, MCEXEC_UP_STRNCPY_FROM_USER, 0) == -14);
    require(call(SYS_IOCTL, fd, MCEXEC_UP_STRNCPY_FROM_USER, -1) == -14);
    require(call(SYS_MPROTECT, (long)(argument + 4096), 4096, 0) == 0);
    require(call(SYS_IOCTL, fd, MCEXEC_UP_STRNCPY_FROM_USER,
                 (long)(argument + 4096 - sizeof(long))) == -14);

    struct strncpy_from_user_desc *readonly = (void *)argument;
    *readonly = (struct strncpy_from_user_desc){destination, source, 10, 1234567};
    string_fill(destination, 8192, 0x6d);
    require(call(SYS_MPROTECT, (long)argument, 4096, 1) == 0);
    require(call(SYS_IOCTL, fd, MCEXEC_UP_STRNCPY_FROM_USER, (long)readonly) == -14);
    require(readonly->result == 1234567);
    require(destination[0] == 'a' && destination[1] == 'b' && destination[2] == 0);
    require(destination[3] == 0x6d);
    require(string_cases == 14);
    require(call(SYS_MUNMAP, (long)argument, 8192, 0) == 0);
    require(call(SYS_MUNMAP, (long)source, 8192, 0) == 0);
    require(call(SYS_MUNMAP, (long)destination, 8192, 0) == 0);
    close_fd(fd);
    static const char passed[] = "<6>NATIVE_STRING_COPY " ARCH_LABEL " PASS cases=14 descriptor_faults=4 guarded=1 applications=0\n";
    int log = call(SYS_OPEN, (long)"/dev/kmsg", 1, 0);
    require(log >= 0);
    require(call(SYS_WRITE, log, (long)passed, sizeof(passed) - 1) == (long)sizeof(passed) - 1);
    close_fd(log);
    return 0;
}
