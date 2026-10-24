/* SPDX-License-Identifier: GPL-2.0 */
#include "layout_witness_v2.c"
#include <linux/bug.h>
#include <linux/panic.h>
_Static_assert(sizeof(atomic_long_t) == 8, "64-bit rwsem count");
_Static_assert(__alignof__(atomic_long_t) == 8, "aligned rwsem count");
_Static_assert(sizeof(struct bug_entry) == 12, "relative verbose bug entry");
_Static_assert(RWSEM_WRITER_LOCKED == 1, "writer bit");
_Static_assert(BUGFLAG_WARNING == 1 && TAINT_WARN == 9, "warning flags");
const unsigned long m15_c_warning_layout[] = {
    1, sizeof(atomic_long_t), __alignof__(atomic_long_t),
    offsetof(struct rw_semaphore, count), offsetof(atomic_long_t, counter),
    sizeof(struct bug_entry), offsetof(struct bug_entry, bug_addr_disp),
    offsetof(struct bug_entry, file_disp), offsetof(struct bug_entry, line),
    offsetof(struct bug_entry, flags), RWSEM_WRITER_LOCKED,
    BUGFLAG_WARNING | BUGFLAG_TAINT(TAINT_WARN),
};
