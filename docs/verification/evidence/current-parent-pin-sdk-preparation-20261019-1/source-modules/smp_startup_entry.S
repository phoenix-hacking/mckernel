/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Adapted from pinned IHK smp-x86_64-startup.S. Instruction body retained. */
.pushsection .rodata.mckernel_smp_startup, "a", @progbits
.balign 8
.code64
/**
 * \file startup.S
 * \brief
 *	IHK BUILTIN Driver: startup routine
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 * Copyright (C) 2011-2012 Taku Shimosawa <shimosawa@is.s.u-tokyo.ac.jp>
 */

.globl mckernel_smp_startup_data
mckernel_smp_startup_data:
	leaq	0(%rip),%rbx
mckernel_startup_base:
	jmp	mckernel_startup_startup_body
	.org	16
mckernel_startup_pgtbl:
	.quad	0
mckernel_startup_stack:
	.quad	0
mckernel_startup_arg2:
	.quad	0
mckernel_startup_trampoline:
	.quad	0
mckernel_startup_next_rip:
	.quad	0
mckernel_startup_startup_body:
	movq	%cr3,%rax
	movq	%rax,%cr3

	movq	(mckernel_startup_pgtbl - mckernel_startup_base)(%rbx),%rax
	movq	%rax,%cr3

	movq	%cr3,%rax
	movq	%rax,%cr3

	movq	(mckernel_startup_stack - mckernel_startup_base)(%rbx),%rax
	movq	%rax,%rsp

	movq	%cr3,%rax
	movq	%rax,%cr3

	movq	(mckernel_startup_arg2 - mckernel_startup_base)(%rbx),%rsi
	movq	(mckernel_startup_trampoline - mckernel_startup_base)(%rbx),%rdx
	
	movq	(mckernel_startup_next_rip - mckernel_startup_base)(%rbx),%r8

	movq	%cr3,%rax
	movq	%rax,%cr3

	jmp	*%r8
.globl mckernel_smp_startup_end
mckernel_smp_startup_end:
.popsection
