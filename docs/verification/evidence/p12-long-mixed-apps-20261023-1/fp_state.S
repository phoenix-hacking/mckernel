/* Derived from the accepted attempt3 native-vector-enabled-state.S contract:
 * 16 full YMM loads/stores, direct syscall live interval, fnstcw/stmxcsr,
 * vzeroupper + fninit + original controls restoration. This two-thread
 * extension is a NEW source proposal requiring independent ABI review.
 * SysV: r12-r15/rbx/rbp preserved; rcx/r11 syscall clobbers never hold state.
 * Atomic fields are aligned 32-bit x86 loads/stores, acquire/release compatible.
 * Ready is published only AFTER all live FP loads. Both peers must be ready
 * before either progress store, proving peer progress occurs inside live state.
 * No calls, libc, compiler code, or ABI boundaries occur until cleanup.
 */
.text
.macro YIELD
    cmpl $0, 8(%r13)
    jne .Lpeer_fail
    incl %ebp
    cmpl $65536, %ebp
    ja .Lbudget_fail
    movl $24, %eax
    syscall
    testq %rax, %rax
    jne .Lsys_fail
.endm
.globl fp_state_probe
.type fp_state_probe,@function
fp_state_probe:
    pushq %rbp
    pushq %rbx
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    subq $576, %rsp
    movq %rdi, %r12
    movq %rsi, %r13
    movq %rdx, %r14
    movq %r9, %r15
    movl %ecx, 8(%rsp)
    movl %r8d, 12(%rsp)
    fnstcw 0(%rsp)
    stmxcsr 4(%rsp)
    movzwl 0(%rsp), %eax
    movl %eax, 24(%r15)
    movl 4(%rsp), %eax
    movl %eax, 28(%r15)
    fninit
    fldcw 8(%rsp)
    ldmxcsr 12(%rsp)
    vmovdqu 0(%r14), %ymm0
    vmovdqu 32(%r14), %ymm1
    vmovdqu 64(%r14), %ymm2
    vmovdqu 96(%r14), %ymm3
    vmovdqu 128(%r14), %ymm4
    vmovdqu 160(%r14), %ymm5
    vmovdqu 192(%r14), %ymm6
    vmovdqu 224(%r14), %ymm7
    vmovdqu 256(%r14), %ymm8
    vmovdqu 288(%r14), %ymm9
    vmovdqu 320(%r14), %ymm10
    vmovdqu 352(%r14), %ymm11
    vmovdqu 384(%r14), %ymm12
    vmovdqu 416(%r14), %ymm13
    vmovdqu 448(%r14), %ymm14
    vmovdqu 480(%r14), %ymm15
    xorl %ebp, %ebp
    movl $1, 0(%r12)
.Lready_wait:
    cmpl $0, 8(%r13)
    jne .Lpeer_fail
    cmpl $1, 0(%r13)
    je .Lbegin
    YIELD
    jmp .Lready_wait
.Lbegin:
    movl $1, %ebx
.Lround:
    movl %ebx, 4(%r12)
    YIELD
.Lprogress_wait:
    cmpl $0, 8(%r13)
    jne .Lpeer_fail
    cmpl %ebx, 4(%r13)
    jae .Lcheck
    YIELD
    jmp .Lprogress_wait
.Lcheck:
    vmovdqu %ymm0, 64(%rsp)
    vmovdqu %ymm1, 96(%rsp)
    vmovdqu %ymm2, 128(%rsp)
    vmovdqu %ymm3, 160(%rsp)
    vmovdqu %ymm4, 192(%rsp)
    vmovdqu %ymm5, 224(%rsp)
    vmovdqu %ymm6, 256(%rsp)
    vmovdqu %ymm7, 288(%rsp)
    vmovdqu %ymm8, 320(%rsp)
    vmovdqu %ymm9, 352(%rsp)
    vmovdqu %ymm10, 384(%rsp)
    vmovdqu %ymm11, 416(%rsp)
    vmovdqu %ymm12, 448(%rsp)
    vmovdqu %ymm13, 480(%rsp)
    vmovdqu %ymm14, 512(%rsp)
    vmovdqu %ymm15, 544(%rsp)
    leaq 64(%rsp), %rdi
    movq %r14, %rsi
    movl $64, %ecx
    cld
    repe cmpsq
    jne .Lvector_fail
    fnstcw 16(%rsp)
    movzwl 16(%rsp), %eax
    cmpl 8(%rsp), %eax
    jne .Lcw_fail
    stmxcsr 20(%rsp)
    movl 20(%rsp), %eax
    cmpl 12(%rsp), %eax
    jne .Lmxcsr_fail
    incl 4(%r15)
    movl 4(%r13), %eax
    movl %eax, 8(%r15)
    incl %ebx
    cmpl $64, %ebx
    jbe .Lround
    xorl %ebx, %ebx
    jmp .Lcleanup
.Lvector_fail:
    movl $1, %ebx
    jmp .Lfailed
.Lcw_fail:
    movl $100, %ebx
    jmp .Lfailed
.Lmxcsr_fail:
    movl $101, %ebx
    jmp .Lfailed
.Lsys_fail:
    movq %rax, 40(%r15)
    movl $110, %ebx
    jmp .Lfailed
.Lbudget_fail:
    movl $111, %ebx
    jmp .Lfailed
.Lpeer_fail:
    movl $112, %ebx
.Lfailed:
    movl $1, 8(%r12)
.Lcleanup:
    movl %ebp, 12(%r15)
    vzeroupper
    fninit
    fldcw 0(%rsp)
    ldmxcsr 4(%rsp)
    fnstcw 16(%rsp)
    stmxcsr 20(%rsp)
    movzwl 16(%rsp), %eax
    movl %eax, 32(%r15)
    cmpw 0(%rsp), %ax
    jne .Lrestore_fail
    movl 20(%rsp), %eax
    movl %eax, 36(%r15)
    cmpl 4(%rsp), %eax
    jne .Lrestore_fail
    movl $1, 16(%r15)
    jmp .Lreturn
.Lrestore_fail:
    movl $120, %ebx
    movl $1, 8(%r12)
.Lreturn:
    movl %ebx, 0(%r15)
    movl %ebx, %eax
    addq $576, %rsp
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbx
    popq %rbp
    ret
.size fp_state_probe,.-fp_state_probe
.section .note.GNU-stack,"",@progbits
