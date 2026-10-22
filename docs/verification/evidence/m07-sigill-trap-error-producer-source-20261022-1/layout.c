#define _GNU_SOURCE
#define MCKERNEL_NATIVE_SIGNAL_STACK
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <signal.h>
#include <ucontext.h>
struct x86_basic_regs {
	unsigned long r15;
	unsigned long r14;
	unsigned long r13;
	unsigned long r12;
	unsigned long rbp;
	unsigned long rbx;
	unsigned long r11;
	unsigned long r10;
	unsigned long r9;
	unsigned long r8;
	unsigned long rax;
	unsigned long rcx;
	unsigned long rdx;
	unsigned long rsi;
	unsigned long rdi;
	union {
		unsigned long orig_rax; /* syscall */
		unsigned long error;    /* interrupts */
	};
	unsigned long rip;
	unsigned long cs;
	unsigned long rflags;
	unsigned long rsp;
	unsigned long ss;
};
struct x86_sregs {
	unsigned long fs_base;
	unsigned long gs_base;
	unsigned long ds;
	unsigned long es;
	unsigned long fs;
	unsigned long gs;
};
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
struct sigsp {
	unsigned long flags;
	void *link;
	stack_t sigstack;
	unsigned long regs[23];
#define _r8 regs[0] 
#define _r9 regs[1] 
#define _r10 regs[2] 
#define _r11 regs[3] 
#define _r12 regs[4] 
#define _r13 regs[5] 
#define _r14 regs[6] 
#define _r15 regs[7] 
#define _rdi regs[8] 
#define _rsi regs[9] 
#define _rbp regs[10] 
#define _rbx regs[11] 
#define _rdx regs[12] 
#define _rax regs[13] 
#define _rcx regs[14] 
#define _rsp regs[15] 
#define _rip regs[16] 
#define _rflags regs[17] 
#define _csgsfs regs[18] 
#define _error regs[19] 
#define _trapno regs[20] 
#define _oldmask regs[21] 
#define _cr2 regs[22] 
	void *fpregs;
	unsigned long reserve[8];

#ifdef MCKERNEL_NATIVE_SIGNAL_STACK
	/* libc ucontext_t reserves 128 bytes even though the kernel has 64 signals. */
	unsigned long sigmask[16];
#else
	unsigned long sigrc;
	unsigned long sigmask;
	int num;
	int restart;
	unsigned long ss;
#endif
	siginfo_t info;
};
_Static_assert(offsetof(struct x86_user_context,spare_flags6)==50,"marker byte");
_Static_assert(offsetof(struct x86_user_context,spare_flags5)==51,"vector byte");
_Static_assert(sizeof(struct x86_user_context)==224,"no kernel ABI expansion");
_Static_assert(offsetof(struct sigsp,regs)+19*8==offsetof(ucontext_t,uc_mcontext.gregs)+REG_ERR*8,"REG_ERR");
_Static_assert(offsetof(struct sigsp,regs)+20*8==offsetof(ucontext_t,uc_mcontext.gregs)+REG_TRAPNO*8,"REG_TRAPNO");
int main(void){printf("actual C kernel declarations/libc layout PASS: context=%zu marker=%zu/%zu REG_ERR=%zu REG_TRAPNO=%zu\n",sizeof(struct x86_user_context),offsetof(struct x86_user_context,spare_flags6),offsetof(struct x86_user_context,spare_flags5),offsetof(ucontext_t,uc_mcontext.gregs)+REG_ERR*8,offsetof(ucontext_t,uc_mcontext.gregs)+REG_TRAPNO*8);return 0;}
