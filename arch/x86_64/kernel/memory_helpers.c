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

#endif /* MCKERNEL_RUST_X86_MEMORY_HELPERS */
