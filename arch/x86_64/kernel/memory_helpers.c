/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <arch-memory.h>
#include <arch-memory-helpers.h>

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

#endif /* MCKERNEL_RUST_X86_MEMORY_HELPERS */
