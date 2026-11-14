/* SPDX-License-Identifier: GPL-2.0 */
/* Real application ioctls against the running OS; isolated Linux guest only. */
#define NATIVE_OS_RESOURCE_MAIN native_os_resource_reference_main
#include "native-os-resource-assignment.c"

#if defined(__x86_64__)
#define SYS_FINIT_MODULE 313
#define SYS_DUP 32
#define SYS_PIPE 22
#else
#define SYS_FINIT_MODULE 350
#define SYS_DUP 41
#define SYS_PIPE 42
#endif
#define GET_CPU 0x30a02907
#define GET_NODES 0x30a0290c
#define PREPARE_IMAGE 0x30a02900

static unsigned queries;

static void counts(int fd)
{
    /* Scalar commands ignore the argument, including an inaccessible address. */
    require(call(SYS_IOCTL, fd, GET_CPU, -1) == 1);
    require(call(SYS_IOCTL, fd, GET_NODES, 1) == 1);
    queries += 2;
}

static void reference_count(int expected)
{
    char text[32];
    int fd = call(SYS_OPEN, (long)"/sys/module/mcctrl/refcnt", 0, 0);
    require(fd >= 0);
    int length = call(SYS_READ, fd, (long)text, sizeof(text));
    close_fd(fd);
    require(length == 2 && text[0] == '0' + expected && text[1] == '\n');
}

static void load_module(void)
{
    int fd = call(SYS_OPEN, (long)"/modules/mcctrl.ko", 0, 0);
    require(fd >= 0);
    require(call(SYS_FINIT_MODULE, fd, (long)"", 0) == 0);
    close_fd(fd);
    reference_count(0);
}

static void unload(long expected)
{
    require(call(SYS_DELETE_MODULE, (long)"mcctrl", 2048, 0) == expected);
}

static void signal_one(int fd)
{
    char value = 'x';
    require(call(SYS_WRITE, fd, (long)&value, 1) == 1);
}

static void wait_one(int fd)
{
    char value = 0;
    require(call(SYS_READ, fd, (long)&value, 1) == 1 && value == 'x');
}

static void concurrent_first_use(int fd)
{
    int start[2], acquired[2], resume[2], children[4];
    require(call(SYS_PIPE, (long)start, 0, 0) == 0);
    require(call(SYS_PIPE, (long)acquired, 0, 0) == 0);
    require(call(SYS_PIPE, (long)resume, 0, 0) == 0);
    for (int worker = 0; worker < 4; worker++) {
        children[worker] = call(SYS_FORK, 0, 0, 0);
        require(children[worker] >= 0);
        if (children[worker] == 0) {
            wait_one(start[0]);
            counts(fd);
            signal_one(acquired[1]);
            wait_one(resume[0]);
            for (int iteration = 0; iteration < 64; iteration++) counts(fd);
            call(SYS_EXIT, 0, 0, 0);
            __builtin_unreachable();
        }
    }
    for (int worker = 0; worker < 4; worker++) signal_one(start[1]);
    for (int worker = 0; worker < 4; worker++) wait_one(acquired[0]);
    reference_count(1);
    unload(-EAGAIN);
    for (int worker = 0; worker < 4; worker++) signal_one(resume[1]);
    for (int worker = 0; worker < 4; worker++) {
        int status = -1;
        require(call(SYS_WAIT, children[worker], (long)&status, 0) == children[worker]);
        require(status == 0);
    }
    close_fd(start[0]); close_fd(start[1]);
    close_fd(acquired[0]); close_fd(acquired[1]);
    close_fd(resume[0]); close_fd(resume[1]);
    queries += 4 * 65 * 2;
    reference_count(1);
}

int main(void)
{
    online_mask(13);
    /* The launcher sees guest rank zero, distinct from Linux CPU 1. */
    const char *present[] = {
        "/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu0/online",
        "/sys/class/mcos/mcos0/sys/devices/system/node/node0/cpu0/online",
    };
    for (unsigned i = 0; i < sizeof(present) / sizeof(present[0]); i++) {
        int fd = call(SYS_OPEN, (long)present[i], 0, 0);
        require(fd >= 0); close_fd(fd);
    }
    require(call(SYS_OPEN, (long)"/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu1/online", 0, 0) == -2);
    require(call(SYS_OPEN, (long)"/sys/class/mcos/mcos0/sys/devices/system/node/node1/cpu0/online", 0, 0) == -2);
    for (int cycle = 0; cycle < 2; cycle++) {
        int fd = open_os(0);
        require(call(SYS_IOCTL, fd, GET_CPU, 0) == -19);
        require(call(SYS_IOCTL, fd, GET_NODES, 0) == -19);
        load_module();
        /* Opening the OS file alone does not make mcctrl permanently busy. */
        unload(0);
        require(call(SYS_IOCTL, fd, GET_CPU, 0) == -19);
        load_module();
        int duplicate = call(SYS_DUP, fd, 0, 0);
        require(duplicate >= 0);
        concurrent_first_use(fd);
        counts(fd);
        require(call(SYS_IOCTL, fd, PREPARE_IMAGE, 1) == -EINVAL);
        require(call(SYS_IOCTL, fd, 0x112a03, 0) == 4);
        unload(-EAGAIN);
        close_fd(fd);
        reference_count(1);
        counts(duplicate);
        unload(-EAGAIN);
        int separate = open_os(0);
        counts(separate);
        reference_count(2);
        close_fd(duplicate);
        reference_count(1);
        unload(-EAGAIN);
        counts(separate);
        close_fd(separate);
        reference_count(0);
        unload(0);
    }
    online_mask(13);
    message("NATIVE_MCCTRL_SERVICE " ARCH_LABEL " PASS cycles=2 workers=8 topology_queries=");
    print_number(queries);
    message(" contexts=4 unload_vetoes=8 absent=6 unsupported=2 applications=0\n");
    return 0;
}
