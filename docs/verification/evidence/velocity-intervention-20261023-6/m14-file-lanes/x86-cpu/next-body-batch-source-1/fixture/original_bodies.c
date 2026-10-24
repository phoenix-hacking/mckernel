/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual original bodies; symbol/provider aliases only. */
#include <ihk/context.h>
extern int interrupt_from_user(void*);
extern void cpu_enable_interrupt(void);
extern void check_sig_pending(void);
extern void check_need_resched(void);
extern void check_signal(unsigned long,void*,int);
extern int fixture_stack_snprintf(char*,unsigned long,const char*,...);
extern int fixture_stack_print(const char*,...);
#define snprintf fixture_stack_snprintf
#define __kprintf fixture_stack_print
struct stack {
	struct stack *rbp;
	unsigned long eip;
};
#define STACK_BUF_LEN (1024-sizeof("[  0]: "))
void original_print_stack(struct stack *rbp, unsigned long first) {
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
void
original_mod_nmi_raw(void *nmi_ctx, void (*func)())
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
void original_interrupt_exit(struct x86_user_context *regs)
{
	if (interrupt_from_user(regs)) {
		cpu_enable_interrupt();
		check_sig_pending();
		check_need_resched();
		check_signal(0, regs, -1);
	}
}

#include <registers.h>
extern unsigned long fixture_nmi_capture_flags(void);
void
original_mod_nmi_pure(void *nmi_ctx, void (*func)())
{
	unsigned long *l = nmi_ctx;
	int i;
	unsigned long flags;

	flags = fixture_nmi_capture_flags();
	for (i = 0; i < 22; i++)
		l[i] = l[i + 5];
	l[i++] = (unsigned long)func;		// return address
	l[i++] = 0x20;				// KERNEL CS
	l[i++] = flags & ~RFLAGS_IF;		// rflags (disable interrupt)
	l[i++] = (unsigned long)(l + 27);	// ols rsp
	l[i++] = 0x28;				// KERNEL DS
}
