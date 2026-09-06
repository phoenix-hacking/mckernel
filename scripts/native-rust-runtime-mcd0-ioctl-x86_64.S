/* SPDX-License-Identifier: GPL-2.0-only */
/* Freestanding x86_64 mcd0 GET_BUILDID and error-boundary runtime probe.
 * argv[1] is the exact stage-lock IHK compatibility identity, without NUL.
 * Exit: 10 open, 11 ioctl/copy/guard/setup, 12 close, 13 bad expected identity.
 */

	.section .rodata
mcd0_path:
	.asciz "/dev/mcd0"

	.section .text
	.globl _start
	.type _start, @function
_start:
	lea mcd0_path(%rip), %rbp
	cmpq $2, (%rsp)
	jne .Largument_failed
	mov 16(%rsp), %r14
	xor %r15d, %r15d
.Lidentity_length:
	cmpb $0, (%r14,%r15)
	je .Lidentity_end
	inc %r15d
	cmp $40, %r15d
	ja .Largument_failed
	jmp .Lidentity_length
.Lidentity_end:
	test %r15d, %r15d
	jz .Largument_failed
	inc %r15d			/* Exact payload includes terminating NUL. */
	sub $64, %rsp
	xor %ebx, %ebx			/* No anonymous mapping yet. */
	mov $2, %eax			/* __NR_open */
	mov %rbp, %rdi
	mov $2, %esi			/* O_RDWR */
	xor %edx, %edx
	syscall
	test %rax, %rax
	js .Lopen_failed
	mov %rax, %r12

	/* The complete buffer starts as canaries; data begins after eight. */
	mov %rsp, %rdi
	mov $64, %ecx
	mov $0xa5, %eax
	cld
	rep stosb
	mov $16, %eax			/* __NR_ioctl */
	mov %r12, %rdi
	mov $0x11290b, %esi		/* IHK_DEVICE_GET_BUILDID */
	lea 8(%rsp), %rdx
	syscall
	test %rax, %rax
	jne .Lioctl_failed
	cmpl $0xa5a5a5a5, (%rsp)
	jne .Lioctl_failed
	cmpl $0xa5a5a5a5, 4(%rsp)
	jne .Lioctl_failed
	mov %r14, %rsi
	lea 8(%rsp), %rdi
	mov %r15d, %ecx
	repe cmpsb
	jne .Lioctl_failed
	mov $56, %ecx
	sub %r15d, %ecx
	mov $0xa5, %eax
	repe scasb
	jne .Lioctl_failed

	/* NULL and out-of-range pointers must fail without a kernel fault. */
	mov $16, %eax
	mov %r12, %rdi
	mov $0x11290b, %esi
	xor %edx, %edx
	syscall
	cmp $-14, %rax			/* -EFAULT */
	jne .Lioctl_failed
	mov $16, %eax
	mov %r12, %rdi
	mov $0x11290b, %esi
	mov $-1, %rdx
	syscall
	cmp $-14, %rax
	jne .Lioctl_failed

	/* The separately mapped read-only path must remain unchanged. */
	mov $16, %eax
	mov %r12, %rdi
	mov $0x11290b, %esi
	mov %rbp, %rdx
	syscall
	cmp $-14, %rax
	jne .Lioctl_failed
	cmpl $0x7665642f, (%rbp)
	jne .Lioctl_failed
	cmpl $0x64636d2f, 4(%rbp)
	jne .Lioctl_failed
	cmpw $0x0030, 8(%rbp)
	jne .Lioctl_failed

	/* Anonymous pages start zero; protect the second from any access. */
	mov $9, %eax			/* __NR_mmap */
	xor %edi, %edi
	mov $8192, %esi
	mov $3, %edx			/* PROT_READ | PROT_WRITE */
	mov $0x22, %r10d			/* MAP_PRIVATE | MAP_ANONYMOUS */
	mov $-1, %r8
	xor %r9d, %r9d
	syscall
	cmp $-4095, %rax
	jae .Lioctl_failed
	mov %rax, %rbx
	movl $0xa5a5a5a5, 4091(%rbx)
	movb $0xa5, 4095(%rbx)
	mov $10, %eax			/* __NR_mprotect */
	lea 4096(%rbx), %rdi
	mov $4096, %esi
	xor %edx, %edx			/* PROT_NONE */
	syscall
	test %rax, %rax
	jne .Lioctl_failed
	mov $16, %eax
	mov %r12, %rdi
	mov $0x11290b, %esi
	lea 4095(%rbx), %rdx
	syscall
	cmp $-14, %rax
	jne .Lioctl_failed
	/* A failed usercopy may modify an unspecified accessible prefix. */
	cmpl $0xa5a5a5a5, 4091(%rbx)
	jne .Lioctl_failed
	mov $10, %eax
	lea 4096(%rbx), %rdi
	mov $4096, %esi
	mov $1, %edx			/* PROT_READ: inspect previously protected bytes. */
	syscall
	test %rax, %rax
	jne .Lioctl_failed
	lea 4096(%rbx), %rdi
	mov $4096, %ecx
	xor %eax, %eax
	repe scasb
	jne .Lioctl_failed

	/* Unknown requests retain EINVAL, independent of their argument. */
	mov $16, %eax
	mov %r12, %rdi
	mov $0xdeadbeef, %esi
	xor %edx, %edx
	syscall
	cmp $-22, %rax			/* -EINVAL */
	jne .Lioctl_failed
	mov $16, %eax
	mov %r12, %rdi
	mov $0xdeadbeef, %esi
	mov $-1, %rdx
	syscall
	cmp $-22, %rax
	jne .Lioctl_failed
	xor %r13d, %r13d
	jmp .Lclose_device

.Lioctl_failed:
	mov $11, %r13d
.Lclose_device:
	test %rbx, %rbx
	jz .Lclose_fd
	mov $11, %eax			/* __NR_munmap */
	mov %rbx, %rdi
	mov $8192, %esi
	syscall
	test %rax, %rax
	jz .Lclose_fd
	mov $11, %r13d
.Lclose_fd:
	mov $3, %eax			/* __NR_close */
	mov %r12, %rdi
	syscall
	test %rax, %rax
	js .Lclose_failed
	mov %r13d, %edi
	jmp .Lexit
.Lopen_failed:
	mov $10, %edi
	jmp .Lexit
.Lclose_failed:
	mov $12, %edi
	jmp .Lexit
.Largument_failed:
	mov $13, %edi
.Lexit:
	mov $60, %eax			/* __NR_exit */
	syscall
	.size _start, .-_start
	.section .note.GNU-stack,"",@progbits
