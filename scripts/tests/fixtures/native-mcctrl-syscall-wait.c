/* SPDX-License-Identifier: GPL-2.0 */
/* Included by the existing image probe only for the native waiter run. */
static unsigned syscall_wait_checks;
static volatile unsigned syscall_alarm_count;

static void syscall_wait_require(int condition, int line)
{
    syscall_wait_checks++;
    if (!condition) {
        message("NATIVE_MCCTRL_SYSCALL_WAIT FAIL line=");
        print_number(line); message("\n"); fail(line);
    }
}
#define WAIT_CHECK(value) syscall_wait_require(!!(value), __LINE__)

struct native_signal_action {
    void (*handler)(int);
    unsigned long flags;
    void (*restorer)(void);
    unsigned long mask;
};
_Static_assert(sizeof(struct native_signal_action) == 32, "Linux x86_64 rt_sigaction");
_Static_assert(sizeof(struct syscall_wait_desc) == 88, "unchanged wait UAPI");
_Static_assert(sizeof(struct syscall_ret_desc) == 40, "unchanged return UAPI");

__attribute__((naked)) static void syscall_alarm_restorer(void)
{
    __asm__ volatile("mov $15, %rax\n\tsyscall\n\tud2");
}

static void syscall_alarm_handler(int signal)
{
    if (signal == 14) __atomic_fetch_add(&syscall_alarm_count, 1, __ATOMIC_RELAXED);
}

static long syscall_four(long number, long first, long second, long third, long last)
{
    long result;
    register long fourth __asm__("r10") = last;
    __asm__ volatile("syscall" : "=a"(result)
                     : "0"(number), "D"(first), "S"(second), "d"(third), "r"(fourth)
                     : "rcx", "r11", "memory");
    return result;
}

static long syscall_signal_action(const struct native_signal_action *action,
                                 struct native_signal_action *old)
{
    return syscall_four(13, 14, (long)action, (long)old, 8);
}

static void syscall_before_prepare(int fd)
{
    struct syscall_wait_desc wait = {0};
    struct syscall_ret_desc returned = {0};
    WAIT_CHECK(call(SYS_IOCTL, fd, MCEXEC_UP_WAIT_SYSCALL, (long)&wait) == -22);
    WAIT_CHECK(call(SYS_IOCTL, fd, MCEXEC_UP_RET_SYSCALL, (long)&returned) == -22);
}

static void syscall_waiter_probe(int fd)
{
    struct native_signal_action action = {
        syscall_alarm_handler, 0x04000000UL, syscall_alarm_restorer, 0
    }, old = {0};
    struct syscall_wait_desc wait;
    struct syscall_ret_desc returned = {0};
    WAIT_CHECK(call(SYS_IOCTL, fd, MCEXEC_UP_RET_SYSCALL, -8) == -14);
    WAIT_CHECK(call(SYS_IOCTL, fd, MCEXEC_UP_RET_SYSCALL, (long)&returned) == -22);
    WAIT_CHECK(syscall_signal_action(&action, &old) == 0);
    /* Periodic delivery also bounds the signal-before-WAIT race. SA_RESTART is
     * absent; each empty native wait must return the real Linux interruption. */
    const long timer[4] = {0, 20000, 0, 20000};
    WAIT_CHECK(call(38, 0, (long)timer, 0) == 0);
    for (unsigned iteration = 0; iteration < 128; iteration++) {
        unsigned char *bytes = (unsigned char *)&wait;
        for (unsigned i = 0; i < sizeof(wait); i++) bytes[i] = 0xa5;
        long result = call(SYS_IOCTL, fd, MCEXEC_UP_WAIT_SYSCALL, (long)&wait);
        if (result != -4) {
            message("NATIVE_SYSCALL_WAIT unexpected_negative="); print_number(result < 0);
            message(" magnitude="); print_number(result < 0 ? -result : result); message("\n");
        }
        WAIT_CHECK(result == -4);
        unsigned i;
        for (i = 0; i < sizeof(wait) && bytes[i] == 0xa5; i++) {}
        WAIT_CHECK(i == sizeof(wait));
        WAIT_CHECK(call(SYS_IOCTL, fd, MCEXEC_UP_RET_SYSCALL, (long)&returned) == -22);
    }
    /* Block and drain a last timer signal before restoring the old action. */
    const unsigned long alarm_mask = 1UL << 13;
    unsigned long old_mask = 0;
    WAIT_CHECK(syscall_four(14, 0, (long)&alarm_mask, (long)&old_mask, 8) == 0);
    const long disabled[4] = {0, 0, 0, 0};
    WAIT_CHECK(call(38, 0, (long)disabled, 0) == 0);
    const long no_wait[2] = {0, 0};
    long pending;
    do { pending = syscall_four(128, (long)&alarm_mask, 0, (long)no_wait, 8); } while (pending == 14);
    WAIT_CHECK(pending == -11);
    WAIT_CHECK(__atomic_load_n(&syscall_alarm_count, __ATOMIC_RELAXED) >= 128);
    WAIT_CHECK(syscall_signal_action(&old, 0) == 0);
    WAIT_CHECK(syscall_four(14, 2, (long)&old_mask, 0, 8) == 0);
    message("NATIVE_MCCTRL_SYSCALL_WAIT x86_64 PASS checks="); print_number(syscall_wait_checks);
    message(" interruptions=128 untouched_bytes=11264 idle_returns_rejected=130 copy_faults=1 preprepare_rejections=2 applications=0\n");
}
#undef WAIT_CHECK
