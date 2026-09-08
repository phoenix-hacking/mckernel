/* SPDX-License-Identifier: GPL-2.0 */
/* Real ELF application for the unchanged mcexec launcher. No libc dependency.
 * The runner must distinguish Linux reference execution from McKernel execution.
 */
.section .text
.global _start
.type _start, @function
_start:
	mov $39, %eax                  /* getpid */
	syscall
	test %rax, %rax
	jle .Lfailed
	mov $1, %eax                   /* write */
	mov $1, %edi
	lea message(%rip), %rsi
	mov $(message_end - message), %edx
	syscall
	cmp $(message_end - message), %rax
	jne .Lfailed
	mov $37, %edi                  /* recognizable successful exit status */
	jmp .Lexit
.Lfailed:
	mov $1, %edi
.Lexit:
	mov $231, %eax                 /* exit_group */
	syscall
	ud2
.size _start, . - _start

.section .rodata
message:
	.ascii "NATIVE_APPLICATION_HELLO\n"
message_end:

.section .note.GNU-stack,"",@progbits
