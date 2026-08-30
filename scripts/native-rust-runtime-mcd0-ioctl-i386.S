/* SPDX-License-Identifier: GPL-2.0-only */
/* Freestanding i386 compat mcd0 negative-ioctl runtime probe. */

	.section .rodata
mcd0_path:
	.asciz "/dev/mcd0"

	.section .text
	.globl _start
	.type _start, @function
_start:
	mov $5, %eax			/* __NR_open */
	mov $mcd0_path, %ebx
	mov $2, %ecx			/* O_RDWR */
	xor %edx, %edx
	int $0x80
	test %eax, %eax
	js .Lopen_failed
	mov %eax, %esi

	mov $54, %eax			/* __NR_ioctl */
	mov %esi, %ebx
	mov $0xdeadbeef, %ecx
	xor %edx, %edx
	int $0x80
	cmp $-22, %eax			/* -EINVAL */
	jne .Lioctl_failed

	mov $6, %eax			/* __NR_close */
	mov %esi, %ebx
	int $0x80
	test %eax, %eax
	js .Lclose_failed
	xor %ebx, %ebx
	jmp .Lexit

.Lioctl_failed:
	mov $6, %eax
	mov %esi, %ebx
	int $0x80
	mov $11, %ebx
	jmp .Lexit
.Lopen_failed:
	mov $10, %ebx
	jmp .Lexit
.Lclose_failed:
	mov $12, %ebx
.Lexit:
	mov $1, %eax			/* __NR_exit */
	int $0x80
	.size _start, .-_start
	.section .note.GNU-stack,"",@progbits
