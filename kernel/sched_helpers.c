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
#define PS_RUNNING 0x1
#define SCHED_LIST_POISON1 ((unsigned long)0x00100129)
#define SCHED_LIST_POISON2 ((unsigned long)0x00200229)

#ifndef MCKERNEL_RUST_SCHED_RUNTIME_HELPERS

static int plist_node_empty_addr(unsigned long node_addr,
				 unsigned long plist_offset,
				 unsigned long node_list_offset)
{
	unsigned long node_list = node_addr + plist_offset + node_list_offset;

	return *(unsigned long *)node_list == node_list;
}

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

static inline unsigned long list_next_addr(unsigned long list_addr)
{
	return *(unsigned long *)list_addr;
}

static inline unsigned long list_prev_addr(unsigned long list_addr)
{
	return *(unsigned long *)(list_addr + sizeof(unsigned long));
}

static inline int list_empty_raw(unsigned long list_addr)
{
	return list_next_addr(list_addr) == list_addr;
}

static inline void list_del_raw(unsigned long entry_addr)
{
	unsigned long next = list_next_addr(entry_addr);
	unsigned long prev = list_prev_addr(entry_addr);

	*(unsigned long *)(next + sizeof(unsigned long)) = prev;
	*(unsigned long *)prev = next;
}

static inline int list_detach_poison_raw(unsigned long entry_addr)
{
	unsigned long next;
	unsigned long prev;

	if (!entry_addr)
		return 0;
	next = list_next_addr(entry_addr);
	prev = list_prev_addr(entry_addr);
	if (!next || !prev || next == entry_addr)
		return 0;

	*(unsigned long *)(next + sizeof(unsigned long)) = prev;
	*(unsigned long *)prev = next;
	*(unsigned long *)entry_addr = SCHED_LIST_POISON1;
	*(unsigned long *)(entry_addr + sizeof(unsigned long)) =
		SCHED_LIST_POISON2;
	return 1;
}

static inline void list_add_tail_raw(unsigned long entry_addr,
				     unsigned long head_addr)
{
	unsigned long prev = list_prev_addr(head_addr);

	*(unsigned long *)entry_addr = head_addr;
	*(unsigned long *)(entry_addr + sizeof(unsigned long)) = prev;
	*(unsigned long *)prev = entry_addr;
	*(unsigned long *)(head_addr + sizeof(unsigned long)) = entry_addr;
}

static inline int list_detach_counted_raw(unsigned long entry_addr,
					  unsigned long len_addr)
{
	if (!len_addr || !list_detach_poison_raw(entry_addr))
		return 0;
	(*(unsigned long *)len_addr)--;
	return 1;
}

static inline int list_add_tail_counted_raw(unsigned long entry_addr,
					    unsigned long head_addr,
					    unsigned long len_addr)
{
	if (!entry_addr || !head_addr || !len_addr)
		return 0;
	list_add_tail_raw(entry_addr, head_addr);
	(*(unsigned long *)len_addr)++;
	return 1;
}

int timer_init_timers_result(unsigned long timers_lock_addr,
			     unsigned long timers_head_addr,
			     timer_spin_init_fn_t spin_init_fn)
{
	if (!timers_lock_addr || !timers_head_addr || !spin_init_fn)
		return -EINVAL;

	spin_init_fn(timers_lock_addr);
	init_list_head_addr(timers_head_addr);
	return 0;
}

uint64_t timer_schedule_timeout_body_result(
	unsigned long thread_addr, unsigned long cpu_local_addr,
	uint64_t timeout, uint64_t loop_timeout,
	const struct timer_runtime_offsets *offsets,
	timer_rdtsc_fn_t rdtsc_fn, timer_spin_lock_fn_t spin_lock_fn,
	timer_spin_unlock_fn_t spin_unlock_fn,
	timer_set_status_fn_t set_status_fn, timer_void_fn_t schedule_fn,
	timer_void_fn_t zero_free_fn, timer_void_fn_t pause_fn)
{
	unsigned long thread_spin_lock_addr;
	unsigned long thread_spin_sleep_addr;
	unsigned long thread_status_addr;
	unsigned long runq_lock_addr;
	unsigned long runq_len_addr;

	if (!thread_addr || !cpu_local_addr || !offsets || !loop_timeout)
		return timeout;
	if (!rdtsc_fn || !spin_lock_fn || !spin_unlock_fn || !set_status_fn ||
			!schedule_fn || !zero_free_fn || !pause_fn)
		return timeout;

	thread_spin_lock_addr = thread_addr + offsets->thread_spin_sleep_lock_offset;
	thread_spin_sleep_addr = thread_addr + offsets->thread_spin_sleep_offset;
	thread_status_addr = thread_addr + offsets->thread_status_offset;
	runq_lock_addr = cpu_local_addr + offsets->cpu_runq_lock_offset;
	runq_len_addr = cpu_local_addr + offsets->cpu_runq_len_offset;

	for (;;) {
		uint64_t t_s = rdtsc_fn();
		unsigned long irqstate = spin_lock_fn(thread_spin_lock_addr);

		if (*(int *)thread_spin_sleep_addr == 0) {
			uint64_t t_e = rdtsc_fn();

			timeout = timer_spin_sleep_remaining_result(timeout,
					t_e - t_s);
			spin_unlock_fn(thread_spin_lock_addr, irqstate);
			break;
		}

		spin_unlock_fn(thread_spin_lock_addr, irqstate);

		irqstate = spin_lock_fn(runq_lock_addr);
		if (timer_runq_should_schedule_result(
					*(size_t *)runq_len_addr)) {
			set_status_fn(thread_status_addr, PS_RUNNING);
			spin_unlock_fn(runq_lock_addr, irqstate);
			schedule_fn();
			continue;
		}
		spin_unlock_fn(runq_lock_addr, irqstate);

		while ((rdtsc_fn() - t_s) < loop_timeout) {
			zero_free_fn();
			pause_fn();
		}

		timeout = timer_after_spin_remaining_result(timeout,
				loop_timeout);
		if (!timeout) {
			irqstate = spin_lock_fn(thread_spin_lock_addr);
			*(int *)thread_spin_sleep_addr = 0;
			spin_unlock_fn(thread_spin_lock_addr, irqstate);
			break;
		}
	}

	return timeout;
}

int timer_wake_tick_result(unsigned long timers_lock_addr,
			   unsigned long timers_head_addr,
			   uint64_t loop_timeout,
			   const struct timer_runtime_offsets *offsets,
			   timer_spin_lock_fn_t lock_fn,
			   timer_spin_unlock_fn_t unlock_fn,
			   timer_waitq_wakeup_fn_t wake_fn,
			   timer_log_wake_fn_t log_fn)
{
	unsigned long irqstate;
	unsigned long entry;
	int woken = 0;

	if (!timers_lock_addr || !timers_head_addr || !offsets || !loop_timeout)
		return -EINVAL;
	if (!lock_fn || !unlock_fn || !wake_fn)
		return -EINVAL;

	irqstate = lock_fn(timers_lock_addr);
	entry = list_next_addr(timers_head_addr);
	while (entry != timers_head_addr) {
		unsigned long next = list_next_addr(entry);
		unsigned long timer = entry - offsets->timer_list_offset;
		uint64_t *timeoutp =
			(uint64_t *)(timer + offsets->timer_timeout_offset);
		uint64_t next_timeout =
			timer_after_tick_remaining_result(*timeoutp,
							  loop_timeout);

		*timeoutp = next_timeout;
		if (!next_timeout) {
			unsigned long thread_addr =
				*(unsigned long *)(timer + offsets->timer_thread_offset);

			list_del_raw(entry);
			if (log_fn)
				log_fn(timer, thread_addr);
			wake_fn(timer + offsets->timer_waitq_offset);
			woken++;
		}
		entry = next;
	}
	unlock_fn(timers_lock_addr, irqstate);

	return woken;
}

int timer_wake_loop_body_result(unsigned long timers_lock_addr,
				unsigned long timers_head_addr,
				uint64_t loop_timeout, int max_ticks,
				const struct timer_runtime_offsets *offsets,
				timer_rdtsc_fn_t rdtsc_fn,
				timer_void_fn_t pause_fn,
				timer_spin_lock_fn_t lock_fn,
				timer_spin_unlock_fn_t unlock_fn,
				timer_waitq_wakeup_fn_t wake_fn,
				timer_log_wake_fn_t log_fn)
{
	int ticks = 0;

	if (max_ticks < 0)
		return -EINVAL;
	if (!rdtsc_fn || !pause_fn)
		return -EINVAL;

	for (;;) {
		uint64_t loop_s = rdtsc_fn();

		while (rdtsc_fn() < loop_s + loop_timeout)
			pause_fn();

		timer_wake_tick_result(timers_lock_addr, timers_head_addr,
				loop_timeout, offsets, lock_fn, unlock_fn,
				wake_fn, log_fn);
		ticks++;
		if (max_ticks > 0 && ticks >= max_ticks)
			return ticks;
	}
}

int timer_set_timer_body_result(unsigned long cpu_local_addr, int time_sharing,
				int runq_locked,
				const struct timer_runtime_offsets *offsets,
				timer_spin_lock_fn_t lock_fn,
				timer_spin_unlock_fn_t unlock_fn,
				timer_lapic_enable_fn_t enable_fn,
				timer_lapic_disable_fn_t disable_fn)
{
	unsigned long runq_lock_addr;
	unsigned long irqstate = 0;
	unsigned long runq_head;
	unsigned long entry;
	unsigned long current_thread;
	int current_itimer_enabled = 0;
	int backlog_not_empty;
	int should_enable;
	int *timer_enabledp;
	int num_running = 0;

	if (!time_sharing)
		return 0;
	if (!cpu_local_addr || !offsets)
		return -EINVAL;
	if (!lock_fn || !unlock_fn || !enable_fn || !disable_fn)
		return -EINVAL;

	runq_lock_addr = cpu_local_addr + offsets->cpu_runq_lock_offset;
	if (!runq_locked)
		irqstate = lock_fn(runq_lock_addr);

	runq_head = cpu_local_addr + offsets->cpu_runq_offset;
	for (entry = list_next_addr(runq_head); entry != runq_head;
			entry = list_next_addr(entry)) {
		unsigned long thread = entry - offsets->thread_sched_list_offset;
		int status = *(int *)(thread + offsets->thread_status_offset);
		int spin_sleep =
			*(int *)(thread + offsets->thread_spin_sleep_offset);

		if (status == PS_RUNNING || spin_sleep)
			num_running++;
	}

	current_thread =
		*(unsigned long *)(cpu_local_addr + offsets->cpu_current_offset);
	if (current_thread)
		current_itimer_enabled = *(int *)(current_thread +
				offsets->thread_itimer_enabled_offset);
	backlog_not_empty = !list_empty_raw(cpu_local_addr +
			offsets->cpu_backlog_list_offset);
	should_enable = num_running > 1 || current_itimer_enabled ||
		backlog_not_empty;
	timer_enabledp = (int *)(cpu_local_addr + offsets->cpu_timer_enabled_offset);

	if (should_enable) {
		if (!*timer_enabledp) {
			enable_fn(1000000);
			*timer_enabledp = 1;
		}
	} else if (*timer_enabledp) {
		disable_fn();
		*timer_enabledp = 0;
	}

	if (!runq_locked)
		unlock_fn(runq_lock_addr, irqstate);

	return num_running;
}

int sched_release_cpuid_body_result(
	int cpuid, unsigned long cpu_addr, unsigned long reservation_lock_addr,
	int idle_status, const struct sched_runqueue_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_migrate_noirq_lock_fn_t noirq_lock_fn,
	sched_migrate_noirq_unlock_fn_t noirq_unlock_fn)
{
	unsigned long irqstate;
	unsigned long runq_lock_addr;
	size_t *runq_lenp;
	size_t *reservedp;

	(void)cpuid;
	if (!cpu_addr || !reservation_lock_addr || !offsets)
		return -EINVAL;
	if (!lock_fn || !unlock_fn || !noirq_lock_fn || !noirq_unlock_fn)
		return -EINVAL;

	irqstate = lock_fn(reservation_lock_addr);
	runq_lock_addr = cpu_addr + offsets->cpu_runq_lock_offset;
	noirq_lock_fn(runq_lock_addr);

	runq_lenp = (size_t *)(cpu_addr + offsets->cpu_runq_len_offset);
	if (!*runq_lenp)
		*(int *)(cpu_addr + offsets->cpu_status_offset) = idle_status;

	reservedp = (size_t *)(cpu_addr + offsets->cpu_runq_reserved_offset);
	--*reservedp;

	noirq_unlock_fn(runq_lock_addr);
	unlock_fn(reservation_lock_addr, irqstate);
	return 0;
}

int sched_check_need_resched_body_result(
	unsigned long cpu_addr, unsigned int need_resched_flag,
	unsigned int need_migrate_flag,
	const struct sched_runqueue_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_migrate_void_fn_t schedule_fn,
	sched_runq_log_fn_t log_fn)
{
	unsigned long runq_lock_addr;
	unsigned long irqstate;
	unsigned int *flagsp;

	if (!cpu_addr || !offsets)
		return -EINVAL;
	if (!lock_fn || !unlock_fn || !schedule_fn)
		return -EINVAL;

	runq_lock_addr = cpu_addr + offsets->cpu_runq_lock_offset;
	irqstate = lock_fn(runq_lock_addr);
	flagsp = (unsigned int *)(cpu_addr + offsets->cpu_flags_offset);
	if (!(*flagsp & need_resched_flag)) {
		unlock_fn(runq_lock_addr, irqstate);
		return 0;
	}

	if (*(int *)(cpu_addr + offsets->cpu_in_interrupt_offset) &&
			(*flagsp & need_migrate_flag)) {
		if (log_fn)
			log_fn(SCHED_RUNQ_LOG_NO_MIGRATION_IRQ,
			       cpu_addr, 0, 0, 0);
		unlock_fn(runq_lock_addr, irqstate);
		return 0;
	}

	*flagsp &= ~need_resched_flag;
	unlock_fn(runq_lock_addr, irqstate);
	schedule_fn();
	return 1;
}

int sched_runq_add_thread_locked_result(
	unsigned long thread_addr, unsigned long cpu_addr, int cpu_id,
	unsigned int need_resched_flag, int running_status,
	const struct sched_runqueue_offsets *offsets,
	sched_runq_log_fn_t log_fn)
{
	if (!thread_addr || !cpu_addr || !offsets)
		return -EINVAL;

	list_add_tail_counted_raw(thread_addr + offsets->thread_sched_list_offset,
				  cpu_addr + offsets->cpu_runq_offset,
				  cpu_addr + offsets->cpu_runq_len_offset);
	*(unsigned int *)(cpu_addr + offsets->cpu_flags_offset) |=
		need_resched_flag;
	*(int *)(thread_addr + offsets->thread_cpu_id_offset) = cpu_id;
	*(int *)(cpu_addr + offsets->cpu_status_offset) = running_status;

	if (log_fn) {
		int tid = *(int *)(thread_addr + offsets->thread_tid_offset);
		log_fn(SCHED_RUNQ_LOG_RUNQ_ADD, thread_addr, cpu_addr,
		       tid, cpu_id);
	}
	return 0;
}

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
	sched_runq_log_fn_t log_fn)
{
	unsigned long irqstate;
	unsigned long runq_lock_addr;
	unsigned long proc_addr;
	int clone_count;
	int rc;

	if (!thread_addr || !cpu_addr || !reservation_lock_addr || !offsets)
		return -EINVAL;
	if (!lock_fn || !unlock_fn || !noirq_lock_fn || !noirq_unlock_fn ||
	    !reserved_dec_fn || !procfs_create_fn || !clone_count_inc_fn ||
	    !rusage_inc_fn || !rusage_debug_fn || !vector_fn || !interrupt_fn)
		return -EINVAL;

	irqstate = lock_fn(reservation_lock_addr);
	runq_lock_addr = cpu_addr + offsets->cpu_runq_lock_offset;
	noirq_lock_fn(runq_lock_addr);
	rc = sched_runq_add_thread_locked_result(thread_addr, cpu_addr, cpu_id,
		need_resched_flag, running_status, offsets, log_fn);
	reserved_dec_fn(cpu_addr + offsets->cpu_runq_reserved_offset);
	noirq_unlock_fn(runq_lock_addr);
	unlock_fn(reservation_lock_addr, irqstate);
	if (rc)
		return rc;

	procfs_create_fn(thread_addr);

	proc_addr = *(unsigned long *)(thread_addr + offsets->thread_proc_offset);
	clone_count = proc_addr ?
		clone_count_inc_fn(proc_addr + offsets->proc_clone_count_offset) :
		0;
	if (log_fn)
		log_fn(SCHED_RUNQ_LOG_CLONE_COUNT, thread_addr, proc_addr,
		       clone_count, 0);

	rusage_inc_fn();
	rusage_debug_fn();

	if (cpu_id != current_cpu_id)
		interrupt_fn(cpu_id, vector_fn(vector_key));
	return 0;
}

int sched_runq_del_thread_body_result(
	unsigned long thread_addr, unsigned long cpu_addr, int idle_status,
	const struct sched_runqueue_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_spin_unlock_fn_t unlock_fn)
{
	unsigned long runq_lock_addr;
	unsigned long irqstate;

	if (!thread_addr || !cpu_addr || !offsets)
		return -EINVAL;
	if (!lock_fn || !unlock_fn)
		return -EINVAL;

	runq_lock_addr = cpu_addr + offsets->cpu_runq_lock_offset;
	irqstate = lock_fn(runq_lock_addr);
	list_detach_counted_raw(thread_addr + offsets->thread_sched_list_offset,
				cpu_addr + offsets->cpu_runq_len_offset);
	if (!*(size_t *)(cpu_addr + offsets->cpu_runq_len_offset))
		*(int *)(cpu_addr + offsets->cpu_status_offset) = idle_status;
	unlock_fn(runq_lock_addr, irqstate);
	return 0;
}

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
	sched_runq_log_fn_t log_fn)
{
	unsigned long proc_addr;
	unsigned long spin_lock_addr;
	unsigned long spin_sleep_addr;
	unsigned long irqstate;
	unsigned long runq_lock_addr;
	unsigned long runq_irqstate = 0;
	int thread_cpu;
	int status;

	if (!thread_addr || !cpu_addr || !update_lock_node_addr || !offsets)
		return -EINVAL;
	if (!lock_fn || !unlock_fn || !rwlock_fn || !rwunlock_fn ||
			!status_set_fn || !set_timer_fn || !vector_fn ||
			!interrupt_fn)
		return -EINVAL;

	proc_addr = *(unsigned long *)(thread_addr + offsets->thread_proc_offset);
	thread_cpu = *(int *)(thread_addr + offsets->thread_cpu_id_offset);
	if (log_fn) {
		int proc_pid = proc_addr ?
			*(int *)(proc_addr + offsets->proc_pid_offset) : -1;
		log_fn(SCHED_RUNQ_LOG_WAKE_ENTRY, thread_addr, proc_addr,
		       proc_pid, valid_states);
	}

	spin_lock_addr = thread_addr + offsets->thread_spin_sleep_lock_offset;
	spin_sleep_addr = thread_addr + offsets->thread_spin_sleep_offset;
	irqstate = lock_fn(spin_lock_addr);
	if (*(int *)spin_sleep_addr == 1 && log_fn)
		log_fn(SCHED_RUNQ_LOG_SPIN_WAKEUP, thread_addr, 0,
		       thread_cpu, valid_states);
	*(int *)spin_sleep_addr = 0;
	unlock_fn(spin_lock_addr, irqstate);

	runq_lock_addr = cpu_addr + offsets->cpu_runq_lock_offset;
	if (!runq_locked)
		runq_irqstate = lock_fn(runq_lock_addr);

	if (*(int *)(thread_addr + offsets->thread_status_offset) &
			valid_states) {
		if (proc_addr) {
			unsigned long proc_lock_addr =
				proc_addr + offsets->proc_update_lock_offset;
			int *proc_statusp =
				(int *)(proc_addr + offsets->proc_status_offset);

			rwlock_fn(proc_lock_addr, update_lock_node_addr);
			if (*proc_statusp != exited_status)
				*proc_statusp = running_status;
			rwunlock_fn(proc_lock_addr, update_lock_node_addr);
		}
		status_set_fn(thread_addr + offsets->thread_status_offset,
			      running_status);
		*(unsigned int *)(cpu_addr + offsets->cpu_flags_offset) |=
			need_resched_flag;
		if (thread_cpu == current_cpu_id)
			set_timer_fn(1);
		status = 0;
	} else {
		status = -EINVAL;
	}

	if (!runq_locked)
		unlock_fn(runq_lock_addr, runq_irqstate);

	if (!status && thread_cpu != current_cpu_id) {
		if (log_fn)
			log_fn(SCHED_RUNQ_LOG_REMOTE_IPI, thread_addr,
			       cpu_addr, thread_cpu, vector_key);
		interrupt_fn(thread_cpu, vector_fn(vector_key));
	}
	return status;
}

static int sched_thread_has_pending_signal_raw(
	unsigned long thread_addr, const struct sched_runqueue_offsets *offsets,
	sched_runq_has_signal_fn_t has_signal_fn)
{
	unsigned long sigcommon;
	int thread_pending;
	int common_pending = 0;

	thread_pending = !list_empty_raw(thread_addr +
			offsets->thread_sigpending_offset);
	sigcommon = *(unsigned long *)(thread_addr +
			offsets->thread_sigcommon_offset);
	if (sigcommon)
		common_pending = !list_empty_raw(sigcommon +
				offsets->sigcommon_sigpending_offset);

	return (thread_pending || common_pending) &&
		has_signal_fn(thread_addr);
}

static void sched_write_schedule_result(
	struct sched_schedule_result *result, unsigned long cpu_addr,
	unsigned long prev_thread_addr, unsigned long next_thread_addr,
	int prevpid, int switch_ctx, int action)
{
	result->cpu_addr = cpu_addr;
	result->prev_thread_addr = prev_thread_addr;
	result->next_thread_addr = next_thread_addr;
	result->prevpid = prevpid;
	result->switch_ctx = switch_ctx;
	result->action = action;
}

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
	sched_runq_log_fn_t log_fn)
{
	unsigned long runq_lock_addr;
	unsigned long flags_addr;
	unsigned long irqstate;
	unsigned long prev_thread_addr;
	unsigned long next_thread_addr = 0;
	int old_prevpid;
	unsigned int flags;
	int prev_exited = 0;
	int switch_ctx = 0;
	int action;

	if (!cpu_addr || !idle_thread_addr || !offsets || !result)
		return -EINVAL;
	if (!irq_save_fn || !irq_restore_fn || !noirq_lock_fn ||
			!noirq_unlock_fn || !set_timer_fn ||
			!reset_cputime_fn || !has_signal_fn)
		return -EINVAL;

	sched_write_schedule_result(result, cpu_addr, 0, 0, 0, 0, 0);
	runq_lock_addr = cpu_addr + offsets->cpu_runq_lock_offset;
	flags_addr = cpu_addr + offsets->cpu_flags_offset;

	if (no_preempt_count) {
		if (log_fn)
			log_fn(SCHED_RUNQ_LOG_NO_PREEMPT, cpu_addr,
			       runq_lock_addr, no_preempt_count, 0);
		irqstate = irq_save_fn();
		noirq_lock_fn(runq_lock_addr);
		*(unsigned int *)flags_addr |= need_resched_flag;
		noirq_unlock_fn(runq_lock_addr);
		irq_restore_fn(irqstate);
		sched_write_schedule_result(result, cpu_addr, 0, 0, 0, 0,
					    SCHED_SCHEDULE_ACTION_RESCHED_ONLY);
		return SCHED_SCHEDULE_ACTION_RESCHED_ONLY;
	}

	irqstate = irq_save_fn();
	noirq_lock_fn(runq_lock_addr);
	*(unsigned long *)(cpu_addr + offsets->cpu_runq_irqstate_offset) =
		irqstate;
	prev_thread_addr =
		*(unsigned long *)(cpu_addr + offsets->cpu_current_offset);
	old_prevpid = *(int *)(cpu_addr + offsets->cpu_prevpid_offset);

	if (prev_thread_addr && prev_thread_addr != idle_thread_addr) {
		list_detach_counted_raw(prev_thread_addr +
					offsets->thread_sched_list_offset,
					cpu_addr + offsets->cpu_runq_len_offset);
		if (*(int *)(prev_thread_addr + offsets->thread_status_offset) !=
				exited_status)
			list_add_tail_counted_raw(prev_thread_addr +
					offsets->thread_sched_list_offset,
					cpu_addr + offsets->cpu_runq_offset,
					cpu_addr + offsets->cpu_runq_len_offset);
	}

	flags = *(unsigned int *)flags_addr;
	if (prev_thread_addr &&
			*(int *)(prev_thread_addr +
				 offsets->thread_status_offset) ==
			exited_status)
		prev_exited = 1;

	if ((flags & need_migrate_flag) || prev_exited) {
		next_thread_addr = idle_thread_addr;
	}
	else {
		unsigned long runq_head = cpu_addr + offsets->cpu_runq_offset;
		unsigned long entry;

		for (entry = list_next_addr(runq_head); entry != runq_head;
				entry = list_next_addr(entry)) {
			unsigned long thread_addr =
				entry - offsets->thread_sched_list_offset;
			int status = *(int *)(thread_addr +
					offsets->thread_status_offset);
			int mod_clone = *(int *)(thread_addr +
					offsets->thread_mod_clone_offset);

			if (status == running_status &&
					mod_clone == spawning_to_remote) {
				next_thread_addr = thread_addr;
				break;
			}
			if (status == running_status ||
					(status == interruptible_status &&
					 sched_thread_has_pending_signal_raw(
						thread_addr, offsets,
						has_signal_fn))) {
				if (!next_thread_addr)
					next_thread_addr = thread_addr;
			}
		}

		if (!next_thread_addr) {
			size_t runq_len = *(size_t *)(cpu_addr +
					offsets->cpu_runq_len_offset);
			next_thread_addr = idle_thread_addr;
			*(int *)(cpu_addr + offsets->cpu_status_offset) =
				runq_len ? reserved_cpu_status : idle_cpu_status;
		}
	}

	if (prev_thread_addr != next_thread_addr) {
		int new_prevpid = 0;

		switch_ctx = 1;
		if (prev_thread_addr) {
			unsigned long proc_addr = *(unsigned long *)
				(prev_thread_addr + offsets->thread_proc_offset);
			if (proc_addr)
				new_prevpid = *(int *)(proc_addr +
						offsets->proc_pid_offset);
		}
		*(int *)(cpu_addr + offsets->cpu_prevpid_offset) = new_prevpid;
		*(unsigned long *)(cpu_addr + offsets->cpu_current_offset) =
			next_thread_addr;
		reset_cputime_fn();
		++*(unsigned long *)(cpu_addr +
				     offsets->cpu_nr_ctx_switches_offset);
	}

	set_timer_fn(1);

	if (switch_ctx) {
		action = SCHED_SCHEDULE_ACTION_SWITCH;
	}
	else {
		noirq_unlock_fn(runq_lock_addr);
		irq_restore_fn(irqstate);
		action = SCHED_SCHEDULE_ACTION_NO_SWITCH;
	}

	sched_write_schedule_result(result, cpu_addr, prev_thread_addr,
				    next_thread_addr, old_prevpid, switch_ctx,
				    action);
	return action;
}

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
	sched_runq_log_fn_t log_fn)
{
	unsigned long thread_spin_lock_addr;
	unsigned long thread_spin_sleep_addr;
	unsigned long runq_lock_addr;
	unsigned long runq_len_addr;
	unsigned long flags_addr;
	int tid;
	unsigned long irqstate;

	if (!thread_addr || !cpu_addr || !offsets)
		return -EINVAL;
	if (!irq_save_fn || !irq_restore_fn || !lock_fn || !unlock_fn ||
			!noirq_lock_fn || !noirq_unlock_fn || !schedule_fn ||
			!zero_free_fn || !pause_fn || !has_signal_fn)
		return -EINVAL;

	thread_spin_lock_addr = thread_addr +
		offsets->thread_spin_sleep_lock_offset;
	thread_spin_sleep_addr = thread_addr + offsets->thread_spin_sleep_offset;
	runq_lock_addr = cpu_addr + offsets->cpu_runq_lock_offset;
	runq_len_addr = cpu_addr + offsets->cpu_runq_len_offset;
	flags_addr = cpu_addr + offsets->cpu_flags_offset;
	tid = *(int *)(thread_addr + offsets->thread_tid_offset);

	if (idle_halt_enabled) {
		if (log_fn)
			log_fn(SCHED_RUNQ_LOG_IDLE_HALT, thread_addr, cpu_addr,
			       tid, current_cpu_id);
		schedule_fn();
		if (log_fn)
			log_fn(SCHED_RUNQ_LOG_SLEEP_WOKEN, thread_addr,
			       cpu_addr, tid, current_cpu_id);
		return 2;
	}

	irqstate = lock_fn(thread_spin_lock_addr);
	if (*(int *)thread_spin_sleep_addr == 0 && log_fn)
		log_fn(SCHED_RUNQ_LOG_LOST_WAKEUP, thread_addr, cpu_addr,
		       tid, current_cpu_id);
	unlock_fn(thread_spin_lock_addr, irqstate);

	for (;;) {
		int do_schedule = 0;
		int woken = 0;
		unsigned int flags;

		irqstate = irq_save_fn();
		noirq_lock_fn(runq_lock_addr);
		flags = *(unsigned int *)flags_addr;
		if ((flags & need_resched_flag) ||
				*(size_t *)runq_len_addr > 1) {
			*(unsigned int *)flags_addr = flags & ~need_resched_flag;
			do_schedule = 1;
		}
		noirq_unlock_fn(runq_lock_addr);
		irq_restore_fn(irqstate);

		irqstate = lock_fn(thread_spin_lock_addr);
		if (*(int *)thread_spin_sleep_addr == 0)
			woken = 1;
		if (do_schedule)
			*(int *)thread_spin_sleep_addr = 0;
		unlock_fn(thread_spin_lock_addr, irqstate);

		if (sched_thread_has_pending_signal_raw(thread_addr, offsets,
					has_signal_fn))
			woken = 1;

		if (woken) {
			if (log_fn)
				log_fn(SCHED_RUNQ_LOG_SPIN_WOKEN, thread_addr,
				       cpu_addr, tid, do_schedule);
			if (do_schedule) {
				irqstate = lock_fn(runq_lock_addr);
				*(unsigned int *)flags_addr |= need_resched_flag;
				unlock_fn(runq_lock_addr, irqstate);
			}
			return 1;
		}

		if (do_schedule)
			break;

		zero_free_fn();
		pause_fn();
	}

	schedule_fn();
	if (log_fn)
		log_fn(SCHED_RUNQ_LOG_SLEEP_WOKEN, thread_addr, cpu_addr,
		       tid, current_cpu_id);
	return 2;
}

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
	sched_migrate_log_fn_t log_fn)
{
	unsigned long migq_lock_addr;
	unsigned long runq_lock_addr;
	unsigned long waitq_addr;
	unsigned long req_list_addr;
	unsigned long irqstate;

	if (!target_cpu_addr || !req_addr || !wait_entry_addr ||
			!thread_addr || !offsets)
		return -EINVAL;
	if (!lock_fn || !unlock_fn || !noirq_lock_fn || !noirq_unlock_fn ||
			!waitq_init_fn || !waitq_prepare_fn ||
			!waitq_finish_fn || !schedule_fn)
		return -EINVAL;
	if (target_cpu_id != current_cpu_id && (!vector_fn || !interrupt_fn))
		return -EINVAL;

	*(unsigned long *)(req_addr + offsets->req_thread_offset) = thread_addr;
	migq_lock_addr = target_cpu_addr + offsets->cpu_migq_lock_offset;
	runq_lock_addr = target_cpu_addr + offsets->cpu_runq_lock_offset;
	waitq_addr = req_addr + offsets->req_wq_offset;
	req_list_addr = req_addr + offsets->req_list_offset;

	irqstate = lock_fn(migq_lock_addr);
	waitq_init_fn(waitq_addr);
	waitq_prepare_fn(waitq_addr, wait_entry_addr, wait_status);
	list_add_tail_raw(req_list_addr,
			  target_cpu_addr + offsets->cpu_migq_offset);

	noirq_lock_fn(runq_lock_addr);
	*(unsigned int *)(target_cpu_addr + offsets->cpu_flags_offset) |=
		need_resched_flag | need_migrate_flag;
	*(int *)(target_cpu_addr + offsets->cpu_status_offset) =
		running_status;
	noirq_unlock_fn(runq_lock_addr);

	if (target_cpu_id != current_cpu_id) {
		int thread_cpu_id = *(int *)(thread_addr +
				offsets->thread_cpu_id_offset);
		interrupt_fn(thread_cpu_id, vector_fn(vector_key));
	}

	if (log_fn) {
		int tid = *(int *)(thread_addr + offsets->thread_tid_offset);
		log_fn(thread_addr, tid, target_cpu_id);
	}

	unlock_fn(migq_lock_addr, irqstate);
	schedule_fn();
	waitq_finish_fn(waitq_addr, wait_entry_addr);

	return 1;
}

static int cpu_set_word(unsigned long set_addr, int cpu, int cpu_set_bits,
			unsigned long *word_addrp, unsigned long *maskp)
{
	unsigned long word;
	unsigned long bit;

	if (!set_addr || cpu < 0 || cpu_set_bits <= 0 || cpu >= cpu_set_bits)
		return 0;

	word = (unsigned long)cpu / (8 * sizeof(unsigned long));
	bit = (unsigned long)cpu % (8 * sizeof(unsigned long));
	*word_addrp = set_addr + word * sizeof(unsigned long);
	*maskp = 1UL << bit;
	return 1;
}

static int cpu_set_isset_raw(unsigned long set_addr, int cpu, int cpu_set_bits)
{
	unsigned long word_addr;
	unsigned long mask;

	if (!cpu_set_word(set_addr, cpu, cpu_set_bits, &word_addr, &mask))
		return 0;

	return !!(*(unsigned long *)word_addr & mask);
}

static int cpu_set_bit_raw(unsigned long set_addr, int cpu, int cpu_set_bits)
{
	unsigned long word_addr;
	unsigned long mask;

	if (!cpu_set_word(set_addr, cpu, cpu_set_bits, &word_addr, &mask))
		return 0;

	*(unsigned long *)word_addr |= mask;
	return 1;
}

static int cpu_clear_bit_raw(unsigned long set_addr, int cpu, int cpu_set_bits)
{
	unsigned long word_addr;
	unsigned long mask;

	if (!cpu_set_word(set_addr, cpu, cpu_set_bits, &word_addr, &mask))
		return 0;

	*(unsigned long *)word_addr &= ~mask;
	return 1;
}

static unsigned long sched_double_rq_lock_raw(
	unsigned long current_cpu_addr, unsigned long target_cpu_addr,
	const struct sched_do_migrate_offsets *offsets,
	sched_migrate_spin_lock_fn_t lock_fn,
	sched_migrate_noirq_lock_fn_t noirq_lock_fn)
{
	unsigned long current_lock =
		current_cpu_addr + offsets->cpu_runq_lock_offset;
	unsigned long target_lock =
		target_cpu_addr + offsets->cpu_runq_lock_offset;
	unsigned long irqstate;

	if (current_cpu_addr < target_cpu_addr) {
		irqstate = lock_fn(current_lock);
		noirq_lock_fn(target_lock);
	} else {
		irqstate = lock_fn(target_lock);
		noirq_lock_fn(current_lock);
	}

	return irqstate;
}

static void sched_double_rq_unlock_raw(
	unsigned long current_cpu_addr, unsigned long target_cpu_addr,
	unsigned long irqstate,
	const struct sched_do_migrate_offsets *offsets,
	sched_migrate_spin_unlock_fn_t unlock_fn,
	sched_migrate_noirq_unlock_fn_t noirq_unlock_fn)
{
	noirq_unlock_fn(current_cpu_addr + offsets->cpu_runq_lock_offset);
	unlock_fn(target_cpu_addr + offsets->cpu_runq_lock_offset, irqstate);
}

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
	sched_do_migrate_log_fn_t log_fn)
{
	unsigned long migq_lock_addr;
	unsigned long migq_head;
	unsigned long irqstate;
	unsigned long entry;
	int processed = 0;

	if (!current_cpu_addr || cpu_set_bits <= 0 || !offsets)
		return -EINVAL;
	if (!lock_fn || !unlock_fn || !noirq_lock_fn || !noirq_unlock_fn ||
			!cpu_local_fn || !waitq_wakeup_fn || !vector_fn ||
			!interrupt_fn)
		return -EINVAL;

	migq_lock_addr = current_cpu_addr + offsets->cpu_migq_lock_offset;
	migq_head = current_cpu_addr + offsets->cpu_migq_offset;
	irqstate = lock_fn(migq_lock_addr);

	for (entry = list_next_addr(migq_head); entry != migq_head;) {
		unsigned long next = list_next_addr(entry);
		unsigned long req_addr = entry - offsets->req_list_offset;
		unsigned long thread_addr =
			*(unsigned long *)(req_addr + offsets->req_thread_offset);
		int thread_cpu_id;
		unsigned long thread_cpu_set;
		int target_cpu_id;
		unsigned long target_cpu_addr;
		int old_cpu_id;
		unsigned long moving_vm;
		int clear_old_cpu = 1;
		unsigned long runq_head;
		unsigned long runq_entry;

		processed++;
		list_detach_poison_raw(entry);

		if (!thread_addr)
			goto ack;

		thread_cpu_id =
			*(int *)(thread_addr + offsets->thread_cpu_id_offset);
		if (thread_cpu_id != current_cpu_id)
			goto ack;

		thread_cpu_set = thread_addr + offsets->thread_cpu_set_offset;
		if (cpu_set_isset_raw(thread_cpu_set, current_cpu_id,
				      cpu_set_bits))
			goto ack;

		for (target_cpu_id = 0; target_cpu_id < cpu_set_bits;
				target_cpu_id++) {
			if (cpu_set_isset_raw(thread_cpu_set, target_cpu_id,
					      cpu_set_bits))
				break;
		}
		if (target_cpu_id == cpu_set_bits)
			goto ack;

		target_cpu_addr = cpu_local_fn(target_cpu_id);
		if (!target_cpu_addr)
			goto ack;

		irqstate = sched_double_rq_lock_raw(current_cpu_addr,
				target_cpu_addr, offsets, lock_fn, noirq_lock_fn);
		list_detach_counted_raw(thread_addr +
				offsets->thread_sched_list_offset,
				current_cpu_addr + offsets->cpu_runq_len_offset);
		old_cpu_id = *(int *)(thread_addr + offsets->thread_cpu_id_offset);
		*(int *)(thread_addr + offsets->thread_cpu_id_offset) =
			target_cpu_id;
		list_add_tail_counted_raw(thread_addr +
				offsets->thread_sched_list_offset,
				target_cpu_addr + offsets->cpu_runq_offset,
				target_cpu_addr + offsets->cpu_runq_len_offset);

		moving_vm = *(unsigned long *)(thread_addr +
				offsets->thread_vm_offset);
		runq_head = current_cpu_addr + offsets->cpu_runq_offset;
		for (runq_entry = list_next_addr(runq_head);
				runq_entry != runq_head;
				runq_entry = list_next_addr(runq_entry)) {
			unsigned long candidate =
				runq_entry - offsets->thread_sched_list_offset;
			unsigned long candidate_vm =
				*(unsigned long *)(candidate +
						offsets->thread_vm_offset);
			if (candidate_vm && candidate_vm == moving_vm) {
				clear_old_cpu = 0;
				break;
			}
		}

		if (moving_vm) {
			unsigned long address_space =
				*(unsigned long *)(moving_vm +
						offsets->vm_address_space_offset);
			if (address_space) {
				unsigned long cpu_set_addr = address_space +
					offsets->address_space_cpu_set_offset;
				unsigned long cpu_set_lock_addr = address_space +
					offsets->address_space_cpu_set_lock_offset;
				unsigned long cpu_set_irqstate =
					lock_fn(cpu_set_lock_addr);

				if (clear_old_cpu)
					cpu_clear_bit_raw(cpu_set_addr, old_cpu_id,
							  cpu_set_bits);
				cpu_set_bit_raw(cpu_set_addr, target_cpu_id,
						cpu_set_bits);
				unlock_fn(cpu_set_lock_addr, cpu_set_irqstate);
			}
		}

		if (log_fn) {
			int tid = *(int *)(thread_addr + offsets->thread_tid_offset);
			log_fn(thread_addr, tid, old_cpu_id, target_cpu_id);
		}

		*(unsigned int *)(target_cpu_addr + offsets->cpu_flags_offset) |=
			need_resched_flag;
		interrupt_fn(target_cpu_id, vector_fn(vector_key));
		waitq_wakeup_fn(req_addr + offsets->req_wq_offset);
		sched_double_rq_unlock_raw(current_cpu_addr, target_cpu_addr,
				irqstate, offsets, unlock_fn, noirq_unlock_fn);
		entry = next;
		continue;
ack:
		waitq_wakeup_fn(req_addr + offsets->req_wq_offset);
		entry = next;
	}

	unlock_fn(migq_lock_addr, irqstate);
	return processed;
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

int futex_get_key_result(unsigned long uaddr, int fshared,
			 unsigned long key_addr, unsigned long mm_addr,
			 unsigned long key_word_offset,
			 unsigned long key_ptr_offset,
			 unsigned long key_offset_offset,
			 unsigned long fut_off_mmshared, int fault_flags,
			 futex_key_refs_fn_t key_refs_fn,
			 futex_get_key_vtop_fn_t vtop_fn,
			 futex_get_key_fault_fn_t fault_fn,
			 futex_get_key_log_fn_t log_fn)
{
	unsigned long base = 0;
	unsigned long offset = 0;
	unsigned long phys = 0;
	int is_private = 0;
	int ret;

	if (!key_addr || !mm_addr || !key_refs_fn || !vtop_fn ||
			!fault_fn || !log_fn)
		return -EINVAL;

	ret = futex_key_prepare_result(uaddr, fshared, &base, &offset,
				       &is_private);
	if (ret)
		return ret;

	*(int *)(key_addr + key_offset_offset) = (int)offset;
	if (is_private) {
		*(unsigned long *)(key_addr + key_word_offset) = base;
		*(unsigned long *)(key_addr + key_ptr_offset) = mm_addr;
		key_refs_fn(key_addr);
		return 0;
	}

	*(int *)(key_addr + key_offset_offset) =
		(int)(offset | fut_off_mmshared);
retry_v2p:
	ret = vtop_fn(mm_addr, uaddr, (unsigned long)&phys);
	if (ret) {
		ret = fault_fn(mm_addr, uaddr, fault_flags);
		if (ret) {
			log_fn(FUTEX_GET_KEY_LOG_VTOP_FAILED);
			return -EFAULT;
		}
		goto retry_v2p;
	}

	*(unsigned long *)(key_addr + key_word_offset) = 0;
	*(unsigned long *)(key_addr + key_ptr_offset) = phys;
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

		q_addr = (unsigned long)((struct plist_node *)((char *)(pos) - offsetof(struct plist_node, plist.node_list)));
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
			   futex_wake_scan_fn_t wake_fn)
{
	unsigned long hb_addr;
	unsigned long irqstate;
	unsigned long target_word;
	unsigned long target_ptr;
	int target_offset;
	int ret;

	if (!key_addr || !get_key_fn || !hash_key_fn || !lock_fn ||
			!unlock_fn || !put_key_fn || !wake_fn)
		return -EINVAL;

	if (!futex_wake_bitset_valid_result(bitset))
		return -EINVAL;

	ret = get_key_fn(uaddr, fshared, key_addr);
	if (ret)
		return ret;

	hb_addr = hash_key_fn(key_addr);
	if (!hb_addr) {
		put_key_fn(fshared, key_addr);
		return -EINVAL;
	}

	target_word = *(unsigned long *)(key_addr + key_word_offset);
	target_ptr = *(unsigned long *)(key_addr + key_ptr_offset);
	target_offset = *(int *)(key_addr + key_offset_offset);
	irqstate = lock_fn(hb_addr + hb_lock_offset);
	ret = futex_wake_scan_result(hb_addr + hb_chain_offset,
			q_list_offset, q_key_offset, q_bitset_offset,
			key_word_offset, key_ptr_offset, key_offset_offset,
			target_word, target_ptr, target_offset, bitset, 1,
			nr_wake, wake_fn);
	unlock_fn(hb_addr + hb_lock_offset, irqstate);
	put_key_fn(fshared, key_addr);
	return ret;
}

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
	futex_wait_put_key_fn_t put_key_fn, futex_wake_scan_fn_t wake_fn)
{
	unsigned long hb1_addr;
	unsigned long hb2_addr;
	int ret;
	int op_ret;

	if (!key1_addr || !key2_addr || !get_key_fn || !hash_key_fn ||
			!lock_fn || !unlock_fn || !atomic_fn || !put_key_fn ||
			!wake_fn)
		return -EINVAL;

retry:
	ret = get_key_fn(uaddr1, fshared, key1_addr);
	if (ret)
		return ret;
	ret = get_key_fn(uaddr2, fshared, key2_addr);
	if (ret)
		goto out_put_key1;

	hb1_addr = hash_key_fn(key1_addr);
	hb2_addr = hash_key_fn(key2_addr);
	if (!hb1_addr || !hb2_addr) {
		ret = -EINVAL;
		goto out_put_keys;
	}

retry_private:
	futex_double_lock_hb_result(hb1_addr, hb2_addr, hb_lock_offset,
			lock_fn);
	op_ret = atomic_fn(op, uaddr2);
	if (op_ret < 0) {
		futex_double_unlock_hb_result(hb1_addr, hb2_addr,
				hb_lock_offset, unlock_fn);

		if (op_ret != -EFAULT) {
			ret = op_ret;
			goto out_put_keys;
		}

		ret = 0;
		if (!fshared)
			goto retry_private;

		put_key_fn(fshared, key2_addr);
		put_key_fn(fshared, key1_addr);
		goto retry;
	}

	ret = futex_wake_scan_result(hb1_addr + hb_chain_offset,
			q_list_offset, q_key_offset, q_bitset_offset,
			key_word_offset, key_ptr_offset, key_offset_offset,
			*(unsigned long *)(key1_addr + key_word_offset),
			*(unsigned long *)(key1_addr + key_ptr_offset),
			*(int *)(key1_addr + key_offset_offset), 0, 0,
			nr_wake, wake_fn);
	if (op_ret > 0) {
		op_ret = futex_wake_scan_result(hb2_addr + hb_chain_offset,
				q_list_offset, q_key_offset, q_bitset_offset,
				key_word_offset, key_ptr_offset,
				key_offset_offset,
				*(unsigned long *)(key2_addr + key_word_offset),
				*(unsigned long *)(key2_addr + key_ptr_offset),
				*(int *)(key2_addr + key_offset_offset), 0, 0,
				nr_wake2, wake_fn);
		ret += op_ret;
	}

	futex_double_unlock_hb_result(hb1_addr, hb2_addr, hb_lock_offset,
			unlock_fn);

out_put_keys:
	put_key_fn(fshared, key2_addr);
out_put_key1:
	put_key_fn(fshared, key1_addr);
	return ret;
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

		q_addr = (unsigned long)((struct plist_node *)((char *)(pos) - offsetof(struct plist_node, plist.node_list)));
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
	futex_requeue_scan_fn_t wake_fn, futex_requeue_scan_fn_t requeue_fn)
{
	unsigned long hb1_addr;
	unsigned long hb2_addr;
	int drop_count = 0;
	int task_count = 0;
	int ret;

	if (!key1_addr || !key2_addr || !ctx_addr || !get_key_fn ||
			!hash_key_fn || !lock_fn || !unlock_fn ||
			!put_key_fn || !drop_key_refs_fn || !wake_fn ||
			!requeue_fn)
		return -EINVAL;
	if (cmpval_addr && !get_value_fn)
		return -EINVAL;

	ret = get_key_fn(uaddr1, fshared, key1_addr);
	if (ret)
		return ret;

	ret = get_key_fn(uaddr2, fshared, key2_addr);
	if (ret)
		goto out_put_key1;

	hb1_addr = hash_key_fn(key1_addr);
	hb2_addr = hash_key_fn(key2_addr);
	if (!hb1_addr || !hb2_addr) {
		ret = -EINVAL;
		goto out_put_keys;
	}

	futex_double_lock_hb_result(hb1_addr, hb2_addr, hb_lock_offset,
			lock_fn);

	if (cmpval_addr) {
		uint32_t curval = 0;

		ret = get_value_fn((unsigned long)&curval, uaddr1);
		if (curval != *(uint32_t *)cmpval_addr) {
			ret = -EAGAIN;
			goto out_unlock;
		}
	}

	*(unsigned long *)(ctx_addr + ctx_hb1_offset) = hb1_addr;
	*(unsigned long *)(ctx_addr + ctx_hb2_offset) = hb2_addr;
	*(unsigned long *)(ctx_addr + ctx_key2_offset) = key2_addr;
	task_count = futex_requeue_scan_result(hb1_addr + hb_chain_offset,
			q_list_offset, q_key_offset, key_word_offset,
			key_ptr_offset, key_offset_offset,
			*(unsigned long *)(key1_addr + key_word_offset),
			*(unsigned long *)(key1_addr + key_ptr_offset),
			*(int *)(key1_addr + key_offset_offset), nr_wake,
			nr_requeue, &drop_count, wake_fn, requeue_fn,
			ctx_addr);

out_unlock:
	futex_double_unlock_hb_result(hb1_addr, hb2_addr, hb_lock_offset,
			unlock_fn);

	while (drop_count-- > 0)
		drop_key_refs_fn(key1_addr);

out_put_keys:
	put_key_fn(fshared, key2_addr);
out_put_key1:
	put_key_fn(fshared, key1_addr);
	return ret ? ret : task_count;
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

int futex_unqueue_me_result(unsigned long q_addr,
			    unsigned long lock_ptr_offset,
			    unsigned long list_offset,
			    unsigned long node_plist_offset,
			    unsigned long key_offset,
			    futex_hb_lock_fn_t lock_fn,
			    futex_hb_unlock_fn_t unlock_fn,
			    futex_key_refs_fn_t drop_key_refs_fn)
{
	unsigned long lock_addr;
	int ret = 0;

	if (!q_addr || !lock_fn || !unlock_fn || !drop_key_refs_fn)
		return -EINVAL;

retry:
	lock_addr = *(unsigned long *)(q_addr + lock_ptr_offset);
	barrier();
	if (lock_addr) {
		lock_fn(lock_addr);
		if (lock_addr != *(unsigned long *)(q_addr + lock_ptr_offset)) {
			unlock_fn(lock_addr);
			goto retry;
		}
		ret = futex_unqueue_detach_result(q_addr, list_offset,
						  node_plist_offset);
		unlock_fn(lock_addr);
	}

	drop_key_refs_fn(q_addr + key_offset);
	return ret;
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
	futex_vector_fn_t vector_fn, futex_hb_unlock_fn_t unlock_fn)
{
	unsigned long proc_addr;
	int cpu_id;

	if (!q_addr || !hb_chain_addr || !hb_lock_addr || !thread_addr ||
			!virt_to_phys_fn || !interrupt_id_fn ||
			!vector_fn || !unlock_fn)
		return -EINVAL;

	futex_queue_insert_result(q_addr, q_list_offset, hb_chain_addr, prio,
				  debug_spinlock_offset, hb_lock_addr);

	proc_addr = *(unsigned long *)(thread_addr + thread_proc_offset);
	cpu_id = *(int *)(thread_addr + thread_cpu_id_offset);
	futex_queue_publish_waiter_result(q_addr, q_task_offset,
		q_th_spin_sleep_pa_offset, q_th_status_pa_offset,
		q_th_spin_sleep_lock_pa_offset, q_proc_status_pa_offset,
		q_proc_update_lock_pa_offset, q_runq_lock_pa_offset,
		q_clv_flags_pa_offset, q_intr_id_offset, q_intr_vector_offset,
		thread_addr,
		virt_to_phys_fn(thread_addr + thread_spin_sleep_offset),
		virt_to_phys_fn(thread_addr + thread_status_offset),
		virt_to_phys_fn(thread_addr + thread_spin_sleep_lock_offset),
		virt_to_phys_fn(proc_addr + proc_status_offset),
		virt_to_phys_fn(proc_addr + proc_update_lock_offset),
		virt_to_phys_fn(runq_lock_addr),
		virt_to_phys_fn(clv_flags_addr),
		interrupt_id_fn(cpu_id), vector_fn(vector_key));

	unlock_fn(hb_lock_addr);
	return 0;
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
	futex_wait_queue_log_fn_t log_fn)
{
	unsigned long irqstate;
	int schedule_action;
	int tid;
	int queued;
	int64_t time_remain = 0;

	if (!hb_addr || !q_addr || !thread_addr || !spin_lock_fn ||
			!spin_unlock_fn || !queue_me_fn || !schedule_timeout_fn ||
			!schedule_direct_fn || !log_fn)
		return -EINVAL;

	futex_wait_mark_interruptible_result(thread_addr, thread_status_offset,
					     interruptible_status);
	if (!idle_halt_enabled || timeout) {
		unsigned long lock_addr =
			thread_addr + thread_spin_sleep_lock_offset;
		irqstate = spin_lock_fn(lock_addr);
		futex_wait_spin_sleep_store_result(thread_addr,
						   thread_spin_sleep_offset, 1);
		spin_unlock_fn(lock_addr, irqstate);
	}

	queue_me_fn(q_addr, hb_addr);
	queued = !plist_node_empty_addr(q_addr + q_list_offset,
					q_node_plist_offset,
					q_plist_node_list_offset);
	schedule_action = futex_wait_schedule_action_result(queued, timeout);
	tid = *(int *)(thread_addr + thread_tid_offset);
	if (schedule_action == FUTEX_WAIT_SCHEDULE_TIMEOUT) {
		log_fn(FUTEX_WAIT_QUEUE_LOG_TIMEOUT, thread_addr, tid);
		time_remain = schedule_timeout_fn(timeout);
	} else if (schedule_action == FUTEX_WAIT_SCHEDULE_DIRECT) {
		log_fn(FUTEX_WAIT_QUEUE_LOG_DIRECT, thread_addr, tid);
		schedule_direct_fn();
		time_remain = 0;
	}
	if (schedule_action != FUTEX_WAIT_SCHEDULE_NONE)
		log_fn(FUTEX_WAIT_QUEUE_LOG_WOKEN, thread_addr, tid);

	futex_wait_finish_state_result(thread_addr, thread_status_offset,
				       thread_spin_sleep_offset, running_status);
	return time_remain;
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
	futex_wait_log_fn_t log_fn)
{
	unsigned long hb_addr;
	int64_t time_remain;
	int has_pending_signal;
	int post_action;
	int ret;
	int tid;
	int unqueued;

	if (!q_addr || !thread_addr || !setup_fn || !wait_queue_fn ||
			!unqueue_fn || !has_signal_fn || !put_key_fn || !log_fn)
		return -EINVAL;

	if (!futex_wake_bitset_valid_result(bitset))
		return -EINVAL;

	futex_wait_prepare_q_result(q_addr, q_bitset_offset,
				    q_requeue_pi_key_offset,
				    q_uti_futex_resp_offset, bitset,
				    uti_futex_resp);
	tid = *(int *)(thread_addr + thread_tid_offset);

retry:
	hb_addr = 0;
	ret = setup_fn(uaddr, val, fshared, q_addr,
		       (unsigned long)&hb_addr);
	if (ret) {
		log_fn(FUTEX_WAIT_LOG_SETUP_RET, thread_addr, tid, ret);
		return ret;
	}

	time_remain = wait_queue_fn(hb_addr, q_addr, timeout);
	ret = 0;
	unqueued = unqueue_fn(q_addr);
	has_pending_signal = 0;
	if (unqueued && !(timeout && !time_remain))
		has_pending_signal = has_signal_fn(thread_addr);
	post_action = futex_wait_post_action_result(unqueued, timeout,
			time_remain, has_pending_signal,
			time_remain == -ERESTARTSYS);
	if (post_action == FUTEX_WAIT_POST_SUCCESS) {
		log_fn(FUTEX_WAIT_LOG_SUCCESS, thread_addr, tid, ret);
		put_key_fn(fshared, q_addr + q_key_offset);
		return ret;
	}
	if (post_action == FUTEX_WAIT_POST_TIMEOUT) {
		ret = -ETIMEDOUT;
		log_fn(FUTEX_WAIT_LOG_TIMEOUT, thread_addr, tid, ret);
		put_key_fn(fshared, q_addr + q_key_offset);
		return ret;
	}
	if (post_action == FUTEX_WAIT_POST_INTERRUPT) {
		ret = -EINTR;
		log_fn(FUTEX_WAIT_LOG_INTERRUPT, thread_addr, tid, ret);
		put_key_fn(fshared, q_addr + q_key_offset);
		return ret;
	}

	put_key_fn(fshared, q_addr + q_key_offset);
	goto retry;
}

int futex_wait_entry_result(
	unsigned long uaddr, int fshared, uint32_t val,
	uint64_t timeout, uint32_t bitset, unsigned long q_addr,
	unsigned long thread_addr, unsigned long uti_futex_resp,
	int profile_enabled, unsigned long thread_profile_offset,
	unsigned long thread_profile_start_ts_offset,
	unsigned long thread_profile_elapsed_ts_offset,
	futex_wait_timestamp_fn_t timestamp_fn,
	futex_wait_body_entry_fn_t wait_body_fn)
{
	int ret;

	if (!q_addr || !thread_addr || !wait_body_fn)
		return -EINVAL;
	if (profile_enabled && !timestamp_fn)
		return -EINVAL;

	if (!futex_wake_bitset_valid_result(bitset))
		return -EINVAL;

	if (profile_enabled &&
			*(int *)(thread_addr + thread_profile_offset) &&
			*(unsigned long *)(thread_addr +
				thread_profile_start_ts_offset)) {
		unsigned long ts = timestamp_fn();
		unsigned long start = *(unsigned long *)(thread_addr +
				thread_profile_start_ts_offset);

		*(unsigned long *)(thread_addr +
				thread_profile_elapsed_ts_offset) += ts - start;
		*(unsigned long *)(thread_addr +
				thread_profile_start_ts_offset) = 0;
	}

	ret = wait_body_fn(uaddr, fshared, val, timeout, bitset, q_addr,
			thread_addr, uti_futex_resp);

	if (profile_enabled &&
			*(int *)(thread_addr + thread_profile_offset))
		*(unsigned long *)(thread_addr +
				thread_profile_start_ts_offset) = timestamp_fn();

	return ret;
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
