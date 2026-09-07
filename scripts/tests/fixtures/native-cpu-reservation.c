/* SPDX-License-Identifier: GPL-2.0 */
/* Freestanding userspace probe. Execute only in the disposable four-CPU guest. */
#if defined(__x86_64__)
#define SYS_READ 0
#define SYS_WRITE 1
#define SYS_OPEN 2
#define SYS_CLOSE 3
#define SYS_IOCTL 16
#define SYS_FORK 57
#define SYS_WAIT 61
#define SYS_EXIT 60
#define SYS_DELETE_MODULE 176
#define ARCH_LABEL "x86_64"
__asm__(".global _start\n_start:\nxor %ebp,%ebp\nandq $-16,%rsp\ncall main\n"
        "mov %eax,%edi\nmov $60,%eax\nsyscall\nud2\n");
static long call(long nr, long a, long b, long c)
{
    long result;
    register long fourth __asm__("r10") = 0;
    __asm__ volatile("syscall" : "=a"(result) : "0"(nr), "D"(a), "S"(b),
                     "d"(c), "r"(fourth) : "rcx", "r11", "memory");
    return result;
}
#else
#define SYS_READ 3
#define SYS_WRITE 4
#define SYS_OPEN 5
#define SYS_CLOSE 6
#define SYS_IOCTL 54
#define SYS_FORK 2
#define SYS_WAIT 7
#define SYS_EXIT 1
#define SYS_DELETE_MODULE 129
#define ARCH_LABEL "i386"
__asm__(".global _start\n_start:\nxor %ebp,%ebp\nandl $-16,%esp\ncall main\n"
        "mov %eax,%ebx\nmov $1,%eax\nint $0x80\nud2\n");
static long call(long nr, long a, long b, long c)
{
    long result;
    __asm__ volatile("int $0x80" : "=a"(result) : "0"(nr), "b"(a), "c"(b),
                     "d"(c) : "memory");
    return result;
}
#endif

#ifndef CPUHP_FAILURE_STATE
#error CPUHP_FAILURE_STATE must come from the exact kernel bindings
#endif
#define STRINGIFY_INNER(value) #value
#define STRINGIFY(value) STRINGIFY_INNER(value)

#define RESERVE 0x112902
#define RELEASE 0x112903
#define QUERY 0x112906
#define COUNT 0x11290c
#define EINVAL 22
#define EFAULT 14
#define EBUSY 16
#define EAGAIN 11
struct request { int *cpus; int count; };
_Static_assert(sizeof(struct request) == (sizeof(void *) == 8 ? 16 : 8), "request ABI");

static unsigned long length(const char *text)
{
    unsigned long n = 0;
    while (text[n]) n++;
    return n;
}
static void message(const char *text)
{
    call(SYS_WRITE, 1, (long)text, length(text));
}
__attribute__((noreturn)) static void fail(int line)
{
    char digits[12];
    int n = 0;
    message("NATIVE_CPU_RESERVATION " ARCH_LABEL " FAIL line=");
    do { digits[n++] = '0' + line % 10; line /= 10; } while (line);
    while (n) call(SYS_WRITE, 1, (long)&digits[--n], 1);
    message("\n");
    call(SYS_EXIT, 1, 0, 0);
    __builtin_unreachable();
}
#define require(test) do { if (!(test)) fail(__LINE__); } while (0)

static long command(int fd, unsigned long cmd, struct request *request)
{
    return call(SYS_IOCTL, fd, cmd, (long)request);
}
static long request(int fd, unsigned long cmd, int *cpus, int count)
{
    struct request value = { cpus, count };
    return command(fd, cmd, &value);
}
static int open_control(void)
{
    int fd = call(SYS_OPEN, (long)"/dev/mcd0", 2, 0);
    require(fd >= 0);
    return fd;
}
static void close_fd(int fd) { require(call(SYS_CLOSE, fd, 0, 0) == 0); }

static const char *online_path[] = {
    "/sys/devices/system/cpu/online",
    "/sys/devices/system/cpu/cpu1/online",
    "/sys/devices/system/cpu/cpu2/online",
    "/sys/devices/system/cpu/cpu3/online",
};
static const char *fail_path[] = {
    "", "/sys/devices/system/cpu/cpu1/hotplug/fail",
    "/sys/devices/system/cpu/cpu2/hotplug/fail",
    "/sys/devices/system/cpu/cpu3/hotplug/fail",
};
static char first_byte(const char *path)
{
    char result = '?';
    int fd = call(SYS_OPEN, (long)path, 0, 0);
    require(fd >= 0);
    require(call(SYS_READ, fd, (long)&result, 1) == 1);
    close_fd(fd);
    return result;
}
static void online_mask(unsigned int mask)
{
    require(first_byte(online_path[0]) == '0');
    for (int cpu = 1; cpu < 4; cpu++)
        require(first_byte(online_path[cpu]) == ((mask & (1U << cpu)) ? '1' : '0'));
}
static long write_file(const char *path, const char *value)
{
    int fd = call(SYS_OPEN, (long)path, 1, 0);
    long status;
    require(fd >= 0);
    status = call(SYS_WRITE, fd, (long)value, length(value));
    close_fd(fd);
    return status;
}
static void inject_failure(int cpu)
{
    const char *value = STRINGIFY(CPUHP_FAILURE_STATE) "\n";
    require(write_file(fail_path[cpu], value) == (long)length(value));
}
static void query_all(int fd)
{
    int result[3] = {-1, -1, -1};
    require(command(fd, COUNT, 0) == 3);
    require(request(fd, QUERY, result, 3) == 0);
    require(result[0] == 1 && result[1] == 2 && result[2] == 3);
}

static void concurrent_cycles(int fd)
{
    int children[3];
    close_fd(fd);
    for (int worker = 0; worker < 3; worker++) {
        children[worker] = call(SYS_FORK, 0, 0, 0);
        require(children[worker] >= 0);
        if (children[worker] == 0) {
            int child_fd = open_control();
            int cpu = worker + 1;
            for (int iteration = 0; iteration < 8; iteration++) {
                require(request(child_fd, RESERVE, &cpu, 1) == 0);
                require(first_byte(online_path[cpu]) == '0');
                require(request(child_fd, RELEASE, &cpu, 1) == 0);
                require(first_byte(online_path[cpu]) == '1');
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
    online_mask(15);
    message("NATIVE_CPU_RESERVATION " ARCH_LABEL " concurrent=3x8 PASS\n");
}

int main(void)
{
    int fd = open_control();
    int all[] = {1, 2, 3};
    int duplicates[] = {3, 1, 3, 2};
    int partial[] = {3, 1, 3};
    int invalid;
    online_mask(15);
    require(command(fd, COUNT, 0) == 0);
    require(request(fd, QUERY, 0, 0) == 0);
    require(request(fd, RESERVE, 0, 0) == 0);
    require(request(fd, RELEASE, 0, 0) == 0);
    require(command(fd, RESERVE, (void *)1) == -EFAULT);
    require(request(fd, RESERVE, 0, 1) == -EINVAL);
    require(request(fd, RESERVE, all, -1) == -EINVAL);
    require(request(fd, RESERVE, all, 513) == -EINVAL);
    require(request(fd, RESERVE, (void *)1, 1) == -EFAULT);
    for (invalid = -1; invalid <= 0; invalid++)
        require(request(fd, RESERVE, &invalid, 1) == -EINVAL);
    invalid = 4;
    require(request(fd, RESERVE, &invalid, 1) == -EINVAL);
    require(command(fd, COUNT, 0) == 0);
    online_mask(15);

    /* Real Linux hotplug errors at every batch position, in both directions. */
    for (int cpu = 1; cpu < 4; cpu++) {
        inject_failure(cpu);
        require(request(fd, RESERVE, all, 3) == -EAGAIN);
        require(command(fd, COUNT, 0) == 0);
        online_mask(15);
    }
    message("NATIVE_CPU_RESERVATION " ARCH_LABEL " reserve-rollback=3 PASS\n");
    require(request(fd, RESERVE, duplicates, 4) == 0);
    online_mask(1);
    query_all(fd);
    require(request(fd, QUERY, all, 2) == -EINVAL);
    require(request(fd, QUERY, (void *)1, 3) == -EFAULT);
    require(request(fd, QUERY, 0, 3) == -EINVAL);
    require(request(fd, RELEASE, (void *)1, 1) == -EFAULT);
    require(request(fd, RESERVE, all, 1) == -EINVAL);
    query_all(fd);
    for (int cpu = 1; cpu < 4; cpu++) {
        require(write_file(online_path[cpu], "1\n") == -EBUSY);
        online_mask(1);
    }
    close_fd(fd);
    require(call(SYS_DELETE_MODULE, (long)"ihk_smp_x86_64", 0x800, 0) == -EAGAIN);
    fd = open_control();
    query_all(fd);
    message("NATIVE_CPU_RESERVATION " ARCH_LABEL " online-veto-and-closed-file-pin PASS\n");
    for (int cpu = 1; cpu < 4; cpu++) {
        inject_failure(cpu);
        require(request(fd, RELEASE, all, 3) == -EAGAIN);
        query_all(fd);
        online_mask(1);
    }
    message("NATIVE_CPU_RESERVATION " ARCH_LABEL " release-rollback=3 PASS\n");
    require(request(fd, RELEASE, partial, 3) == 0);
    require(command(fd, COUNT, 0) == 1);
    online_mask(11);
    require(request(fd, RESERVE, partial, 3) == 0);
    query_all(fd);
    require(request(fd, RELEASE, all, 3) == 0);
    require(command(fd, COUNT, 0) == 0);
    online_mask(15);
    concurrent_cycles(fd);
    fd = open_control();
    require(command(fd, COUNT, 0) == 0);
    close_fd(fd);
    message("NATIVE_CPU_RESERVATION " ARCH_LABEL " COMPLETE PASS\n");
    return 0;
}
