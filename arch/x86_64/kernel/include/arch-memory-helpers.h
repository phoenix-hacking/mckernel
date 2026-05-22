/* SPDX-License-Identifier: GPL-2.0 */
#ifndef HEADER_X86_MEMORY_HELPERS_H
#define HEADER_X86_MEMORY_HELPERS_H

#include <ihk/types.h>

unsigned long x86_attr_to_l3attr_result(unsigned long attr,
					unsigned long attr_mask);
unsigned long x86_attr_to_l2attr_result(unsigned long attr,
					unsigned long attr_mask);
unsigned long x86_attr_to_l1attr_result(unsigned long attr,
					unsigned long attr_mask);
unsigned long x86_set_pte_value_result(unsigned long phys,
					unsigned long attr,
					unsigned long attr_mask);
int x86_pt_set_pte_value_result(size_t pgsize, unsigned long phys,
				unsigned long attr, unsigned long attr_mask,
				int use_1gb_page, unsigned long *entryp);
int x86_smaller_page_size_result(size_t cursize, int use_1gb_page,
				 size_t *newsizep, int *p2alignp);
unsigned long x86_early_alloc_align_end_result(unsigned long end_addr);
int x86_early_alloc_exhausted_result(unsigned long current_phys,
				     unsigned long bootstrap_end);
unsigned long x86_early_alloc_next_result(unsigned long current,
					  int nr_pages);

#endif /* HEADER_X86_MEMORY_HELPERS_H */
