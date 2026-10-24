/**
 * \file context.h
 *  License details are found in the file LICENSE.
 * \brief
 *  Define types of registers consisting of context.
 *  Define macros to retrieve arguments of system call.
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 */
/*
 * HISTORY
 */

#ifndef __HEADER_X86_COMMON_CONTEXT_H
#define __HEADER_X86_COMMON_CONTEXT_H

#include <registers.h>

struct x86_kregs {
	unsigned long rsp, rbp, rbx, rsi, rdi, r12, r13, r14, r15, rflags;
	unsigned long rsp0;
};

typedef struct x86_kregs ihk_mc_kernel_context_t;

/* XXX: User context should contain floating point registers */
struct x86_user_context {
	struct x86_sregs sr;

	/* 16-byte boundary here */
	uint8_t is_gpr_valid;
	uint8_t is_sr_valid;
	uint8_t spare_flags6;
	uint8_t spare_flags5;
	uint8_t spare_flags4;
	uint8_t spare_flags3;
	uint8_t spare_flags2;
	uint8_t spare_flags1;
	struct x86_basic_regs gpr;	/* must be last */
	/* 16-byte boundary here */
};
typedef struct x86_user_context ihk_mc_user_context_t;

unsigned long ihk_mc_syscall_arg0(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg1(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg2(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg3(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg4(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg5(const ihk_mc_user_context_t *uc);

void ihk_mc_syscall_set_arg0(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg1(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg2(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg3(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg4(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg5(ihk_mc_user_context_t *uc, unsigned long value);

unsigned long ihk_mc_syscall_ret(const ihk_mc_user_context_t *uc);
void ihk_mc_syscall_set_ret(ihk_mc_user_context_t *uc, unsigned long value);
unsigned long ihk_mc_syscall_number(const ihk_mc_user_context_t *uc);

unsigned long ihk_mc_syscall_pc(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_sp(const ihk_mc_user_context_t *uc);

#endif
