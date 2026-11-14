/* SPDX-License-Identifier: GPL-2.0 */
/* Adds the assembly key-offset precondition; original witness is preserved. */
#include "layout_witness.c"
_Static_assert(offsetof(struct tracepoint, key) == 8, "M15 gate key offset");
_Static_assert(offsetof(struct mm_struct, mm_lock_seq) % 4 == 0, "MM sequence alignment");
_Static_assert(offsetof(struct vm_area_struct, vm_lock_seq) % 4 == 0, "VMA sequence alignment");
