/* SPDX-License-Identifier: GPL-2.0-only */
/* Freestanding x86_64 mcd0 negative-ioctl runtime probe. */

	.section .rodata
mcd0_path:
	.asciz "/dev/mcd0"

	.section .text
	.globl _start
	.type _start, @function
_start:
	mov $2, %eax			/* __NR_open */
	lea mcd0_path(%rip), %rdi
	mov $2, %esi			/* O_RDWR */
	xor %edx, %edx
	syscall
	test %rax, %rax
	js .Lopen_failed
	mov %rax, %r12

	mov $16, %eax			/* __NR_ioctl */
	mov %r12, %rdi
	mov $0xdeadbeef, %esi
	xor %edx, %edx
	syscall
	cmp $-22, %rax			/* -EINVAL */
	jne .Lioctl_failed

	mov $3, %eax			/* __NR_close */
	mov %r12, %rdi
	syscall
	test %rax, %rax
	js .Lclose_failed
	xor %edi, %edi
	jmp .Lexit

.Lioctl_failed:
	mov $3, %eax
	mov %r12, %rdi
	syscall
	mov $11, %edi
	jmp .Lexit
.Lopen_failed:
	mov $10, %edi
	jmp .Lexit
.Lclose_failed:
	mov $12, %edi
.Lexit:
	mov $60, %eax			/* __NR_exit */
	syscall
	.size _start, .-_start
	.section .note.GNU-stack,"",@progbits
