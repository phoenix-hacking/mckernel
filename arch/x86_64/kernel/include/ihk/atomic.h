/**
 * \file atomic.h
 *  License details are found in the file LICENSE.
 * \brief
 *  Atomic memory operations.
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 */
/*
 * HISTORY
 */

#ifndef HEADER_X86_COMMON_IHK_ATOMIC_H
#define HEADER_X86_COMMON_IHK_ATOMIC_H
 
#include <lwk/compiler.h>

/***********************************************************************
 * ihk_atomic_t
 */

typedef struct {
	int counter;
} ihk_atomic_t;

int ihk_atomic_inc_return(ihk_atomic_t *v);
int ihk_atomic_dec_return(ihk_atomic_t *v);
int ihk_atomic_read(const ihk_atomic_t *v);
void ihk_atomic_set(ihk_atomic_t *v, int i);
void ihk_atomic_add(int i, ihk_atomic_t *v);
void ihk_atomic_sub(int i, ihk_atomic_t *v);
void ihk_atomic_inc(ihk_atomic_t *v);
void ihk_atomic_dec(ihk_atomic_t *v);
int ihk_atomic_dec_and_test(ihk_atomic_t *v);
int ihk_atomic_inc_and_test(ihk_atomic_t *v);
int ihk_atomic_add_return(int i, ihk_atomic_t *v);
int ihk_atomic_sub_return(int i, ihk_atomic_t *v);

/***********************************************************************
 * ihk_atomic64_t
 */

typedef struct {
	long counter64;
} ihk_atomic64_t;

long ihk_atomic64_read(const ihk_atomic64_t *v);
void ihk_atomic64_set(ihk_atomic64_t *v, long i);
void ihk_atomic64_inc(ihk_atomic64_t *v);
long ihk_atomic64_add_return(long i, ihk_atomic64_t *v);
long ihk_atomic64_sub_return(long i, ihk_atomic64_t *v);

/***********************************************************************
 * others
 */

unsigned long xchg8(unsigned long *ptr, unsigned long x);
int xchg4(int *ptr, int x);
unsigned long atomic_xchg_ulong(unsigned long *ptr, unsigned long x);
void *atomic_xchg_ptr(void **ptr, void *x);

unsigned long atomic_cmpxchg8(unsigned long *addr,
		unsigned long oldval, unsigned long newval);
unsigned long atomic_cmpxchg4(unsigned int *addr,
		unsigned int oldval, unsigned int newval);
int atomic_cmpxchg_int(int *addr, int oldval, int newval);
unsigned long atomic_cmpxchg_ulong(unsigned long *addr,
		unsigned long oldval, unsigned long newval);
void *atomic_cmpxchg_ptr(void **addr, void *oldval, void *newval);
void ihk_atomic_add_long(long i, long *v);
void ihk_atomic_add_ulong(long i, unsigned long *v);
unsigned long ihk_atomic_add_long_return(long i, long *v);

#endif
