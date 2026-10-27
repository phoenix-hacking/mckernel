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
int fixture_provider(void *, const void *, size_t);
#define copy_to_user fixture_provider
#define arch_copy_to_user_bridge original_bridge
#include "original-bridge.inc"
#undef arch_copy_to_user_bridge
#undef copy_to_user
long arch_copy_to_user_bridge(unsigned long, const void *, size_t);
typedef long (*public_abi)(unsigned long, const void *, size_t);
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_copy_to_user_bridge), public_abi), "genuine public ABI");

static int calls, response;
static unsigned long got_destination, got_source, got_bytes;
int fixture_provider(void *dst, const void *src, size_t size)
{ calls++; got_destination = (unsigned long)dst; got_source = (unsigned long)src; got_bytes = size; return response; }
int main(void)
{
    const unsigned long pointers[] = {0, 1, 0x8000000000000000UL, ~0UL, 0x12345000UL};
    const unsigned long lengths[] = {0, 1, 4096, ~0UL, 0x8000000000000000UL};
    const int results[] = {0, 1, -1, (-0x7fffffff - 1), 0x7fffffff, -14, 0x12345678};
    unsigned long cases = 0;
    for (unsigned long p = 0; p < 5; p++) for (unsigned long l = 0; l < 5; l++)
    for (unsigned long r = 0; r < 7; r++) {
        unsigned long dst = pointers[p], src = pointers[(p + 1) % 5];
        response = results[r]; calls = 0;
        long old = original_bridge(dst, (const void *)src, lengths[l]);
        CHECK(calls == 1 && got_destination == dst && got_source == src && got_bytes == lengths[l]);
        calls = 0;
        long now = arch_copy_to_user_bridge(dst, (const void *)src, lengths[l]);
        CHECK(calls == 1 && got_destination == dst && got_source == src && got_bytes == lengths[l]);
        CHECK(now == old && now == (long)response);
        cases++;
    }
    CHECK(cases == 175);
    puts("PASS arch_copy_to_user_bridge controlled usercopy pairs175");
    return 0;
}
