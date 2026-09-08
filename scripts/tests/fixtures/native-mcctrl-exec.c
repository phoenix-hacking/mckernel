/* SPDX-License-Identifier: GPL-2.0 */
/* Real native mcctrl/VFS/caller-credential checks; isolated Linux guest only. */
#define NATIVE_OS_RESOURCE_MAIN native_os_resource_reference_main
#include "native-os-resource-assignment.c"

#define OPEN_EXEC 0x30a02912
#define CLOSE_EXEC 0x30a02913
#define GET_CREDV 0x30a0290b
#define PATH_LIMIT 4096
#if defined(__x86_64__)
#define SYS_DUP 32
#define SYS_PIPE 22
#define SYS_MPROTECT 10
#define SYS_MUNMAP 11
#define SYS_SETRESUID 117
#define SYS_GETRESUID 118
#define SYS_SETRESGID 119
#define SYS_GETRESGID 120
#define SYS_SETFSUID 122
#define SYS_SETFSGID 123
#else
#define SYS_DUP 41
#define SYS_PIPE 42
#define SYS_MPROTECT 125
#define SYS_MUNMAP 91
#define SYS_SETRESUID 208
#define SYS_GETRESUID 209
#define SYS_SETRESGID 210
#define SYS_GETRESGID 211
#define SYS_SETFSUID 215
#define SYS_SETFSGID 216
#endif

static unsigned credential_checks, file_checks;

static void *map_pages(void)
{
    long result;
#if defined(__x86_64__)
    register long fourth __asm__("r10") = 34;
    register long fifth __asm__("r8") = -1;
    register long sixth __asm__("r9") = 0;
    __asm__ volatile("syscall" : "=a"(result) : "0"(9L), "D"(0L), "S"(8192L),
                     "d"(3L), "r"(fourth), "r"(fifth), "r"(sixth)
                     : "rcx", "r11", "memory");
#else
    unsigned long args[6] = {0, 8192, 3, 34, (unsigned long)-1, 0};
    result = call(90, (long)args, 0, 0);
#endif
    require((unsigned long)result < (unsigned long)-4095);
    return (void *)result;
}

static void copy_bytes(void *dst, const void *src, unsigned length)
{
    for (unsigned i = 0; i < length; i++) ((char *)dst)[i] = ((const char *)src)[i];
}

static void expected_credentials(unsigned values[8])
{
    require(call(SYS_GETRESUID, (long)&values[0], (long)&values[1], (long)&values[2]) == 0);
    values[3] = call(SYS_SETFSUID, -1, 0, 0);
    require(call(SYS_GETRESGID, (long)&values[4], (long)&values[5], (long)&values[6]) == 0);
    values[7] = call(SYS_SETFSGID, -1, 0, 0);
}

static void credentials(int fd)
{
    struct { unsigned before[4], values[8], after[4]; } result;
    unsigned expected[8];
    expected_credentials(expected);
    for (int i = 0; i < 4; i++) result.before[i] = result.after[i] = 0x13579bdf;
    for (int i = 0; i < 8; i++) result.values[i] = 0xa5a5a5a5;
    require(call(SYS_IOCTL, fd, GET_CREDV, (long)result.values) == 0);
    for (int i = 0; i < 4; i++) require(result.before[i] == 0x13579bdf && result.after[i] == 0x13579bdf);
    for (int i = 0; i < 8; i++) require(result.values[i] == expected[i]);
    credential_checks++;
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

static void join(int pid)
{
    int status = -1;
    require(call(SYS_WAIT, pid, (long)&status, 0) == pid && status == 0);
}

static void caller_credentials(int fd)
{
    int start[2], children[4];
    require(call(SYS_PIPE, (long)start, 0, 0) == 0);
    for (int worker = 0; worker < 4; worker++) {
        children[worker] = call(SYS_FORK, 0, 0, 0);
        require(children[worker] >= 0);
        if (children[worker] == 0) {
            unsigned uid = 70001 + 10 * worker, gid = 80001 + 10 * worker;
            require(call(SYS_SETRESGID, gid, gid + 1, gid + 2) == 0);
            require(call(SYS_SETFSGID, gid + 3, 0, 0) == (long)gid + 1);
            require(call(SYS_SETRESUID, uid, uid + 1, uid + 2) == 0);
            require(call(SYS_SETFSUID, uid, 0, 0) == (long)uid + 1);
            unsigned observed[8]; expected_credentials(observed);
            require(observed[0] == uid && observed[1] == uid + 1 && observed[2] == uid + 2 && observed[3] == uid);
            require(observed[4] == gid && observed[5] == gid + 1 && observed[6] == gid + 2 && observed[7] == gid + 3);
            wait_one(start[0]);
            for (int round = 0; round < 64; round++) {
                call(SYS_SETFSUID, (round & 1) ? uid : uid + 2, 0, 0);
                credentials(fd);
            }
            call(SYS_EXIT, 0, 0, 0);
            __builtin_unreachable();
        }
    }
    for (int worker = 0; worker < 4; worker++) signal_one(start[1]);
    for (int worker = 0; worker < 4; worker++) join(children[worker]);
    close_fd(start[0]); close_fd(start[1]);
    credential_checks += 4 * 64;
    credentials(fd);
}

static void write_access(const char *path, int denied)
{
    long writer = call(SYS_OPEN, (long)path, 1, 0);
    if (denied) require(writer == -26);
    else { require(writer >= 0); close_fd(writer); }
    file_checks++;
}

static void open_exec(int fd, const char *path, long expected)
{
    long actual = call(SYS_IOCTL, fd, OPEN_EXEC, (long)path);
    if (actual != expected) {
        message("NATIVE_MCCTRL_OPEN_RESULT index="); print_number(file_checks);
        message(" actual_negative="); print_number(actual < 0);
        message(" actual_magnitude="); print_number(actual < 0 ? -actual : actual);
        message(" expected_negative="); print_number(expected < 0);
        message(" expected_magnitude="); print_number(expected < 0 ? -expected : expected);
        message(" credential_checks="); print_number(credential_checks); message("\n");
    }
    require(actual == expected);
    file_checks++;
}

static void close_exec(int fd, long expected)
{
    require(call(SYS_IOCTL, fd, CLOSE_EXEC, -1) == expected);
    file_checks++;
}

static void boundary_buffers(int fd)
{
    char *pages = map_pages();
    require(call(SYS_MPROTECT, (long)(pages + PATH_LIMIT), PATH_LIMIT, 0) == 0);
    unsigned expected[8]; expected_credentials(expected);
    unsigned *values = (unsigned *)(pages + PATH_LIMIT - 32);
    require(call(SYS_IOCTL, fd, GET_CREDV, (long)values) == 0);
    for (int i = 0; i < 8; i++) require(values[i] == expected[i]);
    credential_checks++;
    require(call(SYS_IOCTL, fd, GET_CREDV, 1) == -EFAULT);
    require(call(SYS_IOCTL, fd, GET_CREDV, (long)(pages + PATH_LIMIT - 16)) == -EFAULT);
    require(call(SYS_MPROTECT, (long)pages, PATH_LIMIT, 1) == 0);
    require(call(SYS_IOCTL, fd, GET_CREDV, (long)pages) == -EFAULT);
    require(call(SYS_MPROTECT, (long)pages, PATH_LIMIT, 3) == 0);
    const char path[] = "/targets/one";
    char *boundary = pages + PATH_LIMIT - sizeof(path);
    copy_bytes(boundary, path, sizeof(path));
    open_exec(fd, boundary, 0);
    write_access(path, 1);
    for (int i = 0; i < PATH_LIMIT; i++) pages[i] = 'a';
    open_exec(fd, pages, -36);
    write_access(path, 1);
    open_exec(fd, (char *)1, -EINVAL);
    write_access(path, 1);
    close_exec(fd, 0);
    write_access(path, 0);
    require(call(SYS_MUNMAP, (long)pages, 8192, 0) == 0);
}

static void replacement_and_files(int fd)
{
    close_exec(fd, EINVAL);
    open_exec(fd, "", -2);
    open_exec(fd, "/targets/missing", -2);
    open_exec(fd, "/targets", -13);
    open_exec(fd, "/targets/notexec", -13);
    open_exec(fd, "/noexec/one", -13);
    int writer = call(SYS_OPEN, (long)"/targets/one", 1, 0);
    require(writer >= 0);
    open_exec(fd, "/targets/one", -26);
    close_fd(writer);
    open_exec(fd, "/targets/one", 0);
    write_access("/targets/one", 1);
    open_exec(fd, "/targets/missing", -2);
    write_access("/targets/one", 1);
    open_exec(fd, "/targets/link", 0);
    write_access("/targets/one", 1);
    int separate = open_os(0);
    open_exec(separate, "/targets/two", 0);
    write_access("/targets/one", 0);
    write_access("/targets/two", 1);
    /* CLOSE on another descriptor of the same process finds the same owner. */
    close_exec(fd, 0);
    write_access("/targets/two", 0);
    close_exec(separate, EINVAL);
    open_exec(separate, "/targets/two", 0);
    close_fd(separate);
    write_access("/targets/two", 1);
    close_exec(fd, 0);
    write_access("/targets/two", 0);
}

static void forked_owners(int fd)
{
    int ready[2], finish[2];
    require(call(SYS_PIPE, (long)ready, 0, 0) == 0);
    require(call(SYS_PIPE, (long)finish, 0, 0) == 0);
    open_exec(fd, "/targets/one", 0);
    int child = call(SYS_FORK, 0, 0, 0);
    require(child >= 0);
    if (child == 0) {
        open_exec(fd, "/targets/two", 0);
        signal_one(ready[1]); wait_one(finish[0]);
        close_exec(fd, 0);
        signal_one(ready[1]); wait_one(finish[0]);
        call(SYS_EXIT, 0, 0, 0);
        __builtin_unreachable();
    }
    wait_one(ready[0]);
    write_access("/targets/one", 1);
    write_access("/targets/two", 1);
    signal_one(finish[1]); wait_one(ready[0]);
    write_access("/targets/one", 1);
    write_access("/targets/two", 0);
    close_exec(fd, 0);
    signal_one(finish[1]); join(child);
    file_checks += 2;
    close_fd(ready[0]); close_fd(ready[1]); close_fd(finish[0]); close_fd(finish[1]);
}

static void concurrent_replacements(int fd)
{
    int children[4], start[2];
    require(call(SYS_PIPE, (long)start, 0, 0) == 0);
    for (int worker = 0; worker < 4; worker++) {
        children[worker] = call(SYS_FORK, 0, 0, 0);
        require(children[worker] >= 0);
        if (children[worker] == 0) {
            wait_one(start[0]);
            for (int round = 0; round < 32; round++) {
                open_exec(fd, "/targets/one", 0);
                open_exec(fd, "/targets/two", 0);
                close_exec(fd, 0);
                close_exec(fd, EINVAL);
            }
            call(SYS_EXIT, 0, 0, 0);
            __builtin_unreachable();
        }
    }
    for (int worker = 0; worker < 4; worker++) signal_one(start[1]);
    for (int worker = 0; worker < 4; worker++) join(children[worker]);
    close_fd(start[0]); close_fd(start[1]);
    file_checks += 4 * 32 * 4;
    write_access("/targets/one", 0); write_access("/targets/two", 0);
}

static void final_release(int fd)
{
    open_exec(fd, "/targets/one", 0);
    int duplicate = call(SYS_DUP, fd, 0, 0);
    require(duplicate >= 0);
    close_fd(fd);
    write_access("/targets/one", 1);
    close_fd(duplicate);
    write_access("/targets/one", 0);
    /* A child-only open file is retired automatically at Linux process exit. */
    int child = call(SYS_FORK, 0, 0, 0);
    require(child >= 0);
    if (child == 0) {
        int own = open_os(0);
        open_exec(own, "/targets/two", 0);
        call(SYS_EXIT, 0, 0, 0);
        __builtin_unreachable();
    }
    join(child);
    file_checks++;
    write_access("/targets/two", 0);
}

int main(void)
{
    /* Populate the mounted noexec filesystem with the same executable bytes.
     * The minimal initramfs intentionally has no external cp utility. */
    int source = call(SYS_OPEN, (long)"/targets/one", 0, 0);
    int target = call(SYS_OPEN, (long)"/noexec/one", 1 | 64 | 128, 0755);
    require(source >= 0 && target >= 0);
    char block[512];
    long bytes;
    while ((bytes = call(SYS_READ, source, (long)block, sizeof(block))) > 0)
        require(call(SYS_WRITE, target, (long)block, bytes) == bytes);
    require(bytes == 0);
    close_fd(source); close_fd(target);
    int fd = open_os(0);
    credentials(fd);
    caller_credentials(fd);
    boundary_buffers(fd);
    replacement_and_files(fd);
    forked_owners(fd);
    concurrent_replacements(fd);
    final_release(fd);
    online_mask(13);
    message("NATIVE_MCCTRL_EXEC " ARCH_LABEL " PASS credential_checks=");
    print_number(credential_checks);
    message(" credential_faults=3 file_checks="); print_number(file_checks);
    message(" concurrent_callers=8 inherited_owner_isolation=1 final_release=1 applications=0\n");
    return 0;
}
