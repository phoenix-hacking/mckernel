/**
 * \file lock.h
 *  License details are found in the file LICENSE.
 * \brief
 *  Declare functions implementing spin lock.
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 */
/*
 * HISTORY
 */

#ifndef __HEADER_GENERIC_IHK_LOCK
#define __HEADER_GENERIC_IHK_LOCK

#include <arch-lock.h>


/* Simple read/write spinlock implementation */
#define IHK_RWSPINLOCK_WRITELOCKED	(0xffU << 24)
typedef struct {
	ihk_atomic_t v;
} __attribute__((aligned(4))) ihk_rwspinlock_t;

void ihk_rwspinlock_init(ihk_rwspinlock_t *lock);
void __ihk_rwspinlock_read_lock(ihk_rwspinlock_t *lock);
int __ihk_rwspinlock_read_trylock(ihk_rwspinlock_t *lock);
void __ihk_rwspinlock_read_unlock(ihk_rwspinlock_t *lock);
void __ihk_rwspinlock_write_lock(ihk_rwspinlock_t *lock);
void __ihk_rwspinlock_write_unlock(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_read_lock_noirq(ihk_rwspinlock_t *lock);
int ihk_rwspinlock_read_trylock_noirq(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_write_lock_noirq(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_read_unlock_noirq(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_write_unlock_noirq(ihk_rwspinlock_t *lock);
unsigned long ihk_rwspinlock_read_lock(ihk_rwspinlock_t *lock);
unsigned long ihk_rwspinlock_write_lock(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_read_unlock(ihk_rwspinlock_t *lock,
	unsigned long irqstate);
void ihk_rwspinlock_write_unlock(ihk_rwspinlock_t *lock,
	unsigned long irqstate);



#ifndef ARCH_MCS_LOCK
/* An architecture independent implementation of the
 * Mellor-Crummey Scott (MCS) lock */

typedef struct mcs_lock_node {
#ifndef SPIN_LOCK_IN_MCS
	unsigned long locked;
	struct mcs_lock_node *next;
#endif
	unsigned long irqsave;
#ifdef SPIN_LOCK_IN_MCS
	ihk_spinlock_t spinlock;
#endif
#ifndef ENABLE_UBSAN
} __aligned(64) mcs_lock_node_t;
#else
} mcs_lock_node_t;
#endif

typedef mcs_lock_node_t mcs_lock_t;

void mcs_lock_init(struct mcs_lock_node *node);
void __mcs_lock_lock(struct mcs_lock_node *lock,
	struct mcs_lock_node *node);
void __mcs_lock_unlock(struct mcs_lock_node *lock,
	struct mcs_lock_node *node);
void mcs_lock_lock_noirq(struct mcs_lock_node *lock,
	struct mcs_lock_node *node);
void mcs_lock_unlock_noirq(struct mcs_lock_node *lock,
	struct mcs_lock_node *node);
void mcs_lock_lock(struct mcs_lock_node *lock,
	struct mcs_lock_node *node);
void mcs_lock_unlock(struct mcs_lock_node *lock,
	struct mcs_lock_node *node);
#endif // ARCH_MCS_LOCK



#ifndef IHK_STATIC_SPINLOCK_FUNCS
void ihk_mc_spinlock_init(ihk_spinlock_t *);
void ihk_mc_spinlock_lock(ihk_spinlock_t *, unsigned long *);
void ihk_mc_spinlock_unlock(ihk_spinlock_t *, unsigned long *);
#endif

void linux_spin_lock(void *lock);
void linux_spin_unlock(void *lock);
void linux_spin_lock_irqsave(void *lock, unsigned long *flags);
void linux_spin_unlock_irqrestore(void *lock, unsigned long flags);


#endif
