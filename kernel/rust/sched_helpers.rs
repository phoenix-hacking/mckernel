use core::ptr::{read_volatile, write_volatile};
use core::sync::atomic::{compiler_fence, AtomicI32, Ordering};

use crate::abi::{CInt, CULong};

type FutexHbLockFn = unsafe extern "C" fn(usize);
type FutexHbUnlockFn = unsafe extern "C" fn(usize);
type FutexWakeScanFn = unsafe extern "C" fn(usize);
type FutexRequeueScanFn = unsafe extern "C" fn(usize, usize);
type FutexKeyRefsFn = unsafe extern "C" fn(usize);
type FutexWaitGetKeyFn = unsafe extern "C" fn(usize, CInt, usize) -> CInt;
type FutexWaitQueueLockFn = unsafe extern "C" fn(usize) -> usize;
type FutexWaitGetValueFn = unsafe extern "C" fn(usize, usize) -> CInt;
type FutexWaitQueueUnlockFn = unsafe extern "C" fn(usize, usize);
type FutexWaitPutKeyFn = unsafe extern "C" fn(CInt, usize);
type FutexAllocFn = unsafe extern "C" fn(usize, CInt) -> usize;
type FutexHashFn = unsafe extern "C" fn(usize) -> u32;
type FutexDispatchWaitFn = unsafe extern "C" fn(usize, CInt, u32, u64, u32, CInt) -> CInt;
type FutexDispatchWakeFn = unsafe extern "C" fn(usize, CInt, u32, u32) -> CInt;
type FutexDispatchRequeueFn =
    unsafe extern "C" fn(usize, CInt, usize, u32, u32, CInt, u32, CInt) -> CInt;
type FutexDispatchWakeOpFn = unsafe extern "C" fn(usize, CInt, usize, u32, u32, u32) -> CInt;
type FutexDispatchInvalidFn = unsafe extern "C" fn(CInt);
type FutexWakeLinuxChannelByCpuFn = unsafe extern "C" fn(CInt) -> usize;
type FutexWakeSendFn = unsafe extern "C" fn(usize, usize) -> CInt;
type FutexWakeThreadFn = unsafe extern "C" fn(usize, CInt);
type FutexWakeLogFn = unsafe extern "C" fn(CInt, usize, usize, CInt, usize, CInt);

const EINVAL: CInt = 22;
const EPERM: CInt = 1;
const EWOULDBLOCK: CInt = 11;
const SCHED_NORMAL: CInt = 0;
const SCHED_FIFO: CInt = 1;
const SCHED_RR: CInt = 2;
const SCHED_BATCH: CInt = 3;
const SCHED_IDLE: CInt = 5;
const SCHED_DEADLINE: CInt = 6;
const MAX_USER_RT_PRIO: CInt = 100;
const SCHED_RR_INTERVAL_NSEC: i64 = 10_000;
const PAGE_SIZE: usize = 4096;
const FUTEX_WAIT_POST_SUCCESS: CInt = 0;
const FUTEX_WAIT_POST_RETRY: CInt = 1;
const FUTEX_WAIT_POST_TIMEOUT: CInt = 2;
const FUTEX_WAIT_POST_INTERRUPT: CInt = 3;
const FUTEX_WAIT_SCHEDULE_NONE: CInt = 0;
const FUTEX_WAIT_SCHEDULE_TIMEOUT: CInt = 1;
const FUTEX_WAIT_SCHEDULE_DIRECT: CInt = 2;
const FUTEX_WAKE_TARGET_MCKERNEL: CInt = 0;
const FUTEX_WAKE_TARGET_LINUX: CInt = 1;
const FUTEX_WAKE_LOG_LINUX_TARGET: CInt = 1;
const FUTEX_WAKE_LOG_SEND_FAILED: CInt = 2;
const FUTEX_WAKE_LOG_SEND_OK: CInt = 3;
const FUTEX_WAKE_LOG_MCKERNEL_TARGET: CInt = 4;
const FUTEX_WAIT: CInt = 0;
const FUTEX_WAKE: CInt = 1;
const FUTEX_REQUEUE: CInt = 3;
const FUTEX_CMP_REQUEUE: CInt = 4;
const FUTEX_WAKE_OP: CInt = 5;
const FUTEX_WAIT_BITSET: CInt = 9;
const FUTEX_WAKE_BITSET: CInt = 10;
const FUTEX_WAIT_REQUEUE_PI: CInt = 11;
const FUTEX_PRIVATE_FLAG: CInt = 128;
const FUTEX_CLOCK_REALTIME: CInt = 256;
const FUTEX_BITSET_MATCH_ANY: u32 = 0xffff_ffff;
const ENOSYS: CInt = 38;
const PLIST_NODE_PLIST_OFFSET: usize = 8;
const PLIST_HEAD_NODE_LIST_OFFSET: usize = 16;
const PLIST_NODE_LIST_OFFSET: usize = PLIST_NODE_PLIST_OFFSET + PLIST_HEAD_NODE_LIST_OFFSET;

unsafe fn init_list_head_addr(list_addr: usize) {
    unsafe {
        write_volatile(list_addr as *mut usize, list_addr);
        write_volatile(
            list_addr.wrapping_add(core::mem::size_of::<usize>()) as *mut usize,
            list_addr,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_hash_bucket_table_init_result(
    buckets_addr: usize,
    bucket_count: CInt,
    bucket_stride: usize,
    lock_offset: usize,
    lock_word_offset: usize,
    chain_offset: usize,
    prio_list_offset: usize,
    node_list_offset: usize,
    debug_spinlock_offset: usize,
    debug_rawlock_offset: usize,
) -> CInt {
    if bucket_count < 0 || bucket_stride == 0 {
        return -EINVAL;
    }
    if bucket_count != 0 && buckets_addr == 0 {
        return -EINVAL;
    }

    let count = bucket_count as usize;
    for i in 0..count {
        let Some(bucket_delta) = bucket_stride.checked_mul(i) else {
            return -EINVAL;
        };
        let bucket = buckets_addr.wrapping_add(bucket_delta);
        let lock_addr = bucket.wrapping_add(lock_offset);
        let chain_addr = bucket.wrapping_add(chain_offset);

        unsafe {
            write_volatile(lock_addr.wrapping_add(lock_word_offset) as *mut u32, 0);
            init_list_head_addr(chain_addr.wrapping_add(prio_list_offset));
            init_list_head_addr(chain_addr.wrapping_add(node_list_offset));

            if debug_spinlock_offset != 0 {
                write_volatile(
                    chain_addr.wrapping_add(debug_spinlock_offset) as *mut usize,
                    lock_addr,
                );
            }
            if debug_rawlock_offset != 0 {
                write_volatile(
                    chain_addr.wrapping_add(debug_rawlock_offset) as *mut usize,
                    0,
                );
            }
        }
    }

    bucket_count
}

#[no_mangle]
pub unsafe extern "C" fn futex_init_table_result(
    queues_slot_addr: usize,
    hashbits: CInt,
    bucket_stride: usize,
    alloc_flag: CInt,
    alloc_fn: Option<FutexAllocFn>,
    lock_offset: usize,
    lock_word_offset: usize,
    chain_offset: usize,
    prio_list_offset: usize,
    node_list_offset: usize,
    debug_spinlock_offset: usize,
    debug_rawlock_offset: usize,
) -> CInt {
    if queues_slot_addr == 0 || hashbits < 0 || bucket_stride == 0 {
        return -EINVAL;
    }

    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };
    let Some(bucket_count) = (1usize).checked_shl(hashbits as u32) else {
        return -EINVAL;
    };
    let Some(bytes) = bucket_stride.checked_mul(bucket_count) else {
        return -EINVAL;
    };

    let buckets_addr = unsafe { alloc_fn(bytes, alloc_flag) };
    unsafe {
        write_volatile(queues_slot_addr as *mut usize, buckets_addr);
    }
    futex_hash_bucket_table_init_result(
        buckets_addr,
        bucket_count as CInt,
        bucket_stride,
        lock_offset,
        lock_word_offset,
        chain_offset,
        prio_list_offset,
        node_list_offset,
        debug_spinlock_offset,
        debug_rawlock_offset,
    )
}

#[no_mangle]
pub unsafe extern "C" fn futex_hash_bucket_result(
    key_addr: usize,
    queues_addr: usize,
    hashbits: CInt,
    bucket_stride: usize,
    hash_fn: Option<FutexHashFn>,
) -> usize {
    if key_addr == 0 || queues_addr == 0 || hashbits < 0 || bucket_stride == 0 {
        return 0;
    }
    let Some(hash_fn) = hash_fn else {
        return 0;
    };
    let Some(bucket_count) = (1usize).checked_shl(hashbits as u32) else {
        return 0;
    };

    let hash = unsafe { hash_fn(key_addr) } as usize;
    let index = hash & bucket_count.wrapping_sub(1);
    let Some(delta) = bucket_stride.checked_mul(index) else {
        return 0;
    };
    queues_addr.checked_add(delta).unwrap_or(0)
}

#[no_mangle]
pub unsafe extern "C" fn futex_dispatch_result(
    op: CInt,
    uaddr: usize,
    val: u32,
    timeout: u64,
    uaddr2: usize,
    val2: u32,
    val3: u32,
    fshared: CInt,
    wait_fn: Option<FutexDispatchWaitFn>,
    wake_fn: Option<FutexDispatchWakeFn>,
    requeue_fn: Option<FutexDispatchRequeueFn>,
    wake_op_fn: Option<FutexDispatchWakeOpFn>,
    invalid_fn: Option<FutexDispatchInvalidFn>,
) -> CInt {
    let cmd = op & !(FUTEX_PRIVATE_FLAG | FUTEX_CLOCK_REALTIME);
    let clockrt = op & FUTEX_CLOCK_REALTIME;

    if clockrt != 0 && cmd != FUTEX_WAIT_BITSET && cmd != FUTEX_WAIT_REQUEUE_PI {
        return -ENOSYS;
    }

    match cmd {
        FUTEX_WAIT => {
            let Some(wait_fn) = wait_fn else {
                return -ENOSYS;
            };
            unsafe {
                wait_fn(
                    uaddr,
                    fshared,
                    val,
                    timeout,
                    FUTEX_BITSET_MATCH_ANY,
                    clockrt,
                )
            }
        }
        FUTEX_WAIT_BITSET => {
            let Some(wait_fn) = wait_fn else {
                return -ENOSYS;
            };
            unsafe { wait_fn(uaddr, fshared, val, timeout, val3, clockrt) }
        }
        FUTEX_WAKE => {
            let Some(wake_fn) = wake_fn else {
                return -ENOSYS;
            };
            unsafe { wake_fn(uaddr, fshared, val, FUTEX_BITSET_MATCH_ANY) }
        }
        FUTEX_WAKE_BITSET => {
            let Some(wake_fn) = wake_fn else {
                return -ENOSYS;
            };
            unsafe { wake_fn(uaddr, fshared, val, val3) }
        }
        FUTEX_REQUEUE => {
            let Some(requeue_fn) = requeue_fn else {
                return -ENOSYS;
            };
            unsafe { requeue_fn(uaddr, fshared, uaddr2, val, val2, 0, 0, 0) }
        }
        FUTEX_CMP_REQUEUE => {
            let Some(requeue_fn) = requeue_fn else {
                return -ENOSYS;
            };
            unsafe { requeue_fn(uaddr, fshared, uaddr2, val, val2, 1, val3, 0) }
        }
        FUTEX_WAKE_OP => {
            let Some(wake_op_fn) = wake_op_fn else {
                return -ENOSYS;
            };
            unsafe { wake_op_fn(uaddr, fshared, uaddr2, val, val2, val3) }
        }
        _ => {
            if let Some(invalid_fn) = invalid_fn {
                unsafe { invalid_fn(cmd) };
            }
            -ENOSYS
        }
    }
}

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

#[no_mangle]
pub unsafe extern "C" fn futex_key_prepare_result(
    address: usize,
    fshared: CInt,
    basep: *mut usize,
    offsetp: *mut usize,
    privatep: *mut CInt,
) -> CInt {
    let offset = address % PAGE_SIZE;

    if (address % core::mem::size_of::<u32>()) != 0 {
        return -EINVAL;
    }

    if !basep.is_null() {
        unsafe {
            *basep = address - offset;
        }
    }
    if !offsetp.is_null() {
        unsafe {
            *offsetp = offset;
        }
    }
    if !privatep.is_null() {
        unsafe {
            *privatep = (fshared == 0) as CInt;
        }
    }

    0
}

#[no_mangle]
pub extern "C" fn futex_wake_bitset_valid_result(bitset: u32) -> CInt {
    (bitset != 0) as CInt
}

#[no_mangle]
pub extern "C" fn futex_waiter_matches_bitset_result(
    waiter_bitset: u32,
    requested_bitset: u32,
) -> CInt {
    ((waiter_bitset & requested_bitset) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn futex_wake_limit_reached_result(woken: CInt, nr_wake: CInt) -> CInt {
    (woken >= nr_wake) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn futex_wake_scan_result(
    chain_addr: usize,
    q_list_offset: usize,
    q_key_offset: usize,
    q_bitset_offset: usize,
    key_word_offset: usize,
    key_ptr_offset: usize,
    key_offset_offset: usize,
    target_word: usize,
    target_ptr: usize,
    target_offset: CInt,
    requested_bitset: u32,
    use_bitset: CInt,
    nr_wake: CInt,
    wake_fn: Option<FutexWakeScanFn>,
) -> CInt {
    if chain_addr == 0 {
        return 0;
    }
    let Some(wake) = wake_fn else {
        return 0;
    };

    let head_node = chain_addr.wrapping_add(PLIST_HEAD_NODE_LIST_OFFSET);
    let mut pos = unsafe { core::ptr::read_volatile(head_node as *const usize) };
    let mut woken = 0;

    while pos != head_node {
        let next = unsafe { core::ptr::read_volatile(pos as *const usize) };
        let q_addr = pos
            .wrapping_sub(PLIST_NODE_LIST_OFFSET)
            .wrapping_sub(q_list_offset);
        let key_addr = q_addr.wrapping_add(q_key_offset);
        let word = unsafe {
            core::ptr::read_volatile(key_addr.wrapping_add(key_word_offset) as *const usize)
        };
        let ptr = unsafe {
            core::ptr::read_volatile(key_addr.wrapping_add(key_ptr_offset) as *const usize)
        };
        let offset = unsafe {
            core::ptr::read_volatile(key_addr.wrapping_add(key_offset_offset) as *const CInt)
        };

        if word == target_word && ptr == target_ptr && offset == target_offset {
            let bitset_matches = if use_bitset == 0 {
                true
            } else {
                let waiter_bitset = unsafe {
                    core::ptr::read_volatile(q_addr.wrapping_add(q_bitset_offset) as *const u32)
                };
                (waiter_bitset & requested_bitset) != 0
            };

            if bitset_matches {
                unsafe {
                    wake(q_addr);
                }
                woken += 1;
                if woken >= nr_wake {
                    break;
                }
            }
        }

        pos = next;
    }

    woken
}

#[no_mangle]
pub extern "C" fn futex_requeue_should_move_result(
    source_chain: usize,
    target_chain: usize,
) -> CInt {
    (source_chain != target_chain) as CInt
}

#[no_mangle]
pub extern "C" fn futex_requeue_loop_done_result(
    task_count: CInt,
    nr_wake: CInt,
    nr_requeue: CInt,
) -> CInt {
    ((task_count as i64 - nr_wake as i64) >= nr_requeue as i64) as CInt
}

#[no_mangle]
pub extern "C" fn futex_requeue_should_wake_result(task_count: CInt, nr_wake: CInt) -> CInt {
    (task_count <= nr_wake) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn futex_requeue_scan_result(
    chain_addr: usize,
    q_list_offset: usize,
    q_key_offset: usize,
    key_word_offset: usize,
    key_ptr_offset: usize,
    key_offset_offset: usize,
    target_word: usize,
    target_ptr: usize,
    target_offset: CInt,
    nr_wake: CInt,
    nr_requeue: CInt,
    drop_countp: *mut CInt,
    wake_fn: Option<FutexRequeueScanFn>,
    requeue_fn: Option<FutexRequeueScanFn>,
    ctx_addr: usize,
) -> CInt {
    if !drop_countp.is_null() {
        unsafe {
            core::ptr::write_volatile(drop_countp, 0);
        }
    }
    if chain_addr == 0 {
        return 0;
    }
    let Some(wake) = wake_fn else {
        return 0;
    };
    let Some(requeue) = requeue_fn else {
        return 0;
    };

    let head_node = chain_addr.wrapping_add(PLIST_HEAD_NODE_LIST_OFFSET);
    let mut pos = unsafe { core::ptr::read_volatile(head_node as *const usize) };
    let mut task_count: CInt = 0;
    let mut drop_count: CInt = 0;

    while pos != head_node {
        if (task_count as i64 - nr_wake as i64) >= nr_requeue as i64 {
            break;
        }

        let next = unsafe { core::ptr::read_volatile(pos as *const usize) };
        let q_addr = pos
            .wrapping_sub(PLIST_NODE_LIST_OFFSET)
            .wrapping_sub(q_list_offset);
        let key_addr = q_addr.wrapping_add(q_key_offset);
        let word = unsafe {
            core::ptr::read_volatile(key_addr.wrapping_add(key_word_offset) as *const usize)
        };
        let ptr = unsafe {
            core::ptr::read_volatile(key_addr.wrapping_add(key_ptr_offset) as *const usize)
        };
        let offset = unsafe {
            core::ptr::read_volatile(key_addr.wrapping_add(key_offset_offset) as *const CInt)
        };

        if word == target_word && ptr == target_ptr && offset == target_offset {
            task_count = task_count.wrapping_add(1);
            if task_count <= nr_wake {
                unsafe {
                    wake(q_addr, ctx_addr);
                }
            } else {
                unsafe {
                    requeue(q_addr, ctx_addr);
                }
                drop_count = drop_count.wrapping_add(1);
            }
        }

        pos = next;
    }

    if !drop_countp.is_null() {
        unsafe {
            core::ptr::write_volatile(drop_countp, drop_count);
        }
    }

    task_count
}

#[no_mangle]
pub unsafe extern "C" fn futex_double_lock_hb_result(
    hb1_addr: usize,
    hb2_addr: usize,
    lock_offset: usize,
    lock_fn: Option<FutexHbLockFn>,
) {
    let Some(lock) = lock_fn else {
        return;
    };

    unsafe {
        if hb1_addr <= hb2_addr {
            lock(hb1_addr.wrapping_add(lock_offset));
            if hb1_addr < hb2_addr {
                lock(hb2_addr.wrapping_add(lock_offset));
            }
        } else {
            lock(hb2_addr.wrapping_add(lock_offset));
            lock(hb1_addr.wrapping_add(lock_offset));
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_double_unlock_hb_result(
    hb1_addr: usize,
    hb2_addr: usize,
    lock_offset: usize,
    unlock_fn: Option<FutexHbUnlockFn>,
) {
    let Some(unlock) = unlock_fn else {
        return;
    };

    unsafe {
        unlock(hb1_addr.wrapping_add(lock_offset));
        if hb1_addr != hb2_addr {
            unlock(hb2_addr.wrapping_add(lock_offset));
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wake_mark_woken_result(
    q_addr: usize,
    list_offset: usize,
    node_plist_offset: usize,
    lock_ptr_offset: usize,
) {
    let list = q_addr.wrapping_add(list_offset);
    unsafe {
        crate::plist::plist_del(
            list as *mut crate::plist::PlistNode,
            list.wrapping_add(node_plist_offset) as *mut crate::plist::PlistHead,
        );
        compiler_fence(Ordering::SeqCst);
        write_volatile(q_addr.wrapping_add(lock_ptr_offset) as *mut usize, 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_unqueue_detach_result(
    q_addr: usize,
    list_offset: usize,
    node_plist_offset: usize,
) -> CInt {
    let list = q_addr.wrapping_add(list_offset);
    unsafe {
        crate::plist::plist_del(
            list as *mut crate::plist::PlistNode,
            list.wrapping_add(node_plist_offset) as *mut crate::plist::PlistHead,
        );
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn futex_requeue_move_result(
    q_addr: usize,
    list_offset: usize,
    lock_ptr_offset: usize,
    source_chain: usize,
    target_chain: usize,
    target_lock: usize,
    debug_spinlock_offset: usize,
) -> CInt {
    if source_chain == target_chain {
        return 0;
    }

    let list = q_addr.wrapping_add(list_offset);
    unsafe {
        crate::plist::plist_del(
            list as *mut crate::plist::PlistNode,
            source_chain as *mut crate::plist::PlistHead,
        );
        crate::plist::plist_add(
            list as *mut crate::plist::PlistNode,
            target_chain as *mut crate::plist::PlistHead,
        );
        write_volatile(
            q_addr.wrapping_add(lock_ptr_offset) as *mut usize,
            target_lock,
        );
        if debug_spinlock_offset != 0 {
            write_volatile(
                list.wrapping_add(debug_spinlock_offset) as *mut usize,
                target_lock,
            );
        }
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn futex_requeue_key_update_result(
    q_addr: usize,
    q_key_offset: usize,
    key_addr: usize,
    key_size: usize,
    get_refs_fn: Option<FutexKeyRefsFn>,
) -> CInt {
    if q_addr == 0 || key_addr == 0 || key_size == 0 {
        return -EINVAL;
    }
    let Some(get_refs) = get_refs_fn else {
        return -EINVAL;
    };

    unsafe {
        get_refs(key_addr);
        let dst = q_addr.wrapping_add(q_key_offset) as *mut u8;
        let src = key_addr as *const u8;
        for i in 0..key_size {
            write_volatile(dst.add(i), core::ptr::read_volatile(src.add(i)));
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn futex_queue_publish_waiter_result(
    q_addr: usize,
    task_offset: usize,
    th_spin_sleep_pa_offset: usize,
    th_status_pa_offset: usize,
    th_spin_sleep_lock_pa_offset: usize,
    proc_status_pa_offset: usize,
    proc_update_lock_pa_offset: usize,
    runq_lock_pa_offset: usize,
    clv_flags_pa_offset: usize,
    intr_id_offset: usize,
    intr_vector_offset: usize,
    task: usize,
    th_spin_sleep_pa: CULong,
    th_status_pa: CULong,
    th_spin_sleep_lock_pa: CULong,
    proc_status_pa: CULong,
    proc_update_lock_pa: CULong,
    runq_lock_pa: CULong,
    clv_flags_pa: CULong,
    intr_id: CInt,
    intr_vector: CInt,
) {
    unsafe {
        write_volatile(q_addr.wrapping_add(task_offset) as *mut usize, task);
        write_volatile(
            q_addr.wrapping_add(th_spin_sleep_pa_offset) as *mut CULong,
            th_spin_sleep_pa,
        );
        write_volatile(
            q_addr.wrapping_add(th_status_pa_offset) as *mut CULong,
            th_status_pa,
        );
        write_volatile(
            q_addr.wrapping_add(th_spin_sleep_lock_pa_offset) as *mut CULong,
            th_spin_sleep_lock_pa,
        );
        write_volatile(
            q_addr.wrapping_add(proc_status_pa_offset) as *mut CULong,
            proc_status_pa,
        );
        write_volatile(
            q_addr.wrapping_add(proc_update_lock_pa_offset) as *mut CULong,
            proc_update_lock_pa,
        );
        write_volatile(
            q_addr.wrapping_add(runq_lock_pa_offset) as *mut CULong,
            runq_lock_pa,
        );
        write_volatile(
            q_addr.wrapping_add(clv_flags_pa_offset) as *mut CULong,
            clv_flags_pa,
        );
        write_volatile(q_addr.wrapping_add(intr_id_offset) as *mut CInt, intr_id);
        write_volatile(
            q_addr.wrapping_add(intr_vector_offset) as *mut CInt,
            intr_vector,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_queue_insert_result(
    q_addr: usize,
    list_offset: usize,
    chain_addr: usize,
    prio: CInt,
    debug_spinlock_offset: usize,
    lock_addr: usize,
) {
    if q_addr == 0 || chain_addr == 0 {
        return;
    }

    let node_addr = q_addr.wrapping_add(list_offset);
    unsafe {
        write_volatile(node_addr as *mut CInt, prio);
        init_list_head_addr(node_addr.wrapping_add(PLIST_NODE_PLIST_OFFSET));
        init_list_head_addr(
            node_addr
                .wrapping_add(PLIST_NODE_PLIST_OFFSET)
                .wrapping_add(PLIST_HEAD_NODE_LIST_OFFSET),
        );
        if debug_spinlock_offset != 0 {
            write_volatile(
                node_addr.wrapping_add(debug_spinlock_offset) as *mut usize,
                lock_addr,
            );
        }
        crate::plist::plist_add(
            node_addr as *mut crate::plist::PlistNode,
            chain_addr as *mut crate::plist::PlistHead,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wait_prepare_q_result(
    q_addr: usize,
    bitset_offset: usize,
    requeue_pi_key_offset: usize,
    uti_futex_resp_offset: usize,
    bitset: u32,
    uti_futex_resp: usize,
) {
    if q_addr == 0 {
        return;
    }

    unsafe {
        write_volatile(q_addr.wrapping_add(bitset_offset) as *mut u32, bitset);
        write_volatile(q_addr.wrapping_add(requeue_pi_key_offset) as *mut usize, 0);
        write_volatile(
            q_addr.wrapping_add(uti_futex_resp_offset) as *mut usize,
            uti_futex_resp,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wait_key_init_result(
    q_addr: usize,
    key_offset: usize,
    key_size: usize,
) {
    if q_addr == 0 {
        return;
    }

    let key_addr = q_addr.wrapping_add(key_offset);
    let mut i = 0;
    while i < key_size {
        unsafe {
            write_volatile(key_addr.wrapping_add(i) as *mut u8, 0);
        }
        i += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_queue_lock_ptr_store_result(
    q_addr: usize,
    lock_ptr_offset: usize,
    lock_addr: usize,
) {
    if q_addr == 0 {
        return;
    }

    unsafe {
        write_volatile(
            q_addr.wrapping_add(lock_ptr_offset) as *mut usize,
            lock_addr,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wait_setup_result(
    uaddr: usize,
    val: u32,
    fshared: CInt,
    q_addr: usize,
    hb_out: *mut usize,
    key_offset: usize,
    key_size: usize,
    get_key_fn: Option<FutexWaitGetKeyFn>,
    queue_lock_fn: Option<FutexWaitQueueLockFn>,
    get_value_fn: Option<FutexWaitGetValueFn>,
    queue_unlock_fn: Option<FutexWaitQueueUnlockFn>,
    put_key_fn: Option<FutexWaitPutKeyFn>,
) -> CInt {
    if q_addr == 0 {
        return -EINVAL;
    }
    let Some(get_key) = get_key_fn else {
        return -EINVAL;
    };
    let Some(queue_lock) = queue_lock_fn else {
        return -EINVAL;
    };
    let Some(get_value) = get_value_fn else {
        return -EINVAL;
    };
    let Some(queue_unlock) = queue_unlock_fn else {
        return -EINVAL;
    };
    let Some(put_key) = put_key_fn else {
        return -EINVAL;
    };

    unsafe {
        futex_wait_key_init_result(q_addr, key_offset, key_size);
    }
    let key_addr = q_addr.wrapping_add(key_offset);
    let mut ret = unsafe { get_key(uaddr, fshared, key_addr) };
    if ret != 0 {
        return ret;
    }

    let hb_addr = unsafe { queue_lock(q_addr) };
    if !hb_out.is_null() {
        unsafe {
            core::ptr::write_volatile(hb_out, hb_addr);
        }
    }

    let mut uval = 0u32;
    ret = unsafe { get_value((&raw mut uval) as usize, uaddr) };
    if ret != 0 {
        unsafe {
            queue_unlock(q_addr, hb_addr);
            put_key(fshared, key_addr);
        }
        return ret;
    }

    if uval != val {
        unsafe {
            queue_unlock(q_addr, hb_addr);
            put_key(fshared, key_addr);
        }
        return -EWOULDBLOCK;
    }

    0
}

#[inline(always)]
unsafe fn atomic_i32_at(addr: usize, offset: usize) -> Option<&'static AtomicI32> {
    if addr == 0 {
        None
    } else {
        Some(unsafe { &*((addr.wrapping_add(offset)) as *const AtomicI32) })
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wait_mark_interruptible_result(
    thread_addr: usize,
    status_offset: usize,
    interruptible_status: CInt,
) -> CInt {
    unsafe {
        atomic_i32_at(thread_addr, status_offset)
            .map(|status| status.swap(interruptible_status, Ordering::SeqCst))
            .unwrap_or(0)
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wait_spin_sleep_store_result(
    thread_addr: usize,
    spin_sleep_offset: usize,
    value: CInt,
) -> CInt {
    if thread_addr == 0 {
        return 0;
    }

    unsafe {
        let spin_sleep = thread_addr.wrapping_add(spin_sleep_offset) as *mut CInt;
        let old = core::ptr::read_volatile(spin_sleep);
        write_volatile(spin_sleep, value);
        old
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wait_finish_state_result(
    thread_addr: usize,
    status_offset: usize,
    spin_sleep_offset: usize,
    running_status: CInt,
) -> CInt {
    if thread_addr == 0 {
        return 0;
    }

    unsafe {
        let status = thread_addr.wrapping_add(status_offset) as *mut CInt;
        let old = core::ptr::read_volatile(status);
        write_volatile(status, running_status);
        write_volatile(thread_addr.wrapping_add(spin_sleep_offset) as *mut CInt, 0);
        old
    }
}

#[no_mangle]
pub extern "C" fn futex_wait_schedule_action_result(queued: CInt, timeout: u64) -> CInt {
    if queued == 0 {
        return FUTEX_WAIT_SCHEDULE_NONE;
    }
    if timeout != 0 {
        FUTEX_WAIT_SCHEDULE_TIMEOUT
    } else {
        FUTEX_WAIT_SCHEDULE_DIRECT
    }
}

#[no_mangle]
pub extern "C" fn futex_wait_post_action_result(
    unqueued: CInt,
    timeout: u64,
    time_remain: i64,
    has_pending_signal: CInt,
    restart_sys: CInt,
) -> CInt {
    if unqueued == 0 {
        return FUTEX_WAIT_POST_SUCCESS;
    }
    if timeout != 0 && time_remain == 0 {
        return FUTEX_WAIT_POST_TIMEOUT;
    }
    if has_pending_signal != 0 || restart_sys != 0 {
        return FUTEX_WAIT_POST_INTERRUPT;
    }
    FUTEX_WAIT_POST_RETRY
}

#[no_mangle]
pub extern "C" fn futex_wake_target_result(uti_futex_resp: usize) -> CInt {
    if uti_futex_resp != 0 {
        FUTEX_WAKE_TARGET_LINUX
    } else {
        FUTEX_WAKE_TARGET_MCKERNEL
    }
}

#[no_mangle]
pub extern "C" fn futex_wake_linux_channel_result(
    linux_channel: usize,
    fallback_channel: usize,
) -> usize {
    if linux_channel != 0 {
        linux_channel
    } else {
        fallback_channel
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wake_ikc_packet_fill_result(
    packet_addr: usize,
    msg_offset: usize,
    resp_offset: usize,
    spin_sleep_offset: usize,
    msg: CInt,
    resp: usize,
    spin_sleep_addr: usize,
) {
    if packet_addr == 0 {
        return;
    }

    unsafe {
        write_volatile(packet_addr.wrapping_add(msg_offset) as *mut CInt, msg);
        write_volatile(packet_addr.wrapping_add(resp_offset) as *mut usize, resp);
        write_volatile(
            packet_addr.wrapping_add(spin_sleep_offset) as *mut usize,
            spin_sleep_addr,
        );
    }
}

#[inline(always)]
unsafe fn read_usize_field(base: usize, offset: usize) -> usize {
    read_volatile(base.wrapping_add(offset) as *const usize)
}

#[inline(always)]
unsafe fn read_cint_field(base: usize, offset: usize) -> CInt {
    read_volatile(base.wrapping_add(offset) as *const CInt)
}

#[no_mangle]
pub unsafe extern "C" fn futex_wake_orchestrate_result(
    q_addr: usize,
    q_list_offset: usize,
    q_node_plist_offset: usize,
    q_lock_ptr_offset: usize,
    q_task_offset: usize,
    q_uti_futex_resp_offset: usize,
    q_linux_cpu_offset: usize,
    thread_spin_sleep_offset: usize,
    packet_addr: usize,
    packet_msg_offset: usize,
    packet_resp_offset: usize,
    packet_spin_sleep_offset: usize,
    msg: CInt,
    fallback_channel: usize,
    wake_status: CInt,
    linux_channel_fn: Option<FutexWakeLinuxChannelByCpuFn>,
    send_fn: Option<FutexWakeSendFn>,
    wake_thread_fn: Option<FutexWakeThreadFn>,
    log_fn: Option<FutexWakeLogFn>,
) -> CInt {
    if q_addr == 0 {
        return -EINVAL;
    }

    let thread_addr = read_usize_field(q_addr, q_task_offset);
    let uti_futex_resp = read_usize_field(q_addr, q_uti_futex_resp_offset);

    futex_wake_mark_woken_result(
        q_addr,
        q_list_offset,
        q_node_plist_offset,
        q_lock_ptr_offset,
    );

    let target = futex_wake_target_result(uti_futex_resp);
    if target == FUTEX_WAKE_TARGET_LINUX {
        let linux_cpu = read_cint_field(q_addr, q_linux_cpu_offset);
        let linux_channel = if let Some(linux_channel_fn) = linux_channel_fn {
            linux_channel_fn(linux_cpu)
        } else {
            0
        };
        let resp_channel = futex_wake_linux_channel_result(linux_channel, fallback_channel);
        if let Some(log_fn) = log_fn {
            log_fn(
                FUTEX_WAKE_LOG_LINUX_TARGET,
                thread_addr,
                uti_futex_resp,
                linux_cpu,
                resp_channel,
                0,
            );
        }
        futex_wake_ikc_packet_fill_result(
            packet_addr,
            packet_msg_offset,
            packet_resp_offset,
            packet_spin_sleep_offset,
            msg,
            uti_futex_resp,
            thread_addr.wrapping_add(thread_spin_sleep_offset),
        );

        let mut rc = -ENOSYS;
        if let Some(send_fn) = send_fn {
            rc = send_fn(resp_channel, packet_addr);
        }
        if let Some(log_fn) = log_fn {
            log_fn(
                if rc < 0 {
                    FUTEX_WAKE_LOG_SEND_FAILED
                } else {
                    FUTEX_WAKE_LOG_SEND_OK
                },
                thread_addr,
                uti_futex_resp,
                linux_cpu,
                resp_channel,
                rc,
            );
        }
        return target;
    }

    if let Some(wake_thread_fn) = wake_thread_fn {
        if let Some(log_fn) = log_fn {
            log_fn(
                FUTEX_WAKE_LOG_MCKERNEL_TARGET,
                thread_addr,
                uti_futex_resp,
                0,
                0,
                0,
            );
        }
        wake_thread_fn(thread_addr, wake_status);
    }
    target
}

#[no_mangle]
pub extern "C" fn syscall_offload_should_schedule_result(
    no_preempt: CInt,
    tid: CInt,
    need_resched: CInt,
    runq_len: CInt,
    is_sched_setaffinity: CInt,
) -> CInt {
    if no_preempt != 0 || tid == 0 {
        return 0;
    }

    (need_resched != 0 || runq_len > 1 || is_sched_setaffinity != 0) as CInt
}
