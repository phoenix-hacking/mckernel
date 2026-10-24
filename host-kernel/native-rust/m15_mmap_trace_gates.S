/* SPDX-License-Identifier: GPL-2.0 */
/* Private assembly candidate for review: exact HAVE_JUMP_LABEL_HACK table ABI.
 * Production includes baseline Linux linkage/annotation/RET definitions.
 * M15_USER_GATE_PROBE tests the same jump/table body with user-mode returns;
 * it is not the production linkage/ENDBR/rethunk acceptance path. */
#ifdef M15_USER_GATE_PROBE
#define SYM_FUNC_START(name) .globl name; .type name, @function; .p2align 4; name:
#define SYM_FUNC_END(name) .size name, .-name
#define RET ret
.macro M15_ANNOTATE_DATA_SPECIAL
.Lannotation_here_\@:
 .pushsection .discard.annotate_data,"M",@progbits,8
 .long .Lannotation_here_\@ - .
 .long 1
 .popsection
.endm
#define ANNOTATE_DATA_SPECIAL M15_ANNOTATE_DATA_SPECIAL
#else
#include <linux/linkage.h>
#include <linux/annotate.h>
#include <asm/asm.h>
#if !defined(CONFIG_X86_64) || !defined(CONFIG_HAVE_JUMP_LABEL_HACK) || !defined(CONFIG_OBJTOOL)
#error "M15 gates require the exact x86_64/HAVE_JUMP_LABEL_HACK/OBJTOOL pin"
#endif
#endif

/* tracepoint.key offset=8 is separately asserted in the Rust and C witnesses.
 * key+2 encodes the baseline hack flag. branch=false adds zero, not one.
 * Both short and long jumps are understood by pinned objtool check.c.
 * Do not execute an unprocessed object as the default-false kernel gate. */

SYM_FUNC_START(m15_mmap_trace_start_enabled)
1: jmp 2f
 xorl %eax, %eax
 RET
2: movl $1, %eax
 RET
 .pushsection __jump_table,"aw"
 .balign 8
 ANNOTATE_DATA_SPECIAL
 .long 1b - .
 .long 2b - .
 .quad __tracepoint_mmap_lock_start_locking + 8 + 2 - .
 .popsection
SYM_FUNC_END(m15_mmap_trace_start_enabled)

SYM_FUNC_START(m15_mmap_trace_acquire_enabled)
1: jmp 2f
 xorl %eax, %eax
 RET
2: movl $1, %eax
 RET
 .pushsection __jump_table,"aw"
 .balign 8
 ANNOTATE_DATA_SPECIAL
 .long 1b - .
 .long 2b - .
 .quad __tracepoint_mmap_lock_acquire_returned + 8 + 2 - .
 .popsection
SYM_FUNC_END(m15_mmap_trace_acquire_enabled)

SYM_FUNC_START(m15_mmap_trace_release_enabled)
1: jmp 2f
 xorl %eax, %eax
 RET
2: movl $1, %eax
 RET
 .pushsection __jump_table,"aw"
 .balign 8
 ANNOTATE_DATA_SPECIAL
 .long 1b - .
 .long 2b - .
 .quad __tracepoint_mmap_lock_released + 8 + 2 - .
 .popsection
SYM_FUNC_END(m15_mmap_trace_release_enabled)

.section .note.GNU-stack,"",@progbits
