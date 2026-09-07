/* SPDX-License-Identifier: GPL-2.0 */
/* Freestanding userspace probe for the isolated four-CPU NUMA guest only. */
#define NATIVE_MEMORY_MAIN native_memory_reference_main
#include "native-memory-reservation.c"

#define OS_CREATE 0x112900
#define OS_DESTROY 0x112901
#define OS_ASSIGN_CPU 0x112a22
#define OS_RELEASE_CPU 0x112a23
#define OS_ASSIGN_MEM 0x112a24
#define OS_RELEASE_MEM 0x112a25
#define OS_QUERY_CPU 0x112a26
#define OS_QUERY_MEM 0x112a27
#define OS_COUNT_CPU 0x112a38

__attribute__((noreturn)) static void os_resource_fail(int line)
{
    message("NATIVE_OS_RESOURCE " ARCH_LABEL " FAIL\n");
    fail(line);
}
#undef require
#define require(test) do { if (!(test)) os_resource_fail(__LINE__); } while (0)

static int open_os(int minor)
{
    char path[] = "/dev/mcos0";
    require(minor >= 0 && minor < 10);
    path[9] = '0' + minor;
    int fd = call(SYS_OPEN, (long)path, 2, 0);
    require(fd >= 0);
    return fd;
}
static long destroy_os(int fd, int minor)
{
    return call(SYS_IOCTL, fd, OS_DESTROY, minor);
}
static void expect_os_cpu(int fd, const int *expected, int count)
{
    int cpus[5] = {-99, -99, -99, -99, -99};
    require(call(SYS_IOCTL, fd, OS_COUNT_CPU, 0) == count);
    require(request(fd, OS_QUERY_CPU, cpus, count) == 0);
    for (int index = 0; index < count; index++) require(cpus[index] == expected[index]);
    require(cpus[count] == -99);
}
static int query_os_memory(int fd)
{
    struct memory_request value = mem_request(0, 0, 0);
    /* Reservation-only order and timeout limits do not constrain OS queries. */
    value.minimum = 0x7fffffff;
    value.timeout = -1;
    require(mem_command(fd, OS_QUERY_MEM, &value) == 0);
    int count = value.count;
    require(count >= 0 && count <= CAPACITY);
    query_sizes[CAPACITY] = 0x13579UL;
    query_nodes[CAPACITY] = 0x2468;
    value = mem_request(query_sizes, query_nodes, CAPACITY);
    require(mem_command(fd, OS_QUERY_MEM, &value) == 0);
    require(value.count == count);
    require(query_sizes[CAPACITY] == 0x13579UL && query_nodes[CAPACITY] == 0x2468);
    totals[0] = totals[1] = 0;
    for (int index = 0; index < count; index++) {
        require(query_nodes[index] >= 0 && query_nodes[index] < 2);
        require(query_sizes[index] != 0 && query_sizes[index] % 4096 == 0);
        totals[query_nodes[index]] += query_sizes[index];
    }
    return count;
}
static void expect_os_memory(int fd, unsigned long node0, unsigned long node1)
{
    query_os_memory(fd);
    require(totals[0] == node0 && totals[1] == node1);
}
static void concurrent_os_memory(int control)
{
    int children[2];
    for (int worker = 0; worker < 2; worker++) {
        children[worker] = call(SYS_FORK, 0, 0, 0);
        require(children[worker] >= 0);
        if (children[worker] == 0) {
            for (int iteration = 0; iteration < 8; iteration++) {
                int minor = call(SYS_IOCTL, control, OS_CREATE, 0);
                require(minor >= 2 && minor <= 3);
                int fd = open_os(minor);
                require(mem_one(fd, OS_ASSIGN_MEM, 4096, worker) == 0);
                expect_os_memory(fd, worker ? 0 : 4096, worker ? 4096 : 0);
                require(destroy_os(control, minor) == -EBUSY);
                require(mem_one(fd, OS_RELEASE_MEM, 4096, worker) == 0);
                expect_os_memory(fd, 0, 0);
                close_fd(fd);
                require(destroy_os(control, minor) == 0);
            }
            call(SYS_EXIT, 0, 0, 0);
            __builtin_unreachable();
        }
    }
    for (int worker = 0; worker < 2; worker++) {
        int status = -1;
        require(call(SYS_WAIT, children[worker], (long)&status, 0) == children[worker]);
        require(status == 0);
    }
    message("NATIVE_OS_RESOURCE " ARCH_LABEL " concurrent-instances=2x8 PASS\n");
}
#ifndef NATIVE_OS_RESOURCE_MAIN
#define NATIVE_OS_RESOURCE_MAIN main
#endif
int NATIVE_OS_RESOURCE_MAIN(void)
{
    require(native_memory_reference_main() == 0);
    int control = open_control();
    int reserved[] = {3, 2, 1}, first_cpus[] = {3, 1}, second_cpu[] = {2};
    require(request(control, RESERVE, reserved, 3) == 0);
    require(mem_one(control, MEM_RESERVE, 64 * MIB, 0) == 0);
    require(mem_one(control, MEM_RESERVE, 64 * MIB, 1) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 1);
    int first = open_os(0), second = open_os(1);
    require(request(first, OS_ASSIGN_CPU, 0, 0) == 0);
    require(request(first, OS_RELEASE_CPU, 0, 0) == 0);
    require(request(first, OS_ASSIGN_CPU, first_cpus, 2) == 0);
    require(request(second, OS_ASSIGN_CPU, second_cpu, 1) == 0);
    expect_os_cpu(first, first_cpus, 2);
    expect_os_cpu(second, second_cpu, 1);
    require(call(SYS_IOCTL, control, COUNT, 0) == 0);
    int invalid_cpus[] = {3, 2}, duplicate_cpus[] = {3, 3};
    require(request(first, OS_RELEASE_CPU, invalid_cpus, 2) == -EINVAL);
    require(request(first, OS_RELEASE_CPU, duplicate_cpus, 2) == -EINVAL);
    require(request(first, OS_RELEASE_CPU, second_cpu, 1) == -EINVAL);
    require(request(control, RELEASE, second_cpu, 1) == -EINVAL);
    require(call(SYS_IOCTL, first, OS_ASSIGN_CPU, 1) == -EFAULT);
    require(request(first, OS_ASSIGN_CPU, (int *)1, 1) == -EFAULT);
    expect_os_cpu(first, first_cpus, 2);
    require(request(first, OS_QUERY_CPU, (int *)1, 2) == -EFAULT);
    require(request(first, OS_QUERY_CPU, first_cpus, 1) == -EINVAL);
    int released_cpu[] = {3}, kept_cpu[] = {1};
    require(request(first, OS_RELEASE_CPU, released_cpu, 1) == 0);
    expect_os_cpu(first, kept_cpu, 1);
    require(call(SYS_IOCTL, control, COUNT, 0) == 1);
    require(request(first, OS_ASSIGN_CPU, invalid_cpus, 2) == -EINVAL);
    expect_os_cpu(first, kept_cpu, 1);
    require(call(SYS_IOCTL, control, COUNT, 0) == 1);
    require(request(first, OS_ASSIGN_CPU, released_cpu, 1) == 0);
    first_cpus[0] = 1; first_cpus[1] = 3;
    expect_os_cpu(first, first_cpus, 2);
    require(call(SYS_IOCTL, control, COUNT, 0) == 0);
    online_mask(1);
    message("NATIVE_OS_RESOURCE " ARCH_LABEL " ordered-cpu-cross-owner-rollback PASS\n");

    require(mem_one(first, OS_ASSIGN_MEM, 4096, 0) == 0);
    require(mem_one(first, OS_ASSIGN_MEM, 4 * MIB, 1) == 0);
    require(mem_one(second, OS_ASSIGN_MEM, 4 * MIB, 0) == 0);
    require(mem_one(second, OS_ASSIGN_MEM, 4096, 1) == 0);
    expect_os_memory(first, 4096, 4 * MIB);
    expect_os_memory(second, 4 * MIB, 4096);
    expect_memory(control, 60 * MIB - 4096, 60 * MIB - 4096);
    require(mem_one(first, OS_RELEASE_MEM, 4 * MIB, 0) == -EINVAL);
    unsigned long bad_sizes[] = {4096, 65 * MIB};
    int bad_nodes[] = {0, 1};
    struct memory_request value = mem_request(bad_sizes, bad_nodes, 2);
    require(mem_command(first, OS_ASSIGN_MEM, &value) == -ENOMEM);
    expect_os_memory(first, 4096, 4 * MIB);
    bad_sizes[1] = ~0UL;
    require(mem_command(first, OS_RELEASE_MEM, &value) == -EINVAL);
    require(call(SYS_IOCTL, first, OS_ASSIGN_MEM, 1) == -EFAULT);
    value = mem_request((unsigned long *)1, bad_nodes, 1);
    require(mem_command(first, OS_ASSIGN_MEM, &value) == -EFAULT);
    expect_os_memory(first, 4096, 4 * MIB);
    expect_memory(control, 60 * MIB - 4096, 60 * MIB - 4096);
    message("NATIVE_OS_RESOURCE " ARCH_LABEL " numa-subpage-batch-rollback PASS\n");

    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 2);
    int all_os = open_os(2);
    value = mem_request(0, 0, 0);
    require(mem_command(all_os, OS_ASSIGN_MEM, &value) == 0);
    require(mem_command(all_os, OS_RELEASE_MEM, &value) == 0);
    require(mem_one(all_os, OS_ASSIGN_MEM, ~0UL, 0) == 0);
    expect_os_memory(all_os, 60 * MIB - 4096, 0);
    expect_memory(control, 0, 60 * MIB - 4096);
    require(mem_one(all_os, OS_ASSIGN_MEM, ~0UL, 0) == -ENOMEM);
    require(call(SYS_IOCTL, all_os, OS_QUERY_MEM, 1) == -EFAULT);
    value = mem_request((unsigned long *)1, bad_nodes, CAPACITY);
    require(mem_command(all_os, OS_QUERY_MEM, &value) == -EFAULT);
    expect_os_memory(all_os, 60 * MIB - 4096, 0);
    close_fd(all_os);
    require(destroy_os(control, 2) == 0);
    expect_memory(control, 60 * MIB - 4096, 60 * MIB - 4096);
    message("NATIVE_OS_RESOURCE " ARCH_LABEL " all-and-empty-memory-requests PASS\n");

    require(destroy_os(control, 0) == -EBUSY);
    close_fd(first);
    close_fd(second);
    close_fd(control);
    require(call(SYS_DELETE_MODULE, (long)"ihk_smp_x86_64", 0x800, 0) == -EAGAIN);
    control = open_control();
    require(destroy_os(control, 0) == 0);
    expect_memory(control, 60 * MIB, 64 * MIB - 4096);
    require(call(SYS_IOCTL, control, COUNT, 0) == 2);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 0);
    first = open_os(0);
    second = open_os(1);
    expect_os_cpu(first, 0, 0);
    expect_os_memory(first, 0, 0);
    require(request(first, OS_RELEASE_CPU, second_cpu, 1) == -EINVAL);
    require(mem_one(first, OS_RELEASE_MEM, 4 * MIB, 0) == -EINVAL);
    expect_os_cpu(second, second_cpu, 1);
    expect_os_memory(second, 4 * MIB, 4096);
    require(request(first, OS_ASSIGN_CPU, first_cpus, 2) == 0);
    require(mem_one(first, OS_ASSIGN_MEM, 4096, 0) == 0);
    concurrent_os_memory(control);
    expect_os_memory(first, 4096, 0);
    expect_os_memory(second, 4 * MIB, 4096);
    close_fd(first);
    close_fd(second);
    require(destroy_os(control, 0) == 0);
    require(destroy_os(control, 1) == 0);
    expect_memory(control, 64 * MIB, 64 * MIB);
    require(call(SYS_IOCTL, control, COUNT, 0) == 3);
    release_memory(control);
    require(request(control, RELEASE, reserved, 3) == 0);
    online_mask(15);
    close_fd(control);
    message("NATIVE_OS_RESOURCE " ARCH_LABEL " closed-files-generation-cleanup PASS\n");
    message("NATIVE_OS_RESOURCE " ARCH_LABEL " COMPLETE PASS\n");
    return 0;
}
