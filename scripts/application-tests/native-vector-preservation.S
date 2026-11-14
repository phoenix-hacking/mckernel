/* Baseline x86_64 SSE2 only. State exists across raw kernel boundaries,
 * never across an ordinary C call. All called-by-C control state is restored. */
.text
.globl native_vector_probe
.type native_vector_probe,@function
native_vector_probe:
    pushq %r12
    pushq %r13
    pushq %r14
    subq $64, %rsp
    movq %rsi, %r12
    movl %edi, %r13d
    fnstcw 0(%rsp)
    stmxcsr 4(%rsp)
    fninit
    fldcw vector_cw(%rip)
    ldmxcsr vector_mxcsr(%rip)
    fldl vector_a(%rip)
    fldl vector_b(%rip)
    movdqa vector_xmm+0(%rip), %xmm0
    movdqa vector_xmm+16(%rip), %xmm1
    movdqa vector_xmm+32(%rip), %xmm2
    movdqa vector_xmm+48(%rip), %xmm3
    movdqa vector_xmm+64(%rip), %xmm4
    movdqa vector_xmm+80(%rip), %xmm5
    movdqa vector_xmm+96(%rip), %xmm6
    movdqa vector_xmm+112(%rip), %xmm7
    movdqa vector_xmm+128(%rip), %xmm8
    movdqa vector_xmm+144(%rip), %xmm9
    movdqa vector_xmm+160(%rip), %xmm10
    movdqa vector_xmm+176(%rip), %xmm11
    movdqa vector_xmm+192(%rip), %xmm12
    movdqa vector_xmm+208(%rip), %xmm13
    movdqa vector_xmm+224(%rip), %xmm14
    movdqa vector_xmm+240(%rip), %xmm15
    cmpl $0, %r13d
    je .Lgetpid
    cmpl $1, %r13d
    je .Lfutex
    cmpl $2, %r13d
    je .Lsignal
    movl $91, %r14d
    jmp .Lcleanup
.Lgetpid:
    movl $39, %eax
    syscall
    testq %rax, %rax
    jle .Lsysfail
    jmp .Lcheck
.Lfutex:
    movl $1, 4(%r12)
    movq %r12, %rdi
    movl $128, %esi
    xorl %edx, %edx
    leaq vector_timeout(%rip), %r10
    xorl %r8d, %r8d
    xorl %r9d, %r9d
    movl $202, %eax
    syscall
    testq %rax, %rax
    jne .Lsysfail
    jmp .Lcheck
.Lsignal:
    movl $0, native_vector_signal_seen(%rip)
    movl 8(%r12), %edi
    movl 12(%r12), %esi
    movl $10, %edx
    movl $234, %eax
    syscall
    testq %rax, %rax
    jne .Lsysfail
    /* Require completed delivery before ANY interrupted-state comparison.
     * A signal delivered only after those comparisons cannot prove restore. */
    cmpl $1, native_vector_signal_seen(%rip)
    jne .Lsignal_missing
.Lcheck:
    /* VECTOR_TEST_INJECTION */
    movl $1, %r14d
    pcmpeqb vector_xmm+0(%rip), %xmm0
    pmovmskb %xmm0, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $2, %r14d
    pcmpeqb vector_xmm+16(%rip), %xmm1
    pmovmskb %xmm1, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $3, %r14d
    pcmpeqb vector_xmm+32(%rip), %xmm2
    pmovmskb %xmm2, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $4, %r14d
    pcmpeqb vector_xmm+48(%rip), %xmm3
    pmovmskb %xmm3, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $5, %r14d
    pcmpeqb vector_xmm+64(%rip), %xmm4
    pmovmskb %xmm4, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $6, %r14d
    pcmpeqb vector_xmm+80(%rip), %xmm5
    pmovmskb %xmm5, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $7, %r14d
    pcmpeqb vector_xmm+96(%rip), %xmm6
    pmovmskb %xmm6, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $8, %r14d
    pcmpeqb vector_xmm+112(%rip), %xmm7
    pmovmskb %xmm7, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $9, %r14d
    pcmpeqb vector_xmm+128(%rip), %xmm8
    pmovmskb %xmm8, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $10, %r14d
    pcmpeqb vector_xmm+144(%rip), %xmm9
    pmovmskb %xmm9, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $11, %r14d
    pcmpeqb vector_xmm+160(%rip), %xmm10
    pmovmskb %xmm10, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $12, %r14d
    pcmpeqb vector_xmm+176(%rip), %xmm11
    pmovmskb %xmm11, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $13, %r14d
    pcmpeqb vector_xmm+192(%rip), %xmm12
    pmovmskb %xmm12, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $14, %r14d
    pcmpeqb vector_xmm+208(%rip), %xmm13
    pmovmskb %xmm13, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $15, %r14d
    pcmpeqb vector_xmm+224(%rip), %xmm14
    pmovmskb %xmm14, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $16, %r14d
    pcmpeqb vector_xmm+240(%rip), %xmm15
    pmovmskb %xmm15, %eax
    cmpl $65535, %eax
    jne .Lcleanup
    movl $17, %r14d
    fnstcw 8(%rsp)
    cmpw $0x077f, 8(%rsp)
    jne .Lcleanup
    movl $18, %r14d
    stmxcsr 8(%rsp)
    cmpl $0x3fa0, 8(%rsp)
    jne .Lcleanup
    movl $19, %r14d
    fnstsw %ax
    andl $0x3800, %eax
    cmpl $0x3000, %eax
    jne .Lcleanup
    fstpt 16(%rsp)
    fstpt 32(%rsp)
    movl $20, %r14d
    movabsq $0xe000000000000000, %rax
    cmpq %rax, 16(%rsp)
    jne .Lcleanup
    cmpw $0xc000, 24(%rsp)
    jne .Lcleanup
    movl $21, %r14d
    movabsq $0xa000000000000000, %rax
    cmpq %rax, 32(%rsp)
    jne .Lcleanup
    cmpw $0x3fff, 40(%rsp)
    jne .Lcleanup
    xorl %r14d, %r14d
    jmp .Lcleanup
.Lsignal_missing:
    movl $92, %r14d
    jmp .Lcleanup
.Lsysfail:
    movl $90, %r14d
.Lcleanup:
    fninit
    fldcw 0(%rsp)
    ldmxcsr 4(%rsp)
    movl %r14d, %eax
    addq $64, %rsp
    popq %r14
    popq %r13
    popq %r12
    ret
.size native_vector_probe,.-native_vector_probe

/* Signal handler is an ordinary ABI-valid function: XMM registers and x87
 * status are caller-saved, control fields are preserved, x87 stack empty. */
.globl native_vector_handler
.type native_vector_handler,@function
native_vector_handler:
    subq $16, %rsp
    fnstcw 0(%rsp)
    stmxcsr 4(%rsp)
    fninit
    fld1
    fstp %st(0)
    fldcw 0(%rsp)
    orl $0x21, 4(%rsp)
    ldmxcsr 4(%rsp)
    pcmpeqd %xmm0, %xmm0
    pcmpeqd %xmm1, %xmm1
    pcmpeqd %xmm2, %xmm2
    pcmpeqd %xmm3, %xmm3
    pcmpeqd %xmm4, %xmm4
    pcmpeqd %xmm5, %xmm5
    pcmpeqd %xmm6, %xmm6
    pcmpeqd %xmm7, %xmm7
    pcmpeqd %xmm8, %xmm8
    pcmpeqd %xmm9, %xmm9
    pcmpeqd %xmm10, %xmm10
    pcmpeqd %xmm11, %xmm11
    pcmpeqd %xmm12, %xmm12
    pcmpeqd %xmm13, %xmm13
    pcmpeqd %xmm14, %xmm14
    pcmpeqd %xmm15, %xmm15
    movl $1, native_vector_signal_seen(%rip)
    addq $16, %rsp
    ret
.size native_vector_handler,.-native_vector_handler
.section .rodata
.p2align 4
vector_xmm:
    .quad 0x1122334455667700, 0x89abcdef10203000
    .quad 0x1122334455667701, 0x89abcdef10203001
    .quad 0x1122334455667702, 0x89abcdef10203002
    .quad 0x1122334455667703, 0x89abcdef10203003
    .quad 0x1122334455667704, 0x89abcdef10203004
    .quad 0x1122334455667705, 0x89abcdef10203005
    .quad 0x1122334455667706, 0x89abcdef10203006
    .quad 0x1122334455667707, 0x89abcdef10203007
    .quad 0x1122334455667708, 0x89abcdef10203008
    .quad 0x1122334455667709, 0x89abcdef10203009
    .quad 0x112233445566770a, 0x89abcdef1020300a
    .quad 0x112233445566770b, 0x89abcdef1020300b
    .quad 0x112233445566770c, 0x89abcdef1020300c
    .quad 0x112233445566770d, 0x89abcdef1020300d
    .quad 0x112233445566770e, 0x89abcdef1020300e
    .quad 0x112233445566770f, 0x89abcdef1020300f
vector_cw: .short 0x077f
.p2align 2
vector_mxcsr: .long 0x3fa0
.p2align 3
vector_a: .double 1.25
vector_b: .double -3.5
vector_timeout: .quad 3, 0
.section .note.GNU-stack,"",@progbits
