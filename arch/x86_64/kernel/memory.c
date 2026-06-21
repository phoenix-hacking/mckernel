/* memory.c COPYRIGHT FUJITSU LIMITED 2018 */
/**
 * \file memory.c
 *  License details are found in the file LICENSE.
 * \brief
 *  Acquire physical pages and manipulate page table entries.
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2015  RIKEN AICS
 */
/*
 * HISTORY
 */

#include <ihk/cpu.h>
#include <ihk/atomic.h>
#include <ihk/mm.h>
#include <types.h>
#include <memory.h>
#include <string.h>
#include <errno.h>
#include <list.h>
#include <process.h>
#include <arch-memory-helpers.h>
#include <page.h>
#include <cls.h>
#include <kmalloc.h>
#include <rusage_private.h>
#include <ihk/debug.h>

//#define DEBUG

#ifdef DEBUG
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

static char *last_page;
extern char _head[], _end[];

extern unsigned long linux_page_offset_base;
extern unsigned long x86_kernel_phys_base;

#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
#define X86_MEMORY_PUBLIC_BRIDGE
#else
#define X86_MEMORY_PUBLIC_BRIDGE static
#endif

#ifndef MCKERNEL_RUST_PTE_HELPERS
unsigned long STACK_TOP(const struct vm_regions *region)
{
	return region->user_end;
}

uint64_t PM_STATUS(uint64_t nr)
{
	return (nr << PM_STATUS_OFFSET) & PM_STATUS_MASK;
}

uint64_t PM_PSHIFT(uint64_t x)
{
	return (x << PM_PSHIFT_OFFSET) & PM_PSHIFT_MASK;
}

uint64_t PM_PFRAME(uint64_t x)
{
	return x & PM_PFRAME_MASK;
}

unsigned long ALIGN_DOWN(unsigned long x, unsigned long align)
{
	return x & ~(align - 1);
}

unsigned long ALIGN_UP(unsigned long x, unsigned long align)
{
	return ALIGN_DOWN(x + align - 1, align);
}

int pfn_is_write_combined(uintptr_t pfn)
{
	return ((pfn & PFL1_PWT) && !(pfn & PFL1_PCD));
}

int pte_is_null(pte_t *ptep)
{
	return (*ptep == PTE_NULL);
}

int pte_is_present(pte_t *ptep)
{
	return !!(*ptep & PF_PRESENT);
}

int pte_is_writable(pte_t *ptep)
{
	return !!(*ptep & PF_WRITABLE);
}

int pte_is_dirty(pte_t *ptep, size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE:	return !!(*ptep & PFL1_DIRTY);
	case PTL2_SIZE:	return !!(*ptep & PFL2_DIRTY);
	case PTL3_SIZE:	return !!(*ptep & PFL3_DIRTY);
	default:
		return !!(*ptep & PTATTR_DIRTY);
	}
}

int pte_is_fileoff(pte_t *ptep, size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE:	return !!(*ptep & PFL1_FILEOFF);
	case PTL2_SIZE:	return !!(*ptep & PFL2_FILEOFF);
	case PTL3_SIZE:	return !!(*ptep & PFL3_FILEOFF);
	default:
		return !!(*ptep & PTATTR_FILEOFF);
	}
}

void pte_update_phys(pte_t *ptep, unsigned long phys)
{
	*ptep = (*ptep & ~PT_PHYSMASK) | (phys & PT_PHYSMASK);
}

uintptr_t pte_get_phys(pte_t *ptep)
{
	return (*ptep & PT_PHYSMASK);
}

off_t pte_get_off(pte_t *ptep, size_t pgsize)
{
	return (off_t)(*ptep & PAGE_MASK);
}

enum ihk_mc_pt_attribute pte_get_attr(pte_t *ptep, size_t pgsize)
{
	enum ihk_mc_pt_attribute attr;

	attr = *ptep & attr_mask;
	if (*ptep & PFLX_PWT) {
		if (*ptep & PFLX_PCD)
			attr |= PTATTR_UNCACHABLE;
		else
			attr |= PTATTR_WRITE_COMBINED;
	}
	if (((pgsize == PTL2_SIZE) && (*ptep & PFL2_SIZE))
			|| ((pgsize == PTL3_SIZE) && (*ptep & PFL3_SIZE)))
		attr |= PTATTR_LARGEPAGE;

	return attr;
}

void pte_make_null(pte_t *ptep, size_t pgsize)
{
	*ptep = PTE_NULL;
}

void pte_make_fileoff(off_t off, enum ihk_mc_pt_attribute ptattr,
		      size_t pgsize, pte_t *ptep)
{
	uint64_t attr;

	attr = ptattr & ~PAGE_MASK;

	switch (pgsize) {
	case PTL1_SIZE:	attr |= PFL1_FILEOFF;			break;
	case PTL2_SIZE:	attr |= PFL2_FILEOFF | PFL2_SIZE;	break;
	case PTL3_SIZE:	attr |= PFL3_FILEOFF | PFL3_SIZE;	break;
	default:
		attr |= PTATTR_FILEOFF;
		break;
	}
	*ptep = (off & PAGE_MASK) | attr;
}

void pte_xchg(pte_t *ptep, pte_t *valp)
{
	*valp = atomic_xchg_ulong(ptep, *valp);
}

void pte_clear_dirty(pte_t *ptep, size_t pgsize)
{
	uint64_t mask;

	switch (pgsize) {
	default:
	case PTL1_SIZE:	mask = ~PFL1_DIRTY;	break;
	case PTL2_SIZE:	mask = ~PFL2_DIRTY;	break;
	case PTL3_SIZE:	mask = ~PFL3_DIRTY;	break;
	}

	asm volatile ("lock andq %0,%1" :: "r"(mask), "m"(*ptep));
}

void pte_set_dirty(pte_t *ptep, size_t pgsize)
{
	uint64_t mask;

	switch (pgsize) {
	default:
	case PTL1_SIZE:	mask = PFL1_DIRTY;	break;
	case PTL2_SIZE:	mask = PFL2_DIRTY;	break;
	case PTL3_SIZE:	mask = PFL3_DIRTY;	break;
	}

	asm volatile ("lock orq %0,%1" :: "r"(mask), "m"(*ptep));
}

int pte_is_contiguous(pte_t *ptep)
{
	return 0;
}

int pgsize_is_contiguous(size_t pgsize)
{
	return 0;
}

int pgsize_to_tbllv(size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE:	return 1;
	case PTL2_SIZE:	return 2;
	case PTL3_SIZE:	return 3;
	case PTL4_SIZE:	return 4;
	default:
		return 0;
	}
}

int pgsize_to_pgshift(size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE:	return PTL1_SHIFT;
	case PTL2_SIZE:	return PTL2_SHIFT;
	case PTL3_SIZE:	return PTL3_SHIFT;
	case PTL4_SIZE:	return PTL4_SHIFT;
	default: return -EINVAL;
	}
}

size_t tbllv_to_pgsize(int level)
{
	switch (level) {
	case 1: return PTL1_SIZE;
	case 2: return PTL2_SIZE;
	case 3: return PTL3_SIZE;
	case 4: return PTL4_SIZE;
	default:
		return 0;
	}
}

size_t tbllv_to_contpgsize(int level)
{
	return 0;
}

int tbllv_to_contpgshift(int level)
{
	return 0;
}

pte_t *get_contiguous_head(pte_t *__ptep, size_t __pgsize)
{
	return __ptep;
}

pte_t *get_contiguous_tail(pte_t *__ptep, size_t __pgsize)
{
	return __ptep;
}

int page_is_contiguous_head(pte_t *ptep, size_t pgsize)
{
	return 0;
}

int page_is_contiguous_tail(pte_t *ptep, size_t pgsize)
{
	return 0;
}

void arch_adjust_allocate_page_size(struct page_table *pt,
				    uintptr_t fault_addr,
				    pte_t *ptep,
				    void **pgaddrp,
				    size_t *pgsizep)
{
}
#endif

X86_MEMORY_PUBLIC_BRIDGE unsigned long x86_arch_mem_virt_to_phys_bridge(void *addr)
{
	return virt_to_phys(addr);
}

X86_MEMORY_PUBLIC_BRIDGE void *x86_arch_mem_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_early_alloc_panic_bridge(int reason)
{
	switch (reason) {
	case 1:
		panic("Early allocator is already finalized. Do not use it.\n");
		break;
	case 2:
		panic("Early allocator: Out of memory\n");
		break;
	}
}

X86_MEMORY_PUBLIC_BRIDGE void **x86_early_alloc_last_page_slot_bridge(void)
{
	return (void **)&last_page;
}

X86_MEMORY_PUBLIC_BRIDGE unsigned long x86_early_alloc_end_bridge(void)
{
	return (unsigned long)_end;
}

X86_MEMORY_PUBLIC_BRIDGE unsigned long x86_bootstrap_mem_end_bridge(void)
{
	return bootstrap_mem_end;
}

X86_MEMORY_PUBLIC_BRIDGE void x86_early_alloc_invalidate_bridge(void)
{
}

static void x86_mem_cpuid_edx_bridge(unsigned long op, unsigned long *edxp)
{
	unsigned long edx;

	asm ("cpuid" : "=d" (edx) : "a" (op) : "%rbx", "%rcx");
	*edxp = edx;
}

static void x86_mem_log_int_bridge(int event, int value)
{
	switch (event) {
	case 1:
		kprintf("use_1gb_page: %d\n", value);
		break;
	}
}

X86_MEMORY_PUBLIC_BRIDGE void x86_mem_log_bridge(int event)
{
	switch (event) {
	case 1:
		kprintf("%s: error, kmalloc not yet initialized\n",
				"ihk_mc_allocate");
		break;
	case 2:
		kprintf("%s: error, kmalloc not yet initialized\n",
				"ihk_mc_free");
		break;
	}
}

X86_MEMORY_PUBLIC_BRIDGE void *x86_kmalloc_bridge(int size, int flag)
{
	return kmalloc_tracked(size, flag, __FILE__, __LINE__);
}

X86_MEMORY_PUBLIC_BRIDGE int x86_kmalloc_initialized_bridge(void)
{
	return get_this_cpu_local_var()->kmalloc_initialized;
}

X86_MEMORY_PUBLIC_BRIDGE void x86_kfree_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

/* Arch specific early allocation routine */
#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void *early_alloc_pages(int nr_pages)
{
	return x86_early_alloc_pages_body_result((void **)&last_page,
			(unsigned long)_end, bootstrap_mem_end, nr_pages,
			x86_arch_mem_virt_to_phys_bridge,
			x86_arch_mem_phys_to_virt_bridge,
			x86_early_alloc_panic_bridge);
}

void early_alloc_invalidate(void)
{
	x86_early_alloc_invalidate_body_result((void **)&last_page);
}
#endif

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void *ihk_mc_allocate(int size, int flag)
{
	(void)flag;
	return x86_ihk_mc_allocate_body_result(
			get_this_cpu_local_var()->kmalloc_initialized, size,
			IHK_MC_AP_NOWAIT, x86_kmalloc_bridge,
			x86_mem_log_bridge);
}

void ihk_mc_free(void *p)
{
	x86_ihk_mc_free_body_result(get_this_cpu_local_var()->kmalloc_initialized,
			p, x86_kfree_bridge, x86_mem_log_bridge);
}
#endif

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void *get_last_early_heap(void)
{
	return x86_get_last_early_heap_body_result((void **)&last_page);
}
#endif

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void flush_tlb(void)
{
	x86_flush_tlb_result();
}

void flush_tlb_single(unsigned long addr)
{
	x86_flush_tlb_single_result(addr);
}
#endif

struct page_table {
	pte_t entry[PT_ENTRIES];
};

static struct page_table *init_pt;
static struct page_table *boot_pt;
static int init_pt_loaded = 0;
static ihk_spinlock_t init_pt_lock;

void load_page_table(struct page_table *pt);
void init_text_area(struct page_table *pt);
void init_low_area(struct page_table *pt);
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void x86_init_normal_area_public(void *pt);
void x86_init_linux_kernel_mapping_public(void *pt);
void x86_init_fixed_area_public(void *pt);
void x86_init_vsyscall_area_public(void *pt);
#endif

X86_MEMORY_PUBLIC_BRIDGE void *x86_pt_alloc_pages_bridge(int nr_pages, int ap_flag);
unsigned long x86_pt_virt_to_phys_bridge(void *addr);
X86_MEMORY_PUBLIC_BRIDGE void *x86_pt_phys_to_virt_bridge(unsigned long phys);
X86_MEMORY_PUBLIC_BRIDGE void x86_pt_free_pages_bridge(void *pt, int nr_pages);
X86_MEMORY_PUBLIC_BRIDGE void x86_pt_destroy_panic_bridge(int reason);
X86_MEMORY_PUBLIC_BRIDGE void x86_pt_destroy_helper_failed_panic_bridge(void);
static void x86_pt_set_page_log_bridge(unsigned long virt);

static int use_1gb_page = 0;

static void check_available_page_size(void)
{
	x86_check_available_page_size_body_result(&use_1gb_page,
			x86_mem_cpuid_edx_bridge, x86_mem_log_int_bridge);
}

static unsigned long setup_l2(struct page_table *pt,
                              unsigned long page_head, unsigned long start,
                              unsigned long end)
{
	return x86_setup_l2_body_result(pt, page_head, start, end,
			x86_pt_virt_to_phys_bridge);
}

static unsigned long setup_l3(struct page_table *pt,
                              unsigned long page_head, unsigned long start,
                              unsigned long end)
{
	return x86_setup_l3_body_result(pt, page_head, start, end,
			IHK_MC_AP_CRITICAL, x86_pt_alloc_pages_bridge,
			x86_pt_virt_to_phys_bridge);
}

static struct page_table *__alloc_new_pt(ihk_mc_ap_flag ap_flag)
{
	return x86_pt_alloc_zeroed_result(ap_flag, x86_pt_alloc_pages_bridge);
}

/*
 * XXX: Confusingly, L4 and L3 automatically add PRESENT,
 *      but L2 and L1 do not!
 */

enum ihk_mc_pt_attribute attr_mask
		= 0
		| PTATTR_FILEOFF
		| PTATTR_WRITABLE
		| PTATTR_USER
		| PTATTR_ACTIVE
		| 0;
#define	ATTR_MASK	attr_mask

X86_MEMORY_PUBLIC_BRIDGE unsigned long x86_attr_mask_bridge(void)
{
	return ATTR_MASK;
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void enable_ptattr_no_execute(void)
{
	x86_enable_ptattr_no_execute_body_result((unsigned long *)&attr_mask,
			PTATTR_NO_EXECUTE);
}
#endif

#if 0
static unsigned long attr_to_l4attr(enum ihk_mc_pt_attribute attr)
{
	return (attr & ATTR_MASK) | PFL4_PRESENT;
}
#endif
static unsigned long attr_to_l3attr(enum ihk_mc_pt_attribute attr)
{
	return x86_attr_to_l3attr_result(attr, ATTR_MASK);
}
static unsigned long attr_to_l2attr(enum ihk_mc_pt_attribute attr)
{
	return x86_attr_to_l2attr_result(attr, ATTR_MASK);
}
static unsigned long attr_to_l1attr(enum ihk_mc_pt_attribute attr)
{
	return x86_attr_to_l1attr_result(attr, ATTR_MASK);
}

#define PTLX_SHIFT(index) PTL ## index ## _SHIFT

#define GET_VIRT_INDEX(virt, index, dest) \
	dest = ((virt) >> PTLX_SHIFT(index)) & (PT_ENTRIES - 1)

#define GET_VIRT_INDICES(virt, l4i, l3i, l2i, l1i) \
	l4i = ((virt) >> PTL4_SHIFT) & (PT_ENTRIES - 1); \
	l3i = ((virt) >> PTL3_SHIFT) & (PT_ENTRIES - 1); \
	l2i = ((virt) >> PTL2_SHIFT) & (PT_ENTRIES - 1); \
	l1i = ((virt) >> PTL1_SHIFT) & (PT_ENTRIES - 1)

#define	GET_INDICES_VIRT(l4i, l3i, l2i, l1i)		\
		( ((uint64_t)(l4i) << PTL4_SHIFT)	\
		| ((uint64_t)(l3i) << PTL3_SHIFT)	\
		| ((uint64_t)(l2i) << PTL2_SHIFT)	\
		| ((uint64_t)(l1i) << PTL1_SHIFT)	\
		)

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void set_pte(pte_t *ppte, unsigned long phys, enum ihk_mc_pt_attribute attr)
{
	*ppte = x86_set_pte_value_result(phys, attr, ATTR_MASK);
}
#endif


#if 0
/* 
 * get_pte() 
 *
 * Descripton: walks the page tables (creates tables if not existing)
 *             and returns a pointer to the PTE corresponding to the
 *             virtual address.
 */
pte_t *get_pte(struct page_table *pt, void *virt, enum ihk_mc_pt_attribute attr, ihk_mc_ap_flag ap_flag)
{
	int l4idx, l3idx, l2idx, l1idx;
	unsigned long v = (unsigned long)virt;
	struct page_table *newpt;

	if (!pt) {
		pt = init_pt;
	}

	x86_pt_indices_result(v, &l4idx, &l3idx, &l2idx, &l1idx);

    /* TODO: more detailed attribute check */
	if (pt->entry[l4idx] & PFL4_PRESENT) {
		pt = phys_to_virt(pt->entry[l4idx] & PAGE_MASK);
	} else {
		if((newpt = __alloc_new_pt(ap_flag)) == NULL)
			return NULL;
		pt->entry[l4idx] = virt_to_phys(newpt) | attr_to_l4attr(attr);
		pt = newpt;
	}

	if (pt->entry[l3idx] & PFL3_PRESENT) {
		pt = phys_to_virt(pt->entry[l3idx] & PAGE_MASK);
	} else {
		if((newpt = __alloc_new_pt(ap_flag)) == NULL)
			return NULL;
		pt->entry[l3idx] = virt_to_phys(newpt) | attr_to_l3attr(attr);
		pt = newpt;
	}

	/* PTATTR_LARGEPAGE */
	if (attr & PTATTR_LARGEPAGE) {
		return &(pt->entry[l2idx]);
	}

	/* Requested regular page, but large is allocated? */
	if (pt->entry[l2idx] & PFL2_SIZE) {
		return NULL;
	}

	if (pt->entry[l2idx] & PFL2_PRESENT) {
		pt = phys_to_virt(pt->entry[l2idx] & PAGE_MASK);
	} else {
		if((newpt = __alloc_new_pt(ap_flag)) == NULL)
			return NULL;
		pt->entry[l2idx] = virt_to_phys(newpt) | attr_to_l2attr(attr)
			| PFL2_PRESENT;
		pt = newpt;
	}

	return &(pt->entry[l1idx]);
}
#endif

static void x86_pt_set_page_log_bridge(unsigned long virt)
{
	kprintf("EBUSY: page table for 0x%lX is already set\n", virt);
}

static int __set_pt_page(struct page_table *pt, void *virt, unsigned long phys,
                         enum ihk_mc_pt_attribute attr)
{
	int in_kernel = x86_pt_kernel_lock_needed_result((unsigned long)virt);
	unsigned long init_pt_lock_flags;
	int ret;

	init_pt_lock_flags = 0;	/* for avoidance of warning */
	if (in_kernel) {
		init_pt_lock_flags = ihk_mc_spinlock_lock(&init_pt_lock);
	}

	ret = x86_pt_set_page_body_result(pt, init_pt, (unsigned long)virt,
			phys, attr, ATTR_MASK, x86_pt_alloc_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_pt_set_page_log_bridge);

	if (in_kernel) {
		ihk_mc_spinlock_unlock(&init_pt_lock, init_pt_lock_flags);
	}
	return ret;
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
static int __clear_pt_page(struct page_table *pt, void *virt, int largepage)
{
	return x86_pt_clear_page_result(pt, init_pt, (unsigned long)virt,
			largepage, x86_pt_phys_to_virt_bridge);
}

uint64_t ihk_mc_pt_virt_to_pagemap(struct page_table *pt, unsigned long virt)
{
	return x86_pt_virt_to_pagemap_result(pt, init_pt, virt,
			x86_pt_phys_to_virt_bridge);
}

int ihk_mc_pt_virt_to_phys_size(struct page_table *pt,
                           const void *virt,
						   unsigned long *phys,
						   unsigned long *size)
{
	return x86_pt_virt_to_phys_size_result(pt, init_pt,
			(unsigned long)virt, phys, size,
			x86_pt_phys_to_virt_bridge);
}

int ihk_mc_pt_virt_to_phys(struct page_table *pt,
                           const void *virt, unsigned long *phys)
{
	return ihk_mc_pt_virt_to_phys_size(pt, virt, phys, NULL);
}
#endif

X86_MEMORY_PUBLIC_BRIDGE void x86_pt_print_log_bridge(int event, int level,
		unsigned long value, int index)
{
	switch (event) {
	case X86_PT_PRINT_LOG_TABLE:
		__kprintf("l%d table: 0x%lX l%didx: %d \n",
				level, value, level, index);
		break;
	case X86_PT_PRINT_LOG_NOT_PRESENT:
		__kprintf("0x%lX l%didx not present! \n", value, level);
		break;
	case X86_PT_PRINT_LOG_ENTRY:
		__kprintf("l%d entry: 0x%lX\n", level, value);
		break;
	case X86_PT_PRINT_LOG_LARGE:
		if (level == 3)
			__kprintf("l3 entry is 1G page\n");
		else if (level == 2)
			__kprintf("l2 entry is 2M page\n");
		break;
	}
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
int ihk_mc_pt_print_pte(struct page_table *pt, void *virt)
{
	return x86_pt_print_pte_body_result(pt, init_pt, (unsigned long)virt,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_pt_print_log_bridge);
}
#endif

#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
int set_pt_large_page(struct page_table *pt, void *virt, unsigned long phys,
                      enum ihk_mc_pt_attribute attr);
int ihk_mc_pt_set_large_page(page_table_t pt, void *virt,
                       unsigned long phys, enum ihk_mc_pt_attribute attr);
int ihk_mc_pt_set_page(page_table_t pt, void *virt,
                       unsigned long phys, enum ihk_mc_pt_attribute attr);
#else
int set_pt_large_page(struct page_table *pt, void *virt, unsigned long phys,
                      enum ihk_mc_pt_attribute attr)
{
	return __set_pt_page(pt, virt, phys, attr | PTATTR_LARGEPAGE
	                     | PTATTR_ACTIVE);
}

int ihk_mc_pt_set_large_page(page_table_t pt, void *virt,
                       unsigned long phys, enum ihk_mc_pt_attribute attr)
{
	return __set_pt_page(pt, virt, phys, attr | PTATTR_LARGEPAGE
	                     | PTATTR_ACTIVE);
}

int ihk_mc_pt_set_page(page_table_t pt, void *virt,
                       unsigned long phys, enum ihk_mc_pt_attribute attr)
{
	return __set_pt_page(pt, virt, phys, attr | PTATTR_ACTIVE);
}
#endif

X86_MEMORY_PUBLIC_BRIDGE void *x86_pt_alloc_pages_bridge(int nr_pages, int ap_flag)
{
	return _ihk_mc_alloc_aligned_pages_node(nr_pages, PAGE_P2ALIGN, (ihk_mc_ap_flag)ap_flag, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}

unsigned long x86_pt_virt_to_phys_bridge(void *addr)
{
	return virt_to_phys(addr);
}

X86_MEMORY_PUBLIC_BRIDGE int x86_pt_set_page_bridge(void *pt, unsigned long virt,
		unsigned long phys, unsigned long attr)
{
	return __set_pt_page(pt, (void *)virt, phys, attr);
}

#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
int ihk_mc_pt_prepare_map(page_table_t p, void *virt, unsigned long size,
                          enum ihk_mc_pt_prepare_flag flag);
#else
int ihk_mc_pt_prepare_map(page_table_t p, void *virt, unsigned long size,
                          enum ihk_mc_pt_prepare_flag flag)
{
	return x86_pt_prepare_map_result(p, init_pt, (unsigned long)virt,
			size, flag, PTATTR_WRITABLE,
			x86_pt_alloc_pages_bridge, x86_pt_virt_to_phys_bridge,
			x86_pt_set_page_bridge);
}
#endif

#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
struct page_table *ihk_mc_pt_create(ihk_mc_ap_flag ap_flag);
#else
struct page_table *ihk_mc_pt_create(ihk_mc_ap_flag ap_flag)
{
	return x86_pt_create_result(init_pt, ap_flag, x86_pt_alloc_pages_bridge);
}

static void destroy_page_table(int level, struct page_table *pt)
{
	int ret = x86_pt_destroy_table_result(level, pt,
			x86_pt_phys_to_virt_bridge,
			x86_pt_free_pages_bridge,
			x86_pt_destroy_panic_bridge);

	if (ret) {
		panic("destroy_page_table: helper failed");
	}
	return;
}
#endif

X86_MEMORY_PUBLIC_BRIDGE void *x86_pt_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_pt_free_pages_bridge(void *pt, int nr_pages)
{
	_ihk_mc_free_pages(pt, nr_pages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_pt_destroy_panic_bridge(int reason)
{
	if (reason == X86_PT_DESTROY_PANIC_LEVEL) {
		panic("destroy_page_table: level is out of range");
	}
	if (reason == X86_PT_DESTROY_PANIC_NULL) {
		panic("destroy_page_table: pt is NULL");
	}
}

X86_MEMORY_PUBLIC_BRIDGE void x86_pt_destroy_helper_failed_panic_bridge(void)
{
	panic("destroy_page_table: helper failed");
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
static void x86_pt_destroy_bridge(int level, void *pt)
{
	destroy_page_table(level, pt);
}

void ihk_mc_pt_destroy(struct page_table *pt)
{
	x86_pt_destroy_root_result(pt, x86_pt_destroy_bridge);
	return;
}
#else
void ihk_mc_pt_destroy(struct page_table *pt);
#endif

#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
int ihk_mc_pt_clear_page(page_table_t pt, void *virt);
int ihk_mc_pt_clear_large_page(page_table_t pt, void *virt);
#else
int ihk_mc_pt_clear_page(page_table_t pt, void *virt)
{
	return __clear_pt_page(pt, virt, 0);
}

int ihk_mc_pt_clear_large_page(page_table_t pt, void *virt)
{
	return __clear_pt_page(pt, virt, 1);
}
#endif

typedef int walk_pte_fn_t(void *args, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end);

#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
int walk_pte_l1(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args);
int walk_pte_l2(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args);
int walk_pte_l3(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args);
int walk_pte_l4(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args);
#else
static int walk_pte_l1(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args)
{
	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			PTL2_SIZE, PTL1_SHIFT,
			(x86_walk_pte_callback_t)funcp, args, NULL,
			PT_PHYSMASK);
}

static int walk_pte_l2(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args)
{
	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			PTL3_SIZE, PTL2_SHIFT,
			(x86_walk_pte_callback_t)funcp, args, NULL,
			PT_PHYSMASK);
}

static int walk_pte_l3(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args)
{
	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			PTL4_SIZE, PTL3_SHIFT,
			(x86_walk_pte_callback_t)funcp, args, NULL,
			PT_PHYSMASK);
}

static int walk_pte_l4(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args)
{
	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			0, PTL4_SHIFT, (x86_walk_pte_callback_t)funcp, args,
			NULL, PT_PHYSMASK);
}
#endif

static void *x86_split_alloc_new_pt_bridge(int nr_pages, int ap_flag)
{
	if (nr_pages != 1)
		return NULL;
	return __alloc_new_pt((ihk_mc_ap_flag)ap_flag);
}

static void *x86_split_phys_to_page_bridge(unsigned long phys)
{
	return phys_to_page(phys);
}

static void x86_split_page_map_bridge(void *page)
{
	page_map(page);
}

static void x86_split_rss_add_bridge(size_t size, size_t pgsize)
{
	memory_stat_rss_add(size, pgsize);
}

static void x86_split_rss_sub_bridge(size_t size, size_t pgsize)
{
	memory_stat_rss_sub(size, pgsize);
}

static int x86_split_page_unmap_bridge(void *page)
{
	return page_unmap(page);
}

static void x86_split_log_bridge(int event, unsigned long value, size_t size,
		size_t pgsize, void *page)
{
	switch (event) {
	case X86_SPLIT_LARGE_PAGE_LOG_INVALID_PGSIZE:
		ekprintf("split_large_page:invalid pgsize %#lx\n", pgsize);
		break;
	case X86_SPLIT_LARGE_PAGE_LOG_ALLOC_FAILED:
		ekprintf("split_large_page:__alloc_new_pt failed\n");
		break;
	case X86_SPLIT_LARGE_PAGE_LOG_RSS_ADD:
		dkprintf("%lx+,%s: calling memory_stat_rss_add(),size=%ld,pgsize=%ld\n",
				value, "split_large_page", size, pgsize);
		break;
	case X86_SPLIT_LARGE_PAGE_LOG_RSS_SUB:
		dkprintf("%lx-,%s: calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n",
				value, "split_large_page", size, pgsize);
		break;
	case X86_SPLIT_LARGE_PAGE_LOG_PAGE_UNMAP:
		kprintf("split_large_page:page_unmap:%p\n", page);
		break;
	default:
		break;
	}
}

static void x86_split_panic_bridge(void)
{
	panic("split_large_page:page_unmap\n");
}

static int split_large_page(pte_t *ptep, size_t pgsize)
{
	return x86_split_large_page_body_result(ptep, pgsize,
			IHK_MC_AP_NOWAIT, x86_split_alloc_new_pt_bridge,
			x86_pt_virt_to_phys_bridge,
			x86_split_phys_to_page_bridge,
			x86_split_page_map_bridge,
			x86_split_rss_add_bridge,
			x86_split_rss_sub_bridge,
			x86_split_page_unmap_bridge,
			x86_split_log_bridge,
			x86_split_panic_bridge);
}

struct visit_pte_args {
	page_table_t pt;
	enum visit_pte_flag flags;
	int pgshift;
	pte_visitor_t *funcp;
	void *arg;
};

#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
int visit_pte_l1(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end);
int x86_visit_walk_l1_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args);
int visit_pte_l2(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end);
int x86_visit_walk_l2_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args);
int visit_pte_l3(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end);
int x86_visit_walk_l3_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args);
int visit_pte_l4(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end);
int x86_visit_walk_l4_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args);
int visit_pte_range(page_table_t pt, void *start0, void *end0, int pgshift,
		enum visit_pte_flag flags, pte_visitor_t *funcp, void *arg);
int visit_pte_l1_safe(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end);
int x86_visit_walk_l1_safe_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args);
int visit_pte_l2_safe(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end);
int x86_visit_walk_l2_safe_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args);
int visit_pte_l3_safe(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end);
int x86_visit_walk_l3_safe_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args);
int visit_pte_l4_safe(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end);
int x86_visit_walk_l4_safe_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args);
int visit_pte_range_safe(page_table_t pt, void *start0, void *end0, int pgshift,
		enum visit_pte_flag flags, pte_visitor_t *funcp, void *arg);
#else
static int visit_pte_l1(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end)
{
	struct visit_pte_args *args = arg0;

	return x86_visit_pte_leaf_result(args->arg, args->pt,
			(unsigned long *)ptep, base,
			args->flags & VPTEF_SKIP_NULL, PTL1_SHIFT,
			(x86_visit_pte_fn_t)args->funcp);
}

static int x86_visit_walk_l1_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l1(pt, base, start, end, &visit_pte_l1, args);
}
#endif

X86_MEMORY_PUBLIC_BRIDGE void x86_visit_pte_log_bridge(int event,
		int level_shift)
{
	if (event != X86_VISIT_PTE_LOG_SPLIT) {
		return;
	}

	switch (level_shift) {
	case PTL2_SHIFT:
		ekprintf("visit_pte_l2:split large page\n");
		break;
	case PTL3_SHIFT:
		ekprintf("visit_pte_l3:split large page\n");
		break;
	default:
		ekprintf("visit_pte_l%d:split large page\n", level_shift);
		break;
	}
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
static int visit_pte_l2(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end)
{
	struct visit_pte_args *args = arg0;

	return x86_visit_pte_level_result(args->arg, args->pt,
			(unsigned long *)ptep, base, start, end,
			args->flags & VPTEF_SKIP_NULL, 0, args->pgshift,
			PTL2_SIZE, PTL2_SHIFT, PFL2_SIZE, 0, 1, 1,
			PFL2_PDIR_ATTR, x86_pt_alloc_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_visit_walk_l1_bridge, arg0,
			(x86_visit_pte_fn_t)args->funcp,
			x86_visit_pte_log_bridge);
}

static int x86_visit_walk_l2_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l2(pt, base, start, end, &visit_pte_l2, args);
}

static int visit_pte_l3(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end)
{
	struct visit_pte_args *args = arg0;

	return x86_visit_pte_level_result(args->arg, args->pt,
			(unsigned long *)ptep, base, start, end,
			args->flags & VPTEF_SKIP_NULL, 0, args->pgshift,
			PTL3_SIZE, PTL3_SHIFT, PFL3_SIZE, 0, use_1gb_page, 1,
			PFL3_PDIR_ATTR, x86_pt_alloc_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_visit_walk_l2_bridge, arg0,
			(x86_visit_pte_fn_t)args->funcp,
			x86_visit_pte_log_bridge);
}

static int x86_visit_walk_l3_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l3(pt, base, start, end, &visit_pte_l3, args);
}

static int visit_pte_l4(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end)
{
	struct visit_pte_args *args = arg0;

	return x86_visit_pte_root_result((unsigned long *)ptep, base, start,
			end, args->flags & VPTEF_SKIP_NULL, 1,
			PFL4_PDIR_ATTR, x86_pt_alloc_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_visit_walk_l3_bridge, arg0);
}

static int x86_visit_walk_l4_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l4(pt, base, start, end, &visit_pte_l4, args);
}

int visit_pte_range(page_table_t pt, void *start0, void *end0, int pgshift,
		enum visit_pte_flag flags, pte_visitor_t *funcp, void *arg)
{
	const uintptr_t start = (uintptr_t)start0;
	const uintptr_t end = (uintptr_t)end0;
	struct visit_pte_args args;

	args.pt = pt;
	args.flags = flags;
	args.funcp = funcp;
	args.arg = arg;
	args.pgshift = pgshift;

	return x86_visit_pte_range_dispatch_result(pt, start, end, &args,
			x86_visit_walk_l4_bridge);
}
#endif

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
static int x86_walk_page_address_check(unsigned long phys)
{
	return ihk_mc_chk_page_address(phys);
}
#endif

#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
int walk_pte_l1_safe(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args);
int walk_pte_l2_safe(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args);
int walk_pte_l3_safe(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args);
int walk_pte_l4_safe(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args);
#else
static int walk_pte_l1_safe(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args)
{
	if (!pt)
		return 0;

	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			PTL2_SIZE, PTL1_SHIFT,
			(x86_walk_pte_callback_t)funcp, args,
			x86_walk_page_address_check, PT_PHYSMASK);
}

static int walk_pte_l2_safe(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args)
{
	if (!pt)
		return 0;

	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			PTL3_SIZE, PTL2_SHIFT,
			(x86_walk_pte_callback_t)funcp, args,
			x86_walk_page_address_check, PT_PHYSMASK);
}

static int walk_pte_l3_safe(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args)
{
	if (!pt)
		return 0;

	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			PTL4_SIZE, PTL3_SHIFT,
			(x86_walk_pte_callback_t)funcp, args,
			x86_walk_page_address_check, PT_PHYSMASK);
}

static int walk_pte_l4_safe(struct page_table *pt, uint64_t base, uint64_t start,
		uint64_t end, walk_pte_fn_t *funcp, void *args)
{
	if (!pt)
		return 0;

	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			0, PTL4_SHIFT, (x86_walk_pte_callback_t)funcp, args,
			x86_walk_page_address_check, PT_PHYSMASK);
}
#endif

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
static int visit_pte_l1_safe(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end)
{
	struct visit_pte_args *args = arg0;

	return x86_visit_pte_leaf_result(args->arg, args->pt,
			(unsigned long *)ptep, base, 1, PTL1_SHIFT,
			(x86_visit_pte_fn_t)args->funcp);
}

static int x86_visit_walk_l1_safe_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l1_safe(pt, base, start, end, &visit_pte_l1_safe,
			args);
}

static int visit_pte_l2_safe(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end)
{
	struct visit_pte_args *args = arg0;

	return x86_visit_pte_level_result(args->arg, args->pt,
			(unsigned long *)ptep, base, start, end, 1, 1,
			args->pgshift, PTL2_SIZE, PTL2_SHIFT, PFL2_SIZE,
			1, 1, 0, PFL2_PDIR_ATTR, x86_pt_alloc_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_visit_walk_l1_safe_bridge, arg0,
			(x86_visit_pte_fn_t)args->funcp,
			x86_visit_pte_log_bridge);
}

static int x86_visit_walk_l2_safe_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l2_safe(pt, base, start, end, &visit_pte_l2_safe,
			args);
}

static int visit_pte_l3_safe(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end)
{
	struct visit_pte_args *args = arg0;

	return x86_visit_pte_level_result(args->arg, args->pt,
			(unsigned long *)ptep, base, start, end, 1, 1,
			args->pgshift, PTL3_SIZE, PTL3_SHIFT, PFL3_SIZE,
			1, use_1gb_page, 0, PFL3_PDIR_ATTR,
			x86_pt_alloc_pages_bridge, x86_pt_virt_to_phys_bridge,
			x86_pt_phys_to_virt_bridge, x86_visit_walk_l2_safe_bridge,
			arg0, (x86_visit_pte_fn_t)args->funcp,
			x86_visit_pte_log_bridge);
}

static int x86_visit_walk_l3_safe_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l3_safe(pt, base, start, end, &visit_pte_l3_safe,
			args);
}

static int visit_pte_l4_safe(void *arg0, pte_t *ptep, uintptr_t base,
		uintptr_t start, uintptr_t end)
{
	return x86_visit_pte_root_result((unsigned long *)ptep, base, start,
			end, 1, 0, PFL4_PDIR_ATTR, x86_pt_alloc_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_visit_walk_l3_safe_bridge, arg0);
}

static int x86_visit_walk_l4_safe_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l4_safe(pt, base, start, end, &visit_pte_l4_safe,
			args);
}

int visit_pte_range_safe(page_table_t pt, void *start0, void *end0, int pgshift,
		enum visit_pte_flag flags, pte_visitor_t *funcp, void *arg)
{
	const uintptr_t start = (uintptr_t)start0;
	const uintptr_t end = (uintptr_t)end0;
	struct visit_pte_args args;

	args.pt = pt;
	args.flags = flags;
	args.funcp = funcp;
	args.arg = arg;
	args.pgshift = pgshift;

	return x86_visit_pte_range_dispatch_result(pt, start, end, &args,
			x86_visit_walk_l4_safe_bridge);
}
#endif

struct clear_range_args {
	int free_physical;
	struct memobj *memobj;
	struct process_vm *vm;
	unsigned long *addr;
	int nr_addr;
	int max_nr_addr;
};

static void x86_clear_memobj_flush_bridge(void *memobj, unsigned long phys,
		size_t pgsize)
{
	memobj_flush_page(memobj, phys, pgsize);
}

static void *x86_clear_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}

static void x86_clear_free_pages_user_bridge(void *addr, int nr_pages)
{
	_ihk_mc_free_pages(addr, nr_pages, IHK_MC_PG_USER, __FILE__, __LINE__);
}

static int x86_clear_page_unmap_bridge(void *page)
{
	return page_unmap(page);
}

static void x86_clear_rss_sub_bridge(size_t size, size_t pgsize)
{
	memory_stat_rss_sub(size, pgsize);
}

static void x86_clear_memobj_rss_sub_bridge(void *memobj, size_t size,
		size_t pgsize)
{
	rusage_memory_stat_sub(memobj, size, pgsize);
}

static void x86_clear_effect_log_bridge(int event, unsigned long base,
		unsigned long phys, size_t pgsize)
{
	switch (event) {
	case X86_CLEAR_EFFECT_FREE_ANON:
		dkprintf("%lx-,%s: freed anonymous page,base=%lx,size=%ld,pgsize=%ld\n",
				phys, __FUNCTION__, base, pgsize, pgsize);
		break;
	case X86_CLEAR_EFFECT_XPMEM_KEEP:
		dkprintf("%s: XPMEM attach,phys=%lx\n", __FUNCTION__, phys);
		break;
	case X86_CLEAR_EFFECT_FREE_UNMAPPED:
		dkprintf("%lx-,%s: freed unmapped memobj page,base=%lx,size=%ld,pgsize=%ld\n",
				phys, __FUNCTION__, base, pgsize, pgsize);
		break;
	case X86_CLEAR_EFFECT_CHILD_FREE:
		dkprintf("%s: freed child page table at base=%lx,size=%ld\n",
				__FUNCTION__, base, pgsize);
		break;
	default:
		break;
	}
}

static void x86_clear_range_top_log_bridge(int event, void *pt,
		unsigned long start, unsigned long end, int free_physical)
{
	switch (event) {
	case X86_CLEAR_TOP_LOG_INVALID:
		ekprintf("clear_range(%p,%p,%p,%x):"
				"invalid start and/or end.\n",
				pt, (void *)start, (void *)end, free_physical);
		break;
	case X86_CLEAR_TOP_LOG_ALLOC_FAILED:
		ekprintf("%s: error: allocating address array\n", "clear_range");
		break;
	default:
		break;
	}
}

static void x86_clear_range_log_bridge(int event, void *args,
		unsigned long *ptep, unsigned long base, unsigned long start,
		unsigned long end, int error, int level_shift, unsigned long phys)
{
	const char *fn;

	switch (level_shift) {
	case PTL2_SHIFT:
		fn = "clear_range_l2";
		break;
	case PTL3_SHIFT:
		fn = "clear_range_l3";
		break;
	default:
		fn = "clear_range_l4";
		break;
	}

	switch (event) {
	case X86_CLEAR_RANGE_LOG_SPLIT:
		ekprintf("%s(%p,%p,%lx,%lx,%lx):"
				"split page. %d\n",
				fn, args, ptep, base, start, end, error);
		break;
	case X86_CLEAR_RANGE_LOG_LARGE_PHYS:
		dkprintf("%s: phys=%ld, pte_get_phys(&old),PTL3_SIZE\n",
				fn, phys);
		break;
	default:
		break;
	}
}

static int clear_range_old_action(struct clear_range_args *args, pte_t old,
		size_t pgsize, unsigned long *physp, struct page **pagep,
		int *fileoffp)
{
	int is_fileoff;
	int is_dirty;
	int has_page;
	int page_in_memobj;
	unsigned int memobj_flags = args->memobj ? args->memobj->flags : 0;

	x86_clear_range_old_entry_result(old, pgsize, physp, &is_fileoff,
			&is_dirty);
	if (fileoffp)
		*fileoffp = is_fileoff;

	*pagep = NULL;
	if (!is_fileoff)
		*pagep = phys_to_page(*physp);

	has_page = *pagep != NULL;
	page_in_memobj = has_page && page_is_in_memobj(*pagep);

	return x86_clear_range_old_action_result(is_fileoff,
			args->free_physical, has_page, page_in_memobj,
			is_dirty, args->memobj != NULL,
			memobj_flags & (MF_ZEROFILL | MF_PRIVATE),
			memobj_flags & MF_XPMEM);
}

static int x86_clear_old_action_bridge(void *args0, unsigned long old,
		size_t pgsize, unsigned long *physp, void **pagep,
		int *fileoffp)
{
	struct page *page = NULL;
	int ret;

	ret = clear_range_old_action(args0, old, pgsize, physp, &page,
			fileoffp);
	if (pagep)
		*pagep = page;

	return ret;
}

static int clear_range_l1(void *args0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct clear_range_args *args = args0;

	//dkprintf("%s: %lx,%lx,%lx\n", __FUNCTION__, base, start, end);

	return x86_clear_range_leaf_body_result(args0, ptep, base, start, end,
			args->vm, args->addr, &args->nr_addr,
			args->max_nr_addr, ihk_mc_get_processor_id(),
			args->free_physical, args->memobj,
			x86_clear_old_action_bridge,
			(x86_clear_remote_flush_fn_t)remote_flush_tlb_array_cpumask,
			x86_clear_memobj_flush_bridge,
			x86_clear_phys_to_virt_bridge,
			x86_clear_free_pages_user_bridge,
			x86_clear_page_unmap_bridge, x86_clear_rss_sub_bridge,
			x86_clear_memobj_rss_sub_bridge,
			x86_clear_effect_log_bridge);
}

static int x86_clear_range_walk_l1_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l1(pt, base, start, end, &clear_range_l1, args);
}

static int clear_range_l2(void *args0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct clear_range_args *args = args0;

	//dkprintf("%s: %lx,%lx,%lx\n", __FUNCTION__, base, start, end);

	return x86_clear_range_level_body_result(args0, ptep, base, start,
			end, PTL2_SHIFT, PTL2_SIZE, PFL2_SIZE, 1,
			args->vm, args->addr, &args->nr_addr,
			args->max_nr_addr, ihk_mc_get_processor_id(),
			args->free_physical, args->memobj,
			x86_clear_old_action_bridge,
			x86_clear_phys_to_virt_bridge,
			x86_clear_range_walk_l1_bridge,
			(x86_clear_remote_flush_fn_t)remote_flush_tlb_array_cpumask,
			x86_pt_free_pages_bridge,
			x86_clear_memobj_flush_bridge,
			x86_clear_free_pages_user_bridge,
			x86_clear_page_unmap_bridge, x86_clear_rss_sub_bridge,
			x86_clear_memobj_rss_sub_bridge,
			x86_clear_range_log_bridge,
			x86_clear_effect_log_bridge);
}

static int x86_clear_range_walk_l2_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l2(pt, base, start, end, &clear_range_l2, args);
}

static int clear_range_l3(void *args0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct clear_range_args *args = args0;

	//dkprintf("%s: %lx,%lx,%lx\n", __FUNCTION__, base, start, end);

	return x86_clear_range_level_body_result(args0, ptep, base, start,
			end, PTL3_SHIFT, PTL3_SIZE, PFL3_SIZE, use_1gb_page,
			args->vm, args->addr, &args->nr_addr,
			args->max_nr_addr, ihk_mc_get_processor_id(),
			args->free_physical, args->memobj,
			x86_clear_old_action_bridge,
			x86_clear_phys_to_virt_bridge,
			x86_clear_range_walk_l2_bridge,
			(x86_clear_remote_flush_fn_t)remote_flush_tlb_array_cpumask,
			x86_pt_free_pages_bridge,
			x86_clear_memobj_flush_bridge,
			x86_clear_free_pages_user_bridge,
			x86_clear_page_unmap_bridge, x86_clear_rss_sub_bridge,
			x86_clear_memobj_rss_sub_bridge,
			x86_clear_range_log_bridge,
			x86_clear_effect_log_bridge);
}

static int x86_clear_range_walk_l3_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l3(pt, base, start, end, &clear_range_l3, args);
}

static int clear_range_l4(void *args0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	//dkprintf("%s: %lx,%lx,%lx\n", __FUNCTION__, base, start, end);

	return x86_clear_range_root_body_result(args0, ptep, base, start, end,
			x86_clear_phys_to_virt_bridge,
			x86_clear_range_walk_l3_bridge);
}

static int x86_clear_range_walk_l4_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l4(pt, base, start, end, &clear_range_l4, args);
}

#define TLB_INVALID_ARRAY_PAGES	(4)

static int clear_range(struct page_table *pt, struct process_vm *vm,
		uintptr_t start, uintptr_t end, int free_physical,
		struct memobj *memobj)
{
	int error;
	struct clear_range_args args;

	dkprintf("%s: %p,%lx,%lx,%d,%p\n",
			 __FUNCTION__, pt, start, end, free_physical, memobj);

	error = x86_clear_range_top_result(pt, vm, start, end,
			vm->region.user_start, vm->region.user_end,
			free_physical, memobj && (memobj->flags & MF_DEV_FILE),
			memobj && (memobj->flags & MF_PREMAP),
			vm->proc->straight_va &&
			(void *)start == vm->proc->straight_va &&
			(void *)end == (vm->proc->straight_va +
				vm->proc->straight_len),
			memobj, &args.addr, &args.nr_addr, &args.max_nr_addr,
			&args.free_physical, (void **)&args.memobj,
			(void **)&args.vm, TLB_INVALID_ARRAY_PAGES, PAGE_SIZE,
			&args, x86_pt_alloc_pages_bridge, x86_pt_free_pages_bridge,
			x86_clear_range_walk_l4_bridge,
			(x86_clear_remote_flush_fn_t)remote_flush_tlb_array_cpumask,
			ihk_mc_get_processor_id(),
			x86_clear_range_top_log_bridge);

	return error;
}

int ihk_mc_pt_clear_range(page_table_t pt, struct process_vm *vm, 
		void *start, void *end)
{
#define	KEEP_PHYSICAL	0
	return clear_range(pt, vm, (uintptr_t)start, (uintptr_t)end,
			KEEP_PHYSICAL, NULL);
}

int ihk_mc_pt_free_range(page_table_t pt, struct process_vm *vm, 
		void *start, void *end, struct memobj *memobj)
{
#define	FREE_PHYSICAL	1
	return clear_range(pt, vm, (uintptr_t)start, (uintptr_t)end,
			FREE_PHYSICAL, memobj);
}

static int x86_set_range_clear_bridge(void *pt, void *vm,
		unsigned long start, unsigned long end, int free_physical,
		void *memobj)
{
	return clear_range(pt, vm, start, end, free_physical, memobj);
}

static int x86_set_range_rss_add_bridge(void *range, unsigned long phys,
		size_t size, size_t pgsize)
{
	return rusage_memory_stat_add(range, phys, size, pgsize);
}

static const char *x86_set_range_fn_name(int level_shift)
{
	switch (level_shift) {
	case PTL1_SHIFT:
		return "set_range_l1";
	case PTL2_SHIFT:
		return "set_range_l2";
	case PTL3_SHIFT:
		return "set_range_l3";
	default:
		return "set_range_l4";
	}
}

static const char *x86_set_range_walk_name(int level_shift)
{
	switch (level_shift) {
	case PTL2_SHIFT:
		return "walk_pte_l1";
	case PTL3_SHIFT:
		return "walk_pte_l2";
	case PTL4_SHIFT:
		return "walk_pte_l3";
	default:
		return "walk_pte_l4";
	}
}

static void x86_set_range_log_bridge(int event, int level_shift,
		unsigned long base, unsigned long start, unsigned long end,
		int error, unsigned long pte, unsigned long phys, size_t size,
		size_t pgsize, int rss_called)
{
	const char *fn = x86_set_range_fn_name(level_shift);

	switch (event) {
	case X86_SET_RANGE_LOG_BUSY:
		ekprintf("%s(%lx,%lx,%lx):page exists. %d %lx\n",
				fn, base, start, end, error, pte);
		break;
	case X86_SET_RANGE_LOG_ALLOC_FAILED:
		ekprintf("%s(%lx,%lx,%lx):__alloc_new_pt failed. %d %lx\n",
				fn, base, start, end, error, pte);
		break;
	case X86_SET_RANGE_LOG_WALK_FAILED:
		ekprintf("%s(%lx,%lx,%lx):%s failed. %d %lx\n",
				fn, base, start, end,
				x86_set_range_walk_name(level_shift), error, pte);
		break;
	case X86_SET_RANGE_LOG_MAP_LARGE:
		if (level_shift == PTL2_SHIFT) {
			dkprintf("%s(%lx,%lx,%lx):2MiB page. %d %lx\n",
					fn, base, start, end, error, pte);
		} else if (level_shift == PTL3_SHIFT) {
			dkprintf("%s(%lx,%lx,%lx):1GiB page. %d %lx\n",
					fn, base, start, end, error, pte);
		}
		break;
	case X86_SET_RANGE_LOG_RSS_ADD:
		dkprintf("%lx+,%s: calling memory_stat_rss_add(),base=%lx,phys=%lx,size=%ld,pgsize=%ld\n",
				phys, fn, base, phys, (long)size, (long)pgsize);
		break;
	case X86_SET_RANGE_LOG_RSS_SKIP:
		(void)rss_called;
		dkprintf("%s: !calling memory_stat_rss_add(),base=%lx,phys=%lx,size=%ld,pgsize=%ld\n",
				fn, base, phys, (long)size, (long)pgsize);
		break;
	default:
		break;
	}
}

#if 0
struct change_attr_args {
	pte_t clrpte;
	pte_t setpte;
};

static int change_attr_range_l1(void *arg0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct change_attr_args *args = arg0;
	int action;

	action = x86_change_attr_leaf_action_result(*ptep, PFL1_FILEOFF);
	if (action == X86_CHANGE_ATTR_ENOENT) {
		return -ENOENT;
	}

	x86_pte_apply_attr_result(ptep, args->clrpte, args->setpte);
	return 0;
}

static int change_attr_range_l2(void *arg0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct change_attr_args *args = arg0;
	int error;
	struct page_table *pt;
	int action;

	action = x86_change_attr_entry_action_result(*ptep, base, start, end,
			PTL2_SIZE, PFL2_SIZE, PFL2_FILEOFF);
	if (action == X86_CHANGE_ATTR_ENOENT) {
		return -ENOENT;
	}

	if (action == X86_CHANGE_ATTR_SPLIT_ERROR) {
		error = -EINVAL;
		ekprintf("change_attr_range_l2(%p,%p,%lx,%lx,%lx):"
				"split page. %d\n",
				arg0, ptep, base, start, end, error);
		return error;
	}

	if (action == X86_CHANGE_ATTR_APPLY) {
		x86_pte_apply_attr_result(ptep, args->clrpte, args->setpte);
		return 0;
	}

	pt = phys_to_virt(*ptep & PT_PHYSMASK);
	return walk_pte_l1(pt, base, start, end, &change_attr_range_l1, arg0);
}

static int change_attr_range_l3(void *arg0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct change_attr_args *args = arg0;
	int error;
	struct page_table *pt;
	int action;

	action = x86_change_attr_entry_action_result(*ptep, base, start, end,
			PTL3_SIZE, PFL3_SIZE, PFL3_FILEOFF);
	if (action == X86_CHANGE_ATTR_ENOENT) {
		return -ENOENT;
	}

	if (action == X86_CHANGE_ATTR_SPLIT_ERROR) {
		error = -EINVAL;
		ekprintf("change_attr_range_l3(%p,%p,%lx,%lx,%lx):"
				"split page. %d\n",
				arg0, ptep, base, start, end, error);
		return error;
	}

	if (action == X86_CHANGE_ATTR_APPLY) {
		x86_pte_apply_attr_result(ptep, args->clrpte, args->setpte);
		return 0;
	}

	pt = phys_to_virt(*ptep & PT_PHYSMASK);
	return walk_pte_l2(pt, base, start, end, &change_attr_range_l2, arg0);
}

static int change_attr_range_l4(void *arg0, pte_t *ptep, uint64_t base,
		uint64_t start, uint64_t end)
{
	struct page_table *pt;
	int action;

	action = x86_change_attr_entry_action_result(*ptep, base, start, end,
			0, 0, 0);
	if (action == X86_CHANGE_ATTR_ENOENT) {
		return -ENOENT;
	}

	pt = phys_to_virt(*ptep & PT_PHYSMASK);
	return walk_pte_l3(pt, base, start, end, &change_attr_range_l3, arg0);
}
#endif

int ihk_mc_pt_change_attr_range(page_table_t pt, void *start0, void *end0,
		enum ihk_mc_pt_attribute clrattr,
		enum ihk_mc_pt_attribute setattr)
{
	const intptr_t start = (intptr_t)start0;
	const intptr_t end = (intptr_t)end0;

	return x86_pt_change_attr_range_result(pt, start, end,
			attr_to_l1attr(clrattr), attr_to_l1attr(setattr),
			x86_pt_phys_to_virt_bridge);
}

static pte_t *lookup_pte(struct page_table *pt, uintptr_t virt, int pgshift,
		uintptr_t *basep, size_t *sizep, int *p2alignp)
{
	unsigned long base;
	size_t size;
	int p2align;
	pte_t *ptep;

	ptep = (pte_t *)x86_pt_lookup_pte_result(pt, virt, pgshift,
			use_1gb_page, &base, &size, &p2align,
			x86_pt_phys_to_virt_bridge);
	if (basep) *basep = base;
	if (sizep) *sizep = size;
	if (p2alignp) *p2alignp = p2align;
	return ptep;
}

pte_t *ihk_mc_pt_lookup_pte(page_table_t pt, void *virt, int pgshift,
		void **basep, size_t *sizep, int *p2alignp)
{
	pte_t *ptep;
	uintptr_t base;
	size_t size;
	int p2align;

	dkprintf("ihk_mc_pt_lookup_pte(%p,%p,%d)\n", pt, virt, pgshift);
	ptep = lookup_pte(pt, (uintptr_t)virt, pgshift, &base, &size, &p2align);
	if (basep) *basep = (void *)base;
	if (sizep) *sizep = size;
	if (p2alignp) *p2alignp = p2align;
	dkprintf("ihk_mc_pt_lookup_pte(%p,%p,%d): %p %lx %lx %d\n",
			pt, virt, pgshift, ptep, base, size, p2align);
	return ptep;
}

struct set_range_args {
	page_table_t pt;
	uintptr_t phys;
	enum ihk_mc_pt_attribute attr;
	int pgshift;
	uintptr_t diff;
	struct process_vm *vm;
	struct vm_range *range; /* To find pages we don't need to call memory_stat_rss_add() */
};

int set_range_l1(void *args0, pte_t *ptep, uintptr_t base, uintptr_t start,
		uintptr_t end)
{
	struct set_range_args *args = args0;
	int error;

	dkprintf("set_range_l1(%lx,%lx,%lx)\n", base, start, end);

	error = x86_set_range_leaf_body_result(args0, ptep, base, start, end,
			args->pt, args->vm, args->phys, args->attr, ATTR_MASK,
			args->range, x86_set_range_clear_bridge,
			x86_set_range_rss_add_bridge,
			x86_set_range_log_bridge);

	dkprintf("set_range_l1(%lx,%lx,%lx): %d %lx\n",
			base, start, end, error, *ptep);
	return error;
}

static int x86_set_range_walk_l1_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l1(pt, base, start, end, &set_range_l1, args);
}

int set_range_l2(void *args0, pte_t *ptep, uintptr_t base, uintptr_t start,
		uintptr_t end)
{
	struct set_range_args *args = args0;
	int error;

	dkprintf("set_range_l2(%lx,%lx,%lx)\n", base, start, end);

	error = x86_set_range_level_body_result(args0, ptep, base, start, end,
			args->pt, args->vm, args->phys, args->attr, ATTR_MASK,
			args->diff, args->pgshift, PTL2_SHIFT, PTL2_SIZE,
			PFL2_SIZE, 1, PFL2_PDIR_ATTR, args->range,
			x86_pt_alloc_pages_bridge, x86_pt_free_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_set_range_walk_l1_bridge,
			x86_set_range_clear_bridge,
			x86_set_range_rss_add_bridge,
			x86_set_range_log_bridge);
	dkprintf("set_range_l2(%lx,%lx,%lx): %d %lx\n",
			base, start, end, error, *ptep);
	return error;
}

static int x86_set_range_walk_l2_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l2(pt, base, start, end, &set_range_l2, args);
}

int set_range_l3(void *args0, pte_t *ptep, uintptr_t base, uintptr_t start,
		uintptr_t end)
{
	int error;
	struct set_range_args *args = args0;

	dkprintf("set_range_l3(%lx,%lx,%lx)\n", base, start, end);

	error = x86_set_range_level_body_result(args0, ptep, base, start, end,
			args->pt, args->vm, args->phys, args->attr, ATTR_MASK,
			args->diff, args->pgshift, PTL3_SHIFT, PTL3_SIZE,
			PFL3_SIZE, use_1gb_page, PFL3_PDIR_ATTR, args->range,
			x86_pt_alloc_pages_bridge, x86_pt_free_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_set_range_walk_l2_bridge,
			x86_set_range_clear_bridge,
			x86_set_range_rss_add_bridge,
			x86_set_range_log_bridge);
	dkprintf("set_range_l3(%lx,%lx,%lx): %d\n",
			base, start, end, error, *ptep);
	return error;
}

static int x86_set_range_walk_l3_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l3(pt, base, start, end, &set_range_l3, args);
}

int set_range_l4(void *args0, pte_t *ptep, uintptr_t base, uintptr_t start,
		uintptr_t end)
{
	struct set_range_args *args = args0;
	int error;

	dkprintf("set_range_l4(%lx,%lx,%lx)\n", base, start, end);

	error = x86_set_range_level_body_result(args0, ptep, base, start, end,
			args->pt, args->vm, args->phys, args->attr, ATTR_MASK,
			args->diff, args->pgshift, PTL4_SHIFT, 0, 0, 0,
			PFL4_PDIR_ATTR, args->range,
			x86_pt_alloc_pages_bridge, x86_pt_free_pages_bridge,
			x86_pt_virt_to_phys_bridge, x86_pt_phys_to_virt_bridge,
			x86_set_range_walk_l3_bridge,
			x86_set_range_clear_bridge,
			x86_set_range_rss_add_bridge,
			x86_set_range_log_bridge);
	dkprintf("set_range_l4(%lx,%lx,%lx): %d %lx\n",
			base, start, end, error, *ptep);
	return error;
}

static int x86_set_range_walk_l4_bridge(void *pt, unsigned long base,
		unsigned long start, unsigned long end, void *args)
{
	return walk_pte_l4(pt, base, start, end, &set_range_l4, args);
}

int ihk_mc_pt_set_range(page_table_t pt, struct process_vm *vm, void *start, 
		void *end, uintptr_t phys, enum ihk_mc_pt_attribute attr,
		int pgshift, struct vm_range *range, int overwrite)
{
	int error;
	struct set_range_args args;

	dkprintf("ihk_mc_pt_set_range(%p,%p,%p,%lx,%x,%d,%lx-%lx)\n",
			 pt, start, end, phys, attr, pgshift, range->start, range->end);

	error = x86_set_range_top_result(pt, vm, (uintptr_t)start,
			(uintptr_t)end, phys, attr, pgshift, range, &args,
			(void **)&args.pt, (unsigned long *)&args.phys,
			(int *)&args.attr, (unsigned long *)&args.diff,
			(void **)&args.vm, &args.pgshift,
			(void **)&args.range, x86_set_range_walk_l4_bridge,
			x86_set_range_log_bridge);
	dkprintf("ihk_mc_pt_set_range(%p,%p,%p,%lx,%x): %d\n",
			pt, start, end, phys, attr, error);
	return error;
}

static void x86_pt_set_pte_log_bridge(int event, void *pt, pte_t *ptep,
		size_t pgsize, unsigned long phys, unsigned long attr,
		int error, unsigned long current)
{
	switch (event) {
	case X86_PT_SET_PTE_LOG_L2_ALIGN:
		kprintf("%s: error: phys needs to be PTL2_SIZE aligned\n",
				__FUNCTION__);
		break;
	case X86_PT_SET_PTE_LOG_L3_ALIGN:
		kprintf("%s: error: phys needs to be PTL3_SIZE aligned\n",
				__FUNCTION__);
		break;
	case X86_PT_SET_PTE_LOG_PAGE_SIZE:
		ekprintf("ihk_mc_pt_set_pte(%p,%p,%lx,%lx,%x):"
				"page size. %d %lx\n",
				pt, ptep, pgsize, phys, (int)attr,
				error, current);
		break;
	}
}

static void x86_pt_set_pte_panic_bridge(void)
{
	panic("ihk_mc_pt_set_pte:page size");
}

int ihk_mc_pt_set_pte(page_table_t pt, pte_t *ptep, size_t pgsize,
		uintptr_t phys, enum ihk_mc_pt_attribute attr)
{
	int error;

	dkprintf("ihk_mc_pt_set_pte(%p,%p,%lx,%lx,%x)\n",
			pt, ptep, pgsize, phys, attr);

	error = x86_pt_set_pte_body_result(pt, ptep, pgsize, phys, attr,
			ATTR_MASK, use_1gb_page, x86_pt_set_pte_log_bridge,
			x86_pt_set_pte_panic_bridge);
	dkprintf("ihk_mc_pt_set_pte(%p,%p,%lx,%lx,%x): %d %lx\n",
			pt, ptep, pgsize, phys, attr, error, *ptep);
	return error;
}

static pte_t *x86_pt_split_lookup_bridge(void *pt, unsigned long addr,
		int pgshift, unsigned long *pgaddrp, size_t *pgsizep,
		int *p2alignp)
{
	void *pgaddr;
	pte_t *ptep;

	pgaddr = NULL;
	ptep = ihk_mc_pt_lookup_pte(pt, (void *)addr, pgshift,
			pgaddrp ? &pgaddr : NULL, pgsizep, p2alignp);
	if (pgaddrp)
		*pgaddrp = (unsigned long)pgaddr;
	return ptep;
}

static int x86_pt_splitable_bridge(void *page, unsigned int memobj_flags)
{
	return is_splitable(page, memobj_flags);
}

static int x86_pt_split_large_bridge(unsigned long *ptep, size_t pgsize)
{
	return split_large_page(ptep, pgsize);
}

static void x86_pt_split_flush_bridge(void *vm, unsigned long addr,
		int cpu_id)
{
	remote_flush_tlb_cpumask(vm, (intptr_t)addr, cpu_id);
}

static void x86_pt_split_log_bridge(int event, int error)
{
	switch (event) {
	case X86_PT_SPLIT_LOG_NOT_SPLITABLE:
		kprintf("ihk_mc_pt_split:NYI:page break down\n");
		break;
	case X86_PT_SPLIT_LOG_SPLIT_FAILED:
		kprintf("ihk_mc_pt_split:split_large_page failed. %d\n",
				error);
		break;
	default:
		break;
	}
}

int ihk_mc_pt_split(page_table_t pt, struct process_vm *vm,
		struct vm_range *range, void *addr)
{
	unsigned int memobj_flags;

	memobj_flags = range->memobj ? range->memobj->flags : 0;
	return x86_pt_split_body_result(pt, vm, (unsigned long)addr,
			memobj_flags, ihk_mc_get_processor_id(),
			x86_pt_split_lookup_bridge,
			x86_split_phys_to_page_bridge,
			x86_pt_splitable_bridge,
			x86_pt_split_large_bridge,
			x86_pt_split_flush_bridge,
			x86_pt_split_log_bridge);
} /* ihk_mc_pt_split() */

#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
int x86_use_1gb_page_bridge(void)
{
	return use_1gb_page;
}

enum ihk_mc_pt_attribute x86_common_vrflag_to_ptattr_bridge(
		unsigned long flag, uint64_t fault, pte_t *ptep)
{
	return common_vrflag_to_ptattr(flag, fault, ptep);
}

int arch_get_smaller_page_size(void *args, size_t cursize, size_t *newsizep,
		int *p2alignp);
enum ihk_mc_pt_attribute arch_vrflag_to_ptattr(unsigned long flag,
		uint64_t fault, pte_t *ptep);
#else
int arch_get_smaller_page_size(void *args, size_t cursize, size_t *newsizep,
		int *p2alignp)
{
	int error = x86_smaller_page_size_result(cursize, use_1gb_page,
			newsizep, p2alignp);

	/*dkprintf("arch_get_smaller_page_size(%p,%lx): %d %lx %d\n",
	  args, cursize, error, newsize, p2align);*/
	return error;
}

enum ihk_mc_pt_attribute arch_vrflag_to_ptattr(unsigned long flag, uint64_t fault, pte_t *ptep)
{
	enum ihk_mc_pt_attribute attr;

	attr = common_vrflag_to_ptattr(flag, fault, ptep);
	return x86_arch_vrflag_to_ptattr_result(flag, fault, attr);
}
#endif

struct move_args {
	uintptr_t src;
	uintptr_t dest;
	struct process_vm *vm;
	struct vm_range *range;
};

static int x86_move_set_range_bridge(void *pt, void *vm,
		unsigned long start, unsigned long end, unsigned long phys,
		unsigned long attr, int pgshift, void *range, int overwrite)
{
	return ihk_mc_pt_set_range(pt, vm, (void *)start, (void *)end,
			phys, attr, pgshift, range, overwrite);
}

static void x86_move_log_bridge(int event, void *arg, void *pt,
		unsigned long *ptep, unsigned long entry, unsigned long current,
		unsigned long pgaddr, int pgshift, int error)
{
	switch (event) {
	case X86_MOVE_ONE_LOG_FILEOFF:
		kprintf("move_one_page(%p,%p,%p %#lx,%p,%d):fileoff. %d\n",
				arg, pt, ptep, entry, (void *)pgaddr,
				pgshift, error);
		break;
	case X86_MOVE_ONE_LOG_SET_FAILED:
		kprintf("move_one_page(%p,%p,%p %#lx,%p,%d):"
				"set failed. %d\n",
				arg, pt, ptep, current, (void *)pgaddr,
				pgshift, error);
		break;
	default:
		break;
	}
}

static int move_one_page(void *arg0, page_table_t pt, pte_t *ptep, 
		void *pgaddr, int pgshift)
{
	int error;
	struct move_args *args = arg0;

	dkprintf("move_one_page(%p,%p,%p %#lx,%p,%d)\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift);
	error = x86_move_one_page_body_result(arg0, pt, ptep,
			(unsigned long)pgaddr, pgshift, args->src, args->dest,
			args->vm, args->range, x86_move_set_range_bridge,
			x86_move_log_bridge);
	dkprintf("move_one_page(%p,%p,%p %#lx,%p,%d):%d\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
	return error;
}

static int x86_move_visit_range_bridge(void *pt, unsigned long start,
		unsigned long end, int pgshift, int flags,
		x86_visit_pte_fn_t visitor_fn, void *arg)
{
	return visit_pte_range(pt, (void *)start, (void *)end, pgshift,
			(enum visit_pte_flag)flags, (pte_visitor_t *)visitor_fn,
			arg);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_move_flush_tlb_bridge(void)
{
	flush_tlb();
}

int move_pte_range(page_table_t pt, struct process_vm *vm, 
				   void *src, void *dest, size_t size, struct vm_range *range)
{
	int error;
	struct move_args args;

	dkprintf("move_pte_range(%p,%p,%p,%#lx)\n", pt, src, dest, size);
	error = x86_move_pte_range_body_result(pt, (unsigned long)src,
			(unsigned long)dest, size, vm, range, &args,
			&args.src, &args.dest, (void **)&args.vm,
			(void **)&args.range, (x86_visit_pte_fn_t)move_one_page,
			x86_move_visit_range_bridge,
			x86_move_flush_tlb_bridge);
	dkprintf("move_pte_range(%p,%p,%p,%#lx):%d\n",
			pt, src, dest, size, error);
	return error;
}

X86_MEMORY_PUBLIC_BRIDGE void *x86_page_table_init_pt_bridge(void)
{
	return init_pt;
}

X86_MEMORY_PUBLIC_BRIDGE void *x86_page_table_boot_pt_bridge(void)
{
	return boot_pt;
}

X86_MEMORY_PUBLIC_BRIDGE void x86_load_page_table_panic_bridge(void)
{
	panic("load_page_table: helper failed");
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void load_page_table(struct page_table *pt)
{
	int ret;

	ret = x86_load_page_table_body_result(pt, init_pt,
			x86_pt_virt_to_phys_bridge, x86_load_cr3_result);
	if (ret)
		panic("load_page_table: helper failed");
}

void ihk_mc_load_page_table(struct page_table *pt)
{
	load_page_table(pt);
}

struct page_table *get_init_page_table(void)
{
	return init_pt;
}

struct page_table *get_boot_page_table(void)
{
	return boot_pt;
}
#endif

static unsigned long fixed_virt;

X86_MEMORY_PUBLIC_BRIDGE void *x86_map_fixed_area_init_pt_bridge(void)
{
	return init_pt;
}

X86_MEMORY_PUBLIC_BRIDGE unsigned long *x86_map_fixed_area_fixed_virt_slot_bridge(void)
{
	return &fixed_virt;
}

X86_MEMORY_PUBLIC_BRIDGE void x86_map_fixed_area_log_bridge(unsigned long phys,
		unsigned long size, unsigned long virt)
{
	dkprintf("map_fixed: phys: 0x%lx => 0x%lx (%d pages)\n",
			phys & PAGE_MASK, (void *)virt,
			(int)(((phys & (PAGE_SIZE - 1)) + size +
				PAGE_SIZE - 1) >> PAGE_SHIFT));
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
static void init_fixed_area(struct page_table *pt)
{
	int ret;

	(void)pt;
	ret = x86_init_fixed_area_body_result(&fixed_virt, MAP_FIXED_START);
	if (ret)
		panic("init_fixed_area: helper failed");
}
#endif

X86_MEMORY_PUBLIC_BRIDGE void x86_init_fixed_panic_bridge(void)
{
	panic("init_fixed_area: helper failed");
}

X86_MEMORY_PUBLIC_BRIDGE unsigned long x86_init_normal_get_memory_address_bridge(int type,
		int arg)
{
	return ihk_mc_get_memory_address(type, arg);
}

X86_MEMORY_PUBLIC_BRIDGE int x86_init_normal_set_large_bridge(void *pt, unsigned long virt,
		unsigned long phys, unsigned long attr)
{
	return set_pt_large_page(pt, (void *)virt, phys,
			(enum ihk_mc_pt_attribute)attr);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_normal_log_bridge(int event, unsigned long a,
		unsigned long b, unsigned long c)
{
	switch (event) {
	case X86_INIT_NORMAL_LOG_RANGE:
		kprintf("map_start = %lx, map_end = %lx, virt %lx\n",
				a, b, (void *)c);
		break;
	case X86_INIT_NORMAL_LOG_SET_FAILED:
		kprintf("%s: error setting mapping for 0x%lx\n",
				"init_normal_area", a);
		break;
	default:
		break;
	}
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_normal_panic_bridge(void)
{
	panic("init_normal_area: helper failed");
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_text_log_bridge(int event, unsigned long a,
		unsigned long b, unsigned long c)
{
	(void)b;
	(void)c;

	switch (event) {
	case X86_INIT_TEXT_LOG_LPAGES:
		kprintf("TEXT: # of large pages = %d\n", (int)a);
		break;
	case X86_INIT_TEXT_LOG_BASE:
		kprintf("TEXT: Base address = %lx\n", a);
		break;
	default:
		break;
	}
}

X86_MEMORY_PUBLIC_BRIDGE unsigned long x86_init_text_map_kernel_start_bridge(void)
{
	return MAP_KERNEL_START;
}

X86_MEMORY_PUBLIC_BRIDGE unsigned long x86_init_text_end_bridge(void)
{
	return (unsigned long)_end;
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_text_panic_bridge(void)
{
	panic("init_text_area: helper failed");
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_low_panic_bridge(void)
{
	panic("init_low_area: helper failed");
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
static void init_normal_area(struct page_table *pt)
{
	int ret;

	ret = x86_init_normal_area_body_result(pt, MAP_ST_START,
			LARGE_PAGE_SIZE, PTATTR_WRITABLE,
			IHK_MC_GMA_MAP_START, IHK_MC_GMA_MAP_END,
			x86_init_normal_get_memory_address_bridge,
			x86_init_normal_set_large_bridge,
			x86_init_normal_log_bridge);
	if (ret)
		panic("init_normal_area: helper failed");
}
#endif

extern char *find_command_line(char *name);

X86_MEMORY_PUBLIC_BRIDGE char *x86_init_linux_find_command_line_bridge(char *name)
{
	return find_command_line(name);
}

X86_MEMORY_PUBLIC_BRIDGE int x86_init_linux_get_nr_memory_chunks_bridge(void)
{
	return ihk_mc_get_nr_memory_chunks();
}

X86_MEMORY_PUBLIC_BRIDGE int x86_init_linux_get_memory_chunk_bridge(int id,
		unsigned long *start, unsigned long *end, int *numa_id)
{
	return ihk_mc_get_memory_chunk(id, start, end, numa_id);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_linux_log_bridge(int event, unsigned long a,
		unsigned long b, unsigned long c, unsigned long d, int error)
{
	switch (event) {
	case X86_INIT_LINUX_LOG_FULL:
		kprintf("Straight-map entire physical memory\n");
		break;
	case X86_INIT_LINUX_LOG_FULL_RANGE:
		kprintf("Linux kernel virtual: 0x%lx - 0x%lx -> 0x%lx - 0x%lx\n",
				a, b, c, d);
		break;
	case X86_INIT_LINUX_LOG_FULL_SET_FAILED:
		kprintf("%s: error setting mapping for 0x%lx\n",
				"init_linux_kernel_mapping", a);
		break;
	case X86_INIT_LINUX_LOG_CHUNKS:
		kprintf("Straight-map physical memory areas allocated to McKernel\n");
		break;
	case X86_INIT_LINUX_LOG_NO_CHUNK:
		kprintf("%s: ERROR: No memory chunk available.\n",
				"init_linux_kernel_mapping");
		break;
	case X86_INIT_LINUX_LOG_BAD_CHUNK:
		kprintf("%s: ERROR: Memory chunk id (%d) out of range.\n",
				"init_linux_kernel_mapping", (int)a);
		break;
	case X86_INIT_LINUX_LOG_CHUNK_RANGE:
		dkprintf("Linux kernel virtual: 0x%lx - 0x%lx -> 0x%lx - 0x%lx\n",
				a, b, c, d);
		break;
	case X86_INIT_LINUX_LOG_CHUNK_SET_FAILED:
		kprintf("%s: set_pt_large_page() failed for 0x%lx\n",
				"init_linux_kernel_mapping", a);
		break;
	default:
		break;
	}
	(void)error;
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_linux_panic_bridge(void)
{
	panic("init_linux_kernel_mapping: helper failed");
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
static void init_linux_kernel_mapping(struct page_table *pt)
{
	int ret;

	/* Map 2 TB for now when safe_kernel_map is not specified. */
	ret = x86_init_linux_kernel_mapping_body_result(pt,
			linux_page_offset_base, LARGE_PAGE_SIZE,
			PTATTR_WRITABLE, 0x20000000000, "safe_kernel_map",
			x86_init_linux_find_command_line_bridge,
			x86_init_linux_get_nr_memory_chunks_bridge,
			x86_init_linux_get_memory_chunk_bridge,
			x86_init_normal_set_large_bridge,
			x86_init_linux_log_bridge);
	if (ret)
		panic("init_linux_kernel_mapping: helper failed");
}
#endif

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void init_text_area(struct page_table *pt)
{
	int ret;

	ret = x86_init_text_area_body_result(pt, MAP_KERNEL_START,
			(unsigned long)_end, LARGE_PAGE_SIZE,
			LARGE_PAGE_SHIFT, LARGE_PAGE_MASK,
			x86_kernel_phys_base, PTATTR_WRITABLE,
			x86_init_normal_set_large_bridge,
			x86_init_text_log_bridge);
	if (ret)
		panic("init_text_area: helper failed");
}
#endif

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void *map_fixed_area(unsigned long phys, unsigned long size, int uncachable)
{
	void *v = (void *)fixed_virt;
	void *ret;

	dkprintf("map_fixed: phys: 0x%lx => 0x%lx (%d pages)\n",
			phys & PAGE_MASK, v,
			(int)(((phys & (PAGE_SIZE - 1)) + size +
				PAGE_SIZE - 1) >> PAGE_SHIFT));

	ret = x86_map_fixed_area_body_result(init_pt, &fixed_virt, phys,
			size, uncachable, x86_pt_set_page_bridge,
			x86_move_flush_tlb_bridge);
	return ret;
}
#endif

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void init_low_area(struct page_table *pt)
{
	int ret;

	ret = x86_init_low_area_body_result(pt, PTATTR_NO_EXECUTE,
			PTATTR_WRITABLE, x86_init_normal_set_large_bridge);
	if (ret)
		panic("init_low_area: helper failed");
}
#endif

extern char vsyscall_page[];

X86_MEMORY_PUBLIC_BRIDGE void *x86_init_vsyscall_page_bridge(void)
{
	return vsyscall_page;
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_vsyscall_panic_bridge(void)
{
	panic("init_vsyscall_area:__set_pt_page failed");
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
static void init_vsyscall_area(struct page_table *pt)
{
	int error;

#define	VSYSCALL_ADDR	((void *)(0xffffffffff600000))
	error = x86_init_vsyscall_area_body_result(pt,
			(unsigned long)VSYSCALL_ADDR, vsyscall_page,
			PTATTR_ACTIVE | PTATTR_USER,
			x86_pt_virt_to_phys_bridge, x86_pt_set_page_bridge);
	if (error) {
		panic("init_vsyscall_area:__set_pt_page failed");
	}

	return;
}
#endif

X86_MEMORY_PUBLIC_BRIDGE void x86_check_available_page_size_bridge(int event)
{
	(void)event;
	check_available_page_size();
}

X86_MEMORY_PUBLIC_BRIDGE void *x86_init_page_table_alloc_bridge(int nr_pages, int flag)
{
	return _ihk_mc_alloc_aligned_pages_node(nr_pages, PAGE_P2ALIGN, flag, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_spin_init_bridge(void *lock)
{
	ihk_mc_spinlock_init((ihk_spinlock_t *)lock);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_normal_bridge(void *pt)
{
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
	x86_init_normal_area_public(pt);
#else
	init_normal_area((struct page_table *)pt);
#endif
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_linux_bridge(void *pt)
{
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
	x86_init_linux_kernel_mapping_public(pt);
#else
	init_linux_kernel_mapping((struct page_table *)pt);
#endif
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_fixed_bridge(void *pt)
{
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
	x86_init_fixed_area_public(pt);
#else
	init_fixed_area((struct page_table *)pt);
#endif
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_text_bridge(void *pt)
{
	init_text_area((struct page_table *)pt);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_vsyscall_bridge(void *pt)
{
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
	x86_init_vsyscall_area_public(pt);
#else
	init_vsyscall_area((struct page_table *)pt);
#endif
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_low_bridge(void *pt)
{
	init_low_area((struct page_table *)pt);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_load_bridge(void *pt)
{
	load_page_table((struct page_table *)pt);
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_log_bridge(int event, void *pt)
{
	switch (event) {
	case 1:
		kprintf("Page table is now at 0x%lx\n", pt);
		break;
	}
}

X86_MEMORY_PUBLIC_BRIDGE void x86_init_page_table_panic_bridge(int reason)
{
	switch (reason) {
	case 3:
		panic("init_page_table: init_pt allocation failed");
		break;
	case 4:
		panic("init_page_table: boot_pt allocation failed");
		break;
	case 5:
		panic("init low area for boot pt did not affect toplevel entry");
		break;
	default:
		panic("init_page_table: helper failed");
	}
}

X86_MEMORY_PUBLIC_BRIDGE void **x86_init_page_table_init_pt_slot_bridge(void)
{
	return (void **)&init_pt;
}

X86_MEMORY_PUBLIC_BRIDGE void **x86_init_page_table_boot_pt_slot_bridge(void)
{
	return (void **)&boot_pt;
}

X86_MEMORY_PUBLIC_BRIDGE int *x86_init_page_table_loaded_slot_bridge(void)
{
	return &init_pt_loaded;
}

X86_MEMORY_PUBLIC_BRIDGE void *x86_init_page_table_lock_bridge(void)
{
	return &init_pt_lock;
}

X86_MEMORY_PUBLIC_BRIDGE size_t x86_init_page_table_size_bridge(void)
{
	return sizeof(*init_pt);
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void init_page_table(void)
{
	int ret;

	ret = x86_init_page_table_body_result((void **)&init_pt,
			(void **)&boot_pt, &init_pt_loaded, &init_pt_lock,
			sizeof(*init_pt), IHK_MC_AP_CRITICAL,
			x86_check_available_page_size_bridge,
			x86_init_page_table_alloc_bridge,
			x86_init_page_table_spin_init_bridge,
			x86_init_page_table_normal_bridge,
			x86_init_page_table_linux_bridge,
			x86_init_page_table_fixed_bridge,
			x86_init_page_table_text_bridge,
			x86_init_page_table_vsyscall_bridge,
			x86_init_page_table_low_bridge,
			x86_init_page_table_load_bridge,
			x86_init_page_table_log_bridge,
			x86_init_page_table_panic_bridge);
	if (ret)
		panic("init_page_table: helper failed");
}
#endif

extern void __reserve_arch_pages(unsigned long, unsigned long,
		void (*)(struct ihk_page_allocator_desc *, 
			unsigned long, unsigned long, int));

void x86_reserve_arch_pages_bridge(unsigned long start,
		unsigned long end, x86_reserve_pages_cb_fn_t cb_fn)
{
	__reserve_arch_pages(start, end,
			(void (*)(struct ihk_page_allocator_desc *,
				unsigned long, unsigned long, int))cb_fn);
}

void x86_reserve_arch_pages_panic_bridge(void)
{
	panic("ihk_mc_reserve_arch_pages: helper failed");
}

#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC
void ihk_mc_reserve_arch_pages(struct ihk_page_allocator_desc *pa_allocator,
		unsigned long start, unsigned long end,
		void (*cb)(struct ihk_page_allocator_desc *, 
			unsigned long, unsigned long, int))
{
	int ret;

	ret = x86_reserve_arch_pages_body_result(pa_allocator, start, end,
			_head, get_last_early_heap(), ap_trampoline,
			AP_TRAMPOLINE_SIZE, PAGE_SIZE,
			x86_pt_virt_to_phys_bridge,
			(x86_reserve_pages_cb_fn_t)cb,
			x86_reserve_arch_pages_bridge);
	if (ret)
		panic("ihk_mc_reserve_arch_pages: helper failed");
}
#endif

#ifdef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
#define X86_ADDR_PUBLIC_BRIDGE
#else
#define X86_ADDR_PUBLIC_BRIDGE static
#endif

X86_ADDR_PUBLIC_BRIDGE int x86_addr_init_pt_loaded_bridge(void)
{
	return init_pt_loaded;
}

X86_ADDR_PUBLIC_BRIDGE void x86_addr_log_bridge(int event, unsigned long value)
{
	switch (event) {
	case X86_ADDR_LOG_KERNEL:
		dkprintf("%s: MAP_KERNEL_START <= 0x%lx <= linux_page_offset_base\n",
				"virt_to_phys", value);
		break;
	case X86_ADDR_LOG_STRAIGHT:
		dkprintf("%s: MAP_ST_START <= 0x%lx <= MAP_FIXED_START\n",
				"virt_to_phys", value);
		break;
	default:
		break;
	}
}

#ifdef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
extern unsigned long virt_to_phys(void *v);
extern void *phys_to_virt(unsigned long p);
#else
unsigned long virt_to_phys(void *v)
{
	return x86_virt_to_phys_body_result((unsigned long)v,
			MAP_KERNEL_START, x86_kernel_phys_base,
			linux_page_offset_base, MAP_FIXED_START, MAP_ST_START,
			x86_addr_log_bridge);
}

void *phys_to_virt(unsigned long p)
{
	return x86_phys_to_virt_body_result(p, init_pt_loaded,
			MAP_ST_START, linux_page_offset_base);
}
#endif

#ifdef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
#define X86_USER_COPY_BRIDGE
#else
#define X86_USER_COPY_BRIDGE static
#endif

static int x86_read_process_vm_bridge(void *vm, void *kdst, const void *usrc,
		size_t siz);
static int x86_write_process_vm_bridge(void *vm, void *udst, const void *ksrc,
		size_t siz);
X86_USER_COPY_BRIDGE int x86_user_page_fault_bridge(void *vm, void *addr,
		unsigned long reason);
X86_USER_COPY_BRIDGE int x86_user_verify_bridge(void *vm, void *addr,
		unsigned long size);
X86_USER_COPY_BRIDGE int x86_user_vtop_bridge(void *pt, const void *virt,
		unsigned long *physp);
X86_USER_COPY_BRIDGE int x86_user_is_memory_bridge(unsigned long start,
		unsigned long end);
X86_USER_COPY_BRIDGE void *x86_user_map_bridge(unsigned long phys,
		int nr_pages, unsigned long attr);
X86_USER_COPY_BRIDGE void x86_user_unmap_bridge(void *addr, int nr_pages);
X86_USER_COPY_BRIDGE void *x86_user_phys_to_virt_bridge(unsigned long phys);
X86_USER_COPY_BRIDGE void x86_user_copy_log_bridge(int event, void *vm,
		unsigned long a, unsigned long b, int error);
X86_USER_COPY_BRIDGE unsigned long x86_user_map_kernel_start_bridge(void);

#ifndef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
int copy_from_user(void *dst, const void *src, size_t siz)
{
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

	return x86_copy_from_user_result(vm, dst, src, siz,
			x86_read_process_vm_bridge);
}
#endif

int verify_process_vm(struct process_vm *vm, const void *usrc, size_t size);
int read_process_vm(struct process_vm *vm, void *kdst, const void *usrc,
		size_t siz);
int write_process_vm(struct process_vm *vm, void *udst, const void *ksrc,
		size_t siz);

static int x86_read_process_vm_bridge(void *vm, void *kdst, const void *usrc,
		size_t siz)
{
	return read_process_vm(vm, kdst, usrc, siz);
}

static int x86_write_process_vm_bridge(void *vm, void *udst, const void *ksrc,
		size_t siz)
{
	return write_process_vm(vm, udst, ksrc, siz);
}

X86_USER_COPY_BRIDGE int x86_user_page_fault_bridge(void *vm, void *addr,
		unsigned long reason)
{
	return page_fault_process_vm(vm, addr, reason);
}

X86_USER_COPY_BRIDGE int x86_user_verify_bridge(void *vm, void *addr,
		unsigned long size)
{
	return verify_process_vm(vm, addr, size);
}

X86_USER_COPY_BRIDGE int x86_user_vtop_bridge(void *pt, const void *virt,
		unsigned long *physp)
{
	return ihk_mc_pt_virt_to_phys(pt, virt, physp);
}

X86_USER_COPY_BRIDGE int x86_user_is_memory_bridge(unsigned long start,
		unsigned long end)
{
	return is_mckernel_memory(start, end);
}

X86_USER_COPY_BRIDGE void *x86_user_map_bridge(unsigned long phys,
		int nr_pages, unsigned long attr)
{
	return ihk_mc_map_virtual(phys, nr_pages, attr);
}

X86_USER_COPY_BRIDGE void x86_user_unmap_bridge(void *addr, int nr_pages)
{
	ihk_mc_unmap_virtual(addr, nr_pages);
}

X86_USER_COPY_BRIDGE void *x86_user_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}

X86_USER_COPY_BRIDGE void x86_user_copy_log_bridge(int event, void *vm,
		unsigned long a, unsigned long b, int error)
{
	switch (event) {
	case X86_USER_COPY_LOG_RANGE:
		kprintf("x86_user_copy(%p): error: out of user range addr=%lx size=%lx\n",
				vm, a, b);
		break;
	case X86_USER_COPY_LOG_PF:
		kprintf("x86_user_copy(%p): error: PF for %p failed: %d\n",
				vm, (void *)a, error);
		break;
	case X86_USER_COPY_LOG_VTOP:
		kprintf("x86_user_copy(%p): error: resolving physical address of %p: %d\n",
				vm, (void *)a, error);
		break;
	case X86_USER_COPY_LOG_EXTERNAL:
		dkprintf("x86_user_copy(%p): pa is outside of LWK memory, pa: %p, cpsize: %lu\n",
				vm, (void *)a, b);
		break;
	case X86_USER_COPY_LOG_PATCH_START:
		dkprintf("patch_process_vm(%p,%p,%p,%lx)\n",
				vm, (void *)a, (void *)b, (unsigned long)error);
		break;
	case X86_USER_COPY_LOG_PATCH_RANGE:
		kprintf("patch_process_vm(%p,%p,%p,%lx):not in user\n",
				vm, (void *)a, NULL, b);
		break;
	case X86_USER_COPY_LOG_PATCH_PF:
		kprintf("patch_process_vm(%p):pf(%lx):%d\n",
				vm, a, error);
		break;
	case X86_USER_COPY_LOG_PATCH_VTOP:
		kprintf("patch_process_vm(%p):v2p(%p):%d\n",
				vm, (void *)a, error);
		break;
	case X86_USER_COPY_LOG_PATCH_DONE:
		dkprintf("patch_process_vm(%p,%p,%p,%lx):%d\n",
				vm, (void *)a, (void *)b, 0UL, 0);
		break;
	default:
		break;
	}
}

X86_USER_COPY_BRIDGE unsigned long x86_user_map_kernel_start_bridge(void)
{
	return MAP_KERNEL_START;
}

#ifndef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
int strlen_user(const char *s)
{
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

	return x86_strlen_user_result(vm, s, MAP_KERNEL_START,
			x86_user_verify_bridge);
}

int strcpy_from_user(char *dst, const char *src)
{
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

	return x86_strcpy_from_user_result(vm, dst, src, MAP_KERNEL_START,
			x86_user_verify_bridge);
}

long getlong_user(long *dest, const long *p)
{
	return x86_getlong_user_result(dest, p, copy_from_user);
}

int getint_user(int *dest, const int *p)
{
	return x86_getint_user_result(dest, p, copy_from_user);
}
#endif

#ifndef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
int verify_process_vm(struct process_vm *vm,
		const void *usrc, size_t size)
{
	return x86_verify_process_vm_result(vm, (unsigned long)usrc, size,
			vm->region.user_start, vm->region.user_end, PF_USER,
			x86_user_page_fault_bridge, x86_user_copy_log_bridge);
}
#endif

#ifndef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
int read_process_vm(struct process_vm *vm, void *kdst, const void *usrc, size_t siz)
{
	return x86_process_vm_copy_result(vm, vm->address_space->page_table,
			(unsigned long)usrc, (unsigned long)kdst, siz,
			vm->region.user_start, vm->region.user_end, PF_USER,
			X86_USER_COPY_READ, x86_user_page_fault_bridge,
			x86_user_vtop_bridge, x86_user_is_memory_bridge,
			x86_user_map_bridge, x86_user_unmap_bridge,
			x86_user_phys_to_virt_bridge, x86_user_copy_log_bridge);
} /* read_process_vm() */
#endif

#ifndef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
int copy_to_user(void *dst, const void *src, size_t siz)
{
	struct process_vm *vm = get_this_cpu_local_var()->current->vm;

	return x86_copy_to_user_result(vm, dst, src, siz,
			x86_write_process_vm_bridge);
}

int setlong_user(long *dst, long data)
{
	return x86_setlong_user_result(dst, data, copy_to_user);
}

int setint_user(int *dst, int data)
{
	return x86_setint_user_result(dst, data, copy_to_user);
}
#endif

#ifndef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
int write_process_vm(struct process_vm *vm, void *udst, const void *ksrc, size_t siz)
{
	return x86_process_vm_copy_result(vm, vm->address_space->page_table,
			(unsigned long)udst, (unsigned long)ksrc, siz,
			vm->region.user_start, vm->region.user_end,
			PF_POPULATE | PF_WRITE | PF_USER, X86_USER_COPY_WRITE,
			x86_user_page_fault_bridge, x86_user_vtop_bridge,
			x86_user_is_memory_bridge, x86_user_map_bridge,
			x86_user_unmap_bridge, x86_user_phys_to_virt_bridge,
			x86_user_copy_log_bridge);
} /* write_process_vm() */
#endif

#ifndef MCKERNEL_RUST_X86_USER_COPY_PUBLIC
int patch_process_vm(struct process_vm *vm, void *udst, const void *ksrc, size_t siz)
{
	return x86_process_vm_copy_result(vm, vm->address_space->page_table,
			(unsigned long)udst, (unsigned long)ksrc, siz,
			vm->region.user_start, vm->region.user_end,
			PF_PATCH | PF_WRITE | PF_USER, X86_USER_COPY_WRITE,
			x86_user_page_fault_bridge, x86_user_vtop_bridge,
			x86_user_is_memory_bridge, x86_user_map_bridge,
			x86_user_unmap_bridge, x86_user_phys_to_virt_bridge,
			x86_user_copy_log_bridge);
} /* patch_process_vm() */
#endif

int split_contiguous_pages(pte_t *ptep, size_t pgsize,
		uint32_t memobj_flags)
{
	return 0;
}
