#include <assert.h>
#include <stdint.h>
#include <stdio.h>
struct thread;
struct siginfo;
static void *expected_thread, *expected_info;
static int expected_pid, expected_tid, expected_sig, expected_continue, calls;
static unsigned long expected_result;
unsigned long do_kill(struct thread *thread, int pid, int tid, int sig,
                      struct siginfo *info, int ptracecont) {
    assert((void *)thread == expected_thread && (void *)info == expected_info);
    assert(pid == expected_pid && tid == expected_tid && sig == expected_sig);
    assert(ptracecont == expected_continue);
    ++calls;
    return expected_result;
}
extern long ptrace_detach_do_kill_bridge(void *, int, int, int, const void *, int);
static void check(void *thread, int pid, int tid, int sig, const void *info,
                  int cont, unsigned long result, long expected) {
    expected_thread = thread; expected_info = (void *)info;
    expected_pid = pid; expected_tid = tid; expected_sig = sig;
    expected_continue = cont; expected_result = result; calls = 0;
    assert(ptrace_detach_do_kill_bridge(thread, pid, tid, sig, info, cont) == expected);
    assert(calls == 1);
}
int main(void) {
    int t = 0, info = 0;
    _Static_assert(sizeof(long) == 8 && sizeof(int) == 4, "x86-64 ABI");
    check(&t, 123, -1, 9, &info, 0, 0UL, 0L);
    check(&t, -2147483647-1, 2147483647, 19, 0, -1, ~0UL, -1L);
    check(0, -12, 0, 0, &info, 1, 0x8000000000000000UL, (-9223372036854775807L - 1));
    check(&t, 0, -5, -6, &info, 2147483647, 0x7fffffffffffffffUL, 9223372036854775807L);
    puts("PASS 4 actual Rust bridge/adapter C-call cases; one provider call each");
    return 0;
}
