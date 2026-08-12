/* SPDX-License-Identifier: GPL-2.0-only */
/* Minimal x86_64 initramfs poweroff helper: no libc or project module input. */

	.section .text
	.global _start
	.type _start, @function
_start:
	mov $162, %rax                  /* __NR_sync */
	syscall
	mov $169, %rax                  /* __NR_reboot */
	mov $0xfee1dead, %rdi           /* LINUX_REBOOT_MAGIC1 */
	mov $0x28121969, %rsi           /* LINUX_REBOOT_MAGIC2 */
	mov $0x4321fedc, %rdx           /* LINUX_REBOOT_CMD_POWER_OFF */
	xor %r10, %r10
	syscall
	mov $60, %rax                   /* __NR_exit: reboot must not return */
	mov $1, %rdi
	syscall
	.size _start, .-_start

	.section .note.GNU-stack,"",@progbits
