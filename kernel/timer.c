/**
 * \file timer.c
 * Licence details are found in the file LICENSE.
 *  
 * \brief
 * Simple spinning timer for timeout support in futex.
 *
 * \author Balazs Gerofi  <bgerofi@is.s.u-tokyo.ac.jp> \par
 * Copyright (C) 2013  The University of Tokyo
 *
 */
#include <types.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <cpulocal.h>
#include <ihk/mm.h>
#include <ihk/ikc.h>
#include <errno.h>
#include <cls.h>
#include <syscall.h>
#include <page.h>
#include <amemcpy.h>
#include <uio.h>
#include <ihk/lock.h>
#include <ctype.h>
#include <waitq.h>
#include <rlimit.h>
#include <affinity.h>
#include <time.h>
#include <lwk/stddef.h>
#include <futex.h>
#include <bitops.h>
#include <timer.h>
#include <sched_helpers.h>
#include <ihk/debug.h>

//#define DEBUG_PRINT_TIMER

#ifdef DEBUG_PRINT_TIMER
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

#define LOOP_TIMEOUT 500

#ifndef MCKERNEL_RUST_TIMER_HELPERS
void
ts_add(struct timespec *ats, const struct timespec *bts)
{
	ats->tv_sec += bts->tv_sec;
	ats->tv_nsec += bts->tv_nsec;
	while (ats->tv_nsec >= 1000000000) {
		ats->tv_sec++;
		ats->tv_nsec -= 1000000000;
	}
}

void
ts_sub(struct timespec *ats, const struct timespec *bts)
{
	ats->tv_sec -= bts->tv_sec;
	ats->tv_nsec -= bts->tv_nsec;
	while (ats->tv_nsec < 0) {
		ats->tv_sec--;
		ats->tv_nsec += 1000000000;
	}
}

void
tv_add(struct timeval *ats, const struct timeval *bts)
{
	ats->tv_sec += bts->tv_sec;
	ats->tv_usec += bts->tv_usec;
	while (ats->tv_usec >= 1000000) {
		ats->tv_sec++;
		ats->tv_usec -= 1000000;
	}
}

void
tv_sub(struct timeval *ats, const struct timeval *bts)
{
	ats->tv_sec -= bts->tv_sec;
	ats->tv_usec -= bts->tv_usec;
	while (ats->tv_usec < 0) {
		ats->tv_sec--;
		ats->tv_usec += 1000000;
	}
}

void
tv_to_ts(struct timespec *ats, const struct timeval *bts)
{
	ats->tv_sec = bts->tv_sec;
	ats->tv_nsec = bts->tv_usec * 1000;
}

void
ts_to_tv(struct timeval *ats, const struct timespec *bts)
{
	ats->tv_sec = bts->tv_sec;
	ats->tv_usec = bts->tv_nsec / 1000;
}
#endif

struct list_head timers;
ihk_spinlock_t timers_lock;

static const struct timer_runtime_offsets timer_runtime_offsets = {
	.thread_status_offset = __builtin_offsetof(struct thread, status),
	.thread_sched_list_offset = __builtin_offsetof(struct thread, sched_list),
	.thread_spin_sleep_lock_offset =
		__builtin_offsetof(struct thread, spin_sleep_lock),
	.thread_spin_sleep_offset = __builtin_offsetof(struct thread, spin_sleep),
	.thread_itimer_enabled_offset =
		__builtin_offsetof(struct thread, itimer_enabled),
	.cpu_runq_lock_offset = __builtin_offsetof(struct cpu_local_var, runq_lock),
	.cpu_runq_offset = __builtin_offsetof(struct cpu_local_var, runq),
	.cpu_runq_len_offset = __builtin_offsetof(struct cpu_local_var, runq_len),
	.cpu_current_offset = __builtin_offsetof(struct cpu_local_var, current),
	.cpu_timer_enabled_offset =
		__builtin_offsetof(struct cpu_local_var, timer_enabled),
	.cpu_backlog_list_offset =
		__builtin_offsetof(struct cpu_local_var, backlog_list),
	.timer_timeout_offset = __builtin_offsetof(struct timer, timeout),
	.timer_waitq_offset = __builtin_offsetof(struct timer, processes),
	.timer_list_offset = __builtin_offsetof(struct timer, list),
	.timer_thread_offset = __builtin_offsetof(struct timer, thread),
};

static void timer_spin_init_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_init((ihk_spinlock_t *)lock_addr);
}

static unsigned long timer_spin_lock_bridge(unsigned long lock_addr)
{
	return ihk_mc_spinlock_lock((ihk_spinlock_t *)lock_addr);
}

static void timer_spin_unlock_bridge(unsigned long lock_addr,
				     unsigned long irqstate)
{
	ihk_mc_spinlock_unlock((ihk_spinlock_t *)lock_addr, irqstate);
}

static unsigned long timer_spin_lock_noirq_bridge(unsigned long lock_addr)
{
	ihk_mc_spinlock_lock_noirq((ihk_spinlock_t *)lock_addr);
	return 0;
}

static void timer_spin_unlock_noirq_bridge(unsigned long lock_addr,
					   unsigned long irqstate)
{
	(void)irqstate;
	ihk_mc_spinlock_unlock_noirq((ihk_spinlock_t *)lock_addr);
}

static uint64_t timer_rdtsc_bridge(void)
{
	return rdtsc();
}

static void timer_set_status_bridge(unsigned long status_addr, int status)
{
	xchg4((int *)status_addr, status);
}

static void timer_schedule_bridge(void)
{
	schedule();
}

static void timer_zero_free_bridge(void)
{
	ihk_numa_zero_free_pages(ihk_mc_get_numa_node_by_distance(0));
}

static void timer_pause_bridge(void)
{
	cpu_pause();
}

static void timer_waitq_wakeup_bridge(unsigned long waitq_addr)
{
	waitq_wakeup((struct waitq *)waitq_addr);
}

static void timer_log_wake_bridge(unsigned long timer_addr,
				  unsigned long thread_addr)
{
	struct timer *timer = (struct timer *)timer_addr;
	struct thread *thread = (struct thread *)thread_addr;

	dkprintf("timers timeout occurred, waking up pid: %d\n",
			thread && thread->proc ? thread->proc->pid : -1);
	(void)timer;
}

void init_timers(void)
{
	timer_init_timers_result((unsigned long)&timers_lock,
			(unsigned long)&timers, timer_spin_init_bridge);
}

uint64_t schedule_timeout(uint64_t timeout)
{
	struct thread *thread = get_this_cpu_local_var()->current;

	return timer_schedule_timeout_body_result((unsigned long)thread,
			(unsigned long)get_this_cpu_local_var(), timeout,
			LOOP_TIMEOUT, &timer_runtime_offsets,
			timer_rdtsc_bridge, timer_spin_lock_bridge,
			timer_spin_unlock_bridge, timer_set_status_bridge,
			timer_schedule_bridge, timer_zero_free_bridge,
			timer_pause_bridge);
}


void wake_timers_loop(void)
{
	int ret;

	dkprintf("timers thread, entering loop\n");
	ret = timer_wake_loop_body_result((unsigned long)&timers_lock,
			(unsigned long)&timers, LOOP_TIMEOUT, 0,
			&timer_runtime_offsets, timer_rdtsc_bridge,
			timer_pause_bridge, timer_spin_lock_noirq_bridge,
			timer_spin_unlock_noirq_bridge,
			timer_waitq_wakeup_bridge, timer_log_wake_bridge);
	if (ret < 0)
		panic("wake_timers_loop: helper failed");
}
