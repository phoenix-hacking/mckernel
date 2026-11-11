#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#include <immintrin.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>

enum { MAIN_MODE = 0x1f80, OUTER_MODE = 0x3f80, INNER_MODE = 0x5f80 };
static volatile sig_atomic_t depth, failed, expected_pid, expected_tid;
static volatile sig_atomic_t inner_csr, outer_before, outer_after, main_after, tid_ok;

static void inner(int signo)
{
    (void)signo;
    _mm_setcsr(INNER_MODE);
    long tid = syscall(SYS_gettid);
    inner_csr = (sig_atomic_t)_mm_getcsr();
    tid_ok = tid == (long)expected_tid;
    if (!tid_ok) failed = 1;
    depth = 2;
}

static void outer(int signo)
{
    (void)signo;
    _mm_setcsr(OUTER_MODE);
    outer_before = (sig_atomic_t)_mm_getcsr();
    depth = 1;
    if (syscall(SYS_tgkill, (long)expected_pid, (long)expected_tid, SIGUSR2) != 0) failed = 1;
    outer_after = (sig_atomic_t)_mm_getcsr();
    if (depth != 2) failed = 1;
}

int main(void)
{
    long pid = getpid(), tid = syscall(SYS_gettid);
    if (pid <= 0 || tid <= 0 || pid > INT_MAX || tid > INT_MAX) return EXIT_FAILURE;
    expected_pid = (sig_atomic_t)pid;
    expected_tid = (sig_atomic_t)tid;
    if (signal(SIGUSR1, outer) == SIG_ERR || signal(SIGUSR2, inner) == SIG_ERR) return EXIT_FAILURE;
    unsigned original = _mm_getcsr();
    _mm_setcsr(MAIN_MODE);
    if (syscall(SYS_tgkill, pid, tid, SIGUSR1) != 0) failed = 1;
    main_after = (sig_atomic_t)_mm_getcsr();
    _mm_setcsr(original);
    int outer_restored = outer_before == OUTER_MODE && outer_after == OUTER_MODE;
    int main_restored = main_after == MAIN_MODE;
    int exceptions_masked = ((unsigned)inner_csr & 0x1f80u) == 0x1f80u &&
                            ((unsigned)outer_after & 0x1f80u) == 0x1f80u &&
                            ((unsigned)main_after & 0x1f80u) == 0x1f80u;
    int valid = depth == 2 && !failed && tid_ok && inner_csr == INNER_MODE &&
                outer_restored && main_restored && exceptions_masked;
    printf("nested=%d inner_mxcsr=%08x outer_mxcsr=%08x main_mxcsr=%08x "
           "outer_restored=%d main_restored=%d exceptions_masked=%d tid_ok=%d valid=%d\n",
           (int)depth, (unsigned)inner_csr, (unsigned)outer_after, (unsigned)main_after,
           outer_restored, main_restored, exceptions_masked, (int)tid_ok, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
