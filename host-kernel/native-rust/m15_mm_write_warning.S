/* SPDX-License-Identifier: GPL-2.0 */
/* Exact x86 Linux WARN_ON warning mechanism; source candidate, not accepted.
 * Invoked only when !(atomic_long_read(&mmap_lock.count) & 1).
 * WARN_ON repeats: deliberately no BUGFLAG_ONCE, new errors, or early return.
 * These are Linux-owned linkage/annotation macros, not copied project C. */
#include <linux/linkage.h>
#include <linux/annotate.h>
#if !defined(CONFIG_X86_64) || !defined(CONFIG_OBJTOOL) || \
    !defined(CONFIG_GENERIC_BUG) || !defined(CONFIG_GENERIC_BUG_RELATIVE_POINTERS) || \
    !defined(CONFIG_DEBUG_BUGVERBOSE) || !defined(CONFIG_BUG)
#error "M15 warning requires the exact x86/OBJTOOL/relative verbose bug-table pin"
#endif
#if defined(CONFIG_LOCKDEP) || defined(CONFIG_PREEMPT_RT) || defined(CONFIG_NOINSTR_VALIDATION)
#error "M15 warning implements only the pinned non-lockdep/non-RT/no-noinstr-validation assertion"
#endif

/* include/asm-generic/bug.h: BUGFLAG_WARNING=1, TAINT_WARN=9, shift=8.
 * Rust/C witnesses assert these and sizeof(struct bug_entry)==12.
 * The __bug_table record matches _BUG_FLAGS_ASM/ARCH_WARN_ASM on this pin.
 * ANNOTATE_REACHABLE belongs on UD2; Linux resumes after its two bytes.
 * SYM_FUNC_START supplies ENDBR; RET preserves the platform return thunk. */
SYM_FUNC_START(m15_mmap_write_lock_warning)
 ANNOTATE_REACHABLE
.set .Lm15_write_lock_warning_line, __LINE__
.Lm15_write_lock_warn:
 .byte 0x0f, 0x0b
 RET
 .pushsection __bug_table,"aw"
 ANNOTATE_DATA_SPECIAL
.Lm15_write_lock_bug_entry:
 .long .Lm15_write_lock_warn - .
 .long .Lm15_write_lock_warning_file - .
 .short .Lm15_write_lock_warning_line
 .short (1 | (9 << 8))
 .org .Lm15_write_lock_bug_entry + 12
 .popsection
SYM_FUNC_END(m15_mmap_write_lock_warning)

.pushsection .rodata.str1.1,"aMS",@progbits,1
.Lm15_write_lock_warning_file:
 .asciz __FILE__
.popsection
.section .note.GNU-stack,"",@progbits
