/* SPDX-License-Identifier: GPL-2.0 */
/* Userspace-only probe for the disposable four-CPU/two-NUMA native guest. */
#define NATIVE_OS_RESOURCE_MAIN native_os_resource_reference_main
#include "native-os-resource-assignment.c"

#define OS_LOAD 0x112a00
#define OS_STATUS 0x112a03
#define OS_BOOT 0x112a01
static const char image_path[] = "/images/mckernel.img";

__attribute__((noreturn)) static void image_fail(int line)
{
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " FAIL\n");
    fail(line);
}
#undef require
#define require(test) do { if (!(test)) image_fail(__LINE__); } while (0)

static void expect_load(int fd, const char *path, long expected)
{
    long result = call(SYS_IOCTL, fd, OS_LOAD, (long)path);
    if (result != expected) {
        message("NATIVE_IMAGE_LOAD unexpected result magnitude=");
        print_number(result < 0 ? -result : result);
        message(" path=");
        if ((unsigned long)path > 4096) message(path);
        message("\n");
    }
    require(result == expected);
    require(call(SYS_IOCTL, fd, OS_STATUS, 0) == 0);
    online_mask(1);
}

int main(void)
{
    require(native_os_resource_reference_main() == 0);
    int control = open_control();
    int reserved[] = {3, 2, 1}, first_cpus[] = {3, 1}, second_cpu[] = {2};
    require(request(control, RESERVE, reserved, 3) == 0);
    require(mem_one(control, MEM_RESERVE, 128 * MIB, 0) == 0);
    require(mem_one(control, MEM_RESERVE, 128 * MIB, 1) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 1);
    int first = open_os(0), second = open_os(1);
    expect_load(first, image_path, -EINVAL);
    require(request(first, OS_ASSIGN_CPU, first_cpus, 2) == 0);
    require(request(second, OS_ASSIGN_CPU, second_cpu, 1) == 0);
    expect_load(first, image_path, -ENOMEM);
    require(mem_one(first, OS_ASSIGN_MEM, 4096, 1) == 0);
    expect_load(first, image_path, -ENOMEM);
    require(mem_one(first, OS_RELEASE_MEM, 4096, 1) == 0);
    require(mem_one(first, OS_ASSIGN_MEM, 64 * MIB, 1) == 0);
    require(mem_one(second, OS_ASSIGN_MEM, 64 * MIB, 0) == 0);
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " prerequisites-and-other-os-lower-node PASS\n");

    expect_load(first, (const char *)1, -EFAULT);
    char unterminated[256];
    for (unsigned int index = 0; index < sizeof(unterminated); index++) unterminated[index] = 'x';
    require(call(SYS_IOCTL, first, OS_LOAD, (long)unterminated) == -EINVAL);
    expect_load(first, "", -EINVAL);
    expect_load(first, "/images/missing", -2);
    expect_load(first, "/images", -EINVAL);
    expect_load(first, "/images/oversized", -27);
    expect_load(first, "/images/short.elf", -EINVAL);
    expect_load(first, "/images/late-filesz.elf", -EINVAL);
    expect_load(first, "/images/bad-entry.elf", -EINVAL);
    expect_load(first, "/images/late-overlap.elf", -EINVAL);
    expect_load(first, "/images/late-overflow.elf", -75);
    int writer = call(SYS_OPEN, (long)image_path, 1, 0);
    require(writer >= 0);
    expect_load(first, image_path, -26);
    close_fd(writer);
    expect_os_memory(first, 0, 64 * MIB);
    expect_os_memory(second, 64 * MIB, 0);
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " file-errors-atomic-preflight PASS\n");

    expect_load(first, image_path, 0);
    expect_load(first, "/images/late-filesz.elf", -EINVAL);
    expect_load(first, image_path, 0);
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EINVAL);
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " repeat-load-and-bss-readback PASS\n");

    int child = call(SYS_FORK, 0, 0, 0);
    require(child >= 0);
    if (child == 0) {
        expect_load(first, image_path, 0);
        call(SYS_EXIT, 0, 0, 0);
        __builtin_unreachable();
    }
    expect_load(second, image_path, 0);
    int status = -1;
    require(call(SYS_WAIT, child, (long)&status, 0) == child);
    require(status == 0);
    expect_os_memory(first, 0, 64 * MIB);
    expect_os_memory(second, 64 * MIB, 0);
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " simultaneous-os-loads PASS\n");

    int count = query_os_memory(first);
    struct memory_request released = mem_request(query_sizes, query_nodes, count);
    require(mem_command(first, OS_RELEASE_MEM, &released) == 0);
    expect_load(first, image_path, -ENOMEM);
    require(mem_one(first, OS_ASSIGN_MEM, 64 * MIB, 1) == 0);
    expect_load(first, image_path, 0);
    close_fd(first);
    require(destroy_os(control, 0) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 0);
    first = open_os(0);
    expect_load(first, image_path, -EINVAL);
    require(request(first, OS_ASSIGN_CPU, first_cpus, 2) == 0);
    require(mem_one(first, OS_ASSIGN_MEM, 64 * MIB, 1) == 0);
    expect_load(first, image_path, 0);
    close_fd(first);
    close_fd(second);
    require(destroy_os(control, 0) == 0);
    require(destroy_os(control, 1) == 0);
    expect_memory(control, 128 * MIB, 128 * MIB);
    release_memory(control);
    require(request(control, RELEASE, reserved, 3) == 0);
    online_mask(15);
    close_fd(control);
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " release-destroy-generation-cleanup PASS\n");
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " COMPLETE PASS\n");
    return 0;
}
