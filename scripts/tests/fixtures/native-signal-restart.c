// SPDX-License-Identifier: GPL-2.0-only
// Exact selected C policy; ordinary pending-signal restart behavior only.
#include <asm/unistd.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include "signal-restart-body.h"

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "native signal restart policy FAIL line=%d\n", __LINE__); \
    exit(1); \
} } while (0)

int main(void)
{
    const int signals[] = {SIGUSR1, SIGUSR2, SIGCHLD, SIGKILL, SIGSTOP};
    unsigned int checks = 0;
    for (unsigned int i = 0; i < sizeof(signals) / sizeof(signals[0]); ++i) {
        for (int flag = 0; flag <= 1; ++flag) {
#ifdef MCKERNEL_NATIVE_SIGNAL_STACK
            int expected = 0;
#else
            int expected = signals[i] != SIGKILL && signals[i] != SIGSTOP &&
                           (signals[i] == SIGCHLD || flag);
#endif
            CHECK(isrestart(__NR_rt_sigreturn, (unsigned long)-EINTR, signals[i], flag) == expected);
            CHECK(isrestart(__NR_rt_sigreturn, 0, signals[i], flag) == 0);
            checks += 2;
        }
    }
    CHECK(isrestart(__NR_read, (unsigned long)-EINTR, SIGUSR1, 1) == 1);
    CHECK(isrestart(__NR_read, (unsigned long)-EINTR, SIGUSR1, 0) == 0);
    CHECK(isrestart(__NR_read, (unsigned long)-EINTR, SIGCHLD, 0) == 1);
    CHECK(isrestart(__NR_read, (unsigned long)-EINTR, SIGKILL, 1) == 0);
    CHECK(isrestart(__NR_poll, (unsigned long)-EINTR, SIGUSR1, 1) == 0);
    CHECK(isrestart(__NR_nanosleep, (unsigned long)-EINTR, SIGUSR1, 1) == 0);
    CHECK(isrestart(-1, (unsigned long)-EINTR, SIGUSR1, 1) == 0);
    checks += 7;
    printf("native signal restart policy PASS checks=%u\n", checks);
    return 0;
}
