/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <sched_helpers.h>

#define PAGE_SIZE 4096UL

#ifndef MCKERNEL_RUST_SCHED_RUNTIME_HELPERS

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

int syscall_offload_should_schedule_result(int no_preempt, int tid,
					   int need_resched, int runq_len,
					   int is_sched_setaffinity)
{
	if (no_preempt || !tid)
		return 0;

	return need_resched || runq_len > 1 || is_sched_setaffinity;
}

#endif /* MCKERNEL_RUST_SCHED_RUNTIME_HELPERS */
