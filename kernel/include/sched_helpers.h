/* SPDX-License-Identifier: GPL-2.0 */
#ifndef MCKERNEL_SCHED_HELPERS_H
#define MCKERNEL_SCHED_HELPERS_H

#include <types.h>

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

#endif /* MCKERNEL_SCHED_HELPERS_H */
