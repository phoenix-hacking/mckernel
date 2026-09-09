// SPDX-License-Identifier: GPL-2.0-only
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <ucontext.h>
#include <unistd.h>

_Static_assert(offsetof(ucontext_t, uc_stack) == 16, "x86_64 uc_stack");
_Static_assert(offsetof(ucontext_t, uc_mcontext.gregs) == 40, "x86_64 gregs");
_Static_assert(offsetof(ucontext_t, uc_mcontext.fpregs) == 224, "x86_64 fpregs");
_Static_assert(offsetof(ucontext_t, uc_sigmask) == 296, "x86_64 uc_sigmask");
_Static_assert(sizeof(sigset_t) == 128, "libc signal-mask reservation");

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "NATIVE_SIGNAL_ABI FAIL line=%d errno=%d\n", __LINE__, errno); \
    exit(1); \
} } while (0)
#define HANDLER_CHECK(test) do { if (!(test) && handler_error == 0) \
    handler_error = __LINE__; } while (0)

static volatile sig_atomic_t handler_error, received, second_received, sequence;
static volatile sig_atomic_t first_exit_sequence, second_sequence;
static int test_mode;
static uintptr_t alternate_begin, alternate_end;
static uint64_t fp_pattern[2] = {0x0123456789abcdefULL, 0xfedcba9876543210ULL};
static uint64_t fp_clobber[2] = {0x1234123412341234ULL, 0x5678567856785678ULL};
static unsigned short fp_control = 0x027f, handler_control = 0x037f;
static unsigned fp_mxcsr = 0x3f80, handler_mxcsr = 0x1f80;

static void second_handler(int number)
{
    HANDLER_CHECK(number == SIGUSR2);
    ++second_received;
    second_sequence = ++sequence;
}

static void first_handler(int number, siginfo_t *info, void *opaque)
{
    unsigned char stack_byte;
    ucontext_t *context = opaque;
    HANDLER_CHECK(number == SIGUSR1 && info != NULL && info->si_signo == SIGUSR1);
    HANDLER_CHECK(context != NULL);
    HANDLER_CHECK((uintptr_t)&stack_byte >= alternate_begin &&
                  (uintptr_t)&stack_byte < alternate_end);
    ++received;
    if (test_mode == 0) {
        sigset_t current, pending;
        ++sequence;
        HANDLER_CHECK(sigismember(&context->uc_sigmask, SIGALRM) == 1);
        HANDLER_CHECK(sigismember(&context->uc_sigmask, SIGUSR1) == 0);
        HANDLER_CHECK(sigismember(&context->uc_sigmask, SIGUSR2) == 0);
        HANDLER_CHECK(sigprocmask(SIG_SETMASK, NULL, &current) == 0);
        HANDLER_CHECK(sigismember(&current, SIGALRM) == 1);
        HANDLER_CHECK(sigismember(&current, SIGUSR1) == 1);
        HANDLER_CHECK(sigismember(&current, SIGUSR2) == 1);
        HANDLER_CHECK(raise(SIGUSR2) == 0);
        HANDLER_CHECK(second_received == 0);
        HANDLER_CHECK(sigpending(&pending) == 0);
        HANDLER_CHECK(sigismember(&pending, SIGUSR2) == 1);
        HANDLER_CHECK(sigaddset(&context->uc_sigmask, SIGTERM) == 0);
        context->uc_mcontext.gregs[REG_RAX] = 12345;
        first_exit_sequence = ++sequence;
    } else {
        HANDLER_CHECK(context->uc_mcontext.fpregs != NULL);
        HANDLER_CHECK(context->uc_mcontext.fpregs->cwd == fp_control);
        HANDLER_CHECK(context->uc_mcontext.fpregs->mxcsr == fp_mxcsr);
        if (test_mode == 2) {
            const unsigned char *instruction =
                (const unsigned char *)context->uc_mcontext.gregs[REG_RIP];
            HANDLER_CHECK(context->uc_mcontext.gregs[REG_RAX] == SYS_read);
            HANDLER_CHECK(instruction[0] == 0x0f && instruction[1] == 0x05);
            HANDLER_CHECK(write(STDERR_FILENO, "NATIVE_SIGNAL_RESTART_HANDLED\n", 30) == 30);
        }
        __asm__ volatile("fldcw %0\n\tldmxcsr %1\n\tmovdqu %2, %%xmm0"
                         : : "m"(handler_control), "m"(handler_mxcsr), "m"(fp_clobber)
                         : "xmm0", "memory");
    }
}

static long roundtrip(long number, long first, long second, long third)
{
    long result = number;
    unsigned short original_control, after_control;
    unsigned original_mxcsr, after_mxcsr;
    uint64_t after_pattern[2];
    __asm__ volatile("fnstcw %0\n\tstmxcsr %1"
                     : "=m"(original_control), "=m"(original_mxcsr));
    __asm__ volatile("fldcw %4\n\tldmxcsr %5\n\tmovdqu %6, %%xmm0\n\t"
                     "syscall\n\tmovdqu %%xmm0, %1\n\tfnstcw %2\n\tstmxcsr %3"
                     : "+a"(result), "=m"(after_pattern), "=m"(after_control),
                       "=m"(after_mxcsr)
                     : "m"(fp_control), "m"(fp_mxcsr), "m"(fp_pattern),
                       "D"(first), "S"(second), "d"(third)
                     : "rcx", "r11", "xmm0", "memory");
    __asm__ volatile("fldcw %0\n\tldmxcsr %1"
                     : : "m"(original_control), "m"(original_mxcsr) : "memory");
    CHECK(after_control == fp_control && after_mxcsr == fp_mxcsr);
    CHECK(after_pattern[0] == fp_pattern[0] && after_pattern[1] == fp_pattern[1]);
    return result;
}

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    if (strcmp(argv[1], "mask-context") == 0) test_mode = 0;
    else if (strcmp(argv[1], "fp-return") == 0) test_mode = 1;
    else if (strcmp(argv[1], "fp-restart") == 0) test_mode = 2;
    else CHECK(0);
    void *alternate = malloc(65536);
    CHECK(alternate != NULL);
    alternate_begin = (uintptr_t)alternate;
    alternate_end = alternate_begin + 65536;
    stack_t stack = {.ss_sp = alternate, .ss_size = 65536}, old_stack;
    struct sigaction action = {.sa_sigaction = first_handler,
        .sa_flags = SA_SIGINFO | SA_ONSTACK | SA_RESTART}, old_first;
    struct sigaction second = {.sa_handler = second_handler}, old_second;
    sigset_t old_mask, blocked, current;
    CHECK(sigemptyset(&action.sa_mask) == 0);
    CHECK(sigaddset(&action.sa_mask, SIGUSR2) == 0);
    CHECK(sigemptyset(&second.sa_mask) == 0);
    CHECK(sigemptyset(&blocked) == 0 && sigaddset(&blocked, SIGALRM) == 0);
    CHECK(sigprocmask(SIG_BLOCK, &blocked, &old_mask) == 0);
    CHECK(sigaltstack(&stack, &old_stack) == 0);
    CHECK(sigaction(SIGUSR1, &action, &old_first) == 0);
    CHECK(sigaction(SIGUSR2, &second, &old_second) == 0);
    if (test_mode == 2) {
        unsigned char byte = 0;
        CHECK(write(STDOUT_FILENO, "NATIVE_SIGNAL_RESTART_READY\n", 28) == 28);
        CHECK(roundtrip(SYS_read, STDIN_FILENO, (long)&byte, 1) == 1);
        CHECK(byte == 0xa5);
    } else {
        long pid = getpid(), tid = syscall(SYS_gettid);
        long result = roundtrip(SYS_tgkill, pid, tid, SIGUSR1);
        CHECK(result == (test_mode == 0 ? 12345 : 0));
    }
    CHECK(received == 1 && handler_error == 0);
    if (test_mode == 0) {
        CHECK(second_received == 1 && first_exit_sequence == 2 && second_sequence == 3);
        CHECK(sigprocmask(SIG_SETMASK, NULL, &current) == 0);
        CHECK(sigismember(&current, SIGALRM) == 1);
        CHECK(sigismember(&current, SIGTERM) == 1);
        CHECK(sigismember(&current, SIGUSR1) == 0);
        CHECK(sigismember(&current, SIGUSR2) == 0);
    }
    CHECK(sigaction(SIGUSR1, &old_first, NULL) == 0);
    CHECK(sigaction(SIGUSR2, &old_second, NULL) == 0);
    CHECK(sigaltstack(&old_stack, NULL) == 0);
    CHECK(sigprocmask(SIG_SETMASK, &old_mask, NULL) == 0);
    free(alternate);
    CHECK(printf("NATIVE_SIGNAL_ABI PASS %s\n", argv[1]) > 0);
    CHECK(fflush(stdout) == 0);
    return 37;
}
