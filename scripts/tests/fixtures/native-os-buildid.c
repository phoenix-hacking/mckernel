/* SPDX-License-Identifier: GPL-2.0 */
/* Exact existing build-ID UAPI, both pointer widths, isolated guest only. */
#define NATIVE_OS_RESOURCE_MAIN native_os_resource_reference_main
#include "native-os-resource-assignment.c"
#include "native-buildid-abi.h"

_Static_assert(IHK_OS_GET_BUILDID == 0x112a37, "Original OS ioctl number");
static const char expected_id[] = BUILDID;

static void check_id(int fd)
{
    unsigned char guarded[sizeof(expected_id) + 16];
    for (unsigned i = 0; i < sizeof(guarded); i++) guarded[i] = 0xa5;
    require(call(SYS_IOCTL, fd, IHK_OS_GET_BUILDID, (long)&guarded[8]) == 0);
    for (unsigned i = 0; i < 8; i++) {
        require(guarded[i] == 0xa5);
        require(guarded[8 + sizeof(expected_id) + i] == 0xa5);
    }
    for (unsigned i = 0; i < sizeof(expected_id); i++)
        require(guarded[8 + i] == (unsigned char)expected_id[i]);
    require(expected_id[sizeof(expected_id) - 1] == 0);
}

static void copy_faults(int fd)
{
    require(call(SYS_IOCTL, fd, IHK_OS_GET_BUILDID, 0) == -EFAULT);
    require(call(SYS_IOCTL, fd, IHK_OS_GET_BUILDID, 1) == -EFAULT);
    require(call(SYS_IOCTL, fd, IHK_OS_GET_BUILDID, -1) == -EFAULT);
    for (unsigned i = 0; i < sizeof(copy_boundary); i++) copy_boundary[i] = 0xa5;
    require(call(SYS_MPROTECT, (long)&copy_boundary[4096], 4096, 0) == 0);
    require(call(SYS_IOCTL, fd, IHK_OS_GET_BUILDID, (long)&copy_boundary[4092]) == -EFAULT);
    for (unsigned i = 0; i < 4092; i++) require(copy_boundary[i] == 0xa5);
    unsigned start = 4096 - sizeof(expected_id);
    require(call(SYS_IOCTL, fd, IHK_OS_GET_BUILDID, (long)&copy_boundary[start]) == 0);
    for (unsigned i = 0; i < sizeof(expected_id); i++)
        require(copy_boundary[start + i] == (unsigned char)expected_id[i]);
    require(call(SYS_MPROTECT, (long)&copy_boundary[4096], 4096, 1) == 0);
    require(call(SYS_IOCTL, fd, IHK_OS_GET_BUILDID, (long)&copy_boundary[4096]) == -EFAULT);
    for (unsigned i = 4096; i < sizeof(copy_boundary); i++) require(copy_boundary[i] == 0xa5);
    require(call(SYS_MPROTECT, (long)&copy_boundary[4096], 4096, 3) == 0);
}

int main(void)
{
    int control = open_control();
    int running = open_os(0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 1);
    int unbooted = open_os(1);
    require(call(SYS_IOCTL, running, 0x112a03, 0) == 4);
    require(call(SYS_IOCTL, unbooted, 0x112a03, 0) == 0);
    check_id(running); copy_faults(running);
    check_id(unbooted); copy_faults(unbooted);
    require(destroy_os(control, 1) == -EBUSY);
    close_fd(unbooted);
    require(destroy_os(control, 1) == 0);
    close_fd(running); close_fd(control);
    message("NATIVE_OS_BUILDID " ARCH_LABEL " PASS states=2 guarded=4 faults=10 mcctrl_absent=1\n");
    return 0;
}
