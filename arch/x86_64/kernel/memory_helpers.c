/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <arch-memory.h>
#include <arch-memory-helpers.h>
#include <ihk/atomic.h>

#ifndef MCKERNEL_RUST_X86_MEMORY_HELPERS

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

	return xchg(ptep, PTE_NULL);
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

void x86_move_pte_entry_parts_result(unsigned long entry,
				     unsigned long *physp,
				     unsigned long *attrp)
{
	if (physp)
		*physp = entry & PT_PHYSMASK;
	if (attrp)
		*attrp = entry & ~PT_PHYSMASK;
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

#endif /* MCKERNEL_RUST_X86_MEMORY_HELPERS */
