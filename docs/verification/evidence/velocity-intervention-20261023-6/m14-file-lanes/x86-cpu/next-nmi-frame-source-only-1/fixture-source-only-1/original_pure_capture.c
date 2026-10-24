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
