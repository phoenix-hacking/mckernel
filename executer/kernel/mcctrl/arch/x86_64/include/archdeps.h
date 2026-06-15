/* archdeps.h COPYRIGHT FUJITSU LIMITED 2017 */
#ifndef __HEADER_MCCTRL_X86_64_ARCHDEPS_H
#define __HEADER_MCCTRL_X86_64_ARCHDEPS_H

#ifdef POSTK_DEBUG_ARCH_DEP_100 /* rus_mmap() setting vm_flags arch depend defined */
#include <linux/mm.h>
#endif /* POSTK_DEBUG_ARCH_DEP_100 */

extern int translate_rva_to_rpa(ihk_os_t os, unsigned long rpt, unsigned long rva,
				unsigned long *rpap, unsigned long *pgsizep);

#define PFN_WRITE_COMBINED _PAGE_PWT

extern int mcctrl_pte_is_write_combined_result(unsigned long flags);

#define ARCH_PERF_COUNTER_START	0

#if LINUX_VERSION_CODE < KERNEL_VERSION(3,7,0)
static const unsigned long arch_rus_vm_flags = VM_RESERVED | VM_MIXEDMAP;
#else
static const unsigned long arch_rus_vm_flags = VM_DONTDUMP | VM_MIXEDMAP;
#endif

extern int xchg4(int *ptr, int x);

enum x86_pf_error_code {
	PF_PROT     =       1 << 0,
	PF_WRITE    =       1 << 1,
	PF_USER     =       1 << 2,
	PF_RSVD     =       1 << 3,
	PF_INSTR    =       1 << 4,

	PF_PATCH    =       1 << 29,
	PF_POPULATE =       1 << 30,
};

#endif /* __HEADER_MCCTRL_X86_64_ARCHDEPS_H */
