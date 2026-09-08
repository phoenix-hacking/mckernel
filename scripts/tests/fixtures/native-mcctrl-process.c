/* SPDX-License-Identifier: GPL-2.0 */
/* Real CREATE_PPD and final-file cleanup in the isolated Linux/McKernel guest. */
#define NATIVE_MCCTRL_EXEC_MAIN native_exec_reference_main
#include "native-mcctrl-exec.c"
#undef NATIVE_MCCTRL_EXEC_MAIN

#define CREATE_PPD 0x30a0290e
static unsigned process_checks;

static void ppd(int fd, long argument, long expected)
{
    long actual = call(SYS_IOCTL, fd, CREATE_PPD, argument);
    if (actual != expected) {
        message("NATIVE_PPD_RESULT index="); print_number(process_checks);
        message(" actual_negative="); print_number(actual < 0);
        message(" actual_magnitude="); print_number(actual < 0 ? -actual : actual);
        message(" expected_negative="); print_number(expected < 0);
        message(" expected_magnitude="); print_number(expected < 0 ? -expected : expected);
        message("\n");
    }
    require(actual == expected);
    process_checks++;
}

static void references(unsigned expected)
{
    char bytes[32];
    int fd = call(SYS_OPEN, (long)"/sys/module/mcctrl/refcnt", 0, 0);
    require(fd >= 0);
    int length = call(SYS_READ, fd, (long)bytes, sizeof(bytes));
    close_fd(fd);
    require(length >= 2 && length < (int)sizeof(bytes) && bytes[length-1] == '\n');
    unsigned actual = 0;
    for (int i = 0; i < length-1; i++) {
        require(bytes[i] >= '0' && bytes[i] <= '9');
        actual = actual * 10 + bytes[i] - '0';
    }
    require(actual == expected);
}

static void basic_ownership(void)
{
    int fd = open_os(0);
    unsigned long descriptor[3] = {0, 0, 0};
    ppd(fd, 1, -14);
    ppd(fd, -1, -14);
    ppd(fd, (long)descriptor, -95);
    char *pages = map_pages();
    require(call(SYS_MPROTECT, (long)(pages+4096), 4096, 0) == 0);
    ppd(fd, (long)(pages+4096-sizeof(descriptor)+1), -14);
    ppd(fd, (long)(pages+4096-sizeof(descriptor)), -95);
    require(call(SYS_MUNMAP, (long)pages, 8192, 0) == 0);
    ppd(fd, 0, 0);
    int duplicate = call(SYS_DUP, fd, 0, 0);
    require(duplicate >= 0);
    ppd(duplicate, 0, -22);
    int separate = open_os(0);
    ppd(separate, 0, -22);
    references(2);
    require(call(SYS_DELETE_MODULE, (long)"mcctrl", 2048, 0) == -EAGAIN);
    close_fd(fd);
    ppd(separate, 0, -22);
    close_fd(duplicate);
    references(1);
    ppd(separate, 0, -22);
    close_fd(separate);
    references(0);
    fd = open_os(0);
    ppd(fd, 0, 0);
    close_fd(fd);
    references(0);
}

static void inherited_owners(void)
{
    int fd = open_os(0), children[4];
    ppd(fd, 0, 0);
    for (int i = 0; i < 4; i++) {
        children[i] = call(SYS_FORK, 0, 0, 0);
        require(children[i] >= 0);
        if (children[i] == 0) {
            ppd(fd, 0, 0); ppd(fd, 0, -22);
            call(SYS_EXIT, 0, 0, 0);
            __builtin_unreachable();
        }
    }
    for (int i = 0; i < 4; i++) join(children[i]);
    process_checks += 8;
    references(1);
    ppd(fd, 0, -22);
    close_fd(fd);
    references(0);
    /* A child's private descriptor is also released by exit without close(). */
    int child = call(SYS_FORK, 0, 0, 0);
    require(child >= 0);
    if (child == 0) {
        int own = open_os(0);
        ppd(own, 0, 0);
        call(SYS_EXIT, 0, 0, 0);
        __builtin_unreachable();
    }
    join(child); process_checks++;
    references(0);
}

static void capacity_and_reuse(void)
{
    int ready[2], resume[2], children[64];
    require(call(SYS_PIPE, (long)ready, 0, 0) == 0);
    require(call(SYS_PIPE, (long)resume, 0, 0) == 0);
    for (int i = 0; i < 64; i++) {
        children[i] = call(SYS_FORK, 0, 0, 0);
        require(children[i] >= 0);
        if (children[i] == 0) {
            int own = open_os(0);
            ppd(own, 0, 0); ppd(own, 0, -22);
            signal_one(ready[1]);
            wait_one(resume[0]);
            call(SYS_EXIT, 0, 0, 0);
            __builtin_unreachable();
        }
    }
    for (int i = 0; i < 64; i++) wait_one(ready[0]);
    references(64);
    int fd = open_os(0);
    ppd(fd, 0, -11);
    references(65);
    close_fd(fd);
    require(call(SYS_DELETE_MODULE, (long)"mcctrl", 2048, 0) == -EAGAIN);
    for (int i = 0; i < 64; i++) signal_one(resume[1]);
    for (int i = 0; i < 64; i++) join(children[i]);
    process_checks += 128;
    close_fd(ready[0]); close_fd(ready[1]);
    close_fd(resume[0]); close_fd(resume[1]);
    references(0);
    fd = open_os(0);
    ppd(fd, 0, 0); ppd(fd, 0, -22);
    close_fd(fd);
    references(0);
}

#ifndef NATIVE_MCCTRL_PROCESS_MAIN
#define NATIVE_MCCTRL_PROCESS_MAIN main
#endif
int NATIVE_MCCTRL_PROCESS_MAIN(void)
{
    references(0);
    basic_ownership();
    inherited_owners();
    capacity_and_reuse();
    online_mask(13);
    require(process_checks == 153);
    message("NATIVE_MCCTRL_PROCESS " ARCH_LABEL " PASS checks=");
    print_number(process_checks);
    message(" registrations=73 duplicates=74 faults=3 unsupported_vm=2 capacity=64 exhaustion=1 workers=69 unload_vetoes=2 final_release=1 applications=0\n");
    return 0;
}
