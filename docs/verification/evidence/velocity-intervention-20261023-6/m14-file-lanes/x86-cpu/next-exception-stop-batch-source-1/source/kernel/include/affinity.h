/**
 * \file affinity.h
 *  License details are found in the file LICENSE.
 * \brief
 *  Macros used to set and get CPU affinity
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 * Copyright (C) 2011 - 2012  Taku Shimosawa
 */
/*
 * HISTORY:
 */

/* 
 * Adapted from Linux sched.h 
 *
 * Modified to omit __GNUC_PREREQ checks and use 
 * the naive implementations.
 *
 */

#if !defined __cpu_set_t_defined
# define __cpu_set_t_defined
/* Size definition for CPU sets.  */
# define __CPU_SETSIZE	1024
# define __NCPUBITS	(8 * sizeof (__cpu_mask))

/* Type for array elements in 'cpu_set_t'.  */
typedef unsigned long int __cpu_mask;

/* Data structure to describe CPU mask.  */
typedef struct
{
  __cpu_mask __bits[__CPU_SETSIZE / __NCPUBITS];
} cpu_set_t;

#if 0
__BEGIN_DECLS

extern int __sched_cpucount (size_t __setsize, const cpu_set_t *__setp)
  __THROW;
extern cpu_set_t *__sched_cpualloc (size_t __count) __THROW __wur;
extern void __sched_cpufree (cpu_set_t *__set) __THROW;

__END_DECLS
#endif

#endif

/* Access macros for `cpu_set'.  */
# define CPU_SETSIZE __CPU_SETSIZE
unsigned long CPU_SET(unsigned long cpu, cpu_set_t *cpusetp);
int CPU_ISSET(unsigned long cpu, const cpu_set_t *cpusetp);
void CPU_ZERO(cpu_set_t *cpusetp);
unsigned long CPU_SET_S(unsigned long cpu, unsigned long setsize,
			cpu_set_t *cpusetp);
int CPU_ISSET_S(unsigned long cpu, unsigned long setsize,
		const cpu_set_t *cpusetp);
void CPU_ZERO_S(unsigned long setsize, cpu_set_t *cpusetp);

#if 0
/* Set the CPU affinity for a task */
extern int sched_setaffinity (__pid_t __pid, size_t __cpusetsize,
			      __const cpu_set_t *__cpuset) __THROW;

/* Get the CPU affinity for a task */
extern int sched_getaffinity (__pid_t __pid, size_t __cpusetsize,
			      cpu_set_t *__cpuset) __THROW;
#endif
