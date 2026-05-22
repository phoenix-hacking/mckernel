use crate::abi::CInt;

const EINVAL: CInt = 22;
const EPERM: CInt = 1;
const SCHED_NORMAL: CInt = 0;
const SCHED_FIFO: CInt = 1;
const SCHED_RR: CInt = 2;
const SCHED_BATCH: CInt = 3;
const SCHED_IDLE: CInt = 5;
const SCHED_DEADLINE: CInt = 6;
const MAX_USER_RT_PRIO: CInt = 100;
const SCHED_RR_INTERVAL_NSEC: i64 = 10_000;

#[no_mangle]
pub extern "C" fn sched_get_priority_max_value(policy: CInt) -> CInt {
    match policy {
        SCHED_FIFO | SCHED_RR => MAX_USER_RT_PRIO - 1,
        SCHED_DEADLINE | SCHED_NORMAL | SCHED_BATCH | SCHED_IDLE => 0,
        _ => -EINVAL,
    }
}

#[no_mangle]
pub extern "C" fn sched_get_priority_min_value(policy: CInt) -> CInt {
    match policy {
        SCHED_FIFO | SCHED_RR => 1,
        SCHED_DEADLINE | SCHED_NORMAL | SCHED_BATCH | SCHED_IDLE => 0,
        _ => -EINVAL,
    }
}

#[inline(always)]
fn known_policy(policy: CInt) -> bool {
    matches!(
        policy,
        SCHED_DEADLINE | SCHED_FIFO | SCHED_RR | SCHED_NORMAL | SCHED_BATCH | SCHED_IDLE
    )
}

#[no_mangle]
pub extern "C" fn sched_policy_is_valid(policy: CInt) -> CInt {
    known_policy(policy) as CInt
}

#[no_mangle]
pub extern "C" fn sched_policy_needs_root(policy: CInt) -> CInt {
    (known_policy(policy) && policy != SCHED_NORMAL) as CInt
}

#[no_mangle]
pub extern "C" fn setscheduler_validate(policy: CInt, priority: CInt) -> CInt {
    if (policy == SCHED_FIFO || policy == SCHED_RR)
        && (priority < 1 || priority > MAX_USER_RT_PRIO - 1)
    {
        return -EINVAL;
    }

    if (policy == SCHED_NORMAL || policy == SCHED_BATCH || policy == SCHED_IDLE) && priority != 0 {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn sched_rr_interval_nsec(policy: CInt) -> i64 {
    if policy == SCHED_RR {
        SCHED_RR_INTERVAL_NSEC
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn sched_affinity_permission_result(
    caller_euid: u32,
    target_ruid: u32,
    target_euid: u32,
) -> CInt {
    if caller_euid == 0 || caller_euid == target_ruid || caller_euid == target_euid {
        0
    } else {
        -EPERM
    }
}

#[no_mangle]
pub extern "C" fn sched_getaffinity_len_result(len: usize, num_processors: CInt) -> CInt {
    if len.saturating_mul(8) < num_processors as usize {
        return -EINVAL;
    }
    if (len & (core::mem::size_of::<usize>() - 1)) != 0 {
        return -EINVAL;
    }
    0
}

#[no_mangle]
pub extern "C" fn sched_affinity_copy_len(len: usize, cpuset_size: usize) -> usize {
    if len < cpuset_size {
        len
    } else {
        cpuset_size
    }
}

#[no_mangle]
pub extern "C" fn timer_spin_sleep_remaining_result(timeout: u64, elapsed: u64) -> u64 {
    if elapsed < timeout {
        timeout - elapsed
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn timer_runq_should_schedule_result(runq_len: CInt) -> CInt {
    (runq_len > 1) as CInt
}

#[no_mangle]
pub extern "C" fn timer_after_spin_remaining_result(timeout: u64, loop_timeout: u64) -> u64 {
    if timeout < loop_timeout {
        0
    } else {
        timeout - loop_timeout
    }
}

#[no_mangle]
pub extern "C" fn timer_after_tick_remaining_result(timeout: u64, loop_timeout: u64) -> u64 {
    let remaining = timeout.wrapping_sub(loop_timeout);

    if remaining < loop_timeout {
        0
    } else {
        remaining
    }
}

#[no_mangle]
pub extern "C" fn futex_key_match_result(
    has_key1: CInt,
    has_key2: CInt,
    word1: usize,
    ptr1: usize,
    offset1: usize,
    word2: usize,
    ptr2: usize,
    offset2: usize,
) -> CInt {
    (has_key1 != 0 && has_key2 != 0 && word1 == word2 && ptr1 == ptr2 && offset1 == offset2) as CInt
}
