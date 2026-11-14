/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual selected clone store blocks; controlled VM copy provider. */
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#define MCKERNEL_NATIVE_CLONE_TID
#define SYSCALL_POLICY_HELPER_SCOPE static
#define CLONE_PARENT_SETTID 0x00100000
#define CLONE_CHILD_SETTID 0x01000000
#define dkprintf(...) ((void)0)
struct process_vm { unsigned long identity; };
struct thread { struct process_vm *vm; int tid; };
static struct process_vm child_vm = { 2 };
static unsigned calls;
static int copy_result;
static unsigned long expected_address;
static int write_process_vm(struct process_vm *vm, void *dst, const void *src, size_t count)
{
    assert(vm == &child_vm);
    assert((unsigned long)dst == expected_address);
    assert(count == sizeof(int) && *(const int *)src == 431);
    ++calls;
    return copy_result;
}
static int setint_user(int *dst, int value)
{
    assert((unsigned long)dst == expected_address && value == 431);
    ++calls;
    return copy_result;
}
#include "clone-store-conditions.h"
static int child_store(int clone_flags, unsigned long child_tidptr)
{
    struct thread child = { &child_vm, 431 }, *new = &child;
    int err = 0;
    if (0) goto release_ids;
#include "clone-child-store.h"
release_ids:
    return err;
}
static int parent_store(int clone_flags, unsigned long parent_tidptr)
{
    struct thread child = { &child_vm, 431 }, *new = &child;
    int err = 0;
    if (0) goto release_ids;
#include "clone-parent-store.h"
release_ids:
    return err;
}
int main(void)
{
    const unsigned long addresses[] = { 0, 0x1000, 0x1ffd, 0x1ffe, 0x1fff, UINT64_MAX };
    const int results[] = { 0, -EFAULT, -ENOMEM };
    for (unsigned a = 0; a < sizeof addresses / sizeof *addresses; ++a)
        for (unsigned r = 0; r < sizeof results / sizeof *results; ++r) {
            expected_address = addresses[a]; copy_result = results[r]; calls = 0;
            assert(child_store(CLONE_CHILD_SETTID, expected_address) == 0 && calls == 1);
            calls = 0;
            assert(parent_store(CLONE_PARENT_SETTID, expected_address) == 0 && calls == 1);
            calls = 0;
            assert(child_store(0, expected_address) == 0 && parent_store(0, expected_address) == 0 && calls == 0);
        }
    return 0;
}
