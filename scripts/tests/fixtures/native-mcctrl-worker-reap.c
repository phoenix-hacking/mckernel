/* SPDX-License-Identifier: GPL-2.0 */
/* Included by the real prepared-image verifier with its raw x86_64 syscall ABI. */
static unsigned char reaper_stack[16384] __attribute__((aligned(16)));
static volatile int reaper_tid, reaper_entered, reaper_untouched;
static volatile long reaper_result;
static int reaper_fd;
static int reaper_log_fd;

static void reaper_require(int value, int line)
{
    if (!value) { message("NATIVE_WORKER_REAP FAIL line="); print_number(line); message("\n"); fail(line); }
}
#define REAP_CHECK(value) reaper_require(!!(value), __LINE__)

static void reaper_signal(int signal) { (void)signal; }

__attribute__((noreturn, noinline, used)) static void reaper_thread(void)
{
    struct syscall_wait_desc wait;
    unsigned char *bytes = (unsigned char *)&wait;
    for (unsigned i = 0; i < sizeof(wait); ++i) bytes[i] = 0x6d;
    __atomic_store_n(&reaper_entered, 1, __ATOMIC_RELEASE);
    reaper_result = call(SYS_IOCTL, reaper_fd, MCEXEC_UP_WAIT_SYSCALL, (long)&wait);
    unsigned index;
    for (index = 0; index < sizeof(wait) && bytes[index] == 0x6d; ++index) {}
    reaper_untouched = index == sizeof(wait);
    call(60, 0, 0, 0); /* Exit only this Linux thread. */
    __builtin_unreachable();
}

static long reaper_clone(void)
{
    long result;
    register long fourth __asm__("r10") = (long)&reaper_tid;
    register long fifth __asm__("r8") = 0;
    /* VM|FS|FILES|SIGHAND|THREAD|SYSVSEM|PARENT_SETTID|CHILD_CLEARTID.
     * The child switches to its own aligned stack and never returns to C here.
     * It uses no libc/TLS and the parent waits for clear_child_tid before reuse. */
    __asm__ volatile("syscall\n\ttest %%rax, %%rax\n\tjnz 1f\n\t"
                     "xor %%ebp, %%ebp\n\tmovabs $reaper_thread, %%r11\n\tcall *%%r11\n\tud2\n1:"
                     : "=a"(result)
                     : "0"(56L), "D"(0x350f00L), "S"((long)(reaper_stack + sizeof(reaper_stack))),
                       "d"((long)&reaper_tid), "r"(fourth), "r"(fifth)
                     : "rcx", "r11", "cc", "memory");
    return result;
}

static void reaper_sleep(long nanoseconds)
{
    const long duration[2] = {0, nanoseconds};
    REAP_CHECK(call(35, (long)duration, 0, 0) == 0);
}

static void reaper_marker(const char *prefix, long pid, long tid)
{
    char line[128], digits[20];
    unsigned length = 3;
    line[0] = '<'; line[1] = '6'; line[2] = '>';
    while (*prefix) { REAP_CHECK(length < 64); line[length++] = *prefix++; }
    for (unsigned part = 0; part != 2; ++part) {
        const char *label = part ? " tid=" : " pid=";
        while (*label) line[length++] = *label++;
        unsigned long value = part ? (unsigned long)tid : (unsigned long)pid;
        unsigned count = 0;
        do { digits[count++] = '0' + value % 10; value /= 10; } while (value);
        while (count) line[length++] = digits[--count];
    }
    line[length++] = '\n';
    REAP_CHECK(length <= sizeof(line));
    REAP_CHECK(call(SYS_WRITE, reaper_log_fd, (long)line, length) == (long)length);
}

static void worker_reaper_probe(int fd)
{
    reaper_log_fd = call(SYS_OPEN, (long)"/dev/kmsg", 1, 0);
    REAP_CHECK(reaper_log_fd >= 0);
    struct native_signal_action action = { reaper_signal, 0x04000000UL, syscall_alarm_restorer, 0 }, old;
    REAP_CHECK(syscall_four(13, 10, (long)&action, (long)&old, 8) == 0);
    reaper_fd = fd;
    long pid = call(39, 0, 0, 0);
    for (unsigned iteration = 0; iteration != 72; ++iteration) {
        reaper_tid = reaper_entered = reaper_untouched = 0;
        reaper_result = 0x7fffffff;
        long tid = reaper_clone();
        REAP_CHECK(tid > 0);
        reaper_marker("NATIVE_WORKER_REAP_BEGIN", pid, tid);
        unsigned waited = 0;
        while (__atomic_load_n(&reaper_tid, __ATOMIC_ACQUIRE) != 0 && waited++ < 500) {
            if (__atomic_load_n(&reaper_entered, __ATOMIC_ACQUIRE)) {
                long sent = call(234, pid, tid, 10); /* tgkill to this exact worker. */
                REAP_CHECK(sent == 0 || sent == -3);
            }
            reaper_sleep(10000000);
        }
        REAP_CHECK(__atomic_load_n(&reaper_tid, __ATOMIC_ACQUIRE) == 0);
        REAP_CHECK(reaper_result == -4 && reaper_untouched);
        reaper_marker("NATIVE_WORKER_REAP_DEPARTED", pid, tid);
        /* No application ioctl occurs in this window. The external verifier
         * requires this worker's actual retirement log before QUIET_DONE. */
        reaper_sleep(200000000);
        reaper_marker("NATIVE_WORKER_REAP_QUIET_DONE", pid, tid);
    }
    REAP_CHECK(syscall_four(13, 10, (long)&old, 0, 8) == 0);
    static const char passed[] = "<6>NATIVE_WORKER_REAP PASS workers=72 quiet_windows=72 waits_interrupted=72 untouched_bytes=6336 applications=0\n";
    REAP_CHECK(call(SYS_WRITE, reaper_log_fd, (long)passed, sizeof(passed) - 1) == (long)sizeof(passed) - 1);
    REAP_CHECK(call(SYS_CLOSE, reaper_log_fd, 0, 0) == 0);
}
#undef REAP_CHECK
