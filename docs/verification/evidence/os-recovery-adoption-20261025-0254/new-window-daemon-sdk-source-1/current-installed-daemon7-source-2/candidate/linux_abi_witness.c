/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Test-only full-header ABI witness. Never installed or linked into production.
 */
#define _GNU_SOURCE
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <getopt.h>
#include <signal.h>
#include <pthread.h>
#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <sys/ioctl.h>
#include <sys/signalfd.h>
#include <sys/stat.h>
#include <ihk/ihklib.h>
#include <ihk/ihklib_private.h>
#include <ihk/ihk_host_user.h>

#define CHECK_TYPE(symbol, type) \
    _Static_assert(__builtin_types_compatible_p(__typeof__(&(symbol)), type), #symbol " type")
#define FIELD(type, member, offset) \
    _Static_assert(offsetof(type, member) == (offset), #type "." #member)
#define SIZE(type, bytes, alignment) \
    _Static_assert(sizeof(type) == (bytes) && _Alignof(type) == (alignment), #type " layout")

SIZE(sigset_t, 128, 8);
SIZE(struct signalfd_siginfo, 128, 8);
FIELD(struct signalfd_siginfo, ssi_signo, 0);
SIZE(struct epoll_event, 12, 1);
FIELD(struct epoll_event, events, 0);
FIELD(struct epoll_event, data, 4);
SIZE(epoll_data_t, 8, 8);
SIZE(eventfd_t, 8, 8);
SIZE(struct option, 32, 8);
FIELD(struct option, name, 0);
FIELD(struct option, has_arg, 8);
FIELD(struct option, flag, 16);
FIELD(struct option, val, 24);
SIZE(struct ihk_device_get_kmsg_buf_desc, 16, 8);
FIELD(struct ihk_device_get_kmsg_buf_desc, os_index, 0);
FIELD(struct ihk_device_get_kmsg_buf_desc, handle, 8);
SIZE(struct ihk_device_read_kmsg_buf_desc, 24, 8);
FIELD(struct ihk_device_read_kmsg_buf_desc, handle, 0);
FIELD(struct ihk_device_read_kmsg_buf_desc, shift, 8);
FIELD(struct ihk_device_read_kmsg_buf_desc, buf, 16);
SIZE(struct ihk_os_ioctl_eventfd_desc, 8, 4);
FIELD(struct ihk_os_ioctl_eventfd_desc, fd, 0);
FIELD(struct ihk_os_ioctl_eventfd_desc, type, 4);
_Static_assert(sizeof(struct stat) <= 256 && _Alignof(struct stat) <= 8, "stat buffer");
_Static_assert(SIG_BLOCK == 0 && SIG_SETMASK == 2, "signal mask operations");
_Static_assert(SIGINT == 2 && SIGTERM == 15, "signal numbers");
_Static_assert(EPOLLIN == 1 && EPOLL_CTL_ADD == 1 && EPOLL_CTL_DEL == 2, "epoll constants");
_Static_assert(IHK_OS_EVENTFD_TYPE_STATUS == 2 && IHK_OS_EVENTFD_TYPE_KMSG == 101,
               "provider event types");
_Static_assert(IHK_DEVICE_GET_KMSG_BUF == 0x112908, "kmsg acquire");
_Static_assert(IHK_DEVICE_READ_KMSG_BUF == 0x112909, "kmsg read");
_Static_assert(IHK_DEVICE_RELEASE_KMSG_BUF == 0x11290a, "kmsg release");
_Static_assert(IHK_DEVICE_DETECT_HUNGUP == 0x11290f, "hungup request");

CHECK_TYPE(sigemptyset, int (*)(sigset_t *));
CHECK_TYPE(sigaddset, int (*)(sigset_t *, int));
CHECK_TYPE(pthread_sigmask, int (*)(int, const sigset_t *, sigset_t *));
CHECK_TYPE(signalfd, int (*)(int, const sigset_t *, int));
CHECK_TYPE(epoll_create, int (*)(int));
CHECK_TYPE(epoll_ctl, int (*)(int, int, int, struct epoll_event *));
CHECK_TYPE(epoll_wait, int (*)(int, struct epoll_event *, int, int));
CHECK_TYPE(eventfd, int (*)(unsigned int, int));
CHECK_TYPE(read, ssize_t (*)(int, void *, size_t));
CHECK_TYPE(write, ssize_t (*)(int, const void *, size_t));
CHECK_TYPE(close, int (*)(int));
CHECK_TYPE(open, int (*)(const char *, int, ...));
CHECK_TYPE(ioctl, int (*)(int, unsigned long, ...));
CHECK_TYPE(ihklib_device_open, int (*)(int));
CHECK_TYPE(ihk_os_get_eventfd, int (*)(int, int));

/* Metadata stays in the object: read with readelf, without executing the witness.
 * This daemon imports neither sigaction nor poll; neither is a gate here.
 * Rust's epoll_ctl pointer is const; libc's is mutable. Both carry the same ABI;
 * the pointer addresses a live stack Event and Linux reads it for ADD only.
 */
const unsigned long m15_daemon_linux_abi[] = {
    sizeof(sigset_t),
    sizeof(struct epoll_event), offsetof(struct epoll_event, data),
    sizeof(struct signalfd_siginfo), sizeof(struct stat),
    sizeof(struct ihk_device_get_kmsg_buf_desc), sizeof(struct ihk_device_read_kmsg_buf_desc)
};
