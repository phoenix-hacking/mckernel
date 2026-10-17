/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Adapted from pinned IHK smp-x86_64-trampoline.S. Instruction body retained. */
.equ EFER_LME, 0x100
/*
 * Kloader transition code:
 */

.equ BOOT_CS, 0x10
.equ BOOT_DS, 0x18
.equ BOOT_CS64, 0x20
.equ KERN_PAGE_MID, 0x63
.equ KERN_PAGE, 0x0e3
.equ MSR_EFER, 0xc0000080
.pushsection .rodata.mckernel_smp_trampoline, "a", @progbits
.balign 8
.code16

.globl mckernel_smp_trampoline_data
mckernel_trampoline_base = .
mckernel_smp_trampoline_data:
	jmp	mckernel_trampoline_cpu_start_body

	.org	8
mckernel_trampoline_header_pgtbl:
	.quad	0		/* page table address */
mckernel_trampoline_header_load:	
	.quad	0		/* load address */
mckernel_trampoline_stack_ptr:
	.quad	0		/* initial mckernel_trampoline_stack */
mckernel_trampoline_notify_address:
	.quad	0		/* where to notify? */

mckernel_trampoline_cpu_start_body:	
	cli
	wbinvd

	movw	%cs, %ax
	movw	%ax, %ds
	movw	%ax, %es
	movw	%ax, %ss

	xorl	%ebx, %ebx
	movw	%cs, %bx
	shll	$4, %ebx

	/* Adjust GDT ptr to the 32-bit physical address */
	addl	%ebx, mckernel_trampoline_boot_gdtptr + 2 - mckernel_trampoline_base
	addl	%ebx, 2f - mckernel_trampoline_base
	addl	%ebx, mckernel_trampoline_start_64_vec - mckernel_trampoline_base
	
	lgdtl	mckernel_trampoline_boot_gdtptr - mckernel_trampoline_base
	lidtl	mckernel_trampoline_boot_idtptr - mckernel_trampoline_base

	jmp	1f
1:	
	
	movl	%cr0, %edx
	orb	$1, %dl
	movl	%edx, %cr0

	ljmpl	*(2f - mckernel_trampoline_base)
2:	.long	mckernel_trampoline_protect_start - mckernel_trampoline_base
	.word	BOOT_CS

.balign  8
.code32
mckernel_trampoline_protect_start:
	movl	$(BOOT_DS), %eax
	movl	%eax, %ds
	movl	%eax, %ss

	/* Enable PAE */
	movl	%cr4, %eax
	orl	$0x20, %eax
	movl	%eax, %cr4

	leal	(mckernel_trampoline_stack_end - mckernel_trampoline_base)(%ebx), %esp
	
	/* Load a page table */
	movl	(mckernel_trampoline_header_pgtbl - mckernel_trampoline_base)(%ebx), %eax
	movl	%eax, %cr3
	
	movl	(mckernel_trampoline_header_load - mckernel_trampoline_base)(%ebx), %ecx
	movl	(mckernel_trampoline_stack_ptr - mckernel_trampoline_base)(%ebx), %eax
	jz	1f
	movl	%eax, %esp
1:

	/* Enable Long Mode */
	movl	$MSR_EFER, %ecx
	movl	$EFER_LME, %eax
	xorl	%edx, %edx
	wrmsr

	/* Enable Paging */
	movl	%cr0, %edx
	orl	$0x80000000, %edx
	movl	%edx, %cr0

	ljmp	*(mckernel_trampoline_start_64_vec - mckernel_trampoline_base)(%ebx)
	
.code64
.balign 8
mckernel_trampoline_start_64:
	/* Okay, we are completely in the long mode ! */
	movq	%cr3, %rax
	movq	%rax, %cr3

	movq	(mckernel_trampoline_header_load - mckernel_trampoline_base)(%ebx), %rcx
	cmpq	$0, %rcx
	/* If Loading IP is zero, just enter the infinite loop */
	jz	2f

	movq	(mckernel_trampoline_stack_ptr - mckernel_trampoline_base)(%ebx), %rax
	jz	1f
	movq	%rax, %rsp
1:
	/* Now, we prepare the parameters */
	movq	(mckernel_trampoline_notify_address - mckernel_trampoline_base)(%ebx), %rdi
	jmp	*%rcx

2:
	movq	$2, 0(%rax)
3:	
	cli
	hlt
	jmp	3b

mckernel_trampoline_boot_idtptr:
	.short	0
	.long	0
	
mckernel_trampoline_boot_gdtptr:
	.short	mckernel_trampoline_boot_gdt32_end - mckernel_trampoline_boot_gdt32
	.long	mckernel_trampoline_boot_gdt32 - mckernel_trampoline_base
	.align	4
mckernel_trampoline_boot_gdt32:
	.quad	0
	.quad	0
	.quad	0x00cf9b000000ffff
	.quad	0x00cf93000000ffff
	.quad   0x00af9b000000ffff
	.quad	0x0000890000000067
mckernel_trampoline_boot_gdt32_end:

mckernel_trampoline_start_64_vec:
	.long   mckernel_trampoline_start_64 - mckernel_trampoline_base
	.word   BOOT_CS64, 0
	
mckernel_trampoline_stack:
	.org	0x1000
mckernel_trampoline_stack_end:
.globl mckernel_smp_trampoline_end
mckernel_smp_trampoline_end:
.code64
.popsection
