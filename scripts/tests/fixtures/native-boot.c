/* SPDX-License-Identifier: GPL-2.0 */
/* Disposable guest only: real native preparation and retained AP-start attempt. */
#define NATIVE_OS_RESOURCE_MAIN native_os_resource_reference_main
#include "native-os-resource-assignment.c"
#define OS_LOAD 0x112a00
#define OS_BOOT 0x112a01
#define OS_STATUS 0x112a03
#if defined(__x86_64__)
#define SYS_NANOSLEEP 35
#else
#define SYS_NANOSLEEP 162
#endif

static void capture_pause(void)
{
    struct { long seconds, nanoseconds; } delay = {10, 0};
    message("NATIVE_BOOT_CAPTURE " ARCH_LABEL " ready\n");
    require(call(SYS_NANOSLEEP, (long)&delay, 0, 0) == 0);
}

int main(void)
{
    int control = open_control();
#if BOOT_PREPARE_ONLY
    int reserved[] = {3, 2, 1}, first_cpus[] = {3, 1}, second_cpus[] = {2};
    require(request(control, RESERVE, reserved, 3) == 0);
    require(mem_one(control, MEM_RESERVE, 128 * MIB, 0) == 0);
    require(mem_one(control, MEM_RESERVE, 128 * MIB, 1) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 1);
    int first = open_os(0), second = open_os(1);
    require(request(first, OS_ASSIGN_CPU, first_cpus, 2) == 0);
    require(request(second, OS_ASSIGN_CPU, second_cpus, 1) == 0);
    require(mem_one(first, OS_ASSIGN_MEM, 64 * MIB, 1) == 0);
    require(mem_one(second, OS_ASSIGN_MEM, 64 * MIB, 0) == 0);
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/legacy.img") == 0);
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EINVAL);
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/mckernel.img") == 0);
    require(call(SYS_IOCTL, second, OS_LOAD, (long)"/images/mckernel.img") == 0);
    for (int cycle = 0; cycle < 8; cycle++) {
        allocation_failure(0);
        put_value(FI "min-order", "1");
        put_value(FI "times", "-1");
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -ENOMEM);
        put_value("/proc/self/make-it-fail", "0");
        put_value(FI "times", "0");
        put_value(FI "min-order", "10");
        require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
        require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EAGAIN);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EBUSY);
        require(call(SYS_IOCTL, second, OS_LOAD, (long)"/images/missing") == -2);
        require(call(SYS_IOCTL, second, OS_LOAD, (long)"/images/mckernel.img") == 0);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
        require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
        online_mask(1);
        if (cycle == 0) capture_pause();
        // Changing CPU assignment retires the held preparation, retaining the
        // image and original startup tables for a later preparation.
        int changed[] = {1};
        require(request(first, OS_RELEASE_CPU, changed, 1) == 0);
        require(request(first, OS_ASSIGN_CPU, changed, 1) == 0);
    }
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
    close_fd(first);
    require(destroy_os(control, 0) == 0);
    require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EAGAIN);
    close_fd(second);
    require(destroy_os(control, 1) == 0);
    require(mem_one(control, MEM_RELEASE, 128 * MIB, 0) == 0);
    require(mem_one(control, MEM_RELEASE, 128 * MIB, 1) == 0);
    require(request(control, RELEASE, reserved, 3) == 0);
    online_mask(15);
    close_fd(control);
    message("NATIVE_BOOT_PREPARATION " ARCH_LABEL " PASS cycles=8 failures=8 exclusive=1 restored=1\n");
#else
    int assigned[] = {1};
    require(request(control, RESERVE, assigned, 1) == 0);
    require(mem_one(control, MEM_RESERVE, 128 * MIB, 0) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 0);
    int os = open_os(0);
    require(request(os, OS_ASSIGN_CPU, assigned, 1) == 0);
    require(mem_one(os, OS_ASSIGN_MEM, 128 * MIB, 0) == 0);
    require(call(SYS_IOCTL, os, OS_LOAD, (long)"/images/mckernel.img") == 0);
    require(call(SYS_IOCTL, os, OS_BOOT, 0) == -110);
    require(call(SYS_IOCTL, os, OS_STATUS, 0) == 9);
    require(call(SYS_IOCTL, os, OS_BOOT, 0) == -EBUSY);
    require(request(os, OS_RELEASE_CPU, assigned, 1) == -EBUSY);
    require(mem_one(os, OS_RELEASE_MEM, 128 * MIB, 0) == -EBUSY);
    online_mask(13);
    capture_pause();
    close_fd(os);
    require(destroy_os(control, 0) == -EBUSY);
    close_fd(control);
    require(call(SYS_DELETE_MODULE, (long)"ihk_smp_x86_64", 2048, 0) == -EAGAIN);
    message("NATIVE_BOOT_START " ARCH_LABEL " CAPTURED incomplete=1 resources_retained=1\n");
#endif
    return 0;
}
