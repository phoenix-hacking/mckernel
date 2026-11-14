/*
 * Excerpted from Linux 3.0: arch/x86/include/asm/spinlock.h
 */
#ifndef __HEADER_X86_COMMON_ARCH_LOCK
#define __HEADER_X86_COMMON_ARCH_LOCK

#include <ihk/cpu.h>
#include <ihk/atomic.h>
#include <lwk/compiler.h>
#include "config.h"

//#define DEBUG_SPINLOCK
//#define DEBUG_MCS_RWLOCK

#if defined(DEBUG_SPINLOCK) || defined(DEBUG_MCS_RWLOCK)
int __kprintf(const char *format, ...);
#endif

typedef unsigned short __ticket_t;
typedef unsigned int __ticketpair_t;

typedef struct ihk_spinlock {
	union {
		__ticketpair_t head_tail;
		struct __raw_tickets {
			__ticket_t head, tail;
		} tickets;
	};
} ihk_spinlock_t;

extern void preempt_enable(void);
extern void preempt_disable(void);

#define IHK_STATIC_SPINLOCK_FUNCS

#define SPIN_LOCK_UNLOCKED { .head_tail = 0 }

void ihk_mc_spinlock_init(ihk_spinlock_t *lock);
int __ihk_mc_spinlock_trylock_noirq(ihk_spinlock_t *lock);
unsigned long __ihk_mc_spinlock_trylock(ihk_spinlock_t *lock, int *result);
void __ihk_mc_spinlock_lock_noirq(ihk_spinlock_t *lock);
unsigned long __ihk_mc_spinlock_lock(ihk_spinlock_t *lock);
void __ihk_mc_spinlock_unlock_noirq(ihk_spinlock_t *lock);
void __ihk_mc_spinlock_unlock(ihk_spinlock_t *lock, unsigned long flags);
#define ihk_mc_spinlock_trylock_noirq __ihk_mc_spinlock_trylock_noirq
#define ihk_mc_spinlock_trylock __ihk_mc_spinlock_trylock
#define ihk_mc_spinlock_lock_noirq __ihk_mc_spinlock_lock_noirq
#define ihk_mc_spinlock_lock __ihk_mc_spinlock_lock
#define ihk_mc_spinlock_unlock_noirq __ihk_mc_spinlock_unlock_noirq
#define ihk_mc_spinlock_unlock __ihk_mc_spinlock_unlock

#define SPINLOCK_IN_MCS_RWLOCK

// reader/writer lock
typedef struct mcs_rwlock_node {
	ihk_atomic_t count;	// num of readers (use only common reader)
	char type;		// lock type
#define MCS_RWLOCK_TYPE_COMMON_READER 0
#define MCS_RWLOCK_TYPE_READER 1
#define MCS_RWLOCK_TYPE_WRITER 2
	char locked;		// lock
#define MCS_RWLOCK_LOCKED	1
#define MCS_RWLOCK_UNLOCKED	0
	char dmy1;		// unused
	char dmy2;		// unused
	struct mcs_rwlock_node *next;
#ifndef ENABLE_UBSAN
} __aligned(64) mcs_rwlock_node_t;
#else
} mcs_rwlock_node_t;
#endif

typedef struct mcs_rwlock_node_irqsave {
#ifndef SPINLOCK_IN_MCS_RWLOCK
	struct mcs_rwlock_node node;
#endif
	unsigned long irqsave;
#ifndef ENABLE_UBSAN
} __aligned(64) mcs_rwlock_node_irqsave_t;
#else
} mcs_rwlock_node_irqsave_t;
#endif

typedef struct mcs_rwlock_lock {
#ifdef SPINLOCK_IN_MCS_RWLOCK
	ihk_spinlock_t slock;
#else
	struct mcs_rwlock_node reader;		/* common reader lock */
	struct mcs_rwlock_node *node;		/* base */
#endif
#ifndef ENABLE_UBSAN
} __aligned(64) mcs_rwlock_lock_t;
#else
} mcs_rwlock_lock_t;
#endif

void mcs_rwlock_init(struct mcs_rwlock_lock *lock);
void __mcs_rwlock_writer_lock_noirq(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node *node);
void __mcs_rwlock_writer_unlock_noirq(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node *node);
void __mcs_rwlock_reader_lock_noirq(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node *node);
void __mcs_rwlock_reader_unlock_noirq(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node *node);
void __mcs_rwlock_writer_lock(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node_irqsave *node);
void __mcs_rwlock_writer_unlock(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node_irqsave *node);
void __mcs_rwlock_reader_lock(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node_irqsave *node);
void __mcs_rwlock_reader_unlock(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node_irqsave *node);
#define mcs_rwlock_writer_lock_noirq __mcs_rwlock_writer_lock_noirq
#define mcs_rwlock_writer_unlock_noirq __mcs_rwlock_writer_unlock_noirq
#define mcs_rwlock_reader_lock_noirq __mcs_rwlock_reader_lock_noirq
#define mcs_rwlock_reader_unlock_noirq __mcs_rwlock_reader_unlock_noirq
#define mcs_rwlock_writer_lock __mcs_rwlock_writer_lock
#define mcs_rwlock_writer_unlock __mcs_rwlock_writer_unlock
#define mcs_rwlock_reader_lock __mcs_rwlock_reader_lock
#define mcs_rwlock_reader_unlock __mcs_rwlock_reader_unlock

int irqflags_can_interrupt(unsigned long flags);

struct ihk_rwlock {
	union {
		long lock;
		struct {
			unsigned int read;
			int write;
		};
	} lock;
};

void ihk_mc_rwlock_init(struct ihk_rwlock *rw);
void ihk_mc_read_lock(struct ihk_rwlock *rw);
void ihk_mc_write_lock(struct ihk_rwlock *rw);
int ihk_mc_read_trylock(struct ihk_rwlock *rw);
int ihk_mc_write_trylock(struct ihk_rwlock *rw);
void ihk_mc_read_unlock(struct ihk_rwlock *rw);
void ihk_mc_write_unlock(struct ihk_rwlock *rw);
int ihk_mc_write_can_lock(struct ihk_rwlock *rw);
int ihk_mc_read_can_lock(struct ihk_rwlock *rw);
#endif
