#define _GNU_SOURCE
#include <errno.h>
#include <linux/futex.h>
#include <pthread.h>
#include <signal.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

struct control { _Atomic int gate, ready; int pid, tid; };
_Static_assert(offsetof(struct control, ready) == 4, "assembly ready offset");
_Static_assert(offsetof(struct control, pid) == 8, "assembly pid offset");
_Static_assert(offsetof(struct control, tid) == 12, "assembly tid offset");
_Static_assert(sizeof(_Atomic int) == 4, "assembly futex width");
extern int native_vector_probe(int kind, struct control *control);
extern void native_vector_handler(int signal);
volatile sig_atomic_t native_vector_signal_seen;
_Alignas(4096) static unsigned char worker_stack[262144];
static struct control handoff;

static void timeout_handler(int signo) {
    (void)signo;
    static const char message[] = "VECTOR_TIMEOUT\n";
    ssize_t written = write(STDERR_FILENO, message, sizeof(message) - 1);
    (void)written;
    _exit(124);
}
static int fail(const char *stage, int code) {
    printf("VECTOR_FAIL stage=%s code=%d\n", stage, code);
    return 1;
}
/* Capture controls immediately outside the assembly boundary; no XMM values
 * are assumed live across this ordinary SysV call. Status bits are volatile. */
static int checked_probe(int kind, struct control *control) {
    unsigned short before_cw, after_cw;
    unsigned int before_mxcsr, after_mxcsr;
    __asm__ volatile("fnstcw %0; stmxcsr %1" : "=m"(before_cw), "=m"(before_mxcsr) : : "memory");
    int rc = native_vector_probe(kind, control);
    __asm__ volatile("fnstcw %0; stmxcsr %1" : "=m"(after_cw), "=m"(after_mxcsr) : : "memory");
    if (before_cw != after_cw) return 110;
    if ((before_mxcsr & 0xffc0u) != (after_mxcsr & 0xffc0u)) return 111;
    return rc;
}
static void *worker(void *unused) {
    (void)unused;
    handoff.pid = (int)getpid();
    handoff.tid = (int)syscall(SYS_gettid);
    return (void *)(intptr_t)checked_probe(1, &handoff);
}
static void pause_poll(void) {
    const struct timespec pause = {0, 1000000};
    (void)nanosleep(&pause, NULL);
}
int main(void) {
    struct sigaction action = {0};
    action.sa_handler = timeout_handler;
    if (sigemptyset(&action.sa_mask) || sigaction(SIGALRM, &action, NULL)) return fail("watchdog", errno);
    alarm(8);
    struct control self = {0};
    self.pid = (int)getpid(); self.tid = (int)syscall(SYS_gettid);
    int rc = checked_probe(0, &self);
    if (rc) return fail("syscall", rc);
    puts("VECTOR_SYSCALL_PASS");

    pthread_attr_t attr;
    pthread_t thread;
    if ((rc = pthread_attr_init(&attr))) return fail("attr-init", rc);
    if ((rc = pthread_attr_setstack(&attr, worker_stack, sizeof(worker_stack)))) return fail("attr-stack", rc);
    if ((rc = pthread_create(&thread, &attr, worker, NULL))) return fail("create", rc);
    if ((rc = pthread_attr_destroy(&attr))) return fail("attr-destroy", rc);
    int ready = 0;
    for (int i = 0; i < 2000; ++i) {
        if (atomic_load_explicit(&handoff.ready, memory_order_acquire)) { ready = 1; break; }
        pause_poll();
    }
    if (!ready) return fail("handoff-ready", 1);
    int woke = 0;
    for (int i = 0; i < 2000; ++i) {
        long n = syscall(SYS_futex, &handoff.gate, FUTEX_WAKE_PRIVATE, 1, NULL, NULL, 0);
        if (n == 1) { woke = 1; break; }
        if (n != 0) return fail("futex-wake", (int)n);
        pause_poll();
    }
    if (!woke) return fail("futex-wake", 2);
    void *result;
    if ((rc = pthread_join(thread, &result))) return fail("join", rc);
    if ((rc = (int)(intptr_t)result)) return fail("futex-state", rc);
    puts("VECTOR_FUTEX_PASS");

    action.sa_handler = native_vector_handler;
    if (sigemptyset(&action.sa_mask) || sigaction(SIGUSR1, &action, NULL)) return fail("signal-install", errno);
    sigset_t mask;
    if (sigemptyset(&mask) || sigaddset(&mask, SIGUSR1)) return fail("signal-mask", errno);
    if ((rc = pthread_sigmask(SIG_UNBLOCK, &mask, NULL))) return fail("signal-unblock", rc);
    rc = checked_probe(2, &self);
    if (rc) return fail("signal-state", rc);
    if (native_vector_signal_seen != 1) return fail("signal-delivery", 1);
    puts("VECTOR_SIGNAL_PASS");
    alarm(0);
    puts("VECTOR_PROFILE_PASS");
    return 0;
}
