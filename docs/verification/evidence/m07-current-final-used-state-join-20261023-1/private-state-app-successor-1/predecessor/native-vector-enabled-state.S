/* Explicit AVX/YMM plus x87/MXCSR. CPUID/XGETBV gated by C. State exists across raw kernel boundaries,
 * never across an ordinary C call. All called-by-C control state is restored. */
.text
.globl native_enabled_probe
.type native_enabled_probe,@function
native_enabled_probe:
    pushq %r12
    pushq %r13
    pushq %r14
    subq $128, %rsp
    movq %rsi, %r12
    movl %edi, %r13d
    fnstcw 0(%rsp)
    stmxcsr 4(%rsp)
    fninit
    fldcw enabled_cw(%rip)
    ldmxcsr enabled_mxcsr(%rip)
    fldl enabled_a(%rip)
    fldl enabled_b(%rip)
    vmovdqu enabled_ymm+0(%rip), %ymm0
    vmovdqu enabled_ymm+32(%rip), %ymm1
    vmovdqu enabled_ymm+64(%rip), %ymm2
    vmovdqu enabled_ymm+96(%rip), %ymm3
    vmovdqu enabled_ymm+128(%rip), %ymm4
    vmovdqu enabled_ymm+160(%rip), %ymm5
    vmovdqu enabled_ymm+192(%rip), %ymm6
    vmovdqu enabled_ymm+224(%rip), %ymm7
    vmovdqu enabled_ymm+256(%rip), %ymm8
    vmovdqu enabled_ymm+288(%rip), %ymm9
    vmovdqu enabled_ymm+320(%rip), %ymm10
    vmovdqu enabled_ymm+352(%rip), %ymm11
    vmovdqu enabled_ymm+384(%rip), %ymm12
    vmovdqu enabled_ymm+416(%rip), %ymm13
    vmovdqu enabled_ymm+448(%rip), %ymm14
    vmovdqu enabled_ymm+480(%rip), %ymm15
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
    leaq enabled_timeout(%rip), %r10
    xorl %r8d, %r8d
    xorl %r9d, %r9d
    movl $202, %eax
    syscall
    testq %rax, %rax
    jne .Lsysfail
    jmp .Lcheck
.Lsignal:
    movl $0, native_enabled_signal_seen(%rip)
    movl 8(%r12), %edi
    movl 12(%r12), %esi
    movl $10, %edx
    movl $234, %eax
    syscall
    testq %rax, %rax
    jne .Lsysfail
    /* Require completed delivery before ANY interrupted-state comparison.
     * A signal delivered only after those comparisons cannot prove restore. */
    cmpl $1, native_enabled_signal_seen(%rip)
    jne .Lsignal_missing
.Lcheck:
    /* ENABLED_TEST_INJECTION */
    movl $1, %r14d
    vmovdqu %ymm0, 64(%rsp)
    movq enabled_ymm+0(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+8(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+16(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+24(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $2, %r14d
    vmovdqu %ymm1, 64(%rsp)
    movq enabled_ymm+32(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+40(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+48(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+56(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $3, %r14d
    vmovdqu %ymm2, 64(%rsp)
    movq enabled_ymm+64(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+72(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+80(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+88(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $4, %r14d
    vmovdqu %ymm3, 64(%rsp)
    movq enabled_ymm+96(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+104(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+112(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+120(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $5, %r14d
    vmovdqu %ymm4, 64(%rsp)
    movq enabled_ymm+128(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+136(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+144(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+152(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $6, %r14d
    vmovdqu %ymm5, 64(%rsp)
    movq enabled_ymm+160(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+168(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+176(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+184(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $7, %r14d
    vmovdqu %ymm6, 64(%rsp)
    movq enabled_ymm+192(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+200(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+208(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+216(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $8, %r14d
    vmovdqu %ymm7, 64(%rsp)
    movq enabled_ymm+224(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+232(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+240(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+248(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $9, %r14d
    vmovdqu %ymm8, 64(%rsp)
    movq enabled_ymm+256(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+264(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+272(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+280(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $10, %r14d
    vmovdqu %ymm9, 64(%rsp)
    movq enabled_ymm+288(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+296(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+304(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+312(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $11, %r14d
    vmovdqu %ymm10, 64(%rsp)
    movq enabled_ymm+320(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+328(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+336(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+344(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $12, %r14d
    vmovdqu %ymm11, 64(%rsp)
    movq enabled_ymm+352(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+360(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+368(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+376(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $13, %r14d
    vmovdqu %ymm12, 64(%rsp)
    movq enabled_ymm+384(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+392(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+400(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+408(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $14, %r14d
    vmovdqu %ymm13, 64(%rsp)
    movq enabled_ymm+416(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+424(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+432(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+440(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $15, %r14d
    vmovdqu %ymm14, 64(%rsp)
    movq enabled_ymm+448(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+456(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+464(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+472(%rip), %rax
    cmpq %rax, 88(%rsp)
    jne .Lcleanup
    movl $16, %r14d
    vmovdqu %ymm15, 64(%rsp)
    movq enabled_ymm+480(%rip), %rax
    cmpq %rax, 64(%rsp)
    jne .Lcleanup
    movq enabled_ymm+488(%rip), %rax
    cmpq %rax, 72(%rsp)
    jne .Lcleanup
    movq enabled_ymm+496(%rip), %rax
    cmpq %rax, 80(%rsp)
    jne .Lcleanup
    movq enabled_ymm+504(%rip), %rax
    cmpq %rax, 88(%rsp)
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
    vzeroupper
    fninit
    fldcw 0(%rsp)
    ldmxcsr 4(%rsp)
    movl %r14d, %eax
    addq $128, %rsp
    popq %r14
    popq %r13
    popq %r12
    ret
.size native_enabled_probe,.-native_enabled_probe

/* Signal handler is an ordinary ABI-valid function: XMM registers and x87
 * status are caller-saved, control fields are preserved, x87 stack empty. */
.globl native_enabled_handler
.type native_enabled_handler,@function
native_enabled_handler:
    subq $16, %rsp
    fnstcw 0(%rsp)
    stmxcsr 4(%rsp)
    fninit
    fld1
    fstp %st(0)
    fldcw 0(%rsp)
    orl $0x21, 4(%rsp)
    ldmxcsr 4(%rsp)
    vxorps %ymm0, %ymm0, %ymm0
    vxorps %ymm1, %ymm1, %ymm1
    vxorps %ymm2, %ymm2, %ymm2
    vxorps %ymm3, %ymm3, %ymm3
    vxorps %ymm4, %ymm4, %ymm4
    vxorps %ymm5, %ymm5, %ymm5
    vxorps %ymm6, %ymm6, %ymm6
    vxorps %ymm7, %ymm7, %ymm7
    vxorps %ymm8, %ymm8, %ymm8
    vxorps %ymm9, %ymm9, %ymm9
    vxorps %ymm10, %ymm10, %ymm10
    vxorps %ymm11, %ymm11, %ymm11
    vxorps %ymm12, %ymm12, %ymm12
    vxorps %ymm13, %ymm13, %ymm13
    vxorps %ymm14, %ymm14, %ymm14
    vxorps %ymm15, %ymm15, %ymm15
    movl $1, native_enabled_signal_seen(%rip)
    addq $16, %rsp
    ret
.size native_enabled_handler,.-native_enabled_handler
/* Called only after main's CPUID/XGETBV gate. No controls/x87 touched.
 * All YMM caller-saved under SysV. Different helper/worker patterns make
 * missing context restoration visible on either side of a handoff. */
.globl native_enabled_clobber_wake
.type native_enabled_clobber_wake,@function
native_enabled_clobber_wake:
    subq $32, %rsp
    vxorps %ymm0, %ymm0, %ymm0
    vxorps %ymm1, %ymm1, %ymm1
    vxorps %ymm2, %ymm2, %ymm2
    vxorps %ymm3, %ymm3, %ymm3
    vxorps %ymm4, %ymm4, %ymm4
    vxorps %ymm5, %ymm5, %ymm5
    vxorps %ymm6, %ymm6, %ymm6
    vxorps %ymm7, %ymm7, %ymm7
    vxorps %ymm8, %ymm8, %ymm8
    vxorps %ymm9, %ymm9, %ymm9
    vxorps %ymm10, %ymm10, %ymm10
    vxorps %ymm11, %ymm11, %ymm11
    vxorps %ymm12, %ymm12, %ymm12
    vxorps %ymm13, %ymm13, %ymm13
    vxorps %ymm14, %ymm14, %ymm14
    vxorps %ymm15, %ymm15, %ymm15
    movl $129, %esi
    movl $1, %edx
    xorl %r10d, %r10d
    xorl %r8d, %r8d
    xorl %r9d, %r9d
    movl $202, %eax
    syscall
    movq %rax, %r10
    /* ENABLED_HELPER_TEST_INJECTION */
    vmovdqu %ymm0, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm1, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm2, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm3, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm4, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm5, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm6, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm7, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm8, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm9, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm10, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm11, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm12, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm13, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm14, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    vmovdqu %ymm15, (%rsp)
    cmpq $0, 0(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 8(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 16(%rsp)
    jne .Lhelper_corrupt
    cmpq $0, 24(%rsp)
    jne .Lhelper_corrupt
    movq %r10, %rax
    jmp .Lhelper_done
.Lhelper_corrupt:
    movq $-98, %rax
.Lhelper_done:
    vzeroupper
    addq $32, %rsp
    ret
.size native_enabled_clobber_wake,.-native_enabled_clobber_wake
.section .rodata
.p2align 4
enabled_ymm:
    .quad 0x1122334455667700, 0x89abcdef10203000, 0x76543210fedcba00, 0xfedcba9876543200
    .quad 0x1122334455667701, 0x89abcdef10203001, 0x76543210fedcba01, 0xfedcba9876543201
    .quad 0x1122334455667702, 0x89abcdef10203002, 0x76543210fedcba02, 0xfedcba9876543202
    .quad 0x1122334455667703, 0x89abcdef10203003, 0x76543210fedcba03, 0xfedcba9876543203
    .quad 0x1122334455667704, 0x89abcdef10203004, 0x76543210fedcba04, 0xfedcba9876543204
    .quad 0x1122334455667705, 0x89abcdef10203005, 0x76543210fedcba05, 0xfedcba9876543205
    .quad 0x1122334455667706, 0x89abcdef10203006, 0x76543210fedcba06, 0xfedcba9876543206
    .quad 0x1122334455667707, 0x89abcdef10203007, 0x76543210fedcba07, 0xfedcba9876543207
    .quad 0x1122334455667708, 0x89abcdef10203008, 0x76543210fedcba08, 0xfedcba9876543208
    .quad 0x1122334455667709, 0x89abcdef10203009, 0x76543210fedcba09, 0xfedcba9876543209
    .quad 0x112233445566770a, 0x89abcdef1020300a, 0x76543210fedcba0a, 0xfedcba987654320a
    .quad 0x112233445566770b, 0x89abcdef1020300b, 0x76543210fedcba0b, 0xfedcba987654320b
    .quad 0x112233445566770c, 0x89abcdef1020300c, 0x76543210fedcba0c, 0xfedcba987654320c
    .quad 0x112233445566770d, 0x89abcdef1020300d, 0x76543210fedcba0d, 0xfedcba987654320d
    .quad 0x112233445566770e, 0x89abcdef1020300e, 0x76543210fedcba0e, 0xfedcba987654320e
    .quad 0x112233445566770f, 0x89abcdef1020300f, 0x76543210fedcba0f, 0xfedcba987654320f
enabled_cw: .short 0x077f
.p2align 2
enabled_mxcsr: .long 0x3fa0
.p2align 3
enabled_a: .double 1.25
enabled_b: .double -3.5
enabled_timeout: .quad 3, 0
.section .note.GNU-stack,"",@progbits
