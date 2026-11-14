/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * NEW private candidate, independent review required. Standard XSAVE/XRSTOR
 * follows existing reviewed raw-syscall live intervals. Only selected 3/4/9
 * are requested; no ordinary Rust/libc call occurs between seed and restore.
 * Context: mask0 seed8 original16 observed24 ranges32 report40 pkru_offset48.
 * Range: offset0 length8 component_bit16, stride24, zero-length terminator.
 * Report: seeded0 checked4 restored8 restore_checked12 syscall_result16.
 */
.text
/* rbx=context. All temporaries caller-saved; r12-r15 remain probe ownership.
 * Compare only requested XSTATE_BV bits and architecturally defined bytes of
 * components whose EXPECTED state is in use. Initial original state is checked
 * by the cleared in-use bit rather than unspecified XSAVE destination bytes.
 */
.macro VERIFY expected, failure
    movq \expected, %r15
    movq 24(%rbx), %rdi
    movq 0(%rbx), %rax
    movq %rax, %rdx
    shrq $32, %rdx
    xsave64 (%rdi)
    movq 512(%rdi), %rax
    xorq 512(%r15), %rax
    andq 0(%rbx), %rax
    jnz \failure
    movq 32(%rbx), %r10
.Lrange\@:
    movq 8(%r10), %rcx
    testq %rcx, %rcx
    jz .Lverified\@
    movq 16(%r10), %rax
    testq %rax, 512(%r15)
    jz .Lnext\@
    movq 0(%r10), %rax
    leaq (%r15,%rax), %rsi
    movq 24(%rbx), %rdi
    addq %rax, %rdi
    cld
    repe cmpsb
    jne \failure
.Lnext\@:
    addq $24, %r10
    jmp .Lrange\@
.Lverified\@:
.endm
.macro CAPTURE_ORIGINAL
    movq 16(%rbx), %rdi
    movq 0(%rbx), %rax
    movq %rax, %rdx
    shrq $32, %rdx
    xsave64 (%rdi)
.endm
/* Merge original key0..14 bits, changing ONLY the two key15 state bits.
 * No mappings are assigned keys and no access-control behavior is exercised.
 */
.macro PREPARE_PKRU
    testq $0x200, 0(%rbx)
    jz .Lno_pkru\@
    movq 48(%rbx), %rcx
    movq 16(%rbx), %rsi
    movq 8(%rbx), %rdi
    xorl %eax, %eax
    testq $0x200, 512(%rsi)
    jz .Lpkru_initial\@
    movl (%rsi,%rcx), %eax
.Lpkru_initial\@:
    andl $0x3fffffff, %eax
    movl (%rdi,%rcx), %edx
    andl $0xc0000000, %edx
    orl %eax, %edx
    movl %edx, (%rdi,%rcx)
.Lno_pkru\@:
.endm
.macro LOAD_SEED
    movq 8(%rbx), %rdi
    movq 0(%rbx), %rax
    movq %rax, %rdx
    shrq $32, %rdx
    xrstor64 (%rdi)
.endm
.globl component_probe
.type component_probe,@function
component_probe:
    pushq %rbx
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    movl %edi, %r13d
    movq %rsi, %r12
    movq %rdx, %rbx
    xorl %r14d, %r14d
    CAPTURE_ORIGINAL
    PREPARE_PKRU
    LOAD_SEED
    VERIFY 8(%rbx), .Lseed_bad
    movq 40(%rbx), %rdi
    movl $1, 0(%rdi)
    cmpl $0, %r13d
    je .Lsyscall
    cmpl $1, %r13d
    je .Lfutex
    cmpl $2, %r13d
    je .Lsignal
    cmpl $3, %r13d
    je .Lwake
    movl $5, %r14d
    jmp .Lrestore
.Lsyscall:
    movl $39, %eax
    syscall
    movq 40(%rbx), %rdi
    movq %rax, 16(%rdi)
    testq %rax, %rax
    jle .Lsys_bad
    jmp .Lcheck
.Lfutex:
    /* Exact predecessor: publish after live state, FUTEX_WAIT_PRIVATE, 3s. */
    movl $1, 4(%r12)
    movq %r12, %rdi
    movl $128, %esi
    xorl %edx, %edx
    leaq component_timeout(%rip), %r10
    xorl %r8d, %r8d
    xorl %r9d, %r9d
    movl $202, %eax
    syscall
    movq 40(%rbx), %rdi
    movq %rax, 16(%rdi)
    testq %rax, %rax
    jne .Lsys_bad
    jmp .Lcheck
.Lwake:
    /* Exact predecessor helper raw FUTEX_WAKE_PRIVATE, one waiter maximum. */
    movq %r12, %rdi
    movl $129, %esi
    movl $1, %edx
    xorl %r10d, %r10d
    xorl %r8d, %r8d
    xorl %r9d, %r9d
    movl $202, %eax
    syscall
    movq 40(%rbx), %rdi
    movq %rax, 16(%rdi)
    testq %rax, %rax
    js .Lsys_bad
    jmp .Lcheck
.Lsignal:
    /* Exact predecessor self tgkill and delivery marker before comparison. */
    movl $0, COMPONENT_SIGNAL_SEEN(%rip)
    movl 8(%r12), %edi
    movl 12(%r12), %esi
    movl $10, %edx
    movl $234, %eax
    syscall
    movq 40(%rbx), %rdi
    movq %rax, 16(%rdi)
    testq %rax, %rax
    jne .Lsys_bad
    cmpl $1, COMPONENT_SIGNAL_SEEN(%rip)
    jne .Lsignal_bad
.Lcheck:
    /* COMPONENT_BOUNDARY_TEST_INJECTION */
    VERIFY 8(%rbx), .Lstate_bad
    movq 40(%rbx), %rdi
    movl $1, 4(%rdi)
    jmp .Lrestore
.Lseed_bad: movl $1, %r14d; jmp .Lrestore
.Lstate_bad: movl $2, %r14d; jmp .Lrestore
.Lsignal_bad: movl $3, %r14d; jmp .Lrestore
.Lsys_bad: movl $4, %r14d
.Lrestore:
    /* Every controlled success/error path restores before the Rust ABI return. */
    movq 16(%rbx), %rdi
    movq 0(%rbx), %rax
    movq %rax, %rdx
    shrq $32, %rdx
    xrstor64 (%rdi)
    movq 40(%rbx), %rdi
    movl $1, 8(%rdi)
    VERIFY 16(%rbx), .Lrestore_bad
    movq 40(%rbx), %rdi
    movl $1, 12(%rdi)
    jmp .Lreturn
.Lrestore_bad: movl $6, %r14d
.Lreturn:
    movl %r14d, %eax
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbx
    ret
.size component_probe,.-component_probe
/* Handler intentionally leaves a distinct, read-back-verified component state
 * for the existing signal-return mechanism to restore. No Rust/libc calls.
 * Callee-saved GPRs preserved. Register payloads never test memory permissions.
 */
.globl component_handler
.type component_handler,@function
component_handler:
    pushq %rbx
    pushq %r15
    movq COMPONENT_HANDLER_CONTEXT(%rip), %rbx
    testq %rbx, %rbx
    jz .Lhandler_bad
    CAPTURE_ORIGINAL
    PREPARE_PKRU
    LOAD_SEED
    VERIFY 8(%rbx), .Lhandler_bad
    /* COMPONENT_HANDLER_MARKER_TEST_INJECTION */
    movl $1, COMPONENT_SIGNAL_SEEN(%rip)
    jmp .Lhandler_return
.Lhandler_bad:
    movl $-1, COMPONENT_SIGNAL_SEEN(%rip)
.Lhandler_return:
    popq %r15
    popq %rbx
    ret
.size component_handler,.-component_handler
.section .rodata
.p2align 3
component_timeout: .quad 3, 0
.section .note.GNU-stack,"",@progbits
