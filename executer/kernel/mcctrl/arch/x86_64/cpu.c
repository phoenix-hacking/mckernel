/* This is copy of the necessary part from McKernel, for uti-futex */

#include <arch-lock.h>
#include <cpu.h>

/*@
  @ assigns \nothing;
  @ behavior to_enabled:
  @   assumes flags & RFLAGS_IF;
  @   ensures \interrupt_disabled == 0;
  @ behavior to_disabled:
  @   assumes !(flags & RFLAGS_IF);
  @   ensures \interrupt_disabled > 0;
  @*/
void cpu_restore_interrupt(unsigned long flags)
{
	asm volatile("push %0; popf" : : "g"(flags) : "memory", "cc");
}

void cpu_pause(void)
{
	asm volatile("pause" ::: "memory");
}

/*@
  @ assigns \nothing;
  @ ensures \interrupt_disabled > 0;
  @ behavior from_enabled:
  @   assumes \interrupt_disabled == 0;
  @   ensures \result & RFLAGS_IF;
  @ behavior from_disabled:
  @   assumes \interrupt_disabled > 0;
  @   ensures !(\result & RFLAGS_IF);
  @*/
unsigned long cpu_disable_interrupt_save(void)
{
	unsigned long flags;

	asm volatile("pushf; pop %0; cli" : "=r"(flags) : : "memory", "cc");

	return flags;
}

unsigned long cpu_enable_interrupt_save(void)
{
	unsigned long flags;

	asm volatile("pushf; pop %0; sti" : "=r"(flags) : : "memory", "cc");

	return flags;
}

#ifndef MCCTRL_RUST_HELPERS
void ihk_mc_spinlock_init(_ihk_spinlock_t *lock)
{
	lock->head_tail = 0;
}

void __ihk_mc_spinlock_lock_noirq(_ihk_spinlock_t *lock)
{
	register struct ihk__raw_tickets inc = { .tail = 0x0002 };

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
	barrier();  /* make sure nothing creeps before the lock is taken */
}

void __ihk_mc_spinlock_unlock_noirq(_ihk_spinlock_t *lock)
{
	__ticket_t inc = 0x0002;

	asm volatile ("lock addw %1, %0\n"
			: "+m" (lock->tickets.head)
			: "ri" (inc) : "memory", "cc");

	preempt_enable();
}

unsigned long __ihk_mc_spinlock_lock(_ihk_spinlock_t *lock)
{
	unsigned long flags;

	flags = cpu_disable_interrupt_save();

	__ihk_mc_spinlock_lock_noirq(lock);

	return flags;
}

void __ihk_mc_spinlock_unlock(_ihk_spinlock_t *lock, unsigned long flags)
{
	__ihk_mc_spinlock_unlock_noirq(lock);

	cpu_restore_interrupt(flags);
}

void mcs_rwlock_writer_lock_noirq(struct mcs_rwlock_lock *lock)
{
	ihk_mc_spinlock_lock_noirq(&lock->slock);
}

void mcs_rwlock_writer_unlock_noirq(struct mcs_rwlock_lock *lock)
{
	ihk_mc_spinlock_unlock_noirq(&lock->slock);
}
#endif
