/**
 * \file cpu.h
 *  License details are found in the file LICENSE.
 * \brief
 *  Declare architecture-dependent types and functions to control CPU.
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com>
 *      Copyright (C) 2015  RIKEN AICS
 */
/*
 * HISTORY
 */

#ifndef ARCH_CPU_H
#define ARCH_CPU_H

void mb(void);
void rmb(void);
void wmb(void);
void smp_mb(void);
void smp_rmb(void);
void smp_wmb(void);
void arch_barrier(void);

unsigned long read_tsc(void);
unsigned long smp_load_acquire_ulong(const unsigned long *p);
unsigned int smp_load_acquire_uint(const unsigned int *p);
int smp_load_acquire_int(const int *p);
void *smp_load_acquire_ptr(void *const *p);
void smp_store_release_ulong(unsigned long *p, unsigned long v);
void smp_store_release_uint(unsigned int *p, unsigned int v);
void smp_store_release_int(int *p, int v);

void arch_flush_icache_all(void);

#endif /* ARCH_CPU_H */
