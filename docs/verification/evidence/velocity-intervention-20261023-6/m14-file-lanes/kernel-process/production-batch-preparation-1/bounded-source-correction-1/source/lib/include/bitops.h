/* bitops.h COPYRIGHT FUJITSU LIMITED 2015-2016 */
#ifndef INCLUDE_BITOPS_H
#define INCLUDE_BITOPS_H

#include <types.h>

#ifndef __ASSEMBLY__

unsigned long find_next_bit(const unsigned long *addr, unsigned long size,
			    unsigned long offset);

unsigned long find_next_zero_bit(const unsigned long *addr, 
				 unsigned long size, unsigned long offset);

unsigned long find_first_bit(const unsigned long *addr, 
			     unsigned long size);

unsigned long find_first_zero_bit(const unsigned long *addr, 
				  unsigned long size);

#include <bitops-test_bit.h>

extern unsigned int __sw_hweight32(unsigned int w);
extern unsigned int __sw_hweight16(unsigned int w);
extern unsigned int __sw_hweight8(unsigned int w);
extern unsigned long __sw_hweight64(uint64_t w);
unsigned long hweight_long(unsigned long w);

#define BITS_PER_BYTE		8

unsigned long ihk_bit_word(unsigned long nr);
unsigned long ihk_align_mask(unsigned long x, unsigned long mask);
unsigned long ihk_align(unsigned long x, unsigned long a);
int ihk_is_aligned(unsigned long x, unsigned long a);

#endif /*__ASSEMBLY__*/

#include <arch-bitops.h>

#endif /*INCLUDE_BITOPS_H*/
