#include <linux/sched.h>
#include <linux/module.h>
#include <linux/slab.h>
#include <linux/wait.h>
#include <linux/mm.h>
#include <linux/gfp.h>
#include <linux/fs.h>
#include <linux/file.h>
#include <linux/version.h>
#include <linux/semaphore.h>
#include <linux/interrupt.h>
#include <linux/cpumask.h>
#include <linux/rbtree.h>
#include <linux/timekeeping.h>
#include <asm/uaccess.h>
#include <asm/delay.h>
#include <asm/io.h>
#include <linux/syscalls.h>
#include <trace/events/sched.h>
#include <config.h>
#include "mcctrl.h"
#include <ihk/ihk_host_user.h>
#include <rusage.h>
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4, 11, 0)
#include <uapi/linux/sched/types.h>
#endif
#include <archdeps.h>
#include <arch-lock.h>
#include <uti.h>

#include <futex.h>
#include <mcctrl_rust.h>
#include <mc_jhash.h>
#include <arch-futex.h>

static int mcctrl_futex_atomic_access_ok_local(int *uaddr,
					       unsigned long size)
{
#ifdef __UACCESS__
	return access_ok(VERIFY_WRITE, uaddr, size);
#else
	(void)uaddr;
	(void)size;
	return 1;
#endif
}

static int mcctrl_futex_atomic_cmpxchg_inatomic_local(int *uaddr,
						      int oldval,
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

#define MCCTRL_FUTEX_X86_ATOMIC_OP1(insn, ret, oldval, uaddr, oparg) \
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

#define MCCTRL_FUTEX_X86_ATOMIC_OP2(insn, ret, oldval, uaddr, oparg) \
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

static int mcctrl_futex_atomic_op_inuser_local(int op, int *uaddr,
					       int oparg, int *oldval)
{
	int old = 0, ret, tem;

	switch (op) {
	case FUTEX_OP_SET:
		MCCTRL_FUTEX_X86_ATOMIC_OP1("xchgl %0, %2", ret, old,
					    uaddr, oparg);
		break;
	case FUTEX_OP_ADD:
		MCCTRL_FUTEX_X86_ATOMIC_OP1("lock; xaddl %0, %2", ret,
					    old, uaddr, oparg);
		break;
	case FUTEX_OP_OR:
		MCCTRL_FUTEX_X86_ATOMIC_OP2("orl %4, %3", ret, old,
					    uaddr, oparg);
		break;
	case FUTEX_OP_ANDN:
		MCCTRL_FUTEX_X86_ATOMIC_OP2("andl %4, %3", ret, old,
					    uaddr, oparg);
		break;
	case FUTEX_OP_XOR:
		MCCTRL_FUTEX_X86_ATOMIC_OP2("xorl %4, %3", ret, old,
					    uaddr, oparg);
		break;
	default:
		ret = -ENOSYS;
	}

	if (!ret)
		*oldval = old;

	return ret;
}

#ifdef MCCTRL_RUST_HELPERS
void mcctrl_futex_pagefault_disable_bridge(void)
{
	pagefault_disable();
}

void mcctrl_futex_pagefault_enable_bridge(void)
{
	pagefault_enable();
}

int mcctrl_futex_get_user_u32_bridge(uint32_t *dest, uint32_t *from)
{
	return __get_user(*dest, from);
}

int mcctrl_futex_atomic_access_ok_bridge(int *uaddr, unsigned long size)
{
	return mcctrl_futex_atomic_access_ok_local(uaddr, size);
}

int mcctrl_futex_atomic_cmpxchg_inatomic_bridge(int *uaddr, int oldval,
						int newval)
{
	return mcctrl_futex_atomic_cmpxchg_inatomic_local(uaddr, oldval,
							  newval);
}

int mcctrl_futex_atomic_op_inuser_bridge(int op, int *uaddr, int oparg,
					 int *oldval)
{
	return mcctrl_futex_atomic_op_inuser_local(op, uaddr, oparg, oldval);
}
#else
int get_futex_value_locked(uint32_t *dest, uint32_t *from)
{
	int ret;

	pagefault_disable();
	ret = __get_user(*dest, from);
	pagefault_enable();

	return ret ? -EFAULT : 0;
}

int futex_atomic_cmpxchg_inatomic(int *uaddr, int oldval, int newval)
{
	if (!mcctrl_futex_atomic_access_ok_local(uaddr, sizeof(int)))
		return -EFAULT;

	return mcctrl_futex_atomic_cmpxchg_inatomic_local(uaddr, oldval,
							  newval);
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

	if (!mcctrl_futex_atomic_access_ok_local(uaddr, sizeof(int)))
		return -EFAULT;

	if (op == FUTEX_OP_ANDN)
		oparg = ~oparg;
	ret = mcctrl_futex_atomic_op_inuser_local(op, uaddr, oparg, &oldval);

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
#endif

#ifdef DEBUG
#define dprintk printk
#else
#define dprintk(...)
#endif

#define NS_PER_SEC  1000000000UL

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
typedef struct timespec64 mcctrl_timespec_t;
#define MCCTRL_TIMESPEC_VALID(ts) timespec64_valid(ts)
#define MCCTRL_GET_REALTIME(ts) ktime_get_real_ts64(ts)
#define MCCTRL_GET_MONOTONIC(ts) ktime_get_ts64(ts)
#else
typedef struct timespec mcctrl_timespec_t;
#define MCCTRL_TIMESPEC_VALID(ts) timespec_valid(ts)
#define MCCTRL_GET_REALTIME(ts) getnstimeofday64(ts)
#define MCCTRL_GET_MONOTONIC(ts) ktime_get_ts64(ts)
#endif

static long uti_wait_event(void *_resp, unsigned long nsec_timeout)
{
	struct uti_futex_resp *resp = _resp;

	if (nsec_timeout) {
		return wait_event_interruptible_timeout(resp->wq, resp->done,
				nsecs_to_jiffies(nsec_timeout));
	} else {
		return wait_event_interruptible(resp->wq, resp->done);
	}
}

static int uti_clock_gettime(clockid_t clk_id, mcctrl_timespec_t *tp)
{
	int ret = 0;
	struct timespec64 ts64;

	dprintk("%s: clk_id=%x,REALTIME=%x,MONOTONIC=%x\n", __func__,
			clk_id, CLOCK_REALTIME, CLOCK_MONOTONIC);
	switch (clk_id) {
	case CLOCK_REALTIME:
		MCCTRL_GET_REALTIME(&ts64);
		tp->tv_sec = ts64.tv_sec;
		tp->tv_nsec = ts64.tv_nsec;
		dprintk("%s: CLOCK_REALTIME,%ld.%09ld\n", __func__,
				tp->tv_sec, tp->tv_nsec);
		break;
	case CLOCK_MONOTONIC:
		/* Do not use getrawmonotonic() because it returns different value than clock_gettime() */
		MCCTRL_GET_MONOTONIC(&ts64);
		tp->tv_sec = ts64.tv_sec;
		tp->tv_nsec = ts64.tv_nsec;
		dprintk("%s: CLOCK_MONOTONIC,%ld.%09ld\n", __func__,
				tp->tv_sec, tp->tv_nsec);
		break;
	default:
		ret = -EINVAL;
	}
	return ret;
}
/*
 * Hash buckets are shared by all the futex_keys that hash to the same
 * location.  Each key may have multiple futex_q structures, one for each task
 * waiting on a futex.
 */
struct futex_hash_bucket {
	_ihk_spinlock_t lock;
	struct mc_plist_head chain;
};

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

static inline
void put_futex_key(int fshared, union futex_key *key)
{
	drop_futex_key_refs(key);
}

/*
 * We hash on the keys returned from get_futex_key (see below).
 */
static struct futex_hash_bucket *hash_futex(
		union futex_key *key,
		struct futex_hash_bucket *futex_queue)
{
	uint32_t hash = mc_jhash2((uint32_t *)&key->both.word,
			  (sizeof(key->both.word)+sizeof(key->both.ptr))/4,
			  key->both.offset);
	return &futex_queue[hash & ((1 << FUTEX_HASHBITS)-1)];
}

/* The key must be already stored in q->key. */
static inline struct futex_hash_bucket *queue_lock(
		struct futex_q *q,
		struct futex_hash_bucket *futex_queue)
{
	struct futex_hash_bucket *hb;

	get_futex_key_refs(&q->key);
	hb = hash_futex(&q->key, futex_queue);
	q->lock_ptr = &hb->lock;

	ihk_mc_spinlock_lock_noirq(&hb->lock);

	return hb;
}

static inline void
queue_unlock(struct futex_q *q, struct futex_hash_bucket *hb)
{
	ihk_mc_spinlock_unlock_noirq(&hb->lock);
	drop_futex_key_refs(&q->key);
}

/*
 * Express the locking dependencies for lockdep:
 */
static inline void
double_lock_hb(struct futex_hash_bucket *hb1, struct futex_hash_bucket *hb2)
{
	if (hb1 <= hb2) {
		ihk_mc_spinlock_lock_noirq(&hb1->lock);
		if (hb1 < hb2)
			ihk_mc_spinlock_lock_noirq(&hb2->lock);
	} else { /* hb1 > hb2 */
		ihk_mc_spinlock_lock_noirq(&hb2->lock);
		ihk_mc_spinlock_lock_noirq(&hb1->lock);
	}
}

static inline void
double_unlock_hb(struct futex_hash_bucket *hb1, struct futex_hash_bucket *hb2)
{
	ihk_mc_spinlock_unlock_noirq(&hb1->lock);
	if (hb1 != hb2)
		ihk_mc_spinlock_unlock_noirq(&hb2->lock);
}

/* remote_page_fault for uti-futex */
static int uti_remote_page_fault(struct mcctrl_usrdata *usrdata,
			void *fault_addr, uint64_t reason,
			struct mcctrl_per_proc_data *ppd, int tid, int cpu)
{
	int error;
	struct ikc_scd_packet packet;

	/* Request page fault */
	packet.msg = SCD_MSG_REMOTE_PAGE_FAULT;
	packet.fault_address = (unsigned long)fault_addr;
	packet.fault_reason = reason;
	packet.fault_tid = tid;

	/* packet->target_cpu was set in rus_vm_fault if a thread was found */
	error = mcctrl_ikc_send_wait(usrdata->os, cpu, &packet,
				0, NULL, NULL, 0);
	if (error < 0) {
		pr_warn("%s: WARNING: failed to request uti remote page fault :%d\n",
			__func__, error);
	}

	return error;
}

struct rva_to_rpa_cache_node {
	struct rb_node node;
	unsigned long rva;
	unsigned long rpa;
};

#ifdef MCCTRL_RUST_HELPERS
static void *mcctrl_futex_rb_first_bridge(void *root)
{
	return rb_first((struct rb_root *)root);
}

static void mcctrl_futex_rb_erase_bridge(void *node, void *root)
{
	rb_erase((struct rb_node *)node, (struct rb_root *)root);
}

static void mcctrl_futex_rb_link_node_bridge(void *node, void *parent,
					     void *link)
{
	rb_link_node((struct rb_node *)node, (struct rb_node *)parent,
		     (struct rb_node **)link);
}

static void mcctrl_futex_rb_insert_color_bridge(void *node, void *root)
{
	rb_insert_color((struct rb_node *)node, (struct rb_root *)root);
}

static void mcctrl_futex_cache_free_bridge(void *ptr)
{
	kfree(ptr);
}
#endif

void futex_remove_process(struct mcctrl_per_proc_data *ppd)
{
#ifdef MCCTRL_RUST_HELPERS
	mcctrl_futex_remove_process_body_result(&ppd->rva_to_rpa_cache,
			mcctrl_futex_rb_first_bridge,
			mcctrl_futex_rb_erase_bridge,
			mcctrl_futex_cache_free_bridge);
#else
	struct rb_node *node;

	while ((node = rb_first(&ppd->rva_to_rpa_cache))) {
		struct rva_to_rpa_cache_node *cache_node;

		cache_node = container_of(node, struct rva_to_rpa_cache_node,
					  node);
		rb_erase(node, &ppd->rva_to_rpa_cache);
		kfree(cache_node);
	}
#endif
}

struct rva_to_rpa_cache_node *rva_to_rpa_cache_search(struct rb_root *root,
						      unsigned long rva)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_rva_to_rpa_cache_search_body_result(root, rva);
#else
	struct rb_node **iter = &root->rb_node, *parent = NULL;

	while (*iter) {
		struct rva_to_rpa_cache_node *inode =
			container_of(*iter, struct rva_to_rpa_cache_node, node);

		parent = *iter;

		if (rva == inode->rva) {
			return inode;
		}

		if (rva < inode->rva)
			iter = &((*iter)->rb_left);
		else
			iter = &((*iter)->rb_right);
	}

	return NULL;
#endif
}

int rva_to_rpa_cache_insert(struct rb_root *root,
			    struct rva_to_rpa_cache_node *cache_node)
{
#ifdef MCCTRL_RUST_HELPERS
	return mcctrl_rva_to_rpa_cache_insert_body_result(root, cache_node,
			mcctrl_futex_rb_link_node_bridge,
			mcctrl_futex_rb_insert_color_bridge);
#else
	struct rb_node **iter = &root->rb_node, *parent = NULL;

	while (*iter) {
		struct rva_to_rpa_cache_node *inode =
			container_of(*iter, struct rva_to_rpa_cache_node, node);

		parent = *iter;

		if (cache_node->rva == inode->rva)
			return -EINVAL;

		if (cache_node->rva < inode->rva)
			iter = &((*iter)->rb_left);
		else
			iter = &((*iter)->rb_right);
	}

	rb_link_node(&cache_node->node, parent, iter);
	rb_insert_color(&cache_node->node, root);

	return 0;
#endif
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
get_futex_key(uint32_t *uaddr, int fshared, union futex_key *key,
		struct uti_info *uti_info)
{
	unsigned long address = (unsigned long)uaddr;
	unsigned long phys, pgsize;
	void *mm = uti_info->vm;
	struct mcctrl_usrdata *usrdata;
	struct mcctrl_per_proc_data *ppd;
	int ret = 0, error = 0;
	struct rva_to_rpa_cache_node *cache_node;

	/*
	 * The futex address must be "naturally" aligned.
	 */
	key->both.offset = address % PAGE_SIZE;
	if (((address % sizeof(uint32_t)) != 0)) {
		ret = -EINVAL;
		goto out;
	}
	address -= key->both.offset;

	/*
	 * PROCESS_PRIVATE futexes are fast.
	 * As the mm cannot disappear under us and the 'key' only needs
	 * virtual address, we dont even have to find the underlying vma.
	 * Note : We do have to check 'uaddr' is a valid user address,
	 *        but access_ok() should be faster than find_vma()
	 */
	if (!fshared) {
		key->private.mm = mm;
		key->private.address = address;
		get_futex_key_refs(key);
		ret = 0;
		goto out;
	}

	key->both.offset |= FUT_OFF_MMSHARED;

	usrdata = ihk_host_os_get_usrdata((ihk_os_t)uti_info->os);
	if (!usrdata) {
		pr_err("%s: ERROR: mcctrl_usrdata not found\n", __func__);
		ret = -EINVAL;
		goto out;
	}

	ppd = mcctrl_get_per_proc_data(usrdata, task_tgid_vnr(current));
	if (!ppd) {
		pr_err("%s: ERROR: no per-process structure for PID %d\n",
				__func__, task_tgid_vnr(current));
		ret = -EINVAL;
		goto out;
	}

	/* cache because translate_rva_to_rpa calls smp_ihk_arch_dcache_flush
	 * via ihk_device_unmap_virtual
	 */
	cache_node = rva_to_rpa_cache_search(&ppd->rva_to_rpa_cache,
					     (unsigned long)uaddr);
	if (cache_node) {
		phys = cache_node->rpa;
		dprintk("%s: cache hit, rva: %lx, rpa: %lx\n",
			__func__, (unsigned long)uaddr, phys);
		goto found;
	}
retry_v2p:
	error = translate_rva_to_rpa((ihk_os_t)uti_info->os, ppd->rpgtable,
			(unsigned long)uaddr, &phys, &pgsize);
	if (error) {
		/* Check if we can fault in page */
		error = uti_remote_page_fault(usrdata, (void *)address,
				PF_POPULATE | PF_WRITE | PF_USER,
				ppd, uti_info->tid, uti_info->cpu);
		if (error) {
			pr_err("%s: ERROR: virt to phys translation failed\n",
					__func__);
			ret = -EFAULT;
			goto put_out;
		}

		goto retry_v2p;
	}

	cache_node = kmalloc(sizeof(struct rva_to_rpa_cache_node), GFP_KERNEL);
	if (!cache_node) {
		ret = -ENOMEM;
		goto put_out;
	}
	cache_node->rva = (unsigned long)uaddr;
	cache_node->rpa = phys;
	dprintk("%s: cache insert, rva: %lx, rpa: %lx\n",
		__func__, (unsigned long)uaddr, phys);
	ret = rva_to_rpa_cache_insert(&ppd->rva_to_rpa_cache, cache_node);
	if (ret) {
		pr_err("%s: error: cache entry found, rva: %lx, rpa: %lx\n",
		       __func__, (unsigned long)uaddr, phys);
		goto put_out;
	}

 found:
	key->shared.phys = (void *)phys;
	key->shared.pgoff = 0;

put_out:
	mcctrl_put_per_proc_data(ppd);

out:
	return ret;
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
static inline void queue_me(struct futex_q *q, struct futex_hash_bucket *hb,
			struct uti_info *uti_info)
{
	int prio;

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

	mc_plist_node_init(&q->list, prio);
#ifdef CONFIG_DEBUG_PI_LIST
	q->list.plist.spinlock = &hb->lock;
#endif
	mc_plist_add(&q->list, &hb->chain);
	q->task = (void *)uti_info->thread_va;
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
	_ihk_spinlock_t *lock_ptr;
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
		mc_plist_del(&q->list, &q->list.plist);

		ihk_mc_spinlock_unlock_noirq(lock_ptr);
		ret = 1;
	}

	drop_futex_key_refs(&q->key);
	return ret;
}

/*
 * Return 1 if two futex_keys are equal, 0 otherwise.
 */
static inline int match_futex(union futex_key *key1, union futex_key *key2)
{
	return (key1 && key2
		&& key1->both.word == key2->both.word
		&& key1->both.ptr == key2->both.ptr
		&& key1->both.offset == key2->both.offset);
}

/* Convert phys_addr to virt_addr on Linux */
static void futex_q_p2v(struct futex_q *q)
{
	q->th_spin_sleep = (void *)phys_to_virt(q->th_spin_sleep_pa);
	q->th_status = (void *)phys_to_virt(q->th_status_pa);
	q->th_spin_sleep_lock = (void *)phys_to_virt(q->th_spin_sleep_lock_pa);
	q->proc_status = (void *)phys_to_virt(q->proc_status_pa);
	q->proc_update_lock = (void *)phys_to_virt(q->proc_update_lock_pa);
	q->runq_lock = (void *)phys_to_virt(q->runq_lock_pa);
	q->clv_flags = (void *)phys_to_virt(q->clv_flags_pa);
}

#define CPU_FLAG_NEED_RESCHED	0x1U
#define CPU_FLAG_NEED_MIGRATE	0x2U
#define PS_RUNNING           0x1
#define PS_INTERRUPTIBLE     0x2
#define PS_UNINTERRUPTIBLE   0x4
#define PS_ZOMBIE            0x8
#define PS_EXITED            0x10
#define PS_STOPPED           0x20
#define PS_TRACED            0x40 /* Set to "not running" by a ptrace related event */
#define PS_STOPPING          0x80
#define PS_TRACING           0x100
#define PS_DELAY_STOPPED     0x200
#define PS_DELAY_TRACED      0x400

#define PS_NORMAL	(PS_INTERRUPTIBLE | PS_UNINTERRUPTIBLE)
static int uti_sched_wakeup_thread(struct futex_q *q, int valid_states,
		struct uti_info *uti_info)
{
	int status;
	unsigned long irqstate;

	futex_q_p2v(q);
	irqstate = ihk_mc_spinlock_lock(
			(_ihk_spinlock_t *)q->th_spin_sleep_lock);
	if (*(int *)q->th_spin_sleep == 1) {
		dprintk("%s: spin wakeup: cpu_id: %d\n", __func__, uti_info->cpu);
		status = 0;
	}
	*(int *)q->th_spin_sleep = 0;
	ihk_mc_spinlock_unlock(
			(_ihk_spinlock_t *)q->th_spin_sleep_lock, irqstate);

	irqstate = ihk_mc_spinlock_lock((_ihk_spinlock_t *)q->runq_lock);

	if (*(int *)q->th_status & valid_states) {
		mcs_rwlock_writer_lock_noirq(
			(mcs_rwlock_lock_t *)q->proc_update_lock);

		if (*(int *)q->proc_status != PS_EXITED) {
			*(int *)q->proc_status = PS_RUNNING;
		}

		mcs_rwlock_writer_unlock_noirq((mcs_rwlock_lock_t *)q->proc_update_lock);

		xchg4((int *)q->th_status, PS_RUNNING);
		status = 0;

		/* Make interrupt_exit() call schedule() */
		*(unsigned int *)q->clv_flags |= CPU_FLAG_NEED_RESCHED;
	}
	else {
		status = -EINVAL;
	}

	ihk_mc_spinlock_unlock((_ihk_spinlock_t *)q->runq_lock, irqstate);

	if (!status) {
		dprintk("%s: issuing IPI, thread->cpu_id=%d, intr_id: %d\n",
			__func__, uti_info->cpu, q->intr_id);

		ihk_os_issue_interrupt(uti_info->os, q->intr_id,
				       q->intr_vector);
	}

	return status;
}

/*
 * The hash bucket lock must be held when this is called.
 * Afterwards, the futex_q must not be accessed.
 */
static void wake_futex(struct futex_q *q, struct uti_info *uti_info)
{
	/*
	 * We set q->lock_ptr = NULL _before_ we wake up the task. If
	 * a non futex wake up happens on another CPU then the task
	 * might exit and p would dereference a non existing task
	 * struct. Prevent this by holding a reference on p across the
	 * wake up.
	 */

	mc_plist_del(&q->list, &q->list.plist);
	if (q->uti_futex_resp) {
		/* TODO: Add the case when a Linux thread waking up another Linux thread */
		pr_err("%s: ERROR: A Linux thread is waking up migrated-to-Linux thread\n", __func__);
	} else {
		dprintk("%s: waking up McKernel thread (tid %d)\n",
				__func__, uti_info->tid);
		uti_sched_wakeup_thread(q, PS_NORMAL, uti_info);
	}

	/*
	 * The waiting task can free the futex_q as soon as
	 * q->lock_ptr = NULL is written, without taking any locks. A
	 * memory barrier is required here to prevent the following
	 * store to lock_ptr from getting ahead of the plist_del.
	 */
	barrier();
	q->lock_ptr = NULL;
}

#ifdef MCCTRL_RUST_HELPERS
static int mcctrl_futex_get_key_for_body_bridge(unsigned long uaddr,
		int fshared, unsigned long key_addr, unsigned long ctx_addr)
{
	return get_futex_key((uint32_t *)uaddr, fshared,
			(union futex_key *)key_addr,
			(struct uti_info *)ctx_addr);
}

static unsigned long mcctrl_futex_hash_key_bridge(unsigned long key_addr,
		unsigned long queue_addr)
{
	return (unsigned long)hash_futex((union futex_key *)key_addr,
			(struct futex_hash_bucket *)queue_addr);
}

static unsigned long mcctrl_futex_wake_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((_ihk_spinlock_t *)lock_addr);
}

static void mcctrl_futex_wake_unlock_bridge(unsigned long lock_addr,
		unsigned long irqstate)
{
	ihk_mc_spinlock_unlock((_ihk_spinlock_t *)lock_addr, irqstate);
}

static void mcctrl_futex_hb_lock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((_ihk_spinlock_t *)lock_addr);
}

static void mcctrl_futex_hb_unlock_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_unlock_noirq((_ihk_spinlock_t *)lock_addr);
}

static void mcctrl_futex_put_key_bridge(int fshared, unsigned long key_addr)
{
	put_futex_key(fshared, (union futex_key *)key_addr);
}

static void mcctrl_futex_wake_entry_bridge(unsigned long q_addr,
		unsigned long ctx_addr)
{
	wake_futex((struct futex_q *)q_addr, (struct uti_info *)ctx_addr);
}
#endif

/*
 * Wake up waiters matching bitset queued on this futex (uaddr).
 */
static int futex_wake(uint32_t *uaddr, int fshared, int nr_wake,
		uint32_t bitset, struct uti_info *uti_info)
{
#ifdef MCCTRL_RUST_HELPERS
	union futex_key key = FUTEX_KEY_INIT;

	return mcctrl_futex_wake_body_result((unsigned long)uaddr, fshared,
			nr_wake, bitset, (unsigned long)&key,
			(unsigned long)uti_info->futex_queue,
			(unsigned long)uti_info,
			offsetof(struct futex_hash_bucket, lock),
			offsetof(struct futex_hash_bucket, chain),
			offsetof(struct futex_q, list),
			offsetof(struct futex_q, key),
			offsetof(struct futex_q, bitset),
			offsetof(union futex_key, both.word),
			offsetof(union futex_key, both.ptr),
			offsetof(union futex_key, both.offset),
			mcctrl_futex_get_key_for_body_bridge,
			mcctrl_futex_hash_key_bridge,
			mcctrl_futex_wake_lock_bridge,
			mcctrl_futex_wake_unlock_bridge,
			mcctrl_futex_put_key_bridge,
			mcctrl_futex_wake_entry_bridge);
#else
	struct futex_hash_bucket *hb;
	struct futex_q *this, *next;
	struct mc_plist_head *head;
	union futex_key key = FUTEX_KEY_INIT;
	int ret;
	unsigned long irqstate;

	if (!bitset) {
		return -EINVAL;
	}

	ret = get_futex_key(uaddr, fshared, &key, uti_info);
	if ((ret != 0)) {
		goto out;
	}

	hb = hash_futex(&key, uti_info->futex_queue);
	irqstate = ihk_mc_spinlock_lock(&hb->lock);
	head = &hb->chain;

	list_for_each_entry_safe(this, next, &head->node_list,
			list.plist.node_list) {
		if (match_futex(&this->key, &key)) {
			/* RIKEN: no pi state... */
			/* Check if one of the bits is set in both bitsets */
			if (!(this->bitset & bitset))
				continue;

			wake_futex(this, uti_info);
			if (++ret >= nr_wake)
				break;
		}
	}

	ihk_mc_spinlock_unlock(&hb->lock, irqstate);
	put_futex_key(fshared, &key);
out:
	return ret;
#endif
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

static int64_t futex_wait_queue_me(struct futex_hash_bucket *hb, struct futex_q *q,
				   uint64_t timeout, struct uti_info *uti_info)
{
	int64_t time_remain = 0;
	unsigned long irqstate;

	/*
	 * The task state is guaranteed to be set before another task can
	 * wake it.
	 * queue_me() calls spin_unlock() upon completion, serializing
	 * access to the hash list and forcing a memory barrier.
	 */
	xchg4((int *)uti_info->status, PS_INTERRUPTIBLE);

	/* Indicate spin sleep. Note that schedule_timeout() with
	 * idle_halt should use spin sleep because sleep with timeout
	 * is not implemented.
	 */
	if (!uti_info->mc_idle_halt || timeout) {
		irqstate = ihk_mc_spinlock_lock(
				(_ihk_spinlock_t *)uti_info->spin_sleep_lock);
		*(int *)uti_info->spin_sleep = 1;
		ihk_mc_spinlock_unlock(
				(_ihk_spinlock_t *)uti_info->spin_sleep_lock,
				irqstate);
	}

	queue_me(q, hb, uti_info);

	if (!mc_plist_node_empty(&q->list)) {
		dprintk("%s: tid: %d is trying to sleep, cpu: %d\n",
			__func__, uti_info->tid, ihk_ikc_get_processor_id());
		/* Note that the unit of timeout is nsec */
		time_remain = uti_wait_event(q->uti_futex_resp, timeout);

		/* Note that time_remain == 0 indicates contidion evaluated to false after the timeout elapsed */
		if (time_remain < 0) {
			if (time_remain == -ERESTARTSYS) { /* Interrupted by signal */
				dprintk("%s: DEBUG: wait_event returned -ERESTARTSYS\n", __func__);
			} else {
				pr_err("%s: ERROR: wait_event returned %lld\n", __func__, time_remain);
			}
		}
		dprintk("%s: tid: %d woken up, cpu: %d\n",
			__func__, uti_info->tid, ihk_ikc_get_processor_id());
	}

	/* This does not need to be serialized */
	*(int *)uti_info->status = PS_RUNNING;
	*(int *)uti_info->spin_sleep = 0;

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
			    struct futex_q *q, struct futex_hash_bucket **hb,
			    struct uti_info *uti_info)
{
	uint32_t uval;
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
	q->key = FUTEX_KEY_INIT;
	ret = get_futex_key(uaddr, fshared, &q->key, uti_info);
	if (ret != 0)
		return ret;

	*hb = queue_lock(q, (struct futex_hash_bucket *)uti_info->futex_queue);

	ret = get_futex_value_locked(&uval, uaddr);
	if (ret) {
		queue_unlock(q, *hb);
		put_futex_key(fshared, &q->key);
		return ret;
	}

	if (uval != val) {
		queue_unlock(q, *hb);
		ret = -EWOULDBLOCK;
	}

	if (ret)
		put_futex_key(fshared, &q->key);

	return ret;
}

#ifdef MCCTRL_RUST_HELPERS
static void *mcctrl_futex_uti_q_bridge(void *uti_info0)
{
	struct uti_info *uti_info = uti_info0;

	return uti_info->futex_q;
}

static void *mcctrl_futex_uti_resp_bridge(void *uti_info0)
{
	struct uti_info *uti_info = uti_info0;

	return uti_info->uti_futex_resp;
}

static int mcctrl_futex_current_cpu_bridge(void)
{
	return ihk_ikc_get_processor_id();
}

static void mcctrl_futex_prepare_wait_q_bridge(void *q0, uint32_t bitset,
		void *uti_futex_resp, int linux_cpu)
{
	struct futex_q *q = q0;

	q->bitset = bitset;
	q->requeue_pi_key = NULL;
	q->uti_futex_resp = uti_futex_resp;
	q->linux_cpu = linux_cpu;
}

static int mcctrl_futex_wait_setup_bridge(uint32_t *uaddr, uint32_t val,
		int fshared, void *q, void **hb, void *uti_info)
{
	struct futex_hash_bucket *bucket = NULL;
	int ret;

	ret = futex_wait_setup(uaddr, val, fshared, q, &bucket, uti_info);
	*hb = bucket;
	return ret;
}

static int64_t mcctrl_futex_wait_queue_bridge(void *hb, void *q,
		uint64_t timeout, void *uti_info)
{
	return futex_wait_queue_me(hb, q, timeout, uti_info);
}

static int mcctrl_futex_unqueue_bridge(void *q)
{
	return unqueue_me(q);
}

static void mcctrl_futex_put_q_key_bridge(int fshared, void *q0)
{
	struct futex_q *q = q0;

	put_futex_key(fshared, &q->key);
}

static void mcctrl_futex_wait_log_bridge(int stage, void *uti_info0)
{
	struct uti_info *uti_info = uti_info0;

	(void)uti_info;
	switch (stage) {
	case 0:
		dprintk("%s: tid=%d unqueued\n", "futex_wait",
				uti_info->tid);
		break;
	case 1:
		dprintk("%s: tid=%d timer expired\n", "futex_wait",
				uti_info->tid);
		break;
	case 2:
		dprintk("%s: tid=%d woken up by signal\n", "futex_wait",
				uti_info->tid);
		break;
	default:
		break;
	}
}
#endif

static int futex_wait(uint32_t __user *uaddr, int fshared,
		uint32_t val, uint64_t timeout, uint32_t bitset,
		int clockrt, struct uti_info *uti_info)
{
#ifdef MCCTRL_RUST_HELPERS
	(void)clockrt;
	return mcctrl_futex_wait_body_result(uaddr, fshared, val, timeout,
			bitset, uti_info, mcctrl_futex_uti_q_bridge,
			mcctrl_futex_uti_resp_bridge,
			mcctrl_futex_current_cpu_bridge,
			mcctrl_futex_prepare_wait_q_bridge,
			mcctrl_futex_wait_setup_bridge,
			mcctrl_futex_wait_queue_bridge,
			mcctrl_futex_unqueue_bridge,
			mcctrl_futex_put_q_key_bridge,
			mcctrl_futex_wait_log_bridge);
#else
	struct futex_hash_bucket *hb;
	int64_t time_remain;
	struct futex_q *q = NULL;
	int ret;

	if (!bitset)
		return -EINVAL;

	q = (struct futex_q *)uti_info->futex_q;

	q->bitset = bitset;
	q->requeue_pi_key = NULL;
	q->uti_futex_resp = uti_info->uti_futex_resp;
	q->linux_cpu = ihk_ikc_get_processor_id();

retry:
	/* Prepare to wait on uaddr. */
	ret = futex_wait_setup(uaddr, val, fshared, q, &hb, uti_info);
	if (ret) {
		goto out;
	}

	/* queue_me and wait for wakeup, timeout, or a signal. */
	time_remain = futex_wait_queue_me(hb, q, timeout, uti_info);

	/* If we were woken (and unqueued), we succeeded, whatever. */
	ret = 0;
	if (!unqueue_me(q)) {
		dprintk("%s: tid=%d unqueued\n", __func__, uti_info->tid);
		goto out_put_key;
	}
	ret = -ETIMEDOUT;

	/* RIKEN: timer expired case (indicated by !time_remain) */
	if (timeout && !time_remain) {
		dprintk("%s: tid=%d timer expired\n", __func__, uti_info->tid);
		goto out_put_key;
	}

	/* RIKEN: futex_wait_queue_me() returns -ERESTARTSYS when waiting on Linux CPU and woken up by signal */
	if (time_remain == -ERESTARTSYS) {
		ret = -EINTR;
		dprintk("%s: tid=%d woken up by signal\n", __func__,
				uti_info->tid);
		goto out_put_key;
	}

	/* RIKEN: no signals */
	put_futex_key(fshared, &q->key);

	goto retry;

out_put_key:
	put_futex_key(fshared, &q->key);
out:
	return ret;
#endif
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

	/*
	 * If key1 and key2 hash to the same bucket, no need to
	 * requeue.
	 */
	if (&hb1->chain != &hb2->chain) {
		mc_plist_del(&q->list, &hb1->chain);
		mc_plist_add(&q->list, &hb2->chain);
		q->lock_ptr = &hb2->lock;
#ifdef CONFIG_DEBUG_PI_LIST
		q->list.plist.spinlock = &hb2->lock;
#endif
	}
	get_futex_key_refs(key2);
	q->key = *key2;
}

#ifdef MCCTRL_RUST_HELPERS
struct mcctrl_futex_requeue_ctx {
	struct futex_hash_bucket *hb1;
	struct futex_hash_bucket *hb2;
	union futex_key *key2;
	struct uti_info *uti_info;
};

static void mcctrl_futex_drop_key_refs_bridge(unsigned long key_addr)
{
	drop_futex_key_refs((union futex_key *)key_addr);
}

static int mcctrl_futex_get_value_bridge(unsigned long value_addr,
		unsigned long uaddr)
{
	return get_futex_value_locked((uint32_t *)value_addr,
			(uint32_t *)uaddr);
}

static void mcctrl_futex_requeue_wake_bridge(unsigned long q_addr,
		unsigned long ctx_addr)
{
	struct mcctrl_futex_requeue_ctx *ctx =
		(struct mcctrl_futex_requeue_ctx *)ctx_addr;

	wake_futex((struct futex_q *)q_addr, ctx->uti_info);
}

static void mcctrl_futex_requeue_move_bridge(unsigned long q_addr,
		unsigned long ctx_addr)
{
	struct mcctrl_futex_requeue_ctx *ctx =
		(struct mcctrl_futex_requeue_ctx *)ctx_addr;

	requeue_futex((struct futex_q *)q_addr, ctx->hb1, ctx->hb2,
			ctx->key2);
}

static int mcctrl_futex_atomic_op_bridge(int op, unsigned long uaddr)
{
	return futex_atomic_op_inuser(op, (int *)uaddr);
}
#endif

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
		int requeue_pi, struct uti_info *uti_info)
{
#ifdef MCCTRL_RUST_HELPERS
	union futex_key key1 = FUTEX_KEY_INIT, key2 = FUTEX_KEY_INIT;
	struct mcctrl_futex_requeue_ctx ctx = {
		.uti_info = uti_info,
	};

	(void)requeue_pi;
	return mcctrl_futex_requeue_body_result((unsigned long)uaddr1,
			fshared, (unsigned long)uaddr2, nr_wake, nr_requeue,
			(unsigned long)cmpval, (unsigned long)&key1,
			(unsigned long)&key2, (unsigned long)&ctx,
			(unsigned long)uti_info->futex_queue,
			offsetof(struct futex_hash_bucket, lock),
			offsetof(struct futex_hash_bucket, chain),
			offsetof(struct futex_q, list),
			offsetof(struct futex_q, key),
			offsetof(union futex_key, both.word),
			offsetof(union futex_key, both.ptr),
			offsetof(union futex_key, both.offset),
			offsetof(struct mcctrl_futex_requeue_ctx, hb1),
			offsetof(struct mcctrl_futex_requeue_ctx, hb2),
			offsetof(struct mcctrl_futex_requeue_ctx, key2),
			mcctrl_futex_get_key_for_body_bridge,
			mcctrl_futex_hash_key_bridge,
			mcctrl_futex_hb_lock_bridge,
			mcctrl_futex_hb_unlock_bridge,
			mcctrl_futex_get_value_bridge,
			mcctrl_futex_put_key_bridge,
			mcctrl_futex_drop_key_refs_bridge,
			mcctrl_futex_requeue_wake_bridge,
			mcctrl_futex_requeue_move_bridge);
#else
	union futex_key key1 = FUTEX_KEY_INIT, key2 = FUTEX_KEY_INIT;
	int drop_count = 0, task_count = 0, ret;
	struct futex_hash_bucket *hb1, *hb2;
	struct mc_plist_head *head1;
	struct futex_q *this, *next;

	ret = get_futex_key(uaddr1, fshared, &key1, uti_info);
	if ((ret != 0))
		goto out;
	ret = get_futex_key(uaddr2, fshared, &key2, uti_info);
	if ((ret != 0))
		goto out_put_key1;

	hb1 = hash_futex(&key1, uti_info->futex_queue);
	hb2 = hash_futex(&key2, uti_info->futex_queue);

	double_lock_hb(hb1, hb2);

	if (cmpval != NULL) {
		uint32_t curval;

		ret = get_futex_value_locked(&curval, uaddr1);

		if (curval != *cmpval) {
			ret = -EAGAIN;
			goto out_unlock;
		}
	}

	head1 = &hb1->chain;
	list_for_each_entry_safe(this, next, &head1->node_list,
			list.plist.node_list) {
		if (task_count - nr_wake >= nr_requeue)
			break;

		if (!match_futex(&this->key, &key1))
			continue;

		/*
		 * Wake nr_wake waiters.  For requeue_pi, if we acquired the
		 * lock, we already woke the top_waiter.  If not, it will be
		 * woken by futex_unlock_pi().
		 */
		/* RIKEN: no requeue_pi at this moment */
		if (++task_count <= nr_wake) {
			wake_futex(this, uti_info);
			continue;
		}

		requeue_futex(this, hb1, hb2, &key2);
		drop_count++;
	}

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
#endif
}

/*
 * Wake up all waiters hashed on the physical page that is mapped
 * to this virtual address:
 */
static int
futex_wake_op(uint32_t *uaddr1, int fshared, uint32_t *uaddr2,
			  int nr_wake, int nr_wake2, int op,
			  struct uti_info *uti_info)
{
#ifdef MCCTRL_RUST_HELPERS
	union futex_key key1 = FUTEX_KEY_INIT, key2 = FUTEX_KEY_INIT;

	return mcctrl_futex_wake_op_body_result((unsigned long)uaddr1,
			fshared, (unsigned long)uaddr2, nr_wake, nr_wake2,
			op, (unsigned long)&key1, (unsigned long)&key2,
			(unsigned long)uti_info->futex_queue,
			(unsigned long)uti_info,
			offsetof(struct futex_hash_bucket, lock),
			offsetof(struct futex_hash_bucket, chain),
			offsetof(struct futex_q, list),
			offsetof(struct futex_q, key),
			offsetof(struct futex_q, bitset),
			offsetof(union futex_key, both.word),
			offsetof(union futex_key, both.ptr),
			offsetof(union futex_key, both.offset),
			mcctrl_futex_get_key_for_body_bridge,
			mcctrl_futex_hash_key_bridge,
			mcctrl_futex_hb_lock_bridge,
			mcctrl_futex_hb_unlock_bridge,
			mcctrl_futex_atomic_op_bridge,
			mcctrl_futex_put_key_bridge,
			mcctrl_futex_wake_entry_bridge);
#else
	union futex_key key1 = FUTEX_KEY_INIT, key2 = FUTEX_KEY_INIT;
	struct futex_hash_bucket *hb1, *hb2;
	struct mc_plist_head *head;
	struct futex_q *this, *next;
	int ret, op_ret;

retry:
	ret = get_futex_key(uaddr1, fshared, &key1, uti_info);
	if ((ret != 0))
		goto out;
	ret = get_futex_key(uaddr2, fshared, &key2, uti_info);
	if ((ret != 0))
		goto out_put_key1;

	hb1 = hash_futex(&key1, uti_info->futex_queue);
	hb2 = hash_futex(&key2, uti_info->futex_queue);

retry_private:
	double_lock_hb(hb1, hb2);
	op_ret = futex_atomic_op_inuser(op, (int *)uaddr2);
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

	list_for_each_entry_safe(this, next, &head->node_list,
			list.plist.node_list) {
		if (match_futex(&this->key, &key1)) {
			wake_futex(this, uti_info);
			if (++ret >= nr_wake)
				break;
		}
	}

	if (op_ret > 0) {
		head = &hb2->chain;

		op_ret = 0;
		list_for_each_entry_safe(this, next, &head->node_list,
				list.plist.node_list) {
			if (match_futex(&this->key, &key2)) {
				wake_futex(this, uti_info);
				if (++op_ret >= nr_wake2)
					break;
			}
		}
		ret += op_ret;
	}

	double_unlock_hb(hb1, hb2);
out_put_keys:
	put_futex_key(fshared, &key2);
out_put_key1:
	put_futex_key(fshared, &key1);
out:
	return ret;
#endif
}

#ifndef MCCTRL_RUST_HELPERS
static int futex(uint32_t *uaddr, int op, uint32_t val, uint64_t timeout,
		uint32_t *uaddr2, uint32_t val2, uint32_t val3, int fshared,
		struct uti_info *uti_info)
{
	int clockrt, ret = -ENOSYS;
	int cmd = mcctrl_futex_cmd(op);


	clockrt = mcctrl_futex_clock_realtime(op);
	if (clockrt && !mcctrl_futex_realtime_cmd_valid(cmd))
		return -ENOSYS;

	switch (cmd) {
	case FUTEX_WAIT:
		val3 = FUTEX_BITSET_MATCH_ANY;
	case FUTEX_WAIT_BITSET:
		ret = futex_wait(uaddr, fshared, val, timeout,
				val3, clockrt, uti_info);
		break;
	case FUTEX_WAKE:
		val3 = FUTEX_BITSET_MATCH_ANY;
	case FUTEX_WAKE_BITSET:
		ret = futex_wake(uaddr, fshared, val, val3, uti_info);
		break;
	case FUTEX_REQUEUE:
		ret = futex_requeue(uaddr, fshared, uaddr2, val,
				val2, NULL, 0, uti_info);
		break;
	case FUTEX_CMP_REQUEUE:
		ret = futex_requeue(uaddr, fshared, uaddr2, val,
				val2, NULL, 0, uti_info);
		break;
	case FUTEX_WAKE_OP:
		ret = futex_wake_op(uaddr, fshared, uaddr2, val,
				val2, val3, uti_info);
		break;
	/* RIKEN: these calls are not supported for now.
	case FUTEX_LOCK_PI:
		if (futex_cmpxchg_enabled)
			ret = futex_lock_pi(uaddr, fshared, val, timeout, 0);
		break;
	case FUTEX_UNLOCK_PI:
		if (futex_cmpxchg_enabled)
			ret = futex_unlock_pi(uaddr, fshared);
		break;
	case FUTEX_TRYLOCK_PI:
		if (futex_cmpxchg_enabled)
			ret = futex_lock_pi(uaddr, fshared, 0, timeout, 1);
		break;
	case FUTEX_WAIT_REQUEUE_PI:
		val3 = FUTEX_BITSET_MATCH_ANY;
		ret = futex_wait_requeue_pi(uaddr, fshared, val, timeout, val3,
						clockrt, uaddr2);
		break;
	case FUTEX_CMP_REQUEUE_PI:
		ret = futex_requeue(uaddr, fshared, uaddr2, val, val2, &val3,
					1);
		break;
	*/
	default:
		pr_warn("%s: invalid cmd: %d\n", __func__, cmd);
		ret = -ENOSYS;
	}
	return ret;
}
#endif

#ifdef MCCTRL_RUST_HELPERS
void mcctrl_futex_set_resp_bridge(struct uti_info *uti_info,
		void *uti_futex_resp)
{
	uti_info->uti_futex_resp = uti_futex_resp;
}

int mcctrl_futex_timeout_bridge(unsigned long utime_addr, int op, int flags,
		uint64_t *timeout)
{
	mcctrl_timespec_t *utime = (mcctrl_timespec_t *)utime_addr;
	mcctrl_timespec_t ts;
	int ret;

	if (copy_from_user(&ts, utime, sizeof(ts)) != 0) {
		return -EFAULT;
	}

	dprintk("%s: utime=%ld.%09ld\n", __func__, ts.tv_sec, ts.tv_nsec);
	if (!MCCTRL_TIMESPEC_VALID(&ts)) {
		return -EINVAL;
	}

	if (op == FUTEX_WAIT_BITSET) {
		mcctrl_timespec_t ats;

		ret = uti_clock_gettime((flags & FUTEX_CLOCK_REALTIME) ?
				CLOCK_REALTIME : CLOCK_MONOTONIC, &ats);
		if (ret) {
			return ret;
		}

		dprintk("%s: ats=%ld.%09ld\n", __func__,
				ats.tv_sec, ats.tv_nsec);
		*timeout = (ts.tv_sec * NS_PER_SEC + ts.tv_nsec) -
			(ats.tv_sec * NS_PER_SEC + ats.tv_nsec);
	} else {
		*timeout = ts.tv_sec * NS_PER_SEC + ts.tv_nsec;
	}

	return 0;
}

static int mcctrl_futex_wait_bridge(uint32_t *uaddr, int fshared,
		uint32_t val, uint64_t timeout, uint32_t bitset, int clockrt,
		void *uti_info)
{
	return futex_wait(uaddr, fshared, val, timeout, bitset, clockrt,
			uti_info);
}

static int mcctrl_futex_wake_bridge(uint32_t *uaddr, int fshared,
		int nr_wake, uint32_t bitset, void *uti_info)
{
	return futex_wake(uaddr, fshared, nr_wake, bitset, uti_info);
}

static int mcctrl_futex_requeue_bridge(uint32_t *uaddr1, int fshared,
		uint32_t *uaddr2, int nr_wake, int nr_requeue,
		uint32_t *cmpval, int requeue_pi, void *uti_info)
{
	return futex_requeue(uaddr1, fshared, uaddr2, nr_wake, nr_requeue,
			cmpval, requeue_pi, uti_info);
}

static int mcctrl_futex_wake_op_bridge(uint32_t *uaddr1, int fshared,
		uint32_t *uaddr2, int nr_wake, int nr_wake2, int op,
		void *uti_info)
{
	return futex_wake_op(uaddr1, fshared, uaddr2, nr_wake, nr_wake2,
			op, uti_info);
}

static void mcctrl_futex_invalid_cmd_bridge(int cmd)
{
	pr_warn("%s: invalid cmd: %d\n", "futex", cmd);
}

int mcctrl_futex_dispatch_bridge(uint32_t *uaddr, int op, uint32_t val,
		uint64_t timeout, uint32_t *uaddr2, uint32_t val2,
		uint32_t val3, int fshared, struct uti_info *uti_info)
{
	return mcctrl_futex_dispatch_body_result(uaddr, op, val, timeout,
			uaddr2, val2, val3, fshared, uti_info,
			mcctrl_futex_wait_bridge, mcctrl_futex_wake_bridge,
			mcctrl_futex_requeue_bridge,
			mcctrl_futex_wake_op_bridge,
			mcctrl_futex_invalid_cmd_bridge);
}
#else
long do_futex(int n, unsigned long arg0, unsigned long arg1,
			  unsigned long arg2, unsigned long arg3,
			  unsigned long arg4, unsigned long arg5,
			  struct uti_info *uti_info,
			  void *uti_futex_resp)
{
	uint64_t timeout = 0; // No timeout
	uint32_t val2 = 0;
	int fshared = 1;
	int ret = 0;

	uint32_t *uaddr = (uint32_t *)arg0;
	int op = (int)arg1;
	uint32_t val = (uint32_t)arg2;
	mcctrl_timespec_t *utime = (mcctrl_timespec_t *)arg3;
	mcctrl_timespec_t ts;
	uint32_t *uaddr2 = (uint32_t *)arg4;
	uint32_t val3 = (uint32_t)arg5;
	int flags = op;

	/* Fill in uti_futex_resp */
	uti_info->uti_futex_resp = uti_futex_resp;

	/* Cross-address space futex? */
	if (mcctrl_futex_is_private(op)) {
		fshared = 0;
	}
	op = mcctrl_futex_cmd(op);

	dprintk("futex op=[%x, %s],uaddr=%lx, val=%x, utime=%p, uaddr2=%p, val3=%x, shared: %d\n",
			flags,
			mcctrl_futex_op_label(op),
			(unsigned long)uaddr, val, utime, uaddr2, val3, fshared);

	if (utime && mcctrl_futex_wait_uses_timeout(op)) {
		if (copy_from_user(&ts, utime, sizeof(ts)) != 0) {
			return -EFAULT;
		}

		dprintk("%s: utime=%ld.%09ld\n", __func__, ts.tv_sec, ts.tv_nsec);
		if (!MCCTRL_TIMESPEC_VALID(&ts)) {
			return -EINVAL;
		}

	if (op == FUTEX_WAIT_BITSET) { /* User passed absolute time */
		mcctrl_timespec_t ats;

			ret = uti_clock_gettime((flags & FUTEX_CLOCK_REALTIME) ?
					CLOCK_REALTIME : CLOCK_MONOTONIC, &ats);
			if (ret) {
				return ret;
			}
			dprintk("%s: ats=%ld.%09ld\n", __func__, ats.tv_sec, ats.tv_nsec);
			/* Use nsec for UTI case */
			timeout = (ts.tv_sec * NS_PER_SEC + ts.tv_nsec) -
				(ats.tv_sec * NS_PER_SEC + ats.tv_nsec);
		} else { /* User passed relative time */
			/* Use nsec for UTI case */
			timeout = (ts.tv_sec * NS_PER_SEC + ts.tv_nsec);
		}
	}

	/* Requeue parameter in 'utime' if op == FUTEX_CMP_REQUEUE.
	 * number of waiters to wake in 'utime' if op == FUTEX_WAKE_OP. */
	if (mcctrl_futex_arg3_is_val2(op)) {
		val2 = (uint32_t) (unsigned long) arg3;
	}

	ret = futex(uaddr, op, val, timeout, uaddr2,
			val2, val3, fshared, uti_info);

	dprintk("futex op=[%x, %s],uaddr=%lx, val=%x, utime=%p, uaddr2=%p, val3=%x, shared: %d, ret: %d\n",
			op,
			mcctrl_futex_op_label(op),
			(unsigned long)uaddr, val, utime, uaddr2, val3, fshared, ret);

	return ret;
}
#endif
