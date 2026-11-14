/* syscall.c COPYRIGHT FUJITSU LIMITED 2018 */
/**
 * \file syscall.c
 *  License details are found in the file LICENSE.
 * \brief
 *  archtecture depended system call handlers
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 * \author Masamichi Takagi  <m-takagi@ab.jp.nec.com> \par
 * 	Copyright (C) 2013  NEC Corporation
 * \author Tomoki Shirasawa  <tomoki.shirasawa.kk@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 */
/*
 * HISTORY:
 */

#include <ihk/cpu.h>
#include <cls.h>
#include <cpulocal.h>
#include <syscall.h>
#include <process.h>
#include <string.h>
#include <errno.h>
#include <kmalloc.h>
#include <uio.h>
#include <mman.h>
#include <shm.h>
#include <prctl.h>
#include <ihk/ikc.h>
#include <page.h>
#include <limits.h>
#include <syscall.h>
#include <bitops.h>
#include <rusage_private.h>
#include <memory.h>
#include <arch-memory-helpers.h>
#include <ihk/debug.h>
#include <elfcore.h>

#include <memory.h>

extern void abort(void);
extern int puts(const char *);
#define CHECK(x) do { if (!(x)) abort(); } while (0)
long fixture_provider(int, ihk_mc_user_context_t *);
#define syscall_generic_forwarding fixture_provider
#define arch_syscall_forward_context_bridge original_bridge
#include "original-bridge.inc"
#undef arch_syscall_forward_context_bridge
#undef syscall_generic_forwarding
long arch_syscall_forward_context_bridge(int, void *);
typedef long (*public_abi)(int, void *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_syscall_forward_context_bridge), public_abi), "genuine public ABI");

static int calls, expected_number;
static unsigned long got_number, got_context;
static long response;
long fixture_provider(int number, ihk_mc_user_context_t *context)
{ calls++; got_number = (unsigned long)(long)number; got_context = (unsigned long)context; return response; }
int main(void)
{
    const int numbers[] = {0, -1, 0x7fffffff, (-0x7fffffff - 1)};
    const unsigned long pointers[] = {0, 1, 0x8000000000000000UL, ~0UL, 0x12345000UL};
    const long results[] = {0, 1, -1, (-0x7fffffffffffffffL - 1), 0x7fffffffffffffffL, -14, 0x123456789abcdefL};
    unsigned long cases = 0;
    for (unsigned long n = 0; n < 4; n++) for (unsigned long p = 0; p < 5; p++)
    for (unsigned long r = 0; r < 7; r++) {
        response = results[r];
        calls = 0;
        long old = original_bridge(numbers[n], (void *)pointers[p]);
        CHECK(calls == 1 && got_number == (unsigned long)(long)numbers[n] && got_context == pointers[p]);
        calls = 0;
        long now = arch_syscall_forward_context_bridge(numbers[n], (void *)pointers[p]);
        CHECK(calls == 1 && got_number == (unsigned long)(long)numbers[n] && got_context == pointers[p]);
        CHECK(now == old && now == response);
        cases++;
    }
    CHECK(cases == 140);
    puts("PASS arch_syscall_forward_context_bridge controlled forwarding pairs140");
    return 0;
}
