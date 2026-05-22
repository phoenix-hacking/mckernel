/* SPDX-License-Identifier: GPL-2.0 */
#include <sched_helpers.h>

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

#endif /* MCKERNEL_RUST_SCHED_RUNTIME_HELPERS */
