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

#ifdef FUTEX_OP
#undef FUTEX_OP
#endif
int FUTEX_OP(int op, int oparg, int cmp, int cmparg)
{
	unsigned int encoded = (((unsigned int)op & 0x0f) << 28) |
		(((unsigned int)cmp & 0x0f) << 24) |
		(((unsigned int)oparg & 0x0fff) << 12) |
		((unsigned int)cmparg & 0x0fff);

	return (int)encoded;
}

int get_futex_value_locked(uint32_t *dest, uint32_t *from)
{
	*dest = *(volatile uint32_t *)from;

	return 0;
}

static int futex_atomic_access_ok_fallback(int *uaddr, unsigned long size)
{
#ifdef __UACCESS__
	return access_ok(VERIFY_WRITE, uaddr, size);
#else
	(void)uaddr;
	(void)size;
	return 1;
#endif
}

static int futex_atomic_cmpxchg_inatomic_fallback(int *uaddr, int oldval,
						  int newval)
{
	asm volatile("1:\tlock; cmpxchgl %3, %1\n"
		     "2:\t.section .fixup, \"ax\"\n"
		     "3:\tmov     %2, %0\n"
		     "\tjmp     2b\n"
		     "\t.previous\n"
		     " .section __ex_table,\"a\"\n"
		     " .balign 8\n"
		     " .quad 1b,3b\n"
		     " .previous\n"
		     : "=a" (oldval), "+m" (*uaddr)
		     : "i" (-EFAULT), "r" (newval), "0" (oldval)
		     : "memory");

	return oldval;
}

int futex_atomic_cmpxchg_inatomic(int *uaddr, int oldval, int newval)
{
	if (!futex_atomic_access_ok_fallback(uaddr, sizeof(int)))
		return -EFAULT;

	return futex_atomic_cmpxchg_inatomic_fallback(uaddr, oldval, newval);
}

#define FUTEX_X86_ATOMIC_OP1(insn, ret, oldval, uaddr, oparg)	\
	asm volatile("1:\t" insn "\n"				\
		     "2:\t.section .fixup,\"ax\"\n"		\
		     "3:\tmov\t%3, %1\n"			\
		     "\tjmp\t2b\n"				\
		     "\t.previous\n"				\
		     " .section __ex_table,\"a\"\n"		\
		     " .balign 8\n"				\
		     " .quad 1b,3b\n"				\
		     " .previous\n"				\
		     : "=r" (oldval), "=r" (ret), "+m" (*uaddr)	\
		     : "i" (-EFAULT), "0" (oparg), "1" (0))

#define FUTEX_X86_ATOMIC_OP2(insn, ret, oldval, uaddr, oparg)	\
	asm volatile("1:\tmovl	%2, %0\n"			\
		     "\tmovl\t%0, %3\n"				\
		     "\t" insn "\n"				\
		     "2:\tlock; cmpxchgl %3, %2\n"		\
		     "\tjnz\t1b\n"				\
		     "3:\t.section .fixup,\"ax\"\n"		\
		     "4:\tmov\t%5, %1\n"			\
		     "\tjmp\t3b\n"				\
		     "\t.previous\n"				\
		     " .section __ex_table,\"a\"\n"		\
		     " .balign 8\n"				\
		     " .quad 1b,4b\n"				\
		     " .previous\n"				\
		     " .section __ex_table,\"a\"\n"		\
		     " .balign 8\n"				\
		     " .quad 2b,4b\n"				\
		     " .previous\n"				\
		     : "=&a" (oldval), "=&r" (ret),		\
		       "+m" (*uaddr), "=&r" (tem)		\
		     : "r" (oparg), "i" (-EFAULT), "1" (0))

static int futex_atomic_op_inuser_fallback(int op, int *uaddr, int oparg,
					   int *oldval)
{
	int old = 0, ret, tem;

	switch (op) {
	case FUTEX_OP_SET:
		FUTEX_X86_ATOMIC_OP1("xchgl %0, %2", ret, old,
				     uaddr, oparg);
		break;
	case FUTEX_OP_ADD:
		FUTEX_X86_ATOMIC_OP1("lock; xaddl %0, %2", ret, old,
				     uaddr, oparg);
		break;
	case FUTEX_OP_OR:
		FUTEX_X86_ATOMIC_OP2("orl %4, %3", ret, old, uaddr,
				     oparg);
		break;
	case FUTEX_OP_ANDN:
		FUTEX_X86_ATOMIC_OP2("andl %4, %3", ret, old, uaddr,
				     oparg);
		break;
	case FUTEX_OP_XOR:
		FUTEX_X86_ATOMIC_OP2("xorl %4, %3", ret, old, uaddr,
				     oparg);
		break;
	default:
		ret = -ENOSYS;
	}

	if (!ret)
		*oldval = old;

	return ret;
}

int futex_atomic_op_inuser(int encoded_op, int *uaddr)
{
	int op = (encoded_op >> 28) & 7;
	int cmp = (encoded_op >> 24) & 15;
	int oparg = (encoded_op & 0x00fff000) >> 12;
	int cmparg = encoded_op & 0xfff;
	int oldval = 0, ret;

	if (encoded_op & (FUTEX_OP_OPARG_SHIFT << 28))
		oparg = 1 << oparg;

	if (!futex_atomic_access_ok_fallback(uaddr, sizeof(int)))
		return -EFAULT;

	if (op == FUTEX_OP_ANDN)
		oparg = ~oparg;
	ret = futex_atomic_op_inuser_fallback(op, uaddr, oparg, &oldval);

	if (!ret) {
		switch (cmp) {
		case FUTEX_OP_CMP_EQ:
			ret = (oldval == cmparg);
			break;
		case FUTEX_OP_CMP_NE:
			ret = (oldval != cmparg);
			break;
		case FUTEX_OP_CMP_LT:
			ret = (oldval < cmparg);
			break;
		case FUTEX_OP_CMP_GE:
			ret = (oldval >= cmparg);
			break;
		case FUTEX_OP_CMP_LE:
			ret = (oldval <= cmparg);
			break;
		case FUTEX_OP_CMP_GT:
			ret = (oldval > cmparg);
			break;
		default:
			ret = -ENOSYS;
		}
	}
	return ret;
}

static void mc_jhash_mix(uint32_t *a, uint32_t *b, uint32_t *c)
{
	*a -= *b; *a -= *c; *a ^= (*c >> 13);
	*b -= *c; *b -= *a; *b ^= (*a << 8);
	*c -= *a; *c -= *b; *c ^= (*b >> 13);
	*a -= *b; *a -= *c; *a ^= (*c >> 12);
	*b -= *c; *b -= *a; *b ^= (*a << 16);
	*c -= *a; *c -= *b; *c ^= (*b >> 5);
	*a -= *b; *a -= *c; *a ^= (*c >> 3);
	*b -= *c; *b -= *a; *b ^= (*a << 10);
	*c -= *a; *c -= *b; *c ^= (*b >> 15);
}

uint32_t mc_jhash2(const uint32_t *k, uint32_t length, uint32_t initval)
{
	uint32_t a, b, c, len;

	a = b = JHASH_GOLDEN_RATIO;
	c = initval;
	len = length;

	while (len >= 3) {
		a += k[0];
		b += k[1];
		c += k[2];
		mc_jhash_mix(&a, &b, &c);
		k += 3;
		len -= 3;
	}

	c += length * 4;

	switch (len) {
	case 2:
		b += k[1];
	case 1:
		a += k[0];
	};

	mc_jhash_mix(&a, &b, &c);

	return c;
}

struct futex_hash_bucket *get_futex_queues(void)
{
	return futex_queues;
}

static unsigned long futex_kmalloc_bridge(unsigned long size, int flag)
{
	return (unsigned long)kmalloc_tracked(size, flag, __FILE__, __LINE__);
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

static unsigned long futex_wake_hash_key_bridge(unsigned long key_addr)
{
	return (unsigned long)hash_futex((union futex_key *)key_addr);
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

static int futex_get_key_vtop_bridge(unsigned long mm_addr,
				     unsigned long uaddr,
				     unsigned long phys_out_addr)
{
	struct process_vm *mm = (struct process_vm *)mm_addr;

	return ihk_mc_pt_virt_to_phys(mm->address_space->page_table,
			(void *)uaddr, (unsigned long *)phys_out_addr);
}

static int futex_get_key_fault_bridge(unsigned long mm_addr,
				      unsigned long uaddr, int flags)
{
	return page_fault_process_vm((struct process_vm *)mm_addr,
			(void *)uaddr, flags);
}

static void futex_get_key_log_bridge(int event)
{
	if (event == FUTEX_GET_KEY_LOG_VTOP_FAILED)
		kprintf("error: get_futex_key() virt to phys translation failed\n");
}

static void futex_key_refs_bridge(unsigned long key_addr);

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
	struct thread *thread = get_this_cpu_local_var()->current;
	struct process_vm *mm = thread->vm;

	return futex_get_key_result((unsigned long)uaddr, fshared,
			(unsigned long)key, (unsigned long)mm,
			__builtin_offsetof(union futex_key, both.word),
			__builtin_offsetof(union futex_key, both.ptr),
			__builtin_offsetof(union futex_key, both.offset),
			FUT_OFF_MMSHARED, PF_POPULATE | PF_WRITE | PF_USER,
			futex_key_refs_bridge, futex_get_key_vtop_bridge,
			futex_get_key_fault_bridge, futex_get_key_log_bridge);
}

static int futex_get_key_call_bridge(unsigned long uaddr, int fshared,
				     unsigned long key_addr)
{
	return get_futex_key((uint32_t *)uaddr, fshared,
			(union futex_key *)key_addr);
}


static inline
void put_futex_key(int fshared, union futex_key *key)
{
	drop_futex_key_refs(key);
}

static void futex_put_key_call_bridge(int fshared, unsigned long key_addr)
{
	put_futex_key(fshared, (union futex_key *)key_addr);
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
			SCD_MSG_FUTEX_WAKE, (unsigned long)get_this_cpu_local_var()->ikc2linux,
			PS_NORMAL, futex_wake_linux_channel_bridge,
			futex_wake_send_bridge, futex_wake_thread_bridge,
			futex_wake_log_bridge);
}

static void futex_wake_scan_bridge(unsigned long q_addr)
{
	wake_futex((struct futex_q *)q_addr);
}

static unsigned long futex_wake_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

static void futex_wake_unlock_bridge(unsigned long lock_addr,
				     unsigned long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, irqstate);
}

static int futex_wake_atomic_op_bridge(int op, unsigned long uaddr)
{
	return futex_atomic_op_inuser(op, (int *)uaddr);
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

/*
 * Wake up waiters matching bitset queued on this futex (uaddr).
 */
static int futex_wake(uint32_t *uaddr, int fshared, int nr_wake,
		uint32_t bitset)
{
	union futex_key key = FUTEX_KEY_INIT;

	return futex_wake_body_result((unsigned long)uaddr, fshared,
			nr_wake, bitset, (unsigned long)&key,
			__builtin_offsetof(struct futex_hash_bucket, lock),
			__builtin_offsetof(struct futex_hash_bucket, chain),
			__builtin_offsetof(struct futex_q, list),
			__builtin_offsetof(struct futex_q, key),
			__builtin_offsetof(struct futex_q, bitset),
			__builtin_offsetof(union futex_key, both.word),
			__builtin_offsetof(union futex_key, both.ptr),
			__builtin_offsetof(union futex_key, both.offset),
			futex_get_key_call_bridge, futex_wake_hash_key_bridge,
			futex_wake_lock_bridge, futex_wake_unlock_bridge,
			futex_put_key_call_bridge,
			futex_wake_scan_bridge);
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

	return futex_wake_op_body_result((unsigned long)uaddr1, fshared,
			(unsigned long)uaddr2, nr_wake, nr_wake2, op,
			(unsigned long)&key1, (unsigned long)&key2,
			__builtin_offsetof(struct futex_hash_bucket, lock),
			__builtin_offsetof(struct futex_hash_bucket, chain),
			__builtin_offsetof(struct futex_q, list),
			__builtin_offsetof(struct futex_q, key),
			__builtin_offsetof(struct futex_q, bitset),
			__builtin_offsetof(union futex_key, both.word),
			__builtin_offsetof(union futex_key, both.ptr),
			__builtin_offsetof(union futex_key, both.offset),
			futex_get_key_call_bridge, futex_wake_hash_key_bridge,
			futex_hb_lock_bridge, futex_hb_unlock_bridge,
			futex_wake_atomic_op_bridge, futex_put_key_call_bridge,
			futex_wake_scan_bridge);
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

static int futex_wait_get_value_bridge(unsigned long value_addr,
				       unsigned long uaddr);
static void futex_unqueue_drop_key_refs_bridge(unsigned long key_addr);

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
	struct futex_requeue_scan_context requeue_ctx;

	(void)requeue_pi;
	return futex_requeue_body_result((unsigned long)uaddr1, fshared,
			(unsigned long)uaddr2, nr_wake, nr_requeue,
			(unsigned long)cmpval, (unsigned long)&key1,
			(unsigned long)&key2, (unsigned long)&requeue_ctx,
			__builtin_offsetof(struct futex_hash_bucket, lock),
			__builtin_offsetof(struct futex_hash_bucket, chain),
			__builtin_offsetof(struct futex_q, list),
			__builtin_offsetof(struct futex_q, key),
			__builtin_offsetof(union futex_key, both.word),
			__builtin_offsetof(union futex_key, both.ptr),
			__builtin_offsetof(union futex_key, both.offset),
			__builtin_offsetof(struct futex_requeue_scan_context,
				hb1),
			__builtin_offsetof(struct futex_requeue_scan_context,
				hb2),
			__builtin_offsetof(struct futex_requeue_scan_context,
				key2),
			futex_get_key_call_bridge, futex_wake_hash_key_bridge,
			futex_hb_lock_bridge, futex_hb_unlock_bridge,
			futex_wait_get_value_bridge, futex_put_key_call_bridge,
			futex_unqueue_drop_key_refs_bridge,
			futex_requeue_wake_bridge, futex_requeue_move_bridge);
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

static unsigned long futex_wait_queue_lock_bridge(unsigned long q_addr)
{
	return (unsigned long)queue_lock((struct futex_q *)q_addr);
}

static unsigned long futex_virt_to_phys_bridge(unsigned long addr)
{
	return virt_to_phys((void *)addr);
}

static int futex_interrupt_id_bridge(int cpu_id)
{
	return ihk_mc_get_interrupt_id(cpu_id);
}

static int futex_vector_bridge(int vector_key)
{
	return ihk_mc_get_vector(vector_key);
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

static void futex_unqueue_lock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock_addr);
}

static void futex_unqueue_unlock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock_addr);
}

static void futex_unqueue_drop_key_refs_bridge(unsigned long key_addr)
{
	drop_futex_key_refs((union futex_key *)key_addr);
}

static inline void queue_me(struct futex_q *q, struct futex_hash_bucket *hb);

static unsigned long futex_wait_spin_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

static void futex_wait_spin_unlock_bridge(unsigned long lock_addr,
					  unsigned long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, irqstate);
}

static void futex_wait_queue_me_bridge(unsigned long q_addr,
				       unsigned long hb_addr)
{
	queue_me((struct futex_q *)q_addr, (struct futex_hash_bucket *)hb_addr);
}

static int64_t futex_wait_schedule_timeout_bridge(uint64_t timeout)
{
	return (int64_t)schedule_timeout(timeout);
}

static void futex_wait_schedule_direct_bridge(void)
{
	spin_sleep_or_schedule();
}

static void futex_wait_queue_log_bridge(int event, unsigned long thread_addr,
					int tid)
{
	(void)thread_addr;

	if (event == FUTEX_WAIT_QUEUE_LOG_TIMEOUT)
		dkprintf("futex_wait_queue_me(): tid: %d schedule_timeout()\n",
				tid);
	else if (event == FUTEX_WAIT_QUEUE_LOG_DIRECT)
		dkprintf("futex_wait_queue_me(): tid: %d schedule()\n", tid);
	else if (event == FUTEX_WAIT_QUEUE_LOG_WOKEN)
		dkprintf("futex_wait_queue_me(): tid: %d woken up\n", tid);
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
	struct thread *thread = get_this_cpu_local_var()->current;
	ihk_spinlock_t *_runq_lock = &get_this_cpu_local_var()->runq_lock;
	unsigned int *_flags = &get_this_cpu_local_var()->flags;
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
	futex_queue_me_result((unsigned long)q,
		__builtin_offsetof(struct futex_q, list),
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
		(unsigned long)&hb->chain,
		(unsigned long)&hb->lock,
		10,
		debug_spinlock_offset,
		(unsigned long)thread,
		__builtin_offsetof(struct thread, spin_sleep),
		__builtin_offsetof(struct thread, status),
		__builtin_offsetof(struct thread, spin_sleep_lock),
		__builtin_offsetof(struct thread, proc),
		__builtin_offsetof(struct thread, cpu_id),
		__builtin_offsetof(struct process, status),
		__builtin_offsetof(struct process, update_lock),
		(unsigned long)_runq_lock,
		(unsigned long)_flags,
		IHK_GV_IKC,
		futex_virt_to_phys_bridge,
		futex_interrupt_id_bridge,
		futex_vector_bridge,
		futex_hb_unlock_bridge);
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
	return futex_unqueue_me_result((unsigned long)q,
		__builtin_offsetof(struct futex_q, lock_ptr),
		__builtin_offsetof(struct futex_q, list),
		__builtin_offsetof(struct plist_node, plist),
		__builtin_offsetof(struct futex_q, key),
		futex_unqueue_lock_bridge,
		futex_unqueue_unlock_bridge,
		futex_unqueue_drop_key_refs_bridge);
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
	struct thread *thread = get_this_cpu_local_var()->current;

	return futex_wait_queue_me_result((unsigned long)hb, (unsigned long)q,
		__builtin_offsetof(struct futex_q, list),
		__builtin_offsetof(struct plist_node, plist),
		__builtin_offsetof(struct plist_head, node_list),
		(unsigned long)thread,
		__builtin_offsetof(struct thread, status),
		__builtin_offsetof(struct thread, spin_sleep),
		__builtin_offsetof(struct thread, spin_sleep_lock),
		__builtin_offsetof(struct thread, tid),
		idle_halt, timeout, PS_INTERRUPTIBLE, PS_RUNNING,
		futex_wait_spin_lock_bridge,
		futex_wait_spin_unlock_bridge,
		futex_wait_queue_me_bridge,
		futex_wait_schedule_timeout_bridge,
		futex_wait_schedule_direct_bridge,
		futex_wait_queue_log_bridge);
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
			futex_get_key_call_bridge,
			futex_wait_queue_lock_bridge,
			futex_wait_get_value_bridge,
			futex_wait_queue_unlock_bridge,
			futex_put_key_call_bridge);
	if (!ret)
		*hb = (struct futex_hash_bucket *)hb_addr;
	return ret;
}

static int futex_wait_setup_body_bridge(unsigned long uaddr, uint32_t val,
		int fshared, unsigned long q_addr, unsigned long hb_out_addr)
{
	struct futex_hash_bucket *hb = NULL;
	int ret;

	ret = futex_wait_setup((uint32_t *)uaddr, val, fshared,
			(struct futex_q *)q_addr, &hb);
	if (!ret && hb_out_addr)
		*(unsigned long *)hb_out_addr = (unsigned long)hb;
	return ret;
}

static int64_t futex_wait_queue_body_bridge(unsigned long hb_addr,
		unsigned long q_addr, uint64_t timeout)
{
	return futex_wait_queue_me((struct futex_hash_bucket *)hb_addr,
			(struct futex_q *)q_addr, timeout);
}

static int futex_wait_unqueue_body_bridge(unsigned long q_addr)
{
	return unqueue_me((struct futex_q *)q_addr);
}

static int futex_wait_has_signal_bridge(unsigned long thread_addr)
{
	return hassigpending((struct thread *)thread_addr) != NULL;
}

static void futex_wait_log_bridge(int event, unsigned long thread_addr,
		int tid, int ret)
{
	(void)thread_addr;

	if (event == FUTEX_WAIT_LOG_SETUP_RET)
		dkprintf("futex_wait: tid=%d futex_wait_setup returns zero, no need to sleep\n",
				tid);
	else if (event == FUTEX_WAIT_LOG_SUCCESS)
		dkprintf("futex_wait: tid=%d unqueued\n", tid);
	else if (event == FUTEX_WAIT_LOG_TIMEOUT)
		dkprintf("futex_wait: tid=%d timer expired\n", tid);
	else if (event == FUTEX_WAIT_LOG_INTERRUPT)
		dkprintf("futex_wait: tid=%d woken up by signal\n", tid);
	(void)ret;
}

static unsigned long futex_wait_timestamp_bridge(void)
{
	return rdtsc();
}

static int futex_wait_body_entry_bridge(unsigned long uaddr, int fshared,
		uint32_t val, uint64_t timeout, uint32_t bitset,
		unsigned long q_addr, unsigned long thread_addr,
		unsigned long uti_futex_resp)
{
	return futex_wait_body_result(uaddr, fshared, val, timeout, bitset,
		q_addr, thread_addr, uti_futex_resp,
		__builtin_offsetof(struct futex_q, bitset),
		__builtin_offsetof(struct futex_q, requeue_pi_key),
		__builtin_offsetof(struct futex_q, uti_futex_resp),
		__builtin_offsetof(struct futex_q, key),
		__builtin_offsetof(struct thread, tid),
		futex_wait_setup_body_bridge,
		futex_wait_queue_body_bridge,
		futex_wait_unqueue_body_bridge,
		futex_wait_has_signal_bridge,
		futex_put_key_call_bridge,
		futex_wait_log_bridge);
}

static int futex_wait(uint32_t __user *uaddr, int fshared,
		      uint32_t val, uint64_t timeout, uint32_t bitset, int clockrt)
{
	struct futex_q lq;
	struct futex_q *q = NULL;
	struct thread *thread;
	int profile_enabled = 0;

	q = &lq;
	thread = get_this_cpu_local_var()->current;

#ifdef PROFILE_ENABLE
	profile_enabled = 1;
#endif

	return futex_wait_entry_result((unsigned long)uaddr, fshared, val,
		timeout, bitset, (unsigned long)q, (unsigned long)thread,
		(unsigned long)get_this_cpu_local_var()->uti_futex_resp, profile_enabled,
		__builtin_offsetof(struct thread, profile),
		__builtin_offsetof(struct thread, profile_start_ts),
		__builtin_offsetof(struct thread, profile_elapsed_ts),
		futex_wait_timestamp_bridge,
		futex_wait_body_entry_bridge);
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
