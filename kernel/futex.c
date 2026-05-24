/**
 * \file futex.c
 * Licence details are found in the file LICENSE.
 *  
 * \brief
 * Futex adaptation to McKernel
 *
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 * Copyright (C) 2012  RIKEN AICS
 *
 *
 * HISTORY:
 *
 */

/*
 *  Fast Userspace Mutexes (which I call "Futexes!").
 *  (C) Rusty Russell, IBM 2002
 *
 *  Generalized futexes, futex requeueing, misc fixes by Ingo Molnar
 *  (C) Copyright 2003 Red Hat Inc, All Rights Reserved
 *
 *  Removed page pinning, fix privately mapped COW pages and other cleanups
 *  (C) Copyright 2003, 2004 Jamie Lokier
 *
 *  Robust futex support started by Ingo Molnar
 *  (C) Copyright 2006 Red Hat Inc, All Rights Reserved
 *  Thanks to Thomas Gleixner for suggestions, analysis and fixes.
 *
 *  PI-futex support started by Ingo Molnar and Thomas Gleixner
 *  Copyright (C) 2006 Red Hat, Inc., Ingo Molnar <mingo@redhat.com>
 *  Copyright (C) 2006 Timesys Corp., Thomas Gleixner <tglx@timesys.com>
 *
 *  PRIVATE futexes by Eric Dumazet
 *  Copyright (C) 2007 Eric Dumazet <dada1@cosmosbay.com>
 *
 *  Requeue-PI support by Darren Hart <dvhltc@us.ibm.com>
 *  Copyright (C) IBM Corporation, 2009
 *  Thanks to Thomas Gleixner for conceptual design and careful reviews.
 *
 *  Thanks to Ben LaHaise for yelling "hashed waitqueues" loudly
 *  enough at me, Linus for the original (flawed) idea, Matthew
 *  Kirkwood for proof-of-concept implementation.
 *
 *  "The futexes are also cursed."
 *  "But they come in a choice of three flavours!"
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */

#include <process.h>
#include <futex.h>
#include <mc_jhash.h>
#include <ihk/lock.h>
#include <ihk/atomic.h>
#include <list.h>
#include <plist.h>
#include <cls.h>
#include <kmsg.h>
#include <timer.h>
#include <ihk/debug.h>
#include <syscall.h>
#include <kmalloc.h>
#include <ikc/queue.h>
#include <sched_helpers.h>


unsigned long ihk_mc_get_ns_per_tsc(void);

struct futex_hash_bucket *futex_queues;

extern struct ihk_ikc_channel_desc **ikc2linuxs;

struct futex_hash_bucket *get_futex_queues(void)
{
	return futex_queues;
}

static unsigned long futex_kmalloc_bridge(unsigned long size, int flag)
{
	return (unsigned long)kmalloc(size, flag);
}

static unsigned int futex_key_hash_bridge(unsigned long key_addr)
{
	union futex_key *key = (union futex_key *)key_addr;

	return mc_jhash2((uint32_t *)&key->both.word,
			(sizeof(key->both.word) + sizeof(key->both.ptr)) / 4,
			key->both.offset);
}

/*
 * We hash on the keys returned from get_futex_key (see below).
 */
static struct futex_hash_bucket *hash_futex(union futex_key *key)
{
	return (struct futex_hash_bucket *)futex_hash_bucket_result(
			(unsigned long)key, (unsigned long)futex_queues,
			FUTEX_HASHBITS, sizeof(struct futex_hash_bucket),
			futex_key_hash_bridge);
}

/*
 * Return 1 if two futex_keys are equal, 0 otherwise.
 */
static inline int match_futex(union futex_key *key1, union futex_key *key2)
{
	return futex_key_match_result(key1 != NULL, key2 != NULL,
		key1 ? key1->both.word : 0,
		key1 ? (unsigned long)key1->both.ptr : 0,
		key1 ? key1->both.offset : 0,
		key2 ? key2->both.word : 0,
		key2 ? (unsigned long)key2->both.ptr : 0,
		key2 ? key2->both.offset : 0);
}

/*
 * Take a reference to the resource addressed by a key.
 * Can be called while holding spinlocks.
 *
 */
static void get_futex_key_refs(union futex_key *key)
{
	/* RIKEN: no swapping in McKernel */
	return;
}

/*
 * Drop a reference to the resource addressed by a key.
 * The hash bucket spinlock must not be held.
 */
static void drop_futex_key_refs(union futex_key *key)
{
	/* RIKEN: no swapping in McKernel */
	return;
}
/**
 * get_futex_key() - Get parameters which are the keys for a futex
 * @uaddr:	virtual address of the futex
 * @fshared:	0 for a PROCESS_PRIVATE futex, 1 for PROCESS_SHARED
 * @key:	address where result is stored.
 *
 * Returns a negative error code or 0
 * The key words are stored in *key on success.
 *
 * For shared mappings, it's (page->index, vma->vm_file->f_path.dentry->d_inode,
 * offset_within_page).  For private mappings, it's (uaddr, current->mm).
 * We can usually work out the index without swapping in the page.
 *
 * lock_page() might sleep, the caller should not hold a spinlock.
 */
static int
get_futex_key(uint32_t *uaddr, int fshared, union futex_key *key)
{
	unsigned long address = (unsigned long)uaddr;
	unsigned long base;
	unsigned long offset;
	unsigned long phys;
	struct thread *thread = cpu_local_var(current);
	struct process_vm *mm = thread->vm;
	int is_private;
	int error;

	/*
	 * The futex address must be "naturally" aligned.
	 */
	error = futex_key_prepare_result(address, fshared, &base, &offset,
					 &is_private);
	if (error)
		return error;
	key->both.offset = offset;
	address = base;

	/*
	 * PROCESS_PRIVATE futexes are fast.
	 * As the mm cannot disappear under us and the 'key' only needs
	 * virtual address, we dont even have to find the underlying vma.
	 * Note : We do have to check 'uaddr' is a valid user address,
	 *        but access_ok() should be faster than find_vma()
	 */
	if (is_private) {
		key->private.mm = mm;
		key->private.address = address;
		get_futex_key_refs(key);
		return 0;
	}

	key->both.offset |= FUT_OFF_MMSHARED;

retry_v2p:
	/* Just use physical address of page, McKernel does not do swapping */
	if (ihk_mc_pt_virt_to_phys(mm->address_space->page_table, 
				(void *)uaddr, &phys)) { 

		/* Check if we can fault in page */
		if (page_fault_process_vm(mm, uaddr, PF_POPULATE | PF_WRITE | PF_USER)) {
			kprintf("error: get_futex_key() virt to phys translation failed\n");
			return -EFAULT;
		}

		goto retry_v2p;
	}
	key->shared.phys = (void *)phys;
	key->shared.pgoff = 0;

	return 0;
}


static inline
void put_futex_key(int fshared, union futex_key *key)
{
	drop_futex_key_refs(key);
}

static int cmpxchg_futex_value_locked(uint32_t __user *uaddr, uint32_t uval, uint32_t newval)
{
	int curval;

	/* RIKEN: futexes are on not swappable memory */
	curval = futex_atomic_cmpxchg_inatomic((int*)uaddr, (int)uval, (int)newval);

	return curval;
}

/*
 * The hash bucket lock must be held when this is called.
 * Afterwards, the futex_q must not be accessed.
 */
static unsigned long futex_wake_linux_channel_bridge(int linux_cpu)
{
	return (unsigned long)ikc2linuxs[linux_cpu];
}

static int futex_wake_send_bridge(unsigned long channel_addr,
				  unsigned long packet_addr)
{
	return ihk_ikc_send((struct ihk_ikc_channel_desc *)channel_addr,
			(void *)packet_addr, 0);
}

static void futex_wake_thread_bridge(unsigned long thread_addr, int status)
{
	sched_wakeup_thread((struct thread *)thread_addr, status);
}

static void futex_wake_log_bridge(int event, unsigned long thread_addr,
				  unsigned long uti_futex_resp, int linux_cpu,
				  unsigned long channel_addr, int rc)
{
	struct thread *p = (struct thread *)thread_addr;

	if (event == FUTEX_WAKE_LOG_LINUX_TARGET) {
		dkprintf("%s: waking up migrated-to-Linux thread (tid %d),uti_futex_resp=%p,linux_cpu: %d\n",
			__func__, p->tid, (void *)uti_futex_resp, linux_cpu);
	}
	else if (event == FUTEX_WAKE_LOG_SEND_FAILED) {
		dkprintf("%s: ERROR: ihk_ikc_send returned %d, resp_channel=%p\n",
				__func__, rc, (void *)channel_addr);
	}
	else if (event == FUTEX_WAKE_LOG_SEND_OK) {
		dkprintf("%s: futex wake IKC sent, resp_channel=%p\n",
				__func__, (void *)channel_addr);
	}
	else if (event == FUTEX_WAKE_LOG_MCKERNEL_TARGET) {
		dkprintf("%s: waking up McKernel thread (tid %d)\n",
				__func__, p->tid);
	}
}

static void wake_futex(struct futex_q *q)
{
	/*
	 * We set q->lock_ptr = NULL _before_ we wake up the task. If
	 * a non futex wake up happens on another CPU then the task
	 * might exit and p would dereference a non existing task
	 * struct. Prevent this by holding a reference on p across the
	 * wake up.
	 */

	struct ikc_scd_packet pckt;

	futex_wake_orchestrate_result((unsigned long)q,
			__builtin_offsetof(struct futex_q, list),
			__builtin_offsetof(struct plist_node, plist),
			__builtin_offsetof(struct futex_q, lock_ptr),
			__builtin_offsetof(struct futex_q, task),
			__builtin_offsetof(struct futex_q, uti_futex_resp),
			__builtin_offsetof(struct futex_q, linux_cpu),
			__builtin_offsetof(struct thread, spin_sleep),
			(unsigned long)&pckt,
			__builtin_offsetof(struct ikc_scd_packet, msg),
			__builtin_offsetof(struct ikc_scd_packet, futex.resp),
			__builtin_offsetof(struct ikc_scd_packet,
					   futex.spin_sleep),
			SCD_MSG_FUTEX_WAKE, (unsigned long)cpu_local_var(ikc2linux),
			PS_NORMAL, futex_wake_linux_channel_bridge,
			futex_wake_send_bridge, futex_wake_thread_bridge,
			futex_wake_log_bridge);
}

static void futex_wake_scan_bridge(unsigned long q_addr)
{
	wake_futex((struct futex_q *)q_addr);
}

/*
 * Express the locking dependencies for lockdep:
 */
static void futex_hb_lock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock_addr);
}

static void futex_hb_unlock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock_addr);
}

static void futex_key_refs_bridge(unsigned long key_addr)
{
	get_futex_key_refs((union futex_key *)key_addr);
}

static inline void
double_lock_hb(struct futex_hash_bucket *hb1, struct futex_hash_bucket *hb2)
{
	futex_double_lock_hb_result((unsigned long)hb1, (unsigned long)hb2,
			__builtin_offsetof(struct futex_hash_bucket, lock),
			futex_hb_lock_bridge);
}

static inline void
double_unlock_hb(struct futex_hash_bucket *hb1, struct futex_hash_bucket *hb2)
{
	futex_double_unlock_hb_result((unsigned long)hb1, (unsigned long)hb2,
			__builtin_offsetof(struct futex_hash_bucket, lock),
			futex_hb_unlock_bridge);
}

/*
 * Wake up waiters matching bitset queued on this futex (uaddr).
 */
static int futex_wake(uint32_t *uaddr, int fshared, int nr_wake,
		uint32_t bitset)
{
	struct futex_hash_bucket *hb;
	struct plist_head *head;
	union futex_key key = FUTEX_KEY_INIT;
	int ret;
	unsigned long irqstate;

	if (!futex_wake_bitset_valid_result(bitset))
		return -EINVAL;

	ret = get_futex_key(uaddr, fshared, &key);
	if ((ret != 0))
		goto out;

	hb = hash_futex(&key);
	irqstate = ihk_mc_spinlock_lock(&hb->lock);
	head = &hb->chain;

	ret = futex_wake_scan_result((unsigned long)head,
			__builtin_offsetof(struct futex_q, list),
			__builtin_offsetof(struct futex_q, key),
			__builtin_offsetof(struct futex_q, bitset),
			__builtin_offsetof(union futex_key, both.word),
			__builtin_offsetof(union futex_key, both.ptr),
			__builtin_offsetof(union futex_key, both.offset),
			key.both.word, (unsigned long)key.both.ptr,
			key.both.offset, bitset, 1, nr_wake,
			futex_wake_scan_bridge);

	ihk_mc_spinlock_unlock(&hb->lock, irqstate);
	put_futex_key(fshared, &key);
out:
	return ret;
}

/*
 * Wake up all waiters hashed on the physical page that is mapped
 * to this virtual address:
 */
static int
futex_wake_op(uint32_t *uaddr1, int fshared, uint32_t *uaddr2,
			  int nr_wake, int nr_wake2, int op)
{
	union futex_key key1 = FUTEX_KEY_INIT, key2 = FUTEX_KEY_INIT;
	struct futex_hash_bucket *hb1, *hb2;
	struct plist_head *head;
	int ret, op_ret;

retry:
	ret = get_futex_key(uaddr1, fshared, &key1);
	if ((ret != 0))
		goto out;
	ret = get_futex_key(uaddr2, fshared, &key2);
	if ((ret != 0))
		goto out_put_key1;

	hb1 = hash_futex(&key1);
	hb2 = hash_futex(&key2);

retry_private:
	double_lock_hb(hb1, hb2);
	op_ret = futex_atomic_op_inuser(op, (int*)uaddr2);
	if ((op_ret < 0)) {

		double_unlock_hb(hb1, hb2);

		if ((op_ret != -EFAULT)) {
			ret = op_ret;
			goto out_put_keys;
		}

		/* RIKEN: set ret to 0 as if fault_in_user_writeable() returned it */
		ret = 0;

		if (!fshared)
			goto retry_private;

		put_futex_key(fshared, &key2);
		put_futex_key(fshared, &key1);
		goto retry;
	}

	head = &hb1->chain;

	ret = futex_wake_scan_result((unsigned long)head,
			__builtin_offsetof(struct futex_q, list),
			__builtin_offsetof(struct futex_q, key),
			__builtin_offsetof(struct futex_q, bitset),
			__builtin_offsetof(union futex_key, both.word),
			__builtin_offsetof(union futex_key, both.ptr),
			__builtin_offsetof(union futex_key, both.offset),
			key1.both.word, (unsigned long)key1.both.ptr,
			key1.both.offset, 0, 0, nr_wake,
			futex_wake_scan_bridge);

	if (op_ret > 0) {
		head = &hb2->chain;

		op_ret = futex_wake_scan_result((unsigned long)head,
				__builtin_offsetof(struct futex_q, list),
				__builtin_offsetof(struct futex_q, key),
				__builtin_offsetof(struct futex_q, bitset),
				__builtin_offsetof(union futex_key, both.word),
				__builtin_offsetof(union futex_key, both.ptr),
				__builtin_offsetof(union futex_key, both.offset),
				key2.both.word, (unsigned long)key2.both.ptr,
				key2.both.offset, 0, 0, nr_wake2,
				futex_wake_scan_bridge);
		ret += op_ret;
	}

	double_unlock_hb(hb1, hb2);
out_put_keys:
	put_futex_key(fshared, &key2);
out_put_key1:
	put_futex_key(fshared, &key1);
out:
	return ret;
}

/**
 * requeue_futex() - Requeue a futex_q from one hb to another
 * @q:		the futex_q to requeue
 * @hb1:	the source hash_bucket
 * @hb2:	the target hash_bucket
 * @key2:	the new key for the requeued futex_q
 */
static inline
void requeue_futex(struct futex_q *q, struct futex_hash_bucket *hb1,
		   struct futex_hash_bucket *hb2, union futex_key *key2)
{
#ifdef CONFIG_DEBUG_PI_LIST
	const unsigned long debug_spinlock_offset =
		__builtin_offsetof(struct plist_node, plist.spinlock);
#else
	const unsigned long debug_spinlock_offset = 0;
#endif

	/*
	 * If key1 and key2 hash to the same bucket, no need to
	 * requeue.
	 */
	futex_requeue_move_result((unsigned long)q,
				  __builtin_offsetof(struct futex_q, list),
				  __builtin_offsetof(struct futex_q, lock_ptr),
				  (unsigned long)&hb1->chain,
				  (unsigned long)&hb2->chain,
				  (unsigned long)&hb2->lock,
				  debug_spinlock_offset);
	if (futex_requeue_key_update_result((unsigned long)q,
				__builtin_offsetof(struct futex_q, key),
				(unsigned long)key2, sizeof(*key2),
				futex_key_refs_bridge)) {
		get_futex_key_refs(key2);
		q->key = *key2;
	}
}

struct futex_requeue_scan_context {
	struct futex_hash_bucket *hb1;
	struct futex_hash_bucket *hb2;
	union futex_key *key2;
};

static void futex_requeue_wake_bridge(unsigned long q_addr,
				      unsigned long ctx_addr)
{
	(void)ctx_addr;
	wake_futex((struct futex_q *)q_addr);
}

static void futex_requeue_move_bridge(unsigned long q_addr,
				      unsigned long ctx_addr)
{
	struct futex_requeue_scan_context *ctx =
		(struct futex_requeue_scan_context *)ctx_addr;

	requeue_futex((struct futex_q *)q_addr, ctx->hb1, ctx->hb2,
			ctx->key2);
}

/**
 * futex_requeue() - Requeue waiters from uaddr1 to uaddr2
 * uaddr1:	source futex user address
 * uaddr2:	target futex user address
 * nr_wake:	number of waiters to wake (must be 1 for requeue_pi)
 * nr_requeue:	number of waiters to requeue (0-INT_MAX)
 * requeue_pi:	if we are attempting to requeue from a non-pi futex to a
 * 		pi futex (pi to pi requeue is not supported)
 *
 * Requeue waiters on uaddr1 to uaddr2. In the requeue_pi case, try to acquire
 * uaddr2 atomically on behalf of the top waiter.
 *
 * Returns:
 * >=0 - on success, the number of tasks requeued or woken
 *  <0 - on error
 */
static int futex_requeue(uint32_t *uaddr1, int fshared, uint32_t *uaddr2,
		int nr_wake, int nr_requeue, uint32_t *cmpval,
		int requeue_pi)
{
	union futex_key key1 = FUTEX_KEY_INIT, key2 = FUTEX_KEY_INIT;
	int drop_count = 0, task_count = 0, ret;
	struct futex_hash_bucket *hb1, *hb2;
	struct futex_requeue_scan_context requeue_ctx;
	struct plist_head *head1;

	ret = get_futex_key(uaddr1, fshared, &key1);
	if ((ret != 0))
		goto out;
	ret = get_futex_key(uaddr2, fshared, &key2);
	if ((ret != 0))
		goto out_put_key1;

	hb1 = hash_futex(&key1);
	hb2 = hash_futex(&key2);

	double_lock_hb(hb1, hb2);

	if ((cmpval != NULL)) {
		uint32_t curval;

		ret = get_futex_value_locked(&curval, uaddr1);

		if (curval != *cmpval) {
			ret = -EAGAIN;
			goto out_unlock;
		}
	}

	head1 = &hb1->chain;
	requeue_ctx.hb1 = hb1;
	requeue_ctx.hb2 = hb2;
	requeue_ctx.key2 = &key2;
	task_count = futex_requeue_scan_result((unsigned long)head1,
			__builtin_offsetof(struct futex_q, list),
			__builtin_offsetof(struct futex_q, key),
			__builtin_offsetof(union futex_key, both.word),
			__builtin_offsetof(union futex_key, both.ptr),
			__builtin_offsetof(union futex_key, both.offset),
			key1.both.word, (unsigned long)key1.both.ptr,
			key1.both.offset, nr_wake, nr_requeue, &drop_count,
			futex_requeue_wake_bridge, futex_requeue_move_bridge,
			(unsigned long)&requeue_ctx);

out_unlock:
	double_unlock_hb(hb1, hb2);

	/*
	 * drop_futex_key_refs() must be called outside the spinlocks. During
	 * the requeue we moved futex_q's from the hash bucket at key1 to the
	 * one at key2 and updated their key pointer.  We no longer need to
	 * hold the references to key1.
	 */
	while (--drop_count >= 0)
		drop_futex_key_refs(&key1);

	put_futex_key(fshared, &key2);
out_put_key1:
	put_futex_key(fshared, &key1);
out:
	return ret ? ret : task_count;
}

/* The key must be already stored in q->key. */
static inline struct futex_hash_bucket *queue_lock(struct futex_q *q)
{
	struct futex_hash_bucket *hb;

	get_futex_key_refs(&q->key);
	hb = hash_futex(&q->key);
	futex_queue_lock_ptr_store_result((unsigned long)q,
		__builtin_offsetof(struct futex_q, lock_ptr),
		(unsigned long)&hb->lock);

	ihk_mc_spinlock_lock_noirq(&hb->lock);
	return hb;
}

static inline void
queue_unlock(struct futex_q *q, struct futex_hash_bucket *hb)
{
	ihk_mc_spinlock_unlock_noirq(&hb->lock);
	drop_futex_key_refs(&q->key);
}

static int futex_wait_get_key_bridge(unsigned long uaddr, int fshared,
				     unsigned long key_addr)
{
	return get_futex_key((uint32_t *)uaddr, fshared,
			(union futex_key *)key_addr);
}

static unsigned long futex_wait_queue_lock_bridge(unsigned long q_addr)
{
	return (unsigned long)queue_lock((struct futex_q *)q_addr);
}

static int futex_wait_get_value_bridge(unsigned long value_addr,
				       unsigned long uaddr)
{
	return get_futex_value_locked((uint32_t *)value_addr,
			(uint32_t *)uaddr);
}

static void futex_wait_queue_unlock_bridge(unsigned long q_addr,
					   unsigned long hb_addr)
{
	queue_unlock((struct futex_q *)q_addr,
			(struct futex_hash_bucket *)hb_addr);
}

static void futex_wait_put_key_bridge(int fshared, unsigned long key_addr)
{
	put_futex_key(fshared, (union futex_key *)key_addr);
}

/**
 * queue_me() - Enqueue the futex_q on the futex_hash_bucket
 * @q:	The futex_q to enqueue
 * @hb:	The destination hash bucket
 *
 * The hb->lock must be held by the caller, and is released here. A call to
 * queue_me() is typically paired with exactly one call to unqueue_me().  The
 * exceptions involve the PI related operations, which may use unqueue_me_pi()
 * or nothing if the unqueue is done as part of the wake process and the unqueue
 * state is implicit in the state of woken task (see futex_wait_requeue_pi() for
 * an example).
 */
static inline void queue_me(struct futex_q *q, struct futex_hash_bucket *hb)
{
	int prio;
	struct thread *thread = cpu_local_var(current);
	ihk_spinlock_t *_runq_lock = &cpu_local_var(runq_lock);
	unsigned int *_flags = &cpu_local_var(flags);
#ifdef CONFIG_DEBUG_PI_LIST
	const unsigned long debug_spinlock_offset =
		__builtin_offsetof(struct plist_node, plist.spinlock);
#else
	const unsigned long debug_spinlock_offset = 0;
#endif

	/*
	 * The priority used to register this element is
	 * - either the real thread-priority for the real-time threads
	 * (i.e. threads with a priority lower than MAX_RT_PRIO)
	 * - or MAX_RT_PRIO for non-RT threads.
	 * Thus, all RT-threads are woken first in priority order, and
	 * the others are woken last, in FIFO order.
	 *
	 * RIKEN: no priorities at the moment, everyone is 10.
	 */
	prio = 10; 

	futex_queue_insert_result((unsigned long)q,
		__builtin_offsetof(struct futex_q, list),
		(unsigned long)&hb->chain,
		prio,
		debug_spinlock_offset,
		(unsigned long)&hb->lock);

	/* Store information about wait thread for uti-futex*/
	futex_queue_publish_waiter_result((unsigned long)q,
		__builtin_offsetof(struct futex_q, task),
		__builtin_offsetof(struct futex_q, th_spin_sleep_pa),
		__builtin_offsetof(struct futex_q, th_status_pa),
		__builtin_offsetof(struct futex_q, th_spin_sleep_lock_pa),
		__builtin_offsetof(struct futex_q, proc_status_pa),
		__builtin_offsetof(struct futex_q, proc_update_lock_pa),
		__builtin_offsetof(struct futex_q, runq_lock_pa),
		__builtin_offsetof(struct futex_q, clv_flags_pa),
		__builtin_offsetof(struct futex_q, intr_id),
		__builtin_offsetof(struct futex_q, intr_vector),
		(unsigned long)thread,
		virt_to_phys((void *)&thread->spin_sleep),
		virt_to_phys((void *)&thread->status),
		virt_to_phys((void *)&thread->spin_sleep_lock),
		virt_to_phys((void *)&thread->proc->status),
		virt_to_phys((void *)&thread->proc->update_lock),
		virt_to_phys((void *)_runq_lock),
		virt_to_phys((void *)_flags),
		ihk_mc_get_interrupt_id(thread->cpu_id),
		ihk_mc_get_vector(IHK_GV_IKC));

	ihk_mc_spinlock_unlock_noirq(&hb->lock);
}

/**
 * unqueue_me() - Remove the futex_q from its futex_hash_bucket
 * @q:	The futex_q to unqueue
 *
 * The q->lock_ptr must not be held by the caller. A call to unqueue_me() must
 * be paired with exactly one earlier call to queue_me().
 *
 * Returns:
 *   1 - if the futex_q was still queued (and we removed unqueued it)
 *   0 - if the futex_q was already removed by the waking thread
 */
static int unqueue_me(struct futex_q *q)
{
	ihk_spinlock_t *lock_ptr;
	int ret = 0;

	/* In the common case we don't take the spinlock, which is nice. */
retry:
	lock_ptr = q->lock_ptr;
	barrier();
	if (lock_ptr != NULL) {
		ihk_mc_spinlock_lock_noirq(lock_ptr);
		/*
		 * q->lock_ptr can change between reading it and
		 * spin_lock(), causing us to take the wrong lock.  This
		 * corrects the race condition.
		 *
		 * Reasoning goes like this: if we have the wrong lock,
		 * q->lock_ptr must have changed (maybe several times)
		 * between reading it and the spin_lock().  It can
		 * change again after the spin_lock() but only if it was
		 * already changed before the spin_lock().  It cannot,
		 * however, change back to the original value.  Therefore
		 * we can detect whether we acquired the correct lock.
		 */
		if (lock_ptr != q->lock_ptr) {
			ihk_mc_spinlock_unlock_noirq(lock_ptr);
			goto retry;
		}
		ret = futex_unqueue_detach_result((unsigned long)q,
			__builtin_offsetof(struct futex_q, list),
			__builtin_offsetof(struct plist_node, plist));

		ihk_mc_spinlock_unlock_noirq(lock_ptr);
	}

	drop_futex_key_refs(&q->key);
	return ret;
}

/**
 * futex_wait_queue_me() - queue_me() and wait for wakeup, timeout, or signal
 * @hb:		the futex hash bucket, must be locked by the caller
 * @q:		the futex_q to queue up on
 * @timeout:	the prepared hrtimer_sleeper, or null for no timeout
 */

/* RIKEN: this function has been rewritten so that it returns the remaining
 * time in case we are waken.
 */
static int64_t futex_wait_queue_me(struct futex_hash_bucket *hb,
		struct futex_q *q, uint64_t timeout)
{
	int64_t time_remain = 0;
	unsigned long irqstate;
	struct thread *thread = cpu_local_var(current);
	int schedule_action;
	/*
	 * The task state is guaranteed to be set before another task can
	 * wake it. 
	 * queue_me() calls spin_unlock() upon completion, serializing
	 * access to the hash list and forcing a memory barrier.
	 */
	futex_wait_mark_interruptible_result((unsigned long)thread,
		__builtin_offsetof(struct thread, status),
		PS_INTERRUPTIBLE);

	/* Indicate spin sleep. Note that schedule_timeout() with
	 * idle_halt should use spin sleep because sleep with timeout
	 * is not implemented.
	 */
	if (!idle_halt || timeout) {
		irqstate = ihk_mc_spinlock_lock(&thread->spin_sleep_lock);
		futex_wait_spin_sleep_store_result((unsigned long)thread,
			__builtin_offsetof(struct thread, spin_sleep), 1);
		ihk_mc_spinlock_unlock(&thread->spin_sleep_lock, irqstate);
	}

	queue_me(q, hb);

	schedule_action = futex_wait_schedule_action_result(
		!plist_node_empty(&q->list), timeout);
	if (schedule_action == FUTEX_WAIT_SCHEDULE_TIMEOUT) {
		dkprintf("futex_wait_queue_me(): tid: %d schedule_timeout()\n", thread->tid);
		time_remain = schedule_timeout(timeout);
	} else if (schedule_action == FUTEX_WAIT_SCHEDULE_DIRECT) {
		dkprintf("futex_wait_queue_me(): tid: %d schedule()\n", thread->tid);
		spin_sleep_or_schedule();
		time_remain = 0;
	}
	if (schedule_action != FUTEX_WAIT_SCHEDULE_NONE)
		dkprintf("futex_wait_queue_me(): tid: %d woken up\n", thread->tid);
	
	/* This does not need to be serialized */
	futex_wait_finish_state_result((unsigned long)thread,
		__builtin_offsetof(struct thread, status),
		__builtin_offsetof(struct thread, spin_sleep),
		PS_RUNNING);
	
	return time_remain;
}

/**
 * futex_wait_setup() - Prepare to wait on a futex
 * @uaddr:	the futex userspace address
 * @val:	the expected value
 * @fshared:	whether the futex is shared (1) or not (0)
 * @q:		the associated futex_q
 * @hb:		storage for hash_bucket pointer to be returned to caller
 *
 * Setup the futex_q and locate the hash_bucket.  Get the futex value and
 * compare it with the expected value.  Handle atomic faults internally.
 * Return with the hb lock held and a q.key reference on success, and unlocked
 * with no q.key reference on failure.
 *
 * Returns:
 *  0 - uaddr contains val and hb has been locked
 * <1 - -EFAULT or -EWOULDBLOCK (uaddr does not contain val) and hb is unlcoked
 */
static int futex_wait_setup(uint32_t __user *uaddr, uint32_t val, int fshared,
		struct futex_q *q, struct futex_hash_bucket **hb)
{
	unsigned long hb_addr = 0;
	int ret;

	/*
	 * Access the page AFTER the hash-bucket is locked.
	 * Order is important:
	 *
	 *   Userspace waiter: val = var; if (cond(val)) futex_wait(&var, val);
	 *   Userspace waker:  if (cond(var)) { var = new; futex_wake(&var); }
	 *
	 * The basic logical guarantee of a futex is that it blocks ONLY
	 * if cond(var) is known to be true at the time of blocking, for
	 * any cond.  If we queued after testing *uaddr, that would open
	 * a race condition where we could block indefinitely with
	 * cond(var) false, which would violate the guarantee.
	 *
	 * A consequence is that futex_wait() can return zero and absorb
	 * a wakeup when *uaddr != val on entry to the syscall.  This is
	 * rare, but normal.
	 */
	ret = futex_wait_setup_result((unsigned long)uaddr, val, fshared,
			(unsigned long)q, &hb_addr,
			__builtin_offsetof(struct futex_q, key),
			sizeof(q->key),
			futex_wait_get_key_bridge,
			futex_wait_queue_lock_bridge,
			futex_wait_get_value_bridge,
			futex_wait_queue_unlock_bridge,
			futex_wait_put_key_bridge);
	if (!ret)
		*hb = (struct futex_hash_bucket *)hb_addr;
	return ret;
}

static int futex_wait(uint32_t __user *uaddr, int fshared,
		      uint32_t val, uint64_t timeout, uint32_t bitset, int clockrt)
{
	struct futex_hash_bucket *hb;
	int64_t time_remain;
	struct futex_q lq;
	struct futex_q *q = NULL;
	int has_pending_signal = 0, post_action, ret, unqueued;

	if (!futex_wake_bitset_valid_result(bitset))
		return -EINVAL;

	q = &lq;

#ifdef PROFILE_ENABLE
	if (cpu_local_var(current)->profile &&
		cpu_local_var(current)->profile_start_ts) {
		cpu_local_var(current)->profile_elapsed_ts +=
			(rdtsc() - cpu_local_var(current)->profile_start_ts);
		cpu_local_var(current)->profile_start_ts = 0;
	}
#endif

	futex_wait_prepare_q_result((unsigned long)q,
		__builtin_offsetof(struct futex_q, bitset),
		__builtin_offsetof(struct futex_q, requeue_pi_key),
		__builtin_offsetof(struct futex_q, uti_futex_resp),
		bitset,
		(unsigned long)cpu_local_var(uti_futex_resp));

retry:
	/* Prepare to wait on uaddr. */
	ret = futex_wait_setup(uaddr, val, fshared, q, &hb);
	if (ret) {
		dkprintf("%s: tid=%d futex_wait_setup returns zero, no need to sleep\n",
			__func__, cpu_local_var(current)->tid);
		goto out;
	}

	/* queue_me and wait for wakeup, timeout, or a signal. */
	time_remain = futex_wait_queue_me(hb, q, timeout);

	/* If we were woken (and unqueued), we succeeded, whatever. */
	ret = 0;
	unqueued = unqueue_me(q);
	if (unqueued && !(timeout && !time_remain))
		has_pending_signal = hassigpending(cpu_local_var(current)) != NULL;
	post_action = futex_wait_post_action_result(unqueued, timeout,
			time_remain, has_pending_signal,
			time_remain == -ERESTARTSYS);
	if (post_action == FUTEX_WAIT_POST_SUCCESS) {
		dkprintf("%s: tid=%d unqueued\n",
				__func__, cpu_local_var(current)->tid);
		goto out_put_key;
	}

	/* RIKEN: timer expired case (indicated by !time_remain) */
	if (post_action == FUTEX_WAIT_POST_TIMEOUT) {
		ret = -ETIMEDOUT;
		dkprintf("%s: tid=%d timer expired\n",
				__func__, cpu_local_var(current)->tid);
		goto out_put_key;
	}

	/* RIKEN: futex_wait_queue_me() returns -ERESTARTSYS when waiting on Linux CPU and woken up by signal */
	if (post_action == FUTEX_WAIT_POST_INTERRUPT) {
		ret = -EINTR;
		dkprintf("%s: tid=%d woken up by signal\n",
				__func__, cpu_local_var(current)->tid);
		goto out_put_key;
	}

	/* RIKEN: no signals */
	put_futex_key(fshared, &q->key);
	goto retry;

out_put_key:
	put_futex_key(fshared, &q->key);
out:
#ifdef PROFILE_ENABLE
	if (cpu_local_var(current)->profile) {
		cpu_local_var(current)->profile_start_ts = rdtsc();
	}
#endif
	return ret;
}

static int futex_dispatch_wait_bridge(unsigned long uaddr, int fshared,
		uint32_t val, uint64_t timeout, uint32_t val3, int clockrt)
{
	return futex_wait((uint32_t *)uaddr, fshared, val, timeout, val3,
			clockrt);
}

static int futex_dispatch_wake_bridge(unsigned long uaddr, int fshared,
		uint32_t val, uint32_t val3)
{
	return futex_wake((uint32_t *)uaddr, fshared, val, val3);
}

static int futex_dispatch_requeue_bridge(unsigned long uaddr, int fshared,
		unsigned long uaddr2, uint32_t val, uint32_t val2,
		int cmpval_present, uint32_t cmpval, int requeue_pi)
{
	uint32_t local_cmpval = cmpval;

	return futex_requeue((uint32_t *)uaddr, fshared, (uint32_t *)uaddr2,
			val, val2, cmpval_present ? &local_cmpval : NULL,
			requeue_pi);
}

static int futex_dispatch_wake_op_bridge(unsigned long uaddr, int fshared,
		unsigned long uaddr2, uint32_t val, uint32_t val2, uint32_t val3)
{
	return futex_wake_op((uint32_t *)uaddr, fshared, (uint32_t *)uaddr2,
			val, val2, val3);
}

static void futex_dispatch_invalid_bridge(int cmd)
{
	kprintf("futex() invalid cmd: %d \n", cmd);
}

int futex(uint32_t *uaddr, int op, uint32_t val, uint64_t timeout,
		uint32_t *uaddr2, uint32_t val2, uint32_t val3, int fshared)
{
	dkprintf("%s: uaddr=%p, op=%x, val=%x, timeout=%ld, uaddr2=%p, val2=%x, val3=%x, fshared=%d\n",
			__func__, uaddr, op, val, timeout, uaddr2,
			val2, val3, fshared);

	return futex_dispatch_result(op, (unsigned long)uaddr, val, timeout,
			(unsigned long)uaddr2, val2, val3, fshared,
			futex_dispatch_wait_bridge, futex_dispatch_wake_bridge,
			futex_dispatch_requeue_bridge,
			futex_dispatch_wake_op_bridge,
			futex_dispatch_invalid_bridge);
}

#ifndef ARRAY_SIZE
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
#endif

int futex_init(void)
{
	int ret;
#ifdef CONFIG_DEBUG_PI_LIST
	const unsigned long debug_spinlock_offset =
		__builtin_offsetof(struct plist_head, spinlock);
	const unsigned long debug_rawlock_offset =
		__builtin_offsetof(struct plist_head, rawlock);
#else
	const unsigned long debug_spinlock_offset = 0;
	const unsigned long debug_rawlock_offset = 0;
#endif

	ret = futex_init_table_result((unsigned long)&futex_queues,
			FUTEX_HASHBITS,
			sizeof(struct futex_hash_bucket),
			IHK_MC_AP_NOWAIT,
			futex_kmalloc_bridge,
			__builtin_offsetof(struct futex_hash_bucket, lock),
			0,
			__builtin_offsetof(struct futex_hash_bucket, chain),
			__builtin_offsetof(struct plist_head, prio_list),
			__builtin_offsetof(struct plist_head, node_list),
			debug_spinlock_offset,
			debug_rawlock_offset);
	if (ret < 0)
		return ret;

	return 0;
}
