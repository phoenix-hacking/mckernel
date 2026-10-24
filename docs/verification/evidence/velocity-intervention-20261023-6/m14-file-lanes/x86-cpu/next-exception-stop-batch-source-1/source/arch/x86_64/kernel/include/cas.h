/**
 * \file arch/x86/kernel/include/cas.h
 *  License details are found in the file LICENSE.
 * \brief
 *  compare and swap
 * \author Tomoki Shirasawa  <tomoki.shirasawa.kk@hitachi-solutions.com> \par
 *      Copyright (C) 2012 - 2013 Hitachi, Ltd.
 */
/*
 * HISTORY:
 */

#ifndef __HEADER_X86_COMMON_CAS_H
#define __HEADER_X86_COMMON_CAS_H
// return 0:fail, 1:success
int compare_and_swap(void *addr, unsigned long olddata, unsigned long newdata);
#endif /*__HEADER_X86_COMMON_CAS_H*/
