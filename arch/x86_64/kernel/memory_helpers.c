/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <arch-memory.h>
#include <arch-memory-helpers.h>
#include <ihk/atomic.h>
#include <process.h>
#include <registers.h>
#include <string.h>
#include <syscall.h>

#ifndef MCKERNEL_RUST_X86_MEMORY_HELPERS

void flush_nfo_tlb(void)
{
}

void flush_nfo_tlb_mm(struct process_vm *vm)
{
	(void)vm;
}

int x86_vdso_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
				   unsigned long arg)
{
	if (!packet)
		return -EINVAL;

	packet->msg = msg;
	packet->arg = arg;

	return 0;
}

void *x86_early_alloc_pages_body_result(
	void **last_page_slot, unsigned long end_addr,
	unsigned long bootstrap_end, int nr_pages,
	unsigned long (*virt_to_phys_fn)(void *),
	void *(*phys_to_virt_fn)(unsigned long),
	void (*panic_fn)(int))
{
	void *last_page;
	void *ret;

	if (!last_page_slot || !virt_to_phys_fn || !phys_to_virt_fn ||
	    !panic_fn)
		return NULL;

	last_page = *last_page_slot;
	if (!last_page) {
		last_page = (void *)x86_early_alloc_align_end_result(end_addr);
		last_page = phys_to_virt_fn(virt_to_phys_fn(last_page));
	} else if (last_page == (void *)-1) {
		panic_fn(1);
		return NULL;
	} else if (x86_early_alloc_exhausted_result(
			   virt_to_phys_fn(last_page), bootstrap_end)) {
		panic_fn(2);
		return NULL;
	}

	ret = last_page;
	*last_page_slot = (void *)x86_early_alloc_next_result(
		(unsigned long)last_page, nr_pages);
	return ret;
}

int x86_early_alloc_invalidate_body_result(void **last_page_slot)
{
	if (!last_page_slot)
		return -EINVAL;
	*last_page_slot = (void *)-1;
	return 0;
}

void *x86_get_last_early_heap_body_result(void **last_page_slot)
{
	return last_page_slot ? *last_page_slot : NULL;
}

int x86_check_available_page_size_body_result(
	int *use_1gb_page_slot,
	void (*cpuid_edx_fn)(unsigned long, unsigned long *),
	void (*log_fn)(int, int))
{
	unsigned long edx;

	if (!use_1gb_page_slot || !cpuid_edx_fn)
		return -EINVAL;
	cpuid_edx_fn(0x80000001UL, &edx);
	*use_1gb_page_slot = (edx & (1UL << 26)) ? 1 : 0;
	if (log_fn)
		log_fn(1, *use_1gb_page_slot);
	return 0;
}

int x86_enable_ptattr_no_execute_body_result(unsigned long *attr_mask_slot,
					     unsigned long no_execute_attr)
{
	if (!attr_mask_slot)
		return -EINVAL;
	*attr_mask_slot |= no_execute_attr;
	return 0;
}

void *x86_ihk_mc_allocate_body_result(
	int kmalloc_initialized, int size, int nowait_flag,
	void *(*kmalloc_fn)(int, int), void (*log_fn)(int))
{
	if (!kmalloc_initialized) {
		if (log_fn)
			log_fn(1);
		return NULL;
	}
	return kmalloc_fn ? kmalloc_fn(size, nowait_flag) : NULL;
}

int x86_ihk_mc_free_body_result(int kmalloc_initialized, void *ptr,
				void (*kfree_fn)(void *), void (*log_fn)(int))
{
	if (!kmalloc_initialized) {
		if (log_fn)
			log_fn(2);
		return 0;
	}
	if (!kfree_fn)
		return -EINVAL;
	kfree_fn(ptr);
	return 0;
}

unsigned long x86_setup_l2_body_result(
	void *pt0, unsigned long page_head, unsigned long start,
	unsigned long end, x86_pt_virt_to_phys_fn_t virt_to_phys_fn)
{
	unsigned long *pt = pt0;
	int i;

	if (!pt || !virt_to_phys_fn)
		return 0;

	for (i = 0; i < PT_ENTRIES; i++) {
		unsigned long phys = page_head + ((unsigned long)i << PTL2_SHIFT);

		if (phys + PTL2_SIZE <= start || phys >= end) {
			pt[i] = 0;
			continue;
		}

		pt[i] = phys | PFL2_KERN_ATTR | PFL2_SIZE;
	}

	return virt_to_phys_fn(pt);
}

unsigned long x86_setup_l3_body_result(
	void *pt0, unsigned long page_head, unsigned long start,
	unsigned long end, int critical_flag,
	x86_pt_alloc_pages_fn_t alloc_pages_fn,
	x86_pt_virt_to_phys_fn_t virt_to_phys_fn)
{
	unsigned long *pt = pt0;
	int i;

	if (!pt || !alloc_pages_fn || !virt_to_phys_fn)
		return 0;

	for (i = 0; i < PT_ENTRIES; i++) {
		unsigned long phys = page_head + ((unsigned long)i << PTL3_SHIFT);
		unsigned long pt_phys;
		void *child_pt;

		if (phys + PTL3_SIZE <= start || phys >= end) {
			pt[i] = 0;
			continue;
		}

		child_pt = alloc_pages_fn(1, critical_flag);
		if (!child_pt)
			return 0;
		pt_phys = x86_setup_l2_body_result(child_pt, phys, start, end,
						   virt_to_phys_fn);
		pt[i] = pt_phys | PFL3_PDIR_ATTR;
	}

	return virt_to_phys_fn(pt);
}

int x86_init_page_table_body_result(
	void **init_pt_slot, void **boot_pt_slot, int *init_pt_loaded_slot,
	void *init_pt_lock, size_t page_table_size, int critical_flag,
	void (*check_available_page_size_fn)(int),
	void *(*alloc_pages_fn)(int, int),
	void (*spin_init_fn)(void *),
	void (*init_normal_area_fn)(void *),
	void (*init_linux_kernel_mapping_fn)(void *),
	void (*init_fixed_area_fn)(void *),
	void (*init_text_area_fn)(void *),
	void (*init_vsyscall_area_fn)(void *),
	void (*init_low_area_fn)(void *),
	void (*load_page_table_fn)(void *),
	void (*log_fn)(int, void *),
	void (*panic_fn)(int))
{
	void *init_pt;
	void *boot_pt;

	if (!init_pt_slot || !boot_pt_slot || !init_pt_loaded_slot ||
	    !init_pt_lock || !page_table_size ||
	    !check_available_page_size_fn || !alloc_pages_fn ||
	    !spin_init_fn || !init_normal_area_fn ||
	    !init_linux_kernel_mapping_fn || !init_fixed_area_fn ||
	    !init_text_area_fn || !init_vsyscall_area_fn ||
	    !init_low_area_fn || !load_page_table_fn || !panic_fn)
		return -EINVAL;

	check_available_page_size_fn(3);
	init_pt = alloc_pages_fn(1, critical_flag);
	if (!init_pt) {
		panic_fn(3);
		return -ENOMEM;
	}
	*init_pt_slot = init_pt;
	spin_init_fn(init_pt_lock);
	memset(init_pt, 0, page_table_size);

	init_normal_area_fn(init_pt);
	init_linux_kernel_mapping_fn(init_pt);
	init_fixed_area_fn(init_pt);
	init_text_area_fn(init_pt);
	init_vsyscall_area_fn(init_pt);

	boot_pt = alloc_pages_fn(1, critical_flag);
	if (!boot_pt) {
		panic_fn(4);
		return -ENOMEM;
	}
	*boot_pt_slot = boot_pt;
	memcpy(boot_pt, init_pt, page_table_size);
	init_low_area_fn(boot_pt);
	if (memcmp(init_pt, boot_pt, page_table_size) == 0) {
		panic_fn(5);
		return -EINVAL;
	}

	load_page_table_fn(init_pt);
	*init_pt_loaded_slot = 1;
	if (log_fn)
		log_fn(1, init_pt);
	return 0;
}

int x86_pt_print_pte_body_result(
	void *pt0, void *init_pt, unsigned long virt,
	x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
	x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
	x86_pt_print_log_fn_t log_fn)
{
	unsigned long *pt = pt0 ? pt0 : init_pt;
	unsigned long entry;
	int l4idx, l3idx, l2idx, l1idx;

	if (!virt_to_phys_fn || !phys_to_virt_fn || !log_fn)
		return -EINVAL;
	if (!pt)
		return -EFAULT;

	x86_pt_indices_result(virt, &l4idx, &l3idx, &l2idx, &l1idx);

	log_fn(X86_PT_PRINT_LOG_TABLE, 4, virt_to_phys_fn(pt), l4idx);
	entry = pt[l4idx];
	if (!(entry & PFL4_PRESENT)) {
		log_fn(X86_PT_PRINT_LOG_NOT_PRESENT, 4, virt, l4idx);
		return -EFAULT;
	}
	log_fn(X86_PT_PRINT_LOG_ENTRY, 4, entry, l4idx);

	pt = phys_to_virt_fn(entry & PAGE_MASK);
	if (!pt)
		return -EFAULT;
	log_fn(X86_PT_PRINT_LOG_TABLE, 3, virt_to_phys_fn(pt), l3idx);
	entry = pt[l3idx];
	if (!(entry & PFL3_PRESENT)) {
		log_fn(X86_PT_PRINT_LOG_NOT_PRESENT, 3, virt, l3idx);
		return -EFAULT;
	}
	log_fn(X86_PT_PRINT_LOG_ENTRY, 3, entry, l3idx);
	if (entry & PFL3_SIZE) {
		log_fn(X86_PT_PRINT_LOG_LARGE, 3, entry, l3idx);
		return 0;
	}

	pt = phys_to_virt_fn(entry & PAGE_MASK);
	if (!pt)
		return -EFAULT;
	log_fn(X86_PT_PRINT_LOG_TABLE, 2, virt_to_phys_fn(pt), l2idx);
	entry = pt[l2idx];
	if (!(entry & PFL2_PRESENT)) {
		log_fn(X86_PT_PRINT_LOG_NOT_PRESENT, 2, virt, l2idx);
		return -EFAULT;
	}
	log_fn(X86_PT_PRINT_LOG_ENTRY, 2, entry, l2idx);
	if (entry & PFL2_SIZE) {
		log_fn(X86_PT_PRINT_LOG_LARGE, 2, entry, l2idx);
		return 0;
	}

	pt = phys_to_virt_fn(entry & PAGE_MASK);
	if (!pt)
		return -EFAULT;
	log_fn(X86_PT_PRINT_LOG_TABLE, 1, virt_to_phys_fn(pt), l1idx);
	entry = pt[l1idx];
	if (!(entry & PFL1_PRESENT)) {
		log_fn(X86_PT_PRINT_LOG_NOT_PRESENT, 1, virt, l1idx);
		log_fn(X86_PT_PRINT_LOG_ENTRY, 1, entry, l1idx);
		return -EFAULT;
	}
	log_fn(X86_PT_PRINT_LOG_ENTRY, 1, entry, l1idx);
	return 0;
}

unsigned long x86_attr_to_l3attr_result(unsigned long attr,
					unsigned long attr_mask)
{
	unsigned long r = attr & (attr_mask | PTATTR_LARGEPAGE);

	if ((attr & PTATTR_UNCACHABLE) && (attr & PTATTR_LARGEPAGE))
		return r | PFL3_PCD | PFL3_PWT;

	return r;
}

unsigned long x86_attr_to_l2attr_result(unsigned long attr,
					unsigned long attr_mask)
{
	unsigned long r = attr & (attr_mask | PTATTR_LARGEPAGE);

	if ((attr & PTATTR_UNCACHABLE) && (attr & PTATTR_LARGEPAGE))
		return r | PFL2_PCD | PFL2_PWT;

	return r;
}

unsigned long x86_attr_to_l1attr_result(unsigned long attr,
					unsigned long attr_mask)
{
	if (attr & PTATTR_UNCACHABLE)
		return (attr & attr_mask) | PFL1_PCD | PFL1_PWT;
	else if (attr & PTATTR_WRITE_COMBINED)
		return (attr & attr_mask) | PFL1_PWT;
	else
		return attr & attr_mask;
}

unsigned long x86_set_pte_value_result(unsigned long phys,
					unsigned long attr,
					unsigned long attr_mask)
{
	if (attr & PTATTR_LARGEPAGE)
		return phys | x86_attr_to_l2attr_result(attr, attr_mask) |
			PFL2_SIZE;

	return phys | x86_attr_to_l1attr_result(attr, attr_mask);
}

int x86_pt_set_pte_value_result(size_t pgsize, unsigned long phys,
				unsigned long attr, unsigned long attr_mask,
				int use_1gb_page, unsigned long *entryp)
{
	unsigned long entry;

	if (pgsize == PTL1_SIZE) {
		entry = phys | x86_attr_to_l1attr_result(attr, attr_mask);
	}
	else if (pgsize == PTL2_SIZE) {
		if (phys & (PTL2_SIZE - 1))
			return -1;
		entry = phys | x86_attr_to_l2attr_result(
			attr | PTATTR_LARGEPAGE, attr_mask);
	}
	else if ((pgsize == PTL3_SIZE) && use_1gb_page) {
		if (phys & (PTL3_SIZE - 1))
			return -1;
		entry = phys | x86_attr_to_l3attr_result(
			attr | PTATTR_LARGEPAGE, attr_mask);
	}
	else {
		return -EINVAL;
	}

	if (entryp)
		*entryp = entry;
	return 0;
}

int x86_smaller_page_size_result(size_t cursize, int use_1gb,
				 size_t *newsizep, int *p2alignp)
{
	size_t newsize;
	int p2align;

	if ((cursize > PTL3_SIZE) && use_1gb) {
		newsize = PTL3_SIZE;
		p2align = PTL3_SHIFT - PTL1_SHIFT;
	}
	else if (cursize > PTL2_SIZE) {
		newsize = PTL2_SIZE;
		p2align = PTL2_SHIFT - PTL1_SHIFT;
	}
	else if (cursize > PTL1_SIZE) {
		newsize = PTL1_SIZE;
		p2align = 0;
	}
	else {
		if (newsizep)
			*newsizep = 0;
		if (p2alignp)
			*p2alignp = -1;
		return -ENOMEM;
	}

	if (newsizep)
		*newsizep = newsize;
	if (p2alignp)
		*p2alignp = p2align;

	return 0;
}

unsigned long x86_early_alloc_align_end_result(unsigned long end_addr)
{
	return (end_addr + PAGE_SIZE - 1) & PAGE_MASK;
}

int x86_early_alloc_exhausted_result(unsigned long current_phys,
				     unsigned long bootstrap_end)
{
	return current_phys >= bootstrap_end;
}

unsigned long x86_early_alloc_next_result(unsigned long current,
					  int nr_pages)
{
	return current + ((unsigned long)nr_pages * PAGE_SIZE);
}

void x86_pt_indices_result(unsigned long virt, int *l4idxp, int *l3idxp,
			   int *l2idxp, int *l1idxp)
{
	if (l4idxp)
		*l4idxp = (virt >> PTL4_SHIFT) & (PT_ENTRIES - 1);
	if (l3idxp)
		*l3idxp = (virt >> PTL3_SHIFT) & (PT_ENTRIES - 1);
	if (l2idxp)
		*l2idxp = (virt >> PTL2_SHIFT) & (PT_ENTRIES - 1);
	if (l1idxp)
		*l1idxp = (virt >> PTL1_SHIFT) & (PT_ENTRIES - 1);
}

void x86_walk_bounds_result(unsigned long start, unsigned long end,
			    unsigned long base, unsigned long span,
			    int shift, int *sixp, int *eixp)
{
	unsigned long size = 1UL << shift;
	int six = start <= base ? 0 : (int)((start - base) >> shift);
	int eix;

	if (end == 0 || (span && base + span <= end))
		eix = PT_ENTRIES;
	else
		eix = (int)(((end - base) + (size - 1)) >> shift);

	if (sixp)
		*sixp = six;
	if (eixp)
		*eixp = eix;
}

int x86_walk_step_result(int current_ret, int error, int *next_retp)
{
	int next_ret = current_ret;
	int stop = 0;

	if (!error) {
		next_ret = 0;
	}
	else if (error != -ENOENT) {
		next_ret = error;
		stop = 1;
	}

	if (next_retp)
		*next_retp = next_ret;
	return stop;
}

int x86_walk_pte_range_result(unsigned long pt_addr, uint64_t base,
			      uint64_t start, uint64_t end,
			      uint64_t span, int shift,
			      x86_walk_pte_callback_t funcp, void *args,
			      x86_walk_phys_check_fn_t phys_check_fn,
			      unsigned long phys_mask)
{
	unsigned long *pt = (unsigned long *)pt_addr;
	int six;
	int eix;
	int ret = -ENOENT;
	int i;
	int error;

	if (!pt || !funcp)
		return -ENOENT;

	x86_walk_bounds_result(start, end, base, span, shift, &six, &eix);

	for (i = six; i < eix; ++i) {
		uint64_t off = (uint64_t)i << shift;
		unsigned long *ptep = &pt[i];

		if (phys_check_fn &&
		    phys_check_fn(*ptep & phys_mask) == -1) {
			continue;
		}

		error = funcp(args, ptep, base + off, start, end);
		if (x86_walk_step_result(ret, error, &ret))
			break;
	}

	return ret;
}

int x86_virt_to_phys_level_result(unsigned long entry, unsigned long virt,
				  int level_shift, unsigned long size_flag,
				  unsigned long *physp,
				  unsigned long *sizep)
{
	unsigned long level_size = 1UL << level_shift;

	if (!(entry & PFL2_PRESENT))
		return X86_VTOP_MISS;

	if ((size_flag && (entry & size_flag)) || level_shift == PTL1_SHIFT) {
		if (physp)
			*physp = (entry & PT_PHYSMASK) |
				(virt & (level_size - 1));
		if (sizep)
			*sizep = level_size;
		return X86_VTOP_HIT;
	}

	return X86_VTOP_WALK;
}

int x86_pt_virt_to_phys_size_result(void *pt0, void *init_pt0,
				    unsigned long virt, unsigned long *phys,
				    unsigned long *size,
				    x86_pt_phys_to_virt_fn_t phys_to_virt_fn)
{
	unsigned long *pt = pt0 ? pt0 : init_pt0;
	int l4idx, l3idx, l2idx, l1idx;
	int action;

	if (!pt || !phys_to_virt_fn)
		return -EFAULT;

	x86_pt_indices_result(virt, &l4idx, &l3idx, &l2idx, &l1idx);

	action = x86_virt_to_phys_level_result(pt[l4idx], virt,
			PTL4_SHIFT, 0, NULL, NULL);
	if (action == X86_VTOP_MISS)
		return -EFAULT;

	pt = phys_to_virt_fn(pt[l4idx] & PT_PHYSMASK);
	if (!pt)
		return -EFAULT;

	action = x86_virt_to_phys_level_result(pt[l3idx], virt,
			PTL3_SHIFT, PFL3_SIZE, phys, size);
	if (action == X86_VTOP_MISS)
		return -EFAULT;
	if (action == X86_VTOP_HIT)
		return 0;

	pt = phys_to_virt_fn(pt[l3idx] & PT_PHYSMASK);
	if (!pt)
		return -EFAULT;

	action = x86_virt_to_phys_level_result(pt[l2idx], virt,
			PTL2_SHIFT, PFL2_SIZE, phys, size);
	if (action == X86_VTOP_MISS)
		return -EFAULT;
	if (action == X86_VTOP_HIT)
		return 0;

	pt = phys_to_virt_fn(pt[l2idx] & PT_PHYSMASK);
	if (!pt)
		return -EFAULT;

	action = x86_virt_to_phys_level_result(pt[l1idx], virt,
			PTL1_SHIFT, 0, phys, size);
	if (action == X86_VTOP_MISS)
		return -EFAULT;

	return 0;
}

uint64_t x86_pt_virt_to_pagemap_result(void *pt, void *init_pt,
				       unsigned long virt,
				       x86_pt_phys_to_virt_fn_t phys_to_virt_fn)
{
	unsigned long phys;
	uint64_t pagemap;

	if (x86_pt_virt_to_phys_size_result(pt, init_pt, virt, &phys, NULL,
			phys_to_virt_fn))
		return PM_PSHIFT(PAGE_SHIFT);

	pagemap = PM_PFRAME(phys >> PAGE_SHIFT);
	pagemap |= PM_PSHIFT(PAGE_SHIFT) | PM_PRESENT;
	return pagemap;
}

int x86_split_large_page_prepare_result(unsigned long entry, size_t pgsize,
					unsigned long *child_entryp,
					size_t *rss_pgsizep,
					unsigned long *step_p)
{
	if (pgsize != PTL3_SIZE && pgsize != PTL2_SIZE)
		return -EINVAL;

	if (child_entryp) {
		if (pgsize == PTL2_SIZE)
			*child_entryp = entry & ~PFL2_SIZE;
		else
			*child_entryp = entry;
	}
	if (rss_pgsizep)
		*rss_pgsizep = pgsize / PT_ENTRIES;
	if (step_p)
		*step_p = pgsize / PT_ENTRIES;

	return 0;
}

unsigned long x86_split_large_page_next_entry_result(unsigned long entry,
						    size_t pgsize)
{
	return entry + pgsize / PT_ENTRIES;
}

int x86_split_large_page_source_result(unsigned long entry, size_t pgsize,
				       unsigned long *phys_basep,
				       unsigned long *child_entryp,
				       size_t *rss_pgsizep)
{
	pte_t pte = entry;
	unsigned long step;

	if (x86_split_large_page_prepare_result(entry, pgsize, child_entryp,
			rss_pgsizep, &step))
		return -EINVAL;

	if (phys_basep)
		*phys_basep = pte_is_fileoff(&pte, pgsize) ?
			(unsigned long)-1 : pte_get_phys(&pte);

	return 0;
}

int x86_split_large_page_child_map_result(unsigned long phys_base,
					  size_t pgsize, int index,
					  unsigned long *physp)
{
	if (phys_base == (unsigned long)-1 || pgsize == PTL2_SIZE)
		return 0;

	if (physp)
		*physp = phys_base +
			((unsigned long)index * pgsize / PT_ENTRIES);

	return 1;
}

unsigned long x86_split_large_page_publish_result(unsigned long child_pt_phys)
{
	return (child_pt_phys & PT_PHYSMASK) | PFL2_PDIR_ATTR;
}

int x86_split_large_page_source_unmap_result(unsigned long phys_base,
					     size_t pgsize,
					     unsigned long *physp)
{
	if (phys_base == (unsigned long)-1 || pgsize == PTL2_SIZE)
		return 0;

	if (physp)
		*physp = phys_base;

	return 1;
}

int x86_split_large_page_body_result(unsigned long *ptep, size_t pgsize,
				     int alloc_ap_flag,
				     x86_pt_alloc_pages_fn_t alloc_fn,
				     x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				     x86_split_phys_to_page_fn_t phys_to_page_fn,
				     x86_split_page_map_fn_t page_map_fn,
				     x86_split_rss_fn_t rss_add_fn,
				     x86_split_rss_fn_t rss_sub_fn,
				     x86_split_page_unmap_fn_t page_unmap_fn,
				     x86_split_log_fn_t log_fn,
				     x86_split_panic_fn_t panic_fn)
{
	unsigned long source_entry;
	unsigned long phys_base;
	unsigned long child_entry;
	size_t rss_pgsize;
	unsigned long phys;
	unsigned long *pt;
	int source_fileoff;
	int i;

	if (!ptep)
		return -EINVAL;

	source_entry = *ptep;
	source_fileoff = source_entry & PTATTR_FILEOFF;
	if (x86_split_large_page_source_result(source_entry, pgsize,
			&phys_base, &child_entry, &rss_pgsize)) {
		if (log_fn)
			log_fn(X86_SPLIT_LARGE_PAGE_LOG_INVALID_PGSIZE, 0,
					pgsize, pgsize, NULL);
		return -EINVAL;
	}

	if (!alloc_fn || !virt_to_phys_fn || !rss_add_fn || !rss_sub_fn)
		return -EINVAL;

	pt = alloc_fn(1, alloc_ap_flag);
	if (!pt) {
		if (log_fn)
			log_fn(X86_SPLIT_LARGE_PAGE_LOG_ALLOC_FAILED, 0,
					pgsize, pgsize, NULL);
		return -ENOMEM;
	}

	for (i = 0; i < PT_ENTRIES; ++i) {
		if (x86_split_large_page_child_map_result(phys_base, pgsize,
				i, &phys)) {
			void *page;

			if (!phys_to_page_fn)
				return -EINVAL;
			page = phys_to_page_fn(phys);
			if (page) {
				if (!page_map_fn)
					return -EINVAL;
				page_map_fn(page);
			}
		}

		x86_pte_store_result(&pt[i], child_entry);
		if (log_fn)
			log_fn(X86_SPLIT_LARGE_PAGE_LOG_RSS_ADD,
					source_fileoff ? (child_entry & PAGE_MASK) :
					(child_entry & PT_PHYSMASK),
					rss_pgsize, rss_pgsize, NULL);
		rss_add_fn(rss_pgsize, rss_pgsize);
		child_entry = x86_split_large_page_next_entry_result(
				child_entry, pgsize);
	}

	x86_pte_store_result(ptep,
			x86_split_large_page_publish_result(virt_to_phys_fn(pt)));

	if (log_fn)
		log_fn(X86_SPLIT_LARGE_PAGE_LOG_RSS_SUB, phys_base, pgsize,
				pgsize, NULL);
	rss_sub_fn(pgsize, pgsize);

	if (x86_split_large_page_source_unmap_result(phys_base, pgsize,
			&phys)) {
		void *page;

		if (!phys_to_page_fn)
			return -EINVAL;
		page = phys_to_page_fn(phys);
		if (page) {
			if (!page_unmap_fn)
				return -EINVAL;
			if (page_unmap_fn(page)) {
				if (log_fn)
					log_fn(X86_SPLIT_LARGE_PAGE_LOG_PAGE_UNMAP,
							phys, pgsize, pgsize, page);
				if (panic_fn)
					panic_fn();
			}
		}
	}

	return 0;
}

int x86_pt_split_body_result(void *pt, void *vm, unsigned long addr,
			     unsigned int memobj_flags, int cpu_id,
			     x86_pt_split_lookup_fn_t lookup_fn,
			     x86_split_phys_to_page_fn_t phys_to_page_fn,
			     x86_pt_splitable_fn_t splitable_fn,
			     x86_pt_split_large_fn_t split_large_fn,
			     x86_pt_split_flush_fn_t flush_fn,
			     x86_pt_split_log_fn_t log_fn)
{
	unsigned long *ptep;
	unsigned long pgaddr;
	size_t pgsize;
	unsigned long entry;
	void *page;
	int error;

	if (!lookup_fn || !splitable_fn || !split_large_fn || !flush_fn)
		return -EINVAL;

	for (;;) {
		pgaddr = 0;
		pgsize = 0;
		ptep = lookup_fn(pt, addr, 0, &pgaddr, &pgsize, NULL);
		if (!ptep || *ptep == PTE_NULL || pgaddr == addr)
			return 0;

		entry = *ptep;
		page = NULL;
		if (!(entry & PTATTR_FILEOFF)) {
			if (!phys_to_page_fn)
				return -EINVAL;
			page = phys_to_page_fn(entry & PT_PHYSMASK);
		}

		if (!splitable_fn(page, memobj_flags)) {
			if (log_fn)
				log_fn(X86_PT_SPLIT_LOG_NOT_SPLITABLE, 0);
			return -EINVAL;
		}

		error = split_large_fn(ptep, pgsize);
		if (error) {
			if (log_fn)
				log_fn(X86_PT_SPLIT_LOG_SPLIT_FAILED, error);
			return error;
		}

		flush_fn(vm, pgaddr, cpu_id);
	}
}

unsigned long x86_clear_pt_page_aligned_addr_result(unsigned long virt,
						    int largepage)
{
	return largepage ? (virt & LARGE_PAGE_MASK) : (virt & PAGE_MASK);
}

int x86_clear_pt_page_target_result(unsigned long l2_entry, int largepage,
				    int *clear_l2p)
{
	if (!(l2_entry & PFL2_PRESENT))
		return -EINVAL;

	if (clear_l2p)
		*clear_l2p = largepage != 0;

	return 0;
}

int x86_pt_clear_page_result(void *pt0, void *init_pt0, unsigned long virt,
			     int largepage,
			     x86_pt_phys_to_virt_fn_t phys_to_virt_fn)
{
	unsigned long *pt = pt0 ? pt0 : init_pt0;
	int l4idx, l3idx, l2idx, l1idx;
	int clear_l2;
	int error;

	if (!pt || !phys_to_virt_fn)
		return -EINVAL;

	virt = x86_clear_pt_page_aligned_addr_result(virt, largepage);
	x86_pt_indices_result(virt, &l4idx, &l3idx, &l2idx, &l1idx);

	if (!(pt[l4idx] & PFL4_PRESENT))
		return -EINVAL;
	pt = phys_to_virt_fn(pt[l4idx] & PAGE_MASK);
	if (!pt)
		return -EINVAL;

	if (!(pt[l3idx] & PFL3_PRESENT))
		return -EINVAL;
	pt = phys_to_virt_fn(pt[l3idx] & PAGE_MASK);
	if (!pt)
		return -EINVAL;

	error = x86_clear_pt_page_target_result(pt[l2idx], largepage,
			&clear_l2);
	if (error)
		return error;
	if (clear_l2) {
		pt[l2idx] = 0;
		return 0;
	}

	pt = phys_to_virt_fn(pt[l2idx] & PAGE_MASK);
	if (!pt)
		return -EINVAL;

	pt[l1idx] = 0;
	return 0;
}

int x86_visit_pte_action_result(unsigned long entry, int skip_null,
				unsigned long start, unsigned long end,
				unsigned long base, unsigned long level_size,
				int target_shift, int pgshift,
				unsigned long size_flag,
				int direct_requires_size,
				int direct_enabled, int can_allocate)
{
	int is_null = entry == PTE_NULL;
	int is_large = size_flag && (entry & size_flag);
	int full_cover = start <= base &&
		(((base + level_size) <= end) || end == 0);
	int pgshift_match = !pgshift || pgshift == target_shift;

	if (is_null) {
		if (skip_null)
			return X86_VISIT_PTE_SKIP;
		if (direct_enabled && !direct_requires_size &&
		    full_cover && pgshift_match)
			return X86_VISIT_PTE_DIRECT;
		return can_allocate ? X86_VISIT_PTE_ALLOC_AND_WALK :
			X86_VISIT_PTE_SKIP;
	}

	if (direct_enabled && (!direct_requires_size || is_large) &&
	    full_cover && pgshift_match)
		return X86_VISIT_PTE_DIRECT;

	if (is_large)
		return X86_VISIT_PTE_SPLIT_ERROR;

	return X86_VISIT_PTE_WALK;
}

int x86_visit_pte_leaf_result(void *visitor_arg, void *root_pt,
			      unsigned long *ptep, unsigned long base,
			      int skip_null, int level_shift,
			      x86_visit_pte_fn_t visitor_fn)
{
	if (!ptep)
		return -EINVAL;
	if (*ptep == PTE_NULL && skip_null)
		return 0;
	if (!visitor_fn)
		return -EINVAL;

	return visitor_fn(visitor_arg, root_pt, ptep, (void *)base,
			  level_shift);
}

int x86_visit_pte_level_result(void *visitor_arg, void *root_pt,
			       unsigned long *ptep, unsigned long base,
			       unsigned long start, unsigned long end,
			       int skip_null, int retry_skip_null,
			       int pgshift, unsigned long level_size,
			       int target_shift, unsigned long size_flag,
			       int direct_requires_size,
			       int direct_enabled, int can_allocate,
			       unsigned long pdir_attr,
			       x86_pt_alloc_pages_fn_t alloc_fn,
			       x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
			       x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
			       x86_visit_pte_walk_fn_t child_walk_fn,
			       void *child_args,
			       x86_visit_pte_fn_t visitor_fn,
			       x86_visit_pte_log_fn_t log_fn)
{
	unsigned long *pt;
	int action;
	int error;

	if (!ptep || !visitor_fn || !child_walk_fn || !phys_to_virt_fn)
		return -EINVAL;

	action = x86_visit_pte_action_result(*ptep, skip_null, start, end,
			base, level_size, target_shift, pgshift, size_flag,
			direct_requires_size, direct_enabled, can_allocate);
	if (action == X86_VISIT_PTE_SKIP)
		return 0;

	if (action == X86_VISIT_PTE_DIRECT) {
		error = visitor_fn(visitor_arg, root_pt, ptep, (void *)base,
				   target_shift);
		if (error != -E2BIG)
			return error;
		action = x86_visit_pte_action_result(*ptep, retry_skip_null,
				start, end, base, level_size, target_shift,
				pgshift, size_flag, direct_requires_size, 0,
				can_allocate);
	}

	if (action == X86_VISIT_PTE_SPLIT_ERROR) {
		if (log_fn)
			log_fn(X86_VISIT_PTE_LOG_SPLIT, target_shift);
		return -ENOMEM;
	}

	if (action == X86_VISIT_PTE_ALLOC_AND_WALK) {
		if (!alloc_fn || !virt_to_phys_fn)
			return -EINVAL;
		pt = alloc_fn(1, IHK_MC_AP_NOWAIT);
		if (!pt)
			return -ENOMEM;
		x86_pte_store_result(ptep, virt_to_phys_fn(pt) | pdir_attr);
	}
	else {
		pt = phys_to_virt_fn(*ptep & PT_PHYSMASK);
	}

	return child_walk_fn(pt, base, start, end, child_args);
}

int x86_visit_pte_root_result(unsigned long *ptep, unsigned long base,
			      unsigned long start, unsigned long end,
			      int skip_null, int can_allocate,
			      unsigned long pdir_attr,
			      x86_pt_alloc_pages_fn_t alloc_fn,
			      x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
			      x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
			      x86_visit_pte_walk_fn_t child_walk_fn,
			      void *child_args)
{
	unsigned long *pt;

	if (!ptep)
		return -EINVAL;
	if (*ptep == PTE_NULL && skip_null)
		return 0;
	if (!child_walk_fn)
		return -EINVAL;

	if (*ptep == PTE_NULL) {
		if (!can_allocate)
			return 0;
		if (!alloc_fn || !virt_to_phys_fn)
			return -EINVAL;
		pt = alloc_fn(1, IHK_MC_AP_NOWAIT);
		if (!pt)
			return -ENOMEM;
		x86_pte_store_result(ptep, virt_to_phys_fn(pt) | pdir_attr);
	}
	else {
		if (!phys_to_virt_fn)
			return -EINVAL;
		pt = phys_to_virt_fn(*ptep & PT_PHYSMASK);
	}

	return child_walk_fn(pt, base, start, end, child_args);
}

int x86_visit_pte_range_dispatch_result(void *pt, unsigned long start,
					unsigned long end, void *args,
					x86_visit_pte_walk_fn_t walk_fn)
{
	if (!walk_fn)
		return -EINVAL;

	return walk_fn(pt, 0, start, end, args);
}

int x86_clear_range_validate_result(unsigned long start, unsigned long end,
				    unsigned long user_start,
				    unsigned long user_end)
{
	return (start < user_start || user_end < end || end <= start) ?
		-EINVAL : 0;
}

int x86_clear_range_free_physical_result(int free_physical, int is_dev_file,
					 int is_premap,
					 int is_straight_main)
{
	if (!free_physical || is_dev_file || is_premap || is_straight_main)
		return 0;

	return 1;
}

int x86_clear_range_entry_action_result(unsigned long entry,
					unsigned long base,
					unsigned long start,
					unsigned long end,
					unsigned long level_size,
					unsigned long size_flag)
{
	if (entry == PTE_NULL)
		return X86_CLEAR_RANGE_SKIP;

	if (entry & size_flag) {
		if (base < start || end < base + level_size)
			return X86_CLEAR_RANGE_SPLIT_ERROR;
		return X86_CLEAR_RANGE_CLEAR_LARGE;
	}

	return X86_CLEAR_RANGE_WALK;
}

void x86_clear_range_old_entry_result(unsigned long entry, size_t pgsize,
				      unsigned long *physp,
				      int *fileoffp, int *dirtyp)
{
	pte_t pte = entry;

	if (physp)
		*physp = pte_get_phys(&pte);
	if (fileoffp)
		*fileoffp = pte_is_fileoff(&pte, pgsize);
	if (dirtyp)
		*dirtyp = pte_is_dirty(&pte, pgsize);
}

int x86_clear_range_old_action_result(int is_fileoff, int free_physical,
				      int has_page, int page_in_memobj,
				      int entry_dirty, int has_memobj,
				      int memobj_no_flush,
				      int memobj_xpmem)
{
	int action = 0;

	if (is_fileoff)
		return 0;

	if (has_page && page_in_memobj && entry_dirty && has_memobj &&
	    !memobj_no_flush)
		action |= X86_CLEAR_OLD_FLUSH_MEMOBJ;

	if (free_physical) {
		if (!has_page) {
			if (!has_memobj || !memobj_xpmem)
				action |= X86_CLEAR_OLD_FREE_ANON;
			else
				action |= X86_CLEAR_OLD_XPMEM_KEEP;
		}
		else {
			action |= X86_CLEAR_OLD_TRY_UNMAP;
		}
	}

	return action;
}

int x86_remote_flush_tlb_add_addr_result(void *vm, unsigned long *addr_array,
					 int *nr_addrp, int max_nr_addr,
					 unsigned long addr, int cpu_id,
					 x86_clear_remote_flush_fn_t flush_fn)
{
	int nr_addr;

	if (!addr_array || !nr_addrp || max_nr_addr <= 0)
		return -EINVAL;

	nr_addr = *nr_addrp;
	if (nr_addr < 0)
		return -EINVAL;

	if (nr_addr < max_nr_addr) {
		addr_array[nr_addr] = addr;
		*nr_addrp = nr_addr + 1;
		return 0;
	}

	if (!flush_fn)
		return -EINVAL;

	flush_fn(vm, addr_array, nr_addr, cpu_id);
	addr_array[0] = addr;
	*nr_addrp = 1;
	return 1;
}

int x86_clear_range_old_effects_result(int old_action, int is_fileoff,
				       int free_physical, void *memobj,
				       void *page, unsigned long phys,
				       unsigned long base, size_t pgsize,
				       x86_clear_flush_memobj_fn_t flush_fn,
				       x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
				       x86_clear_free_pages_fn_t free_pages_fn,
				       x86_clear_page_unmap_fn_t page_unmap_fn,
				       x86_clear_rss_sub_fn_t rss_sub_fn,
				       x86_clear_memobj_rss_sub_fn_t memobj_rss_sub_fn,
				       x86_clear_effect_log_fn_t log_fn)
{
	int nr_pages;

	if (!pgsize)
		return -EINVAL;

	if (old_action & X86_CLEAR_OLD_FLUSH_MEMOBJ) {
		if (!flush_fn)
			return -EINVAL;
		flush_fn(memobj, phys, pgsize);
		if (log_fn)
			log_fn(X86_CLEAR_EFFECT_FLUSH_MEMOBJ, base, phys,
			       pgsize);
	}

	if (is_fileoff || !free_physical)
		return 0;

	nr_pages = pgsize >> PAGE_SHIFT;

	if (old_action & X86_CLEAR_OLD_FREE_ANON) {
		if (!phys_to_virt_fn || !free_pages_fn || !rss_sub_fn)
			return -EINVAL;
		free_pages_fn(phys_to_virt_fn(phys), nr_pages);
		rss_sub_fn(pgsize, pgsize);
		if (log_fn)
			log_fn(X86_CLEAR_EFFECT_FREE_ANON, base, phys,
			       pgsize);
	}
	else if (old_action & X86_CLEAR_OLD_XPMEM_KEEP) {
		if (log_fn)
			log_fn(X86_CLEAR_EFFECT_XPMEM_KEEP, base, phys,
			       pgsize);
	}
	else if (old_action & X86_CLEAR_OLD_TRY_UNMAP) {
		if (!page_unmap_fn || !phys_to_virt_fn || !free_pages_fn ||
		    !memobj_rss_sub_fn)
			return -EINVAL;
		if (page && page_unmap_fn(page)) {
			free_pages_fn(phys_to_virt_fn(phys), nr_pages);
			memobj_rss_sub_fn(memobj, pgsize, pgsize);
			if (log_fn)
				log_fn(X86_CLEAR_EFFECT_FREE_UNMAPPED, base,
				       phys, pgsize);
		}
	}

	return 0;
}

int x86_clear_range_child_table_result(unsigned long *ptep, void *pt,
					       unsigned long start, unsigned long base,
					       unsigned long end,
				       unsigned long level_size, int enabled,
				       void *vm, unsigned long *addr_array,
				       int *nr_addrp, int max_nr_addr,
				       int cpu_id,
				       x86_clear_remote_flush_fn_t flush_fn,
				       x86_pt_free_pages_fn_t free_pages_fn,
				       x86_clear_effect_log_fn_t log_fn)
{
	int ret;

	if (!enabled || !(start <= base && base + level_size <= end))
		return 0;
	if (!ptep || !pt || !level_size || !free_pages_fn)
		return -EINVAL;

	x86_pte_store_result(ptep, PTE_NULL);
	ret = x86_remote_flush_tlb_add_addr_result(vm, addr_array, nr_addrp,
						   max_nr_addr, base, cpu_id,
						   flush_fn);
	if (ret < 0)
		return ret;

	free_pages_fn(pt, 1);
	if (log_fn)
		log_fn(X86_CLEAR_EFFECT_CHILD_FREE, base, 0, level_size);
	return 1;
}

static int x86_clear_range_clear_entry_effects(
	void *args, unsigned long *ptep, unsigned long base, size_t pgsize,
	void *vm, unsigned long *addr_array, int *nr_addrp, int max_nr_addr,
	int cpu_id, int free_physical, void *memobj,
	x86_clear_old_action_fn_t old_action_fn,
	x86_clear_remote_flush_fn_t flush_fn,
	x86_clear_flush_memobj_fn_t flush_memobj_fn,
	x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
	x86_clear_free_pages_fn_t free_pages_fn,
	x86_clear_page_unmap_fn_t page_unmap_fn,
	x86_clear_rss_sub_fn_t rss_sub_fn,
	x86_clear_memobj_rss_sub_fn_t memobj_rss_sub_fn,
	x86_clear_effect_log_fn_t effect_log_fn)
{
	unsigned long phys = 0;
	void *page = NULL;
	unsigned long old;
	int old_action;
	int is_fileoff = 0;

	if (!ptep || !pgsize || !old_action_fn)
		return -EINVAL;

	old = x86_pte_clear_result(ptep);
	(void)x86_remote_flush_tlb_add_addr_result(vm, addr_array, nr_addrp,
						   max_nr_addr, base, cpu_id,
						   flush_fn);

	old_action = old_action_fn(args, old, pgsize, &phys, &page, &is_fileoff);
	if (old_action < 0)
		return old_action;

	return x86_clear_range_old_effects_result(old_action, is_fileoff,
			free_physical, memobj, page, phys, base, pgsize,
			flush_memobj_fn, phys_to_virt_fn, free_pages_fn,
			page_unmap_fn, rss_sub_fn, memobj_rss_sub_fn,
			effect_log_fn);
}

int x86_clear_range_leaf_body_result(
	void *args, unsigned long *ptep, unsigned long base, unsigned long start,
	unsigned long end, void *vm, unsigned long *addr_array, int *nr_addrp,
	int max_nr_addr, int cpu_id, int free_physical, void *memobj,
	x86_clear_old_action_fn_t old_action_fn,
	x86_clear_remote_flush_fn_t flush_fn,
	x86_clear_flush_memobj_fn_t flush_memobj_fn,
	x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
	x86_clear_free_pages_fn_t free_pages_fn,
	x86_clear_page_unmap_fn_t page_unmap_fn,
	x86_clear_rss_sub_fn_t rss_sub_fn,
	x86_clear_memobj_rss_sub_fn_t memobj_rss_sub_fn,
	x86_clear_effect_log_fn_t effect_log_fn)
{
	(void)start;
	(void)end;

	if (!ptep)
		return -EINVAL;
	if (*ptep == PTE_NULL)
		return -ENOENT;

	return x86_clear_range_clear_entry_effects(args, ptep, base, PTL1_SIZE,
			vm, addr_array, nr_addrp, max_nr_addr, cpu_id,
			free_physical, memobj, old_action_fn, flush_fn,
			flush_memobj_fn, phys_to_virt_fn, free_pages_fn,
			page_unmap_fn, rss_sub_fn, memobj_rss_sub_fn,
			effect_log_fn);
}

int x86_clear_range_level_body_result(
	void *args, unsigned long *ptep, unsigned long base, unsigned long start,
	unsigned long end, int level_shift, unsigned long level_size,
	unsigned long size_flag, int child_teardown_enabled, void *vm,
	unsigned long *addr_array, int *nr_addrp, int max_nr_addr, int cpu_id,
	int free_physical, void *memobj,
	x86_clear_old_action_fn_t old_action_fn,
	x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
	x86_clear_child_walk_fn_t child_walk_fn,
	x86_clear_remote_flush_fn_t flush_fn,
	x86_pt_free_pages_fn_t pt_free_pages_fn,
	x86_clear_flush_memobj_fn_t flush_memobj_fn,
	x86_clear_free_pages_fn_t free_pages_fn,
	x86_clear_page_unmap_fn_t page_unmap_fn,
	x86_clear_rss_sub_fn_t rss_sub_fn,
	x86_clear_memobj_rss_sub_fn_t memobj_rss_sub_fn,
	x86_clear_range_log_fn_t range_log_fn,
	x86_clear_effect_log_fn_t effect_log_fn)
{
	void *child_pt;
	unsigned long old;
	unsigned long phys = 0;
	int action;
	int error;

	if (!ptep)
		return -EINVAL;

	action = x86_clear_range_entry_action_result(*ptep, base, start, end,
			level_size, size_flag);
	if (action == X86_CLEAR_RANGE_SKIP)
		return -ENOENT;
	if (action == X86_CLEAR_RANGE_SPLIT_ERROR) {
		if (range_log_fn)
			range_log_fn(X86_CLEAR_RANGE_LOG_SPLIT, args, ptep,
				     base, start, end, -EINVAL, level_shift, 0);
		return -EINVAL;
	}
	if (action == X86_CLEAR_RANGE_CLEAR_LARGE) {
		old = *ptep;
		error = x86_clear_range_clear_entry_effects(args, ptep, base,
				level_size, vm, addr_array, nr_addrp,
				max_nr_addr, cpu_id, free_physical, memobj,
				old_action_fn, flush_fn, flush_memobj_fn,
				phys_to_virt_fn, free_pages_fn, page_unmap_fn,
				rss_sub_fn, memobj_rss_sub_fn, effect_log_fn);
		if (level_shift == PTL3_SHIFT && range_log_fn) {
			x86_clear_range_old_entry_result(old, level_size,
					&phys, NULL, NULL);
			range_log_fn(X86_CLEAR_RANGE_LOG_LARGE_PHYS, args,
				     ptep, base, start, end, error, level_shift,
				     phys);
		}
		return error;
	}

	if (!phys_to_virt_fn || !child_walk_fn)
		return -EINVAL;
	child_pt = phys_to_virt_fn(*ptep & PT_PHYSMASK);
	if (!child_pt)
		return -EINVAL;

	error = child_walk_fn(child_pt, base, start, end, args);
	if (error && error != -ENOENT)
		return error;

	error = x86_clear_range_child_table_result(ptep, child_pt, start, base,
			end, level_size, child_teardown_enabled, vm, addr_array,
			nr_addrp, max_nr_addr, cpu_id, flush_fn, pt_free_pages_fn,
			effect_log_fn);
	if (error < 0)
		return error;

	return 0;
}

int x86_clear_range_root_body_result(void *args, unsigned long *ptep,
				     unsigned long base, unsigned long start,
				     unsigned long end,
				     x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
				     x86_clear_child_walk_fn_t child_walk_fn)
{
	void *child_pt;

	if (!ptep)
		return -EINVAL;
	if (*ptep == PTE_NULL)
		return -ENOENT;
	if (!phys_to_virt_fn || !child_walk_fn)
		return -EINVAL;

	child_pt = phys_to_virt_fn(*ptep & PT_PHYSMASK);
	if (!child_pt)
		return -EINVAL;

	return child_walk_fn(child_pt, base, start, end, args);
}

int x86_clear_range_top_result(void *pt, void *vm, unsigned long start,
				       unsigned long end, unsigned long user_start,
				       unsigned long user_end, int requested_free,
			       int is_dev_file, int is_premap,
			       int is_straight_main, void *memobj,
			       unsigned long **addr_slot, int *nr_addrp,
			       int *max_nr_addrp, int *free_physicalp,
			       void **memobj_slot, void **vm_slot,
			       int tlb_array_pages, unsigned long page_size,
			       void *args, x86_pt_alloc_pages_fn_t alloc_fn,
			       x86_pt_free_pages_fn_t free_fn,
			       x86_range_top_walk_fn_t walk_fn,
			       x86_clear_remote_flush_fn_t flush_fn,
			       int cpu_id, x86_clear_range_top_log_fn_t log_fn)
{
	unsigned long *addr;
	int error;
	int max_nr_addr;
	int free_physical;

	if (!addr_slot || !nr_addrp || !max_nr_addrp || !free_physicalp ||
	    !memobj_slot || !vm_slot || !args || !alloc_fn || !free_fn ||
	    !walk_fn || !flush_fn || tlb_array_pages <= 0 ||
	    page_size < sizeof(unsigned long)) {
		return -EINVAL;
	}

	if (x86_clear_range_validate_result(start, end, user_start, user_end)) {
		if (log_fn)
			log_fn(X86_CLEAR_TOP_LOG_INVALID, pt, start, end,
			       requested_free);
		return -EINVAL;
	}

	addr = alloc_fn(tlb_array_pages, IHK_MC_AP_CRITICAL);
	if (!addr) {
		if (log_fn)
			log_fn(X86_CLEAR_TOP_LOG_ALLOC_FAILED, pt, start, end,
			       requested_free);
		return -ENOMEM;
	}

	max_nr_addr = (int)((tlb_array_pages * page_size) /
			   sizeof(unsigned long));
	free_physical = x86_clear_range_free_physical_result(
		requested_free, is_dev_file, is_premap, is_straight_main);

	*addr_slot = addr;
	*nr_addrp = 0;
	*max_nr_addrp = max_nr_addr;
	*free_physicalp = free_physical;
	*memobj_slot = memobj;
	*vm_slot = vm;

	error = walk_fn(pt, 0, start, end, args);
	if (*nr_addrp > 0)
		flush_fn(vm, addr, *nr_addrp, cpu_id);

	free_fn(addr, tlb_array_pages);

	return error;
}

int x86_change_attr_leaf_action_result(unsigned long entry,
				       unsigned long fileoff_flag)
{
	if (entry == PTE_NULL || (fileoff_flag && (entry & fileoff_flag)))
		return X86_CHANGE_ATTR_ENOENT;

	return X86_CHANGE_ATTR_APPLY;
}

int x86_change_attr_entry_action_result(unsigned long entry,
					unsigned long base,
					unsigned long start,
					unsigned long end,
					unsigned long level_size,
					unsigned long size_flag,
					unsigned long fileoff_flag)
{
	if (entry == PTE_NULL || (fileoff_flag && (entry & fileoff_flag)))
		return X86_CHANGE_ATTR_ENOENT;

	if (size_flag && (entry & size_flag)) {
		if (base < start || end < base + level_size)
			return X86_CHANGE_ATTR_SPLIT_ERROR;
		return X86_CHANGE_ATTR_APPLY;
	}

	return X86_CHANGE_ATTR_WALK;
}

struct x86_pt_change_attr_args {
	unsigned long clrpte;
	unsigned long setpte;
	x86_pt_phys_to_virt_fn_t phys_to_virt_fn;
};

static int x86_pt_change_attr_l1(void *arg0, unsigned long *ptep,
				 uint64_t base, uint64_t start,
				 uint64_t end)
{
	struct x86_pt_change_attr_args *args = arg0;
	int action = x86_change_attr_leaf_action_result(*ptep, PFL1_FILEOFF);

	if (action == X86_CHANGE_ATTR_ENOENT)
		return -ENOENT;

	x86_pte_apply_attr_result(ptep, args->clrpte, args->setpte);
	return 0;
}

static int x86_pt_change_attr_l2(void *arg0, unsigned long *ptep,
				 uint64_t base, uint64_t start,
				 uint64_t end)
{
	struct x86_pt_change_attr_args *args = arg0;
	unsigned long *pt;
	int action = x86_change_attr_entry_action_result(*ptep, base, start,
			end, PTL2_SIZE, PFL2_SIZE, PFL2_FILEOFF);

	if (action == X86_CHANGE_ATTR_ENOENT)
		return -ENOENT;
	if (action == X86_CHANGE_ATTR_SPLIT_ERROR)
		return -EINVAL;
	if (action == X86_CHANGE_ATTR_APPLY) {
		x86_pte_apply_attr_result(ptep, args->clrpte, args->setpte);
		return 0;
	}

	pt = args->phys_to_virt_fn(*ptep & PT_PHYSMASK);
	if (!pt)
		return -EINVAL;
	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			PTL2_SIZE, PTL1_SHIFT, x86_pt_change_attr_l1, arg0,
			NULL, PT_PHYSMASK);
}

static int x86_pt_change_attr_l3(void *arg0, unsigned long *ptep,
				 uint64_t base, uint64_t start,
				 uint64_t end)
{
	struct x86_pt_change_attr_args *args = arg0;
	unsigned long *pt;
	int action = x86_change_attr_entry_action_result(*ptep, base, start,
			end, PTL3_SIZE, PFL3_SIZE, PFL3_FILEOFF);

	if (action == X86_CHANGE_ATTR_ENOENT)
		return -ENOENT;
	if (action == X86_CHANGE_ATTR_SPLIT_ERROR)
		return -EINVAL;
	if (action == X86_CHANGE_ATTR_APPLY) {
		x86_pte_apply_attr_result(ptep, args->clrpte, args->setpte);
		return 0;
	}

	pt = args->phys_to_virt_fn(*ptep & PT_PHYSMASK);
	if (!pt)
		return -EINVAL;
	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			PTL3_SIZE, PTL2_SHIFT, x86_pt_change_attr_l2, arg0,
			NULL, PT_PHYSMASK);
}

static int x86_pt_change_attr_l4(void *arg0, unsigned long *ptep,
				 uint64_t base, uint64_t start,
				 uint64_t end)
{
	struct x86_pt_change_attr_args *args = arg0;
	unsigned long *pt;
	int action = x86_change_attr_entry_action_result(*ptep, base, start,
			end, 0, 0, 0);

	if (action == X86_CHANGE_ATTR_ENOENT)
		return -ENOENT;

	pt = args->phys_to_virt_fn(*ptep & PT_PHYSMASK);
	if (!pt)
		return -EINVAL;
	return x86_walk_pte_range_result((unsigned long)pt, base, start, end,
			PTL4_SIZE, PTL3_SHIFT, x86_pt_change_attr_l3, arg0,
			NULL, PT_PHYSMASK);
}

int x86_pt_change_attr_range_result(void *pt, unsigned long start,
				    unsigned long end, unsigned long clrpte,
				    unsigned long setpte,
				    x86_pt_phys_to_virt_fn_t phys_to_virt_fn)
{
	struct x86_pt_change_attr_args args = {
		.clrpte = clrpte,
		.setpte = setpte,
		.phys_to_virt_fn = phys_to_virt_fn,
	};

	if (!phys_to_virt_fn)
		return -EINVAL;

	return x86_walk_pte_range_result((unsigned long)pt, 0, start, end,
			0, PTL4_SHIFT, x86_pt_change_attr_l4, &args,
			NULL, PT_PHYSMASK);
}

int x86_set_range_leaf_action_result(unsigned long entry)
{
	return entry == PTE_NULL ? X86_SET_RANGE_APPLY : X86_SET_RANGE_BUSY;
}

int x86_set_range_entry_action_result(unsigned long entry,
				      unsigned long base,
				      unsigned long start,
				      unsigned long end,
				      unsigned long diff,
				      int pgshift,
				      int target_shift,
				      unsigned long level_size,
				      unsigned long size_flag,
				      int direct_enabled)
{
	int full_cover = start <= base && (base + level_size) <= end;
	int diff_aligned = !(diff & (level_size - 1));
	int pgshift_match = !pgshift || pgshift == target_shift;

	if (entry == PTE_NULL) {
		if (direct_enabled && full_cover && diff_aligned &&
		    pgshift_match)
			return X86_SET_RANGE_MAP_LARGE;
		return X86_SET_RANGE_ALLOC_AND_WALK;
	}

	if (size_flag && (entry & size_flag))
		return X86_SET_RANGE_BUSY;

	return X86_SET_RANGE_WALK;
}

int x86_set_range_map_entry_result(unsigned long phys_base,
				   unsigned long base,
				   unsigned long start,
				   unsigned long attr,
				   int level_shift,
				   unsigned long attr_mask,
				   unsigned long *physp,
				   unsigned long *entryp)
{
	unsigned long phys = phys_base + (base - start);
	unsigned long entry;

	if (level_shift == PTL1_SHIFT)
		entry = phys | x86_attr_to_l1attr_result(attr, attr_mask);
	else if (level_shift == PTL2_SHIFT)
		entry = phys | x86_attr_to_l2attr_result(
			attr | PTATTR_LARGEPAGE, attr_mask);
	else if (level_shift == PTL3_SHIFT)
		entry = phys | x86_attr_to_l3attr_result(
			attr | PTATTR_LARGEPAGE, attr_mask);
	else
		return -EINVAL;

	if (physp)
		*physp = phys;
	if (entryp)
		*entryp = entry;

	return 0;
}

int x86_set_range_conflict_result(void *pt, void *vm, unsigned long start,
				  unsigned long end, unsigned long base,
				  unsigned long current, int level_shift,
				  int free_physical,
				  x86_set_range_clear_fn_t clear_fn,
				  x86_set_range_log_fn_t log_fn)
{
	if (!clear_fn)
		return -EINVAL;

	if (log_fn)
		log_fn(X86_SET_RANGE_LOG_BUSY, level_shift, base, start, end,
		       -EBUSY, current, start, base, end, free_physical);
	clear_fn(pt, vm, start, base, free_physical, NULL);

	return -EBUSY;
}

int x86_set_range_alloc_failed_result(void *pt, void *vm,
				      unsigned long start,
				      unsigned long end,
				      unsigned long base,
				      unsigned long current,
				      int level_shift,
				      int free_physical,
				      x86_set_range_clear_fn_t clear_fn,
				      x86_set_range_log_fn_t log_fn)
{
	if (!clear_fn)
		return -EINVAL;

	if (log_fn)
		log_fn(X86_SET_RANGE_LOG_ALLOC_FAILED, level_shift, base,
		       start, end, -ENOMEM, current, start, base, end,
		       free_physical);
	clear_fn(pt, vm, start, base, free_physical, NULL);

	return -ENOMEM;
}

int x86_set_range_walk_failed_result(int error, unsigned long base,
				     unsigned long start, unsigned long end,
				     unsigned long current, int level_shift,
				     x86_set_range_log_fn_t log_fn)
{
	if (error && log_fn)
		log_fn(X86_SET_RANGE_LOG_WALK_FAILED, level_shift, base,
		       start, end, error, current, start, base, end, error);

	return error;
}

int x86_set_range_map_effect_result(unsigned long phys_base,
				    unsigned long base,
				    unsigned long start,
				    unsigned long end,
				    unsigned long attr,
				    int level_shift,
				    unsigned long attr_mask,
				    size_t pgsize,
				    unsigned long *ptep,
				    void *range,
				    int log_large,
				    x86_set_range_rss_add_fn_t rss_add_fn,
				    x86_set_range_log_fn_t log_fn)
{
	unsigned long phys;
	unsigned long entry;
	int ret;
	int rss_called;

	if (!ptep || !pgsize || !rss_add_fn)
		return -EINVAL;

	ret = x86_set_range_map_entry_result(phys_base, base, start, attr,
					     level_shift, attr_mask, &phys,
					     &entry);
	if (ret)
		return ret;

	ret = x86_pte_store_result(ptep, entry);
	if (ret)
		return ret;

	if (log_large && log_fn)
		log_fn(X86_SET_RANGE_LOG_MAP_LARGE, level_shift, base, start,
		       end, 0, *ptep, phys, pgsize, pgsize, 0);

	rss_called = rss_add_fn(range, phys, pgsize, pgsize);
	if (log_fn)
		log_fn(rss_called ? X86_SET_RANGE_LOG_RSS_ADD :
		       X86_SET_RANGE_LOG_RSS_SKIP, level_shift, base, start,
		       end, 0, *ptep, phys, pgsize, pgsize, rss_called);

	return 0;
}

int x86_set_range_leaf_body_result(void *args, unsigned long *ptep,
				   unsigned long base, unsigned long start,
				   unsigned long end, void *pt, void *vm,
				   unsigned long phys_base,
				   unsigned long attr,
				   unsigned long attr_mask, void *range,
				   x86_set_range_clear_fn_t clear_fn,
				   x86_set_range_rss_add_fn_t rss_add_fn,
				   x86_set_range_log_fn_t log_fn)
{
	int action;

	(void)args;
	if (!ptep)
		return -EINVAL;

	action = x86_set_range_leaf_action_result(*ptep);
	if (action == X86_SET_RANGE_BUSY)
		return x86_set_range_conflict_result(pt, vm, start, end,
						     base, *ptep, PTL1_SHIFT,
						     0, clear_fn, log_fn);

	return x86_set_range_map_effect_result(phys_base, base, start, end,
					       attr, PTL1_SHIFT, attr_mask,
					       PTL1_SIZE, ptep, range, 0,
					       rss_add_fn, log_fn);
}

int x86_set_range_level_body_result(void *args, unsigned long *ptep,
				    unsigned long base, unsigned long start,
				    unsigned long end, void *pt, void *vm,
				    unsigned long phys_base,
				    unsigned long attr,
				    unsigned long attr_mask,
				    unsigned long diff, int pgshift,
				    int target_shift,
				    unsigned long level_size,
				    unsigned long size_flag,
				    int direct_enabled,
				    unsigned long pdir_attr, void *range,
				    x86_pt_alloc_pages_fn_t alloc_fn,
				    x86_pt_free_pages_fn_t free_fn,
				    x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				    x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
				    x86_set_range_child_walk_fn_t child_walk_fn,
				    x86_set_range_clear_fn_t clear_fn,
				    x86_set_range_rss_add_fn_t rss_add_fn,
				    x86_set_range_log_fn_t log_fn)
{
	void *newpt = NULL;
	void *child_pt = NULL;
	unsigned long current;
	unsigned long old;
	int action;
	int error;
	int child_walk_failed = 0;

	if (!ptep || !alloc_fn || !free_fn || !virt_to_phys_fn ||
	    !phys_to_virt_fn || !child_walk_fn)
		return -EINVAL;

	for (;;) {
		current = *ptep;
		action = x86_set_range_entry_action_result(current, base, start,
				end, diff, pgshift, target_shift, level_size,
				size_flag, direct_enabled);

		if (action == X86_SET_RANGE_ALLOC_AND_WALK) {
			if (!newpt) {
				newpt = x86_pt_alloc_zeroed_result(
						IHK_MC_AP_NOWAIT, alloc_fn);
				if (!newpt) {
					error = x86_set_range_alloc_failed_result(
							pt, vm, start, end,
							base, current,
							target_shift, 0,
							clear_fn, log_fn);
					break;
				}
			}

			old = x86_pte_publish_table_result(
					ptep, virt_to_phys_fn(newpt) |
					pdir_attr);
			if (old != PTE_NULL)
				continue;

			child_pt = newpt;
			newpt = NULL;
			error = child_walk_fn(child_pt, base, start, end, args);
			child_walk_failed = !!error;
			break;
		}
		else if (action == X86_SET_RANGE_MAP_LARGE) {
			error = x86_set_range_map_effect_result(phys_base, base,
					start, end, attr, target_shift,
					attr_mask, level_size, ptep, range, 1,
					rss_add_fn, log_fn);
			break;
		}
		else if (action == X86_SET_RANGE_BUSY) {
			error = x86_set_range_conflict_result(pt, vm, start,
					end, base, current, target_shift, 0,
					clear_fn, log_fn);
			break;
		}
		else {
			child_pt = phys_to_virt_fn(current & PT_PHYSMASK);
			if (!child_pt) {
				error = -EINVAL;
				break;
			}
			error = child_walk_fn(child_pt, base, start, end, args);
			child_walk_failed = !!error;
			break;
		}
	}

	if (child_walk_failed)
		error = x86_set_range_walk_failed_result(error, base, start,
				end, *ptep, target_shift, log_fn);
	if (newpt)
		free_fn(newpt, 1);

	return error;
}

int x86_set_range_top_result(void *pt, void *vm, unsigned long start,
			     unsigned long end, unsigned long phys,
			     int attr, int pgshift, void *range, void *args,
			     void **args_ptp, unsigned long *args_physp,
			     int *args_attrp, unsigned long *args_diffp,
			     void **args_vmp, int *args_pgshiftp,
			     void **args_rangep, x86_range_top_walk_fn_t walk_fn,
			     x86_set_range_log_fn_t log_fn)
{
	int error;

	if (!args || !args_ptp || !args_physp || !args_attrp ||
	    !args_diffp || !args_vmp || !args_pgshiftp || !args_rangep ||
	    !walk_fn) {
		return -EINVAL;
	}

	*args_ptp = pt;
	*args_physp = phys;
	*args_attrp = attr;
	*args_diffp = start ^ phys;
	*args_vmp = vm;
	*args_pgshiftp = pgshift;
	*args_rangep = range;

	error = walk_fn(pt, 0, start, end, args);
	if (error)
		return x86_set_range_walk_failed_result(error, 0, start, end,
							0, 0, log_fn);

	return 0;
}

int x86_pte_store_result(unsigned long *ptep, unsigned long entry)
{
	if (!ptep)
		return -EINVAL;

	*ptep = entry;
	return 0;
}

unsigned long x86_pte_publish_table_result(unsigned long *ptep,
					   unsigned long entry)
{
	if (!ptep)
		return ~0UL;

	return atomic_cmpxchg8(ptep, PTE_NULL, entry);
}

unsigned long x86_pte_clear_result(unsigned long *ptep)
{
	if (!ptep)
		return ~0UL;

	return atomic_xchg_ulong(ptep, PTE_NULL);
}

unsigned long x86_pte_apply_attr_result(unsigned long *ptep,
					unsigned long clrpte,
					unsigned long setpte)
{
	if (!ptep)
		return ~0UL;

	*ptep = (*ptep & ~clrpte) | setpte;
	return *ptep;
}

int x86_pt_kernel_lock_needed_result(unsigned long virt)
{
	return virt >= 0xffff000000000000UL;
}

void *x86_pt_alloc_zeroed_result(int ap_flag,
				 x86_pt_alloc_pages_fn_t alloc_fn)
{
	unsigned long *pt;
	int i;

	if (!alloc_fn)
		return NULL;

	pt = alloc_fn(1, ap_flag);
	if (!pt)
		return NULL;

	for (i = 0; i < PT_ENTRIES; i++)
		pt[i] = 0;

	return pt;
}

unsigned long *x86_pt_get_pte_result(void *pt0, void *init_pt0,
				     unsigned long virt, unsigned long attr,
				     unsigned long attr_mask, int ap_flag,
				     x86_pt_alloc_pages_fn_t alloc_fn,
				     x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				     x86_pt_phys_to_virt_fn_t phys_to_virt_fn)
{
	unsigned long *pt = pt0 ? pt0 : init_pt0;
	unsigned long *entryp;
	unsigned long entry;
	int l4idx, l3idx, l2idx, l1idx;
	void *newpt;

	if (!pt || !virt_to_phys_fn || !phys_to_virt_fn)
		return NULL;

	x86_pt_indices_result(virt, &l4idx, &l3idx, &l2idx, &l1idx);

	entryp = &pt[l4idx];
	entry = *entryp;
	if (entry & PFL4_PRESENT) {
		pt = phys_to_virt_fn(entry & PAGE_MASK);
		if (!pt)
			return NULL;
	}
	else {
		newpt = x86_pt_alloc_zeroed_result(ap_flag, alloc_fn);
		if (!newpt)
			return NULL;
		*entryp = virt_to_phys_fn(newpt) |
			((attr & attr_mask) | PFL4_PRESENT);
		pt = newpt;
	}

	entryp = &pt[l3idx];
	entry = *entryp;
	if (entry & PFL3_PRESENT) {
		pt = phys_to_virt_fn(entry & PAGE_MASK);
		if (!pt)
			return NULL;
	}
	else {
		newpt = x86_pt_alloc_zeroed_result(ap_flag, alloc_fn);
		if (!newpt)
			return NULL;
		*entryp = virt_to_phys_fn(newpt) |
			x86_attr_to_l3attr_result(attr, attr_mask);
		pt = newpt;
	}

	if (attr & PTATTR_LARGEPAGE)
		return &pt[l2idx];

	entryp = &pt[l2idx];
	entry = *entryp;
	if (entry & PFL2_SIZE)
		return NULL;
	if (entry & PFL2_PRESENT) {
		pt = phys_to_virt_fn(entry & PAGE_MASK);
		if (!pt)
			return NULL;
	}
	else {
		newpt = x86_pt_alloc_zeroed_result(ap_flag, alloc_fn);
		if (!newpt)
			return NULL;
		*entryp = virt_to_phys_fn(newpt) |
			x86_attr_to_l2attr_result(attr, attr_mask) |
			PFL2_PRESENT;
		pt = newpt;
	}

	return &pt[l1idx];
}

int x86_pt_set_page_body_result(void *pt0, void *init_pt0,
				unsigned long virt, unsigned long phys,
				unsigned long attr, unsigned long attr_mask,
				x86_pt_alloc_pages_fn_t alloc_fn,
				x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
				x86_pt_set_page_log_fn_t log_fn)
{
	unsigned long *pt = pt0 ? pt0 : init_pt0;
	unsigned long *entryp;
	unsigned long entry;
	int l4idx, l3idx, l2idx, l1idx;
	int ap_flag;
	void *newpt;

	if (!pt || !virt_to_phys_fn || !phys_to_virt_fn)
		return -ENOMEM;

	ap_flag = (attr & PTATTR_FOR_USER) ? 0x000002 : 0x000001;
	phys &= (attr & PTATTR_LARGEPAGE) ? LARGE_PAGE_MASK : PAGE_MASK;

	x86_pt_indices_result(virt, &l4idx, &l3idx, &l2idx, &l1idx);

	entryp = &pt[l4idx];
	entry = *entryp;
	if (entry & PFL4_PRESENT) {
		pt = phys_to_virt_fn(entry & PAGE_MASK);
		if (!pt)
			return -ENOMEM;
	}
	else {
		newpt = x86_pt_alloc_zeroed_result(ap_flag, alloc_fn);
		if (!newpt)
			return -ENOMEM;
		*entryp = virt_to_phys_fn(newpt) | PFL4_PDIR_ATTR;
		pt = newpt;
	}

	entryp = &pt[l3idx];
	entry = *entryp;
	if (entry & PFL3_PRESENT) {
		pt = phys_to_virt_fn(entry & PAGE_MASK);
		if (!pt)
			return -ENOMEM;
	}
	else {
		newpt = x86_pt_alloc_zeroed_result(ap_flag, alloc_fn);
		if (!newpt)
			return -ENOMEM;
		*entryp = virt_to_phys_fn(newpt) | PFL3_PDIR_ATTR;
		pt = newpt;
	}

	if (attr & PTATTR_LARGEPAGE) {
		entryp = &pt[l2idx];
		entry = *entryp;
		if (entry & PFL2_PRESENT)
			return ((entry & PAGE_MASK) != phys) ? -ENOMEM : 0;

		*entryp = phys | x86_attr_to_l2attr_result(attr, attr_mask) |
			PFL2_SIZE;
		return 0;
	}

	entryp = &pt[l2idx];
	entry = *entryp;
	if (entry & PFL2_PRESENT) {
		pt = phys_to_virt_fn(entry & PAGE_MASK);
		if (!pt)
			return -ENOMEM;
	}
	else {
		newpt = x86_pt_alloc_zeroed_result(ap_flag, alloc_fn);
		if (!newpt)
			return -ENOMEM;
		*entryp = virt_to_phys_fn(newpt) | PFL2_PDIR_ATTR;
		pt = newpt;
	}

	entryp = &pt[l1idx];
	entry = *entryp;
	if (entry & PFL1_PRESENT) {
		if ((entry & PT_PHYSMASK) != phys) {
			if (log_fn)
				log_fn(virt);
			return -EBUSY;
		}
		return 0;
	}

	*entryp = phys | x86_attr_to_l1attr_result(attr, attr_mask);
	return 0;
}

int x86_lookup_default_pgshift_result(int pgshift, int use_1gb_page)
{
	if (pgshift)
		return pgshift;

	return use_1gb_page ? PTL3_SHIFT : PTL2_SHIFT;
}

int x86_lookup_l4_empty_pgshift_result(int pgshift)
{
	return pgshift > PTL3_SHIFT ? PTL3_SHIFT : pgshift;
}

int x86_lookup_level_action_result(unsigned long entry, int pgshift,
				   int level_shift, unsigned long size_flag)
{
	if (entry == PTE_NULL || (size_flag && (entry & size_flag)))
		return pgshift >= level_shift ? X86_LOOKUP_PTE_HIT :
			X86_LOOKUP_PTE_MISS;

	return X86_LOOKUP_PTE_WALK;
}

void x86_lookup_shape_result(unsigned long virt, int pgshift,
			     unsigned long *basep, size_t *sizep,
			     int *p2alignp)
{
	size_t size = (size_t)1 << pgshift;
	unsigned long base = virt & ~(size - 1);

	if (basep)
		*basep = base;
	if (sizep)
		*sizep = size;
	if (p2alignp)
		*p2alignp = pgshift - PAGE_SHIFT;
}

unsigned long *x86_pt_lookup_pte_result(void *pt0, unsigned long virt,
					int pgshift, int use_1gb_page,
					unsigned long *basep,
					size_t *sizep, int *p2alignp,
					x86_pt_phys_to_virt_fn_t phys_to_virt_fn)
{
	unsigned long *pt = pt0;
	unsigned long *ptep = NULL;
	int l4idx, l3idx, l2idx, l1idx;
	int action;

	x86_pt_indices_result(virt, &l4idx, &l3idx, &l2idx, &l1idx);
	pgshift = x86_lookup_default_pgshift_result(pgshift, use_1gb_page);

	if (!pt)
		goto out;
	if (pt[l4idx] == PTE_NULL) {
		pgshift = x86_lookup_l4_empty_pgshift_result(pgshift);
		goto out;
	}
	if (!phys_to_virt_fn)
		goto out;

	pt = phys_to_virt_fn(pt[l4idx] & PT_PHYSMASK);
	if (!pt)
		goto out;
	action = x86_lookup_level_action_result(pt[l3idx], pgshift,
			PTL3_SHIFT, PFL3_SIZE);
	if (action == X86_LOOKUP_PTE_HIT) {
		ptep = &pt[l3idx];
		pgshift = PTL3_SHIFT;
		goto out;
	}
	if (action == X86_LOOKUP_PTE_MISS)
		goto out;

	pt = phys_to_virt_fn(pt[l3idx] & PT_PHYSMASK);
	if (!pt)
		goto out;
	action = x86_lookup_level_action_result(pt[l2idx], pgshift,
			PTL2_SHIFT, PFL2_SIZE);
	if (action == X86_LOOKUP_PTE_HIT) {
		ptep = &pt[l2idx];
		pgshift = PTL2_SHIFT;
		goto out;
	}
	if (action == X86_LOOKUP_PTE_MISS)
		goto out;

	pt = phys_to_virt_fn(pt[l2idx] & PT_PHYSMASK);
	if (!pt)
		goto out;
	ptep = &pt[l1idx];
	pgshift = PTL1_SHIFT;

out:
	x86_lookup_shape_result(virt, pgshift, basep, sizep, p2alignp);
	return ptep;
}

int x86_move_pte_preflight_result(unsigned long entry, size_t pgsize,
				  unsigned long src, unsigned long dest,
				  unsigned long pgaddr,
				  unsigned long *mapped_destp)
{
	pte_t pte = entry;

	if (pte_is_fileoff(&pte, pgsize))
		return -ENOTSUPP;

	if (mapped_destp)
		*mapped_destp = dest + (pgaddr - src);

	return 0;
}

int x86_move_one_page_body_result(void *arg, void *pt, unsigned long *ptep,
				  unsigned long pgaddr, int pgshift,
				  unsigned long src, unsigned long dest,
				  void *vm, void *range,
				  x86_move_set_range_fn_t set_range_fn,
				  x86_move_log_fn_t log_fn)
{
	size_t pgsize;
	unsigned long mapped_dest;
	unsigned long entry;
	unsigned long old_entry;
	unsigned long phys;
	unsigned long attr;
	int error;

	if (!set_range_fn || !ptep || pgshift < 0)
		return -EINVAL;

	pgsize = (size_t)1 << pgshift;
	entry = *ptep;
	error = x86_move_pte_preflight_result(entry, pgsize, src, dest,
			pgaddr, &mapped_dest);
	if (error) {
		if (log_fn)
			log_fn(X86_MOVE_ONE_LOG_FILEOFF, arg, pt, ptep, entry,
					entry, pgaddr, pgshift, error);
		return error;
	}

	old_entry = x86_pte_clear_result(ptep);
	x86_move_pte_entry_parts_result(old_entry, &phys, &attr);

	error = set_range_fn(pt, vm, mapped_dest, mapped_dest + pgsize, phys,
			attr, pgshift, range, 0);
	if (error) {
		if (log_fn)
			log_fn(X86_MOVE_ONE_LOG_SET_FAILED, arg, pt, ptep,
					old_entry, *ptep, pgaddr, pgshift, error);
		return error;
	}

	return 0;
}

int x86_move_pte_range_body_result(void *pt, unsigned long src,
				   unsigned long dest, size_t size,
				   void *vm, void *range, void *args,
				   uintptr_t *args_srcp,
				   uintptr_t *args_destp,
				   void **args_vmp, void **args_rangep,
				   x86_visit_pte_fn_t visitor_fn,
				   x86_move_visit_range_fn_t visit_fn,
				   x86_move_flush_fn_t flush_fn)
{
	int error;

	if (!visitor_fn || !visit_fn || !flush_fn || !args ||
	    !args_srcp || !args_destp || !args_vmp || !args_rangep)
		return -EINVAL;

	*args_srcp = src;
	*args_destp = dest;
	*args_vmp = vm;
	*args_rangep = range;

	error = visit_fn(pt, src, src + size, 0, 0x0001, visitor_fn, args);
	flush_fn();
	if (error)
		return error;

	return 0;
}

void x86_load_cr3_result(unsigned long pt_addr)
{
	asm volatile ("movq %0, %%cr3" : : "r"(pt_addr) : "memory");
}

unsigned long x86_read_cr3_result(void)
{
	unsigned long cr3;

	asm volatile("movq %%cr3, %0" : "=r"(cr3) : : "memory");
	return cr3;
}

void x86_flush_tlb_body_result(x86_read_cr3_fn_t read_cr3_fn,
			       x86_load_cr3_fn_t load_cr3_fn)
{
	unsigned long cr3;

	if (!read_cr3_fn || !load_cr3_fn)
		return;

	cr3 = read_cr3_fn();
	load_cr3_fn(cr3);
}

void x86_flush_tlb_result(void)
{
	x86_flush_tlb_body_result(x86_read_cr3_result, x86_load_cr3_result);
}

void x86_flush_tlb_single_body_result(unsigned long addr,
				      x86_invlpg_fn_t invlpg_fn)
{
	if (invlpg_fn)
		invlpg_fn(addr);
}

void x86_flush_tlb_single_result(unsigned long addr)
{
	asm volatile("invlpg (%0)" :: "r" (addr) : "memory");
}

int x86_load_page_table_body_result(void *pt, void *init_pt,
				    x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				    x86_load_cr3_fn_t load_cr3_fn)
{
	unsigned long pt_addr;
	void *target;

	if (!virt_to_phys_fn || !load_cr3_fn)
		return -EINVAL;

	target = pt ? pt : init_pt;
	if (!target)
		return -EINVAL;

	pt_addr = virt_to_phys_fn(target);
	load_cr3_fn(pt_addr);
	return 0;
}

void *x86_map_fixed_area_body_result(void *init_pt, unsigned long *fixed_virtp,
				     unsigned long phys, unsigned long size,
				     int uncachable,
				     x86_pt_set_page_fn_t set_page_fn,
				     x86_move_flush_fn_t flush_fn)
{
	unsigned long poffset;
	unsigned long paligned;
	unsigned long npages;
	unsigned long fixed;
	unsigned long base;
	unsigned long attr;
	unsigned long i;

	if (!init_pt || !fixed_virtp || !set_page_fn || !flush_fn)
		return NULL;

	poffset = phys & (PAGE_SIZE - 1);
	paligned = phys & PAGE_MASK;
	npages = (poffset + size + PAGE_SIZE - 1) >> PAGE_SHIFT;
	fixed = *fixed_virtp;
	base = fixed;
	attr = PTATTR_WRITABLE | PTATTR_ACTIVE;
	if (uncachable)
		attr |= PTATTR_UNCACHABLE;

	for (i = 0; i < npages; i++) {
		if (set_page_fn(init_pt, fixed, paligned, attr))
			return NULL;
		fixed += PAGE_SIZE;
		paligned += PAGE_SIZE;
	}

	*fixed_virtp = fixed;
	flush_fn();
	return (void *)(base + poffset);
}

int x86_init_normal_area_body_result(void *pt, unsigned long map_st_start,
				     unsigned long large_page_size,
				     unsigned long writable_attr,
				     int map_start_key, int map_end_key,
				     x86_get_memory_address_fn_t get_addr_fn,
				     x86_pt_set_page_fn_t set_large_fn,
				     x86_init_normal_log_fn_t log_fn)
{
	unsigned long map_start;
	unsigned long map_end;
	unsigned long phys;
	unsigned long virt;
	int error;

	if (!pt || !large_page_size || !get_addr_fn || !set_large_fn || !log_fn)
		return -EINVAL;

	map_start = get_addr_fn(map_start_key, 0);
	map_end = get_addr_fn(map_end_key, 0);
	virt = map_st_start + map_start;

	log_fn(X86_INIT_NORMAL_LOG_RANGE, map_start, map_end, virt);

	for (phys = map_start; phys < map_end; phys += large_page_size) {
		error = set_large_fn(pt, virt, phys, writable_attr);
		if (error)
			log_fn(X86_INIT_NORMAL_LOG_SET_FAILED, virt, phys,
			       (unsigned long)error);
		virt += large_page_size;
	}

	return 0;
}

int x86_init_text_area_body_result(void *pt, unsigned long map_kernel_start,
				   unsigned long end_addr,
				   unsigned long large_page_size,
				   int large_page_shift,
				   unsigned long large_page_mask,
				   unsigned long kernel_phys_base,
				   unsigned long writable_attr,
				   x86_pt_set_page_fn_t set_large_fn,
				   x86_init_text_log_fn_t log_fn)
{
	unsigned long end_aligned;
	unsigned long nlpages;
	unsigned long phys;
	unsigned long virt;
	unsigned long i;

	if (!pt || !large_page_size || large_page_shift < 0 ||
	    large_page_shift >= (int)(sizeof(unsigned long) * 8) ||
	    !set_large_fn || !log_fn)
		return -EINVAL;

	end_aligned = (end_addr + large_page_size * 2 - 1) & large_page_mask;
	nlpages = (end_aligned - map_kernel_start) >> large_page_shift;

	log_fn(X86_INIT_TEXT_LOG_LPAGES, nlpages, 0, 0);
	log_fn(X86_INIT_TEXT_LOG_BASE, kernel_phys_base, 0, 0);

	phys = kernel_phys_base;
	virt = map_kernel_start;
	for (i = 0; i < nlpages; i++) {
		set_large_fn(pt, virt, phys, writable_attr);
		virt += large_page_size;
		phys += large_page_size;
	}

	return 0;
}

int x86_init_fixed_area_body_result(unsigned long *fixed_virtp,
				    unsigned long map_fixed_start)
{
	if (!fixed_virtp)
		return -EINVAL;

	*fixed_virtp = map_fixed_start;
	return 0;
}

int x86_init_low_area_body_result(void *pt, unsigned long no_execute_attr,
				  unsigned long writable_attr,
				  x86_pt_set_page_fn_t set_large_fn)
{
	if (!pt || !set_large_fn)
		return -EINVAL;

	set_large_fn(pt, 0, 0, no_execute_attr | writable_attr);
	return 0;
}

int x86_init_vsyscall_area_body_result(void *pt, unsigned long vsyscall_addr,
				       void *vsyscall_page,
				       unsigned long attr,
				       x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
				       x86_pt_set_page_fn_t set_page_fn)
{
	unsigned long phys;

	if (!pt || !vsyscall_page || !virt_to_phys_fn || !set_page_fn)
		return -EINVAL;

	phys = virt_to_phys_fn(vsyscall_page);
	return set_page_fn(pt, vsyscall_addr, phys, attr);
}

int x86_init_linux_kernel_mapping_body_result(
	void *pt, unsigned long linux_page_offset_base,
	unsigned long large_page_size, unsigned long writable_attr,
	unsigned long full_map_end, char *safe_kernel_map_name,
	x86_find_command_line_fn_t find_command_line_fn,
	x86_get_nr_memory_chunks_fn_t get_nr_chunks_fn,
	x86_get_memory_chunk_fn_t get_chunk_fn,
	x86_pt_set_page_fn_t set_large_fn,
	x86_init_linux_log_fn_t log_fn)
{
	unsigned long map_start;
	unsigned long map_end;
	unsigned long phys;
	unsigned long virt;
	int nr_memory_chunks;
	int chunk_id;
	int numa_id;
	int error;

	if (!pt || !large_page_size || !safe_kernel_map_name ||
	    !find_command_line_fn || !get_nr_chunks_fn || !get_chunk_fn ||
	    !set_large_fn || !log_fn)
		return -EINVAL;

	if (find_command_line_fn(safe_kernel_map_name) == NULL) {
		log_fn(X86_INIT_LINUX_LOG_FULL, 0, 0, 0, 0, 0);
		map_start = 0;
		map_end = full_map_end;
		virt = linux_page_offset_base;
		log_fn(X86_INIT_LINUX_LOG_FULL_RANGE, virt, virt + map_end,
		       0, map_end, 0);

		for (phys = map_start; phys < map_end;
		     phys += large_page_size) {
			error = set_large_fn(pt, virt, phys, writable_attr);
			if (error)
				log_fn(X86_INIT_LINUX_LOG_FULL_SET_FAILED,
				       virt, phys, 0, 0, error);
			virt += large_page_size;
		}
		return 0;
	}

	log_fn(X86_INIT_LINUX_LOG_CHUNKS, 0, 0, 0, 0, 0);
	nr_memory_chunks = get_nr_chunks_fn();
	if (nr_memory_chunks == 0) {
		log_fn(X86_INIT_LINUX_LOG_NO_CHUNK, 0, 0, 0, 0, 0);
		return 0;
	}

	for (chunk_id = 0; chunk_id < nr_memory_chunks; chunk_id++) {
		if (get_chunk_fn(chunk_id, &map_start, &map_end, &numa_id)) {
			log_fn(X86_INIT_LINUX_LOG_BAD_CHUNK,
			       (unsigned long)chunk_id, 0, 0, 0, 0);
			continue;
		}

		log_fn(X86_INIT_LINUX_LOG_CHUNK_RANGE,
		       linux_page_offset_base + map_start,
		       linux_page_offset_base + map_end,
		       map_start, map_end, 0);

		virt = linux_page_offset_base + map_start;
		for (phys = map_start; phys < map_end;
		     phys += large_page_size) {
			error = set_large_fn(pt, virt, phys, writable_attr);
			if (error)
				log_fn(X86_INIT_LINUX_LOG_CHUNK_SET_FAILED,
				       virt, phys, 0, 0, error);
			virt += large_page_size;
		}
	}

	return 0;
}

unsigned long x86_virt_to_phys_body_result(
	unsigned long va, unsigned long map_kernel_start,
	unsigned long kernel_phys_base, unsigned long linux_page_offset_base,
	unsigned long map_fixed_start, unsigned long map_st_start,
	x86_addr_log_fn_t log_fn)
{
	if (va >= map_kernel_start) {
		if (log_fn)
			log_fn(X86_ADDR_LOG_KERNEL, va);
		return va - map_kernel_start + kernel_phys_base;
	}
	if (va >= linux_page_offset_base)
		return va - linux_page_offset_base;
	if (va >= map_fixed_start)
		return va - map_fixed_start;

	if (log_fn)
		log_fn(X86_ADDR_LOG_STRAIGHT, va);
	return va - map_st_start;
}

void *x86_phys_to_virt_body_result(unsigned long phys, int init_pt_loaded,
				   unsigned long map_st_start,
				   unsigned long linux_page_offset_base)
{
	if (!init_pt_loaded)
		return (void *)(phys + map_st_start);

	return (void *)(phys + linux_page_offset_base);
}

int x86_reserve_arch_pages_body_result(
	void *pa_allocator, unsigned long start, unsigned long end,
	void *head, void *last_early_heap,
	unsigned long ap_trampoline, unsigned long ap_trampoline_size,
	unsigned long page_size,
	x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
	x86_reserve_pages_cb_fn_t cb_fn,
	x86_reserve_arch_fn_t reserve_arch_fn)
{
	unsigned long head_phys;
	unsigned long heap_phys;

	if (!pa_allocator || !head || !last_early_heap || !virt_to_phys_fn ||
	    !cb_fn || !reserve_arch_fn)
		return -EINVAL;

	head_phys = virt_to_phys_fn(head);
	heap_phys = virt_to_phys_fn(last_early_heap);
	cb_fn(pa_allocator, head_phys, heap_phys, 0);
	cb_fn(pa_allocator, ap_trampoline,
	      ap_trampoline + ap_trampoline_size, 0);
	cb_fn(pa_allocator, 0, page_size, 0);
	reserve_arch_fn(start, end, cb_fn);
	return 0;
}

void x86_move_pte_entry_parts_result(unsigned long entry,
				     unsigned long *physp,
				     unsigned long *attrp)
{
	if (physp)
		*physp = entry & PT_PHYSMASK;
	if (attrp)
		*attrp = entry & ~PT_PHYSMASK;
}

unsigned long x86_arch_vrflag_to_ptattr_result(unsigned long flag,
					       uint64_t fault,
					       unsigned long common_attr)
{
	if ((fault & PF_PROT) ||
	    ((fault & (PF_POPULATE | PF_PATCH)) && (flag & VR_PRIVATE)))
		common_attr |= PTATTR_DIRTY;

	return common_attr;
}

int x86_destroy_pt_entry_action_result(int level, unsigned long entry,
				       unsigned long *lower_physp)
{
	if (lower_physp)
		*lower_physp = 0;

	if (level <= 1)
		return X86_DESTROY_PT_SKIP;
	if (!(entry & PF_PRESENT))
		return X86_DESTROY_PT_SKIP;
	if (entry & PF_SIZE)
		return X86_DESTROY_PT_SKIP;

	if (lower_physp)
		*lower_physp = entry & PT_PHYSMASK;
	return X86_DESTROY_PT_DESCEND;
}

void *x86_pt_create_result(void *init_pt, int ap_flag,
			   x86_pt_alloc_pages_fn_t alloc_fn)
{
	unsigned long *init = init_pt;
	unsigned long *pt;
	int i;

	if (!alloc_fn)
		return NULL;

	pt = alloc_fn(1, ap_flag);
	if (!pt)
		return NULL;

	for (i = 0; i < PT_ENTRIES; i++)
		pt[i] = 0;

	for (i = PT_ENTRIES / 2; i < PT_ENTRIES; i++)
		pt[i] = init[i];

	return pt;
}

int x86_pt_destroy_table_result(int level, void *pt,
				x86_pt_phys_to_virt_fn_t phys_to_virt_fn,
				x86_pt_free_pages_fn_t free_pages_fn,
				x86_pt_destroy_panic_fn_t panic_fn)
{
	unsigned long *entries = pt;
	int ix;

	if ((level < 1) || (4 < level)) {
		if (panic_fn)
			panic_fn(X86_PT_DESTROY_PANIC_LEVEL);
		return -EINVAL;
	}
	if (!pt) {
		if (panic_fn)
			panic_fn(X86_PT_DESTROY_PANIC_NULL);
		return -EINVAL;
	}
	if (!free_pages_fn)
		return -EINVAL;
	if (level > 1 && !phys_to_virt_fn)
		return -EINVAL;

	if (level > 1) {
		for (ix = 0; ix < PT_ENTRIES; ix++) {
			unsigned long entry = entries[ix];
			unsigned long lower_phys;
			void *lower;
			int ret;

			if (x86_destroy_pt_entry_action_result(level, entry,
					&lower_phys) != X86_DESTROY_PT_DESCEND)
				continue;

			lower = phys_to_virt_fn(lower_phys);
			ret = x86_pt_destroy_table_result(level - 1, lower,
					phys_to_virt_fn, free_pages_fn,
					panic_fn);
			if (ret)
				return ret;
		}
	}

	free_pages_fn(pt, 1);
	return 0;
}

void x86_pt_destroy_root_result(void *pt, x86_pt_destroy_fn_t destroy_fn)
{
	unsigned long *entries = pt;
	int i;

	for (i = PT_ENTRIES / 2; i < PT_ENTRIES; i++)
		entries[i] = 0;

	if (destroy_fn)
		destroy_fn(4, pt);
}

int x86_pt_prepare_map_result(void *pt, void *init_pt, unsigned long virt,
			      unsigned long size, int flag,
			      unsigned long writable_attr,
			      x86_pt_alloc_pages_fn_t alloc_fn,
			      x86_pt_virt_to_phys_fn_t virt_to_phys_fn,
			      x86_pt_set_page_fn_t set_page_fn)
{
	unsigned long *entries = pt ? pt : init_pt;
	unsigned long v = virt;
	int l4idx = (v >> PTL4_SHIFT) & (PT_ENTRIES - 1);
	int ret = 0;

	if (flag == 0) {
		int l4e = ((v + size) >> PTL4_SHIFT) & (PT_ENTRIES - 1);

		if (!alloc_fn || !virt_to_phys_fn)
			return -ENOMEM;

		for (; l4idx <= l4e; l4idx++) {
			if (entries[l4idx] & PFL4_PRESENT) {
				return 0;
			} else {
				void *newpt = alloc_fn(1, 0x000001);

				if (!newpt) {
					ret = -ENOMEM;
				} else {
					entries[l4idx] = virt_to_phys_fn(newpt) |
						PFL4_PDIR_ATTR;
				}
			}
		}
	} else {
		unsigned long end = v + size;

		if (!set_page_fn)
			return -ENOMEM;

		for (; v < end; v += PAGE_SIZE) {
			ret = set_page_fn(entries, v, 0, writable_attr);
			if (ret)
				break;
		}
	}

	return ret;
}

int x86_pt_set_pte_body_result(void *pt, unsigned long *ptep, size_t pgsize,
			       unsigned long phys, unsigned long attr,
			       unsigned long attr_mask, int use_1gb_page,
			       x86_pt_set_pte_log_fn_t log_fn,
			       x86_pt_set_pte_panic_fn_t panic_fn)
{
	unsigned long entry = 0;
	unsigned long current = ptep ? *ptep : 0;
	int error;

	error = x86_pt_set_pte_value_result(pgsize, phys, attr, attr_mask,
					    use_1gb_page, &entry);
	if (error) {
		if (error == -1 && pgsize == PTL2_SIZE) {
			if (log_fn)
				log_fn(X86_PT_SET_PTE_LOG_L2_ALIGN, pt, ptep,
				       pgsize, phys, attr, error, current);
			return error;
		}
		if (error == -1 && pgsize == PTL3_SIZE) {
			if (log_fn)
				log_fn(X86_PT_SET_PTE_LOG_L3_ALIGN, pt, ptep,
				       pgsize, phys, attr, error, current);
			return error;
		}
		if (log_fn)
			log_fn(X86_PT_SET_PTE_LOG_PAGE_SIZE, pt, ptep, pgsize,
			       phys, attr, error, current);
		if (panic_fn)
			panic_fn();
		return error;
	}

	x86_pte_store_result(ptep, entry);
	return 0;
}

static void x86_user_copy_bytes_fallback(void *dst, const void *src,
					 size_t size)
{
	unsigned char *d = dst;
	const unsigned char *s = src;
	size_t i;

	for (i = 0; i < size; i++)
		d[i] = s[i];
}

static int x86_user_range_valid_fallback(unsigned long uaddr, size_t size,
					 unsigned long user_start,
					 unsigned long user_end)
{
	return !(uaddr < user_start || user_end <= uaddr ||
		 (user_end - uaddr) < size);
}

int x86_verify_process_vm_result(void *vm, unsigned long uaddr, size_t size,
				 unsigned long user_start,
				 unsigned long user_end,
				 unsigned long reason,
				 x86_user_page_fault_fn_t page_fault_fn,
				 x86_user_log_fn_t log_fn)
{
	unsigned long uend;
	unsigned long addr;
	int error;

	if (!x86_user_range_valid_fallback(uaddr, size, user_start, user_end)) {
		if (log_fn)
			log_fn(X86_USER_COPY_LOG_RANGE, vm, uaddr, size,
			       -EFAULT);
		return -EFAULT;
	}
	if (!page_fault_fn)
		return -EFAULT;

	uend = uaddr + size;
	for (addr = uaddr & PAGE_MASK; addr < uend; addr += PAGE_SIZE) {
		if (!addr)
			return -EINVAL;

		error = page_fault_fn(vm, (void *)addr, reason);
		if (error) {
			if (log_fn)
				log_fn(X86_USER_COPY_LOG_PF, vm, addr,
				       reason, error);
			return error;
		}
	}

	return 0;
}

int x86_process_vm_copy_result(void *vm, void *pt, unsigned long user_addr,
			       unsigned long kernel_addr, size_t size,
			       unsigned long user_start, unsigned long user_end,
			       unsigned long reason, int direction,
			       x86_user_page_fault_fn_t page_fault_fn,
			       x86_user_vtop_fn_t vtop_fn,
			       x86_user_is_memory_fn_t is_memory_fn,
			       x86_user_map_fn_t map_fn,
			       x86_user_unmap_fn_t unmap_fn,
			       x86_user_phys_to_virt_fn_t phys_to_virt_fn,
			       x86_user_log_fn_t log_fn)
{
	unsigned long user_cursor = user_addr;
	unsigned long kernel_cursor = kernel_addr;
	size_t remain = size;
	int error;

	if (reason & PF_PATCH) {
		if (log_fn)
			log_fn(X86_USER_COPY_LOG_PATCH_START, vm,
			       user_addr, kernel_addr, size);
	}

	error = x86_verify_process_vm_result(vm, user_addr, size,
					     user_start, user_end, reason,
					     page_fault_fn, log_fn);
	if (error) {
		if ((reason & PF_PATCH) && log_fn) {
			log_fn(error == -EFAULT ? X86_USER_COPY_LOG_PATCH_RANGE :
			       X86_USER_COPY_LOG_PATCH_PF, vm, user_addr,
			       size, error);
		}
		return error;
	}

	if (!vtop_fn || !is_memory_fn || !map_fn || !unmap_fn ||
	    !phys_to_virt_fn)
		return -EFAULT;

	while (remain > 0) {
		size_t cpsize = PAGE_SIZE - (user_cursor & (PAGE_SIZE - 1));
		unsigned long pa = 0;
		void *va;
		int is_lwk;

		if (cpsize > remain)
			cpsize = remain;

		error = vtop_fn(pt, (const void *)user_cursor, &pa);
		if (error) {
			if (log_fn)
				log_fn((reason & PF_PATCH) ?
				       X86_USER_COPY_LOG_PATCH_VTOP :
				       X86_USER_COPY_LOG_VTOP, vm,
				       user_cursor, pa, error);
			return error;
		}

		is_lwk = is_memory_fn(pa, pa + cpsize);
		if (!is_lwk) {
			if (log_fn)
				log_fn(X86_USER_COPY_LOG_EXTERNAL, vm, pa,
				       cpsize, 0);
			va = map_fn(pa, 1, PTATTR_ACTIVE);
		} else {
			va = phys_to_virt_fn(pa);
		}
		if (!va)
			return -EFAULT;

		if (direction == X86_USER_COPY_READ)
			x86_user_copy_bytes_fallback((void *)kernel_cursor, va,
						     cpsize);
		else
			x86_user_copy_bytes_fallback(va,
						     (const void *)kernel_cursor,
						     cpsize);

		if (!is_lwk)
			unmap_fn(va, 1);

		user_cursor += cpsize;
		kernel_cursor += cpsize;
		remain -= cpsize;
	}

	if (reason & PF_PATCH) {
		if (log_fn)
			log_fn(X86_USER_COPY_LOG_PATCH_DONE, vm, user_addr,
			       kernel_addr, 0);
	}
	return 0;
}

int x86_copy_from_user_result(void *vm, void *dst, const void *src,
			      size_t size, x86_read_process_vm_fn_t read_fn)
{
	return read_fn ? read_fn(vm, dst, src, size) : -EFAULT;
}

int x86_copy_to_user_result(void *vm, void *dst, const void *src,
			    size_t size, x86_write_process_vm_fn_t write_fn)
{
	return write_fn ? write_fn(vm, dst, src, size) : -EFAULT;
}

long x86_getlong_user_result(long *dest, const long *src,
			     x86_copy_from_user_fn_t copy_fn)
{
	return copy_fn ? copy_fn(dest, src, sizeof(long)) : -EFAULT;
}

int x86_getint_user_result(int *dest, const int *src,
			   x86_copy_from_user_fn_t copy_fn)
{
	return copy_fn ? copy_fn(dest, src, sizeof(int)) : -EFAULT;
}

int x86_setlong_user_result(long *dst, long data,
			    x86_copy_to_user_fn_t copy_fn)
{
	return copy_fn ? copy_fn(dst, &data, sizeof(data)) : -EFAULT;
}

int x86_setint_user_result(int *dst, int data,
			   x86_copy_to_user_fn_t copy_fn)
{
	return copy_fn ? copy_fn(dst, &data, sizeof(data)) : -EFAULT;
}

int x86_strlen_user_result(void *vm, const char *src,
			   unsigned long map_kernel_start,
			   x86_user_page_fault_fn_t verify_fn)
{
	int maxlen = PAGE_SIZE - ((unsigned long)src & (PAGE_SIZE - 1));
	unsigned long pgstart = (unsigned long)src & PAGE_MASK;
	const char *head = src;
	int error;

	if (!verify_fn)
		return -EFAULT;
	if (!pgstart || pgstart >= map_kernel_start)
		return -EFAULT;

	for (;;) {
		error = verify_fn(vm, (void *)src, 1);
		if (error)
			return error;
		while (*src && maxlen > 0) {
			src++;
			maxlen--;
		}
		if (!*src)
			break;
		maxlen = PAGE_SIZE;
	}
	return src - head;
}

int x86_strcpy_from_user_result(void *vm, char *dst, const char *src,
				unsigned long map_kernel_start,
				x86_user_page_fault_fn_t verify_fn)
{
	int maxlen = PAGE_SIZE - ((unsigned long)src & (PAGE_SIZE - 1));
	unsigned long pgstart = (unsigned long)src & PAGE_MASK;
	int error;

	if (!verify_fn)
		return -EFAULT;
	if (!pgstart || pgstart >= map_kernel_start)
		return -EFAULT;

	for (;;) {
		error = verify_fn(vm, (void *)src, 1);
		if (error)
			return error;
		while (*src && maxlen > 0) {
			*(dst++) = *(src++);
			maxlen--;
		}
		if (!*src) {
			*dst = '\0';
			break;
		}
		maxlen = PAGE_SIZE;
	}
	return 0;
}

static struct process_vm *x86_public_thread_vm_fallback(void *thread)
{
	return ((struct thread *)thread)->vm;
}

int x86_copy_from_user_public_result(void *thread, void *dst,
				     const void *src, size_t size,
				     x86_read_process_vm_fn_t read_fn)
{
	return x86_copy_from_user_result(x86_public_thread_vm_fallback(thread),
					 dst, src, size, read_fn);
}

int x86_copy_to_user_public_result(void *thread, void *dst, const void *src,
				   size_t size,
				   x86_write_process_vm_fn_t write_fn)
{
	return x86_copy_to_user_result(x86_public_thread_vm_fallback(thread),
				       dst, src, size, write_fn);
}

int x86_copy_from_user_direct_public_result(void *thread, void *dst,
					    const void *src, size_t size,
					    x86_user_page_fault_fn_t page_fault_fn,
					    x86_user_vtop_fn_t vtop_fn,
					    x86_user_is_memory_fn_t is_memory_fn,
					    x86_user_map_fn_t map_fn,
					    x86_user_unmap_fn_t unmap_fn,
					    x86_user_phys_to_virt_fn_t phys_to_virt_fn,
					    x86_user_log_fn_t log_fn)
{
	return x86_read_process_vm_public_result(
		x86_public_thread_vm_fallback(thread), dst, src, size,
		page_fault_fn, vtop_fn, is_memory_fn, map_fn, unmap_fn,
		phys_to_virt_fn, log_fn);
}

int x86_copy_to_user_direct_public_result(void *thread, void *dst,
					  const void *src, size_t size,
					  x86_user_page_fault_fn_t page_fault_fn,
					  x86_user_vtop_fn_t vtop_fn,
					  x86_user_is_memory_fn_t is_memory_fn,
					  x86_user_map_fn_t map_fn,
					  x86_user_unmap_fn_t unmap_fn,
					  x86_user_phys_to_virt_fn_t phys_to_virt_fn,
					  x86_user_log_fn_t log_fn)
{
	return x86_write_process_vm_public_result(
		x86_public_thread_vm_fallback(thread), dst, src, size,
		page_fault_fn, vtop_fn, is_memory_fn, map_fn, unmap_fn,
		phys_to_virt_fn, log_fn);
}

int x86_strlen_user_public_result(void *thread, const char *src,
				  unsigned long map_kernel_start,
				  x86_user_page_fault_fn_t verify_fn)
{
	return x86_strlen_user_result(x86_public_thread_vm_fallback(thread),
				      src, map_kernel_start, verify_fn);
}

int x86_strcpy_from_user_public_result(void *thread, char *dst,
				       const char *src,
				       unsigned long map_kernel_start,
				       x86_user_page_fault_fn_t verify_fn)
{
	return x86_strcpy_from_user_result(x86_public_thread_vm_fallback(thread),
					   dst, src, map_kernel_start,
					   verify_fn);
}

long x86_getlong_user_public_result(long *dest, const long *src,
				    x86_copy_from_user_fn_t copy_fn)
{
	return x86_getlong_user_result(dest, src, copy_fn);
}

int x86_getint_user_public_result(int *dest, const int *src,
				  x86_copy_from_user_fn_t copy_fn)
{
	return x86_getint_user_result(dest, src, copy_fn);
}

int x86_setlong_user_public_result(long *dst, long data,
				   x86_copy_to_user_fn_t copy_fn)
{
	return x86_setlong_user_result(dst, data, copy_fn);
}

int x86_setint_user_public_result(int *dst, int data,
				  x86_copy_to_user_fn_t copy_fn)
{
	return x86_setint_user_result(dst, data, copy_fn);
}

int x86_verify_process_vm_public_result(void *vmp, const void *usrc,
					size_t size,
					x86_user_page_fault_fn_t page_fault_fn,
					x86_user_log_fn_t log_fn)
{
	struct process_vm *vm = vmp;

	return x86_verify_process_vm_result(vm, (unsigned long)usrc, size,
					    vm->region.user_start,
					    vm->region.user_end, PF_USER,
					    page_fault_fn, log_fn);
}

int x86_read_process_vm_public_result(void *vmp, void *kdst,
				      const void *usrc, size_t size,
				      x86_user_page_fault_fn_t page_fault_fn,
				      x86_user_vtop_fn_t vtop_fn,
				      x86_user_is_memory_fn_t is_memory_fn,
				      x86_user_map_fn_t map_fn,
				      x86_user_unmap_fn_t unmap_fn,
				      x86_user_phys_to_virt_fn_t phys_to_virt_fn,
				      x86_user_log_fn_t log_fn)
{
	struct process_vm *vm = vmp;

	return x86_process_vm_copy_result(vm, vm->address_space->page_table,
					  (unsigned long)usrc,
					  (unsigned long)kdst, size,
					  vm->region.user_start,
					  vm->region.user_end, PF_USER,
					  X86_USER_COPY_READ, page_fault_fn,
					  vtop_fn, is_memory_fn, map_fn,
					  unmap_fn, phys_to_virt_fn, log_fn);
}

int x86_write_process_vm_public_result(void *vmp, void *udst,
				       const void *ksrc, size_t size,
				       x86_user_page_fault_fn_t page_fault_fn,
				       x86_user_vtop_fn_t vtop_fn,
				       x86_user_is_memory_fn_t is_memory_fn,
				       x86_user_map_fn_t map_fn,
				       x86_user_unmap_fn_t unmap_fn,
				       x86_user_phys_to_virt_fn_t phys_to_virt_fn,
				       x86_user_log_fn_t log_fn)
{
	struct process_vm *vm = vmp;

	return x86_process_vm_copy_result(vm, vm->address_space->page_table,
					  (unsigned long)udst,
					  (unsigned long)ksrc, size,
					  vm->region.user_start,
					  vm->region.user_end,
					  PF_POPULATE | PF_WRITE | PF_USER,
					  X86_USER_COPY_WRITE, page_fault_fn,
					  vtop_fn, is_memory_fn, map_fn,
					  unmap_fn, phys_to_virt_fn, log_fn);
}

int x86_patch_process_vm_public_result(void *vmp, void *udst,
				       const void *ksrc, size_t size,
				       x86_user_page_fault_fn_t page_fault_fn,
				       x86_user_vtop_fn_t vtop_fn,
				       x86_user_is_memory_fn_t is_memory_fn,
				       x86_user_map_fn_t map_fn,
				       x86_user_unmap_fn_t unmap_fn,
				       x86_user_phys_to_virt_fn_t phys_to_virt_fn,
				       x86_user_log_fn_t log_fn)
{
	struct process_vm *vm = vmp;

	return x86_process_vm_copy_result(vm, vm->address_space->page_table,
					  (unsigned long)udst,
					  (unsigned long)ksrc, size,
					  vm->region.user_start,
					  vm->region.user_end,
					  PF_PATCH | PF_WRITE | PF_USER,
					  X86_USER_COPY_WRITE, page_fault_fn,
					  vtop_fn, is_memory_fn, map_fn,
					  unmap_fn, phys_to_virt_fn, log_fn);
}

#endif /* MCKERNEL_RUST_X86_MEMORY_HELPERS */
