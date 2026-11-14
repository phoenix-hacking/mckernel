#define MCKERNEL_NATIVE_SIGNAL_STACK
#define X86_SREGS_BASE  (0)
#define X86_SREGS_SIZE  48

#define X86_FLAGS_BASE  (X86_SREGS_BASE + X86_SREGS_SIZE)
#define X86_FLAGS_SIZE  8

#define X86_REGS_BASE   (X86_FLAGS_BASE + X86_FLAGS_SIZE)
#define RAX_OFFSET      (X86_REGS_BASE + 80)
#define ERROR_OFFSET    (X86_REGS_BASE + 120)
#define RSP_OFFSET      (X86_REGS_BASE + 152)

#define PUSH_ALL_REGS   \
        pushq %rdi;     \
        pushq %rsi;     \
        pushq %rdx;     \
        pushq %rcx;     \
        pushq %rax;     \
        pushq %r8;      \
        pushq %r9;      \
        pushq %r10;     \
        pushq %r11;     \
        pushq %rbx;     \
        pushq %rbp;     \
        pushq %r12;     \
        pushq %r13;     \
        pushq %r14;     \
        pushq %r15;     \
        pushq $1;               /* is_gpr_valid is set, and others are cleared */ \
        subq  $X86_FLAGS_BASE,%rsp      /* for x86_sregs, etc. */

#define POP_ALL_REGS    \
        movq  $0,X86_FLAGS_BASE(%rsp);  /* clear all flags */ \
        addq  $X86_REGS_BASE,%rsp;      /* discard x86_sregs, flags, etc. */ \
        popq  %r15;     \
        popq  %r14;     \
        popq  %r13;     \
        popq  %r12;     \
        popq  %rbp;     \
        popq  %rbx;     \
        popq  %r11;     \
        popq  %r10;     \
        popq  %r9;      \
        popq  %r8;      \
        popq  %rax;     \
        popq  %rcx;     \
        popq  %rdx;     \
        popq  %rsi;     \
        popq  %rdi

.text
.globl fixture_produce
fixture_produce:
 subq $8,%rsp
 pushq $0x3b
 pushq $0x1000
 pushq $0x202
 pushq $0x33
 pushq $0x4031ba
 pushq %rdi
		PUSH_ALL_REGS
		movq    ERROR_OFFSET(%rsp), %rdi
#ifdef MCKERNEL_NATIVE_SIGNAL_STACK
		/* #UD has no CPU error word: generic entry saved its vector in
		 * gpr.error for dispatch. Keep that convention, and mark the
		 * separate native signal-frame trap metadata in spare flag bytes.
		 * PUSH_ALL_REGS initialized the complete flag word to one, so
		 * other interrupts/syscalls cannot inherit this valid marker. */
		cmpq    $6, %rdi
		jne     .Lnative_signal_not_ud
		movw    $0x06a5, (X86_FLAGS_BASE + 2)(%rsp)
.Lnative_signal_not_ud:
#endif
		movq	%rsp, %rsi
		call 	handle_interrupt /* Enter C code */
		POP_ALL_REGS
		addq	$8, %rsp
		addq $48, %rsp
		ret

.section .note.GNU-stack,"",@progbits
