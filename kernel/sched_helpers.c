/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <ihk/atomic.h>
#include <lwk/compiler.h>
#include <plist.h>
#include <sched_helpers.h>

#define PAGE_SIZE 4096UL
#define FUTEX_WAIT 0
#define FUTEX_WAKE 1
#define FUTEX_REQUEUE 3
#define FUTEX_CMP_REQUEUE 4
#define FUTEX_WAKE_OP 5
#define FUTEX_WAIT_BITSET 9
#define FUTEX_WAKE_BITSET 10
#define FUTEX_WAIT_REQUEUE_PI 11
#define FUTEX_PRIVATE_FLAG 128
#define FUTEX_CLOCK_REALTIME 256
#define FUTEX_BITSET_MATCH_ANY 0xffffffffU

#ifndef MCKERNEL_RUST_SCHED_RUNTIME_HELPERS

static inline void init_list_head_addr(unsigned long list_addr)
{
	*(unsigned long *)list_addr = list_addr;
	*(unsigned long *)(list_addr + sizeof(unsigned long)) = list_addr;
}

int futex_hash_bucket_table_init_result(unsigned long buckets_addr,
					int bucket_count,
					unsigned long bucket_stride,
					unsigned long lock_offset,
					unsigned long lock_word_offset,
					unsigned long chain_offset,
					unsigned long prio_list_offset,
					unsigned long node_list_offset,
					unsigned long debug_spinlock_offset,
					unsigned long debug_rawlock_offset)
{
	if (bucket_count < 0 || bucket_stride == 0)
		return -EINVAL;
	if (bucket_count && !buckets_addr)
		return -EINVAL;

	for (int i = 0; i < bucket_count; i++) {
		unsigned long bucket = buckets_addr + (bucket_stride * i);
		unsigned long lock_addr = bucket + lock_offset;
		unsigned long chain_addr = bucket + chain_offset;
		unsigned long prio_list_addr = chain_addr + prio_list_offset;
		unsigned long node_list_addr = chain_addr + node_list_offset;

		*(unsigned int *)(lock_addr + lock_word_offset) = 0;
		init_list_head_addr(prio_list_addr);
		init_list_head_addr(node_list_addr);

		if (debug_spinlock_offset)
			*(unsigned long *)(chain_addr + debug_spinlock_offset) =
				lock_addr;
		if (debug_rawlock_offset)
			*(unsigned long *)(chain_addr + debug_rawlock_offset) = 0;
	}

	return bucket_count;
}

int futex_init_table_result(unsigned long queues_slot_addr, int hashbits,
			    unsigned long bucket_stride, int alloc_flag,
			    futex_alloc_fn_t alloc_fn,
			    unsigned long lock_offset,
			    unsigned long lock_word_offset,
			    unsigned long chain_offset,
			    unsigned long prio_list_offset,
			    unsigned long node_list_offset,
			    unsigned long debug_spinlock_offset,
			    unsigned long debug_rawlock_offset)
{
	unsigned long buckets_addr;
	unsigned long bucket_count;
	unsigned long bytes;

	if (!queues_slot_addr || hashbits < 0 || !bucket_stride || !alloc_fn)
		return -EINVAL;
	if ((unsigned long)hashbits >= sizeof(unsigned long) * 8)
		return -EINVAL;
	bucket_count = 1UL << hashbits;
	if (bucket_count > ((unsigned long)-1) / bucket_stride)
		return -EINVAL;
	bytes = bucket_count * bucket_stride;

	buckets_addr = alloc_fn(bytes, alloc_flag);
	*(unsigned long *)queues_slot_addr = buckets_addr;
	return futex_hash_bucket_table_init_result(buckets_addr,
			(int)bucket_count, bucket_stride, lock_offset,
			lock_word_offset, chain_offset, prio_list_offset,
			node_list_offset, debug_spinlock_offset,
			debug_rawlock_offset);
}

unsigned long futex_hash_bucket_result(unsigned long key_addr,
				       unsigned long queues_addr,
				       int hashbits,
				       unsigned long bucket_stride,
				       futex_hash_fn_t hash_fn)
{
	unsigned long bucket_count;
	unsigned long hash;

	if (!key_addr || !queues_addr || hashbits < 0 ||
			!bucket_stride || !hash_fn)
		return 0;
	if ((unsigned long)hashbits >= sizeof(unsigned long) * 8)
		return 0;

	bucket_count = 1UL << hashbits;
	hash = hash_fn(key_addr);
	if ((hash & (bucket_count - 1)) >
			((unsigned long)-1 - queues_addr) / bucket_stride)
		return 0;

	return queues_addr + bucket_stride * (hash & (bucket_count - 1));
}

int futex_dispatch_result(int op, unsigned long uaddr, uint32_t val,
			  uint64_t timeout, unsigned long uaddr2,
			  uint32_t val2, uint32_t val3, int fshared,
			  futex_dispatch_wait_fn_t wait_fn,
			  futex_dispatch_wake_fn_t wake_fn,
			  futex_dispatch_requeue_fn_t requeue_fn,
			  futex_dispatch_wake_op_fn_t wake_op_fn,
			  futex_dispatch_invalid_fn_t invalid_fn)
{
	int clockrt;
	int cmd;

	cmd = op & ~(FUTEX_PRIVATE_FLAG | FUTEX_CLOCK_REALTIME);
	clockrt = op & FUTEX_CLOCK_REALTIME;
	if (clockrt && cmd != FUTEX_WAIT_BITSET &&
			cmd != FUTEX_WAIT_REQUEUE_PI)
		return -ENOSYS;

	switch (cmd) {
	case FUTEX_WAIT:
		return wait_fn ? wait_fn(uaddr, fshared, val, timeout,
				FUTEX_BITSET_MATCH_ANY, clockrt) : -ENOSYS;
	case FUTEX_WAIT_BITSET:
		return wait_fn ? wait_fn(uaddr, fshared, val, timeout, val3,
				clockrt) : -ENOSYS;
	case FUTEX_WAKE:
		return wake_fn ? wake_fn(uaddr, fshared, val,
				FUTEX_BITSET_MATCH_ANY) : -ENOSYS;
	case FUTEX_WAKE_BITSET:
		return wake_fn ? wake_fn(uaddr, fshared, val, val3) : -ENOSYS;
	case FUTEX_REQUEUE:
		return requeue_fn ? requeue_fn(uaddr, fshared, uaddr2, val,
				val2, 0, 0, 0) : -ENOSYS;
	case FUTEX_CMP_REQUEUE:
		return requeue_fn ? requeue_fn(uaddr, fshared, uaddr2, val,
				val2, 1, val3, 0) : -ENOSYS;
	case FUTEX_WAKE_OP:
		return wake_op_fn ? wake_op_fn(uaddr, fshared, uaddr2, val,
				val2, val3) : -ENOSYS;
	default:
		if (invalid_fn)
			invalid_fn(cmd);
		return -ENOSYS;
	}
}

uint64_t timer_spin_sleep_remaining_result(uint64_t timeout, uint64_t elapsed)
{
	return elapsed < timeout ? timeout - elapsed : 1;
}

int timer_runq_should_schedule_result(int runq_len)
{
	return runq_len > 1;
}

uint64_t timer_after_spin_remaining_result(uint64_t timeout,
					   uint64_t loop_timeout)
{
	return timeout < loop_timeout ? 0 : timeout - loop_timeout;
}

uint64_t timer_after_tick_remaining_result(uint64_t timeout,
					   uint64_t loop_timeout)
{
	uint64_t remaining = timeout - loop_timeout;

	return remaining < loop_timeout ? 0 : remaining;
}

int futex_key_match_result(int has_key1, int has_key2,
			   unsigned long word1, unsigned long ptr1,
			   unsigned long offset1, unsigned long word2,
			   unsigned long ptr2, unsigned long offset2)
{
	return has_key1 && has_key2 &&
		word1 == word2 && ptr1 == ptr2 && offset1 == offset2;
}

int futex_key_prepare_result(unsigned long address, int fshared,
			     unsigned long *basep, unsigned long *offsetp,
			     int *privatep)
{
	unsigned long offset = address % PAGE_SIZE;

	if ((address % sizeof(unsigned int)) != 0)
		return -EINVAL;

	if (basep)
		*basep = address - offset;
	if (offsetp)
		*offsetp = offset;
	if (privatep)
		*privatep = !fshared;

	return 0;
}

int futex_wake_bitset_valid_result(unsigned int bitset)
{
	return bitset != 0;
}

int futex_waiter_matches_bitset_result(unsigned int waiter_bitset,
				       unsigned int requested_bitset)
{
	return (waiter_bitset & requested_bitset) != 0;
}

int futex_wake_limit_reached_result(int woken, int nr_wake)
{
	return woken >= nr_wake;
}

int futex_wake_scan_result(unsigned long chain_addr,
			   unsigned long q_list_offset,
			   unsigned long q_key_offset,
			   unsigned long q_bitset_offset,
			   unsigned long key_word_offset,
			   unsigned long key_ptr_offset,
			   unsigned long key_offset_offset,
			   unsigned long target_word,
			   unsigned long target_ptr,
			   int target_offset,
			   unsigned int requested_bitset,
			   int use_bitset,
			   int nr_wake,
			   futex_wake_scan_fn_t wake_fn)
{
	struct plist_head *chain = (struct plist_head *)chain_addr;
	struct list_head *head;
	struct list_head *pos;
	struct list_head *next;
	int woken = 0;

	if (!chain || !wake_fn)
		return 0;

	head = &chain->node_list;
	for (pos = head->next, next = pos->next; pos != head;
			pos = next, next = pos->next) {
		unsigned long q_addr;
		unsigned long key_addr;

		q_addr = (unsigned long)container_of(pos,
				struct plist_node, plist.node_list);
		q_addr -= q_list_offset;
		key_addr = q_addr + q_key_offset;

		if (!futex_key_match_result(1, 1,
					*(unsigned long *)(key_addr +
						key_word_offset),
					*(unsigned long *)(key_addr +
						key_ptr_offset),
					*(int *)(key_addr +
						key_offset_offset),
					target_word, target_ptr,
					target_offset))
			continue;

		if (use_bitset && !futex_waiter_matches_bitset_result(
					*(unsigned int *)(q_addr +
						q_bitset_offset),
					requested_bitset))
			continue;

		wake_fn(q_addr);
		if (futex_wake_limit_reached_result(++woken, nr_wake))
			break;
	}

	return woken;
}

int futex_requeue_should_move_result(unsigned long source_chain,
				     unsigned long target_chain)
{
	return source_chain != target_chain;
}

int futex_requeue_loop_done_result(int task_count, int nr_wake,
				   int nr_requeue)
{
	return ((long long)task_count - nr_wake) >= nr_requeue;
}

int futex_requeue_should_wake_result(int task_count, int nr_wake)
{
	return task_count <= nr_wake;
}

int futex_requeue_scan_result(unsigned long chain_addr,
			      unsigned long q_list_offset,
			      unsigned long q_key_offset,
			      unsigned long key_word_offset,
			      unsigned long key_ptr_offset,
			      unsigned long key_offset_offset,
			      unsigned long target_word,
			      unsigned long target_ptr,
			      int target_offset,
			      int nr_wake,
			      int nr_requeue,
			      int *drop_countp,
			      futex_requeue_scan_fn_t wake_fn,
			      futex_requeue_scan_fn_t requeue_fn,
			      unsigned long ctx_addr)
{
	struct plist_head *chain = (struct plist_head *)chain_addr;
	struct list_head *head;
	struct list_head *pos;
	struct list_head *next;
	int task_count = 0;
	int drop_count = 0;

	if (drop_countp)
		*drop_countp = 0;
	if (!chain || !wake_fn || !requeue_fn)
		return 0;

	head = &chain->node_list;
	for (pos = head->next, next = pos->next; pos != head;
			pos = next, next = pos->next) {
		unsigned long q_addr;
		unsigned long key_addr;

		if (futex_requeue_loop_done_result(task_count, nr_wake,
					nr_requeue))
			break;

		q_addr = (unsigned long)container_of(pos,
				struct plist_node, plist.node_list);
		q_addr -= q_list_offset;
		key_addr = q_addr + q_key_offset;

		if (!futex_key_match_result(1, 1,
					*(unsigned long *)(key_addr +
						key_word_offset),
					*(unsigned long *)(key_addr +
						key_ptr_offset),
					*(int *)(key_addr +
						key_offset_offset),
					target_word, target_ptr,
					target_offset))
			continue;

		if (futex_requeue_should_wake_result(++task_count,
					nr_wake)) {
			wake_fn(q_addr, ctx_addr);
			continue;
		}

		requeue_fn(q_addr, ctx_addr);
		drop_count++;
	}

	if (drop_countp)
		*drop_countp = drop_count;
	return task_count;
}

void futex_double_lock_hb_result(unsigned long hb1_addr,
				 unsigned long hb2_addr,
				 unsigned long lock_offset,
				 futex_hb_lock_fn_t lock_fn)
{
	if (!lock_fn)
		return;

	if (hb1_addr <= hb2_addr) {
		lock_fn(hb1_addr + lock_offset);
		if (hb1_addr < hb2_addr)
			lock_fn(hb2_addr + lock_offset);
	}
	else {
		lock_fn(hb2_addr + lock_offset);
		lock_fn(hb1_addr + lock_offset);
	}
}

void futex_double_unlock_hb_result(unsigned long hb1_addr,
				   unsigned long hb2_addr,
				   unsigned long lock_offset,
				   futex_hb_unlock_fn_t unlock_fn)
{
	if (!unlock_fn)
		return;

	unlock_fn(hb1_addr + lock_offset);
	if (hb1_addr != hb2_addr)
		unlock_fn(hb2_addr + lock_offset);
}

void futex_wake_mark_woken_result(unsigned long q_addr,
				  unsigned long list_offset,
				  unsigned long node_plist_offset,
				  unsigned long lock_ptr_offset)
{
	struct plist_node *node = (void *)(q_addr + list_offset);
	struct plist_head *head = (void *)(q_addr + list_offset +
					   node_plist_offset);
	void **lock_ptr = (void **)(q_addr + lock_ptr_offset);

	plist_del(node, head);
	barrier();
	*lock_ptr = NULL;
}

int futex_unqueue_detach_result(unsigned long q_addr,
				unsigned long list_offset,
				unsigned long node_plist_offset)
{
	struct plist_node *node = (void *)(q_addr + list_offset);
	struct plist_head *head = (void *)(q_addr + list_offset +
					   node_plist_offset);

	plist_del(node, head);
	return 1;
}

int futex_requeue_move_result(unsigned long q_addr,
			      unsigned long list_offset,
			      unsigned long lock_ptr_offset,
			      unsigned long source_chain,
			      unsigned long target_chain,
			      unsigned long target_lock,
			      unsigned long debug_spinlock_offset)
{
	struct plist_node *node = (void *)(q_addr + list_offset);
	struct plist_head *source = (void *)source_chain;
	struct plist_head *target = (void *)target_chain;
	void **lock_ptr = (void **)(q_addr + lock_ptr_offset);

	if (source_chain == target_chain)
		return 0;

	plist_del(node, source);
	plist_add(node, target);
	*lock_ptr = (void *)target_lock;
	if (debug_spinlock_offset) {
		void **spinlock = (void **)(q_addr + list_offset +
					    debug_spinlock_offset);

		*spinlock = (void *)target_lock;
	}

	return 1;
}

int futex_requeue_key_update_result(unsigned long q_addr,
				    unsigned long q_key_offset,
				    unsigned long key_addr,
				    unsigned long key_size,
				    futex_key_refs_fn_t get_refs_fn)
{
	unsigned char *dst;
	unsigned char *src;

	if (!q_addr || !key_addr || !key_size || !get_refs_fn)
		return -EINVAL;

	get_refs_fn(key_addr);

	dst = (unsigned char *)(q_addr + q_key_offset);
	src = (unsigned char *)key_addr;
	for (unsigned long i = 0; i < key_size; i++)
		dst[i] = src[i];

	return 0;
}

void futex_queue_publish_waiter_result(
	unsigned long q_addr, unsigned long task_offset,
	unsigned long th_spin_sleep_pa_offset,
	unsigned long th_status_pa_offset,
	unsigned long th_spin_sleep_lock_pa_offset,
	unsigned long proc_status_pa_offset,
	unsigned long proc_update_lock_pa_offset,
	unsigned long runq_lock_pa_offset,
	unsigned long clv_flags_pa_offset,
	unsigned long intr_id_offset,
	unsigned long intr_vector_offset,
	unsigned long task, unsigned long th_spin_sleep_pa,
	unsigned long th_status_pa,
	unsigned long th_spin_sleep_lock_pa,
	unsigned long proc_status_pa,
	unsigned long proc_update_lock_pa,
	unsigned long runq_lock_pa,
	unsigned long clv_flags_pa,
	int intr_id, int intr_vector)
{
	*(unsigned long *)(q_addr + task_offset) = task;
	*(unsigned long *)(q_addr + th_spin_sleep_pa_offset) =
		th_spin_sleep_pa;
	*(unsigned long *)(q_addr + th_status_pa_offset) = th_status_pa;
	*(unsigned long *)(q_addr + th_spin_sleep_lock_pa_offset) =
		th_spin_sleep_lock_pa;
	*(unsigned long *)(q_addr + proc_status_pa_offset) = proc_status_pa;
	*(unsigned long *)(q_addr + proc_update_lock_pa_offset) =
		proc_update_lock_pa;
	*(unsigned long *)(q_addr + runq_lock_pa_offset) = runq_lock_pa;
	*(unsigned long *)(q_addr + clv_flags_pa_offset) = clv_flags_pa;
	*(int *)(q_addr + intr_id_offset) = intr_id;
	*(int *)(q_addr + intr_vector_offset) = intr_vector;
}

void futex_queue_insert_result(unsigned long q_addr,
			       unsigned long list_offset,
			       unsigned long chain_addr,
			       int prio,
			       unsigned long debug_spinlock_offset,
			       unsigned long lock_addr)
{
	struct plist_node *node;
	struct plist_head *chain;

	if (!q_addr || !chain_addr)
		return;

	node = (struct plist_node *)(q_addr + list_offset);
	chain = (struct plist_head *)chain_addr;
	plist_node_init(node, prio);
#ifdef CONFIG_DEBUG_PI_LIST
	if (debug_spinlock_offset)
		*(unsigned long *)(q_addr + list_offset +
				   debug_spinlock_offset) = lock_addr;
#else
	(void)debug_spinlock_offset;
	(void)lock_addr;
#endif
	plist_add(node, chain);
}

void futex_wait_prepare_q_result(unsigned long q_addr,
				 unsigned long bitset_offset,
				 unsigned long requeue_pi_key_offset,
				 unsigned long uti_futex_resp_offset,
				 unsigned int bitset,
				 unsigned long uti_futex_resp)
{
	if (!q_addr)
		return;

	*(unsigned int *)(q_addr + bitset_offset) = bitset;
	*(unsigned long *)(q_addr + requeue_pi_key_offset) = 0;
	*(unsigned long *)(q_addr + uti_futex_resp_offset) =
		uti_futex_resp;
}

void futex_wait_key_init_result(unsigned long q_addr,
				unsigned long key_offset,
				unsigned long key_size)
{
	unsigned char *key;
	unsigned long i;

	if (!q_addr)
		return;

	key = (unsigned char *)(q_addr + key_offset);
	for (i = 0; i < key_size; i++)
		key[i] = 0;
}

void futex_queue_lock_ptr_store_result(unsigned long q_addr,
				       unsigned long lock_ptr_offset,
				       unsigned long lock_addr)
{
	if (!q_addr)
		return;

	*(unsigned long *)(q_addr + lock_ptr_offset) = lock_addr;
}

int futex_wait_setup_result(unsigned long uaddr, unsigned int val,
			    int fshared, unsigned long q_addr,
			    unsigned long *hb_out,
			    unsigned long key_offset,
			    unsigned long key_size,
			    futex_wait_get_key_fn_t get_key_fn,
			    futex_wait_queue_lock_fn_t queue_lock_fn,
			    futex_wait_get_value_fn_t get_value_fn,
			    futex_wait_queue_unlock_fn_t queue_unlock_fn,
			    futex_wait_put_key_fn_t put_key_fn)
{
	unsigned long key_addr;
	unsigned long hb_addr;
	unsigned int uval;
	int ret;

	if (!q_addr || !get_key_fn || !queue_lock_fn || !get_value_fn ||
			!queue_unlock_fn || !put_key_fn)
		return -EINVAL;

	futex_wait_key_init_result(q_addr, key_offset, key_size);
	key_addr = q_addr + key_offset;
	ret = get_key_fn(uaddr, fshared, key_addr);
	if (ret)
		return ret;

	hb_addr = queue_lock_fn(q_addr);
	if (hb_out)
		*hb_out = hb_addr;

	ret = get_value_fn((unsigned long)&uval, uaddr);
	if (ret) {
		queue_unlock_fn(q_addr, hb_addr);
		put_key_fn(fshared, key_addr);
		return ret;
	}

	if (uval != val) {
		queue_unlock_fn(q_addr, hb_addr);
		put_key_fn(fshared, key_addr);
		return -EWOULDBLOCK;
	}

	return 0;
}

int futex_wait_mark_interruptible_result(unsigned long thread_addr,
					 unsigned long status_offset,
					 int interruptible_status)
{
	if (!thread_addr)
		return 0;

	return xchg4((int *)(thread_addr + status_offset),
		     interruptible_status);
}

int futex_wait_spin_sleep_store_result(unsigned long thread_addr,
				       unsigned long spin_sleep_offset,
				       int value)
{
	int *spin_sleep;
	int old;

	if (!thread_addr)
		return 0;

	spin_sleep = (int *)(thread_addr + spin_sleep_offset);
	old = *spin_sleep;
	*spin_sleep = value;
	return old;
}

int futex_wait_finish_state_result(unsigned long thread_addr,
				   unsigned long status_offset,
				   unsigned long spin_sleep_offset,
				   int running_status)
{
	int *status;
	int old;

	if (!thread_addr)
		return 0;

	status = (int *)(thread_addr + status_offset);
	old = *status;
	*status = running_status;
	*(int *)(thread_addr + spin_sleep_offset) = 0;
	return old;
}

int futex_wait_schedule_action_result(int queued, uint64_t timeout)
{
	if (!queued)
		return FUTEX_WAIT_SCHEDULE_NONE;
	return timeout ? FUTEX_WAIT_SCHEDULE_TIMEOUT :
		FUTEX_WAIT_SCHEDULE_DIRECT;
}

int futex_wait_post_action_result(int unqueued, uint64_t timeout,
				  int64_t time_remain,
				  int has_pending_signal,
				  int restart_sys)
{
	if (!unqueued)
		return FUTEX_WAIT_POST_SUCCESS;
	if (timeout && !time_remain)
		return FUTEX_WAIT_POST_TIMEOUT;
	if (has_pending_signal || restart_sys)
		return FUTEX_WAIT_POST_INTERRUPT;
	return FUTEX_WAIT_POST_RETRY;
}

int futex_wake_target_result(unsigned long uti_futex_resp)
{
	return uti_futex_resp ? FUTEX_WAKE_TARGET_LINUX :
		FUTEX_WAKE_TARGET_MCKERNEL;
}

unsigned long futex_wake_linux_channel_result(unsigned long linux_channel,
					      unsigned long fallback_channel)
{
	return linux_channel ? linux_channel : fallback_channel;
}

void futex_wake_ikc_packet_fill_result(unsigned long packet_addr,
				       unsigned long msg_offset,
				       unsigned long resp_offset,
				       unsigned long spin_sleep_offset,
				       int msg, unsigned long resp,
				       unsigned long spin_sleep_addr)
{
	if (!packet_addr)
		return;

	*(int *)(packet_addr + msg_offset) = msg;
	*(unsigned long *)(packet_addr + resp_offset) = resp;
	*(unsigned long *)(packet_addr + spin_sleep_offset) = spin_sleep_addr;
}

int futex_wake_orchestrate_result(
	unsigned long q_addr, unsigned long q_list_offset,
	unsigned long q_node_plist_offset, unsigned long q_lock_ptr_offset,
	unsigned long q_task_offset, unsigned long q_uti_futex_resp_offset,
	unsigned long q_linux_cpu_offset,
	unsigned long thread_spin_sleep_offset,
	unsigned long packet_addr, unsigned long packet_msg_offset,
	unsigned long packet_resp_offset,
	unsigned long packet_spin_sleep_offset, int msg,
	unsigned long fallback_channel, int wake_status,
	futex_wake_linux_channel_by_cpu_fn_t linux_channel_fn,
	futex_wake_send_fn_t send_fn,
	futex_wake_thread_fn_t wake_thread_fn,
	futex_wake_log_fn_t log_fn)
{
	unsigned long thread_addr;
	unsigned long uti_futex_resp;
	int target;

	if (!q_addr)
		return -EINVAL;

	thread_addr = *(unsigned long *)(q_addr + q_task_offset);
	uti_futex_resp = *(unsigned long *)(q_addr + q_uti_futex_resp_offset);

	futex_wake_mark_woken_result(q_addr, q_list_offset,
			q_node_plist_offset, q_lock_ptr_offset);

	target = futex_wake_target_result(uti_futex_resp);
	if (target == FUTEX_WAKE_TARGET_LINUX) {
		int linux_cpu = *(int *)(q_addr + q_linux_cpu_offset);
		unsigned long linux_channel = linux_channel_fn ?
			linux_channel_fn(linux_cpu) : 0;
		unsigned long resp_channel =
			futex_wake_linux_channel_result(linux_channel,
					fallback_channel);
		int rc = -ENOSYS;

		if (log_fn)
			log_fn(FUTEX_WAKE_LOG_LINUX_TARGET, thread_addr,
			       uti_futex_resp, linux_cpu, resp_channel, 0);
		futex_wake_ikc_packet_fill_result(packet_addr,
				packet_msg_offset, packet_resp_offset,
				packet_spin_sleep_offset, msg, uti_futex_resp,
				thread_addr + thread_spin_sleep_offset);
		if (send_fn)
			rc = send_fn(resp_channel, packet_addr);
		if (log_fn) {
			log_fn(rc < 0 ? FUTEX_WAKE_LOG_SEND_FAILED :
			       FUTEX_WAKE_LOG_SEND_OK, thread_addr,
			       uti_futex_resp, linux_cpu, resp_channel, rc);
		}
		return target;
	}

	if (wake_thread_fn) {
		if (log_fn)
			log_fn(FUTEX_WAKE_LOG_MCKERNEL_TARGET, thread_addr,
			       uti_futex_resp, 0, 0, 0);
		wake_thread_fn(thread_addr, wake_status);
	}
	return target;
}

int syscall_offload_should_schedule_result(int no_preempt, int tid,
					   int need_resched, int runq_len,
					   int is_sched_setaffinity)
{
	if (no_preempt || !tid)
		return 0;

	return need_resched || runq_len > 1 || is_sched_setaffinity;
}

#endif /* MCKERNEL_RUST_SCHED_RUNTIME_HELPERS */
