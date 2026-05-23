/* SPDX-License-Identifier: GPL-2.0 */
#ifndef MCKERNEL_SCHED_HELPERS_H
#define MCKERNEL_SCHED_HELPERS_H

#include <types.h>

#define FUTEX_WAIT_POST_SUCCESS 0
#define FUTEX_WAIT_POST_RETRY 1
#define FUTEX_WAIT_POST_TIMEOUT 2
#define FUTEX_WAIT_POST_INTERRUPT 3

#define FUTEX_WAIT_SCHEDULE_NONE 0
#define FUTEX_WAIT_SCHEDULE_TIMEOUT 1
#define FUTEX_WAIT_SCHEDULE_DIRECT 2

#define FUTEX_WAKE_TARGET_MCKERNEL 0
#define FUTEX_WAKE_TARGET_LINUX 1

typedef void (*futex_hb_lock_fn_t)(unsigned long lock_addr);
typedef void (*futex_hb_unlock_fn_t)(unsigned long lock_addr);
typedef void (*futex_wake_scan_fn_t)(unsigned long q_addr);
typedef void (*futex_requeue_scan_fn_t)(unsigned long q_addr,
					unsigned long ctx_addr);
typedef void (*futex_key_refs_fn_t)(unsigned long key_addr);
typedef int (*futex_wait_get_key_fn_t)(unsigned long uaddr, int fshared,
				       unsigned long key_addr);
typedef unsigned long (*futex_wait_queue_lock_fn_t)(unsigned long q_addr);
typedef int (*futex_wait_get_value_fn_t)(unsigned long value_addr,
					 unsigned long uaddr);
typedef void (*futex_wait_queue_unlock_fn_t)(unsigned long q_addr,
					     unsigned long hb_addr);
typedef void (*futex_wait_put_key_fn_t)(int fshared, unsigned long key_addr);

uint64_t timer_spin_sleep_remaining_result(uint64_t timeout, uint64_t elapsed);
int timer_runq_should_schedule_result(int runq_len);
uint64_t timer_after_spin_remaining_result(uint64_t timeout,
					   uint64_t loop_timeout);
uint64_t timer_after_tick_remaining_result(uint64_t timeout,
					   uint64_t loop_timeout);
int futex_key_match_result(int has_key1, int has_key2,
			   unsigned long word1, unsigned long ptr1,
			   unsigned long offset1, unsigned long word2,
			   unsigned long ptr2, unsigned long offset2);
int futex_key_prepare_result(unsigned long address, int fshared,
			     unsigned long *basep, unsigned long *offsetp,
			     int *privatep);
int futex_wake_bitset_valid_result(unsigned int bitset);
int futex_waiter_matches_bitset_result(unsigned int waiter_bitset,
				       unsigned int requested_bitset);
int futex_wake_limit_reached_result(int woken, int nr_wake);
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
			   futex_wake_scan_fn_t wake_fn);
int futex_requeue_should_move_result(unsigned long source_chain,
				     unsigned long target_chain);
int futex_requeue_loop_done_result(int task_count, int nr_wake,
				   int nr_requeue);
int futex_requeue_should_wake_result(int task_count, int nr_wake);
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
			      unsigned long ctx_addr);
void futex_double_lock_hb_result(unsigned long hb1_addr,
				 unsigned long hb2_addr,
				 unsigned long lock_offset,
				 futex_hb_lock_fn_t lock_fn);
void futex_double_unlock_hb_result(unsigned long hb1_addr,
				   unsigned long hb2_addr,
				   unsigned long lock_offset,
				   futex_hb_unlock_fn_t unlock_fn);
void futex_wake_mark_woken_result(unsigned long q_addr,
				  unsigned long list_offset,
				  unsigned long node_plist_offset,
				  unsigned long lock_ptr_offset);
int futex_unqueue_detach_result(unsigned long q_addr,
				unsigned long list_offset,
				unsigned long node_plist_offset);
int futex_requeue_move_result(unsigned long q_addr,
			      unsigned long list_offset,
			      unsigned long lock_ptr_offset,
			      unsigned long source_chain,
			      unsigned long target_chain,
			      unsigned long target_lock,
			      unsigned long debug_spinlock_offset);
int futex_requeue_key_update_result(unsigned long q_addr,
				    unsigned long q_key_offset,
				    unsigned long key_addr,
				    unsigned long key_size,
				    futex_key_refs_fn_t get_refs_fn);
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
	int intr_id, int intr_vector);
void futex_queue_insert_result(unsigned long q_addr,
			       unsigned long list_offset,
			       unsigned long chain_addr,
			       int prio,
			       unsigned long debug_spinlock_offset,
			       unsigned long lock_addr);
void futex_wait_prepare_q_result(unsigned long q_addr,
				 unsigned long bitset_offset,
				 unsigned long requeue_pi_key_offset,
				 unsigned long uti_futex_resp_offset,
				 unsigned int bitset,
				 unsigned long uti_futex_resp);
void futex_wait_key_init_result(unsigned long q_addr,
				unsigned long key_offset,
				unsigned long key_size);
void futex_queue_lock_ptr_store_result(unsigned long q_addr,
				       unsigned long lock_ptr_offset,
				       unsigned long lock_addr);
int futex_wait_setup_result(unsigned long uaddr,
			    unsigned int val,
			    int fshared,
			    unsigned long q_addr,
			    unsigned long *hb_out,
			    unsigned long key_offset,
			    unsigned long key_size,
			    futex_wait_get_key_fn_t get_key_fn,
			    futex_wait_queue_lock_fn_t queue_lock_fn,
			    futex_wait_get_value_fn_t get_value_fn,
			    futex_wait_queue_unlock_fn_t queue_unlock_fn,
			    futex_wait_put_key_fn_t put_key_fn);
int futex_wait_mark_interruptible_result(unsigned long thread_addr,
					 unsigned long status_offset,
					 int interruptible_status);
int futex_wait_spin_sleep_store_result(unsigned long thread_addr,
				       unsigned long spin_sleep_offset,
				       int value);
int futex_wait_finish_state_result(unsigned long thread_addr,
				   unsigned long status_offset,
				   unsigned long spin_sleep_offset,
				   int running_status);
int futex_wait_schedule_action_result(int queued, uint64_t timeout);
int futex_wait_post_action_result(int unqueued, uint64_t timeout,
				  int64_t time_remain,
				  int has_pending_signal,
				  int restart_sys);
int futex_wake_target_result(unsigned long uti_futex_resp);
unsigned long futex_wake_linux_channel_result(unsigned long linux_channel,
					      unsigned long fallback_channel);
void futex_wake_ikc_packet_fill_result(unsigned long packet_addr,
				       unsigned long msg_offset,
				       unsigned long resp_offset,
				       unsigned long spin_sleep_offset,
				       int msg, unsigned long resp,
				       unsigned long spin_sleep_addr);
int futex_hash_bucket_table_init_result(unsigned long buckets_addr,
					int bucket_count,
					unsigned long bucket_stride,
					unsigned long lock_offset,
					unsigned long lock_word_offset,
					unsigned long chain_offset,
					unsigned long prio_list_offset,
					unsigned long node_list_offset,
					unsigned long debug_spinlock_offset,
					unsigned long debug_rawlock_offset);
int syscall_offload_should_schedule_result(int no_preempt, int tid,
					   int need_resched, int runq_len,
					   int is_sched_setaffinity);

#endif /* MCKERNEL_SCHED_HELPERS_H */
