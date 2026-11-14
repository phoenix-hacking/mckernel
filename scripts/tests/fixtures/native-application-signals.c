/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact extracted pinned Linux stack predicates and configuration body. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define __user
#define unlikely(x) (x)
#define SS_ONSTACK 1
#define SS_DISABLE 2
#define SS_AUTODISARM (1U << 31)
#define SS_FLAG_BITS SS_AUTODISARM
typedef struct { void *ss_sp; int ss_flags; size_t ss_size; } stack_t;
struct task_struct { unsigned long sas_ss_sp; size_t sas_ss_size; unsigned sas_ss_flags; } task;
static struct task_struct *current = &task;
static void sigaltstack_lock(void) {}
static void sigaltstack_unlock(void) {}
static bool sigaltstack_size_valid(size_t size) { (void)size; return true; }
#include "linux-signal-reference.h"
int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    FILE *file = fopen(argv[1], "rb");
    if (!file) return 3;
    uint64_t w[10];
    while (fread(w, sizeof(w), 1, file) == 1) {
        task.sas_ss_sp = w[0]; task.sas_ss_size = w[1]; task.sas_ss_flags = w[2];
        stack_t new = { (void *)w[4], w[6], w[5] }, old = { 0 };
        int ret = do_sigaltstack(w[7] ? &new : NULL, w[8] ? &old : NULL, w[3], 2048);
        if (ret || !w[8]) memset(&old, 0, sizeof old);
        printf("%d %lu %zu %d %lu %zu %d\n", ret, task.sas_ss_sp, task.sas_ss_size,
               sas_ss_flags(w[3]), (unsigned long)old.ss_sp, old.ss_size, old.ss_flags);
    }
    if (ferror(file)) return 4;
    return fclose(file) != 0;
}
