/* SPDX-License-Identifier: GPL-2.0 */
/* Disposable guest only: real native preparation and retained AP-start attempt. */
#define NATIVE_OS_RESOURCE_MAIN native_os_resource_reference_main
#include "native-os-resource-assignment.c"
#define OS_LOAD 0x112a00
#define OS_BOOT 0x112a01
#define OS_STATUS 0x112a03
#define OS_KARGS 0x112a04
#if defined(__x86_64__)
#define SYS_NANOSLEEP 35
#else
#define SYS_NANOSLEEP 162
#endif

static unsigned sysfs_checks;
#if defined(NATIVE_SYSFS_OS)
static unsigned sysfs_completed;
#endif
static void sysfs_state(int minor, int present)
{
#if defined(NATIVE_SYSFS_OS)
    const char *paths[] = {"/sys/class/mcos/mcos0/sys", "/sys/class/mcos/mcos1/sys"};
    const char *markers[] = {"/sys/class/mcos/mcos0/sys/setup_complete", "/sys/class/mcos/mcos1/sys/setup_complete"};
    require(minor == 0 || minor == 1);
    long fd = call(SYS_OPEN, (long)paths[minor], 0, 0);
    if (present) { require(fd >= 0); close_fd(fd); }
    else { require(fd == -2); }
    // The root's existence must never stand in for the actual setup service.
    fd = call(SYS_OPEN, (long)markers[minor], 0, 0);
    if (minor == 0 && sysfs_completed) { require(fd >= 0); close_fd(fd); }
    else { require(fd == -2); }
    sysfs_checks++;
#else
    (void)minor; (void)present;
#endif
}

static void capture_pause(void)
{
    struct { long seconds, nanoseconds; } delay = {10, 0};
    message("NATIVE_BOOT_CAPTURE " ARCH_LABEL " ready\n");
    require(call(SYS_NANOSLEEP, (long)&delay, 0, 0) == 0);
}

#if defined(NATIVE_SYSFS_SERVICE) && !BOOT_PREPARE_ONLY
static void service_value(const char *path, char expected)
{
    char value[32];
    long fd = call(SYS_OPEN, (long)path, 0, 0);
    require(fd >= 0);
    require(call(SYS_READ, fd, (long)value, sizeof(value)) == 2);
    require(value[0] == expected && value[1] == '\n');
    require(call(SYS_READ, fd, (long)value, sizeof(value)) == 0);
    close_fd(fd);
}

static void service_roundtrips(void)
{
    const char *online = "/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu0/online";
    service_value("/sys/class/mcos/mcos0/sys/devices/system/cpu/num_processors", '1');
    service_value(online, '1');
    for (int cycle = 0; cycle < 32; cycle++) {
        // This is McKernel's documented simulated per-CPU online attribute;
        // the test changes its guest value, not Linux CPU hotplug state.
        put_value(online, "0\n");
        service_value(online, '0');
        put_value(online, "1\n");
        service_value(online, '1');
    }
    message("NATIVE_SYSFS_SERVICE " ARCH_LABEL " PASS read_checks=66 store_checks=64 rounds=32\n");
}
#endif

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
    sysfs_state(0, 0); sysfs_state(1, 0);
    char arguments[1024];
    for (int i = 0; i < 1024; i++) arguments[i] = 'y';
    require(call(SYS_IOCTL, first, OS_KARGS, (long)arguments) == 0);
    require(call(SYS_IOCTL, second, OS_KARGS, (long)"second-os") == 0);
    require(request(first, OS_ASSIGN_CPU, first_cpus, 2) == 0);
    require(request(second, OS_ASSIGN_CPU, second_cpus, 1) == 0);
    require(mem_one(first, OS_ASSIGN_MEM, 64 * MIB, 1) == 0);
    require(mem_one(second, OS_ASSIGN_MEM, 64 * MIB, 0) == 0);
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/legacy.img") == 0);
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EINVAL);
    // Revision 1 advertises the correct IRQ/boot layout but releases queue
    // slots before reading. It remains loadable and must fail before startup.
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/native-v1.img") == 0);
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EINVAL);
    require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
#if defined(NATIVE_VDSO_REV3)
    // Revision 2 completes queue reads but still uses the old 88-byte vDSO
    // descriptor. Reject it before taking any native startup resources.
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/native-v2.img") == 0);
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EINVAL);
    require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
#endif
    online_mask(1);
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/mckernel.img") == 0);
    require(call(SYS_IOCTL, second, OS_LOAD, (long)"/images/mckernel.img") == 0);
    require(call(SYS_IOCTL, first, OS_KARGS, 1) == -EFAULT);
    for (int cycle = 0; cycle < 8; cycle++) {
        allocation_failure(0);
        put_value(FI "min-order", "1");
        put_value(FI "times", "-1");
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -ENOMEM);
        put_value("/proc/self/make-it-fail", "0");
        put_value(FI "times", "0");
        put_value(FI "min-order", "10");
        require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
        sysfs_state(0, 0);
        require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EAGAIN);
        sysfs_state(1, 1);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EBUSY);
        sysfs_state(0, 0); sysfs_state(1, 1);
        require(call(SYS_IOCTL, second, OS_LOAD, (long)"/images/missing") == -2);
        sysfs_state(1, 0);
        require(call(SYS_IOCTL, second, OS_LOAD, (long)"/images/mckernel.img") == 0);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
        require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
        sysfs_state(0, 1);
        // Failed argument reads preserve the held preparation. Successful
        // changes retire it, making the exclusive trampoline available again.
        require(call(SYS_IOCTL, first, OS_KARGS, 1) == -EFAULT);
        sysfs_state(0, 1);
        require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EBUSY);
        require(call(SYS_IOCTL, first, OS_KARGS, (long)arguments) == 0);
        sysfs_state(0, 0);
        require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EAGAIN);
        sysfs_state(1, 1);
        require(call(SYS_IOCTL, second, OS_KARGS, (long)"second-os") == 0);
        sysfs_state(1, 0);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
        sysfs_state(0, 1);
        online_mask(1);
        if (cycle == 0) capture_pause();
        // Changing CPU assignment retires the held preparation, retaining the
        // image and original startup tables for a later preparation.
        int changed[] = {1};
        require(request(first, OS_RELEASE_CPU, changed, 1) == 0);
        sysfs_state(0, 0);
        require(request(first, OS_ASSIGN_CPU, changed, 1) == 0);
    }
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
    close_fd(first);
    require(destroy_os(control, 0) == 0);
    sysfs_state(0, 0);
    require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EAGAIN);
    close_fd(second);
    require(destroy_os(control, 1) == 0);
    sysfs_state(1, 0);
#if defined(NATIVE_SYSFS_OS)
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 0);
    sysfs_state(0, 0);
    require(destroy_os(control, 0) == 0);
#endif
    int chunks = query_memory(control), node1_chunks = 0;
    require(totals[0] == 128 * MIB && totals[1] == 128 * MIB);
    for (int i = 0; i < chunks; i++) {
        message("NATIVE_BOOT_RESTORED " ARCH_LABEL " node="); print_number(query_nodes[i]);
        message(" bytes="); print_number(query_sizes[i]); message("\n");
        if (query_nodes[i] == 1) node1_chunks++;
    }
    if (node1_chunks > 1) {
        // Legacy exact release addresses one returned contiguous chunk.
        // Reservation may legitimately return several chunks totaling 128 MiB.
        require(mem_one(control, MEM_RELEASE, 128 * MIB, 1) == -EINVAL);
        expect_memory(control, 128 * MIB, 128 * MIB);
    }
    release_memory(control);
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
    require(call(SYS_IOCTL, os, OS_KARGS, (long)"hidos") == 0);
    require(request(os, OS_ASSIGN_CPU, assigned, 1) == 0);
    require(mem_one(os, OS_ASSIGN_MEM, 128 * MIB, 0) == 0);
    require(call(SYS_IOCTL, os, OS_LOAD, (long)"/images/mckernel.img") == 0);
#if defined(NATIVE_SYSFS_SERVICE)
    long boot_result = call(SYS_IOCTL, os, OS_BOOT, 0);
    message("NATIVE_BOOT_SERVICE " ARCH_LABEL " boot_errno=");
    print_number(boot_result < 0 ? (unsigned long)-boot_result : 0);
    message("\n");
    require(boot_result == 0);
#else
    require(call(SYS_IOCTL, os, OS_BOOT, 0) == -110);
#endif
#if defined(NATIVE_SYSFS_SETUP)
    sysfs_completed = 1;
#endif
#if defined(NATIVE_SYSFS_SERVICE)
    require(call(SYS_IOCTL, os, OS_STATUS, 0) == 4);
#else
    require(call(SYS_IOCTL, os, OS_STATUS, 0) == 9);
#endif
    sysfs_state(0, 1);
    require(call(SYS_IOCTL, os, OS_KARGS, (long)"changed") == -EBUSY);
    require(call(SYS_IOCTL, os, OS_BOOT, 0) == -EBUSY);
    require(request(os, OS_RELEASE_CPU, assigned, 1) == -EBUSY);
    require(mem_one(os, OS_RELEASE_MEM, 128 * MIB, 0) == -EBUSY);
    online_mask(13);
    capture_pause();
#if defined(NATIVE_SYSFS_SERVICE)
    service_roundtrips();
    capture_pause();
#endif
    close_fd(os);
    require(destroy_os(control, 0) == -EBUSY);
    sysfs_state(0, 1);
    close_fd(control);
    require(call(SYS_DELETE_MODULE, (long)"ihk_smp_x86_64", 2048, 0) == -EAGAIN);
#if defined(NATIVE_SYSFS_SERVICE)
    message("NATIVE_BOOT_START " ARCH_LABEL " CAPTURED ready=1 resources_retained=1\n");
#else
    message("NATIVE_BOOT_START " ARCH_LABEL " CAPTURED incomplete=1 resources_retained=1\n");
#endif
#endif
#if defined(NATIVE_SYSFS_OS)
    message("NATIVE_OS_SYSFS " ARCH_LABEL " PASS checks="); print_number(sysfs_checks);
    message(" setup_completed="); print_number(sysfs_completed); message("\n");
#else
    (void)sysfs_checks;
#endif
    return 0;
}
