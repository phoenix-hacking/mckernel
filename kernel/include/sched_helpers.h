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

#define FUTEX_WAIT_QUEUE_LOG_TIMEOUT 1
#define FUTEX_WAIT_QUEUE_LOG_DIRECT 2
#define FUTEX_WAIT_QUEUE_LOG_WOKEN 3

#define FUTEX_WAIT_LOG_SETUP_RET 1
#define FUTEX_WAIT_LOG_SUCCESS 2
#define FUTEX_WAIT_LOG_TIMEOUT 3
#define FUTEX_WAIT_LOG_INTERRUPT 4

#define FUTEX_GET_KEY_LOG_VTOP_FAILED 1

typedef void (*futex_hb_lock_fn_t)(unsigned long lock_addr);
typedef void (*futex_hb_unlock_fn_t)(unsigned long lock_addr);
typedef void (*futex_wake_scan_fn_t)(unsigned long q_addr);
typedef void (*futex_requeue_scan_fn_t)(unsigned long q_addr,
					unsigned long ctx_addr);
typedef void (*futex_key_refs_fn_t)(unsigned long key_addr);
typedef int (*futex_get_key_vtop_fn_t)(unsigned long mm_addr,
				       unsigned long uaddr,
				       unsigned long phys_out_addr);
typedef int (*futex_get_key_fault_fn_t)(unsigned long mm_addr,
					unsigned long uaddr, int flags);
typedef void (*futex_get_key_log_fn_t)(int event);
typedef unsigned long (*futex_wake_hash_key_fn_t)(unsigned long key_addr);
typedef unsigned long (*futex_wake_lock_fn_t)(unsigned long lock_addr);
typedef void (*futex_wake_unlock_fn_t)(unsigned long lock_addr,
				       unsigned long irqstate);
typedef int (*futex_wait_get_key_fn_t)(unsigned long uaddr, int fshared,
				       unsigned long key_addr);
typedef int (*futex_wake_atomic_op_fn_t)(int op, unsigned long uaddr);
typedef unsigned long (*futex_wait_queue_lock_fn_t)(unsigned long q_addr);
typedef int (*futex_wait_get_value_fn_t)(unsigned long value_addr,
					 unsigned long uaddr);
typedef void (*futex_wait_queue_unlock_fn_t)(unsigned long q_addr,
					     unsigned long hb_addr);
typedef void (*futex_wait_put_key_fn_t)(int fshared, unsigned long key_addr);
typedef unsigned long (*futex_alloc_fn_t)(unsigned long size, int flag);
typedef unsigned int (*futex_hash_fn_t)(unsigned long key_addr);
typedef int (*futex_dispatch_wait_fn_t)(unsigned long uaddr, int fshared,
					uint32_t val, uint64_t timeout,
					uint32_t val3, int clockrt);
typedef int (*futex_dispatch_wake_fn_t)(unsigned long uaddr, int fshared,
					uint32_t val, uint32_t val3);
typedef int (*futex_dispatch_requeue_fn_t)(unsigned long uaddr, int fshared,
					   unsigned long uaddr2, uint32_t val,
					   uint32_t val2, int cmpval_present,
					   uint32_t cmpval, int requeue_pi);
typedef int (*futex_dispatch_wake_op_fn_t)(unsigned long uaddr, int fshared,
					   unsigned long uaddr2, uint32_t val,
					   uint32_t val2, uint32_t val3);
typedef void (*futex_dispatch_invalid_fn_t)(int cmd);
typedef unsigned long (*futex_wake_linux_channel_by_cpu_fn_t)(int linux_cpu);
typedef int (*futex_wake_send_fn_t)(unsigned long channel_addr,
				    unsigned long packet_addr);
typedef void (*futex_wake_thread_fn_t)(unsigned long thread_addr,
				       int status);
typedef void (*futex_wake_log_fn_t)(int event, unsigned long thread_addr,
				    unsigned long uti_futex_resp,
				    int linux_cpu,
				    unsigned long channel_addr, int rc);
typedef unsigned long (*futex_virt_to_phys_fn_t)(unsigned long addr);
typedef int (*futex_interrupt_id_fn_t)(int cpu_id);
typedef int (*futex_vector_fn_t)(int vector_key);
typedef unsigned long (*futex_wait_spin_lock_fn_t)(unsigned long lock_addr);
typedef void (*futex_wait_spin_unlock_fn_t)(unsigned long lock_addr,
					    unsigned long irqstate);
typedef void (*futex_wait_queue_me_fn_t)(unsigned long q_addr,
					 unsigned long hb_addr);
typedef int64_t (*futex_wait_schedule_timeout_fn_t)(uint64_t timeout);
typedef void (*futex_wait_schedule_direct_fn_t)(void);
typedef void (*futex_wait_queue_log_fn_t)(int event,
					  unsigned long thread_addr,
					  int tid);
typedef int (*futex_wait_setup_call_fn_t)(unsigned long uaddr,
					  uint32_t val,
					  int fshared,
					  unsigned long q_addr,
					  unsigned long hb_out_addr);
typedef int64_t (*futex_wait_queue_call_fn_t)(unsigned long hb_addr,
					      unsigned long q_addr,
					      uint64_t timeout);
typedef int (*futex_wait_unqueue_fn_t)(unsigned long q_addr);
typedef int (*futex_wait_has_signal_fn_t)(unsigned long thread_addr);
typedef void (*futex_wait_log_fn_t)(int event, unsigned long thread_addr,
				    int tid, int ret);
typedef unsigned long (*futex_wait_timestamp_fn_t)(void);
typedef int (*futex_wait_body_entry_fn_t)(unsigned long uaddr, int fshared,
					  uint32_t val, uint64_t timeout,
					  uint32_t bitset,
					  unsigned long q_addr,
					  unsigned long thread_addr,
					  unsigned long uti_futex_resp);
typedef void (*timer_spin_init_fn_t)(unsigned long lock_addr);
typedef unsigned long (*timer_spin_lock_fn_t)(unsigned long lock_addr);
typedef void (*timer_spin_unlock_fn_t)(unsigned long lock_addr,
				       unsigned long irqstate);
typedef uint64_t (*timer_rdtsc_fn_t)(void);
typedef void (*timer_void_fn_t)(void);
typedef void (*timer_set_status_fn_t)(unsigned long status_addr, int status);
typedef void (*timer_lapic_enable_fn_t)(unsigned int clocks);
typedef void (*timer_lapic_disable_fn_t)(void);
typedef void (*timer_waitq_wakeup_fn_t)(unsigned long waitq_addr);
typedef void (*timer_log_wake_fn_t)(unsigned long timer_addr,
				    unsigned long thread_addr);
typedef unsigned long (*sched_migrate_spin_lock_fn_t)(
	unsigned long lock_addr);
typedef void (*sched_migrate_spin_unlock_fn_t)(unsigned long lock_addr,
					       unsigned long irqstate);
typedef void (*sched_migrate_noirq_lock_fn_t)(unsigned long lock_addr);
typedef void (*sched_migrate_noirq_unlock_fn_t)(unsigned long lock_addr);
typedef void (*sched_migrate_waitq_init_fn_t)(unsigned long waitq_addr);
typedef void (*sched_migrate_waitq_prepare_fn_t)(unsigned long waitq_addr,
						 unsigned long entry_addr,
						 int status);
typedef void (*sched_migrate_waitq_finish_fn_t)(unsigned long waitq_addr,
						unsigned long entry_addr);
typedef int (*sched_migrate_vector_fn_t)(int vector_key);
typedef void (*sched_migrate_interrupt_fn_t)(int cpu, int vector);
typedef void (*sched_migrate_void_fn_t)(void);
typedef void (*sched_migrate_log_fn_t)(unsigned long thread_addr, int tid,
				       int cpu_id);
typedef unsigned long (*sched_migrate_cpu_local_fn_t)(int cpu_id);
typedef void (*sched_migrate_waitq_wakeup_fn_t)(unsigned long waitq_addr);
typedef void (*sched_do_migrate_log_fn_t)(unsigned long thread_addr, int tid,
					  int old_cpu_id, int new_cpu_id);
typedef void (*sched_runq_rwlock_fn_t)(unsigned long lock_addr,
				       unsigned long node_addr);
typedef void (*sched_runq_status_set_fn_t)(unsigned long status_addr,
					   int status);
typedef void (*sched_runq_set_timer_fn_t)(int runq_locked);
typedef void (*sched_runq_log_fn_t)(int event, unsigned long arg0,
				    unsigned long arg1, int arg2, int arg3);
typedef unsigned long (*sched_runq_irq_save_fn_t)(void);
typedef void (*sched_runq_irq_restore_fn_t)(unsigned long irqstate);
typedef int (*sched_runq_has_signal_fn_t)(unsigned long thread_addr);
typedef void (*sched_runq_void_fn_t)(void);
typedef void (*sched_runq_thread_fn_t)(unsigned long thread_addr);
typedef int (*sched_runq_counter_inc_fn_t)(unsigned long counter_addr);
typedef void (*sched_runq_counter_dec_fn_t)(unsigned long counter_addr);

struct timer_runtime_offsets {
	unsigned long thread_status_offset;
	unsigned long thread_sched_list_offset;
	unsigned long thread_spin_sleep_lock_offset;
	unsigned long thread_spin_sleep_offset;
	unsigned long thread_itimer_enabled_offset;
	unsigned long cpu_runq_lock_offset;
	unsigned long cpu_runq_offset;
	unsigned long cpu_runq_len_offset;
	unsigned long cpu_current_offset;
	unsigned long cpu_timer_enabled_offset;
	unsigned long cpu_backlog_list_offset;
	unsigned long timer_timeout_offset;
	unsigned long timer_waitq_offset;
	unsigned long timer_list_offset;
	unsigned long timer_thread_offset;
};

struct sched_migrate_offsets {
	unsigned long req_list_offset;
	unsigned long req_thread_offset;
	unsigned long req_wq_offset;
	unsigned long thread_cpu_id_offset;
	unsigned long thread_tid_offset;
	unsigned long cpu_migq_lock_offset;
	unsigned long cpu_migq_offset;
	unsigned long cpu_runq_lock_offset;
	unsigned long cpu_flags_offset;
	unsigned long cpu_status_offset;
};

struct sched_do_migrate_offsets {
	unsigned long req_list_offset;
	unsigned long req_thread_offset;
	unsigned long req_wq_offset;
	unsigned long thread_cpu_id_offset;
	unsigned long thread_tid_offset;
	unsigned long thread_cpu_set_offset;
	unsigned long thread_sched_list_offset;
	unsigned long thread_vm_offset;
	unsigned long vm_address_space_offset;
	unsigned long address_space_cpu_set_offset;
	unsigned long address_space_cpu_set_lock_offset;
	unsigned long cpu_migq_lock_offset;
	unsigned long cpu_migq_offset;
	unsigned long cpu_runq_lock_offset;
	unsigned long cpu_runq_offset;
	unsigned long cpu_runq_len_offset;
	unsigned long cpu_flags_offset;
};

struct sched_runqueue_offsets {
	unsigned long thread_cpu_id_offset;
	unsigned long thread_tid_offset;
	unsigned long thread_status_offset;
	unsigned long thread_spin_sleep_lock_offset;
	unsigned long thread_spin_sleep_offset;
	unsigned long thread_sched_list_offset;
	unsigned long thread_sigpending_offset;
	unsigned long thread_sigcommon_offset;
	unsigned long sigcommon_sigpending_offset;
	unsigned long thread_proc_offset;
	unsigned long thread_mod_clone_offset;
	unsigned long proc_pid_offset;
	unsigned long proc_status_offset;
	unsigned long proc_update_lock_offset;
	unsigned long proc_clone_count_offset;
	unsigned long cpu_runq_lock_offset;
	unsigned long cpu_runq_irqstate_offset;
	unsigned long cpu_current_offset;
	unsigned long cpu_prevpid_offset;
	unsigned long cpu_runq_offset;
	unsigned long cpu_runq_len_offset;
	unsigned long cpu_runq_reserved_offset;
	unsigned long cpu_flags_offset;
	unsigned long cpu_status_offset;
	unsigned long cpu_in_interrupt_offset;
	unsigned long cpu_nr_ctx_switches_offset;
};

struct sched_schedule_result {
	unsigned long cpu_addr;
	unsigned long prev_thread_addr;
	unsigned long next_thread_addr;
	int prevpid;
	int switch_ctx;
	int action;
};

#define SCHED_RUNQ_LOG_NO_MIGRATION_IRQ 1
#define SCHED_RUNQ_LOG_WAKE_ENTRY 2
#define SCHED_RUNQ_LOG_SPIN_WAKEUP 3
#define SCHED_RUNQ_LOG_REMOTE_IPI 4
#define SCHED_RUNQ_LOG_RUNQ_ADD 5
#define SCHED_RUNQ_LOG_IDLE_HALT 6
#define SCHED_RUNQ_LOG_LOST_WAKEUP 7
#define SCHED_RUNQ_LOG_SPIN_WOKEN 8
#define SCHED_RUNQ_LOG_SLEEP_WOKEN 9
#define SCHED_RUNQ_LOG_NO_PREEMPT 10
#define SCHED_RUNQ_LOG_CLONE_COUNT 11

#define SCHED_SCHEDULE_ACTION_RESCHED_ONLY 1
#define SCHED_SCHEDULE_ACTION_NO_SWITCH 2
#define SCHED_SCHEDULE_ACTION_SWITCH 3

#define FUTEX_WAKE_LOG_LINUX_TARGET 1
#define FUTEX_WAKE_LOG_SEND_FAILED 2
#define FUTEX_WAKE_LOG_SEND_OK 3
#define FUTEX_WAKE_LOG_MCKERNEL_TARGET 4

uint64_t timer_spin_sleep_remaining_result(uint64_t timeout, uint64_t elapsed);
int timer_runq_should_schedule_result(int runq_len);
uint64_t timer_after_spin_remaining_result(uint64_t timeout,
					   uint64_t loop_timeout);
uint64_t timer_after_tick_remaining_result(uint64_t timeout,
					   uint64_t loop_timeout);
int timer_init_timers_result(unsigned long timers_lock_addr,
			     unsigned long timers_head_addr,
			     timer_spin_init_fn_t spin_init_fn);
uint64_t timer_schedule_timeout_body_result(
	unsigned long thread_addr, unsigned long cpu_local_addr,
	uint64_t timeout, uint64_t loop_timeout,
	const struct timer_runtime_offsets *offsets,
	timer_rdtsc_fn_t rdtsc_fn, timer_spin_lock_fn_t spin_lock_fn,
	timer_spin_unlock_fn_t spin_unlock_fn,
	timer_set_status_fn_t set_status_fn, timer_void_fn_t schedule_fn,
	timer_void_fn_t zero_free_fn, timer_void_fn_t pause_fn);
int timer_wake_tick_result(unsigned long timers_lock_addr,
			   unsigned long timers_head_addr,
			   uint64_t loop_timeout,
			   const struct timer_runtime_offsets *offsets,
			   timer_spin_lock_fn_t lock_fn,
			   timer_spin_unlock_fn_t unlock_fn,
			   timer_waitq_wakeup_fn_t wake_fn,
			   timer_log_wake_fn_t log_fn);
int timer_wake_loop_body_result(unsigned long timers_lock_addr,
				unsigned long timers_head_addr,
				uint64_t loop_timeout, int max_ticks,
				const struct timer_runtime_offsets *offsets,
				timer_rdtsc_fn_t rdtsc_fn,
				timer_void_fn_t pause_fn,
				timer_spin_lock_fn_t lock_fn,
				timer_spin_unlock_fn_t unlock_fn,
				timer_waitq_wakeup_fn_t wake_fn,
				timer_log_wake_fn_t log_fn);
int timer_set_timer_body_result(unsigned long cpu_local_addr, int time_sharing,
				int runq_locked,
				const struct timer_runtime_offsets *offsets,
				timer_spin_lock_fn_t lock_fn,
				timer_spin_unlock_fn_t unlock_fn,
				timer_lapic_enable_fn_t enable_fn,
				timer_lapic_disable_fn_t disable_fn);
int sched_request_migrate_body_result(
	int target_cpu_id, unsigned long target_cpu_addr,
	unsigned long req_addr, unsigned long wait_entry_addr,
	unsigned long thread_addr, int current_cpu_id, int wait_status,
	unsigned int need_resched_flag, unsigned int need_migrate_flag,
	int running_status, int vector_key,
	const struct sched_migrate_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_migrate_noirq_lock_fn_t noirq_lock_fn,
	sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
	sched_migrate_waitq_init_fn_t waitq_init_fn,
	sched_migrate_waitq_prepare_fn_t waitq_prepare_fn,
	sched_migrate_waitq_finish_fn_t waitq_finish_fn,
	sched_migrate_vector_fn_t vector_fn,
	sched_migrate_interrupt_fn_t interrupt_fn,
	sched_migrate_void_fn_t schedule_fn,
	sched_migrate_log_fn_t log_fn);
int sched_do_migrate_body_result(
	int current_cpu_id, unsigned long current_cpu_addr, int cpu_set_bits,
	unsigned int need_resched_flag, int vector_key,
	const struct sched_do_migrate_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_migrate_noirq_lock_fn_t noirq_lock_fn,
	sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
	sched_migrate_cpu_local_fn_t cpu_local_fn,
	sched_migrate_waitq_wakeup_fn_t waitq_wakeup_fn,
	sched_migrate_vector_fn_t vector_fn,
	sched_migrate_interrupt_fn_t interrupt_fn,
	sched_do_migrate_log_fn_t log_fn);
int sched_release_cpuid_body_result(
	int cpuid, unsigned long cpu_addr, unsigned long reservation_lock_addr,
	int idle_status, const struct sched_runqueue_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_migrate_noirq_lock_fn_t noirq_lock_fn,
	sched_migrate_noirq_unlock_fn_t noirq_unlock_fn);
int sched_check_need_resched_body_result(
	unsigned long cpu_addr, unsigned int need_resched_flag,
	unsigned int need_migrate_flag,
	const struct sched_runqueue_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_migrate_void_fn_t schedule_fn,
	sched_runq_log_fn_t log_fn);
int sched_runq_add_thread_locked_result(
	unsigned long thread_addr, unsigned long cpu_addr, int cpu_id,
	unsigned int need_resched_flag, int running_status,
	const struct sched_runqueue_offsets *offsets,
	sched_runq_log_fn_t log_fn);
int sched_runq_add_thread_body_result(
	unsigned long thread_addr, unsigned long cpu_addr,
	unsigned long reservation_lock_addr, int cpu_id, int current_cpu_id,
	unsigned int need_resched_flag, int running_status, int vector_key,
	const struct sched_runqueue_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_migrate_noirq_lock_fn_t noirq_lock_fn,
	sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
	sched_runq_counter_dec_fn_t reserved_dec_fn,
	sched_runq_thread_fn_t procfs_create_fn,
	sched_runq_counter_inc_fn_t clone_count_inc_fn,
	sched_runq_void_fn_t rusage_inc_fn,
	sched_runq_void_fn_t rusage_debug_fn,
	sched_migrate_vector_fn_t vector_fn,
	sched_migrate_interrupt_fn_t interrupt_fn,
	sched_runq_log_fn_t log_fn);
int sched_runq_del_thread_body_result(
	unsigned long thread_addr, unsigned long cpu_addr, int idle_status,
	const struct sched_runqueue_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn);
int sched_wakeup_thread_body_result(
	unsigned long thread_addr, unsigned long cpu_addr,
	unsigned long update_lock_node_addr, int current_cpu_id,
	int valid_states, int runq_locked, int running_status, int exited_status,
	unsigned int need_resched_flag, int vector_key,
	const struct sched_runqueue_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_runq_rwlock_fn_t rwlock_fn,
	sched_runq_rwlock_fn_t rwunlock_fn,
	sched_runq_status_set_fn_t status_set_fn,
	sched_runq_set_timer_fn_t set_timer_fn,
	sched_migrate_vector_fn_t vector_fn,
	sched_migrate_interrupt_fn_t interrupt_fn,
	sched_runq_log_fn_t log_fn);
int sched_spin_sleep_or_schedule_body_result(
	unsigned long thread_addr, unsigned long cpu_addr, int current_cpu_id,
	int idle_halt_enabled, unsigned int need_resched_flag,
	const struct sched_runqueue_offsets *offsets,
	sched_runq_irq_save_fn_t irq_save_fn,
	sched_runq_irq_restore_fn_t irq_restore_fn,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_migrate_noirq_lock_fn_t noirq_lock_fn,
	sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
	sched_migrate_void_fn_t schedule_fn,
	sched_migrate_void_fn_t zero_free_fn,
	sched_migrate_void_fn_t pause_fn,
	sched_runq_has_signal_fn_t has_signal_fn,
	sched_runq_log_fn_t log_fn);
int sched_schedule_prepare_body_result(
	unsigned long cpu_addr, unsigned long idle_thread_addr,
	int no_preempt_count, unsigned int need_resched_flag,
	unsigned int need_migrate_flag, int running_status,
	int interruptible_status, int exited_status, int spawning_to_remote,
	int idle_cpu_status, int reserved_cpu_status,
	const struct sched_runqueue_offsets *offsets,
	struct sched_schedule_result *result,
	sched_runq_irq_save_fn_t irq_save_fn,
	sched_runq_irq_restore_fn_t irq_restore_fn,
	sched_migrate_noirq_lock_fn_t noirq_lock_fn,
	sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
	sched_runq_set_timer_fn_t set_timer_fn,
	sched_runq_void_fn_t reset_cputime_fn,
	sched_runq_has_signal_fn_t has_signal_fn,
	sched_runq_log_fn_t log_fn);
int futex_key_match_result(int has_key1, int has_key2,
			   unsigned long word1, unsigned long ptr1,
			   unsigned long offset1, unsigned long word2,
			   unsigned long ptr2, unsigned long offset2);
int futex_key_prepare_result(unsigned long address, int fshared,
			     unsigned long *basep, unsigned long *offsetp,
			     int *privatep);
int futex_get_key_result(unsigned long uaddr, int fshared,
			 unsigned long key_addr, unsigned long mm_addr,
			 unsigned long key_word_offset,
			 unsigned long key_ptr_offset,
			 unsigned long key_offset_offset,
			 unsigned long fut_off_mmshared, int fault_flags,
			 futex_key_refs_fn_t key_refs_fn,
			 futex_get_key_vtop_fn_t vtop_fn,
			 futex_get_key_fault_fn_t fault_fn,
			 futex_get_key_log_fn_t log_fn);
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
int futex_wake_body_result(unsigned long uaddr, int fshared, int nr_wake,
			   unsigned int bitset, unsigned long key_addr,
			   unsigned long hb_lock_offset,
			   unsigned long hb_chain_offset,
			   unsigned long q_list_offset,
			   unsigned long q_key_offset,
			   unsigned long q_bitset_offset,
			   unsigned long key_word_offset,
			   unsigned long key_ptr_offset,
			   unsigned long key_offset_offset,
			   futex_wait_get_key_fn_t get_key_fn,
			   futex_wake_hash_key_fn_t hash_key_fn,
			   futex_wake_lock_fn_t lock_fn,
			   futex_wake_unlock_fn_t unlock_fn,
			   futex_wait_put_key_fn_t put_key_fn,
			   futex_wake_scan_fn_t wake_fn);
int futex_wake_op_body_result(
	unsigned long uaddr1, int fshared, unsigned long uaddr2, int nr_wake,
	int nr_wake2, int op, unsigned long key1_addr,
	unsigned long key2_addr, unsigned long hb_lock_offset,
	unsigned long hb_chain_offset, unsigned long q_list_offset,
	unsigned long q_key_offset, unsigned long q_bitset_offset,
	unsigned long key_word_offset, unsigned long key_ptr_offset,
	unsigned long key_offset_offset, futex_wait_get_key_fn_t get_key_fn,
	futex_wake_hash_key_fn_t hash_key_fn, futex_hb_lock_fn_t lock_fn,
	futex_hb_unlock_fn_t unlock_fn, futex_wake_atomic_op_fn_t atomic_fn,
	futex_wait_put_key_fn_t put_key_fn, futex_wake_scan_fn_t wake_fn);
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
int futex_requeue_body_result(
	unsigned long uaddr1, int fshared, unsigned long uaddr2, int nr_wake,
	int nr_requeue, unsigned long cmpval_addr, unsigned long key1_addr,
	unsigned long key2_addr, unsigned long ctx_addr,
	unsigned long hb_lock_offset, unsigned long hb_chain_offset,
	unsigned long q_list_offset, unsigned long q_key_offset,
	unsigned long key_word_offset, unsigned long key_ptr_offset,
	unsigned long key_offset_offset, unsigned long ctx_hb1_offset,
	unsigned long ctx_hb2_offset, unsigned long ctx_key2_offset,
	futex_wait_get_key_fn_t get_key_fn,
	futex_wake_hash_key_fn_t hash_key_fn, futex_hb_lock_fn_t lock_fn,
	futex_hb_unlock_fn_t unlock_fn,
	futex_wait_get_value_fn_t get_value_fn,
	futex_wait_put_key_fn_t put_key_fn,
	futex_key_refs_fn_t drop_key_refs_fn,
	futex_requeue_scan_fn_t wake_fn, futex_requeue_scan_fn_t requeue_fn);
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
int futex_unqueue_me_result(unsigned long q_addr,
			    unsigned long lock_ptr_offset,
			    unsigned long list_offset,
			    unsigned long node_plist_offset,
			    unsigned long key_offset,
			    futex_hb_lock_fn_t lock_fn,
			    futex_hb_unlock_fn_t unlock_fn,
			    futex_key_refs_fn_t drop_key_refs_fn);
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
int futex_queue_me_result(
	unsigned long q_addr, unsigned long q_list_offset,
	unsigned long q_task_offset, unsigned long q_th_spin_sleep_pa_offset,
	unsigned long q_th_status_pa_offset,
	unsigned long q_th_spin_sleep_lock_pa_offset,
	unsigned long q_proc_status_pa_offset,
	unsigned long q_proc_update_lock_pa_offset,
	unsigned long q_runq_lock_pa_offset,
	unsigned long q_clv_flags_pa_offset,
	unsigned long q_intr_id_offset,
	unsigned long q_intr_vector_offset,
	unsigned long hb_chain_addr, unsigned long hb_lock_addr,
	int prio, unsigned long debug_spinlock_offset,
	unsigned long thread_addr, unsigned long thread_spin_sleep_offset,
	unsigned long thread_status_offset,
	unsigned long thread_spin_sleep_lock_offset,
	unsigned long thread_proc_offset,
	unsigned long thread_cpu_id_offset,
	unsigned long proc_status_offset,
	unsigned long proc_update_lock_offset,
	unsigned long runq_lock_addr, unsigned long clv_flags_addr,
	int vector_key, futex_virt_to_phys_fn_t virt_to_phys_fn,
	futex_interrupt_id_fn_t interrupt_id_fn,
	futex_vector_fn_t vector_fn, futex_hb_unlock_fn_t unlock_fn);
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
int64_t futex_wait_queue_me_result(
	unsigned long hb_addr, unsigned long q_addr,
	unsigned long q_list_offset, unsigned long q_node_plist_offset,
	unsigned long q_plist_node_list_offset,
	unsigned long thread_addr, unsigned long thread_status_offset,
	unsigned long thread_spin_sleep_offset,
	unsigned long thread_spin_sleep_lock_offset,
	unsigned long thread_tid_offset, int idle_halt_enabled,
	uint64_t timeout, int interruptible_status, int running_status,
	futex_wait_spin_lock_fn_t spin_lock_fn,
	futex_wait_spin_unlock_fn_t spin_unlock_fn,
	futex_wait_queue_me_fn_t queue_me_fn,
	futex_wait_schedule_timeout_fn_t schedule_timeout_fn,
	futex_wait_schedule_direct_fn_t schedule_direct_fn,
	futex_wait_queue_log_fn_t log_fn);
int futex_wait_post_action_result(int unqueued, uint64_t timeout,
				  int64_t time_remain,
				  int has_pending_signal,
				  int restart_sys);
int futex_wait_body_result(
	unsigned long uaddr, int fshared, uint32_t val,
	uint64_t timeout, uint32_t bitset,
	unsigned long q_addr, unsigned long thread_addr,
	unsigned long uti_futex_resp,
	unsigned long q_bitset_offset,
	unsigned long q_requeue_pi_key_offset,
	unsigned long q_uti_futex_resp_offset,
	unsigned long q_key_offset,
	unsigned long thread_tid_offset,
	futex_wait_setup_call_fn_t setup_fn,
	futex_wait_queue_call_fn_t wait_queue_fn,
	futex_wait_unqueue_fn_t unqueue_fn,
	futex_wait_has_signal_fn_t has_signal_fn,
	futex_wait_put_key_fn_t put_key_fn,
	futex_wait_log_fn_t log_fn);
int futex_wait_entry_result(
	unsigned long uaddr, int fshared, uint32_t val,
	uint64_t timeout, uint32_t bitset, unsigned long q_addr,
	unsigned long thread_addr, unsigned long uti_futex_resp,
	int profile_enabled, unsigned long thread_profile_offset,
	unsigned long thread_profile_start_ts_offset,
	unsigned long thread_profile_elapsed_ts_offset,
	futex_wait_timestamp_fn_t timestamp_fn,
	futex_wait_body_entry_fn_t wait_body_fn);
int futex_wake_target_result(unsigned long uti_futex_resp);
unsigned long futex_wake_linux_channel_result(unsigned long linux_channel,
					      unsigned long fallback_channel);
void futex_wake_ikc_packet_fill_result(unsigned long packet_addr,
				       unsigned long msg_offset,
				       unsigned long resp_offset,
				       unsigned long spin_sleep_offset,
				       int msg, unsigned long resp,
				       unsigned long spin_sleep_addr);
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
	futex_wake_log_fn_t log_fn);
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
int futex_init_table_result(unsigned long queues_slot_addr, int hashbits,
			    unsigned long bucket_stride, int alloc_flag,
			    futex_alloc_fn_t alloc_fn,
			    unsigned long lock_offset,
			    unsigned long lock_word_offset,
			    unsigned long chain_offset,
			    unsigned long prio_list_offset,
			    unsigned long node_list_offset,
			    unsigned long debug_spinlock_offset,
			    unsigned long debug_rawlock_offset);
unsigned long futex_hash_bucket_result(unsigned long key_addr,
				       unsigned long queues_addr,
				       int hashbits,
				       unsigned long bucket_stride,
				       futex_hash_fn_t hash_fn);
int futex_dispatch_result(int op, unsigned long uaddr, uint32_t val,
			  uint64_t timeout, unsigned long uaddr2,
			  uint32_t val2, uint32_t val3, int fshared,
			  futex_dispatch_wait_fn_t wait_fn,
			  futex_dispatch_wake_fn_t wake_fn,
			  futex_dispatch_requeue_fn_t requeue_fn,
			  futex_dispatch_wake_op_fn_t wake_op_fn,
			  futex_dispatch_invalid_fn_t invalid_fn);
int syscall_offload_should_schedule_result(int no_preempt, int tid,
					   int need_resched, int runq_len,
					   int is_sched_setaffinity);

#endif /* MCKERNEL_SCHED_HELPERS_H */
