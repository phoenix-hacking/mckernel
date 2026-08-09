/* This is copy of the necessary part from McKernel, for uti-futex */

#ifndef __HEADER_X86_COMMON_ARCH_LOCK
#define __HEADER_X86_COMMON_ARCH_LOCK

#include <linux/preempt.h>
#include <cpu.h>

#define ihk_mc_spinlock_lock __ihk_mc_spinlock_lock
#define ihk_mc_spinlock_unlock __ihk_mc_spinlock_unlock

#define ihk_mc_spinlock_lock_noirq __ihk_mc_spinlock_lock_noirq
#define ihk_mc_spinlock_unlock_noirq __ihk_mc_spinlock_unlock_noirq

typedef unsigned short __ticket_t;
typedef unsigned int __ticketpair_t;

/* arch/x86/include/asm/spinlock_types.h defines struct __raw_tickets */
typedef struct ihk_spinlock {
	union {
		__ticketpair_t head_tail;
		struct ihk__raw_tickets {
			__ticket_t head, tail;
		} tickets;
	};
} _ihk_spinlock_t;

void ihk_mc_spinlock_init(_ihk_spinlock_t *lock);
void __ihk_mc_spinlock_lock_noirq(_ihk_spinlock_t *lock);
void __ihk_mc_spinlock_unlock_noirq(_ihk_spinlock_t *lock);
unsigned long __ihk_mc_spinlock_lock(_ihk_spinlock_t *lock);
void __ihk_mc_spinlock_unlock(_ihk_spinlock_t *lock, unsigned long flags);

typedef struct mcs_rwlock_lock {
	_ihk_spinlock_t slock;

#ifndef ENABLE_UBSAN
} __aligned(64) mcs_rwlock_lock_t;
#else
} mcs_rwlock_lock_t;
#endif

void mcs_rwlock_writer_lock_noirq(struct mcs_rwlock_lock *lock);
void mcs_rwlock_writer_unlock_noirq(struct mcs_rwlock_lock *lock);

#endif
