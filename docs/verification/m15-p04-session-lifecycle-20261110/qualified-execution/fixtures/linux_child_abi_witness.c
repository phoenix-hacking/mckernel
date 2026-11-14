/* NONSHIPPED ABI witness only. It calls no process/control/signal operation. */
#define _GNU_SOURCE
#include <sys/types.h>
#include <linux/wait.h>
/* Preserve actual UAPI values before glibc's same-name macro definitions. */
enum { KERNEL_P_ALL = P_ALL, KERNEL_P_PIDFD = P_PIDFD,
       KERNEL_WNOHANG = WNOHANG, KERNEL_WEXITED = WEXITED,
       KERNEL_WNOWAIT = WNOWAIT };
#undef P_ALL
#undef P_PID
#undef P_PGID
#undef P_PIDFD
#undef WNOHANG
#undef WUNTRACED
#undef WSTOPPED
#undef WEXITED
#undef WCONTINUED
#undef WNOWAIT
#undef __WNOTHREAD
#undef __WALL
#undef __WCLONE
#include <sys/wait.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <signal.h>
#include <poll.h>
#include <errno.h>
#include <stdio.h>
_Static_assert(sizeof(void*) == 8 && sizeof(long) == 8, "Linux x86_64 LP64");
_Static_assert(sizeof(pid_t) == 4 && sizeof(id_t) == 4, "pid/id width");
_Static_assert(_Generic((pid_t)0, int:1, default:0), "pid_t signed int");
_Static_assert(_Generic((id_t)0, unsigned int:1, default:0), "id_t unsigned int");
_Static_assert(_Generic((idtype_t)0, unsigned int:1, default:0), "idtype_t unsigned enum ABI");
_Static_assert(sizeof(siginfo_t) == 128 && _Alignof(siginfo_t) == 8, "opaque waitid output storage");
_Static_assert(_Generic(&waitid, int(*)(idtype_t,id_t,siginfo_t*,int):1, default:0), "waitid prototype");
_Static_assert(_Generic(&waitpid, pid_t(*)(pid_t,int*,int):1, default:0), "waitpid prototype");
_Static_assert(_Generic(&prctl, int(*)(int,...):1, default:0), "prctl prototype");
_Static_assert(_Generic(&syscall, long int(*)(long int,...):1, default:0), "syscall prototype");
_Static_assert(__NR_pidfd_open == 434 && __NR_pidfd_send_signal == 424, "x86_64 syscall numbers");
_Static_assert(PR_SET_CHILD_SUBREAPER == 36 && PR_GET_CHILD_SUBREAPER == 37, "subreaper options");
_Static_assert(P_ALL == 0 && (int)KERNEL_P_ALL == (int)P_ALL && KERNEL_P_PIDFD == 3, "wait selectors");
_Static_assert(WNOHANG == 1 && WEXITED == 4 && WNOWAIT == 0x01000000 && KERNEL_WNOHANG == WNOHANG && KERNEL_WEXITED == WEXITED && KERNEL_WNOWAIT == WNOWAIT, "nonreaping wait flags");
_Static_assert(SIGKILL == 9 && ESRCH == 3 && ECHILD == 10, "signal/errno bindings");
_Static_assert(POLLIN == 0x001 && POLLERR == 0x008 && POLLNVAL == 0x020, "pidfd poll events");
int main(void) {
    puts("{\"scope\":\"nonshipped actual Linux/glibc ABI only\",\"siginfo_bytes\":128,\"siginfo_alignment\":8,\"idtype_unsigned32\":true,\"pidfd_open\":434,\"pidfd_send_signal\":424,\"P_PIDFD\":3,\"process_control_calls\":0}");
    return 0;
}
