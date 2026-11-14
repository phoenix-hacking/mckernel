/* Functional McKernel OS/apps + Rust/assembly only; no security testing.
 * One raw legacy clone, private COW mapping, own child exit/wait only.
 * No SETTLS/TID flags or pointers, exec, handler, kill, frame or xstate work.
 * SIGCHLD is only the ordinary clone ABI exit notification used for waitpid.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#if !defined(__x86_64__) || __SIZEOF_POINTER__ != 8
#error selected Linux x86_64 LP64 ABI required
#endif
_Static_assert(sizeof(long) == 8 && sizeof(size_t) == 8 && sizeof(pid_t) == 4,
               "selected clone syscall ABI widths");
_Static_assert(SYS_clone == 56 && SYS_exit == 60, "selected x86_64 syscall numbers");
int main(void) {
    const size_t bytes = 4096;
    volatile unsigned char *p = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
                                    MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if ((void *)p == MAP_FAILED) { perror("clone mapping"); return 1; }
    p[0] = 0x31; p[bytes - 1] = 0x47;
    /* x86_64 clone(flags,stack,parent_tid,child_tid,tls): all optional values0. */
    long child = syscall(SYS_clone, (unsigned long)SIGCHLD, 0UL, 0UL, 0UL, 0UL);
    if (child == 0) {
        int code = (p[0] == 0x31 && p[bytes - 1] == 0x47) ? 73 : 74;
        p[0] = 0x72; p[bytes - 1] = 0x91;
        (void)syscall(SYS_exit, (long)code);
        __builtin_unreachable();
    }
    if (child < 0) {
        int saved = errno;
        int unmap = munmap((void *)p, bytes);
        fprintf(stderr, "clone failed errno=%d cleanup_unmap=%d\n", saved, unmap);
        return 1;
    }
    if (child > INT_MAX) {
        int unmap = munmap((void *)p, bytes);
        fprintf(stderr, "clone returned outside pid_t ABI; child wait unproved, unmap=%d\n", unmap);
        return 1;
    }
    int status = 0;
    pid_t joined;
    do { joined = waitpid((pid_t)child, &status, 0); }
    while (joined == -1 && errno == EINTR);
    int wait_errno = errno;
    int cow = p[0] == 0x31 && p[bytes - 1] == 0x47;
    int unmap = munmap((void *)p, bytes);
    if (joined != (pid_t)child || !WIFEXITED(status) || WEXITSTATUS(status) != 73 || !cow || unmap) {
        fprintf(stderr, "clone result joined=%d status=%d cow=%d unmap=%d wait_errno=%d\n",
                joined == (pid_t)child, status, cow, unmap, wait_errno);
        return 1;
    }
    puts("clone_basic child_exit=73 parent_cow=1 child_reaped=1 mapping_unmapped=1");
    return 0;
}
