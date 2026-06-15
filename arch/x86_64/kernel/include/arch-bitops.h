/**
 * \file arch-bitops.h
 *  License details are found in the file LICENSE.
 * \brief
 *  Find last set bit in word.
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 */
/*
 * HISTORY
 */

#ifndef HEADER_X86_COMMON_ARCH_BITOPS_H
#define HEADER_X86_COMMON_ARCH_BITOPS_H

#define ARCH_HAS_FAST_MULTIPLIER 1

int fls(int x);
int ffs(int x);
unsigned long __ffs(unsigned long word);
unsigned long ffz(unsigned long word);
void set_bit(int nr, volatile unsigned long *addr);
void clear_bit(int nr, volatile unsigned long *addr);

#endif
