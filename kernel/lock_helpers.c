/**
 * \file lock_helpers.c
 * \brief C fallback implementations for generic IHK lock helpers.
 */

#include <types.h>
#include <lwk/stddef.h>
#include <ihk/lock.h>

#ifndef MCKERNEL_RUST_LOCK_HELPERS
void ihk_rwspinlock_init(ihk_rwspinlock_t *lock)
{
	ihk_atomic_set(&lock->v, 0);
}

void __ihk_rwspinlock_read_lock(ihk_rwspinlock_t *lock)
{
	int desired_old_val;
	int new_val;

	for (;;) {
		desired_old_val = ihk_atomic_read(&lock->v);
		desired_old_val &= ~(IHK_RWSPINLOCK_WRITELOCKED);
		new_val = desired_old_val + 1;

		if (likely((uint32_t)new_val < IHK_RWSPINLOCK_WRITELOCKED)) {
			if (likely(atomic_cmpxchg_int(&lock->v.counter,
						      desired_old_val,
						      new_val) ==
				   desired_old_val))
				return;
		}
	}
}

int __ihk_rwspinlock_read_trylock(ihk_rwspinlock_t *lock)
{
	int desired_old_val;
	int new_val;

	desired_old_val = ihk_atomic_read(&lock->v);
	desired_old_val &= ~(IHK_RWSPINLOCK_WRITELOCKED);
	new_val = desired_old_val + 1;

	if (likely((uint32_t)new_val < IHK_RWSPINLOCK_WRITELOCKED)) {
		if (likely(atomic_cmpxchg_int(&lock->v.counter,
					      desired_old_val, new_val) ==
			   desired_old_val))
			return 1;
	}

	return 0;
}

void __ihk_rwspinlock_read_unlock(ihk_rwspinlock_t *lock)
{
	ihk_atomic_dec((ihk_atomic_t *)&lock->v);
}

void __ihk_rwspinlock_write_lock(ihk_rwspinlock_t *lock)
{
	for (;;) {
		if (likely(atomic_cmpxchg_int(&lock->v.counter,
					      0, IHK_RWSPINLOCK_WRITELOCKED)
			   == 0))
			return;
		cpu_pause();
	}
}

void __ihk_rwspinlock_write_unlock(ihk_rwspinlock_t *lock)
{
	smp_store_release_int(&(lock->v.counter), 0);
}

void ihk_rwspinlock_read_lock_noirq(ihk_rwspinlock_t *lock)
{
	preempt_disable();
	__ihk_rwspinlock_read_lock(lock);
}

int ihk_rwspinlock_read_trylock_noirq(ihk_rwspinlock_t *lock)
{
	int rc;

	preempt_disable();
	rc = __ihk_rwspinlock_read_trylock(lock);
	if (!rc) {
		preempt_enable();
	}

	return rc;
}

void ihk_rwspinlock_write_lock_noirq(ihk_rwspinlock_t *lock)
{
	preempt_disable();
	__ihk_rwspinlock_write_lock(lock);
}

void ihk_rwspinlock_read_unlock_noirq(ihk_rwspinlock_t *lock)
{
	__ihk_rwspinlock_read_unlock(lock);
	preempt_enable();
}

void ihk_rwspinlock_write_unlock_noirq(ihk_rwspinlock_t *lock)
{
	__ihk_rwspinlock_write_unlock(lock);
	preempt_enable();
}

unsigned long ihk_rwspinlock_read_lock(ihk_rwspinlock_t *lock)
{
	unsigned long irqstate = cpu_disable_interrupt_save();

	ihk_rwspinlock_read_lock_noirq(lock);
	return irqstate;
}

unsigned long ihk_rwspinlock_write_lock(ihk_rwspinlock_t *lock)
{
	unsigned long irqstate = cpu_disable_interrupt_save();

	ihk_rwspinlock_write_lock_noirq(lock);
	return irqstate;
}

void ihk_rwspinlock_read_unlock(ihk_rwspinlock_t *lock,
	unsigned long irqstate)
{
	ihk_rwspinlock_read_unlock_noirq(lock);
	cpu_restore_interrupt(irqstate);
}

void ihk_rwspinlock_write_unlock(ihk_rwspinlock_t *lock,
	unsigned long irqstate)
{
	ihk_rwspinlock_write_unlock_noirq(lock);
	cpu_restore_interrupt(irqstate);
}

void linux_spin_lock(void *lock)
{
	unsigned int *lock_word = (unsigned int *)lock;

	while (!__sync_bool_compare_and_swap(lock_word, 0, 1U)) {
		cpu_pause();
	}
}

void linux_spin_unlock(void *lock)
{
	smp_store_release_uint((unsigned int *)lock, 0);
}

void linux_spin_lock_irqsave(void *lock, unsigned long *flags)
{
	*flags = cpu_disable_interrupt_save();
	linux_spin_lock(lock);
}

void linux_spin_unlock_irqrestore(void *lock, unsigned long flags)
{
	linux_spin_unlock(lock);
	cpu_restore_interrupt(flags);
}

#ifndef ARCH_MCS_LOCK
void mcs_lock_init(struct mcs_lock_node *node)
{
#ifdef SPIN_LOCK_IN_MCS
	ihk_mc_spinlock_init(&node->spinlock);
#else
	node->locked = 0;
	node->next = NULL;
#endif
}

void __mcs_lock_lock(struct mcs_lock_node *lock,
	struct mcs_lock_node *node)
{
#ifdef SPIN_LOCK_IN_MCS
	ihk_mc_spinlock_lock_noirq(&lock->spinlock);
#else
	struct mcs_lock_node *pred;

	node->next = NULL;
	node->locked = 0;

	pred = atomic_xchg_ptr((void **)&lock->next, node);
	if (likely(pred == NULL)) {
		return;
	}
	WRITE_ONCE(pred->next, node);

	while (!(smp_load_acquire_ulong(&node->locked)))
		cpu_pause();
#endif
}

void __mcs_lock_unlock(struct mcs_lock_node *lock,
	struct mcs_lock_node *node)
{
#ifdef SPIN_LOCK_IN_MCS
	ihk_mc_spinlock_unlock_noirq(&lock->spinlock);
#else
	struct mcs_lock_node *next = READ_ONCE(node->next);

	if (likely(!next)) {
		if (likely(atomic_cmpxchg_ptr((void **)&lock->next,
					      node, NULL) == node))
			return;

		while (!(next = READ_ONCE(node->next)))
			cpu_pause();
	}

	smp_store_release_ulong((&next->locked), 1);
#endif
}

void mcs_lock_lock_noirq(struct mcs_lock_node *lock,
	struct mcs_lock_node *node)
{
	preempt_disable();
	__mcs_lock_lock(lock, node);
}

void mcs_lock_unlock_noirq(struct mcs_lock_node *lock,
	struct mcs_lock_node *node)
{
	__mcs_lock_unlock(lock, node);
	preempt_enable();
}

void mcs_lock_lock(struct mcs_lock_node *lock,
	struct mcs_lock_node *node)
{
	node->irqsave = cpu_disable_interrupt_save();
	mcs_lock_lock_noirq(lock, node);
}

void mcs_lock_unlock(struct mcs_lock_node *lock,
	struct mcs_lock_node *node)
{
	mcs_lock_unlock_noirq(lock, node);
	cpu_restore_interrupt(node->irqsave);
}
#endif /* ARCH_MCS_LOCK */
#endif /* MCKERNEL_RUST_LOCK_HELPERS */
