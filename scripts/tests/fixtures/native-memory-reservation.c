/* SPDX-License-Identifier: GPL-2.0 */
/* Userspace validation only: run inside the disposable four-CPU NUMA guest.
 * Reuse the complete CPU probe and its freestanding syscall implementation. */
#define main native_cpu_reference_main
#include "native-cpu-reservation.c"
#undef main

#define MEM_RESERVE 0x112904
#define MEM_RELEASE 0x112905
#define MEM_QUERY 0x112907
#define MEM_PARTIAL 0x11290d
#define ENOMEM 12
#define MIB (1024UL * 1024UL)
#define CAPACITY 4096
#if defined(__x86_64__)
#define SYS_MPROTECT 10
#define SYS_EXECVE 59
#else
#define SYS_MPROTECT 125
#define SYS_EXECVE 11
#endif
struct memory_request {
    unsigned long *sizes;
    int *nodes;
    int count, minimum, ratio, timeout;
};
_Static_assert(sizeof(struct memory_request) == (sizeof(void *) == 8 ? 32 : 24), "memory ABI");
static unsigned long query_sizes[CAPACITY + 1];
static int query_nodes[CAPACITY + 1];
static unsigned long totals[2];
static unsigned char copy_boundary[8192] __attribute__((aligned(4096)));

__attribute__((noreturn)) static void memory_fail(int line)
{
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " FAIL\n");
    fail(line);
}
#undef require
#define require(test) do { if (!(test)) memory_fail(__LINE__); } while (0)

static struct memory_request mem_request(unsigned long *sizes, int *nodes, int count)
{
    struct memory_request value = { sizes, nodes, count, 4 * MIB, 95, 30 };
    return value;
}
static long mem_command(int fd, unsigned long op, struct memory_request *value)
{
    return call(SYS_IOCTL, fd, op, (long)value);
}
static long mem_one(int fd, unsigned long op, unsigned long bytes, int node)
{
    struct memory_request value = mem_request(&bytes, &node, 1);
    return mem_command(fd, op, &value);
}
static int query_memory(int fd)
{
    struct memory_request value = mem_request(0, 0, 0);
    require(mem_command(fd, MEM_QUERY, &value) == 0);
    require(value.count >= 0 && value.count <= CAPACITY);
    int count = value.count;
    query_sizes[CAPACITY] = 0x13579UL;
    query_nodes[CAPACITY] = 0x2468;
    value = mem_request(query_sizes, query_nodes, CAPACITY);
    require(mem_command(fd, MEM_QUERY, &value) == 0);
    require(value.count == count);
    require(query_sizes[CAPACITY] == 0x13579UL && query_nodes[CAPACITY] == 0x2468);
    totals[0] = totals[1] = 0;
    for (int i = 0; i < count; i++) {
        require(query_sizes[i] > 0 && query_sizes[i] % 4096 == 0);
        require(query_nodes[i] == 0 || query_nodes[i] == 1);
        totals[query_nodes[i]] += query_sizes[i];
    }
    return count;
}
static void expect_memory(int fd, unsigned long node0, unsigned long node1)
{
    query_memory(fd);
    require(totals[0] == node0 && totals[1] == node1);
}
static void release_memory(int fd)
{
    int count = query_memory(fd);
    struct memory_request value = mem_request(query_sizes, query_nodes, count);
    require(mem_command(fd, MEM_RELEASE, &value) == 0);
    expect_memory(fd, 0, 0);
}
static void put_value(const char *path, const char *value)
{
    require(write_file(path, value) == (long)length(value));
}
static void put_number(const char *path, unsigned long value)
{
    char text[24];
    unsigned int index = sizeof(text) - 1;
    text[index] = 0;
    do { text[--index] = '0' + value % 10; value /= 10; } while (value);
    put_value(path, &text[index]);
}
static void print_number(unsigned long value)
{
    char text[24];
    unsigned int index = sizeof(text) - 1;
    text[index] = 0;
    do { text[--index] = '0' + value % 10; value /= 10; } while (value);
    message(&text[index]);
}
#define FI "/sys/kernel/debug/fail_page_alloc/"
static void allocation_failure(unsigned int position)
{
    put_value(FI "times", "0");
    put_value(FI "task-filter", "1");
    put_value(FI "ignore-gfp-wait", "0");
    put_value(FI "min-order", "10");
    put_value(FI "verbose", "0");
    put_value(FI "probability", "100");
    put_value(FI "interval", "1");
    /* Linux's space counter skips while space > (1 << allocation order). */
    put_number(FI "space", position * 1024UL);
    put_value(FI "times", "1");
    put_value("/proc/self/make-it-fail", "1");
}
static void allocation_failure_consumed(void)
{
    put_value("/proc/self/make-it-fail", "0");
    require(first_byte(FI "times") == '0');
    put_value(FI "times", "0");
}
static unsigned long node_free_kib(int node)
{
    const char *paths[] = { "/sys/devices/system/node/node0/meminfo",
                           "/sys/devices/system/node/node1/meminfo" };
    const char needle[] = "MemFree:";
    char data[4096];
    int fd = call(SYS_OPEN, (long)paths[node], 0, 0);
    require(fd >= 0);
    long size = call(SYS_READ, fd, (long)data, sizeof(data) - 1);
    require(size > 0);
    close_fd(fd);
    data[size] = 0;
    for (long i = 0; i < size; i++) {
        unsigned int j = 0;
        while (j < sizeof(needle) - 1 && (unsigned long)i + j < (unsigned long)size && data[i + j] == needle[j]) j++;
        if (j == sizeof(needle) - 1) {
            unsigned long result = 0;
            i += j;
            while (data[i] == ' ' || data[i] == '\t') i++;
            require(data[i] >= '0' && data[i] <= '9');
            while (data[i] >= '0' && data[i] <= '9') result = result * 10 + data[i++] - '0';
            return result;
        }
    }
    memory_fail(__LINE__);
}
static void invalid_requests(int fd)
{
    unsigned long bytes = 4 * MIB;
    int node = 0;
    struct memory_request value = mem_request(&bytes, &node, 1);
    struct memory_request empty = mem_request(0, 0, 0);
    static const struct memory_request readonly_empty = { 0, 0, 0, 0, 0, 0 };
    require(mem_command(fd, MEM_RESERVE, &empty) == 0);
    require(mem_command(fd, MEM_RELEASE, &empty) == 0);
    require(mem_command(fd, MEM_PARTIAL, &empty) == 0);
    require(mem_command(fd, MEM_RESERVE, (void *)1) == -EFAULT);
    require(mem_command(fd, MEM_QUERY, (struct memory_request *)&readonly_empty) == -EFAULT);
    value.count = -1;
    require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);
    value.count = CAPACITY + 1;
    require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);
    value.count = 1;
    value.sizes = 0;
    require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);
    value.sizes = (void *)1;
    require(mem_command(fd, MEM_RESERVE, &value) == -EFAULT);
    value.sizes = &bytes;
    value.nodes = (void *)1;
    require(mem_command(fd, MEM_RESERVE, &value) == -EFAULT);
    value.nodes = &node;
    const int invalid_nodes[] = { -1, 2, 1024 };
    for (unsigned int i = 0; i < sizeof(invalid_nodes) / sizeof(invalid_nodes[0]); i++) {
        node = invalid_nodes[i];
        require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);
    }
    node = 0;
    bytes = 4096;
    require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);
    bytes = 4 * MIB;
    value.minimum = -1;
    require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);
    value.minimum = 4 * MIB + 1;
    require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);
    value.minimum = 4 * MIB;
    value.ratio = 99;
    require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);
    value.ratio = -1;
    require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);
    value.ratio = 95;
    value.timeout = -1;
    require(mem_command(fd, MEM_RESERVE, &value) == -EINVAL);

    /* A readable first size followed by an inaccessible second size must be
     * rejected before allocation. The untouched fault counter proves ordering. */
    unsigned long *boundary = (unsigned long *)&copy_boundary[4096 - sizeof(unsigned long)];
    int boundary_nodes[] = { 0, 1 };
    *boundary = 4 * MIB;
    require(call(SYS_MPROTECT, (long)&copy_boundary[4096], 4096, 0) == 0);
    value = mem_request(boundary, boundary_nodes, 2);
    allocation_failure(1);
    require(mem_command(fd, MEM_RESERVE, &value) == -EFAULT);
    put_value("/proc/self/make-it-fail", "0");
    require(first_byte(FI "times") == '1');
    put_value(FI "times", "0");
    require(call(SYS_MPROTECT, (long)&copy_boundary[4096], 4096, 3) == 0);
    expect_memory(fd, 0, 0);
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " malformed-copyfaults PASS\n");
}
static int os_lifecycle_with_reserved_memory(int fd)
{
    /* Reuse the existing assembly BUILDID/OS lifecycle probe unchanged.
     * Creating and destroying unbooted OS instances must preserve this pool. */
    const char *path = "/bin/mcd0-ioctl-" ARCH_LABEL;
    const char *argv[] = { path, "3114d9e", 0 };
    const char *envp[] = { 0 };
    close_fd(fd);
    long child = call(SYS_FORK, 0, 0, 0);
    require(child >= 0);
    if (child == 0) {
        call(SYS_EXECVE, (long)path, (long)argv, (long)envp);
        memory_fail(__LINE__);
    }
    int status = -1;
    require(call(SYS_WAIT, child, (long)&status, 0) == child);
    require(status == 0);
    fd = open_control();
    expect_memory(fd, 16 * MIB, 16 * MIB);
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " unbooted-os-preserves-pool PASS\n");
    return fd;
}
static int normal_and_release(int fd)
{
    unsigned long sizes[] = { 8 * MIB, 8 * MIB, 16 * MIB };
    int nodes[] = { 0, 0, 1 };
    struct memory_request value = mem_request(sizes, nodes, 3);
    require(mem_command(fd, MEM_RESERVE, &value) == 0);
    expect_memory(fd, 16 * MIB, 16 * MIB);
    int count = query_memory(fd);
    require(count >= 2);
    value = mem_request(query_sizes, query_nodes, count - 1);
    require(mem_command(fd, MEM_QUERY, &value) == -EINVAL);
    value = mem_request((void *)1, query_nodes, count);
    require(mem_command(fd, MEM_QUERY, &value) == -EFAULT);
    value = mem_request(query_sizes, (void *)1, count);
    require(mem_command(fd, MEM_QUERY, &value) == -EFAULT);
    expect_memory(fd, 16 * MIB, 16 * MIB);
    close_fd(fd);
    require(call(SYS_DELETE_MODULE, (long)"ihk_smp_x86_64", 0x800, 0) == -EAGAIN);
    fd = open_control();
    expect_memory(fd, 16 * MIB, 16 * MIB);
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " numa-query-closed-file-pin PASS\n");
    fd = os_lifecycle_with_reserved_memory(fd);

    sizes[0] = query_sizes[0]; sizes[1] = 3 * 4096;
    nodes[0] = query_nodes[0]; nodes[1] = 0;
    value = mem_request(sizes, nodes, 2);
    require(mem_command(fd, MEM_RELEASE, &value) == -EINVAL);
    expect_memory(fd, 16 * MIB, 16 * MIB);
    sizes[0] = 4 * MIB; sizes[1] = 128 * MIB;
    nodes[0] = 0; nodes[1] = 1;
    require(mem_command(fd, MEM_PARTIAL, &value) == -EINVAL);
    expect_memory(fd, 16 * MIB, 16 * MIB);
    require(mem_one(fd, MEM_PARTIAL, 5 * MIB, 0) == 0);
    expect_memory(fd, 12 * MIB, 16 * MIB);
    require(mem_one(fd, MEM_PARTIAL, MIB, 0) == 0);
    expect_memory(fd, 12 * MIB, 16 * MIB);
    release_memory(fd);
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " release-preflight-partial-rounding PASS\n");
    return fd;
}
static void failed_allocations(int fd)
{
    unsigned long sizes[] = { 16 * MIB, 16 * MIB };
    int nodes[] = { 0, 1 };
    struct memory_request value = mem_request(sizes, nodes, 2);
    /* Warm metadata before measuring physical cleanup. */
    require(mem_command(fd, MEM_RESERVE, &value) == 0);
    release_memory(fd);
    require(mem_one(fd, MEM_RESERVE, 8 * MIB, 0) == 0);
    unsigned long before[] = { node_free_kib(0), node_free_kib(1) };
    for (int round = 0; round < 3; round++) {
        for (unsigned int position = 1; position <= 8; position++) {
            allocation_failure(position);
            require(mem_command(fd, MEM_RESERVE, &value) == -ENOMEM);
            allocation_failure_consumed();
            expect_memory(fd, 8 * MIB, 0);
        }
    }
    for (int node = 0; node < 2; node++) {
        unsigned long after = node_free_kib(node);
        message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " free-kib node=");
        print_number(node);
        message(" before="); print_number(before[node]);
        message(" after="); print_number(after);
        message(" tolerance=8192\n");
        require(after + 8192 >= before[node]);
    }
    release_memory(fd);
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " allocation-rollback=8x3-no-leak PASS\n");

    sizes[0] = 8 * MIB; nodes[0] = 1;
    value = mem_request(sizes, nodes, 1);
    value.minimum = 4096;
    allocation_failure(1);
    require(mem_command(fd, MEM_RESERVE, &value) == 0);
    allocation_failure_consumed();
    expect_memory(fd, 0, 8 * MIB);
    release_memory(fd);
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " allocation-order-fallback PASS\n");

    sizes[0] = ~0UL;
    value = mem_request(sizes, nodes, 1);
    value.ratio = 1;
    require(mem_command(fd, MEM_RESERVE, &value) == 0);
    query_memory(fd);
    require(totals[0] == 0 && totals[1] > 0 && totals[1] <= 48 * MIB);
    release_memory(fd);
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " bounded-all-request PASS\n");
}
static void concurrent_memory(int fd)
{
    int children[3];
    close_fd(fd);
    for (int worker = 0; worker < 3; worker++) {
        children[worker] = call(SYS_FORK, 0, 0, 0);
        require(children[worker] >= 0);
        if (children[worker] == 0) {
            int child_fd = open_control();
            for (int iteration = 0; iteration < 8; iteration++) {
                require(mem_one(child_fd, MEM_RESERVE, 4 * MIB, worker % 2) == 0);
                require(mem_one(child_fd, MEM_PARTIAL, 4 * MIB, worker % 2) == 0);
            }
            close_fd(child_fd);
            call(SYS_EXIT, 0, 0, 0);
            __builtin_unreachable();
        }
    }
    for (int worker = 0; worker < 3; worker++) {
        int status = -1;
        require(call(SYS_WAIT, children[worker], (long)&status, 0) == children[worker]);
        require(status == 0);
    }
    fd = open_control();
    expect_memory(fd, 0, 0);
    close_fd(fd);
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " concurrent=3x8 PASS\n");
}
int main(void)
{
    require(native_cpu_reference_main() == 0);
    int fd = open_control();
    expect_memory(fd, 0, 0);
    invalid_requests(fd);
    fd = normal_and_release(fd);
    failed_allocations(fd);
    concurrent_memory(fd);
    message("NATIVE_MEMORY_RESERVATION " ARCH_LABEL " COMPLETE PASS\n");
    return 0;
}
