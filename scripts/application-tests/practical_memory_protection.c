/* Frozen success oracle, independent of observed Linux output:
 * faults=1 accerr=1 address=1 restored_write=1 mask_restored=1\n
 * stderr empty, status 0. One actual protected write, no fork or emulation.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <setjmp.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>

_Static_assert(ATOMIC_POINTER_LOCK_FREE == 2, "signal target pointer must be lock-free");
static _Atomic(void *) fault_target;
static sigjmp_buf recovery;
static volatile sig_atomic_t armed;
static volatile sig_atomic_t faults;
static volatile sig_atomic_t accerr_ok;
static volatile sig_atomic_t address_ok;

static void fault_handler(int signal_number, siginfo_t *info, void *context) {
    (void)context;
    /* Only async-signal-safe operations: lock-free atomic load, sig_atomic_t
     * flags, siglongjmp, or whole-process _Exit. Never swallow another fault. */
    if (!armed || faults != 0 || signal_number != SIGSEGV || info == NULL ||
        info->si_code != SEGV_ACCERR ||
        info->si_addr != atomic_load_explicit(&fault_target, memory_order_relaxed))
        _Exit(120);
    armed = 0;
    faults = 1;
    accerr_ok = 1;
    address_ok = 1;
    siglongjmp(recovery, 1);
}
static void fatal(const char *operation, int error) {
    (void)fprintf(stderr, "fatal=%s error=%d\n", operation, error);
    _Exit(EXIT_FAILURE);
}
static void check(const char *operation, int result) {
    if (result != 0) fatal(operation, errno);
}
static void require_same_mask(const sigset_t *left, const sigset_t *right) {
    /* Compare logical members, never uninitialized sigset_t padding. */
    for (int number = 1; number < NSIG; ++number) {
        int a = sigismember(left, number);
        int b = sigismember(right, number);
        if (a < 0 || b < 0) fatal("sigismember", errno);
        if (a != b) fatal("signal_mask_changed", EIO);
    }
}
int main(void) {
    long page_size = sysconf(_SC_PAGESIZE);
    if (page_size < 64) fatal("page_size", EINVAL);
    unsigned char *page = mmap(NULL, (size_t)page_size, PROT_READ | PROT_WRITE,
                               MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (page == MAP_FAILED) fatal("mmap", errno);
    volatile unsigned char *target = page + 37;
    *target = 0x31;
    if (*target != 0x31) fatal("initial_read_write", EIO);
    atomic_store_explicit(&fault_target, (void *)(page + 37), memory_order_relaxed);

    sigset_t original_mask;
    check("get_original_mask", sigprocmask(SIG_SETMASK, NULL, &original_mask));
    sigset_t active_mask = original_mask;
    check("unblock_sigsegv_set", sigdelset(&active_mask, SIGSEGV));
    struct sigaction action = {0};
    struct sigaction original_action;
    action.sa_sigaction = fault_handler;
    action.sa_flags = SA_SIGINFO;
    check("handler_empty_mask", sigemptyset(&action.sa_mask));
    check("install_handler", sigaction(SIGSEGV, &action, &original_action));
    check("set_active_mask", sigprocmask(SIG_SETMASK, &active_mask, NULL));
    check("protect_readonly", mprotect(page, (size_t)page_size, PROT_READ));
    if (*target != 0x31) fatal("readonly_read", EIO);

    /* Locals used after the jump were initialized before sigsetjmp and are
     * not modified between it and siglongjmp. Shared flags are volatile.
     * Keep sigsetjmp in its permitted controlling-expression context. */
    if (sigsetjmp(recovery, 1) == 0) {
        armed = 1;
        *target = 0x52;
        armed = 0;
        fatal("protected_write_did_not_fault", EIO);
    }
    if (armed || faults != 1 || !accerr_ok || !address_ok)
        fatal("fault_record", EIO);
    sigset_t after_jump;
    check("get_jump_mask", sigprocmask(SIG_SETMASK, NULL, &after_jump));
    require_same_mask(&after_jump, &active_mask);
    if (sigismember(&after_jump, SIGSEGV) != 0) fatal("jump_left_sigsegv_blocked", EIO);
    if (*target != 0x31) fatal("failed_write_changed_byte", EIO);

    check("restore_read_write", mprotect(page, (size_t)page_size, PROT_READ | PROT_WRITE));
    *target = 0x73;
    if (*target != 0x73) fatal("restored_write_read", EIO);
    check("restore_handler", sigaction(SIGSEGV, &original_action, NULL));
    check("restore_original_mask", sigprocmask(SIG_SETMASK, &original_mask, NULL));
    sigset_t restored_mask;
    check("get_restored_mask", sigprocmask(SIG_SETMASK, NULL, &restored_mask));
    require_same_mask(&restored_mask, &original_mask);
    check("munmap", munmap(page, (size_t)page_size));
    atomic_store_explicit(&fault_target, NULL, memory_order_relaxed);
    if (printf("faults=1 accerr=1 address=1 restored_write=1 mask_restored=1\n") < 0 || fflush(stdout) != 0)
        fatal("stdout", errno);
    return EXIT_SUCCESS;
}
