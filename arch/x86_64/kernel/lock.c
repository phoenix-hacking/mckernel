/**
 * \file lock.c
 *  License details are found in the file LICENSE.
 * \brief
 *  Spin lock.
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 *      Copyright (C) 2011 - 2012  Taku Shimosawa
 */
/*
 * HISTORY
 */

#include <ihk/lock.h>

#ifndef MCKERNEL_RUST_SPINLOCK_HELPERS
void ihk_mc_spinlock_init(ihk_spinlock_t *lock)
{
	lock->head_tail = 0;
}

int __ihk_mc_spinlock_trylock_noirq(ihk_spinlock_t *lock)
{
	ihk_spinlock_t cur = { .head_tail = lock->head_tail };
	ihk_spinlock_t next = { .tickets = {
		.head = cur.tickets.head,
		.tail = cur.tickets.tail + 2
	} };
	int success;

	if (cur.tickets.head != cur.tickets.tail) {
		return 0;
	}

	preempt_disable();

	success = __sync_bool_compare_and_swap((__ticketpair_t *)lock,
		cur.head_tail, next.head_tail);

	if (!success) {
		preempt_enable();
	}
	return success;
}

unsigned long __ihk_mc_spinlock_trylock(ihk_spinlock_t *lock, int *result)
{
	unsigned long flags = cpu_disable_interrupt_save();

	*result = __ihk_mc_spinlock_trylock_noirq(lock);
	return flags;
}

void __ihk_mc_spinlock_lock_noirq(ihk_spinlock_t *lock)
{
	register struct __raw_tickets inc = { .tail = 0x0002 };

	preempt_disable();

	asm volatile ("lock xaddl %0, %1\n"
			: "+r" (inc), "+m" (*(lock)) : : "memory", "cc");

	if (inc.head == inc.tail)
		goto out;

	for (;;) {
		if (*((volatile __ticket_t *)&lock->tickets.head) == inc.tail)
			goto out;
		cpu_pause();
	}

out:
	barrier();
}

unsigned long __ihk_mc_spinlock_lock(ihk_spinlock_t *lock)
{
	unsigned long flags = cpu_disable_interrupt_save();

	__ihk_mc_spinlock_lock_noirq(lock);
	return flags;
}

void __ihk_mc_spinlock_unlock_noirq(ihk_spinlock_t *lock)
{
	__ticket_t inc = 0x0002;

	asm volatile ("lock addw %1, %0\n"
			: "+m" (lock->tickets.head) : "ri" (inc) : "memory", "cc");

	preempt_enable();
}

void __ihk_mc_spinlock_unlock(ihk_spinlock_t *lock, unsigned long flags)
{
	__ihk_mc_spinlock_unlock_noirq(lock);
	cpu_restore_interrupt(flags);
}
#endif /* MCKERNEL_RUST_SPINLOCK_HELPERS */

#ifndef MCKERNEL_RUST_MCS_RWLOCK_HELPERS
void mcs_rwlock_init(struct mcs_rwlock_lock *lock)
{
	ihk_mc_spinlock_init(&lock->slock);
}

void __mcs_rwlock_writer_lock_noirq(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node *node)
{
	(void)node;
	ihk_mc_spinlock_lock_noirq(&lock->slock);
}

void __mcs_rwlock_writer_unlock_noirq(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node *node)
{
	(void)node;
	ihk_mc_spinlock_unlock_noirq(&lock->slock);
}

void __mcs_rwlock_reader_lock_noirq(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node *node)
{
	(void)node;
	ihk_mc_spinlock_lock_noirq(&lock->slock);
}

void __mcs_rwlock_reader_unlock_noirq(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node *node)
{
	(void)node;
	ihk_mc_spinlock_unlock_noirq(&lock->slock);
}

void __mcs_rwlock_writer_lock(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node_irqsave *node)
{
	node->irqsave = ihk_mc_spinlock_lock(&lock->slock);
}

void __mcs_rwlock_writer_unlock(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node_irqsave *node)
{
	ihk_mc_spinlock_unlock(&lock->slock, node->irqsave);
}

void __mcs_rwlock_reader_lock(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node_irqsave *node)
{
	node->irqsave = ihk_mc_spinlock_lock(&lock->slock);
}

void __mcs_rwlock_reader_unlock(struct mcs_rwlock_lock *lock,
	struct mcs_rwlock_node_irqsave *node)
{
	ihk_mc_spinlock_unlock(&lock->slock, node->irqsave);
}
#endif /* MCKERNEL_RUST_MCS_RWLOCK_HELPERS */

int irqflags_can_interrupt(unsigned long flags)
{
	return !!(flags & 0x200);
}

#ifndef MCKERNEL_RUST_MC_RWLOCK_HELPERS
void ihk_mc_rwlock_init(struct ihk_rwlock *rw)
{
	rw->lock.read = 0;
	rw->lock.write = 1;
}

void ihk_mc_read_lock(struct ihk_rwlock *rw)
{
	asm volatile("1:\t"
		     "lock; decq %0\n\t"
		     "jns 3f\n\t"
		     "lock incq %0\n\t"
		     "2:\t"
		     "pause\n\t"
		     "cmpq $0x1, %0\n\t"
		     "jns 1b\n\t"
		     "jmp 2b\n\t"
		     "3:"
		     : "+m" (rw->lock.lock) : : "memory");
}

void ihk_mc_write_lock(struct ihk_rwlock *rw)
{
	asm volatile("1:\t"
		     "lock; decl %0\n\t"
		     "je 3f\n\t"
		     "lock; incl %0\n\t"
		     "2:\t"
		     "pause\n\t"
		     "cmpl $0x1,%0\n\t"
		     "je 1b\n\t"
		     "jmp 2b\n\t"
		     "3:"
		     : "+m" (rw->lock.write) : "i" (((1L) << 32)) : "memory");
}

int ihk_mc_read_trylock(struct ihk_rwlock *rw)
{
	ihk_atomic64_t *count = (ihk_atomic64_t *)rw;

	if (ihk_atomic64_sub_return(1, count) >= 0)
		return 1;
	ihk_atomic64_inc(count);
	return 0;
}

int ihk_mc_write_trylock(struct ihk_rwlock *rw)
{
	ihk_atomic_t *count = (ihk_atomic_t *)&rw->lock.write;

	if (ihk_atomic_dec_and_test(count))
		return 1;
	ihk_atomic_inc(count);
	return 0;
}

void ihk_mc_read_unlock(struct ihk_rwlock *rw)
{
	asm volatile("lock; incq %0" : "+m" (rw->lock.lock) : : "memory");
}

void ihk_mc_write_unlock(struct ihk_rwlock *rw)
{
	asm volatile("lock; incl %0"
		     : "+m" (rw->lock.write) : "i" (((1L) << 32)) : "memory");
}

int ihk_mc_write_can_lock(struct ihk_rwlock *rw)
{
	return rw->lock.write == 1;
}

int ihk_mc_read_can_lock(struct ihk_rwlock *rw)
{
	return rw->lock.lock > 0;
}
#endif /* MCKERNEL_RUST_MC_RWLOCK_HELPERS */
