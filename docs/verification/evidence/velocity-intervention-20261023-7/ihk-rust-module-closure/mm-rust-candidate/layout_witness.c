/* SPDX-License-Identifier: GPL-2.0 */
/* Source-only witness: compile with exact retained SDK flags; never load. */
#include <linux/mm.h>
#include <linux/jump_label.h>
#include <linux/tracepoint-defs.h>
#include <linux/stddef.h>

_Static_assert(sizeof(((seqcount_t *)0)->sequence) == 4, "u32 sequence");
_Static_assert(sizeof(((struct vm_area_struct *)0)->vm_lock_seq) == 4, "u32 VMA sequence");
const unsigned long m15_c_mm_layout[] = {
    1, /* witness version; positions match layout_witness.rs */
    sizeof(struct mm_struct), __alignof__(struct mm_struct),
    offsetof(struct mm_struct, mmap_lock),
    offsetof(struct mm_struct, mm_lock_seq),
    sizeof(seqcount_t), __alignof__(seqcount_t), offsetof(seqcount_t, sequence),
    sizeof(struct vm_area_struct), __alignof__(struct vm_area_struct),
    offsetof(struct vm_area_struct, vm_mm),
    offsetof(struct vm_area_struct, vm_lock_seq),
    offsetof(struct vm_area_struct, vm_lock),
    sizeof(struct vma_lock), offsetof(struct vma_lock, lock),
    sizeof(struct rw_semaphore), __alignof__(struct rw_semaphore),
    sizeof(struct tracepoint), __alignof__(struct tracepoint),
    offsetof(struct tracepoint, key), sizeof(struct static_key),
    offsetof(struct static_key, enabled), sizeof(struct jump_entry),
};
