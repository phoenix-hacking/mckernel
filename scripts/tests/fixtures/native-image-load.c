/* SPDX-License-Identifier: GPL-2.0 */
/* Userspace-only probe for the disposable four-CPU/two-NUMA native guest. */
#define NATIVE_OS_RESOURCE_MAIN native_os_resource_reference_main
#include "native-os-resource-assignment.c"

#define OS_LOAD 0x112a00
#define OS_STATUS 0x112a03
#define OS_BOOT 0x112a01
static const char image_path[] = "/images/mckernel.img";
static char zone_information[65536];

__attribute__((noreturn)) static void image_fail(int line)
{
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " FAIL\n");
    fail(line);
}
#undef require
#define require(test) do { if (!(test)) image_fail(__LINE__); } while (0)

/* Linux 6.12 accounts these free pages on PCP lists, outside NR_FREE_PAGES. */
static unsigned long node_cached_free_kib(int wanted_node)
{
    int fd = call(SYS_OPEN, (long)"/proc/zoneinfo", 0, 0);
    require(fd >= 0);
    unsigned long used = 0;
    for (;;) {
        require(used < sizeof(zone_information) - 1);
        long count = call(SYS_READ, fd, (long)(zone_information + used),
                          sizeof(zone_information) - 1 - used);
        require(count >= 0);
        if (count == 0) break;
        used += count;
    }
    close_fd(fd);
    zone_information[used] = 0;
    int node = -1;
    unsigned long pages = 0;
    unsigned int samples = 0;
    for (unsigned long position = 0; position < used;) {
        unsigned long end = position;
        while (end < used && zone_information[end] != '\n') end++;
        char *line = zone_information + position;
        unsigned long length = end - position;
        if (length >= 6 && line[0] == 'N' && line[1] == 'o' &&
            line[2] == 'd' && line[3] == 'e' && line[4] == ' ') {
            unsigned long offset = 5;
            node = 0;
            require(line[offset] >= '0' && line[offset] <= '9');
            while (offset < length && line[offset] >= '0' && line[offset] <= '9')
                node = node * 10 + line[offset++] - '0';
            require(offset < length && line[offset] == ',');
        } else if (node == wanted_node) {
            unsigned long offset = 0;
            while (offset < length && (line[offset] == ' ' || line[offset] == '\t')) offset++;
            const char name[] = "count:";
            unsigned int match = 0;
            while (match < sizeof(name) - 1 && offset + match < length && line[offset + match] == name[match]) match++;
            if (match == sizeof(name) - 1) {
                offset += match;
                while (offset < length && (line[offset] == ' ' || line[offset] == '\t')) offset++;
                require(offset < length && line[offset] >= '0' && line[offset] <= '9');
                unsigned long value = 0;
                while (offset < length && line[offset] >= '0' && line[offset] <= '9')
                    value = value * 10 + line[offset++] - '0';
                pages += value;
                samples++;
            }
        }
        position = end + 1;
    }
    require(samples > 0);
    return pages * 4;
}

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

static void fail_startup_allocations(int fd)
{
    for (unsigned int attempt = 0; attempt < 8; attempt++) {
        allocation_failure(0);
        put_value(FI "min-order", "9");
        /* All high orders fail; vmalloc may fall back, the mandatory owned
         * order-9 startup allocation cannot. Only this task is affected. */
        put_value(FI "times", "-1");
        expect_load(fd, image_path, -ENOMEM);
        put_value("/proc/self/make-it-fail", "0");
        put_value(FI "times", "0");
        put_value(FI "min-order", "10");
    }
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

    unsigned long before_cached = node_cached_free_kib(0);
    unsigned long before_startup = node_free_kib(0);
    for (unsigned int attempt = 0; attempt < 8; attempt++) {
        expect_load(first, image_path, 0);
        expect_load(first, "/images/late-filesz.elf", -EINVAL);
    }
    /* All eight low-memory table owners have been invalidated. Include free
     * pages held in Linux's per-CPU caches: free_unref_page_commit() can move
     * several MiB there without returning them to zone NR_FREE_PAGES. The
     * allowance stays 4 MiB; an order-9 owner leaked per load loses 16 MiB. */
    unsigned long after_cached = node_cached_free_kib(0);
    unsigned long after_startup = node_free_kib(0);
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " startup-memory-kib before=");
    print_number(before_startup);
    message(" after=");
    print_number(after_startup);
    message(" cached-before=");
    print_number(before_cached);
    message(" cached-after=");
    print_number(after_cached);
    message("\n");
    require(after_startup + after_cached + 4096 >= before_startup + before_cached);
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " startup-owner-cleanup=8 PASS\n");
    fail_startup_allocations(first);
    expect_load(first, image_path, 0);
    fail_startup_allocations(first);
    message("NATIVE_IMAGE_LOAD " ARCH_LABEL " startup-allocation-failures=16 PASS\n");
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
