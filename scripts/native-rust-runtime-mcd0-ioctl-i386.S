/* SPDX-License-Identifier: GPL-2.0-only */
/* Freestanding i386 compat mcd0 GET_BUILDID, unbooted OS lifecycle and error-boundary probe.
 * argv[1] is the exact stage-lock IHK compatibility identity, without NUL.
 * Exit: 10 open, 11 ioctl/copy/guard/setup, 12 close, 13 bad expected identity.
 */

	.section .rodata
mcd0_path:
	.asciz "/dev/mcd0"
mcos0_path:
	.asciz "/dev/mcos0"
smp_module_name:
	.asciz "ihk_smp_x86_64"

	.section .text
	.globl _start
	.type _start, @function
_start:
	mov $mcd0_path, %ebp
	cmpl $2, (%esp)
	jne .Largument_failed
	mov 8(%esp), %esi
	xor %ecx, %ecx
.Lidentity_length:
	cmpb $0, (%esi,%ecx)
	je .Lidentity_end
	inc %ecx
	cmp $40, %ecx
	ja .Largument_failed
	jmp .Lidentity_length
.Lidentity_end:
	test %ecx, %ecx
	jz .Largument_failed
	inc %ecx			/* Exact payload includes terminating NUL. */
	/* fd, mapping, expected, length, result, then guarded buffer at +32. */
	sub $96, %esp
	mov %esi, 8(%esp)
	mov %ecx, 12(%esp)
	movl $0, 4(%esp)
	mov $5, %eax			/* __NR_open */
	mov %ebp, %ebx
	mov $2, %ecx			/* O_RDWR */
	xor %edx, %edx
	int $0x80
	test %eax, %eax
	js .Lopen_failed
	mov %eax, (%esp)

	lea 32(%esp), %edi
	mov $64, %ecx
	mov $0xa5, %eax
	cld
	rep stosb
	mov $54, %eax			/* __NR_ioctl */
	mov (%esp), %ebx
	mov $0x11290b, %ecx		/* IHK_DEVICE_GET_BUILDID */
	lea 40(%esp), %edx
	int $0x80
	test %eax, %eax
	jne .Lioctl_failed
	cmpl $0xa5a5a5a5, 32(%esp)
	jne .Lioctl_failed
	cmpl $0xa5a5a5a5, 36(%esp)
	jne .Lioctl_failed
	mov 8(%esp), %esi
	lea 40(%esp), %edi
	mov 12(%esp), %ecx
	repe cmpsb
	jne .Lioctl_failed
	mov $56, %ecx
	sub 12(%esp), %ecx
	mov $0xa5, %eax
	repe scasb
	jne .Lioctl_failed

	/* NULL and out-of-range compat pointers must fail. */
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x11290b, %ecx
	xor %edx, %edx
	int $0x80
	cmp $-14, %eax			/* -EFAULT */
	jne .Lioctl_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x11290b, %ecx
	mov $-1, %edx
	int $0x80
	cmp $-14, %eax
	jne .Lioctl_failed

	/* The separately mapped read-only path must remain unchanged. */
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x11290b, %ecx
	mov %ebp, %edx
	int $0x80
	cmp $-14, %eax
	jne .Lioctl_failed
	cmpl $0x7665642f, (%ebp)
	jne .Lioctl_failed
	cmpl $0x64636d2f, 4(%ebp)
	jne .Lioctl_failed
	cmpw $0x0030, 8(%ebp)
	jne .Lioctl_failed

	mov $192, %eax			/* __NR_mmap2 */
	xor %ebx, %ebx
	mov $8192, %ecx
	mov $3, %edx			/* PROT_READ | PROT_WRITE */
	mov $0x22, %esi			/* MAP_PRIVATE | MAP_ANONYMOUS */
	mov $-1, %edi
	push %ebp
	xor %ebp, %ebp			/* pgoffset */
	int $0x80
	pop %ebp
	cmp $-4095, %eax
	jae .Lioctl_failed
	mov %eax, 4(%esp)
	movl $0xa5a5a5a5, 4091(%eax)
	movb $0xa5, 4095(%eax)
	lea 4096(%eax), %ebx
	mov $125, %eax			/* __NR_mprotect */
	mov $4096, %ecx
	xor %edx, %edx			/* PROT_NONE */
	int $0x80
	test %eax, %eax
	jne .Lioctl_failed
	mov 4(%esp), %edx
	add $4095, %edx
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x11290b, %ecx
	int $0x80
	cmp $-14, %eax
	jne .Lioctl_failed
	/* Do not assume a fixed written prefix for a failed usercopy. */
	mov 4(%esp), %edx
	cmpl $0xa5a5a5a5, 4091(%edx)
	jne .Lioctl_failed
	lea 4096(%edx), %ebx
	mov $125, %eax
	mov $4096, %ecx
	mov $1, %edx			/* PROT_READ: inspect previously protected bytes. */
	int $0x80
	test %eax, %eax
	jne .Lioctl_failed
	mov 4(%esp), %edi
	add $4096, %edi
	mov $4096, %ecx
	xor %eax, %eax
	repe scasb
	jne .Lioctl_failed

	mov $54, %eax
	mov (%esp), %ebx
	mov $0xdeadbeef, %ecx
	xor %edx, %edx
	int $0x80
	cmp $-22, %eax			/* -EINVAL */
	jne .Lioctl_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0xdeadbeef, %ecx
	mov $-1, %edx
	int $0x80
	cmp $-22, %eax
	jne .Lioctl_failed

	/* Create distinct unbooted instances; scalar create arguments are ignored. */
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112900, %ecx
	mov $-1, %edx
	int $0x80
	cmp $0, %eax
	jne .Lioctl_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112900, %ecx
	mov $0, %edx
	int $0x80
	cmp $1, %eax
	jne .Lioctl_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112901, %ecx
	mov $1, %edx
	int $0x80
	cmp $0, %eax
	jne .Lioctl_failed

	/* An instance pins SMP even with every control and OS file closed. */
	mov $6, %eax
	mov (%esp), %ebx
	int $0x80
	test %eax, %eax
	jne .Lclose_failed
	movl $-1, (%esp)
	mov $129, %eax
	lea 21(%ebp), %ebx
	mov $0x800, %ecx
	int $0x80
	cmp $-11, %eax			/* -EWOULDBLOCK, Linux live-reference refusal. */
	jne .Lioctl_failed
	mov $5, %eax
	lea 0(%ebp), %ebx
	mov $2, %ecx
	xor %edx, %edx
	int $0x80
	test %eax, %eax
	js .Lioctl_failed
	mov %eax, (%esp)

	/* Two independent opens keep destruction busy until the final release. */
	mov $5, %eax
	lea 10(%ebp), %ebx
	mov $2, %ecx
	xor %edx, %edx
	int $0x80
	test %eax, %eax
	js .Lioctl_failed
	mov %eax, 20(%esp)
	mov $5, %eax
	lea 10(%ebp), %ebx
	mov $2, %ecx
	xor %edx, %edx
	int $0x80
	test %eax, %eax
	js .Lioctl_failed
	mov %eax, 24(%esp)
	mov $54, %eax
	mov 20(%esp), %ebx
	mov $0x112a03, %ecx
	mov $-1, %edx
	int $0x80
	cmp $0, %eax
	jne .Lioctl_failed
	mov $54, %eax
	mov 24(%esp), %ebx
	mov $0x112a14, %ecx
	mov $0, %edx
	int $0x80
	cmp $0, %eax
	jne .Lioctl_failed
	mov $54, %eax
	mov 20(%esp), %ebx
	mov $0x112a02, %ecx
	mov $0, %edx
	int $0x80
	cmp $-22, %eax
	jne .Lioctl_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112901, %ecx
	mov $0, %edx
	int $0x80
	cmp $-16, %eax
	jne .Lioctl_failed
	mov $6, %eax
	mov 20(%esp), %ebx
	int $0x80
	test %eax, %eax
	jne .Lclose_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112901, %ecx
	mov $0, %edx
	int $0x80
	cmp $-16, %eax
	jne .Lioctl_failed
	mov $6, %eax
	mov 24(%esp), %ebx
	int $0x80
	test %eax, %eax
	jne .Lclose_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112901, %ecx
	mov $0, %edx
	int $0x80
	cmp $0, %eax
	jne .Lioctl_failed

	/* Dead/invalid minors fail, the node disappears, and zero can be reused. */
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112901, %ecx
	mov $0, %edx
	int $0x80
	cmp $-22, %eax
	jne .Lioctl_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112901, %ecx
	mov $64, %edx
	int $0x80
	cmp $-22, %eax
	jne .Lioctl_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112901, %ecx
	mov $-1, %edx
	int $0x80
	cmp $-22, %eax
	jne .Lioctl_failed
	mov $5, %eax
	lea 10(%ebp), %ebx
	mov $2, %ecx
	xor %edx, %edx
	int $0x80
	cmp $-2, %eax
	jne .Lioctl_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112900, %ecx
	mov $0, %edx
	int $0x80
	cmp $0, %eax
	jne .Lioctl_failed
	mov $54, %eax
	mov (%esp), %ebx
	mov $0x112901, %ecx
	mov $0, %edx
	int $0x80
	cmp $0, %eax
	jne .Lioctl_failed

	movl $0, 16(%esp)
	jmp .Lclose_device

.Lioctl_failed:
	movl $11, 16(%esp)
.Lclose_device:
	mov 4(%esp), %ebx
	test %ebx, %ebx
	jz .Lclose_fd
	mov $91, %eax			/* __NR_munmap */
	mov $8192, %ecx
	int $0x80
	test %eax, %eax
	jz .Lclose_fd
	movl $11, 16(%esp)
.Lclose_fd:
	mov 16(%esp), %ebx
	cmpl $0, (%esp)
	js .Lexit
	mov $6, %eax			/* __NR_close */
	mov (%esp), %ebx
	int $0x80
	test %eax, %eax
	js .Lclose_failed
	mov 16(%esp), %ebx
	jmp .Lexit
.Lopen_failed:
	mov $10, %ebx
	jmp .Lexit
.Lclose_failed:
	mov $12, %ebx
	jmp .Lexit
.Largument_failed:
	mov $13, %ebx
.Lexit:
	mov $1, %eax			/* __NR_exit */
	int $0x80
	.size _start, .-_start
	.section .note.GNU-stack,"",@progbits
