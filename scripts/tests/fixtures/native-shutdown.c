/* SPDX-License-Identifier: GPL-2.0 */
/*
 * Bounded x86_64 initramfs shutdown fixture.  This is deliberately a
 * freestanding source probe: it does not load or unload a provider module.
 * The reservation and syscall primitives are the already-reviewed native
 * CPU/memory fixtures.
 */
#define NATIVE_MEMORY_MAIN native_shutdown_memory_reference_main
#include "native-memory-reservation.c"

#define IHK_OS_SHUTDOWN       0x112a02
#define OS_DESTROY            0x112901

__attribute__((noreturn)) static void shutdown_fail(int line)
{
    message("NATIVE_SHUTDOWN " ARCH_LABEL " FAIL line=");
    char digits[12];
    int n = 0;
    do { digits[n++] = '0' + line % 10; line /= 10; } while (line);
    while (n) call(SYS_WRITE, 1, (long)&digits[--n], 1);
    message("\n");
    call(SYS_EXIT, 1, 0, 0);
    __builtin_unreachable();
}
#undef require
#define require(test) do { if (!(test)) shutdown_fail(__LINE__); } while (0)

static void query_returned_cpu_and_release(int control)
{
    int cpus[4] = {-1, -1, -1, -1};
    long count = call(SYS_IOCTL, control, COUNT, 0);
    require(count == 1);
    require(request(control, QUERY, cpus, (int)count) == 0);
    require(cpus[0] == 1 && cpus[1] == -1);
    require(request(control, RELEASE, cpus, (int)count) == 0);
    require(call(SYS_IOCTL, control, COUNT, 0) == 0);
    require(request(control, QUERY, cpus, 0) == 0);
    require(cpus[0] == -1);
}

static void shutdown_os_zero(int control)
{
    /* control is the already-open /dev/mcd0 provider descriptor. */
    int os = call(SYS_OPEN, (long)"/dev/mcos0", 2, 0);
    require(os >= 0);
    require(call(SYS_IOCTL, os, IHK_OS_SHUTDOWN, 0) == 0);
    close_fd(os);
    require(call(SYS_IOCTL, control, OS_DESTROY, 0) == 0);
}

int main(void)
{
    int control = open_control();
    shutdown_os_zero(control);
    query_returned_cpu_and_release(control);
    /* query_memory snapshots every returned extent; release_memory issues one
     * exact batch and then performs the zero-reserve proof. */
    require(query_memory(control) > 0);
    release_memory(control);
    close_fd(control);
    /* PASS marker: NATIVE_SHUTDOWN x86_64 os0-shutdown-destroy-release-empty PASS */
    message("NATIVE_SHUTDOWN " ARCH_LABEL " os0-shutdown-destroy-release-empty PASS\n");
    return 0;
}
