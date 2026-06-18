/* cpu.c COPYRIGHT FUJITSU LIMITED 2018-2019 */
/**
 * \file cpu.c
 *  License details are found in the file LICENSE.
 * \brief
 *  Control CPU. 
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2015  RIKEN AICS
 */
/*
 * HISTORY
 *  2015/02/26: bgerofi - set pstate, turbo mode and power/perf bias MSRs
 *  2015/02/12: Dave - enable AVX if supported
 */

#include <ihk/cpu.h>
#include <ihk/mm.h>
#include <types.h>
#include <errno.h>
#include <list.h>
#include <memory.h>
#include <string.h>
#include <registers.h>
#include <cpulocal.h>
#include <march.h>
#include <signal.h>
#include <process.h>
#include <cls.h>
#include <prctl.h>
#include <page.h>
#include <kmalloc.h>
#include <ihk/debug.h>
#include <cas.h>

#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
unsigned long rdtsc(void)
{
	unsigned int high, low;

	asm volatile("rdtsc" : "=a" (low), "=d" (high));

	return (unsigned long)high << 32 | low;
}

unsigned long read_tsc(void)
{
	return rdtsc();
}

void mb(void)
{
	asm volatile("mfence" : : : "memory");
}

void rmb(void)
{
	asm volatile("lfence" : : : "memory");
}

void wmb(void)
{
	asm volatile("sfence" : : : "memory");
}

void smp_mb(void)
{
	mb();
}

void smp_rmb(void)
{
	rmb();
}

void smp_wmb(void)
{
	asm volatile("" : : : "memory");
}

void arch_barrier(void)
{
	asm volatile("" : : : "memory");
}

unsigned long smp_load_acquire_ulong(const unsigned long *p)
{
	unsigned long value = *(const volatile unsigned long *)p;

	asm volatile("" : : : "memory");
	return value;
}

unsigned int smp_load_acquire_uint(const unsigned int *p)
{
	unsigned int value = *(const volatile unsigned int *)p;

	asm volatile("" : : : "memory");
	return value;
}

int smp_load_acquire_int(const int *p)
{
	int value = *(const volatile int *)p;

	asm volatile("" : : : "memory");
	return value;
}

void *smp_load_acquire_ptr(void *const *p)
{
	void *value = *(void *const volatile *)p;

	asm volatile("" : : : "memory");
	return value;
}

void smp_store_release_ulong(unsigned long *p, unsigned long value)
{
	asm volatile("" : : : "memory");
	*(volatile unsigned long *)p = value;
}

void smp_store_release_uint(unsigned int *p, unsigned int value)
{
	asm volatile("" : : : "memory");
	*(volatile unsigned int *)p = value;
}

void smp_store_release_int(int *p, int value)
{
	asm volatile("" : : : "memory");
	*(volatile int *)p = value;
}

unsigned long CVAL(unsigned int event, unsigned int mask)
{
	return (((event & 0xf00UL) << 24) | (mask << 8) | (event & 0xff));
}

unsigned long CVAL2(unsigned int event, unsigned int mask,
		unsigned int inv, unsigned int count)
{
	return CVAL(event, mask) | ((inv & 1) << 23) | ((count & 0xff) << 24);
}

unsigned long xgetbv(unsigned int index)
{
	unsigned int low, high;

	asm volatile("xgetbv" : "=a" (low), "=d" (high) : "c" (index));

	return low | ((unsigned long)high << 32);
}

void xsetbv(unsigned int index, unsigned long val)
{
	unsigned int low, high;

	low = val;
	high = val >> 32;

	asm volatile("xsetbv" : : "a" (low), "d" (high), "c" (index));
}

void wrmsr(unsigned int idx, unsigned long value)
{
	unsigned int high, low;

	high = value >> 32;
	low = value & 0xffffffffU;

	asm volatile("wrmsr" : : "c" (idx), "a" (low), "d" (high) : "memory");
}

unsigned long rdpmc(unsigned int counter)
{
	unsigned int high, low;

	asm volatile("rdpmc" : "=a" (low), "=d" (high) : "c" (counter));

	return (unsigned long)high << 32 | low;
}

unsigned long rdmsr(unsigned int index)
{
	unsigned int high, low;

	asm volatile("rdmsr" : "=a" (low), "=d" (high) : "c" (index));

	return (unsigned long)high << 32 | low;
}

void ihk_mc_mb(void)
{
	asm volatile("mfence" : : : "memory");
}

unsigned long REGS_GET_STACK_POINTER(const void *regs)
{
	const ihk_mc_user_context_t *uc = regs;

	return uc ? uc->gpr.rsp : 0;
}

unsigned long ihk_mc_syscall_arg0(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.rdi : 0;
}

unsigned long ihk_mc_syscall_arg1(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.rsi : 0;
}

unsigned long ihk_mc_syscall_arg2(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.rdx : 0;
}

unsigned long ihk_mc_syscall_arg3(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.r10 : 0;
}

unsigned long ihk_mc_syscall_arg4(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.r8 : 0;
}

unsigned long ihk_mc_syscall_arg5(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.r9 : 0;
}

void ihk_mc_syscall_set_arg0(ihk_mc_user_context_t *uc, unsigned long value)
{
	if (uc)
		uc->gpr.rdi = value;
}

void ihk_mc_syscall_set_arg1(ihk_mc_user_context_t *uc, unsigned long value)
{
	if (uc)
		uc->gpr.rsi = value;
}

void ihk_mc_syscall_set_arg2(ihk_mc_user_context_t *uc, unsigned long value)
{
	if (uc)
		uc->gpr.rdx = value;
}

void ihk_mc_syscall_set_arg3(ihk_mc_user_context_t *uc, unsigned long value)
{
	if (uc)
		uc->gpr.r10 = value;
}

void ihk_mc_syscall_set_arg4(ihk_mc_user_context_t *uc, unsigned long value)
{
	if (uc)
		uc->gpr.r8 = value;
}

void ihk_mc_syscall_set_arg5(ihk_mc_user_context_t *uc, unsigned long value)
{
	if (uc)
		uc->gpr.r9 = value;
}

unsigned long ihk_mc_syscall_ret(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.rax : 0;
}

void ihk_mc_syscall_set_ret(ihk_mc_user_context_t *uc, unsigned long value)
{
	if (uc)
		uc->gpr.rax = value;
}

unsigned long ihk_mc_syscall_number(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.orig_rax : 0;
}

unsigned long ihk_mc_syscall_pc(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.rip : 0;
}

unsigned long ihk_mc_syscall_sp(const ihk_mc_user_context_t *uc)
{
	return uc ? uc->gpr.rsp : 0;
}
#endif

#define LAPIC_ID            0x020
#define LAPIC_TIMER         0x320
#define LAPIC_LVTPC         0x340
#define LAPIC_TIMER_INITIAL 0x380
#define LAPIC_TIMER_CURRENT 0x390
#define LAPIC_TIMER_DIVIDE  0x3e0
#define LAPIC_SPURIOUS      0x0f0
#define LAPIC_EOI           0x0b0
#define LAPIC_ICR0          0x300
#define LAPIC_ICR2          0x310
#define LAPIC_ESR           0x280
#define LOCAL_TIMER_VECTOR  0xef
#define LOCAL_PERF_VECTOR   0xf0
#define LOCAL_SMP_FUNC_CALL_VECTOR   0xf1

#define APIC_INT_LEVELTRIG      0x08000
#define APIC_INT_ASSERT         0x04000
#define APIC_ICR_BUSY           0x01000
#define APIC_DEST_PHYSICAL      0x00000
#define APIC_DM_FIXED           0x00000
#define APIC_DM_NMI             0x00400
#define APIC_DM_INIT            0x00500
#define APIC_DM_STARTUP         0x00600
#define APIC_DIVISOR            16
#define APIC_LVT_TIMER_PERIODIC (1 << 17)

#define APIC_BASE_MSR		0x800
#define IA32_X2APIC_APICID	0x802
#define IA32_X2APIC_ICR		0x830
#define X2APIC_ENABLE		(1UL << 10)
#define NMI_VECTOR		0x02

//#define DEBUG_PRINT_CPU

#ifdef DEBUG_PRINT_CPU
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

static void *lapic_vp;
static int x2apic;
static void (*lapic_write)(int reg, unsigned int value);
static unsigned int (*lapic_read)(int reg);
static void (*lapic_icr_write)(unsigned int h, unsigned int l);
static void (*lapic_wait_icr_idle)(void);

#ifndef MCKERNEL_RUST_ATOMIC_HELPERS
int ihk_atomic_read(const ihk_atomic_t *v)
{
	return (*(volatile int *)&(v)->counter);
}

void ihk_atomic_set(ihk_atomic_t *v, int i)
{
	v->counter = i;
}

void ihk_atomic_add(int i, ihk_atomic_t *v)
{
	asm volatile("lock addl %1,%0"
		     : "+m" (v->counter)
		     : "ir" (i));
}

void ihk_atomic_sub(int i, ihk_atomic_t *v)
{
	asm volatile("lock subl %1,%0"
		     : "+m" (v->counter)
		     : "ir" (i));
}

void ihk_atomic_inc(ihk_atomic_t *v)
{
	asm volatile("lock incl %0"
		     : "+m" (v->counter));
}

void ihk_atomic_dec(ihk_atomic_t *v)
{
	asm volatile("lock decl %0"
		     : "+m" (v->counter));
}

int ihk_atomic_dec_and_test(ihk_atomic_t *v)
{
	unsigned char c;

	asm volatile("lock decl %0; sete %1"
		     : "+m" (v->counter), "=qm" (c)
		     : : "memory");
	return c != 0;
}

int ihk_atomic_inc_and_test(ihk_atomic_t *v)
{
	unsigned char c;

	asm volatile("lock incl %0; sete %1"
		     : "+m" (v->counter), "=qm" (c)
		     : : "memory");
	return c != 0;
}

int ihk_atomic_add_return(int i, ihk_atomic_t *v)
{
	int __i;

	__i = i;
	asm volatile("lock xaddl %0, %1"
		     : "+r" (i), "+m" (v->counter)
		     : : "memory");
	return i + __i;
}

int ihk_atomic_sub_return(int i, ihk_atomic_t *v)
{
	return ihk_atomic_add_return(-i, v);
}

int ihk_atomic_inc_return(ihk_atomic_t *v)
{
	return ihk_atomic_add_return(1, v);
}

int ihk_atomic_dec_return(ihk_atomic_t *v)
{
	return ihk_atomic_sub_return(1, v);
}

long ihk_atomic64_read(const ihk_atomic64_t *v)
{
	return *(volatile long *)&(v)->counter64;
}

void ihk_atomic64_set(ihk_atomic64_t *v, long i)
{
	v->counter64 = i;
}

void ihk_atomic64_inc(ihk_atomic64_t *v)
{
	asm volatile("lock incq %0" : "+m" (v->counter64));
}

long ihk_atomic64_add_return(long i, ihk_atomic64_t *v)
{
	long __i;

	__i = i;
	asm volatile("lock xaddq %0, %1"
		     : "+r" (i), "+m" (v->counter64)
		     : : "memory");
	return i + __i;
}

long ihk_atomic64_sub_return(long i, ihk_atomic64_t *v)
{
	return ihk_atomic64_add_return(-i, v);
}

unsigned long xchg8(unsigned long *ptr, unsigned long x)
{
	unsigned long __x = x;

	asm volatile("xchgq %0,%1"
		     : "=r" (__x)
		     : "m" (*(volatile unsigned long *)(ptr)), "0" (__x)
		     : "memory");
	return __x;
}

int xchg4(int *ptr, int x)
{
	int __x = x;

	asm volatile("xchgl %k0,%1"
		     : "=r" (__x)
		     : "m" (*ptr), "0" (__x)
		     : "memory");
	return __x;
}

unsigned long atomic_xchg_ulong(unsigned long *ptr, unsigned long x)
{
	return xchg8(ptr, x);
}

void *atomic_xchg_ptr(void **ptr, void *x)
{
	return (void *)xchg8((unsigned long *)ptr, (unsigned long)x);
}

unsigned long atomic_cmpxchg8(unsigned long *addr,
		unsigned long oldval, unsigned long newval)
{
	asm volatile("lock; cmpxchgq %2, %1\n"
		     : "=a" (oldval), "+m" (*addr)
		     : "r" (newval), "0" (oldval)
		     : "memory");
	return oldval;
}

unsigned long atomic_cmpxchg4(unsigned int *addr,
		unsigned int oldval, unsigned int newval)
{
	asm volatile("lock; cmpxchgl %2, %1\n"
		     : "=a" (oldval), "+m" (*addr)
		     : "r" (newval), "0" (oldval)
		     : "memory");
	return oldval;
}

int atomic_cmpxchg_int(int *addr, int oldval, int newval)
{
	return (int)atomic_cmpxchg4((unsigned int *)addr,
				    (unsigned int)oldval,
				    (unsigned int)newval);
}

unsigned long atomic_cmpxchg_ulong(unsigned long *addr,
		unsigned long oldval, unsigned long newval)
{
	return atomic_cmpxchg8(addr, oldval, newval);
}

void *atomic_cmpxchg_ptr(void **addr, void *oldval, void *newval)
{
	return (void *)atomic_cmpxchg8((unsigned long *)addr,
				       (unsigned long)oldval,
				       (unsigned long)newval);
}

void ihk_atomic_add_long(long i, long *v)
{
	asm volatile("lock addq %1,%0"
		     : "+m" (*v)
		     : "ir" (i));
}

void ihk_atomic_add_ulong(long i, unsigned long *v)
{
	asm volatile("lock addq %1,%0"
		     : "+m" (*v)
		     : "ir" (i));
}

unsigned long ihk_atomic_add_long_return(long i, long *v)
{
	long __i;

	__i = i;
	asm volatile("lock xaddq %0, %1"
		     : "+r" (i), "+m" (*v)
		     : : "memory");
	return i + __i;
}

int compare_and_swap(void *addr, unsigned long olddata, unsigned long newdata)
{
	unsigned long before;

	asm volatile (
		"lock; cmpxchgq %2,%1"
		: "=a" (before), "+m" (*(unsigned long *)addr)
		: "q" (newdata), "0" (olddata)
		: "cc");
	return before == olddata;
}
#endif
void (*x86_issue_ipi)(unsigned int apicid, unsigned int low);
int running_on_kvm(void);
void smp_func_call_handler(void);
#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
int ihk_mc_get_smp_handler_irq(void)
{
	return LOCAL_SMP_FUNC_CALL_VECTOR;
}
#endif

void init_processors_local(int max_id);
void assign_processor_id(void);
void arch_delay(int);
void x86_set_warm_reset(unsigned long ip, char *first_page_va);
void x86_init_perfctr(void);
int gettime_local_support = 0;

extern int kprintf(const char *format, ...);
extern int interrupt_from_user(void *);
extern void perf_start(struct mc_perf_event *event);
extern void perf_reset(struct mc_perf_event *event);

static struct idt_entry{
	uint32_t desc[4];
} idt[256] __attribute__((aligned(16)));

static struct x86_desc_ptr idt_desc, gdt_desc;

static uint64_t gdt[] __attribute__((aligned(16))) = {
	0,                  /* 0 */
	0,                  /* 8 */
	0,                  /* 16 */
	0,                  /* 24 */
	0x00af9b000000ffff, /* 32 : KERNEL_CS */
	0x00cf93000000ffff, /* 40 : KERNEL_DS */
	0x00affb000000ffff, /* 48 : USER_CS */
	0x00aff3000000ffff, /* 56 : USER_DS */
	0x0000890000000067, /* 64 : TSS */
	0,                  /* (72: TSS) */
	0,                  /* 80 */
	0,                  /* 88 */
	0,                  /* 96 */
	0,                  /* 104 */
	0,                  /* 112 */
	0x0000f10000000000, /* 120 : GETCPU */
};

struct tss64 tss __attribute__((aligned(16)));

static void set_idt_entry(int idx, unsigned long addr)
{
	idt[idx].desc[0] = (addr & 0xffff) | (KERNEL_CS << 16);
	idt[idx].desc[1] = (addr & 0xffff0000) | 0x8e00;
	idt[idx].desc[2] = (addr >> 32);
	idt[idx].desc[3] = 0;
}

static void set_idt_entry_trap_gate(int idx, unsigned long addr)
{
	idt[idx].desc[0] = (addr & 0xffff) | (KERNEL_CS << 16);
	idt[idx].desc[1] = (addr & 0xffff0000) | 0xef00;
	idt[idx].desc[2] = (addr >> 32);
	idt[idx].desc[3] = 0;
}

extern uint64_t generic_common_handlers[];

void reload_idt(void)
{
	asm volatile("lidt %0" : : "m"(idt_desc) : "memory");
}

static struct list_head handlers[256 - 32];
extern char nmi_handler[];
extern char page_fault[], general_protection_exception[];
extern char debug_exception[], int3_exception[];

uint64_t boot_pat_state = 0;
int no_turbo = 1; /* May be updated by early parsing of kargs */

extern int num_processors; /* kernel/ap.c */
struct pvclock_vsyscall_time_info *pvti = NULL;
int pvti_npages;
long pvti_msr = -1;


static void init_idt(void)
{
	int i;

	idt_desc.size = sizeof(idt) - 1;
	idt_desc.address = (unsigned long)idt;
        
	for (i = 0; i < 256; i++) {
		if (i >= 32) {
			INIT_LIST_HEAD(&handlers[i - 32]);
		}
		set_idt_entry(i, generic_common_handlers[i]);
	}

	set_idt_entry(2, (uintptr_t)nmi_handler);
	set_idt_entry(13, (unsigned long)general_protection_exception);
	set_idt_entry(14, (unsigned long)page_fault);

	set_idt_entry_trap_gate(1, (unsigned long)debug_exception);
	set_idt_entry_trap_gate(3, (unsigned long)int3_exception);

	reload_idt();
}

static int xsave_available = 0;
static int xsave_size = 0;
static uint64_t xsave_mask = 0x0;
static unsigned char initial_fp_regs[PAGE_SIZE] __attribute__((aligned(64)));
static int initial_fp_regs_available;

void init_fpu(void)
{
	unsigned long reg;
	unsigned long cpuid01_ecx;

	asm volatile("movq %%cr0, %0" : "=r"(reg));
	/* Unset EM and TS flag. */
	reg &= ~((1 << 2) | (1 << 3));
	/* Set MP flag */
	reg |= 1 << 1;
	asm volatile("movq %0, %%cr0" : : "r"(reg));

#ifdef ENABLE_SSE
	asm volatile("cpuid" : "=c" (cpuid01_ecx) : "a" (0x1) : "%rbx", "%rdx");
	asm volatile("movq %%cr4, %0" : "=r"(reg));
	/* Cr4 flags: 
	   OSFXSR[b9] - enables SSE instructions
	   OSXMMEXCPT[b10] - generate SIMD FP exception instead of invalid op
	   OSXSAVE[b18] - enables access to xcr0

	   CPUID.01H:ECX flags:
	   XSAVE[b26] - verify existence of extended crs/XSAVE
	   AVX[b28] - verify existence of AVX instructions
	*/
	reg |= ((1 << 9) | (1 << 10));
	if(cpuid01_ecx & (1 << 26)) {
		/* XSAVE set, enable access to xcr0 */
		dkprintf("init_fpu(): XSAVE available\n");
		xsave_available = 1;
		reg |= (1 << 18);
	}
	asm volatile("movq %0, %%cr4" : : "r"(reg));

	dkprintf("init_fpu(): SSE init: CR4 = 0x%016lX\n", reg);

	/* Set xcr0[2:1] to enable avx ops */
	if(xsave_available){
		unsigned long eax;
		unsigned long ebx;
		unsigned long ecx;
		unsigned long edx;
		asm volatile("cpuid" : "=a"(eax),"=b"(ebx),"=c"(ecx),"=d"(edx) : "a" (0x0d), "c" (0x00));
		xsave_size = ecx;
		dkprintf("init_fpu(): xsave_size = %d\n", xsave_size);

		if ((eax & (1 << 5)) && (eax & (1 << 6)) && (eax & (1 << 7))) {
			/* Set xcr0[7:5] to enable avx-512 ops */
			reg = xgetbv(0);
			reg |= 0xe6;
			xsetbv(0, reg);
			dkprintf("init_fpu(): AVX-512 init: XCR0 = 0x%016lX\n", reg);
		} else {
			reg = xgetbv(0);
			reg |= 0x6;
			xsetbv(0, reg);
			dkprintf("init_fpu(): AVX init: XCR0 = 0x%016lX\n", reg);
		}

		xsave_mask = xgetbv(0);
		dkprintf("init_fpu(): xsave_mask = 0x%016lX\n", xsave_mask);
	}

	/* TODO: set MSR_IA32_XSS to enable xsaves/xrstors */

#else
	kprintf("init_fpu(): SSE not enabled\n");
#endif

	asm volatile("finit");

	if (xsave_available && xsave_size <= sizeof(initial_fp_regs)) {
		unsigned int low = (unsigned int)xsave_mask;
		unsigned int high = (unsigned int)(xsave_mask >> 32);

		memset(initial_fp_regs, 0, sizeof(initial_fp_regs));
		asm volatile("xsave %0" : "=m" (*(fp_regs_struct *)initial_fp_regs)
				: "a" (low), "d" (high) : "memory");
		initial_fp_regs_available = 1;
	}
}

int
get_xsave_size()
{
	return xsave_size;
}

uint64_t get_xsave_mask()
{
	return xsave_mask;
}

void reload_gdt(struct x86_desc_ptr *gdt_ptr)
{
	asm volatile("pushq %1\n"
	             "leaq 1f(%%rip), %%rbx\n"
	             "pushq %%rbx\n"
	             "lgdt %0\n"
	             "lretq\n"
	             "1:\n" : :
	             "m" (*gdt_ptr),
	             "i" (KERNEL_CS) : "rbx");
	asm volatile("movl %0, %%ds" : : "r"(KERNEL_DS));
	asm volatile("movl %0, %%ss" : : "r"(KERNEL_DS));
	/* And, set TSS */
	asm volatile("ltr %0" : : "r"((short)GLOBAL_TSS) : "memory");
}

void init_gdt(void)
{
	register unsigned long stack_pointer asm("rsp");
	unsigned long tss_addr = (unsigned long)&tss;

	memset(&tss, 0, sizeof(tss));
	tss.rsp0 = stack_pointer;
        
	/* 0x89 = Present (8) | Type = 9 (TSS) */
	gdt[GLOBAL_TSS_ENTRY] = (sizeof(tss) - 1) 
		| ((tss_addr & 0xffffff) << 16)
		| (0x89UL << 40) | ((tss_addr & 0xff000000) << 32);
	gdt[GLOBAL_TSS_ENTRY + 1] = (tss_addr >> 32);

	gdt_desc.size = sizeof(gdt) - 1;
	gdt_desc.address = (unsigned long)gdt;
        
	/* Load the new GDT, and set up CS, DS and SS. */
	reload_gdt(&gdt_desc);
}

static void
apic_write(int reg, unsigned int value)
{
	*(volatile unsigned int *)((char *)lapic_vp + reg) = value;
}

static void
x2apic_write(int reg, unsigned int value)
{
	reg >>= 4;
	reg |= APIC_BASE_MSR;
	wrmsr(reg, value);
}

static unsigned int
apic_read(int reg)
{
	return *(volatile unsigned int *)((char *)lapic_vp + reg);
}

static unsigned int
x2apic_read(int reg)
{
	unsigned long value;

	reg >>= 4;
	reg |= APIC_BASE_MSR;
	value = rdmsr(reg);
	return (int)value;
}

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
extern int x86_lapic_timer_enable_body_result(unsigned int clocks,
		void (*write_fn)(int, unsigned int));
extern int x86_lapic_timer_disable_body_result(
		void (*write_fn)(int, unsigned int));
extern int x86_lapic_ack_body_result(
		void (*write_fn)(int, unsigned int));
extern int x86_x2apic_issue_ipi_body_result(unsigned int apicid,
		unsigned int low, void (*mb_fn)(void),
		unsigned long (*disable_save_fn)(void),
		void (*icr_write_fn)(unsigned int, unsigned int),
		void (*restore_fn)(unsigned long));
extern int x86_apic_issue_ipi_body_result(unsigned int apicid,
		unsigned int low, int lapic_icr_id_shift,
		unsigned long (*disable_save_fn)(void),
		void (*wait_idle_fn)(void),
		void (*icr_write_fn)(unsigned int, unsigned int),
		void (*restore_fn)(unsigned long));
extern unsigned long x86_x2apic_enabled_result(unsigned long msr,
		unsigned long enable_bit);
extern int x86_init_lapic_bsp_body_result(unsigned long enabled,
		void (*select_fn)(int));
extern int x86_init_lapic_body_result(int x2apic_enabled, void **lapic_vp_slot,
		int apic_base_msr, unsigned long page_mask,
		unsigned long page_size, unsigned long apic_enable_bit,
		unsigned long (*read_msr_fn)(int),
		void (*write_msr_fn)(int, unsigned long),
		void *(*map_fixed_fn)(unsigned long, unsigned long, int),
		void (*write_fn)(int, unsigned int));
extern int x86_init_pstate_turbo_body_result(int no_turbo,
		int platform_info_msr, int turbo_ratio_msr, int perf_ctl_msr,
		int energy_perf_bias_msr, int (*running_on_kvm_fn)(void),
		void (*cpuid6_fn)(unsigned long *, unsigned long *),
		unsigned long (*read_msr_fn)(int),
		void (*write_msr_fn)(int, unsigned long));
extern int x86_init_pat_body_result(uint64_t *boot_pat_state,
		int cr_pat_msr,
		void (*cpuid_edx_fn)(unsigned long, unsigned long *),
		unsigned long (*read_msr_fn)(int),
		void (*write_msr_fn)(int, unsigned long),
		void (*log_fn)(int));
extern int x86_init_syscall_body_result(int efer_msr, int star_msr,
		int lstar_msr, unsigned long kernel_cs, unsigned long user_cs,
		unsigned long syscall_addr, unsigned long (*read_msr_fn)(int),
		void (*write_msr_fn)(int, unsigned long));
extern int x86_enable_no_execute_body_result(int no_execute_available,
		int efer_msr, unsigned long nxe_bit,
		unsigned long (*read_msr_fn)(int),
		void (*write_msr_fn)(int, unsigned long));
extern int x86_check_no_execute_body_result(int *no_execute_available_slot,
		void (*cpuid_edx_fn)(unsigned long, unsigned long *),
		void (*log_fn)(int, int), void (*enable_ptattr_fn)(void));
extern int x86_init_gettime_support_body_result(
		int *gettime_local_support_slot,
		void (*cpuid_edx_fn)(unsigned long, unsigned long *),
		void (*log_fn)(int));
extern int x86_init_cpu_body_result(
		void (*enable_page_protection_fault_fn)(void),
		void (*enable_no_execute_fn)(void), void (*init_fpu_fn)(void),
		void (*init_lapic_fn)(void), void (*init_syscall_fn)(void),
		void (*init_perfctr_fn)(void), void (*init_pstate_turbo_fn)(void),
		void (*init_pat_fn)(void));
extern int x86_setup_phase1_body_result(void (*disable_interrupt_fn)(void),
		void (*init_idt_fn)(void), void (*init_gdt_fn)(void),
		void (*init_page_table_fn)(void));
extern int x86_setup_phase2_body_result(void (*check_no_execute_fn)(void),
		void (*init_lapic_bsp_fn)(void), void (*init_cpu_fn)(void),
		void (*init_gettime_support_fn)(void), void (*log_fn)(int));
extern int x86_ihk_mc_init_ap_body_result(char **trampoline_va_slot,
		char **first_page_va_slot, unsigned long ap_trampoline,
		unsigned long ap_trampoline_size, unsigned long page_size,
		void *(*map_fixed_fn)(unsigned long, unsigned long, int),
		int (*get_ncpus_fn)(void),
		void (*init_processors_fn)(int),
		void (*assign_processor_id_fn)(void),
		void (*init_smp_processor_fn)(void),
		void (*log_fn)(int, unsigned long));
extern int x86_running_on_kvm_body_result(unsigned long signature_leaf,
		void (*cpuid_fn)(unsigned long, unsigned long *,
			unsigned long *, unsigned long *, unsigned long *));
extern int x86_pvclock_available_body_result(long *pvti_msr_slot,
		unsigned long signature_leaf, unsigned long features_leaf,
		int feature_new_bit, int feature_old_bit, long msr_new,
		long msr_old, void (*cpuid_fn)(unsigned long, unsigned long *,
			unsigned long *, unsigned long *, unsigned long *),
		void (*log_fn)(int));
extern int x86_arch_setup_pvclock_body_result(
		void **pvti_slot, int *pvti_npages_slot, int num_processors,
		unsigned long pvti_entry_size, unsigned long page_size,
		int page_p2align, unsigned long alloc_flag, int pg_kernel,
		char *file, int line, int (*available_fn)(void),
		void *(*alloc_fn)(int, int, unsigned long, int, int,
			unsigned long, char *, int),
		void (*log_fn)(int));
extern int x86_arch_start_pvclock_body_result(
		void *pvti_arg, long pvti_msr_arg, unsigned long pvti_entry_size,
		unsigned long enable_bit, int (*current_cpu_fn)(void),
		unsigned long (*virt_to_phys_fn)(void *),
		void (*write_msr_fn)(int, unsigned long), void (*log_fn)(int));
extern int x86_call_ap_func_body_result(int *cpu_boot_status_slot,
		void (*next_func)(void));
extern int x86_show_stack_body_result(unsigned long *sp,
		unsigned long lower_bound, unsigned long upper_bound,
		void (*log_fn)(unsigned long, unsigned long, unsigned long));
extern int x86_arch_print_pre_interrupt_stack_body_result(
		const void *regs, unsigned long error_offset,
		unsigned long rsp_offset, unsigned long rip_offset,
		unsigned long pf_user, unsigned long scan_window,
		void (*log_fn)(int),
		void (*print_stack_fn)(void *, unsigned long));
extern int x86_arch_print_stack_body_result(void *rbp,
		void (*log_fn)(int),
		void (*print_stack_fn)(void *, unsigned long));
extern int x86_print_user_context_body_result(const void *uctx,
		void (*log_fn)(int, unsigned long, unsigned long,
			unsigned long, unsigned long));
extern int x86_arch_show_interrupt_context_body_result(const void *uctx,
		unsigned long (*lock_fn)(void),
		void (*unlock_fn)(unsigned long),
		void (*log_fn)(int, unsigned long, unsigned long,
			unsigned long, unsigned long));
extern int x86_arch_save_panic_regs_body_result(
		const void *regs, const void *current_ctx,
		uint64_t *panic_regs, unsigned long *paniced_slot,
		unsigned long user_end, unsigned long enter_user_mode_addr,
		void (*log_fn)(int, unsigned long));
extern int x86_arch_clear_panic_body_result(unsigned long *paniced_slot);
extern int x86_arch_cpu_read_write_register_body_result(void *desc, int op,
		int read_op, int write_op, unsigned long addr_offset,
		unsigned long val_offset, unsigned long (*read_msr_fn)(int),
		void (*write_msr_fn)(int, unsigned long));

static void
x86_lapic_write_bridge(int reg, unsigned int value)
{
	lapic_write(reg, value);
}

static void
x86_mb_bridge(void)
{
	ihk_mc_mb();
}

static unsigned long
x86_cpu_disable_interrupt_save_bridge(void)
{
	return cpu_disable_interrupt_save();
}

static void
x86_cpu_restore_interrupt_bridge(unsigned long flags)
{
	cpu_restore_interrupt(flags);
}

static unsigned long
x86_read_msr_bridge(int reg)
{
	return rdmsr(reg);
}

void
x86_write_msr_bridge(int reg, unsigned long value)
{
	wrmsr(reg, value);
}

static void *
x86_map_fixed_area_bridge(unsigned long phys, unsigned long size, int uncached)
{
	return map_fixed_area(phys, size, uncached);
}

void *
x86_alloc_aligned_pages_node_bridge(int npages, int p2align,
		unsigned long flag, int node, int is_user, unsigned long virt_addr,
		char *file, int line)
{
	return _ihk_mc_alloc_aligned_pages_node(npages, p2align, flag, node,
			is_user, virt_addr, file, line);
}

unsigned long
x86_virt_to_phys_bridge(void *addr)
{
	return virt_to_phys(addr);
}

int
x86_current_cpu_bridge(void)
{
	return ihk_mc_get_processor_id();
}

static int
x86_running_on_kvm_bridge(void)
{
	return running_on_kvm();
}

static void
x86_cpuid6_bridge(unsigned long *eaxp, unsigned long *ecxp)
{
	unsigned long eax, ecx;

	asm volatile("cpuid" : "=a" (eax), "=c" (ecx) :
			"a" (0x6) : "%rbx", "%rdx");
	*eaxp = eax;
	*ecxp = ecx;
}

static void
x86_cpuid_edx_bridge(unsigned long op, unsigned long *edxp)
{
	unsigned long edx;

	asm volatile("cpuid" : "=d" (edx) : "a" (op) : "%rbx", "%rcx");
	*edxp = edx;
}

void
x86_cpuid_leaf_bridge(unsigned long op, unsigned long *eaxp,
		unsigned long *ebxp, unsigned long *ecxp,
		unsigned long *edxp)
{
	unsigned long eax, ebx, ecx, edx;

	asm volatile("cpuid" : "=a" (eax), "=b" (ebx), "=c" (ecx),
			"=d" (edx) : "a" (op));
	*eaxp = eax;
	*ebxp = ebx;
	*ecxp = ecx;
	*edxp = edx;
}

static void
x86_cpu_log_bridge(int event)
{
	switch (event) {
	case 1:
		kprintf("PAT not supported.\n");
		break;
	case 2:
		dkprintf("PAT support detected and reconfigured.\n");
		break;
	case 3:
		kprintf("Invariant TSC supported.\n");
		break;
	case 4:
		kprintf("setup_x86 done.\n");
		break;
	}
}

static void
x86_cpu_value_log_bridge(int event, int value)
{
	switch (event) {
	case 1:
		kprintf("no_execute_available: %d\n", value);
		break;
	}
}

extern void enable_ptattr_no_execute(void);
static void
x86_enable_ptattr_no_execute_bridge(void)
{
	enable_ptattr_no_execute();
}

static void
x86_cpu_ulong_log_bridge(int event, unsigned long value)
{
	switch (event) {
	case 1:
		kprintf("Trampoline area: 0x%lx \n", value);
		break;
	case 2:
		kprintf("# of cpus : %lu\n", value);
		break;
	case 15:
		kprintf("arch_save_panic_regs: in user-space: %p\n",
				(void *)value);
		break;
	}
}

static int
x86_cpu_info_ncpus_bridge(void)
{
	struct ihk_mc_cpu_info *cpu_info = ihk_mc_get_cpu_info();

	return cpu_info->ncpus;
}

static void
x86_init_processors_local_bridge(int max_id)
{
	init_processors_local(max_id);
}
#endif

void
lapic_timer_enable(unsigned int clocks)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_lapic_timer_enable_body_result(clocks, x86_lapic_write_bridge);
#else
	unsigned int lvtt_value;

	lapic_write(LAPIC_TIMER_INITIAL, clocks / APIC_DIVISOR);
	lapic_write(LAPIC_TIMER_DIVIDE, 3);

	/* initialize periodic timer */
	lvtt_value = LOCAL_TIMER_VECTOR | APIC_LVT_TIMER_PERIODIC;
	lapic_write(LAPIC_TIMER, lvtt_value);
#endif
}

void
lapic_timer_disable()
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_lapic_timer_disable_body_result(x86_lapic_write_bridge);
#else
	lapic_write(LAPIC_TIMER_INITIAL, 0);
#endif
}

void
lapic_ack(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_lapic_ack_body_result(x86_lapic_write_bridge);
#else
	lapic_write(LAPIC_EOI, 0);
#endif
}

static void
x2apic_wait_icr_idle(void)
{
}

static void
apic_wait_icr_idle(void)
{
	while (lapic_read(LAPIC_ICR0) & APIC_ICR_BUSY) {
		cpu_pause();
	}
}

static void
x2apic_icr_write(unsigned int low, unsigned int apicid)
{
	wrmsr(IA32_X2APIC_ICR, (((unsigned long)apicid) << 32) | low);
}

static void
apic_icr_write(unsigned int h, unsigned int l)
{
	lapic_write(LAPIC_ICR2, (unsigned int)h);
	lapic_write(LAPIC_ICR0, l);
}

static void
x2apic_x86_issue_ipi(unsigned int apicid, unsigned int low)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_x2apic_issue_ipi_body_result(apicid, low, x86_mb_bridge,
			x86_cpu_disable_interrupt_save_bridge,
			x2apic_icr_write, x86_cpu_restore_interrupt_bridge);
#else
	unsigned long icr = low;
	unsigned long flags;

	ihk_mc_mb();
	flags = cpu_disable_interrupt_save();
	x2apic_icr_write(icr, apicid);
	cpu_restore_interrupt(flags);
#endif
}

static void
apic_x86_issue_ipi(unsigned int apicid, unsigned int low)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_apic_issue_ipi_body_result(apicid, low, LAPIC_ICR_ID_SHIFT,
			x86_cpu_disable_interrupt_save_bridge,
			apic_wait_icr_idle, apic_icr_write,
			x86_cpu_restore_interrupt_bridge);
#else
	unsigned long flags;

	flags = cpu_disable_interrupt_save();
	apic_wait_icr_idle();
	apic_icr_write(apicid << LAPIC_ICR_ID_SHIFT, low);
	cpu_restore_interrupt(flags);
#endif
}

unsigned long
x2apic_is_enabled()
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	return x86_x2apic_enabled_result(rdmsr(MSR_IA32_APIC_BASE),
			X2APIC_ENABLE);
#else
	unsigned long msr;

	msr = rdmsr(MSR_IA32_APIC_BASE);

	return (msr & X2APIC_ENABLE);
#endif
}

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
static void
x86_lapic_bsp_select_bridge(int use_x2apic)
{
	if (use_x2apic) {
		x2apic = 1;
		lapic_write = x2apic_write;
		lapic_read = x2apic_read;
		lapic_icr_write = x2apic_icr_write;
		lapic_wait_icr_idle = x2apic_wait_icr_idle;
		x86_issue_ipi = x2apic_x86_issue_ipi;
	}
	else {
		x2apic = 0;
		lapic_write = apic_write;
		lapic_read = apic_read;
		lapic_icr_write = apic_icr_write;
		lapic_wait_icr_idle = apic_wait_icr_idle;
		x86_issue_ipi = apic_x86_issue_ipi;
	}
}
#endif

void init_lapic_bsp(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_init_lapic_bsp_body_result(x2apic_is_enabled(),
			x86_lapic_bsp_select_bridge);
#else
	if(x2apic_is_enabled()){
		x2apic = 1;
		lapic_write = x2apic_write;
		lapic_read = x2apic_read;
		lapic_icr_write = x2apic_icr_write;
		lapic_wait_icr_idle = x2apic_wait_icr_idle;
		x86_issue_ipi = x2apic_x86_issue_ipi;
	}
	else{
		x2apic = 0;
		lapic_write = apic_write;
		lapic_read = apic_read;
		lapic_icr_write = apic_icr_write;
		lapic_wait_icr_idle = apic_wait_icr_idle;
		x86_issue_ipi = apic_x86_issue_ipi;

	}
#endif
}

void
init_lapic()
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_init_lapic_body_result(x2apic, &lapic_vp,
			MSR_IA32_APIC_BASE, PAGE_MASK, PAGE_SIZE, 0x800,
			x86_read_msr_bridge, x86_write_msr_bridge,
			x86_map_fixed_area_bridge, x86_lapic_write_bridge);
#else
	if(!x2apic){
		unsigned long baseaddr;

		/* Enable Local APIC */
		baseaddr = rdmsr(MSR_IA32_APIC_BASE);
		if (!lapic_vp) {
			lapic_vp = map_fixed_area(baseaddr & PAGE_MASK, PAGE_SIZE, 1);
		}
		baseaddr |= 0x800;
		wrmsr(MSR_IA32_APIC_BASE, baseaddr);
	}

	lapic_write(LAPIC_SPURIOUS, 0x1ff);
	lapic_write(LAPIC_LVTPC, LOCAL_PERF_VECTOR);
#endif
}

void print_msr(int idx)
{
	int bit;
	unsigned long long val;

	val = rdmsr(idx);

	__kprintf("MSR 0x%x val (dec): %llu\n", idx, val);
	__kprintf("MSR 0x%x val (hex): 0x%llx\n", idx, val);

	__kprintf("                    ");
	for (bit = 63; bit >= 0; --bit) {
		__kprintf("%3d", bit);
	}
	__kprintf("\n");

	__kprintf("MSR 0x%x val (bin):", idx);
	for (bit = 63; bit >= 0; --bit) {
		__kprintf("%3d", (val & ((unsigned long)1 << bit)) ? 1 : 0);
	}
	__kprintf("\n");
}


void init_pstate_and_turbo(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_init_pstate_turbo_body_result(no_turbo, MSR_PLATFORM_INFO,
			MSR_NHM_TURBO_RATIO_LIMIT, MSR_IA32_PERF_CTL,
			MSR_IA32_ENERGY_PERF_BIAS, x86_running_on_kvm_bridge,
			x86_cpuid6_bridge, x86_read_msr_bridge,
			x86_write_msr_bridge);
#else
	uint64_t value;
	uint64_t eax, ecx;

	if (running_on_kvm()) return;

	asm volatile("cpuid" : "=a" (eax), "=c" (ecx) : "a" (0x6) : "%rbx", "%rdx");
	if (!(ecx & 0x01)) {
		/* P-states and/or Turbo Boost are not supported. */
		return;
	}

	/* Query and set max pstate value: 
	 *
	 * IA32_PERF_CTL (0x199H) bit 15:0:
	 * Target performance State Value
	 *
	 * The base operating ratio can be read 
	 * from MSR_PLATFORM_INFO[15:8].
	 */
	value = rdmsr(MSR_PLATFORM_INFO);
	value &= 0xFF00;

	/* Turbo boost setting:
	 * Bit 1 of EAX in Leaf 06H (i.e. CPUID.06H:EAX[1]) indicates opportunistic 
	 * processor performance operation, such as IDA, has been enabled by BIOS.
	 *
	 * IA32_PERF_CTL (0x199H) bit 32: IDA (i.e., turbo boost) Engage. (R/W)
	 * When set to 1: disengages IDA
	 * When set to 0: enables IDA
	 */
	if ((eax & (1 << 1))) {
		if (!no_turbo) {
			uint64_t turbo_value;

			turbo_value = rdmsr(MSR_NHM_TURBO_RATIO_LIMIT);
			turbo_value &= 0xFF;
			value = turbo_value << 8;

			/* Enable turbo boost */
			value &= ~((uint64_t)1 << 32);
		}
		/* Turbo boost feature is supported, but requested to be turned off */
		else {
			/* Disable turbo boost */
			value |= (uint64_t)1 << 32; 
		}
	}

	wrmsr(MSR_IA32_PERF_CTL, value);

	/* IA32_ENERGY_PERF_BIAS (0x1B0H) bit 3:0:
	 * (The processor supports this capability if CPUID.06H:ECX.SETBH[bit 3] is set.)
	 * Power Policy Preference:
	 * 0 indicates preference to highest performance.
	 * 15 indicates preference to maximize energy saving.
	 *
	 * Set energy/perf bias to high performance 
	 */ 
	if (ecx & (1 << 3)) {
		wrmsr(MSR_IA32_ENERGY_PERF_BIAS, 0);
	}
	
	//print_msr(MSR_IA32_MISC_ENABLE);
	//print_msr(MSR_IA32_PERF_CTL);
	//print_msr(MSR_IA32_ENERGY_PERF_BIAS);
#endif
}

enum {
	PAT_UC = 0,		/* uncached */
	PAT_WC = 1,		/* Write combining */
	PAT_WT = 4,		/* Write Through */
	PAT_WP = 5,		/* Write Protected */
	PAT_WB = 6,		/* Write Back (default) */
	PAT_UC_MINUS = 7,	/* UC, but can be overriden by MTRR */
};

#define PAT(x, y)	((uint64_t)PAT_ ## y << ((x)*8))

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
extern int x86_set_kstack_body_result(void *cpu_local,
		unsigned long kernel_stack_offset,
		unsigned long tss_rsp0_offset, unsigned long stack_pointer);
#endif

void init_pat(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_init_pat_body_result(&boot_pat_state, MSR_IA32_CR_PAT,
			x86_cpuid_edx_bridge, x86_read_msr_bridge,
			x86_write_msr_bridge, x86_cpu_log_bridge);
#else
	uint64_t pat;
	uint64_t edx;

	/*
	 * An operating system or executive can detect the availability of the 
	 * PAT by executing the CPUID instruction with a value of 1 in the EAX 
	 * register. Support for the PAT is indicated by the PAT flag (bit 16 
	 * of the values returned to EDX register). If the PAT is supported, 
	 * the operating system or executive can use the IA32_PAT MSR to program 
	 * the PAT. When memory types have been assigned to entries in the PAT, 
	 * software can then use of the PAT-index bit (PAT) in the page-table and 
	 * page-directory entries along with the PCD and PWT bits to assign memory 
	 * types from the PAT to individual pages.
	 */

	asm volatile("cpuid" : "=d" (edx) : "a" (0x1) : "%rbx", "%rcx");
	if (!(edx & ((uint64_t)1 << 16))) {
		kprintf("PAT not supported.\n");
		return;	
	}
	
	/* Set PWT to Write-Combining. All other bits stay the same */
	/* (Based on Linux' settings)
	 *
	 * PTE encoding used in Linux:
	 *      PAT
	 *      |PCD
	 *      ||PWT
	 *      |||
	 *      000 WB		_PAGE_CACHE_WB
	 *      001 WC		_PAGE_CACHE_WC
	 *      010 UC-		_PAGE_CACHE_UC_MINUS
	 *      011 UC		_PAGE_CACHE_UC
	 * PAT bit unused
	 */
	pat = PAT(0, WB) | PAT(1, WC) | PAT(2, UC_MINUS) | PAT(3, UC) |
	      PAT(4, WB) | PAT(5, WC) | PAT(6, UC_MINUS) | PAT(7, UC);

	/* Boot CPU check */
	if (!boot_pat_state)
		boot_pat_state = rdmsr(MSR_IA32_CR_PAT);

	wrmsr(MSR_IA32_CR_PAT, pat);
	dkprintf("PAT support detected and reconfigured.\n");
#endif
}

static void set_kstack(unsigned long ptr)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_set_kstack_body_result(get_x86_this_cpu_local(),
			__builtin_offsetof(struct x86_cpu_local_variables,
				kernel_stack),
			__builtin_offsetof(struct x86_cpu_local_variables,
				tss.rsp0),
			ptr);
#else
	struct x86_cpu_local_variables *v;

	v = get_x86_this_cpu_local();
	v->kernel_stack = ptr;
	v->tss.rsp0 = ptr;
#endif
}

static void init_smp_processor(void)
{
	struct x86_cpu_local_variables *v;
	unsigned long tss_addr;
	unsigned node_cpu;

	v = get_x86_this_cpu_local();
	tss_addr = (unsigned long)&v->tss;

	if(x2apic_is_enabled()){
		v->apic_id = rdmsr(IA32_X2APIC_APICID);
	}
	else{
		v->apic_id = lapic_read(LAPIC_ID) >> LAPIC_ID_SHIFT;
	}

	memcpy(v->gdt, gdt, sizeof(v->gdt));
	
	memset(&v->tss, 0, sizeof(v->tss));

	v->gdt[GLOBAL_TSS_ENTRY] = (sizeof(v->tss) - 1) 
		| ((tss_addr & 0xffffff) << 16)
		| (0x89UL << 40) | ((tss_addr & 0xff000000) << 32);
	v->gdt[GLOBAL_TSS_ENTRY + 1] = (tss_addr >> 32);

	node_cpu = v->processor_id;	/* assumes NUMA node 0 */
	v->gdt[GETCPU_ENTRY] |= node_cpu;

	v->gdt_ptr.size = sizeof(v->gdt) - 1;
	v->gdt_ptr.address = (unsigned long)v->gdt;
        
	/* Load the new GDT, and set up CS, DS and SS. */
	reload_gdt(&v->gdt_ptr);

	set_kstack((unsigned long)get_x86_this_cpu_kstack());

	/* MSR_IA32_TSC_AUX on KVM seems broken */
	if (running_on_kvm()) return;
#define MSR_IA32_TSC_AUX 0xc0000103
	wrmsr(MSR_IA32_TSC_AUX, node_cpu);
}

static char *trampoline_va, *first_page_va;

/*@
  @ assigns torampoline_va;
  @ assigns first_page_va;
  @*/
void ihk_mc_init_ap(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_ihk_mc_init_ap_body_result(&trampoline_va, &first_page_va,
			ap_trampoline, AP_TRAMPOLINE_SIZE, PAGE_SIZE,
			x86_map_fixed_area_bridge, x86_cpu_info_ncpus_bridge,
			x86_init_processors_local_bridge, assign_processor_id,
			init_smp_processor, x86_cpu_ulong_log_bridge);
#else
	struct ihk_mc_cpu_info *cpu_info = ihk_mc_get_cpu_info();

	trampoline_va = map_fixed_area(ap_trampoline, AP_TRAMPOLINE_SIZE, 0);
	kprintf("Trampoline area: 0x%lx \n", ap_trampoline);
	first_page_va = map_fixed_area(0, PAGE_SIZE, 0);

	kprintf("# of cpus : %d\n", cpu_info->ncpus);
	init_processors_local(cpu_info->ncpus);
	
	/* Do initialization for THIS cpu (BSP) */
	assign_processor_id();

	init_smp_processor();
#endif
}

extern void init_page_table(void);

extern char x86_syscall[];
long (*__x86_syscall_handler)(int, ihk_mc_user_context_t *);

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
struct x86_thread_context_offsets {
	unsigned long thread_status_offset;
	unsigned long thread_uctx_offset;
	unsigned long thread_tlsblock_base_offset;
};

struct x86_trace_enter_user_offsets {
	unsigned long thread_tid_offset;
	unsigned long thread_status_offset;
	unsigned long thread_proc_offset;
	unsigned long process_pid_offset;
};

extern int x86_init_context_body_result(ihk_mc_kernel_context_t *new_ctx,
		void *stack_pointer, void *next_function,
		void *(*stack_fn)(void));
extern int x86_boot_cpu_body_result(void *trampoline_va,
		const void *trampoline_code_data,
		unsigned long trampoline_code_size, int cpuid, unsigned long pc,
		unsigned long ap_trampoline, int *boot_status_slot,
		void *setup_x86_ap_addr,
		unsigned long (*boot_page_table_phys_fn)(void),
		unsigned long (*cpu_kstack_fn)(int),
		unsigned long (*transit_page_table_fn)(void),
		void (*wakeup_fn)(int, unsigned long), void (*pause_fn)(void));
extern int x86_init_user_process_body_result(
		ihk_mc_kernel_context_t *ctx, ihk_mc_user_context_t **puctx,
		void *stack_pointer, unsigned long new_pc,
		unsigned long user_sp, unsigned long user_cs,
		unsigned long user_ds, unsigned long rflags_if,
		void *enter_user_mode_addr);
extern int x86_modify_user_context_result(ihk_mc_user_context_t *uctx,
		int reg, unsigned long value, int stack_pointer_reg,
		int program_counter_reg);
extern ihk_mc_user_context_t *x86_lookup_user_context_body_result(
		struct thread *thread, struct thread *current_thread,
		int sleep_status_mask,
		const struct x86_thread_context_offsets *offsets);
extern int x86_syscall_handler_publish_result(unsigned long *slot,
		void *handler);
extern int x86_page_fault_handler_publish_result(unsigned long *slot,
		void *handler);
extern int x86_arch_noop_body_result(void);
extern int x86_mcexec_v10_trace_enter_user_body_result(
		const ihk_mc_user_context_t *regs, const struct thread *thread,
		int *counter, int limit, int cpu,
		const struct x86_trace_enter_user_offsets *offsets,
		void (*log_fn)(int, int, int, unsigned long, unsigned long,
			unsigned long, unsigned long, unsigned long, int));
extern int x86_release_runq_lock_body_result(void *cpu_local,
		unsigned long runq_lock_offset, unsigned long runq_irqstate_offset,
		void (*unlock_fn)(void *, unsigned long));
extern int x86_set_kstack_body_result(void *cpu_local,
		unsigned long kernel_stack_offset,
		unsigned long tss_rsp0_offset, unsigned long stack_pointer);
extern int x86_delay_us_body_result(int us, void (*delay_fn)(int));
extern int x86_tick_log_body_result(int event, void (*log_fn)(int));
extern int x86_arch_set_special_register_result(int reg_type, int fs_type,
		unsigned long value, void (*write_fn)(unsigned long));
extern int x86_arch_get_special_register_result(int reg_type, int fs_type,
		unsigned long *valuep, unsigned long (*read_fn)(void));
extern int x86_get_interrupt_id_result(int cpu,
		void *(*cpu_local_fn)(int), unsigned long apic_id_offset);
extern int x86_interrupt_cpu_result(int cpu, int vector, int num_processors,
		void *(*cpu_local_fn)(int), unsigned long apic_id_offset,
		void (*issue_ipi_fn)(unsigned long, int),
		void (*log_fn)(int, int, int));

static const struct x86_thread_context_offsets x86_thread_context_offsets = {
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_uctx_offset = __builtin_offsetof(struct thread, uctx),
	.thread_tlsblock_base_offset =
		__builtin_offsetof(struct thread, tlsblock_base),
};

static const struct x86_trace_enter_user_offsets x86_trace_enter_user_offsets = {
	.thread_tid_offset = __builtin_offsetof(struct thread, tid),
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_proc_offset = __builtin_offsetof(struct thread, proc),
	.process_pid_offset = __builtin_offsetof(struct process, pid),
};

static void *x86_this_kstack_bridge(void)
{
	return get_x86_this_cpu_kstack();
}

static void *x86_cpu_local_bridge(int cpu)
{
	return get_x86_cpu_local_variable(cpu);
}

static void x86_arch_delay_bridge(int us)
{
	arch_delay(us);
}

void x86_tick_log_bridge(int event)
{
	switch (event) {
	case 1:
		dkprintf("init_tick():\n");
		break;
	case 2:
		dkprintf("init_delay():\n");
		break;
	case 3:
		dkprintf("sync_tick():\n");
		break;
	}
}

void x86_pvclock_log_bridge(int event)
{
	switch (event) {
	case 1:
		dkprintf("is_pvclock_available()\n");
		break;
	case 2:
		dkprintf("is_pvclock_available(): false (not kvm)\n");
		break;
	case 3:
		dkprintf("is_pvclock_available(): true (new)\n");
		break;
	case 4:
		dkprintf("is_pvclock_available(): true (old)\n");
		break;
	case 5:
		dkprintf("is_pvclock_available(): false (not supported)\n");
		break;
	case 6:
		dkprintf("arch_setup_pvclock()\n");
		break;
	case 7:
		dkprintf("arch_setup_pvclock(): not supported\n");
		break;
	case 8:
		ekprintf("arch_setup_pvclock: allocate_pages failed.\n");
		break;
	case 9:
		dkprintf("arch_setup_pvclock(): ok\n");
		break;
	case 10:
		dkprintf("arch_start_pvclock()\n");
		break;
	case 11:
		dkprintf("arch_start_pvclock(): not supported\n");
		break;
	case 12:
		dkprintf("arch_start_pvclock(): ok\n");
		break;
	case 13:
		__kprintf("Pre-interrupt stack trace:\n");
		break;
	case 14:
		__kprintf("Approximative stack trace:\n");
		break;
	}
}
#endif

void init_syscall(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_init_syscall_body_result(MSR_EFER, MSR_STAR, MSR_LSTAR,
			KERNEL_CS, USER_CS, (unsigned long)x86_syscall,
			x86_read_msr_bridge, x86_write_msr_bridge);
#else
	unsigned long r;

	r = rdmsr(MSR_EFER);
	r |= 1; /* SYSCALL Enable */
	wrmsr(MSR_EFER, r);

	r = (((unsigned long)KERNEL_CS) << 32) 
		| (((unsigned long)USER_CS) << 48);
	wrmsr(MSR_STAR, r);
	
	wrmsr(MSR_LSTAR, (unsigned long)x86_syscall);
#endif
}

static void enable_page_protection_fault(void)
{
	asm volatile (
			"pushf	;"
			"cli	;"
			"mov	%%cr0,%%rax;"
			"or	$0x10000,%%rax;"
			"mov	%%rax,%%cr0;"
			"popf"
			::: "%rax");
	return;
}

static int no_execute_available = 0;

static void enable_no_execute(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_enable_no_execute_body_result(no_execute_available, MSR_EFER,
			1UL << 11, x86_read_msr_bridge, x86_write_msr_bridge);
#else
	unsigned long efer;

	if (!no_execute_available) {
		return;
	}

	efer = rdmsr(MSR_EFER);
#define	IA32_EFER_NXE	(1UL << 11)
	efer |= IA32_EFER_NXE;
	wrmsr(MSR_EFER, efer);

	return;
#endif
}

static void check_no_execute(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_check_no_execute_body_result(&no_execute_available,
			x86_cpuid_edx_bridge, x86_cpu_value_log_bridge,
			x86_enable_ptattr_no_execute_bridge);
#else
	uint32_t edx;
	extern void enable_ptattr_no_execute(void);

	/* check Execute Disable Bit available bit */
	asm ("cpuid" : "=d" (edx) : "a" (0x80000001) : "%rbx", "%rcx");
	no_execute_available = (edx & (1 << 20))? 1: 0;
	kprintf("no_execute_available: %d\n", no_execute_available);

	if (no_execute_available) {
		enable_ptattr_no_execute();
	}

	return;
#endif
}

void init_gettime_support(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_init_gettime_support_body_result(&gettime_local_support,
			x86_cpuid_edx_bridge, x86_cpu_log_bridge);
#else
	uint64_t op;
	uint64_t eax;
	uint64_t ebx;
	uint64_t ecx;
	uint64_t edx;

	/* Check if Invariant TSC supported.
	 * Processor's support for invariant TSC is indicated by
	 * CPUID.80000007H:EDX[8].
	 * See page 2498 of the Intel64 and IA-32 Architectures Software
	 * Developer's Manual - combined */

	op = 0x80000007;
	asm volatile("cpuid" : "=a"(eax),"=b"(ebx),"=c"(ecx),"=d"(edx) : "a" (op));

	if (edx & (1 << 8)) {
		gettime_local_support = 1;
		kprintf("Invariant TSC supported.\n");
	}
#endif
}

void init_cpu(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_init_cpu_body_result(enable_page_protection_fault,
			enable_no_execute, init_fpu, init_lapic, init_syscall,
			x86_init_perfctr, init_pstate_and_turbo, init_pat);
#else
	enable_page_protection_fault();
	enable_no_execute();
	init_fpu();
	init_lapic();
	init_syscall();
	x86_init_perfctr();
	init_pstate_and_turbo();
	init_pat();
#endif
}

void setup_x86_phase1(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_setup_phase1_body_result(cpu_disable_interrupt, init_idt,
			init_gdt, init_page_table);
#else
	cpu_disable_interrupt();

	init_idt();

	init_gdt();

	init_page_table();
#endif
}

void setup_x86_phase2(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_setup_phase2_body_result(check_no_execute, init_lapic_bsp,
			init_cpu, init_gettime_support, x86_cpu_log_bridge);
#else
	check_no_execute();

	init_lapic_bsp();

	init_cpu();

	init_gettime_support();

	kprintf("setup_x86 done.\n");
#endif
}

static volatile int cpu_boot_status;

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
int *x86_cpu_boot_status_slot_bridge(void)
{
	return (int *)&cpu_boot_status;
}

void call_ap_func(void (*next_func)(void));
#else
void call_ap_func(void (*next_func)(void))
{
	cpu_boot_status = 1;
	next_func();
}
#endif

struct page_table *get_init_page_table(void);
void setup_x86_ap(void (*next_func)(void))
{
	unsigned long rsp;
	cpu_disable_interrupt();

	ihk_mc_load_page_table(get_init_page_table());

	assign_processor_id();

	init_smp_processor();

	reload_idt();

	init_cpu();

	rsp = (unsigned long)get_x86_this_cpu_kstack();

	asm volatile("movq %0, %%rdi\n"
	             "movq %1, %%rsp\n"
	             "call *%2" : : "r"(next_func), "r"(rsp), "r"(call_ap_func)
	             : "rdi");
	while(1);
}

void arch_show_interrupt_context(const void *reg);
extern void tlb_flush_handler(int vector);
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void x86_stack_frame_log_bridge(unsigned long ip, unsigned long sp,
		unsigned long fp);
#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void __show_stack(uintptr_t *sp);
#else
void __show_stack(uintptr_t *sp) {
	while (((uintptr_t)sp >= 0xffff800000000000)
			&& ((uintptr_t)sp <  0xffffffff80000000)) {
		uintptr_t fp;
		uintptr_t ip;

		fp = sp[0];
		ip = sp[1];
		kprintf("IP: %016lx, SP: %016lx, FP: %016lx\n", ip, (uintptr_t)sp, fp);
		sp = (void *)fp;
	}
	return;
}
#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void show_context_stack(uintptr_t *rbp);
#else
void show_context_stack(uintptr_t *rbp) {
	__show_stack(rbp);
	return;
}
#endif

#ifdef ENABLE_FUGAKU_HACKS
void __show_context_stack(struct thread *thread,
        unsigned long pc, uintptr_t sp, int kprintf_locked)
{
    uintptr_t stack_top;
    unsigned long irqflags = 0;

    stack_top = ALIGN_UP(sp, (uintptr_t)KERNEL_STACK_SIZE);

    if (!kprintf_locked)
        irqflags = kprintf_lock();

    __kprintf("TID: %d, call stack (most recent first):\n",
        thread->tid);
    __kprintf("PC: %016lx, SP: %016lx\n", pc, sp);
    for (;;) {
        extern char _head[], _end[];
        uintptr_t *fp, *lr;
        fp = (uintptr_t *)sp;
        lr = (uintptr_t *)(sp + 8);

        if ((*fp <= sp)) {
            break;
        }

        if ((*fp > stack_top)) {
            break;
        }

        if ((*lr < (unsigned long)_head) ||
            (*lr > (unsigned long)_end)) {
            break;
        }

        __kprintf("PC: %016lx, SP: %016lx, FP: %016lx\n", *lr - 4, sp, *fp);
        sp = *fp;
    }

    if (!kprintf_locked)
        kprintf_unlock(irqflags);
}
#endif

void interrupt_exit(struct x86_user_context *regs)
{
	if (interrupt_from_user(regs)) {
		cpu_enable_interrupt();
		check_sig_pending();
		check_need_resched();
		check_signal(0, regs, -1);
	}
}

void handle_interrupt(int vector, struct x86_user_context *regs)
{
	struct ihk_mc_interrupt_handler *h;
	struct cpu_local_var *v = get_this_cpu_local_var();
	int from_user = interrupt_from_user(regs);
	static int mcexec_v10_exception_logs;

	lapic_ack();
	++v->in_interrupt;

	set_cputime(from_user ?
		CPUTIME_MODE_U2K : CPUTIME_MODE_K2K_IN);

	dkprintf("CPU[%d] got interrupt, vector: %d, RIP: 0x%lX\n", 
	         ihk_mc_get_processor_id(), vector, regs->gpr.rip);

	if (vector < 0 || vector > 255) {
		panic("Invalid interrupt vector.");
	} 
	else if (vector < 32) {
		struct siginfo info;

		if (from_user && mcexec_v10_exception_logs < 32) {
			struct thread *thread = get_this_cpu_local_var()->current;

			kprintf("mcexec_v10: exception cpu=%d vector=%d pid=%d tid=%d rip=0x%lx sp=0x%lx error=0x%lx rflags=0x%lx\n",
				ihk_mc_get_processor_id(), vector,
				thread && thread->proc ? thread->proc->pid : -1,
				thread ? thread->tid : -1,
				regs->gpr.rip, regs->gpr.rsp,
				regs->gpr.error, regs->gpr.rflags);
			mcexec_v10_exception_logs++;
		}

		switch(vector){
		    case 0:
			memset(&info, '\0', sizeof info);
			info.si_signo = SIGFPE;
			info.si_code = FPE_INTDIV;
			info._sifields._sigfault.si_addr = (void *)regs->gpr.rip;
			set_signal(SIGFPE, regs, &info);
			break;
		    case 9:
		    case 16:
		    case 19:
			set_signal(SIGFPE, regs, NULL);
			break;
		    case 4:
		    case 5:
			set_signal(SIGSEGV, regs, NULL);
			break;
		    case 6:
			memset(&info, '\0', sizeof info);
			info.si_signo = SIGILL;
			info.si_code = ILL_ILLOPN;
			info._sifields._sigfault.si_addr = (void *)regs->gpr.rip;
			set_signal(SIGILL, regs, &info);
			break;
		    case 10:
			set_signal(SIGSEGV, regs, NULL);
			break;
		    case 11:
		    case 12:
			set_signal(SIGBUS, regs, NULL);
			break;
		    case 17:
			memset(&info, '\0', sizeof info);
			info.si_signo = SIGBUS;
			info.si_code = BUS_ADRALN;
			set_signal(SIGBUS, regs, &info);
			break;
		    default:
			kprintf("Exception %d, rflags: 0x%lX CS: 0x%lX, RIP: 0x%lX\n",
			        vector, regs->gpr.rflags, regs->gpr.cs, regs->gpr.rip);
			arch_show_interrupt_context(regs);
			panic("Unhandled exception");
		}
	}
	else if (vector == LOCAL_TIMER_VECTOR) {
		unsigned long irqstate;
		/* Timer interrupt, enabled only on oversubscribed CPU cores,
		 * request reschedule */
		irqstate = ihk_mc_spinlock_lock(&v->runq_lock);
		v->flags |= CPU_FLAG_NEED_RESCHED;
		ihk_mc_spinlock_unlock(&v->runq_lock, irqstate);
		dkprintf("timer[%lu]: CPU_FLAG_NEED_RESCHED \n", rdtsc());

		do_backlog();
	}
	else if (vector == LOCAL_PERF_VECTOR) {
		struct siginfo info;
		unsigned long value;
		struct thread *thread = get_this_cpu_local_var()->current;
        	struct process *proc = thread->proc;
		long irqstate;
		struct mckfd *fdp;

		lapic_write(LAPIC_LVTPC, LOCAL_PERF_VECTOR);

		value = rdmsr(MSR_PERF_GLOBAL_STATUS);
		wrmsr(MSR_PERF_GLOBAL_OVF_CTRL, value);
		wrmsr(MSR_PERF_GLOBAL_OVF_CTRL, 0);

		irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
	        for(fdp = proc->mckfd; fdp; fdp = fdp->next) {
			if(fdp->sig_no > 0)
                	        break;
		}
	        ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);

		if(fdp) {
			memset(&info, '\0', sizeof info);
			info.si_signo = fdp->sig_no;
			info._sifields._sigfault.si_addr = (void *)regs->gpr.rip;
			info._sifields._sigpoll.si_fd = fdp->fd;
			set_signal(fdp->sig_no, regs, &info); 
		}
		else {
			set_signal(SIGIO, regs, NULL);
		}
	}
	else if (vector >= IHK_TLB_FLUSH_IRQ_VECTOR_START && 
	         vector < IHK_TLB_FLUSH_IRQ_VECTOR_END) {

			tlb_flush_handler(vector);
	} 
	else if (vector == LOCAL_SMP_FUNC_CALL_VECTOR) {
		smp_func_call_handler();
	}
	else if (vector == 133) {
		show_context_stack((uintptr_t *)regs->gpr.rbp);
	}
	else {
		for (h = ((typeof(*h) *)((char *)((&handlers[vector - 32])->next) - offsetof(typeof(*h), list))); &h->list != (&handlers[vector - 32]); h = ((typeof(*h) *)((char *)(h->list.next) - offsetof(typeof(*h), list)))) {
			if (h->func) {
				h->func(h->priv);
			}
		}
	}

	interrupt_exit(regs);
	set_cputime(from_user ?
		CPUTIME_MODE_K2U : CPUTIME_MODE_K2K_OUT);

	--v->in_interrupt;

	/* for migration by IPI */
	if (v->flags & CPU_FLAG_NEED_MIGRATE) {
		// Don't migrate on K2K schedule
		if (from_user) {
			schedule();
			check_signal(0, regs, 0);
		}
	}
}

void gpe_handler(struct x86_user_context *regs)
{
	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_U2K : CPUTIME_MODE_K2K_IN);
	kprintf("General protection fault (err: %lx, %lx:%lx)\n",
	        regs->gpr.error, regs->gpr.cs, regs->gpr.rip);
	arch_show_interrupt_context(regs);
	if ((regs->gpr.cs & 3) == 0) {
		panic("gpe_handler");
	}
	set_signal(SIGSEGV, regs, NULL);
	interrupt_exit(regs);
	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_K2U : CPUTIME_MODE_K2K_OUT);
	panic("GPF");
}

void debug_handler(struct x86_user_context *regs)
{
	unsigned long db6;
	int si_code = 0;
	struct siginfo info;

	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_U2K : CPUTIME_MODE_K2K_IN);
#ifdef DEBUG_PRINT_CPU
	kprintf("debug exception (err: %lx, %lx:%lx)\n",
	        regs->gpr.error, regs->gpr.cs, regs->gpr.rip);
	arch_show_interrupt_context(regs);
#endif

	asm("mov %%db6, %0" :"=r" (db6));
	if (db6 & DB6_BS) {
	        regs->gpr.rflags &= ~RFLAGS_TF;
		si_code = TRAP_TRACE;
	} else if (db6 & (DB6_B3|DB6_B2|DB6_B1|DB6_B0)) {
		si_code = TRAP_HWBKPT;
	}

	memset(&info, '\0', sizeof info);
	info.si_code = si_code;
	set_signal(SIGTRAP, regs, &info);
	interrupt_exit(regs);
	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_K2U : CPUTIME_MODE_K2K_OUT);
}

void int3_handler(struct x86_user_context *regs)
{
	struct siginfo info;

	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_U2K : CPUTIME_MODE_K2K_IN);
#ifdef DEBUG_PRINT_CPU
	kprintf("int3 exception (err: %lx, %lx:%lx)\n",
	        regs->gpr.error, regs->gpr.cs, regs->gpr.rip);
	arch_show_interrupt_context(regs);
#endif

	memset(&info, '\0', sizeof info);
	info.si_code = TRAP_BRKPT;
	set_signal(SIGTRAP, regs, &info);
	interrupt_exit(regs);
	set_cputime(interrupt_from_user(regs) ?
		CPUTIME_MODE_K2U : CPUTIME_MODE_K2K_OUT);
}

static void outb(uint8_t v, uint16_t port)
{
	asm volatile("outb %0, %1" : : "a" (v), "d" (port));
}

static void set_warm_reset_vector(unsigned long ip)
{
	x86_set_warm_reset(ip, first_page_va);
}

static void __x86_wakeup(int apicid, unsigned long ip)
{
	int retry = 3;

	set_warm_reset_vector(ip);

	/* Clear the error */
	lapic_write(LAPIC_ESR, 0);
	lapic_read(LAPIC_ESR);

	/* INIT */
	x86_issue_ipi(apicid, 
	              APIC_INT_LEVELTRIG | APIC_INT_ASSERT | APIC_DM_INIT);

	x86_issue_ipi(apicid, 
	              APIC_INT_LEVELTRIG | APIC_DM_INIT);
	lapic_wait_icr_idle();

	while (retry--) {
		lapic_read(LAPIC_ESR);
		x86_issue_ipi(apicid, APIC_DM_STARTUP | (ip >> 12));
		lapic_wait_icr_idle();

		arch_delay(200);

		if (cpu_boot_status) 
			break;
	}
}

/** IHK Functions **/

/*@
  @ assigns \nothing;
  @ ensures \interrupt_disabled == 0;
  @*/
void cpu_halt(void)
{
	asm volatile("hlt");
}

#ifdef ENABLE_FUGAKU_HACKS
/*@
  @ assigns \nothing;
  @ ensures \interrupt_disabled == 0;
  @*/
void cpu_halt_panic(void)
{
    cpu_halt();
}
#endif

/*@
  @ assigns \nothing;
  @ ensures \interrupt_disabled == 0;
  @*/
void cpu_safe_halt(void)
{
    asm volatile("sti; hlt");
}

/*@
  @ assigns \nothing;
  @ ensures \interrupt_disabled == 0;
  @*/
void cpu_enable_interrupt(void)
{
	asm volatile("sti");
}

/*@
  @ assigns \nothing;
  @ ensures \interrupt_disabled > 0;
  @*/
void cpu_disable_interrupt(void)
{
	asm volatile("cli");
}

/*@
  @ assigns \nothing;
  @ behavior to_enabled:
  @   assumes flags & RFLAGS_IF;
  @   ensures \interrupt_disabled == 0;
  @ behavior to_disabled:
  @   assumes !(flags & RFLAGS_IF);
  @   ensures \interrupt_disabled > 0;
  @*/
void cpu_restore_interrupt(unsigned long flags)
{
	asm volatile("push %0; popf" : : "g"(flags) : "memory", "cc");
}

/*@
  @ assigns \nothing;
  @*/
void cpu_pause(void)
{
	asm volatile("pause" ::: "memory");
}

/*@
  @ assigns \nothing;
  @ ensures \interrupt_disabled > 0;
  @ behavior from_enabled:
  @   assumes \interrupt_disabled == 0;
  @   ensures \result & RFLAGS_IF;
  @ behavior from_disabled:
  @   assumes \interrupt_disabled > 0;
  @   ensures !(\result & RFLAGS_IF);
  @*/
unsigned long cpu_disable_interrupt_save(void)
{
	unsigned long flags;

	asm volatile("pushf; pop %0; cli" : "=r"(flags) : : "memory", "cc");

	return flags;
}

unsigned long cpu_enable_interrupt_save(void)
{
	unsigned long flags;

	asm volatile("pushf; pop %0; sti" : "=r"(flags) : : "memory", "cc");

	return flags;
}

int cpu_interrupt_disabled(void)
{
	unsigned long flags;

	asm volatile("pushf; pop %0" : "=r"(flags) : : "memory", "cc");

	return !(flags & 0x200);
}

/*@
  @ behavior valid_vector:
  @   assumes 32 <= vector <= 255;
  @   requires \valid(h);
  @   assigns handlers[vector-32];
  @   ensures \result == 0;
  @ behavior invalid_vector:
  @   assumes (vector < 32) || (255 < vector);
  @   assigns \nothing;
  @   ensures \result == -EINVAL;
  @*/
int ihk_mc_register_interrupt_handler(int vector,
                                      struct ihk_mc_interrupt_handler *h)
{
	if (vector < 32 || vector > 255) {
		return -EINVAL;
	}

	list_add_tail(&h->list, &handlers[vector - 32]);

	return 0;
}
int ihk_mc_unregister_interrupt_handler(int vector,
                                        struct ihk_mc_interrupt_handler *h)
{
	list_del(&h->list);

	return 0;
}

extern unsigned long __page_fault_handler_address;

/*@
  @ requires \valid(h);
  @ assigns __page_fault_handler_address;
  @ ensures __page_fault_handler_address == h;
  @*/
#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
void ihk_mc_set_page_fault_handler(void (*h)(void *, uint64_t, void *))
{
	__page_fault_handler_address = (unsigned long)h;
}
#endif

extern char trampoline_code_data[], trampoline_code_data_end[];
struct page_table *get_boot_page_table(void);
unsigned long get_transit_page_table(void);

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
static unsigned long x86_boot_page_table_phys_bridge(void)
{
	return virt_to_phys(get_boot_page_table());
}

static unsigned long x86_cpu_kstack_bridge(int cpuid)
{
	return (unsigned long)get_x86_cpu_local_kstack(cpuid);
}

static unsigned long x86_transit_page_table_bridge(void)
{
	return get_transit_page_table();
}

static void x86_wakeup_bridge(int cpuid, unsigned long trampoline)
{
	__x86_wakeup(cpuid, trampoline);
}

static void x86_cpu_pause_bridge(void)
{
	cpu_pause();
}
#endif

/* reusable, but not reentrant */
/*@
  @ requires \valid_apicid(cpuid);	// valid APIC ID or not
  @ requires \valid(pc);
  @ requires \valid(trampoline_va);
  @ requires \valid(trampoline_code_data
  @		+(0..(trampoline_code_data_end - trampoline_code_data)));
  @ requires \valid_physical(ap_trampoline);	// valid physical address or not
  @ assigns (char *)trampoline_va+(0..trampoline_code_data_end - trampoline_code_data);
  @ assigns cpu_boot_status;
  @ ensures cpu_boot_status != 0;
  @*/
void ihk_mc_boot_cpu(int cpuid, unsigned long pc)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_boot_cpu_body_result(trampoline_va, trampoline_code_data,
			trampoline_code_data_end - trampoline_code_data,
			cpuid, pc, ap_trampoline, (int *)&cpu_boot_status,
			(void *)setup_x86_ap, x86_boot_page_table_phys_bridge,
			x86_cpu_kstack_bridge, x86_transit_page_table_bridge,
			x86_wakeup_bridge, x86_cpu_pause_bridge);
#else
	unsigned long *p;

	p = (unsigned long *)trampoline_va;

	memcpy(p, trampoline_code_data, 
	       trampoline_code_data_end - trampoline_code_data);

	p[1] = (unsigned long)virt_to_phys(get_boot_page_table());
	p[2] = (unsigned long)setup_x86_ap;
	p[3] = pc;
	p[4] = (unsigned long)get_x86_cpu_local_kstack(cpuid);
	p[6] = (unsigned long)get_transit_page_table();
	if (!p[6]) {
		p[6] = p[1];
	}

	cpu_boot_status = 0;

	__x86_wakeup(cpuid, ap_trampoline);

	/* XXX: Time out */
	while (!cpu_boot_status) {
		cpu_pause();
	}
#endif
}

/*@
  @ requires \valid(new_ctx);
  @ requires (stack_pointer == NULL) || \valid((unsigned long *)stack_pointer-1);
  @ requires \valid(next_function);
  @*/
void ihk_mc_init_context(ihk_mc_kernel_context_t *new_ctx,
                         void *stack_pointer, void (*next_function)(void))
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_init_context_body_result(new_ctx, stack_pointer,
			(void *)next_function, x86_this_kstack_bridge);
#else
	unsigned long *sp;

	if (!stack_pointer) {
		stack_pointer = get_x86_this_cpu_kstack();
	}

	sp = stack_pointer;
	memset(new_ctx, 0, sizeof(ihk_mc_kernel_context_t));

	/* Set the return address */
	new_ctx->rsp = (unsigned long)(sp - 1);
	sp[-1] = (unsigned long)next_function;
#endif
}

extern char enter_user_mode[];

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
static void x86_mcexec_v10_trace_log_bridge(int cpu, int pid, int tid,
		unsigned long rip, unsigned long sp, unsigned long cs,
		unsigned long ss, unsigned long rflags, int status)
{
	kprintf("mcexec_v10: enter_user cpu=%d pid=%d tid=%d rip=0x%lx sp=0x%lx cs=0x%lx ss=0x%lx rflags=0x%lx status=%d\n",
		cpu, pid, tid, rip, sp, cs, ss, rflags, status);
}

static void x86_runq_unlock_bridge(void *lock, unsigned long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock, irqstate);
}
#endif

void mcexec_v10_trace_enter_user(struct x86_user_context *regs)
{
	static int mcexec_v10_enter_user_logs;
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_mcexec_v10_trace_enter_user_body_result(regs,
			get_this_cpu_local_var()->current,
			&mcexec_v10_enter_user_logs, 32,
			ihk_mc_get_processor_id(),
			&x86_trace_enter_user_offsets,
			x86_mcexec_v10_trace_log_bridge);
#else
	struct thread *thread = get_this_cpu_local_var()->current;

	if (mcexec_v10_enter_user_logs >= 32) {
		return;
	}

	kprintf("mcexec_v10: enter_user cpu=%d pid=%d tid=%d rip=0x%lx sp=0x%lx cs=0x%lx ss=0x%lx rflags=0x%lx status=%d\n",
		ihk_mc_get_processor_id(),
		thread && thread->proc ? thread->proc->pid : -1,
		thread ? thread->tid : -1,
		regs ? regs->gpr.rip : 0UL,
		regs ? regs->gpr.rsp : 0UL,
		regs ? regs->gpr.cs : 0UL,
		regs ? regs->gpr.ss : 0UL,
		regs ? regs->gpr.rflags : 0UL,
		thread ? thread->status : -1);
	mcexec_v10_enter_user_logs++;
#endif
}

/* 
 * Release runq_lock before entering user space.
 * This is needed because schedule() holds the runq lock throughout
 * the context switch and when a new process is created it starts
 * execution in enter_user_mode, which in turn calls this function.
 */
void release_runq_lock(void)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_release_runq_lock_body_result(get_this_cpu_local_var(),
			__builtin_offsetof(struct cpu_local_var, runq_lock),
			__builtin_offsetof(struct cpu_local_var, runq_irqstate),
			x86_runq_unlock_bridge);
#else
	ihk_mc_spinlock_unlock(&(get_this_cpu_local_var()->runq_lock),
			get_this_cpu_local_var()->runq_irqstate);
#endif
}

/*@
  @ requires \valid(ctx);
  @ requires \valid(puctx);
  @ requires \valid((ihk_mc_user_context_t *)stack_pointer-1);
  @ requires \valid_user(new_pc);	// valid user space address or not
  @ requires \valid_user(user_sp-1);
  @ assigns *((ihk_mc_user_context_t *)stack_pointer-1);
  @ assigns ctx->rsp0;
  @*/
void ihk_mc_init_user_process(ihk_mc_kernel_context_t *ctx,
                              ihk_mc_user_context_t **puctx,
                              void *stack_pointer, unsigned long new_pc,
                              unsigned long user_sp)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_init_user_process_body_result(ctx, puctx, stack_pointer, new_pc,
			user_sp, USER_CS, USER_DS, RFLAGS_IF,
			(void *)enter_user_mode);
#else
	char *sp;
	ihk_mc_user_context_t *uctx;

	sp = stack_pointer;
	sp -= sizeof(ihk_mc_user_context_t);
	uctx = (ihk_mc_user_context_t *)sp;

	*puctx = uctx;

	memset(uctx, 0, sizeof(ihk_mc_user_context_t));
	uctx->gpr.cs = USER_CS;
	uctx->gpr.rip = new_pc;
	uctx->gpr.ss = USER_DS;
	uctx->gpr.rsp = user_sp;
	uctx->gpr.rflags = RFLAGS_IF;
	uctx->is_gpr_valid = 1;

	ihk_mc_init_context(ctx, sp, (void (*)(void))enter_user_mode);
	ctx->rsp0 = (unsigned long)stack_pointer;
#endif
}

/*@
  @ behavior rsp:
  @   assumes reg == IHK_UCR_STACK_POINTER;
  @   requires \valid(uctx);
  @   assigns uctx->gpr.rsp;
  @   ensures uctx->gpr.rsp == value;
  @ behavior rip:
  @   assumes reg == IHK_UCR_PROGRAM_COUNTER;
  @   requires \valid(uctx);
  @   assigns uctx->gpr.rip;
  @   ensures uctx->gpr.rip == value;
  @*/
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void ihk_mc_modify_user_context(ihk_mc_user_context_t *uctx,
		enum ihk_mc_user_context_regtype reg, unsigned long value);
#else
void ihk_mc_modify_user_context(ihk_mc_user_context_t *uctx,
                                enum ihk_mc_user_context_regtype reg,
                                unsigned long value)
{
	if (reg == IHK_UCR_STACK_POINTER) {
		uctx->gpr.rsp = value;
	} else if (reg == IHK_UCR_PROGRAM_COUNTER) {
		uctx->gpr.rip = value;
	}
}
#endif

#ifdef POSTK_DEBUG_ARCH_DEP_42 /* /proc/cpuinfo support added. */
long ihk_mc_show_cpuinfo(char *buf, size_t buf_size, unsigned long read_off, int *eofp)
{
	*eofp = 1;
	return -ENOMEM;
}
#endif /* POSTK_DEBUG_ARCH_DEP_42 */

#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
void arch_clone_thread(struct thread *othread, unsigned long pc,
			unsigned long sp, struct thread *nthread)
{
	return;
}
#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
unsigned long x86_kprintf_lock_bridge(void)
{
	return kprintf_lock();
}

void x86_kprintf_unlock_bridge(unsigned long flags)
{
	kprintf_unlock(flags);
}

void x86_context_line_log_bridge(int event, unsigned long a,
		unsigned long b, unsigned long c, unsigned long d)
{
	switch (event) {
	case 1:
		__kprintf("CS:RIP = %4lx:%16lx\n", a, b);
		break;
	case 2:
		__kprintf("             RAX              RBX              RCX              RDX\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 3:
		__kprintf("             RSI              RDI              RSP              RBP\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 4:
		__kprintf("              R8               R9              R10              R11\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 5:
		__kprintf("             R12              R13              R14              R15\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 6:
		__kprintf("              CS               SS           RFLAGS            ERROR\n");
		__kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 20:
		kprintf("CS:RIP = %04lx:%16lx\n", a, b);
		break;
	case 21:
		kprintf("%16lx %16lx %16lx %16lx\n", a, b, c, d);
		break;
	case 22:
		kprintf("%16lx %16lx %16lx\n", a, b, c);
		break;
	}
}
#endif

void ihk_mc_print_user_context(ihk_mc_user_context_t *uctx)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	x86_print_user_context_body_result(uctx, x86_context_line_log_bridge);
#else
	kprintf("CS:RIP = %04lx:%16lx\n", uctx->gpr.cs, uctx->gpr.rip);
	kprintf("%16lx %16lx %16lx %16lx\n%16lx %16lx %16lx\n",
	        uctx->gpr.rax, uctx->gpr.rbx, uctx->gpr.rcx, uctx->gpr.rdx,
	        uctx->gpr.rsi, uctx->gpr.rdi, uctx->gpr.rsp);
#endif
}

/*@
  @ requires \valid(handler);
  @ assigns __x86_syscall_handler;
  @ ensures __x86_syscall_handler == handler;
  @*/
#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
void ihk_mc_set_syscall_handler(long (*handler)(int, ihk_mc_user_context_t *))
{
	__x86_syscall_handler = handler;
}
#endif

/*@
  @ assigns \nothing;
  @*/
#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
void ihk_mc_delay_us(int us)
{
	arch_delay(us);
}
#endif

void arch_show_extended_context(void)
{
	unsigned long cr0, cr4, msr, xcr0 = 0;

	/*  Read and print CRs, MSR_EFER, XCR0  */
	asm volatile("movq %%cr0, %0" : "=r"(cr0));
	asm volatile("movq %%cr4, %0" : "=r"(cr4));
	msr = rdmsr(MSR_EFER);
	if (xsave_available) {
		xcr0 = xgetbv(0);
	}
	__kprintf("\n             CR0              CR4\n");
	__kprintf("%016lX %016lX\n", cr0, cr4);

	__kprintf("             MSR_EFER\n");
	__kprintf("%016lX\n", msr);

	if (xsave_available) {
		__kprintf("             XCR0\n");
		__kprintf("%016lX\n", xcr0);
	}
}

struct stack {
	struct stack *rbp;
	unsigned long eip;
};

/* KPRINTF_LOCAL_BUF_LEN is 1024, useless to go further */
#define STACK_BUF_LEN (1024-sizeof("[  0]: "))
static void __print_stack(struct stack *rbp, unsigned long first) {
	char buf[STACK_BUF_LEN];
	size_t len;

	/* Build string in buffer to output a single line */
	len = snprintf(buf, STACK_BUF_LEN,
		       "addr2line -e smp-x86/kernel/mckernel.img -fpia");

	if (first)
		len += snprintf(buf + len, STACK_BUF_LEN - len,
				" %#16lx", first);

	while ((unsigned long)rbp > 0xffff880000000000 &&
			STACK_BUF_LEN - len > sizeof(" 0x0123456789abcdef")) {
		len += snprintf(buf + len, STACK_BUF_LEN - len,
				" %#16lx", rbp->eip);
		rbp = rbp->rbp;
	}
	__kprintf("%s\n", buf);
}

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void x86_stack_frame_log_bridge(unsigned long ip, unsigned long sp,
		unsigned long fp)
{
	kprintf("IP: %016lx, SP: %016lx, FP: %016lx\n", ip, sp, fp);
}

void x86_print_stack_bridge(void *rbp, unsigned long first)
{
	__print_stack(rbp, first);
}
#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void arch_print_pre_interrupt_stack(const struct x86_basic_regs *regs);
#else
void arch_print_pre_interrupt_stack(const struct x86_basic_regs *regs) {
	struct stack *rbp;

	/* only for kernel stack */
	if (regs->error & PF_USER)
		return;

	__kprintf("Pre-interrupt stack trace:\n");

	/* interrupt stack heuristics:
	 * - the first entry looks like it is always garbage, so skip.
	 * (that is done by taking regs->rsp instead of &regs->rsp)
	 * - that still looks sometimes wrong. For now, if it is not
	 * within 64k of itself, look for the next entry that matches.
	 */

	rbp = (struct stack*)regs->rsp;

	while ((uintptr_t)rbp > (uintptr_t)rbp->rbp
			|| (uintptr_t)rbp + 0x10000 < (uintptr_t)rbp->rbp)
		rbp = (struct stack *)(((uintptr_t *)rbp) + 1);

	__print_stack(rbp, regs->rip);
}
#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void arch_print_stack(void);
#else
void arch_print_stack(void)
{
	struct stack *rbp;

	asm("mov %%rbp, %0" : "=r"(rbp) );

	__kprintf("Approximative stack trace:\n");

	__print_stack(rbp, 0);
}
#endif

#ifdef ENABLE_FUGAKU_HACKS
unsigned long arch_get_instruction_address(const void *reg)
{
	const struct x86_user_context *uctx = reg;
	const struct x86_basic_regs *regs = &uctx->gpr;

	return regs->rip;
}
#endif

/*@
  @ requires \valid(reg);
  @ assigns \nothing;
  @*/
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void arch_show_interrupt_context(const void *reg);
#else
void arch_show_interrupt_context(const void *reg)
{
	const struct x86_user_context *uctx = reg;
	const struct x86_basic_regs *regs = &uctx->gpr;
	unsigned long irqflags;

	irqflags = kprintf_lock();

	__kprintf("CS:RIP = %4lx:%16lx\n", regs->cs, regs->rip);
	__kprintf("             RAX              RBX              RCX              RDX\n");
	__kprintf("%16lx %16lx %16lx %16lx\n",
	        regs->rax, regs->rbx, regs->rcx, regs->rdx);
	__kprintf("             RSI              RDI              RSP              RBP\n");
	__kprintf("%16lx %16lx %16lx %16lx\n",
	        regs->rsi, regs->rdi, regs->rsp, regs->rbp);
	__kprintf("              R8               R9              R10              R11\n");
	__kprintf("%16lx %16lx %16lx %16lx\n",
	        regs->r8, regs->r9, regs->r10, regs->r11);
	__kprintf("             R12              R13              R14              R15\n");
	__kprintf("%16lx %16lx %16lx %16lx\n",
	        regs->r12, regs->r13, regs->r14, regs->r15);
	__kprintf("              CS               SS           RFLAGS            ERROR\n");
	__kprintf("%16lx %16lx %16lx %16lx\n",
	        regs->cs, regs->ss, regs->rflags, regs->error);

kprintf_unlock(irqflags);
return;
	arch_show_extended_context();

	arch_print_pre_interrupt_stack(regs);

	kprintf_unlock(irqflags);
}
#endif

void arch_cpu_stop(void)
{
	while (1) {
		cpu_halt();
	}
}

/*@
  @ behavior fs_base:
  @   assumes type == IHK_ASR_X86_FS;
  @   ensures \result == 0;
  @ behavior invaiid_type:
  @   assumes type != IHK_ASR_X86_FS;
  @   ensures \result == -EINVAL;
  @*/
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
int ihk_mc_arch_set_special_register(enum ihk_asr_type type,
                                     unsigned long value);
#else
int ihk_mc_arch_set_special_register(enum ihk_asr_type type,
                                     unsigned long value)
{
	/* GS modification is not permitted */
	switch (type) {
	case IHK_ASR_X86_FS:
		wrmsr(MSR_FS_BASE, value);
		return 0;
	default:
		return -EINVAL;
	}
}
#endif

/*@
  @ behavior fs_base:
  @   assumes type == IHK_ASR_X86_FS;
  @   requires \valid(value);
  @   ensures \result == 0;
  @ behavior invalid_type:
  @   assumes type != IHK_ASR_X86_FS;
  @   ensures \result == -EINVAL;
  @*/
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
int ihk_mc_arch_get_special_register(enum ihk_asr_type type,
                                     unsigned long *value);
#else
int ihk_mc_arch_get_special_register(enum ihk_asr_type type,
                                     unsigned long *value)
{
	/* GS modification is not permitted */
	switch (type) {
	case IHK_ASR_X86_FS:
		*value = rdmsr(MSR_FS_BASE);
		return 0;
	default:
		return -EINVAL;
	}
}
#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
int ihk_mc_get_interrupt_id(int cpu);
#else
int ihk_mc_get_interrupt_id(int cpu)
{
	return get_x86_cpu_local_variable(cpu)->apic_id;
}
#endif

/*@
  @ requires \valid_cpuid(cpu);     // valid CPU logical ID
  @ ensures \result == 0
  @*/
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void x86_issue_ipi_bridge(unsigned long apic_id, int vector)
{
	x86_issue_ipi(apic_id, vector);
}

void x86_interrupt_log_bridge(int event, int cpu, int vector)
{
	if (event == 1) {
		kprintf("%s: invalid CPU id: %d\n",
				"ihk_mc_interrupt_cpu", cpu);
	} else if (event == 2) {
		dkprintf("[%d] ihk_mc_interrupt_cpu: %d\n",
				ihk_mc_get_processor_id(), cpu);
	}
	(void)vector;
}
#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
int ihk_mc_interrupt_cpu(int cpu, int vector);
#else
int ihk_mc_interrupt_cpu(int cpu, int vector)
{
	if (cpu < 0 || cpu >= num_processors) {
		kprintf("%s: invalid CPU id: %d\n", __func__, cpu);
		return -1;
	}
	dkprintf("[%d] ihk_mc_interrupt_cpu: %d\n", ihk_mc_get_processor_id(), cpu);

	x86_issue_ipi(get_x86_cpu_local_variable(cpu)->apic_id, vector);
	return 0;
}
#endif

struct thread *arch_switch_context(struct thread *prev, struct thread *next)
{
	struct thread *last;
	struct mcs_rwlock_node_irqsave lock;

	dkprintf("[%d] schedule: tlsblock_base: 0x%lX\n",
	         ihk_mc_get_processor_id(), next->tlsblock_base);

	/* Set up new TLS.. */
	ihk_mc_init_user_tlsbase(next->uctx, next->tlsblock_base);

#ifdef ENABLE_PERF
	/* Performance monitoring inherit */
	if(next->proc->monitoring_event) {
		if(next->proc->perf_status == PP_RESET)
			perf_reset(next->proc->monitoring_event);
		if(next->proc->perf_status != PP_COUNT) {
			perf_reset(next->proc->monitoring_event);
			perf_start(next->proc->monitoring_event);
		}
	}
#endif

#ifdef PROFILE_ENABLE
	if (prev && prev->profile && prev->profile_start_ts != 0) {
		prev->profile_elapsed_ts +=
			(rdtsc() - prev->profile_start_ts);
		prev->profile_start_ts = 0;
	}

	if (next->profile && next->profile_start_ts == 0) {
		next->profile_start_ts = rdtsc();
	}
#endif

	if (prev) {
		mcs_rwlock_writer_lock(&prev->proc->update_lock, &lock);
		if (prev->proc->status & (PS_DELAY_STOPPED | PS_DELAY_TRACED)) {
			switch (prev->proc->status) {
			case PS_DELAY_STOPPED:
				prev->proc->status = PS_STOPPED;
				break;
			case PS_DELAY_TRACED:
				prev->proc->status = PS_TRACED;
				break;
			default:
				break;
			}
			mcs_rwlock_writer_unlock(&prev->proc->update_lock,
						&lock);

			/* Wake up the parent who tried wait4 and sleeping */
			waitq_wakeup(&prev->proc->parent->waitpid_q);
		} else {
			mcs_rwlock_writer_unlock(&prev->proc->update_lock,
						&lock);
		}

		last = ihk_mc_switch_context(&prev->ctx, &next->ctx, prev);
	}
	else {
		last = ihk_mc_switch_context(NULL, &next->ctx, prev);
	}
	return last;
}

/*@
  @ requires \valid(thread);
  @ ensures thread->fp_regs == NULL;
  @*/
void
release_fp_regs(struct thread *thread)
{
	int	pages;

	if (thread && !thread->fp_regs)
		return;

	pages = (xsave_size + (PAGE_SIZE - 1)) >> PAGE_SHIFT;
	dkprintf("release_fp_regs: pages=%d\n", pages);
	_ihk_mc_free_pages(thread->fp_regs, pages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
	thread->fp_regs = NULL;
}

static int
check_and_allocate_fp_regs(struct thread *thread)
{
	int pages;
	int result = 0;

	if (!xsave_available || xsave_size <= 0) {
		return 0;
	}

	if (!thread->fp_regs) {
		pages = (xsave_size + (PAGE_SIZE - 1)) >> PAGE_SHIFT;
		dkprintf("save_fp_regs: pages=%d\n", pages);
		thread->fp_regs = _ihk_mc_alloc_aligned_pages_node(pages, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);

		if (!thread->fp_regs) {
			kprintf("error: allocating fp_regs pages\n");
			result = -ENOMEM;
			goto out;
		}

		memset(thread->fp_regs, 0, pages * PAGE_SIZE);
	}
out:
	return result;
}

/*@
  @ requires \valid(thread);
  @*/
int
save_fp_regs(struct thread *thread)
{
	int ret = 0;

	ret = check_and_allocate_fp_regs(thread);
	if (ret) {
		goto out;
	}

	if (xsave_available) {
		unsigned int low, high;

		/* Request full save of x87, SSE, AVX and AVX-512 states */
		low = (unsigned int)xsave_mask;
		high = (unsigned int)(xsave_mask >> 32);

		asm volatile("xsave %0" : : "m" (*thread->fp_regs), "a" (low), "d" (high) 
			: "memory");

		dkprintf("fp_regs for TID %d saved\n", thread->tid);
	}
out:
	return ret;
}

int copy_fp_regs(struct thread *from, struct thread *to)
{
	int ret = 0;

	if (from->fp_regs != NULL) {
		ret = check_and_allocate_fp_regs(to);
		if (!ret) {
			memcpy(to->fp_regs,
				from->fp_regs,
				sizeof(fp_regs_struct));
		}
	}
	return ret;
}

static void restore_default_fp_regs(struct thread *thread)
{
	static int mcexec_v10_fp_default_logs;

	if (mcexec_v10_fp_default_logs < 16) {
		kprintf("mcexec_v10: fp_default cpu=%d pid=%d tid=%d xsave=%d initial=%d\n",
			ihk_mc_get_processor_id(),
			thread && thread->proc ? thread->proc->pid : -1,
			thread ? thread->tid : -1,
			xsave_available, initial_fp_regs_available);
		mcexec_v10_fp_default_logs++;
	}

	if (xsave_available && initial_fp_regs_available) {
		unsigned int low = (unsigned int)xsave_mask;
		unsigned int high = (unsigned int)(xsave_mask >> 32);

		asm volatile("xrstor %0" : : "m" (*(fp_regs_struct *)initial_fp_regs),
				"a" (low), "d" (high) : "memory");
	}
	else {
		unsigned int default_mxcsr = 0x1f80;

		asm volatile("finit" ::: "memory");
#ifdef ENABLE_SSE
		asm volatile("ldmxcsr %0" : : "m" (default_mxcsr) : "memory");
#endif
	}
}

/*@
  @ requires \valid(thread);
  @ assigns thread->fp_regs;
  @*/
void
restore_fp_regs(struct thread *thread)
{
	if (!thread || !thread->fp_regs) {
		restore_default_fp_regs(thread);
		return;
	}

	if (xsave_available) {
		unsigned int low, high;

		/* Request full restore of x87, SSE, AVX and AVX-512 states */
		low = (unsigned int)xsave_mask;
		high = (unsigned int)(xsave_mask >> 32);

		asm volatile("xrstor %0" : : "m" (*thread->fp_regs), 
				"a" (low), "d" (high));
		
		dkprintf("fp_regs for TID %d restored\n", thread->tid);
	}

	// XXX: why release??
	//release_fp_regs(thread);
}

void clear_fp_regs(void)
{
	struct cpu_local_var *v = get_this_cpu_local_var();

	if (v->idle.fp_regs) {
		restore_fp_regs(&v->idle);
	}
	else {
		restore_default_fp_regs(&v->idle);
	}
}

ihk_mc_user_context_t *lookup_user_context(struct thread *thread)
{
#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	return x86_lookup_user_context_body_result(thread, get_this_cpu_local_var()->current,
			PS_INTERRUPTIBLE | PS_UNINTERRUPTIBLE |
			PS_STOPPED | PS_TRACED, &x86_thread_context_offsets);
#else
	ihk_mc_user_context_t *uctx = thread->uctx;

	if ((!(thread->status & (PS_INTERRUPTIBLE | PS_UNINTERRUPTIBLE
						| PS_STOPPED | PS_TRACED))
				&& (thread != get_this_cpu_local_var()->current))
			|| !uctx->is_gpr_valid) {
		return NULL;
	}

	if (!uctx->is_sr_valid) {
		uctx->sr.fs_base = thread->tlsblock_base;
		uctx->sr.gs_base = 0;
		uctx->sr.ds = 0;
		uctx->sr.es = 0;
		uctx->sr.fs = 0;
		uctx->sr.gs = 0;

		uctx->is_sr_valid = 1;
	}

	return uctx;
#endif
} /* lookup_user_context() */

extern long do_arch_prctl(unsigned long code, unsigned long address);
#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
void
ihk_mc_init_user_tlsbase(ihk_mc_user_context_t *ctx,
                         unsigned long tls_base_addr)
{
	do_arch_prctl(ARCH_SET_FS, tls_base_addr);
}
#endif

#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
void arch_flush_icache_all(void)
{
	return;
}
#endif

/*@
  @ assigns \nothing;
  @*/
#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
void init_tick(void)
{
	dkprintf("init_tick():\n");
	return;
}
#else
void init_tick(void);
#endif

/*@
  @ assigns \nothing;
  @*/
#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
void init_delay(void)
{
	dkprintf("init_delay():\n");
	return;
}
#else
void init_delay(void);
#endif

/*@
  @ assigns \nothing;
  @*/
#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
void sync_tick(void)
{
	dkprintf("sync_tick():\n");
	return;
}
#else
void sync_tick(void);
#endif

#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
static int is_pvclock_available(void)
{
	uint32_t eax;
	uint32_t ebx;
	uint32_t ecx;
	uint32_t edx;

	dkprintf("is_pvclock_available()\n");
#define KVM_CPUID_SIGNATURE 0x40000000
	asm ("cpuid" : "=a"(eax), "=b"(ebx), "=c"(ecx), "=d"(edx)
			: "a" (KVM_CPUID_SIGNATURE));
	if ((eax && (eax < 0x40000001))
			|| (ebx != 0x4b4d564b)
			|| (ecx != 0x564b4d56)
			|| (edx != 0x0000004d)) {
		dkprintf("is_pvclock_available(): false (not kvm)\n");
		return 0;
	}

#define KVM_CPUID_FEATURES 0x40000001
	asm ("cpuid" : "=a"(eax)
			: "a"(KVM_CPUID_FEATURES)
			: "%ebx", "%ecx", "%edx");
#define KVM_FEATURE_CLOCKSOURCE2 3
	if (eax & (1 << KVM_FEATURE_CLOCKSOURCE2)) {
#define MSR_KVM_SYSTEM_TIME_NEW 0x4b564d01
		pvti_msr = MSR_KVM_SYSTEM_TIME_NEW;
		dkprintf("is_pvclock_available(): true (new)\n");
		return 1;
	}
#define KVM_FEATURE_CLOCKSOURCE 0
	else if (eax & (1 << KVM_FEATURE_CLOCKSOURCE)) {
#define MSR_KVM_SYSTEM_TIME 0x12
		pvti_msr = MSR_KVM_SYSTEM_TIME;
		dkprintf("is_pvclock_available(): true (old)\n");
		return 1;
	}

	dkprintf("is_pvclock_available(): false (not supported)\n");
	return 0;
} /* is_pvclock_available() */

#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
int arch_setup_pvclock(void);
#else
int arch_setup_pvclock(void)
{
	size_t size;
	int npages;

	dkprintf("arch_setup_pvclock()\n");
	if (!is_pvclock_available()) {
		dkprintf("arch_setup_pvclock(): not supported\n");
		return 0;
	}

	size = num_processors * sizeof(*pvti);
	npages = (size + PAGE_SIZE - 1) / PAGE_SIZE;
	pvti_npages = npages;

	pvti = _ihk_mc_alloc_aligned_pages_node(npages, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (!pvti) {
		ekprintf("arch_setup_pvclock: allocate_pages failed.\n");
		return -ENOMEM;
	}
	memset(pvti, 0, PAGE_SIZE*npages);

	dkprintf("arch_setup_pvclock(): ok\n");
	return 0;
} /* arch_setup_pvclock() */
#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void arch_start_pvclock(void);
#else
void arch_start_pvclock(void)
{
	int cpu;
	intptr_t phys;

	dkprintf("arch_start_pvclock()\n");
	if (!pvti) {
		dkprintf("arch_start_pvclock(): not supported\n");
		return;
	}

	cpu = ihk_mc_get_processor_id();
	phys = virt_to_phys(&pvti[cpu]);
#define KVM_SYSTEM_TIME_ENABLE 0x1
	wrmsr(pvti_msr, phys|KVM_SYSTEM_TIME_ENABLE);
	dkprintf("arch_start_pvclock(): ok\n");
	return;
} /* arch_start_pvclock() */
#endif

#define KVM_CPUID_SIGNATURE	0x40000000

#ifndef MCKERNEL_RUST_X86_CPU_HELPERS
int running_on_kvm(void) {
	static const char signature[12] = "KVMKVMKVM\0\0";
	const uint32_t *sigptr = (const uint32_t *)signature;
	uint64_t op;
	uint64_t eax;
	uint64_t ebx;
	uint64_t ecx;
	uint64_t edx;

	op = KVM_CPUID_SIGNATURE;
	asm volatile("cpuid" : "=a"(eax),"=b"(ebx),"=c"(ecx),"=d"(edx) : "a" (op));

	if (ebx == sigptr[0] && ecx == sigptr[1] && edx == sigptr[2]) {
		return 1;
	}

	return 0;
}
#endif

void
mod_nmi_ctx(void *nmi_ctx, void (*func)())
{
	unsigned long *l = nmi_ctx;
	int i;
	unsigned long flags;

	asm volatile("pushf; pop %0" : "=r"(flags) : : "memory", "cc");
	for (i = 0; i < 22; i++)
		l[i] = l[i + 5];
	l[i++] = (unsigned long)func;		// return address
	l[i++] = 0x20;				// KERNEL CS
	l[i++] = flags & ~RFLAGS_IF;		// rflags (disable interrupt)
	l[i++] = (unsigned long)(l + 27);	// ols rsp
	l[i++] = 0x28;				// KERNEL DS
}

void arch_save_panic_regs(void *irq_regs)
{
	struct thread *current = get_this_cpu_local_var()->current;
	struct x86_user_context *regs =
		(struct x86_user_context *)irq_regs;
	struct x86_cpu_local_variables *x86v =
		get_x86_cpu_local_variable(ihk_mc_get_processor_id());
	struct segment_regs {
		uint32_t rflags;
		uint32_t cs;
		uint32_t ss;
		uint32_t ds;
		uint32_t es;
		uint32_t fs;
		uint32_t gs;
	} *sregs;

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
	if (x86_arch_save_panic_regs_body_result(regs,
				current ? &current->ctx : NULL,
				x86v->panic_regs, &x86v->paniced, USER_END,
				(unsigned long)enter_user_mode,
				x86_cpu_ulong_log_bridge) == 0) {
		return;
	}
#endif

	/* Kernel space? */
	if (regs->gpr.rip > USER_END) {
		x86v->panic_regs[0] = regs->gpr.rax;
		x86v->panic_regs[1] = regs->gpr.rbx;
		x86v->panic_regs[2] = regs->gpr.rcx;
		x86v->panic_regs[3] = regs->gpr.rdx;
		x86v->panic_regs[4] = regs->gpr.rsi;
		x86v->panic_regs[5] = regs->gpr.rdi;
		x86v->panic_regs[6] = regs->gpr.rbp;
		x86v->panic_regs[7] = regs->gpr.rsp;
		x86v->panic_regs[8] = regs->gpr.r8;
		x86v->panic_regs[9] = regs->gpr.r9;
		x86v->panic_regs[10] = regs->gpr.r10;
		x86v->panic_regs[11] = regs->gpr.r11;
		x86v->panic_regs[12] = regs->gpr.r12;
		x86v->panic_regs[13] = regs->gpr.r13;
		x86v->panic_regs[14] = regs->gpr.r14;
		x86v->panic_regs[15] = regs->gpr.r15;
		x86v->panic_regs[16] = regs->gpr.rip;
		sregs = (struct segment_regs *)&x86v->panic_regs[17];
		sregs->rflags = regs->gpr.rflags;
		sregs->cs = regs->gpr.cs;
		sregs->ss = regs->gpr.ss;
		sregs->ds = regs->sr.ds;
		sregs->es = regs->sr.es;
		sregs->fs = regs->sr.fs;
		sregs->gs = regs->sr.gs;
	}
	/* User-space, show kernel context */
	else {
		kprintf("%s: in user-space: %p\n", __func__, regs->gpr.rip);
		x86v->panic_regs[0] = 0;
		x86v->panic_regs[1] = current->ctx.rbx;
		x86v->panic_regs[2] = 0;
		x86v->panic_regs[3] = 0;
		x86v->panic_regs[4] = current->ctx.rsi;
		x86v->panic_regs[5] = current->ctx.rdi;
		x86v->panic_regs[6] = current->ctx.rbp;
		x86v->panic_regs[7] = current->ctx.rsp;
		x86v->panic_regs[8] = 0;
		x86v->panic_regs[9] = 0;
		x86v->panic_regs[10] = 0;
		x86v->panic_regs[11] = 0;
		x86v->panic_regs[12] = regs->gpr.r12;
		x86v->panic_regs[13] = regs->gpr.r13;
		x86v->panic_regs[14] = regs->gpr.r14;
		x86v->panic_regs[15] = regs->gpr.r15;
		x86v->panic_regs[16] = (unsigned long)enter_user_mode;
		sregs = (struct segment_regs *)&x86v->panic_regs[17];
		sregs->rflags = regs->gpr.rflags;
		sregs->cs = regs->gpr.cs;
		sregs->ss = regs->gpr.ss;
		sregs->ds = regs->sr.ds;
		sregs->es = regs->sr.es;
		sregs->fs = regs->sr.fs;
		sregs->gs = regs->sr.gs;
	}

	x86v->paniced = 1;
}

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
void arch_clear_panic(void);
#else
void arch_clear_panic(void)
{
	struct x86_cpu_local_variables *x86v =
		get_x86_cpu_local_variable(ihk_mc_get_processor_id());

	x86v->paniced = 0;
}
#endif

#ifdef MCKERNEL_RUST_X86_CPU_HELPERS
int arch_cpu_read_write_register(
		struct ihk_os_cpu_register *desc,
		enum mcctrl_os_cpu_operation op);
#else
int arch_cpu_read_write_register(
		struct ihk_os_cpu_register *desc,
		enum mcctrl_os_cpu_operation op)
{
	if (op == MCCTRL_OS_CPU_READ_REGISTER) {
		desc->val = rdmsr(desc->addr);
	}
	else if (op == MCCTRL_OS_CPU_WRITE_REGISTER) {
		wrmsr(desc->addr, desc->val);
	}
	else {
		return -1;
	}

	return 0;
}
#endif

extern int nmi_mode;
extern long freeze_thaw(void *nmi_ctx);

void multi_nm_interrupt_handler(void *irq_regs)
{
	dkprintf("%s: ...\n", __func__);
	switch (nmi_mode) {
	case 1:
	case 2:
		/* mode == 1 or 2, for FREEZER NMI */
		dkprintf("%s: freeze mode NMI catch. (nmi_mode=%d)\n",
			 __func__, nmi_mode);
		freeze_thaw(NULL);
		break;

	case 0:
		/* mode == 0, for MEMDUMP NMI */
		arch_save_panic_regs(irq_regs);
		ihk_mc_query_mem_areas();
		/* memdump-nmi is halted McKernel, break is unnecessary. */
		/* fall through */
	case 3:
		/* mode == 3, for SHUTDOWN-WAIT NMI */
		kprintf("%s: STOP\n", __func__);
		while (nmi_mode != 4)
			cpu_halt();
		break;

	case 4:
		/* mode == 4, continue NMI */
		arch_clear_panic();
		if (!ihk_mc_get_processor_id()) {
			ihk_mc_clear_dump_page_completion();
		}
		kprintf("%s: RESUME, nmi_mode: %d\n", __func__, nmi_mode);
		break;

	default:
		ekprintf("%s: Unknown nmi-mode(%d) detected.\n",
			 __func__, nmi_mode);
		break;
	}
}

/*** end of file ***/
