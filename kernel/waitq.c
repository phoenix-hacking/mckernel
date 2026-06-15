/**
 * \file waitq.c
 * Licence details are found in the file LICENSE.
 *  
 * \brief
 * Waitqueue adaptation from Sandia's Kitten OS 
 * (originally taken from Linux)
 *
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 * Copyright (C) 2012  RIKEN AICS
 *
 */

#include <waitq.h>
#include <process.h>
#include <cls.h>

#ifdef MCKERNEL_RUST_WAITQ_CORE
extern void waitq_init(waitq_t *waitq);
extern void waitq_init_entry(waitq_entry_t *entry, struct thread *proc);
extern void waitq_init_locked_entry(waitq_entry_t *entry, struct thread *proc);
extern void waitq_add_entry_locked(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_remove_entry_locked(waitq_t *waitq, waitq_entry_t *entry);
extern int waitq_wake_nr_locked(waitq_t *waitq, int nr);
extern int waitq_wake_schedule_needed_result(int count);
extern int waitq_active_result(waitq_t *waitq);
extern void waitq_add_entry_result(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_remove_entry_result(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_prepare_to_wait_result(waitq_t *waitq,
		waitq_entry_t *entry, int state, struct thread *current,
		unsigned long status_offset);
extern void waitq_finish_wait_result(waitq_t *waitq, waitq_entry_t *entry,
		struct thread *current, unsigned long status_offset,
		int running_state);
extern void waitq_wakeup_result(waitq_t *waitq);
extern int waitq_wake_nr_result(waitq_t *waitq, int nr,
		void (*schedule_fn)(void));
#endif

int
default_wake_function(waitq_entry_t *entry, unsigned mode,
					  int flags, void *key)
{
	return sched_wakeup_thread(entry->private, PS_NORMAL);
}

int
locked_wake_function(waitq_entry_t *entry, unsigned mode,
					  int flags, void *key)
{
	return sched_wakeup_thread_locked(entry->private, PS_NORMAL);
}

#ifdef MCKERNEL_RUST_WAITQ_CORE
/* Rust-owned core waitq list helpers. */
#else
void
waitq_init(waitq_t *waitq)
{
	ihk_mc_spinlock_init(&waitq->lock);
	INIT_LIST_HEAD(&waitq->waitq);
}
#endif

#ifndef MCKERNEL_RUST_WAITQ_CORE
void
waitq_init_entry(waitq_entry_t *entry, struct thread *proc)
{
	entry->private = proc;
	entry->flags = 0;
	entry->func = default_wake_function;
	INIT_LIST_HEAD(&entry->link);
}

void
waitq_init_locked_entry(waitq_entry_t *entry, struct thread *proc)
{
	entry->private = proc;
	entry->flags = 0;
	entry->func = locked_wake_function;
	INIT_LIST_HEAD(&entry->link);
}

int
waitq_wake_schedule_needed_result(int count)
{
	return count > 0;
}
#endif

#ifndef MCKERNEL_RUST_WAITQ_CORE
int
waitq_active_result(waitq_t *waitq)
{
	int active;

	ihk_mc_spinlock_lock_noirq(&waitq->lock);
	active = !list_empty(&waitq->waitq);
	ihk_mc_spinlock_unlock_noirq(&waitq->lock);

	return active;
}
#endif

int
waitq_active(waitq_t *waitq)
{
	return waitq_active_result(waitq);
}

#ifndef MCKERNEL_RUST_WAITQ_CORE
void
waitq_add_entry_result(waitq_t *waitq, waitq_entry_t *entry)
{
	ihk_mc_spinlock_lock_noirq(&waitq->lock);
	waitq_add_entry_locked(waitq, entry);
	ihk_mc_spinlock_unlock_noirq(&waitq->lock);
}
#endif

void
waitq_add_entry(waitq_t *waitq, waitq_entry_t *entry)
{
	waitq_add_entry_result(waitq, entry);
}

#ifndef MCKERNEL_RUST_WAITQ_CORE
void
waitq_add_entry_locked(waitq_t *waitq, waitq_entry_t *entry)
{
	//BUG_ON(!list_empty(&entry->link));
	list_add_tail(&entry->link, &waitq->waitq);
}
#endif


#ifndef MCKERNEL_RUST_WAITQ_CORE
void
waitq_remove_entry_result(waitq_t *waitq, waitq_entry_t *entry)
{
	ihk_mc_spinlock_lock_noirq(&waitq->lock);
	waitq_remove_entry_locked(waitq, entry);
	ihk_mc_spinlock_unlock_noirq(&waitq->lock);
}
#endif

void
waitq_remove_entry(waitq_t *waitq, waitq_entry_t *entry)
{
	waitq_remove_entry_result(waitq, entry);
}

#ifndef MCKERNEL_RUST_WAITQ_CORE
void
waitq_remove_entry_locked(waitq_t *waitq, waitq_entry_t *entry)
{
	//BUG_ON(list_empty(&entry->link));
	list_del_init(&entry->link);
}
#endif


#ifndef MCKERNEL_RUST_WAITQ_CORE
void
waitq_prepare_to_wait_result(waitq_t *waitq, waitq_entry_t *entry, int state,
		struct thread *current, unsigned long status_offset)
{
	ihk_mc_spinlock_lock_noirq(&waitq->lock);
	if (list_empty(&entry->link))
		list_add(&entry->link, &waitq->waitq);
	*(int *)((char *)current + status_offset) = state;
	ihk_mc_spinlock_unlock_noirq(&waitq->lock);
}
#endif

void
waitq_prepare_to_wait(waitq_t *waitq, waitq_entry_t *entry, int state)
{
	waitq_prepare_to_wait_result(waitq, entry, state,
			get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, status));
}

#ifndef MCKERNEL_RUST_WAITQ_CORE
void
waitq_finish_wait_result(waitq_t *waitq, waitq_entry_t *entry,
		struct thread *current, unsigned long status_offset,
		int running_state)
{
	*(int *)((char *)current + status_offset) = running_state;
	waitq_remove_entry_result(waitq, entry);
}
#endif

void
waitq_finish_wait(waitq_t *waitq, waitq_entry_t *entry)
{
	waitq_finish_wait_result(waitq, entry, get_this_cpu_local_var()->current,
			__builtin_offsetof(struct thread, status), PS_RUNNING);
}

#ifndef MCKERNEL_RUST_WAITQ_CORE
void
waitq_wakeup_result(waitq_t *waitq)
{
	struct list_head *tmp;
	waitq_entry_t *entry;
	
	ihk_mc_spinlock_lock_noirq(&waitq->lock);
	for (tmp = (&waitq->waitq)->next; tmp != (&waitq->waitq); tmp = tmp->next) {
		entry = ((waitq_entry_t *)((char *)(tmp) - offsetof(waitq_entry_t, link)));
		entry->func(entry, 0, 0, NULL);
	}
	ihk_mc_spinlock_unlock_noirq(&waitq->lock);
}
#endif

void
waitq_wakeup(waitq_t *waitq)
{
	waitq_wakeup_result(waitq);
}

#ifndef MCKERNEL_RUST_WAITQ_CORE
int
waitq_wake_nr_result(waitq_t * waitq, int nr, void (*schedule_fn)(void))
{
	ihk_mc_spinlock_lock_noirq(&waitq->lock);
	int count = waitq_wake_nr_locked(waitq, nr);
	ihk_mc_spinlock_unlock_noirq(&waitq->lock);

	if (waitq_wake_schedule_needed_result(count) && schedule_fn)
		schedule_fn();
	
	return count;
}
#endif

int
waitq_wake_nr(waitq_t * waitq, int nr)
{
	return waitq_wake_nr_result(waitq, nr, schedule);
}

#ifndef MCKERNEL_RUST_WAITQ_CORE
int
waitq_wake_nr_locked( waitq_t * waitq, int nr )
{
	int count = 0;
	waitq_entry_t *entry;

	for (entry = ((typeof(*entry) *)((char *)((&waitq->waitq)->next) - offsetof(typeof(*entry), link))); &entry->link != (&waitq->waitq); entry = ((typeof(*entry) *)((char *)(entry->link.next) - offsetof(typeof(*entry), link)))) {
		if (++count > nr)
			break;
		
		entry->func(entry, 0, 0, NULL);
	}

	return count - 1;
}
#endif
