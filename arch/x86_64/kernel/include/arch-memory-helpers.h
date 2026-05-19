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
int x86_smaller_page_size_result(size_t cursize, int use_1gb_page,
				 size_t *newsizep, int *p2alignp);

#endif /* HEADER_X86_MEMORY_HELPERS_H */
