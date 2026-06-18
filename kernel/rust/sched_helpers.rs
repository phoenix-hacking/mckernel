use core::mem::offset_of;
use core::ptr::{read_volatile, write_volatile};
use core::sync::atomic::{compiler_fence, AtomicI32, Ordering};

use crate::abi::{
    AbiListHead, AddressSpace, CInt, CLong, CULong, CpuLocalVar, IhkSpinlock, Process, ProcessVm,
    SigCommon, SizeT, Thread, TimeSpec, Waitq, CPU_SET_MAX_CPUS,
};

unsafe extern "C" {
    fn ihk_mc_get_processor_id() -> CInt;
    fn process_sched_cpu_local_bridge(cpu_id: CInt) -> usize;
    #[link_name = "process_spin_lock_bridge"]
    fn process_spin_lock_bridge_c(lock_addr: CULong) -> CULong;
    #[link_name = "process_spin_unlock_bridge"]
    fn process_spin_unlock_bridge_c(lock_addr: CULong, irqstate: CULong);
    #[link_name = "process_sched_noirq_lock_bridge"]
    fn process_sched_noirq_lock_bridge_c(lock_addr: CULong);
    #[link_name = "process_sched_noirq_unlock_bridge"]
    fn process_sched_noirq_unlock_bridge_c(lock_addr: CULong);
    fn process_sched_waitq_wakeup_bridge(waitq_addr: usize);
    fn process_sched_vector_bridge(vector_key: CInt) -> CInt;
    fn process_sched_interrupt_bridge(cpu: CInt, vector: CInt);
    fn process_sched_schedule_bridge();
    fn process_sched_runq_log_bridge(event: CInt, arg0: usize, arg1: usize, arg2: CInt, arg3: CInt);
    static mut runq_reservation_lock: IhkSpinlock;
    fn process_sched_do_migrate_log_bridge(
        thread_addr: usize,
        tid: CInt,
        old_cpu_id: CInt,
        new_cpu_id: CInt,
    );
}

type FutexHbLockFn = unsafe extern "C" fn(usize);
type FutexHbUnlockFn = unsafe extern "C" fn(usize);
type FutexWakeScanFn = unsafe extern "C" fn(usize);
type FutexRequeueScanFn = unsafe extern "C" fn(usize, usize);
type FutexKeyRefsFn = unsafe extern "C" fn(usize);
type FutexGetKeyVtopFn = unsafe extern "C" fn(usize, usize, usize) -> CInt;
type FutexGetKeyFaultFn = unsafe extern "C" fn(usize, usize, CInt) -> CInt;
type FutexGetKeyLogFn = unsafe extern "C" fn(CInt);
type FutexWakeHashKeyFn = unsafe extern "C" fn(usize) -> usize;
type FutexWakeLockFn = unsafe extern "C" fn(usize) -> CULong;
type FutexWakeUnlockFn = unsafe extern "C" fn(usize, CULong);
type FutexWaitGetKeyFn = unsafe extern "C" fn(usize, CInt, usize) -> CInt;
type FutexWakeAtomicOpFn = unsafe extern "C" fn(CInt, usize) -> CInt;
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
type FutexVirtToPhysFn = unsafe extern "C" fn(usize) -> CULong;
type FutexInterruptIdFn = unsafe extern "C" fn(CInt) -> CInt;
type FutexVectorFn = unsafe extern "C" fn(CInt) -> CInt;
type FutexWaitSpinLockFn = unsafe extern "C" fn(usize) -> CULong;
type FutexWaitSpinUnlockFn = unsafe extern "C" fn(usize, CULong);
type FutexWaitQueueMeFn = unsafe extern "C" fn(usize, usize);
type FutexWaitScheduleTimeoutFn = unsafe extern "C" fn(u64) -> i64;
type FutexWaitScheduleDirectFn = unsafe extern "C" fn();
type FutexWaitQueueLogFn = unsafe extern "C" fn(CInt, usize, CInt);
type FutexWaitSetupCallFn = unsafe extern "C" fn(usize, u32, CInt, usize, usize) -> CInt;
type FutexWaitQueueCallFn = unsafe extern "C" fn(usize, usize, u64) -> i64;
type FutexWaitUnqueueFn = unsafe extern "C" fn(usize) -> CInt;
type FutexWaitHasSignalFn = unsafe extern "C" fn(usize) -> CInt;
type FutexWaitLogFn = unsafe extern "C" fn(CInt, usize, CInt, CInt);
type FutexWaitTimestampFn = unsafe extern "C" fn() -> usize;
type FutexWaitBodyEntryFn =
    unsafe extern "C" fn(usize, CInt, u32, u64, u32, usize, usize, usize) -> CInt;
type TimerSpinInitFn = unsafe extern "C" fn(usize);
type TimerSpinLockFn = unsafe extern "C" fn(usize) -> CULong;
type TimerSpinUnlockFn = unsafe extern "C" fn(usize, CULong);
type TimerRdtscFn = unsafe extern "C" fn() -> u64;
type TimerVoidFn = unsafe extern "C" fn();
type TimerSetStatusFn = unsafe extern "C" fn(usize, CInt);
type TimerLapicEnableFn = unsafe extern "C" fn(u32);
type TimerLapicDisableFn = unsafe extern "C" fn();
type TimerWaitqWakeupFn = unsafe extern "C" fn(usize);
type TimerLogWakeFn = unsafe extern "C" fn(usize, usize);
type SchedMigrateSpinLockFn = unsafe extern "C" fn(usize) -> CULong;
type SchedMigrateSpinUnlockFn = unsafe extern "C" fn(usize, CULong);
type SchedMigrateNoirqLockFn = unsafe extern "C" fn(usize);
type SchedMigrateNoirqUnlockFn = unsafe extern "C" fn(usize);
type SchedMigrateWaitqInitFn = unsafe extern "C" fn(usize);
type SchedMigrateWaitqPrepareFn = unsafe extern "C" fn(usize, usize, CInt);
type SchedMigrateWaitqFinishFn = unsafe extern "C" fn(usize, usize);
type SchedMigrateVectorFn = unsafe extern "C" fn(CInt) -> CInt;
type SchedMigrateInterruptFn = unsafe extern "C" fn(CInt, CInt);
type SchedMigrateVoidFn = unsafe extern "C" fn();
type SchedMigrateLogFn = unsafe extern "C" fn(usize, CInt, CInt);
type SchedMigrateCpuLocalFn = unsafe extern "C" fn(CInt) -> usize;
type SchedMigrateWaitqWakeupFn = unsafe extern "C" fn(usize);
type SchedDoMigrateLogFn = unsafe extern "C" fn(usize, CInt, CInt, CInt);
type SchedRunqRwlockFn = unsafe extern "C" fn(usize, usize);
type SchedRunqStatusSetFn = unsafe extern "C" fn(usize, CInt);
type SchedRunqSetTimerFn = unsafe extern "C" fn(CInt);
type SchedRunqLogFn = unsafe extern "C" fn(CInt, usize, usize, CInt, CInt);
type SchedRunqIrqSaveFn = unsafe extern "C" fn() -> CULong;
type SchedRunqIrqRestoreFn = unsafe extern "C" fn(CULong);
type SchedRunqHasSignalFn = unsafe extern "C" fn(usize) -> CInt;
type SchedRunqVoidFn = unsafe extern "C" fn();
type SchedRunqThreadFn = unsafe extern "C" fn(usize);
type SchedRunqCounterIncFn = unsafe extern "C" fn(usize) -> CInt;
type SchedRunqCounterDecFn = unsafe extern "C" fn(usize);
type SchedFindThreadFn = unsafe extern "C" fn(CInt) -> usize;
type SchedThreadUnlockFn = unsafe extern "C" fn(usize);
type SchedHoldThreadFn = unsafe extern "C" fn(usize) -> CInt;
type SchedReleaseThreadFn = unsafe extern "C" fn(usize);
type SchedCopyFromUserFn = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;
type SchedCopyToUserFn = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;
type SchedDoSyscall2Fn = unsafe extern "C" fn(CInt, CULong, CULong) -> CLong;
type SchedApplySchedulerFn = unsafe extern "C" fn(usize, CInt, usize) -> CInt;
type SchedRequestMigrateFn = unsafe extern "C" fn(CInt, usize);

const EINVAL: CInt = 22;
const EPERM: CInt = 1;
const ESRCH: CInt = 3;
const EWOULDBLOCK: CInt = 11;
const SCHED_NORMAL: CInt = 0;
const SCHED_FIFO: CInt = 1;
const SCHED_RR: CInt = 2;
const SCHED_BATCH: CInt = 3;
const SCHED_IDLE: CInt = 5;
const SCHED_DEADLINE: CInt = 6;
const MAX_NICE: CInt = 19;
const MIN_NICE: CInt = -20;
const NICE_WIDTH: CInt = MAX_NICE - MIN_NICE + 1;
const MAX_USER_RT_PRIO: CInt = 100;
const MAX_RT_PRIO: CInt = MAX_USER_RT_PRIO;
const DEFAULT_PRIO: CInt = MAX_RT_PRIO + NICE_WIDTH / 2;
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
const FUTEX_WAIT_QUEUE_LOG_TIMEOUT: CInt = 1;
const FUTEX_WAIT_QUEUE_LOG_DIRECT: CInt = 2;
const FUTEX_WAIT_QUEUE_LOG_WOKEN: CInt = 3;
const FUTEX_WAIT_LOG_SETUP_RET: CInt = 1;
const FUTEX_WAIT_LOG_SUCCESS: CInt = 2;
const FUTEX_WAIT_LOG_TIMEOUT: CInt = 3;
const FUTEX_WAIT_LOG_INTERRUPT: CInt = 4;
const FUTEX_GET_KEY_LOG_VTOP_FAILED: CInt = 1;
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
const EINTR: CInt = 4;
const ETIMEDOUT: CInt = 110;
const ERESTARTSYS: i64 = 512;
const ENOSYS: CInt = 38;
const EFAULT: CInt = 14;
const PS_RUNNING: CInt = 0x1;
const CPU_FLAG_NEED_RESCHED: u32 = 0x1;
const CPU_FLAG_NEED_MIGRATE: u32 = 0x2;
const CPU_STATUS_IDLE: CInt = 1;
const IHK_GV_IKC: CInt = 1;
const PLIST_NODE_PLIST_OFFSET: usize = 8;
const PLIST_HEAD_NODE_LIST_OFFSET: usize = 16;
const PLIST_NODE_LIST_OFFSET: usize = PLIST_NODE_PLIST_OFFSET + PLIST_HEAD_NODE_LIST_OFFSET;
const SCHED_CHECK_SAME_OWNER: CULong = 0x01;
const SCHED_CHECK_ROOT: CULong = 0x02;
const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;
const SCHED_RUNQ_LOG_NO_MIGRATION_IRQ: CInt = 1;
const SCHED_RUNQ_LOG_WAKE_ENTRY: CInt = 2;
const SCHED_RUNQ_LOG_SPIN_WAKEUP: CInt = 3;
const SCHED_RUNQ_LOG_REMOTE_IPI: CInt = 4;
const SCHED_RUNQ_LOG_RUNQ_ADD: CInt = 5;
const SCHED_RUNQ_LOG_IDLE_HALT: CInt = 6;
const SCHED_RUNQ_LOG_LOST_WAKEUP: CInt = 7;
const SCHED_RUNQ_LOG_SPIN_WOKEN: CInt = 8;
const SCHED_RUNQ_LOG_SLEEP_WOKEN: CInt = 9;
const SCHED_RUNQ_LOG_NO_PREEMPT: CInt = 10;
const SCHED_RUNQ_LOG_CLONE_COUNT: CInt = 11;
const SCHED_SCHEDULE_ACTION_RESCHED_ONLY: CInt = 1;
const SCHED_SCHEDULE_ACTION_NO_SWITCH: CInt = 2;
const SCHED_SCHEDULE_ACTION_SWITCH: CInt = 3;

#[repr(C)]
pub struct SchedSyscallOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_sched_param_offset: SizeT,
    pub thread_sched_policy_offset: SizeT,
    pub thread_cpu_id_offset: SizeT,
    pub thread_cpu_set_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_ruid_offset: SizeT,
    pub proc_euid_offset: SizeT,
    pub proc_cpu_set_offset: SizeT,
}

#[repr(C)]
pub struct TimerRuntimeOffsets {
    pub thread_status_offset: usize,
    pub thread_sched_list_offset: usize,
    pub thread_spin_sleep_lock_offset: usize,
    pub thread_spin_sleep_offset: usize,
    pub thread_itimer_enabled_offset: usize,
    pub cpu_runq_lock_offset: usize,
    pub cpu_runq_offset: usize,
    pub cpu_runq_len_offset: usize,
    pub cpu_current_offset: usize,
    pub cpu_timer_enabled_offset: usize,
    pub cpu_backlog_list_offset: usize,
    pub timer_timeout_offset: usize,
    pub timer_waitq_offset: usize,
    pub timer_list_offset: usize,
    pub timer_thread_offset: usize,
}

#[repr(C)]
pub struct SchedMigrateOffsets {
    pub req_list_offset: usize,
    pub req_thread_offset: usize,
    pub req_wq_offset: usize,
    pub thread_cpu_id_offset: usize,
    pub thread_tid_offset: usize,
    pub cpu_migq_lock_offset: usize,
    pub cpu_migq_offset: usize,
    pub cpu_runq_lock_offset: usize,
    pub cpu_flags_offset: usize,
    pub cpu_status_offset: usize,
}

#[repr(C)]
struct SchedMigrateRequest {
    list: AbiListHead,
    thread: *mut Thread,
    wq: Waitq,
}

unsafe extern "C" fn sched_process_spin_lock_bridge(lock_addr: usize) -> CULong {
    unsafe { process_spin_lock_bridge_c(lock_addr as CULong) }
}

unsafe extern "C" fn sched_process_spin_unlock_bridge(lock_addr: usize, irqstate: CULong) {
    unsafe { process_spin_unlock_bridge_c(lock_addr as CULong, irqstate) }
}

unsafe extern "C" fn sched_process_noirq_lock_bridge(lock_addr: usize) {
    unsafe { process_sched_noirq_lock_bridge_c(lock_addr as CULong) }
}

unsafe extern "C" fn sched_process_noirq_unlock_bridge(lock_addr: usize) {
    unsafe { process_sched_noirq_unlock_bridge_c(lock_addr as CULong) }
}

#[repr(C)]
pub struct SchedDoMigrateOffsets {
    pub req_list_offset: usize,
    pub req_thread_offset: usize,
    pub req_wq_offset: usize,
    pub thread_cpu_id_offset: usize,
    pub thread_tid_offset: usize,
    pub thread_cpu_set_offset: usize,
    pub thread_sched_list_offset: usize,
    pub thread_vm_offset: usize,
    pub vm_address_space_offset: usize,
    pub address_space_cpu_set_offset: usize,
    pub address_space_cpu_set_lock_offset: usize,
    pub cpu_migq_lock_offset: usize,
    pub cpu_migq_offset: usize,
    pub cpu_runq_lock_offset: usize,
    pub cpu_runq_offset: usize,
    pub cpu_runq_len_offset: usize,
    pub cpu_flags_offset: usize,
}

#[repr(C)]
pub struct SchedRunqueueOffsets {
    pub thread_cpu_id_offset: usize,
    pub thread_tid_offset: usize,
    pub thread_status_offset: usize,
    pub thread_spin_sleep_lock_offset: usize,
    pub thread_spin_sleep_offset: usize,
    pub thread_sched_list_offset: usize,
    pub thread_sigpending_offset: usize,
    pub thread_sigcommon_offset: usize,
    pub sigcommon_sigpending_offset: usize,
    pub thread_proc_offset: usize,
    pub thread_mod_clone_offset: usize,
    pub proc_pid_offset: usize,
    pub proc_status_offset: usize,
    pub proc_update_lock_offset: usize,
    pub proc_clone_count_offset: usize,
    pub cpu_runq_lock_offset: usize,
    pub cpu_runq_irqstate_offset: usize,
    pub cpu_current_offset: usize,
    pub cpu_prevpid_offset: usize,
    pub cpu_runq_offset: usize,
    pub cpu_runq_len_offset: usize,
    pub cpu_runq_reserved_offset: usize,
    pub cpu_flags_offset: usize,
    pub cpu_status_offset: usize,
    pub cpu_in_interrupt_offset: usize,
    pub cpu_nr_ctx_switches_offset: usize,
}

fn sched_runqueue_offsets() -> SchedRunqueueOffsets {
    SchedRunqueueOffsets {
        thread_cpu_id_offset: offset_of!(Thread, cpu_id),
        thread_tid_offset: offset_of!(Thread, tid),
        thread_status_offset: offset_of!(Thread, status),
        thread_spin_sleep_lock_offset: offset_of!(Thread, spin_sleep_lock),
        thread_spin_sleep_offset: offset_of!(Thread, spin_sleep),
        thread_sched_list_offset: offset_of!(Thread, sched_list),
        thread_sigpending_offset: offset_of!(Thread, sigpending),
        thread_sigcommon_offset: offset_of!(Thread, sigcommon),
        sigcommon_sigpending_offset: offset_of!(SigCommon, sigpending),
        thread_proc_offset: offset_of!(Thread, proc),
        thread_mod_clone_offset: offset_of!(Thread, mod_clone),
        proc_pid_offset: offset_of!(Process, pid),
        proc_status_offset: offset_of!(Process, status),
        proc_update_lock_offset: offset_of!(Process, update_lock),
        proc_clone_count_offset: offset_of!(Process, clone_count),
        cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
        cpu_runq_irqstate_offset: offset_of!(CpuLocalVar, runq_irqstate),
        cpu_current_offset: offset_of!(CpuLocalVar, current),
        cpu_prevpid_offset: offset_of!(CpuLocalVar, prevpid),
        cpu_runq_offset: offset_of!(CpuLocalVar, runq),
        cpu_runq_len_offset: offset_of!(CpuLocalVar, runq_len),
        cpu_runq_reserved_offset: offset_of!(CpuLocalVar, runq_reserved),
        cpu_flags_offset: offset_of!(CpuLocalVar, flags),
        cpu_status_offset: offset_of!(CpuLocalVar, status),
        cpu_in_interrupt_offset: offset_of!(CpuLocalVar, in_interrupt),
        cpu_nr_ctx_switches_offset: offset_of!(CpuLocalVar, nr_ctx_switches),
    }
}

#[repr(C)]
pub struct SchedScheduleResult {
    pub cpu_addr: usize,
    pub prev_thread_addr: usize,
    pub next_thread_addr: usize,
    pub prevpid: CInt,
    pub switch_ctx: CInt,
    pub action: CInt,
}

unsafe fn init_list_head_addr(list_addr: usize) {
    unsafe {
        write_volatile(list_addr as *mut usize, list_addr);
        write_volatile(
            list_addr.wrapping_add(core::mem::size_of::<usize>()) as *mut usize,
            list_addr,
        );
    }
}

#[inline(always)]
unsafe fn list_next(list_addr: usize) -> usize {
    unsafe { read_volatile(list_addr as *const usize) }
}

#[inline(always)]
unsafe fn list_prev_addr(list_addr: usize) -> usize {
    unsafe { read_volatile(list_addr.wrapping_add(core::mem::size_of::<usize>()) as *const usize) }
}

#[inline(always)]
unsafe fn list_empty_addr(list_addr: usize) -> bool {
    unsafe { list_next(list_addr) == list_addr }
}

#[inline(always)]
unsafe fn list_del_addr(entry_addr: usize) {
    let next = unsafe { list_next(entry_addr) };
    let prev = unsafe { list_prev_addr(entry_addr) };

    unsafe {
        write_volatile(
            next.wrapping_add(core::mem::size_of::<usize>()) as *mut usize,
            prev,
        );
        write_volatile(prev as *mut usize, next);
    }
}

#[inline(always)]
unsafe fn list_detach_poison_addr(entry_addr: usize) -> bool {
    if entry_addr == 0 {
        return false;
    }
    let next = unsafe { list_next(entry_addr) };
    let prev = unsafe { list_prev_addr(entry_addr) };
    if next == 0 || prev == 0 || next == entry_addr {
        return false;
    }

    unsafe {
        write_volatile(
            next.wrapping_add(core::mem::size_of::<usize>()) as *mut usize,
            prev,
        );
        write_volatile(prev as *mut usize, next);
        write_volatile(entry_addr as *mut usize, LIST_POISON1);
        write_volatile(
            entry_addr.wrapping_add(core::mem::size_of::<usize>()) as *mut usize,
            LIST_POISON2,
        );
    }
    true
}

#[inline(always)]
unsafe fn list_add_tail_addr(entry_addr: usize, head_addr: usize) {
    let prev = unsafe { list_prev_addr(head_addr) };

    unsafe {
        write_volatile(entry_addr as *mut usize, head_addr);
        write_volatile(
            entry_addr.wrapping_add(core::mem::size_of::<usize>()) as *mut usize,
            prev,
        );
        write_volatile(prev as *mut usize, entry_addr);
        write_volatile(
            head_addr.wrapping_add(core::mem::size_of::<usize>()) as *mut usize,
            entry_addr,
        );
    }
}

#[inline(always)]
unsafe fn list_add_tail_counted_addr(entry_addr: usize, head_addr: usize, len_addr: usize) -> bool {
    if entry_addr == 0 || head_addr == 0 || len_addr == 0 {
        return false;
    }
    unsafe {
        list_add_tail_addr(entry_addr, head_addr);
        let len = read_volatile(len_addr as *const usize);
        write_volatile(len_addr as *mut usize, len.wrapping_add(1));
    }
    true
}

#[inline(always)]
unsafe fn list_detach_counted_addr(entry_addr: usize, len_addr: usize) -> bool {
    if len_addr == 0 || unsafe { !list_detach_poison_addr(entry_addr) } {
        return false;
    }
    unsafe {
        let len = read_volatile(len_addr as *const usize);
        write_volatile(len_addr as *mut usize, len.wrapping_sub(1));
    }
    true
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
pub extern "C" fn NICE_TO_PRIO(nice: CInt) -> CInt {
    nice.wrapping_add(DEFAULT_PRIO)
}

#[no_mangle]
pub extern "C" fn PRIO_TO_NICE(prio: CInt) -> CInt {
    prio.wrapping_sub(DEFAULT_PRIO)
}

#[no_mangle]
pub extern "C" fn USER_PRIO(prio: CInt) -> CInt {
    prio.wrapping_sub(MAX_RT_PRIO)
}

#[no_mangle]
pub extern "C" fn nice_to_rlimit(nice: CLong) -> CLong {
    (MAX_NICE as CLong).wrapping_sub(nice).wrapping_add(1)
}

#[no_mangle]
pub extern "C" fn rlimit_to_nice(prio: CLong) -> CLong {
    (MAX_NICE as CLong).wrapping_sub(prio).wrapping_add(1)
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

#[no_mangle]
pub extern "C" fn sched_get_priority_max_body_result(policy: CInt) -> CLong {
    sched_get_priority_max_value(policy) as CLong
}

#[no_mangle]
pub extern "C" fn sched_get_priority_min_body_result(policy: CInt) -> CLong {
    sched_get_priority_min_value(policy) as CLong
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

#[inline(always)]
fn sched_errno(errno: CInt) -> CLong {
    -(errno as CLong)
}

#[inline(always)]
unsafe fn sched_read_usize(base: usize, offset: SizeT) -> usize {
    unsafe { read_volatile(base.wrapping_add(offset) as *const usize) }
}

#[inline(always)]
unsafe fn sched_read_int(base: usize, offset: SizeT) -> CInt {
    unsafe { read_volatile(base.wrapping_add(offset) as *const CInt) }
}

#[inline(always)]
unsafe fn sched_thread_proc(thread_addr: usize, offsets: &SchedSyscallOffsets) -> usize {
    unsafe { sched_read_usize(thread_addr, offsets.thread_proc_offset) }
}

#[inline(always)]
unsafe fn sched_thread_pid(thread_addr: usize, offsets: &SchedSyscallOffsets) -> CInt {
    let proc_addr = unsafe { sched_thread_proc(thread_addr, offsets) };
    if proc_addr == 0 {
        return -1;
    }
    unsafe { sched_read_int(proc_addr, offsets.proc_pid_offset) }
}

#[inline(always)]
unsafe fn sched_thread_policy(thread_addr: usize, offsets: &SchedSyscallOffsets) -> CInt {
    unsafe { sched_read_int(thread_addr, offsets.thread_sched_policy_offset) }
}

#[inline(always)]
unsafe fn sched_thread_cpu_id(thread_addr: usize, offsets: &SchedSyscallOffsets) -> CInt {
    unsafe { sched_read_int(thread_addr, offsets.thread_cpu_id_offset) }
}

#[inline(always)]
unsafe fn sched_proc_ruid(proc_addr: usize, offsets: &SchedSyscallOffsets) -> u32 {
    unsafe { read_volatile(proc_addr.wrapping_add(offsets.proc_ruid_offset) as *const u32) }
}

#[inline(always)]
unsafe fn sched_proc_euid(proc_addr: usize, offsets: &SchedSyscallOffsets) -> u32 {
    unsafe { read_volatile(proc_addr.wrapping_add(offsets.proc_euid_offset) as *const u32) }
}

unsafe fn sched_cpuset_zero(cpuset_addr: usize, cpuset_size: SizeT) {
    let word_size = core::mem::size_of::<CULong>();
    let words = cpuset_size / word_size;
    let tail = cpuset_size % word_size;

    for index in 0..words {
        unsafe {
            write_volatile(
                cpuset_addr.wrapping_add(index * word_size) as *mut CULong,
                0,
            );
        }
    }
    let tail_base = cpuset_addr.wrapping_add(words * word_size);
    for index in 0..tail {
        unsafe {
            write_volatile(tail_base.wrapping_add(index) as *mut u8, 0);
        }
    }
}

unsafe fn sched_cpuset_copy(dst_addr: usize, src_addr: usize, bytes: SizeT) {
    let word_size = core::mem::size_of::<CULong>();
    let words = bytes / word_size;
    let tail = bytes % word_size;

    for index in 0..words {
        let offset = index * word_size;
        let value = unsafe { read_volatile(src_addr.wrapping_add(offset) as *const CULong) };
        unsafe {
            write_volatile(dst_addr.wrapping_add(offset) as *mut CULong, value);
        }
    }
    let tail_base = words * word_size;
    for index in 0..tail {
        let offset = tail_base + index;
        let value = unsafe { read_volatile(src_addr.wrapping_add(offset) as *const u8) };
        unsafe {
            write_volatile(dst_addr.wrapping_add(offset) as *mut u8, value);
        }
    }
}

#[inline(always)]
unsafe fn sched_cpuset_is_set(cpuset_addr: usize, cpuset_size: SizeT, cpu: CInt) -> bool {
    if cpu < 0 {
        return false;
    }
    let cpu = cpu as usize;
    if cpu >= cpuset_size.saturating_mul(8) {
        return false;
    }
    let word_bits = core::mem::size_of::<CULong>() * 8;
    let word_index = cpu / word_bits;
    let bit = cpu % word_bits;
    let value = unsafe {
        read_volatile(
            cpuset_addr.wrapping_add(word_index * core::mem::size_of::<CULong>()) as *const CULong,
        )
    };
    (value & (1u64 << bit)) != 0
}

#[inline(always)]
unsafe fn sched_cpuset_set(cpuset_addr: usize, cpuset_size: SizeT, cpu: CInt) {
    if cpu < 0 {
        return;
    }
    let cpu = cpu as usize;
    if cpu >= cpuset_size.saturating_mul(8) {
        return;
    }
    let word_bits = core::mem::size_of::<CULong>() * 8;
    let word_index = cpu / word_bits;
    let bit = cpu % word_bits;
    let word_addr =
        cpuset_addr.wrapping_add(word_index * core::mem::size_of::<CULong>()) as *mut CULong;
    let value = unsafe { read_volatile(word_addr) };
    unsafe {
        write_volatile(word_addr, value | (1u64 << bit));
    }
}

unsafe fn sched_normalized_pid(
    pid: CInt,
    current_thread: usize,
    offsets: &SchedSyscallOffsets,
) -> Result<CInt, CLong> {
    if pid < 0 || current_thread == 0 {
        return Err(sched_errno(EINVAL));
    }
    if pid != 0 {
        return Ok(pid);
    }
    let current_pid = unsafe { sched_thread_pid(current_thread, offsets) };
    if current_pid < 0 {
        return Err(sched_errno(EINVAL));
    }
    Ok(current_pid)
}

unsafe fn sched_select_thread(
    pid: CInt,
    current_thread: usize,
    offsets: &SchedSyscallOffsets,
    find_fn: Option<SchedFindThreadFn>,
    unlock_fn: Option<SchedThreadUnlockFn>,
) -> Result<(usize, CInt, bool), CLong> {
    let normalized_pid = unsafe { sched_normalized_pid(pid, current_thread, offsets)? };
    let current_pid = unsafe { sched_thread_pid(current_thread, offsets) };
    if current_pid < 0 {
        return Err(sched_errno(EINVAL));
    }
    if current_pid == normalized_pid {
        return Ok((current_thread, normalized_pid, false));
    }

    let (Some(find_thread), Some(thread_unlock)) = (find_fn, unlock_fn) else {
        return Err(sched_errno(EINVAL));
    };
    let thread = unsafe { find_thread(normalized_pid) };
    if thread == 0 {
        return Err(sched_errno(ESRCH));
    }
    unsafe { thread_unlock(thread) };
    Ok((thread, normalized_pid, true))
}

#[no_mangle]
pub unsafe extern "C" fn sched_setparam_body_result(
    pid: CInt,
    uparam_addr: CULong,
    current_thread: usize,
    param_addr: usize,
    param_size: SizeT,
    offsets: *const SchedSyscallOffsets,
    syscall_nr: CInt,
    find_fn: Option<SchedFindThreadFn>,
    unlock_fn: Option<SchedThreadUnlockFn>,
    copy_from_fn: Option<SchedCopyFromUserFn>,
    syscall2_fn: Option<SchedDoSyscall2Fn>,
    apply_fn: Option<SchedApplySchedulerFn>,
) -> CLong {
    if uparam_addr == 0 || pid < 0 || current_thread == 0 || param_addr == 0 || offsets.is_null() {
        return sched_errno(EINVAL);
    }
    let Some(copy_from) = copy_from_fn else {
        return sched_errno(EINVAL);
    };
    let Some(apply) = apply_fn else {
        return sched_errno(EINVAL);
    };
    let offsets = unsafe { &*offsets };
    let (mut thread, normalized_pid, other_thread) =
        match unsafe { sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn) } {
            Ok(selected) => selected,
            Err(ret) => return ret,
        };

    if other_thread {
        let Some(syscall2) = syscall2_fn else {
            return sched_errno(EINVAL);
        };
        let ret = unsafe { syscall2(syscall_nr, SCHED_CHECK_SAME_OWNER, normalized_pid as CULong) };
        if ret != 0 {
            return ret;
        }
    }

    let ret = unsafe { copy_from(param_addr as *mut u8, uparam_addr, param_size) };
    if ret < 0 {
        return sched_errno(EFAULT);
    }

    if other_thread {
        let (Some(find_thread), Some(thread_unlock)) = (find_fn, unlock_fn) else {
            return sched_errno(EINVAL);
        };
        thread = unsafe { find_thread(normalized_pid) };
        if thread == 0 {
            return sched_errno(ESRCH);
        }
        let policy = unsafe { sched_thread_policy(thread, offsets) };
        let ret = unsafe { apply(thread, policy, param_addr) as CLong };
        unsafe { thread_unlock(thread) };
        return ret;
    }

    let policy = unsafe { sched_thread_policy(thread, offsets) };
    unsafe { apply(thread, policy, param_addr) as CLong }
}

#[no_mangle]
pub unsafe extern "C" fn sched_getparam_body_result(
    pid: CInt,
    uparam_addr: CULong,
    current_thread: usize,
    param_size: SizeT,
    offsets: *const SchedSyscallOffsets,
    find_fn: Option<SchedFindThreadFn>,
    unlock_fn: Option<SchedThreadUnlockFn>,
    copy_to_fn: Option<SchedCopyToUserFn>,
) -> CLong {
    if uparam_addr == 0 || pid < 0 || current_thread == 0 || offsets.is_null() {
        return sched_errno(EINVAL);
    }
    let Some(copy_to) = copy_to_fn else {
        return sched_errno(EINVAL);
    };
    let offsets = unsafe { &*offsets };
    let (thread, _, _) =
        match unsafe { sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn) } {
            Ok(selected) => selected,
            Err(ret) => return ret,
        };
    let src = thread.wrapping_add(offsets.thread_sched_param_offset) as *const u8;
    if unsafe { copy_to(uparam_addr, src, param_size) } != 0 {
        return sched_errno(EFAULT);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn sched_setscheduler_body_result(
    pid: CInt,
    policy: CInt,
    uparam_addr: CULong,
    current_thread: usize,
    param_addr: usize,
    param_size: SizeT,
    offsets: *const SchedSyscallOffsets,
    syscall_nr: CInt,
    find_fn: Option<SchedFindThreadFn>,
    unlock_fn: Option<SchedThreadUnlockFn>,
    copy_from_fn: Option<SchedCopyFromUserFn>,
    syscall2_fn: Option<SchedDoSyscall2Fn>,
    apply_fn: Option<SchedApplySchedulerFn>,
) -> CLong {
    if uparam_addr == 0 || pid < 0 || current_thread == 0 || param_addr == 0 || offsets.is_null() {
        return sched_errno(EINVAL);
    }
    if sched_policy_is_valid(policy) == 0 {
        return sched_errno(EINVAL);
    }

    let Some(syscall2) = syscall2_fn else {
        return sched_errno(EINVAL);
    };
    if sched_policy_needs_root(policy) != 0 {
        let ret = unsafe { syscall2(syscall_nr, SCHED_CHECK_ROOT, 0) };
        if ret != 0 {
            return ret;
        }
    }

    let Some(copy_from) = copy_from_fn else {
        return sched_errno(EINVAL);
    };
    let Some(apply) = apply_fn else {
        return sched_errno(EINVAL);
    };
    let ret = unsafe { copy_from(param_addr as *mut u8, uparam_addr, param_size) };
    if ret < 0 {
        return sched_errno(EFAULT);
    }

    let offsets = unsafe { &*offsets };
    let (thread, normalized_pid, other_thread) =
        match unsafe { sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn) } {
            Ok(selected) => selected,
            Err(ret) => return ret,
        };
    if other_thread {
        let ret = unsafe { syscall2(syscall_nr, SCHED_CHECK_SAME_OWNER, normalized_pid as CULong) };
        if ret != 0 {
            return ret;
        }
    }

    unsafe { apply(thread, policy, param_addr) as CLong }
}

#[no_mangle]
pub unsafe extern "C" fn sched_getscheduler_body_result(
    pid: CInt,
    current_thread: usize,
    offsets: *const SchedSyscallOffsets,
    find_fn: Option<SchedFindThreadFn>,
    unlock_fn: Option<SchedThreadUnlockFn>,
) -> CLong {
    if pid < 0 || current_thread == 0 || offsets.is_null() {
        return sched_errno(EINVAL);
    }
    let offsets = unsafe { &*offsets };
    let (thread, _, _) =
        match unsafe { sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn) } {
            Ok(selected) => selected,
            Err(ret) => return ret,
        };
    unsafe { sched_thread_policy(thread, offsets) as CLong }
}

#[no_mangle]
pub unsafe extern "C" fn sched_rr_get_interval_body_result(
    pid: CInt,
    utime_addr: CULong,
    current_thread: usize,
    offsets: *const SchedSyscallOffsets,
    find_fn: Option<SchedFindThreadFn>,
    unlock_fn: Option<SchedThreadUnlockFn>,
    copy_to_fn: Option<SchedCopyToUserFn>,
) -> CLong {
    if pid < 0 || current_thread == 0 || offsets.is_null() {
        return sched_errno(EINVAL);
    }
    let Some(copy_to) = copy_to_fn else {
        return sched_errno(EINVAL);
    };
    let offsets = unsafe { &*offsets };
    let (thread, _, _) =
        match unsafe { sched_select_thread(pid, current_thread, offsets, find_fn, unlock_fn) } {
            Ok(selected) => selected,
            Err(ret) => return ret,
        };
    let policy = unsafe { sched_thread_policy(thread, offsets) };
    let time = TimeSpec {
        tv_sec: 0,
        tv_nsec: sched_rr_interval_nsec(policy),
    };
    if unsafe {
        copy_to(
            utime_addr,
            (&time as *const TimeSpec).cast::<u8>(),
            core::mem::size_of::<TimeSpec>(),
        )
    } != 0
    {
        return sched_errno(EFAULT);
    }
    0
}

unsafe fn sched_affinity_select_thread(
    tid: CInt,
    current_thread: usize,
    offsets: &SchedSyscallOffsets,
    find_fn: Option<SchedFindThreadFn>,
    unlock_fn: Option<SchedThreadUnlockFn>,
    hold_fn: Option<SchedHoldThreadFn>,
) -> Result<usize, CLong> {
    let Some(hold) = hold_fn else {
        return Err(sched_errno(EINVAL));
    };
    if tid == 0 {
        unsafe {
            hold(current_thread);
        }
        return Ok(current_thread);
    }

    let (Some(find_thread), Some(thread_unlock)) = (find_fn, unlock_fn) else {
        return Err(sched_errno(EINVAL));
    };
    let thread = unsafe { find_thread(tid) };
    if thread == 0 {
        return Err(sched_errno(ESRCH));
    }

    let current_proc = unsafe { sched_thread_proc(current_thread, offsets) };
    let target_proc = unsafe { sched_thread_proc(thread, offsets) };
    if current_proc == 0 || target_proc == 0 {
        unsafe {
            thread_unlock(thread);
        }
        return Err(sched_errno(EINVAL));
    }
    let permission = sched_affinity_permission_result(
        unsafe { sched_proc_euid(current_proc, offsets) },
        unsafe { sched_proc_ruid(target_proc, offsets) },
        unsafe { sched_proc_euid(target_proc, offsets) },
    );
    if permission != 0 {
        unsafe {
            thread_unlock(thread);
        }
        return Err(permission as CLong);
    }

    unsafe {
        hold(thread);
        thread_unlock(thread);
    }
    Ok(thread)
}

#[no_mangle]
pub unsafe extern "C" fn sched_setaffinity_body_result(
    tid: CInt,
    len: SizeT,
    u_cpu_set_addr: CULong,
    current_thread: usize,
    k_cpu_set_addr: usize,
    cpu_set_addr: usize,
    cpuset_size: SizeT,
    num_processors: CInt,
    offsets: *const SchedSyscallOffsets,
    find_fn: Option<SchedFindThreadFn>,
    unlock_fn: Option<SchedThreadUnlockFn>,
    hold_fn: Option<SchedHoldThreadFn>,
    release_fn: Option<SchedReleaseThreadFn>,
    copy_from_fn: Option<SchedCopyFromUserFn>,
    migrate_fn: Option<SchedRequestMigrateFn>,
) -> CLong {
    if u_cpu_set_addr == 0 {
        return sched_errno(EFAULT);
    }
    if current_thread == 0
        || k_cpu_set_addr == 0
        || cpu_set_addr == 0
        || cpuset_size == 0
        || offsets.is_null()
        || num_processors < 0
    {
        return sched_errno(EINVAL);
    }
    let Some(copy_from) = copy_from_fn else {
        return sched_errno(EINVAL);
    };
    let Some(release) = release_fn else {
        return sched_errno(EINVAL);
    };
    let Some(migrate) = migrate_fn else {
        return sched_errno(EINVAL);
    };

    if cpuset_size > len {
        unsafe {
            sched_cpuset_zero(k_cpu_set_addr, cpuset_size);
        }
    }
    let copy_len = sched_affinity_copy_len(len, cpuset_size);
    if unsafe { copy_from(k_cpu_set_addr as *mut u8, u_cpu_set_addr, copy_len) } != 0 {
        return sched_errno(EFAULT);
    }

    let offsets = unsafe { &*offsets };
    let thread = match unsafe {
        sched_affinity_select_thread(tid, current_thread, offsets, find_fn, unlock_fn, hold_fn)
    } {
        Ok(thread) => thread,
        Err(ret) => return ret,
    };
    let target_proc = unsafe { sched_thread_proc(thread, offsets) };
    if target_proc == 0 {
        unsafe {
            release(thread);
        }
        return sched_errno(EINVAL);
    }

    unsafe {
        sched_cpuset_zero(cpu_set_addr, cpuset_size);
    }
    let proc_cpu_set_addr = target_proc.wrapping_add(offsets.proc_cpu_set_offset);
    let mut empty = true;
    for cpu in 0..num_processors {
        if unsafe { sched_cpuset_is_set(k_cpu_set_addr, cpuset_size, cpu) }
            && unsafe { sched_cpuset_is_set(proc_cpu_set_addr, cpuset_size, cpu) }
        {
            unsafe {
                sched_cpuset_set(cpu_set_addr, cpuset_size, cpu);
            }
            empty = false;
        }
    }
    if empty {
        unsafe {
            release(thread);
        }
        return sched_errno(EINVAL);
    }

    let thread_cpu_set_addr = thread.wrapping_add(offsets.thread_cpu_set_offset);
    unsafe {
        sched_cpuset_copy(thread_cpu_set_addr, cpu_set_addr, cpuset_size);
    }
    let cpu_id = unsafe { sched_thread_cpu_id(thread, offsets) };
    if !unsafe { sched_cpuset_is_set(thread_cpu_set_addr, cpuset_size, cpu_id) } {
        unsafe {
            migrate(cpu_id, thread);
        }
    }
    unsafe {
        release(thread);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn sched_getaffinity_body_result(
    tid: CInt,
    len: SizeT,
    u_cpu_set_addr: CULong,
    current_thread: usize,
    cpuset_size: SizeT,
    num_processors: CInt,
    offsets: *const SchedSyscallOffsets,
    find_fn: Option<SchedFindThreadFn>,
    unlock_fn: Option<SchedThreadUnlockFn>,
    hold_fn: Option<SchedHoldThreadFn>,
    release_fn: Option<SchedReleaseThreadFn>,
    copy_to_fn: Option<SchedCopyToUserFn>,
) -> CLong {
    if current_thread == 0 || cpuset_size == 0 || offsets.is_null() || num_processors < 0 {
        return sched_errno(EINVAL);
    }
    let ret = sched_getaffinity_len_result(len, num_processors);
    if ret != 0 {
        return ret as CLong;
    }
    let Some(copy_to) = copy_to_fn else {
        return sched_errno(EINVAL);
    };
    let Some(release) = release_fn else {
        return sched_errno(EINVAL);
    };

    let copy_len = sched_affinity_copy_len(len, cpuset_size);
    let offsets = unsafe { &*offsets };
    let thread = match unsafe {
        sched_affinity_select_thread(tid, current_thread, offsets, find_fn, unlock_fn, hold_fn)
    } {
        Ok(thread) => thread,
        Err(ret) => return ret,
    };
    let src = thread.wrapping_add(offsets.thread_cpu_set_offset) as *const u8;
    let copy_ret = unsafe { copy_to(u_cpu_set_addr, src, copy_len) };
    unsafe {
        release(thread);
    }
    if copy_ret < 0 {
        sched_errno(EFAULT)
    } else {
        copy_len as CLong
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
pub unsafe extern "C" fn timer_init_timers_result(
    timers_lock_addr: usize,
    timers_head_addr: usize,
    spin_init_fn: Option<TimerSpinInitFn>,
) -> CInt {
    let Some(spin_init) = spin_init_fn else {
        return -EINVAL;
    };
    if timers_lock_addr == 0 || timers_head_addr == 0 {
        return -EINVAL;
    }

    unsafe {
        spin_init(timers_lock_addr);
        init_list_head_addr(timers_head_addr);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn timer_schedule_timeout_body_result(
    thread_addr: usize,
    cpu_local_addr: usize,
    mut timeout: u64,
    loop_timeout: u64,
    offsets: *const TimerRuntimeOffsets,
    rdtsc_fn: Option<TimerRdtscFn>,
    spin_lock_fn: Option<TimerSpinLockFn>,
    spin_unlock_fn: Option<TimerSpinUnlockFn>,
    set_status_fn: Option<TimerSetStatusFn>,
    schedule_fn: Option<TimerVoidFn>,
    zero_free_fn: Option<TimerVoidFn>,
    pause_fn: Option<TimerVoidFn>,
) -> u64 {
    if thread_addr == 0 || cpu_local_addr == 0 || offsets.is_null() || loop_timeout == 0 {
        return timeout;
    }
    let (
        Some(rdtsc),
        Some(spin_lock),
        Some(spin_unlock),
        Some(set_status),
        Some(schedule),
        Some(zero_free),
        Some(pause),
    ) = (
        rdtsc_fn,
        spin_lock_fn,
        spin_unlock_fn,
        set_status_fn,
        schedule_fn,
        zero_free_fn,
        pause_fn,
    )
    else {
        return timeout;
    };

    let offsets = unsafe { &*offsets };
    let thread_spin_lock_addr = thread_addr.wrapping_add(offsets.thread_spin_sleep_lock_offset);
    let thread_spin_sleep_addr = thread_addr.wrapping_add(offsets.thread_spin_sleep_offset);
    let thread_status_addr = thread_addr.wrapping_add(offsets.thread_status_offset);
    let runq_lock_addr = cpu_local_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    let runq_len_addr = cpu_local_addr.wrapping_add(offsets.cpu_runq_len_offset);

    loop {
        let t_s = unsafe { rdtsc() };
        let irqstate = unsafe { spin_lock(thread_spin_lock_addr) };

        if unsafe { read_volatile(thread_spin_sleep_addr as *const CInt) } == 0 {
            let t_e = unsafe { rdtsc() };
            timeout = timer_spin_sleep_remaining_result(timeout, t_e.wrapping_sub(t_s));
            unsafe {
                spin_unlock(thread_spin_lock_addr, irqstate);
            }
            break;
        }

        unsafe {
            spin_unlock(thread_spin_lock_addr, irqstate);
        }

        let irqstate = unsafe { spin_lock(runq_lock_addr) };
        let runq_len = unsafe { read_volatile(runq_len_addr as *const usize) };
        let need_schedule = timer_runq_should_schedule_result(runq_len as CInt) != 0;
        if need_schedule {
            unsafe {
                set_status(thread_status_addr, PS_RUNNING);
                spin_unlock(runq_lock_addr, irqstate);
                schedule();
            }
            continue;
        }
        unsafe {
            spin_unlock(runq_lock_addr, irqstate);
        }

        while unsafe { rdtsc().wrapping_sub(t_s) } < loop_timeout {
            unsafe {
                zero_free();
                pause();
            }
        }

        timeout = timer_after_spin_remaining_result(timeout, loop_timeout);
        if timeout == 0 {
            let irqstate = unsafe { spin_lock(thread_spin_lock_addr) };
            unsafe {
                write_volatile(thread_spin_sleep_addr as *mut CInt, 0);
                spin_unlock(thread_spin_lock_addr, irqstate);
            }
            break;
        }
    }

    timeout
}

#[no_mangle]
pub unsafe extern "C" fn timer_wake_tick_result(
    timers_lock_addr: usize,
    timers_head_addr: usize,
    loop_timeout: u64,
    offsets: *const TimerRuntimeOffsets,
    lock_fn: Option<TimerSpinLockFn>,
    unlock_fn: Option<TimerSpinUnlockFn>,
    wake_fn: Option<TimerWaitqWakeupFn>,
    log_fn: Option<TimerLogWakeFn>,
) -> CInt {
    if timers_lock_addr == 0 || timers_head_addr == 0 || offsets.is_null() || loop_timeout == 0 {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock), Some(wake)) = (lock_fn, unlock_fn, wake_fn) else {
        return -EINVAL;
    };

    let offsets = unsafe { &*offsets };
    let irqstate = unsafe { lock(timers_lock_addr) };
    let mut woken = 0;
    let mut entry = unsafe { list_next(timers_head_addr) };

    while entry != timers_head_addr {
        let next = unsafe { list_next(entry) };
        let timer = entry.wrapping_sub(offsets.timer_list_offset);
        let timeout_addr = timer.wrapping_add(offsets.timer_timeout_offset);
        let timeout = unsafe { read_volatile(timeout_addr as *const u64) };
        let next_timeout = timer_after_tick_remaining_result(timeout, loop_timeout);

        unsafe {
            write_volatile(timeout_addr as *mut u64, next_timeout);
        }
        if next_timeout == 0 {
            let thread_addr = unsafe {
                read_volatile(timer.wrapping_add(offsets.timer_thread_offset) as *const usize)
            };
            unsafe {
                list_del_addr(entry);
                if let Some(log) = log_fn {
                    log(timer, thread_addr);
                }
                wake(timer.wrapping_add(offsets.timer_waitq_offset));
            }
            woken += 1;
        }

        entry = next;
    }

    unsafe {
        unlock(timers_lock_addr, irqstate);
    }
    woken
}

#[no_mangle]
pub unsafe extern "C" fn timer_wake_loop_body_result(
    timers_lock_addr: usize,
    timers_head_addr: usize,
    loop_timeout: u64,
    max_ticks: CInt,
    offsets: *const TimerRuntimeOffsets,
    rdtsc_fn: Option<TimerRdtscFn>,
    pause_fn: Option<TimerVoidFn>,
    lock_fn: Option<TimerSpinLockFn>,
    unlock_fn: Option<TimerSpinUnlockFn>,
    wake_fn: Option<TimerWaitqWakeupFn>,
    log_fn: Option<TimerLogWakeFn>,
) -> CInt {
    if max_ticks < 0 {
        return -EINVAL;
    }
    let (Some(rdtsc), Some(pause)) = (rdtsc_fn, pause_fn) else {
        return -EINVAL;
    };

    let mut ticks: CInt = 0;
    loop {
        let loop_start = unsafe { rdtsc() };
        while unsafe { rdtsc() } < loop_start.wrapping_add(loop_timeout) {
            unsafe {
                pause();
            }
        }

        unsafe {
            timer_wake_tick_result(
                timers_lock_addr,
                timers_head_addr,
                loop_timeout,
                offsets,
                lock_fn,
                unlock_fn,
                wake_fn,
                log_fn,
            );
        }
        ticks += 1;
        if max_ticks > 0 && ticks >= max_ticks {
            return ticks;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn timer_set_timer_body_result(
    cpu_local_addr: usize,
    time_sharing_enabled: CInt,
    runq_locked: CInt,
    offsets: *const TimerRuntimeOffsets,
    lock_fn: Option<TimerSpinLockFn>,
    unlock_fn: Option<TimerSpinUnlockFn>,
    enable_fn: Option<TimerLapicEnableFn>,
    disable_fn: Option<TimerLapicDisableFn>,
) -> CInt {
    if time_sharing_enabled == 0 {
        return 0;
    }
    if cpu_local_addr == 0 || offsets.is_null() {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock), Some(enable), Some(disable)) =
        (lock_fn, unlock_fn, enable_fn, disable_fn)
    else {
        return -EINVAL;
    };

    let offsets = unsafe { &*offsets };
    let runq_lock_addr = cpu_local_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    let irqstate = if runq_locked == 0 {
        unsafe { lock(runq_lock_addr) }
    } else {
        0
    };

    let runq_head = cpu_local_addr.wrapping_add(offsets.cpu_runq_offset);
    let mut num_running: CInt = 0;
    let mut entry = unsafe { list_next(runq_head) };
    while entry != runq_head {
        let thread = entry.wrapping_sub(offsets.thread_sched_list_offset);
        let status = unsafe {
            read_volatile(thread.wrapping_add(offsets.thread_status_offset) as *const CInt)
        };
        let spin_sleep = unsafe {
            read_volatile(thread.wrapping_add(offsets.thread_spin_sleep_offset) as *const CInt)
        };
        if status == PS_RUNNING || spin_sleep != 0 {
            num_running += 1;
        }
        entry = unsafe { list_next(entry) };
    }

    let current_thread = unsafe {
        read_volatile(cpu_local_addr.wrapping_add(offsets.cpu_current_offset) as *const usize)
    };
    let current_itimer_enabled = if current_thread == 0 {
        0
    } else {
        unsafe {
            read_volatile(
                current_thread.wrapping_add(offsets.thread_itimer_enabled_offset) as *const CInt,
            )
        }
    };
    let backlog_not_empty =
        unsafe { !list_empty_addr(cpu_local_addr.wrapping_add(offsets.cpu_backlog_list_offset)) };
    let should_enable = num_running > 1 || current_itimer_enabled != 0 || backlog_not_empty;
    let timer_enabled_addr = cpu_local_addr.wrapping_add(offsets.cpu_timer_enabled_offset);
    let timer_enabled = unsafe { read_volatile(timer_enabled_addr as *const CInt) };

    if should_enable {
        if timer_enabled == 0 {
            unsafe {
                enable(1_000_000);
                write_volatile(timer_enabled_addr as *mut CInt, 1);
            }
        }
    } else if timer_enabled != 0 {
        unsafe {
            disable();
            write_volatile(timer_enabled_addr as *mut CInt, 0);
        }
    }

    if runq_locked == 0 {
        unsafe {
            unlock(runq_lock_addr, irqstate);
        }
    }

    num_running
}

#[no_mangle]
pub unsafe extern "C" fn sched_request_migrate_body_result(
    target_cpu_id: CInt,
    target_cpu_addr: usize,
    req_addr: usize,
    wait_entry_addr: usize,
    thread_addr: usize,
    current_cpu_id: CInt,
    wait_status: CInt,
    need_resched_flag: u32,
    need_migrate_flag: u32,
    running_status: CInt,
    vector_key: CInt,
    offsets: *const SchedMigrateOffsets,
    lock_fn: Option<SchedMigrateSpinLockFn>,
    unlock_fn: Option<SchedMigrateSpinUnlockFn>,
    noirq_lock_fn: Option<SchedMigrateNoirqLockFn>,
    noirq_unlock_fn: Option<SchedMigrateNoirqUnlockFn>,
    waitq_init_fn: Option<SchedMigrateWaitqInitFn>,
    waitq_prepare_fn: Option<SchedMigrateWaitqPrepareFn>,
    waitq_finish_fn: Option<SchedMigrateWaitqFinishFn>,
    vector_fn: Option<SchedMigrateVectorFn>,
    interrupt_fn: Option<SchedMigrateInterruptFn>,
    schedule_fn: Option<SchedMigrateVoidFn>,
    log_fn: Option<SchedMigrateLogFn>,
) -> CInt {
    if target_cpu_addr == 0
        || req_addr == 0
        || wait_entry_addr == 0
        || thread_addr == 0
        || offsets.is_null()
    {
        return -EINVAL;
    }
    let (
        Some(lock),
        Some(unlock),
        Some(noirq_lock),
        Some(noirq_unlock),
        Some(waitq_init),
        Some(waitq_prepare),
        Some(waitq_finish),
        Some(schedule),
    ) = (
        lock_fn,
        unlock_fn,
        noirq_lock_fn,
        noirq_unlock_fn,
        waitq_init_fn,
        waitq_prepare_fn,
        waitq_finish_fn,
        schedule_fn,
    )
    else {
        return -EINVAL;
    };
    if target_cpu_id != current_cpu_id && (vector_fn.is_none() || interrupt_fn.is_none()) {
        return -EINVAL;
    }

    let offsets = unsafe { &*offsets };
    unsafe {
        write_volatile(
            req_addr.wrapping_add(offsets.req_thread_offset) as *mut usize,
            thread_addr,
        );
    }

    let migq_lock_addr = target_cpu_addr.wrapping_add(offsets.cpu_migq_lock_offset);
    let runq_lock_addr = target_cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    let waitq_addr = req_addr.wrapping_add(offsets.req_wq_offset);
    let req_list_addr = req_addr.wrapping_add(offsets.req_list_offset);
    let migq_addr = target_cpu_addr.wrapping_add(offsets.cpu_migq_offset);

    let irqstate = unsafe { lock(migq_lock_addr) };
    unsafe {
        waitq_init(waitq_addr);
        waitq_prepare(waitq_addr, wait_entry_addr, wait_status);
        list_add_tail_addr(req_list_addr, migq_addr);

        noirq_lock(runq_lock_addr);
        let flags_addr = target_cpu_addr.wrapping_add(offsets.cpu_flags_offset);
        let flags = read_volatile(flags_addr as *const u32);
        write_volatile(
            flags_addr as *mut u32,
            flags | need_resched_flag | need_migrate_flag,
        );
        write_volatile(
            target_cpu_addr.wrapping_add(offsets.cpu_status_offset) as *mut CInt,
            running_status,
        );
        noirq_unlock(runq_lock_addr);

        if target_cpu_id != current_cpu_id {
            let thread_cpu_id = read_volatile(
                thread_addr.wrapping_add(offsets.thread_cpu_id_offset) as *const CInt,
            );
            let Some(vector) = vector_fn else {
                return -EINVAL;
            };
            let Some(interrupt) = interrupt_fn else {
                return -EINVAL;
            };
            interrupt(thread_cpu_id, vector(vector_key));
        }

        if let Some(log) = log_fn {
            let tid =
                read_volatile(thread_addr.wrapping_add(offsets.thread_tid_offset) as *const CInt);
            log(thread_addr, tid, target_cpu_id);
        }

        unlock(migq_lock_addr, irqstate);
        schedule();
        waitq_finish(waitq_addr, wait_entry_addr);
    }

    1
}

#[inline(always)]
unsafe fn cpu_set_word(set_addr: usize, cpu: CInt, cpu_set_bits: CInt) -> Option<(usize, usize)> {
    if set_addr == 0 || cpu < 0 || cpu_set_bits <= 0 || cpu >= cpu_set_bits {
        return None;
    }
    let cpu = cpu as usize;
    let bits_per_word = core::mem::size_of::<usize>() * 8;
    let word = cpu / bits_per_word;
    let bit = cpu % bits_per_word;
    Some((
        set_addr.wrapping_add(word * core::mem::size_of::<usize>()),
        bit,
    ))
}

#[inline(always)]
unsafe fn cpu_set_isset_addr(set_addr: usize, cpu: CInt, cpu_set_bits: CInt) -> bool {
    let Some((word_addr, bit)) = (unsafe { cpu_set_word(set_addr, cpu, cpu_set_bits) }) else {
        return false;
    };
    let word = unsafe { read_volatile(word_addr as *const usize) };
    (word & (1usize << bit)) != 0
}

#[inline(always)]
unsafe fn cpu_set_bit_addr(set_addr: usize, cpu: CInt, cpu_set_bits: CInt) -> bool {
    let Some((word_addr, bit)) = (unsafe { cpu_set_word(set_addr, cpu, cpu_set_bits) }) else {
        return false;
    };
    unsafe {
        let word = read_volatile(word_addr as *const usize);
        write_volatile(word_addr as *mut usize, word | (1usize << bit));
    }
    true
}

#[inline(always)]
unsafe fn cpu_clear_bit_addr(set_addr: usize, cpu: CInt, cpu_set_bits: CInt) -> bool {
    let Some((word_addr, bit)) = (unsafe { cpu_set_word(set_addr, cpu, cpu_set_bits) }) else {
        return false;
    };
    unsafe {
        let word = read_volatile(word_addr as *const usize);
        write_volatile(word_addr as *mut usize, word & !(1usize << bit));
    }
    true
}

#[inline(always)]
unsafe fn sched_double_rq_lock(
    current_cpu_addr: usize,
    target_cpu_addr: usize,
    offsets: &SchedDoMigrateOffsets,
    lock: SchedMigrateSpinLockFn,
    noirq_lock: SchedMigrateNoirqLockFn,
) -> CULong {
    let current_lock = current_cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    let target_lock = target_cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);

    if current_cpu_addr < target_cpu_addr {
        let irqstate = unsafe { lock(current_lock) };
        unsafe {
            noirq_lock(target_lock);
        }
        irqstate
    } else {
        let irqstate = unsafe { lock(target_lock) };
        unsafe {
            noirq_lock(current_lock);
        }
        irqstate
    }
}

#[inline(always)]
unsafe fn sched_double_rq_unlock(
    current_cpu_addr: usize,
    target_cpu_addr: usize,
    irqstate: CULong,
    offsets: &SchedDoMigrateOffsets,
    unlock: SchedMigrateSpinUnlockFn,
    noirq_unlock: SchedMigrateNoirqUnlockFn,
) {
    unsafe {
        noirq_unlock(current_cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset));
        unlock(
            target_cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset),
            irqstate,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn sched_do_migrate_body_result(
    current_cpu_id: CInt,
    current_cpu_addr: usize,
    cpu_set_bits: CInt,
    need_resched_flag: u32,
    vector_key: CInt,
    offsets: *const SchedDoMigrateOffsets,
    lock_fn: Option<SchedMigrateSpinLockFn>,
    unlock_fn: Option<SchedMigrateSpinUnlockFn>,
    noirq_lock_fn: Option<SchedMigrateNoirqLockFn>,
    noirq_unlock_fn: Option<SchedMigrateNoirqUnlockFn>,
    cpu_local_fn: Option<SchedMigrateCpuLocalFn>,
    waitq_wakeup_fn: Option<SchedMigrateWaitqWakeupFn>,
    vector_fn: Option<SchedMigrateVectorFn>,
    interrupt_fn: Option<SchedMigrateInterruptFn>,
    log_fn: Option<SchedDoMigrateLogFn>,
) -> CInt {
    if current_cpu_addr == 0 || cpu_set_bits <= 0 || offsets.is_null() {
        return -EINVAL;
    }
    let (
        Some(lock),
        Some(unlock),
        Some(noirq_lock),
        Some(noirq_unlock),
        Some(cpu_local),
        Some(waitq_wakeup),
        Some(vector),
        Some(interrupt),
    ) = (
        lock_fn,
        unlock_fn,
        noirq_lock_fn,
        noirq_unlock_fn,
        cpu_local_fn,
        waitq_wakeup_fn,
        vector_fn,
        interrupt_fn,
    )
    else {
        return -EINVAL;
    };

    let offsets = unsafe { &*offsets };
    let migq_lock_addr = current_cpu_addr.wrapping_add(offsets.cpu_migq_lock_offset);
    let migq_head = current_cpu_addr.wrapping_add(offsets.cpu_migq_offset);
    let mut irqstate = unsafe { lock(migq_lock_addr) };
    let mut processed: CInt = 0;
    let mut entry = unsafe { list_next(migq_head) };

    while entry != migq_head {
        let next = unsafe { list_next(entry) };
        let req_addr = entry.wrapping_sub(offsets.req_list_offset);
        let thread_addr = unsafe {
            read_volatile(req_addr.wrapping_add(offsets.req_thread_offset) as *const usize)
        };

        processed = processed.wrapping_add(1);
        unsafe {
            list_detach_poison_addr(entry);
        }

        if thread_addr == 0 {
            unsafe {
                waitq_wakeup(req_addr.wrapping_add(offsets.req_wq_offset));
            }
            entry = next;
            continue;
        }

        let thread_cpu_id = unsafe {
            read_volatile(thread_addr.wrapping_add(offsets.thread_cpu_id_offset) as *const CInt)
        };
        if thread_cpu_id != current_cpu_id {
            unsafe {
                waitq_wakeup(req_addr.wrapping_add(offsets.req_wq_offset));
            }
            entry = next;
            continue;
        }

        let thread_cpu_set = thread_addr.wrapping_add(offsets.thread_cpu_set_offset);
        if unsafe { cpu_set_isset_addr(thread_cpu_set, current_cpu_id, cpu_set_bits) } {
            unsafe {
                waitq_wakeup(req_addr.wrapping_add(offsets.req_wq_offset));
            }
            entry = next;
            continue;
        }

        let mut target_cpu_id = 0;
        while target_cpu_id < cpu_set_bits {
            if unsafe { cpu_set_isset_addr(thread_cpu_set, target_cpu_id, cpu_set_bits) } {
                break;
            }
            target_cpu_id += 1;
        }
        if target_cpu_id == cpu_set_bits {
            unsafe {
                waitq_wakeup(req_addr.wrapping_add(offsets.req_wq_offset));
            }
            entry = next;
            continue;
        }

        let target_cpu_addr = unsafe { cpu_local(target_cpu_id) };
        if target_cpu_addr == 0 {
            unsafe {
                waitq_wakeup(req_addr.wrapping_add(offsets.req_wq_offset));
            }
            entry = next;
            continue;
        }

        irqstate = unsafe {
            sched_double_rq_lock(current_cpu_addr, target_cpu_addr, offsets, lock, noirq_lock)
        };
        unsafe {
            list_detach_counted_addr(
                thread_addr.wrapping_add(offsets.thread_sched_list_offset),
                current_cpu_addr.wrapping_add(offsets.cpu_runq_len_offset),
            );
        }
        let old_cpu_id = unsafe {
            read_volatile(thread_addr.wrapping_add(offsets.thread_cpu_id_offset) as *const CInt)
        };
        unsafe {
            write_volatile(
                thread_addr.wrapping_add(offsets.thread_cpu_id_offset) as *mut CInt,
                target_cpu_id,
            );
            list_add_tail_counted_addr(
                thread_addr.wrapping_add(offsets.thread_sched_list_offset),
                target_cpu_addr.wrapping_add(offsets.cpu_runq_offset),
                target_cpu_addr.wrapping_add(offsets.cpu_runq_len_offset),
            );
        }

        let moving_vm = unsafe {
            read_volatile(thread_addr.wrapping_add(offsets.thread_vm_offset) as *const usize)
        };
        let mut clear_old_cpu = true;
        let runq_head = current_cpu_addr.wrapping_add(offsets.cpu_runq_offset);
        let mut runq_entry = unsafe { list_next(runq_head) };
        while runq_entry != runq_head {
            let candidate = runq_entry.wrapping_sub(offsets.thread_sched_list_offset);
            let candidate_vm = unsafe {
                read_volatile(candidate.wrapping_add(offsets.thread_vm_offset) as *const usize)
            };
            if candidate_vm != 0 && candidate_vm == moving_vm {
                clear_old_cpu = false;
                break;
            }
            runq_entry = unsafe { list_next(runq_entry) };
        }

        if moving_vm != 0 {
            let address_space = unsafe {
                read_volatile(
                    moving_vm.wrapping_add(offsets.vm_address_space_offset) as *const usize
                )
            };
            if address_space != 0 {
                let cpu_set_addr = address_space.wrapping_add(offsets.address_space_cpu_set_offset);
                let cpu_set_lock_addr =
                    address_space.wrapping_add(offsets.address_space_cpu_set_lock_offset);
                let cpu_set_irqstate = unsafe { lock(cpu_set_lock_addr) };
                unsafe {
                    if clear_old_cpu {
                        cpu_clear_bit_addr(cpu_set_addr, old_cpu_id, cpu_set_bits);
                    }
                    cpu_set_bit_addr(cpu_set_addr, target_cpu_id, cpu_set_bits);
                    unlock(cpu_set_lock_addr, cpu_set_irqstate);
                }
            }
        }

        if let Some(log) = log_fn {
            let tid = unsafe {
                read_volatile(thread_addr.wrapping_add(offsets.thread_tid_offset) as *const CInt)
            };
            unsafe {
                log(thread_addr, tid, old_cpu_id, target_cpu_id);
            }
        }

        unsafe {
            let flags_addr = target_cpu_addr.wrapping_add(offsets.cpu_flags_offset);
            let flags = read_volatile(flags_addr as *const u32);
            write_volatile(flags_addr as *mut u32, flags | need_resched_flag);
            interrupt(target_cpu_id, vector(vector_key));
            waitq_wakeup(req_addr.wrapping_add(offsets.req_wq_offset));
            sched_double_rq_unlock(
                current_cpu_addr,
                target_cpu_addr,
                irqstate,
                offsets,
                unlock,
                noirq_unlock,
            );
        }

        entry = next;
    }

    unsafe {
        unlock(migq_lock_addr, irqstate);
    }
    processed
}

#[no_mangle]
pub unsafe extern "C" fn sched_do_migrate_public() {
    let current_cpu_id = unsafe { ihk_mc_get_processor_id() };
    let current_cpu_addr = unsafe { process_sched_cpu_local_bridge(current_cpu_id) };
    let offsets = SchedDoMigrateOffsets {
        req_list_offset: offset_of!(SchedMigrateRequest, list),
        req_thread_offset: offset_of!(SchedMigrateRequest, thread),
        req_wq_offset: offset_of!(SchedMigrateRequest, wq),
        thread_cpu_id_offset: offset_of!(Thread, cpu_id),
        thread_tid_offset: offset_of!(Thread, tid),
        thread_cpu_set_offset: offset_of!(Thread, cpu_set),
        thread_sched_list_offset: offset_of!(Thread, sched_list),
        thread_vm_offset: offset_of!(Thread, vm),
        vm_address_space_offset: offset_of!(ProcessVm, address_space),
        address_space_cpu_set_offset: offset_of!(AddressSpace, cpu_set),
        address_space_cpu_set_lock_offset: offset_of!(AddressSpace, cpu_set_lock),
        cpu_migq_lock_offset: offset_of!(CpuLocalVar, migq_lock),
        cpu_migq_offset: offset_of!(CpuLocalVar, migq),
        cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
        cpu_runq_offset: offset_of!(CpuLocalVar, runq),
        cpu_runq_len_offset: offset_of!(CpuLocalVar, runq_len),
        cpu_flags_offset: offset_of!(CpuLocalVar, flags),
    };

    let _ = unsafe {
        sched_do_migrate_body_result(
            current_cpu_id,
            current_cpu_addr,
            CPU_SET_MAX_CPUS as CInt,
            CPU_FLAG_NEED_RESCHED,
            IHK_GV_IKC,
            &offsets,
            Some(sched_process_spin_lock_bridge),
            Some(sched_process_spin_unlock_bridge),
            Some(sched_process_noirq_lock_bridge),
            Some(sched_process_noirq_unlock_bridge),
            Some(process_sched_cpu_local_bridge),
            Some(process_sched_waitq_wakeup_bridge),
            Some(process_sched_vector_bridge),
            Some(process_sched_interrupt_bridge),
            Some(process_sched_do_migrate_log_bridge),
        )
    };
}

#[no_mangle]
pub unsafe extern "C" fn sched_release_cpuid_body_result(
    _cpuid: CInt,
    cpu_addr: usize,
    reservation_lock_addr: usize,
    idle_status: CInt,
    offsets: *const SchedRunqueueOffsets,
    lock_fn: Option<SchedMigrateSpinLockFn>,
    unlock_fn: Option<SchedMigrateSpinUnlockFn>,
    noirq_lock_fn: Option<SchedMigrateNoirqLockFn>,
    noirq_unlock_fn: Option<SchedMigrateNoirqUnlockFn>,
) -> CInt {
    if cpu_addr == 0 || reservation_lock_addr == 0 || offsets.is_null() {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock), Some(noirq_lock), Some(noirq_unlock)) =
        (lock_fn, unlock_fn, noirq_lock_fn, noirq_unlock_fn)
    else {
        return -EINVAL;
    };

    let offsets = unsafe { &*offsets };
    let irqstate = unsafe { lock(reservation_lock_addr) };
    let runq_lock_addr = cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    unsafe {
        noirq_lock(runq_lock_addr);
    }

    let runq_len = unsafe {
        read_volatile(cpu_addr.wrapping_add(offsets.cpu_runq_len_offset) as *const usize)
    };
    if runq_len == 0 {
        unsafe {
            write_volatile(
                cpu_addr.wrapping_add(offsets.cpu_status_offset) as *mut CInt,
                idle_status,
            );
        }
    }
    let reserved_addr = cpu_addr.wrapping_add(offsets.cpu_runq_reserved_offset);
    let reserved = unsafe { read_volatile(reserved_addr as *const usize) };
    unsafe {
        write_volatile(reserved_addr as *mut usize, reserved.wrapping_sub(1));
        noirq_unlock(runq_lock_addr);
        unlock(reservation_lock_addr, irqstate);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn release_cpuid(cpuid: CInt) {
    let cpu_addr = unsafe { process_sched_cpu_local_bridge(cpuid) };
    let reservation_lock_addr =
        core::ptr::addr_of_mut!(runq_reservation_lock) as *mut IhkSpinlock as usize;
    let offsets = sched_runqueue_offsets();
    let _ = unsafe {
        sched_release_cpuid_body_result(
            cpuid,
            cpu_addr,
            reservation_lock_addr,
            CPU_STATUS_IDLE,
            &offsets,
            Some(sched_process_spin_lock_bridge),
            Some(sched_process_spin_unlock_bridge),
            Some(sched_process_noirq_lock_bridge),
            Some(sched_process_noirq_unlock_bridge),
        )
    };
}

#[no_mangle]
pub unsafe extern "C" fn sched_check_need_resched_body_result(
    cpu_addr: usize,
    need_resched_flag: u32,
    need_migrate_flag: u32,
    offsets: *const SchedRunqueueOffsets,
    lock_fn: Option<SchedMigrateSpinLockFn>,
    unlock_fn: Option<SchedMigrateSpinUnlockFn>,
    schedule_fn: Option<SchedMigrateVoidFn>,
    log_fn: Option<SchedRunqLogFn>,
) -> CInt {
    if cpu_addr == 0 || offsets.is_null() {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock), Some(schedule)) = (lock_fn, unlock_fn, schedule_fn) else {
        return -EINVAL;
    };

    let offsets = unsafe { &*offsets };
    let runq_lock_addr = cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    let irqstate = unsafe { lock(runq_lock_addr) };
    let flags_addr = cpu_addr.wrapping_add(offsets.cpu_flags_offset);
    let mut flags = unsafe { read_volatile(flags_addr as *const u32) };
    if (flags & need_resched_flag) == 0 {
        unsafe {
            unlock(runq_lock_addr, irqstate);
        }
        return 0;
    }

    let in_interrupt = unsafe {
        read_volatile(cpu_addr.wrapping_add(offsets.cpu_in_interrupt_offset) as *const CInt)
    };
    if in_interrupt != 0 && (flags & need_migrate_flag) != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(SCHED_RUNQ_LOG_NO_MIGRATION_IRQ, cpu_addr, 0, 0, 0);
            }
        }
        unsafe {
            unlock(runq_lock_addr, irqstate);
        }
        return 0;
    }

    flags &= !need_resched_flag;
    unsafe {
        write_volatile(flags_addr as *mut u32, flags);
        unlock(runq_lock_addr, irqstate);
        schedule();
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn check_need_resched() {
    let cpu_id = unsafe { ihk_mc_get_processor_id() };
    let cpu_addr = unsafe { process_sched_cpu_local_bridge(cpu_id) };
    let offsets = sched_runqueue_offsets();
    let _ = unsafe {
        sched_check_need_resched_body_result(
            cpu_addr,
            CPU_FLAG_NEED_RESCHED,
            CPU_FLAG_NEED_MIGRATE,
            &offsets,
            Some(sched_process_spin_lock_bridge),
            Some(sched_process_spin_unlock_bridge),
            Some(process_sched_schedule_bridge),
            Some(process_sched_runq_log_bridge),
        )
    };
}

#[no_mangle]
pub unsafe extern "C" fn sched_runq_add_thread_locked_result(
    thread_addr: usize,
    cpu_addr: usize,
    cpu_id: CInt,
    need_resched_flag: u32,
    running_status: CInt,
    offsets: *const SchedRunqueueOffsets,
    log_fn: Option<SchedRunqLogFn>,
) -> CInt {
    if thread_addr == 0 || cpu_addr == 0 || offsets.is_null() {
        return -EINVAL;
    }

    let offsets = unsafe { &*offsets };
    unsafe {
        list_add_tail_counted_addr(
            thread_addr.wrapping_add(offsets.thread_sched_list_offset),
            cpu_addr.wrapping_add(offsets.cpu_runq_offset),
            cpu_addr.wrapping_add(offsets.cpu_runq_len_offset),
        );
        let flags_addr = cpu_addr.wrapping_add(offsets.cpu_flags_offset);
        let flags = read_volatile(flags_addr as *const u32);
        write_volatile(flags_addr as *mut u32, flags | need_resched_flag);
        write_volatile(
            thread_addr.wrapping_add(offsets.thread_cpu_id_offset) as *mut CInt,
            cpu_id,
        );
        write_volatile(
            cpu_addr.wrapping_add(offsets.cpu_status_offset) as *mut CInt,
            running_status,
        );
    }

    if let Some(log) = log_fn {
        let tid = unsafe {
            read_volatile(thread_addr.wrapping_add(offsets.thread_tid_offset) as *const CInt)
        };
        unsafe {
            log(SCHED_RUNQ_LOG_RUNQ_ADD, thread_addr, cpu_addr, tid, cpu_id);
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn sched_runq_add_thread_body_result(
    thread_addr: usize,
    cpu_addr: usize,
    reservation_lock_addr: usize,
    cpu_id: CInt,
    current_cpu_id: CInt,
    need_resched_flag: u32,
    running_status: CInt,
    vector_key: CInt,
    offsets: *const SchedRunqueueOffsets,
    lock_fn: Option<SchedMigrateSpinLockFn>,
    unlock_fn: Option<SchedMigrateSpinUnlockFn>,
    noirq_lock_fn: Option<SchedMigrateNoirqLockFn>,
    noirq_unlock_fn: Option<SchedMigrateNoirqUnlockFn>,
    reserved_dec_fn: Option<SchedRunqCounterDecFn>,
    procfs_create_fn: Option<SchedRunqThreadFn>,
    clone_count_inc_fn: Option<SchedRunqCounterIncFn>,
    rusage_inc_fn: Option<SchedRunqVoidFn>,
    rusage_debug_fn: Option<SchedRunqVoidFn>,
    vector_fn: Option<SchedMigrateVectorFn>,
    interrupt_fn: Option<SchedMigrateInterruptFn>,
    log_fn: Option<SchedRunqLogFn>,
) -> CInt {
    if thread_addr == 0 || cpu_addr == 0 || offsets.is_null() || reservation_lock_addr == 0 {
        return -EINVAL;
    }
    let (
        Some(lock_fn),
        Some(unlock_fn),
        Some(noirq_lock_fn),
        Some(noirq_unlock_fn),
        Some(reserved_dec_fn),
        Some(procfs_create_fn),
        Some(clone_count_inc_fn),
        Some(rusage_inc_fn),
        Some(rusage_debug_fn),
        Some(vector_fn),
        Some(interrupt_fn),
    ) = (
        lock_fn,
        unlock_fn,
        noirq_lock_fn,
        noirq_unlock_fn,
        reserved_dec_fn,
        procfs_create_fn,
        clone_count_inc_fn,
        rusage_inc_fn,
        rusage_debug_fn,
        vector_fn,
        interrupt_fn,
    )
    else {
        return -EINVAL;
    };
    let offsets_ref = &*offsets;

    let irqstate = lock_fn(reservation_lock_addr);
    noirq_lock_fn(cpu_addr.wrapping_add(offsets_ref.cpu_runq_lock_offset));
    let rc = sched_runq_add_thread_locked_result(
        thread_addr,
        cpu_addr,
        cpu_id,
        need_resched_flag,
        running_status,
        offsets,
        log_fn,
    );
    reserved_dec_fn(cpu_addr.wrapping_add(offsets_ref.cpu_runq_reserved_offset));
    noirq_unlock_fn(cpu_addr.wrapping_add(offsets_ref.cpu_runq_lock_offset));
    unlock_fn(reservation_lock_addr, irqstate);
    if rc != 0 {
        return rc;
    }

    procfs_create_fn(thread_addr);

    let proc_addr = sched_read_usize(thread_addr, offsets_ref.thread_proc_offset);
    let clone_count = if proc_addr == 0 {
        0
    } else {
        clone_count_inc_fn(proc_addr.wrapping_add(offsets_ref.proc_clone_count_offset))
    };
    if let Some(log) = log_fn {
        unsafe {
            log(
                SCHED_RUNQ_LOG_CLONE_COUNT,
                thread_addr,
                proc_addr,
                clone_count,
                0,
            );
        }
    }

    rusage_inc_fn();
    rusage_debug_fn();

    if cpu_id != current_cpu_id {
        let vector = vector_fn(vector_key);
        interrupt_fn(cpu_id, vector);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn sched_runq_del_thread_body_result(
    thread_addr: usize,
    cpu_addr: usize,
    idle_status: CInt,
    offsets: *const SchedRunqueueOffsets,
    lock_fn: Option<SchedMigrateSpinLockFn>,
    unlock_fn: Option<SchedMigrateSpinUnlockFn>,
) -> CInt {
    if thread_addr == 0 || cpu_addr == 0 || offsets.is_null() {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock)) = (lock_fn, unlock_fn) else {
        return -EINVAL;
    };

    let offsets = unsafe { &*offsets };
    let runq_lock_addr = cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    let irqstate = unsafe { lock(runq_lock_addr) };
    unsafe {
        list_detach_counted_addr(
            thread_addr.wrapping_add(offsets.thread_sched_list_offset),
            cpu_addr.wrapping_add(offsets.cpu_runq_len_offset),
        );
    }
    let runq_len = unsafe {
        read_volatile(cpu_addr.wrapping_add(offsets.cpu_runq_len_offset) as *const usize)
    };
    if runq_len == 0 {
        unsafe {
            write_volatile(
                cpu_addr.wrapping_add(offsets.cpu_status_offset) as *mut CInt,
                idle_status,
            );
        }
    }
    unsafe {
        unlock(runq_lock_addr, irqstate);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn runq_del_thread(thread: *mut Thread, cpu_id: CInt) {
    let cpu_addr = unsafe { process_sched_cpu_local_bridge(cpu_id) };
    let offsets = sched_runqueue_offsets();
    let _ = unsafe {
        sched_runq_del_thread_body_result(
            thread as usize,
            cpu_addr,
            CPU_STATUS_IDLE,
            &offsets,
            Some(sched_process_spin_lock_bridge),
            Some(sched_process_spin_unlock_bridge),
        )
    };
}

#[no_mangle]
pub unsafe extern "C" fn sched_wakeup_thread_body_result(
    thread_addr: usize,
    cpu_addr: usize,
    update_lock_node_addr: usize,
    current_cpu_id: CInt,
    valid_states: CInt,
    runq_locked: CInt,
    running_status: CInt,
    exited_status: CInt,
    need_resched_flag: u32,
    vector_key: CInt,
    offsets: *const SchedRunqueueOffsets,
    lock_fn: Option<SchedMigrateSpinLockFn>,
    unlock_fn: Option<SchedMigrateSpinUnlockFn>,
    rwlock_fn: Option<SchedRunqRwlockFn>,
    rwunlock_fn: Option<SchedRunqRwlockFn>,
    status_set_fn: Option<SchedRunqStatusSetFn>,
    set_timer_fn: Option<SchedRunqSetTimerFn>,
    vector_fn: Option<SchedMigrateVectorFn>,
    interrupt_fn: Option<SchedMigrateInterruptFn>,
    log_fn: Option<SchedRunqLogFn>,
) -> CInt {
    if thread_addr == 0 || cpu_addr == 0 || update_lock_node_addr == 0 || offsets.is_null() {
        return -EINVAL;
    }
    let (
        Some(lock),
        Some(unlock),
        Some(rwlock),
        Some(rwunlock),
        Some(status_set),
        Some(set_timer),
        Some(vector),
        Some(interrupt),
    ) = (
        lock_fn,
        unlock_fn,
        rwlock_fn,
        rwunlock_fn,
        status_set_fn,
        set_timer_fn,
        vector_fn,
        interrupt_fn,
    )
    else {
        return -EINVAL;
    };

    let offsets = unsafe { &*offsets };
    let proc_addr = unsafe {
        read_volatile(thread_addr.wrapping_add(offsets.thread_proc_offset) as *const usize)
    };
    let thread_cpu = unsafe {
        read_volatile(thread_addr.wrapping_add(offsets.thread_cpu_id_offset) as *const CInt)
    };
    let proc_pid = if proc_addr == 0 {
        -1
    } else {
        unsafe { read_volatile(proc_addr.wrapping_add(offsets.proc_pid_offset) as *const CInt) }
    };
    if let Some(log) = log_fn {
        unsafe {
            log(
                SCHED_RUNQ_LOG_WAKE_ENTRY,
                thread_addr,
                proc_addr,
                proc_pid,
                valid_states,
            );
        }
    }

    let spin_lock_addr = thread_addr.wrapping_add(offsets.thread_spin_sleep_lock_offset);
    let spin_sleep_addr = thread_addr.wrapping_add(offsets.thread_spin_sleep_offset);
    let irqstate = unsafe { lock(spin_lock_addr) };
    if unsafe { read_volatile(spin_sleep_addr as *const CInt) } == 1 {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    SCHED_RUNQ_LOG_SPIN_WAKEUP,
                    thread_addr,
                    0,
                    thread_cpu,
                    valid_states,
                );
            }
        }
    }
    unsafe {
        write_volatile(spin_sleep_addr as *mut CInt, 0);
        unlock(spin_lock_addr, irqstate);
    }

    let runq_lock_addr = cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    let runq_irqstate = if runq_locked == 0 {
        unsafe { lock(runq_lock_addr) }
    } else {
        0
    };

    let current_status = unsafe {
        read_volatile(thread_addr.wrapping_add(offsets.thread_status_offset) as *const CInt)
    };
    let status: CInt = if (current_status & valid_states) != 0 {
        if proc_addr != 0 {
            let proc_lock_addr = proc_addr.wrapping_add(offsets.proc_update_lock_offset);
            unsafe {
                rwlock(proc_lock_addr, update_lock_node_addr);
            }
            let proc_status_addr = proc_addr.wrapping_add(offsets.proc_status_offset);
            let proc_status = unsafe { read_volatile(proc_status_addr as *const CInt) };
            if proc_status != exited_status {
                unsafe {
                    write_volatile(proc_status_addr as *mut CInt, running_status);
                }
            }
            unsafe {
                rwunlock(proc_lock_addr, update_lock_node_addr);
            }
        }

        unsafe {
            status_set(
                thread_addr.wrapping_add(offsets.thread_status_offset),
                running_status,
            );
            let flags_addr = cpu_addr.wrapping_add(offsets.cpu_flags_offset);
            let flags = read_volatile(flags_addr as *const u32);
            write_volatile(flags_addr as *mut u32, flags | need_resched_flag);
        }

        if thread_cpu == current_cpu_id {
            unsafe {
                set_timer(1);
            }
        }
        0
    } else {
        -EINVAL
    };

    if runq_locked == 0 {
        unsafe {
            unlock(runq_lock_addr, runq_irqstate);
        }
    }

    if status == 0 && thread_cpu != current_cpu_id {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    SCHED_RUNQ_LOG_REMOTE_IPI,
                    thread_addr,
                    cpu_addr,
                    thread_cpu,
                    vector_key,
                );
            }
        }
        unsafe {
            interrupt(thread_cpu, vector(vector_key));
        }
    }

    status
}

unsafe fn sched_thread_has_pending_signal(
    thread_addr: usize,
    offsets: &SchedRunqueueOffsets,
    has_signal: SchedRunqHasSignalFn,
) -> bool {
    let thread_pending =
        !unsafe { list_empty_addr(thread_addr.wrapping_add(offsets.thread_sigpending_offset)) };
    let sigcommon = unsafe {
        read_volatile(thread_addr.wrapping_add(offsets.thread_sigcommon_offset) as *const usize)
    };
    let common_pending = sigcommon != 0
        && !unsafe { list_empty_addr(sigcommon.wrapping_add(offsets.sigcommon_sigpending_offset)) };

    (thread_pending || common_pending) && unsafe { has_signal(thread_addr) != 0 }
}

#[inline(always)]
unsafe fn sched_write_schedule_result(
    result: *mut SchedScheduleResult,
    cpu_addr: usize,
    prev_thread_addr: usize,
    next_thread_addr: usize,
    prevpid: CInt,
    switch_ctx: CInt,
    action: CInt,
) {
    unsafe {
        write_volatile(
            result,
            SchedScheduleResult {
                cpu_addr,
                prev_thread_addr,
                next_thread_addr,
                prevpid,
                switch_ctx,
                action,
            },
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn sched_schedule_prepare_body_result(
    cpu_addr: usize,
    idle_thread_addr: usize,
    no_preempt_count: CInt,
    need_resched_flag: u32,
    need_migrate_flag: u32,
    running_status: CInt,
    interruptible_status: CInt,
    exited_status: CInt,
    spawning_to_remote: CInt,
    idle_cpu_status: CInt,
    reserved_cpu_status: CInt,
    offsets: *const SchedRunqueueOffsets,
    result: *mut SchedScheduleResult,
    irq_save_fn: Option<SchedRunqIrqSaveFn>,
    irq_restore_fn: Option<SchedRunqIrqRestoreFn>,
    noirq_lock_fn: Option<SchedMigrateNoirqLockFn>,
    noirq_unlock_fn: Option<SchedMigrateNoirqUnlockFn>,
    set_timer_fn: Option<SchedRunqSetTimerFn>,
    reset_cputime_fn: Option<SchedRunqVoidFn>,
    has_signal_fn: Option<SchedRunqHasSignalFn>,
    log_fn: Option<SchedRunqLogFn>,
) -> CInt {
    if cpu_addr == 0 || idle_thread_addr == 0 || offsets.is_null() || result.is_null() {
        return -EINVAL;
    }
    let (
        Some(irq_save),
        Some(irq_restore),
        Some(noirq_lock),
        Some(noirq_unlock),
        Some(set_timer),
        Some(reset_cputime),
        Some(has_signal),
    ) = (
        irq_save_fn,
        irq_restore_fn,
        noirq_lock_fn,
        noirq_unlock_fn,
        set_timer_fn,
        reset_cputime_fn,
        has_signal_fn,
    )
    else {
        return -EINVAL;
    };

    let offsets = unsafe { &*offsets };
    unsafe {
        sched_write_schedule_result(result, cpu_addr, 0, 0, 0, 0, 0);
    }

    let runq_lock_addr = cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    let flags_addr = cpu_addr.wrapping_add(offsets.cpu_flags_offset);

    if no_preempt_count != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    SCHED_RUNQ_LOG_NO_PREEMPT,
                    cpu_addr,
                    runq_lock_addr,
                    no_preempt_count,
                    0,
                );
            }
        }
        let irqstate = unsafe { irq_save() };
        unsafe { noirq_lock(runq_lock_addr) };
        let flags = unsafe { read_volatile(flags_addr as *const u32) };
        unsafe { write_volatile(flags_addr as *mut u32, flags | need_resched_flag) };
        unsafe { noirq_unlock(runq_lock_addr) };
        unsafe { irq_restore(irqstate) };
        unsafe {
            sched_write_schedule_result(
                result,
                cpu_addr,
                0,
                0,
                0,
                0,
                SCHED_SCHEDULE_ACTION_RESCHED_ONLY,
            );
        }
        return SCHED_SCHEDULE_ACTION_RESCHED_ONLY;
    }

    let irqstate = unsafe { irq_save() };
    unsafe { noirq_lock(runq_lock_addr) };
    unsafe {
        write_volatile(
            cpu_addr.wrapping_add(offsets.cpu_runq_irqstate_offset) as *mut CULong,
            irqstate,
        );
    }

    let prev_thread_addr =
        unsafe { read_volatile(cpu_addr.wrapping_add(offsets.cpu_current_offset) as *const usize) };
    let old_prevpid =
        unsafe { read_volatile(cpu_addr.wrapping_add(offsets.cpu_prevpid_offset) as *const CInt) };

    if prev_thread_addr != 0 && prev_thread_addr != idle_thread_addr {
        unsafe {
            list_detach_counted_addr(
                prev_thread_addr.wrapping_add(offsets.thread_sched_list_offset),
                cpu_addr.wrapping_add(offsets.cpu_runq_len_offset),
            );
        }
        let prev_status = unsafe {
            read_volatile(prev_thread_addr.wrapping_add(offsets.thread_status_offset) as *const CInt)
        };
        if prev_status != exited_status {
            unsafe {
                list_add_tail_counted_addr(
                    prev_thread_addr.wrapping_add(offsets.thread_sched_list_offset),
                    cpu_addr.wrapping_add(offsets.cpu_runq_offset),
                    cpu_addr.wrapping_add(offsets.cpu_runq_len_offset),
                );
            }
        }
    }

    let flags = unsafe { read_volatile(flags_addr as *const u32) };
    let mut next_thread_addr = 0usize;
    let prev_exited = prev_thread_addr != 0
        && unsafe {
            read_volatile(prev_thread_addr.wrapping_add(offsets.thread_status_offset) as *const CInt)
        } == exited_status;

    if (flags & need_migrate_flag) != 0 || prev_exited {
        next_thread_addr = idle_thread_addr;
    } else {
        let runq_head = cpu_addr.wrapping_add(offsets.cpu_runq_offset);
        let mut entry = unsafe { list_next(runq_head) };
        while entry != runq_head {
            let thread_addr = entry.wrapping_sub(offsets.thread_sched_list_offset);
            let status = unsafe {
                read_volatile(thread_addr.wrapping_add(offsets.thread_status_offset) as *const CInt)
            };
            let mod_clone = unsafe {
                read_volatile(
                    thread_addr.wrapping_add(offsets.thread_mod_clone_offset) as *const CInt
                )
            };
            if status == running_status && mod_clone == spawning_to_remote {
                next_thread_addr = thread_addr;
                break;
            }
            if status == running_status
                || (status == interruptible_status
                    && unsafe { sched_thread_has_pending_signal(thread_addr, offsets, has_signal) })
            {
                if next_thread_addr == 0 {
                    next_thread_addr = thread_addr;
                }
            }
            entry = unsafe { list_next(entry) };
        }

        if next_thread_addr == 0 {
            let runq_len = unsafe {
                read_volatile(cpu_addr.wrapping_add(offsets.cpu_runq_len_offset) as *const usize)
            };
            next_thread_addr = idle_thread_addr;
            unsafe {
                write_volatile(
                    cpu_addr.wrapping_add(offsets.cpu_status_offset) as *mut CInt,
                    if runq_len != 0 {
                        reserved_cpu_status
                    } else {
                        idle_cpu_status
                    },
                );
            }
        }
    }

    let mut switch_ctx = 0;
    if prev_thread_addr != next_thread_addr {
        switch_ctx = 1;
        let mut new_prevpid = 0;
        if prev_thread_addr != 0 {
            let proc_addr = unsafe {
                read_volatile(
                    prev_thread_addr.wrapping_add(offsets.thread_proc_offset) as *const usize
                )
            };
            if proc_addr != 0 {
                new_prevpid = unsafe {
                    read_volatile(proc_addr.wrapping_add(offsets.proc_pid_offset) as *const CInt)
                };
            }
        }
        unsafe {
            write_volatile(
                cpu_addr.wrapping_add(offsets.cpu_prevpid_offset) as *mut CInt,
                new_prevpid,
            );
            write_volatile(
                cpu_addr.wrapping_add(offsets.cpu_current_offset) as *mut usize,
                next_thread_addr,
            );
            reset_cputime();
            let nr_addr = cpu_addr.wrapping_add(offsets.cpu_nr_ctx_switches_offset) as *mut CULong;
            let nr = read_volatile(nr_addr);
            write_volatile(nr_addr, nr.wrapping_add(1));
        }
    }

    unsafe { set_timer(1) };

    let action = if switch_ctx != 0 {
        SCHED_SCHEDULE_ACTION_SWITCH
    } else {
        unsafe {
            noirq_unlock(runq_lock_addr);
            irq_restore(irqstate);
        }
        SCHED_SCHEDULE_ACTION_NO_SWITCH
    };

    unsafe {
        sched_write_schedule_result(
            result,
            cpu_addr,
            prev_thread_addr,
            next_thread_addr,
            old_prevpid,
            switch_ctx,
            action,
        );
    }
    action
}

#[no_mangle]
pub unsafe extern "C" fn sched_spin_sleep_or_schedule_body_result(
    thread_addr: usize,
    cpu_addr: usize,
    current_cpu_id: CInt,
    idle_halt_enabled: CInt,
    need_resched_flag: u32,
    offsets: *const SchedRunqueueOffsets,
    irq_save_fn: Option<SchedRunqIrqSaveFn>,
    irq_restore_fn: Option<SchedRunqIrqRestoreFn>,
    lock_fn: Option<SchedMigrateSpinLockFn>,
    unlock_fn: Option<SchedMigrateSpinUnlockFn>,
    noirq_lock_fn: Option<SchedMigrateNoirqLockFn>,
    noirq_unlock_fn: Option<SchedMigrateNoirqUnlockFn>,
    schedule_fn: Option<SchedMigrateVoidFn>,
    zero_free_fn: Option<SchedMigrateVoidFn>,
    pause_fn: Option<SchedMigrateVoidFn>,
    has_signal_fn: Option<SchedRunqHasSignalFn>,
    log_fn: Option<SchedRunqLogFn>,
) -> CInt {
    if thread_addr == 0 || cpu_addr == 0 || offsets.is_null() {
        return -EINVAL;
    }
    let (
        Some(irq_save),
        Some(irq_restore),
        Some(lock),
        Some(unlock),
        Some(noirq_lock),
        Some(noirq_unlock),
        Some(schedule),
        Some(zero_free),
        Some(pause),
        Some(has_signal),
    ) = (
        irq_save_fn,
        irq_restore_fn,
        lock_fn,
        unlock_fn,
        noirq_lock_fn,
        noirq_unlock_fn,
        schedule_fn,
        zero_free_fn,
        pause_fn,
        has_signal_fn,
    )
    else {
        return -EINVAL;
    };

    let offsets = unsafe { &*offsets };
    let thread_spin_lock_addr = thread_addr.wrapping_add(offsets.thread_spin_sleep_lock_offset);
    let thread_spin_sleep_addr = thread_addr.wrapping_add(offsets.thread_spin_sleep_offset);
    let runq_lock_addr = cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);
    let runq_len_addr = cpu_addr.wrapping_add(offsets.cpu_runq_len_offset);
    let flags_addr = cpu_addr.wrapping_add(offsets.cpu_flags_offset);
    let tid = unsafe {
        read_volatile(thread_addr.wrapping_add(offsets.thread_tid_offset) as *const CInt)
    };

    if idle_halt_enabled != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    SCHED_RUNQ_LOG_IDLE_HALT,
                    thread_addr,
                    cpu_addr,
                    tid,
                    current_cpu_id,
                );
            }
        }
        unsafe {
            schedule();
        }
        if let Some(log) = log_fn {
            unsafe {
                log(
                    SCHED_RUNQ_LOG_SLEEP_WOKEN,
                    thread_addr,
                    cpu_addr,
                    tid,
                    current_cpu_id,
                );
            }
        }
        return 2;
    }

    let irqstate = unsafe { lock(thread_spin_lock_addr) };
    if unsafe { read_volatile(thread_spin_sleep_addr as *const CInt) } == 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    SCHED_RUNQ_LOG_LOST_WAKEUP,
                    thread_addr,
                    cpu_addr,
                    tid,
                    current_cpu_id,
                );
            }
        }
    }
    unsafe {
        unlock(thread_spin_lock_addr, irqstate);
    }

    loop {
        let mut do_schedule = false;
        let mut woken = false;

        let irqstate = unsafe { irq_save() };
        unsafe {
            noirq_lock(runq_lock_addr);
        }
        let flags = unsafe { read_volatile(flags_addr as *const u32) };
        let runq_len = unsafe { read_volatile(runq_len_addr as *const usize) };
        if (flags & need_resched_flag) != 0 || runq_len > 1 {
            unsafe {
                write_volatile(flags_addr as *mut u32, flags & !need_resched_flag);
            }
            do_schedule = true;
        }
        unsafe {
            noirq_unlock(runq_lock_addr);
            irq_restore(irqstate);
        }

        let irqstate = unsafe { lock(thread_spin_lock_addr) };
        if unsafe { read_volatile(thread_spin_sleep_addr as *const CInt) } == 0 {
            woken = true;
        }
        if do_schedule {
            unsafe {
                write_volatile(thread_spin_sleep_addr as *mut CInt, 0);
            }
        }
        unsafe {
            unlock(thread_spin_lock_addr, irqstate);
        }

        if unsafe { sched_thread_has_pending_signal(thread_addr, offsets, has_signal) } {
            woken = true;
        }

        if woken {
            if let Some(log) = log_fn {
                unsafe {
                    log(
                        SCHED_RUNQ_LOG_SPIN_WOKEN,
                        thread_addr,
                        cpu_addr,
                        tid,
                        do_schedule as CInt,
                    );
                }
            }
            if do_schedule {
                let irqstate = unsafe { lock(runq_lock_addr) };
                let flags = unsafe { read_volatile(flags_addr as *const u32) };
                unsafe {
                    write_volatile(flags_addr as *mut u32, flags | need_resched_flag);
                    unlock(runq_lock_addr, irqstate);
                }
            }
            return 1;
        }

        if do_schedule {
            break;
        }

        unsafe {
            zero_free();
            pause();
        }
    }

    unsafe {
        schedule();
    }
    if let Some(log) = log_fn {
        unsafe {
            log(
                SCHED_RUNQ_LOG_SLEEP_WOKEN,
                thread_addr,
                cpu_addr,
                tid,
                current_cpu_id,
            );
        }
    }
    2
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
pub unsafe extern "C" fn futex_get_key_result(
    uaddr: usize,
    fshared: CInt,
    key_addr: usize,
    mm_addr: usize,
    key_word_offset: usize,
    key_ptr_offset: usize,
    key_offset_offset: usize,
    fut_off_mmshared: usize,
    fault_flags: CInt,
    key_refs_fn: Option<FutexKeyRefsFn>,
    vtop_fn: Option<FutexGetKeyVtopFn>,
    fault_fn: Option<FutexGetKeyFaultFn>,
    log_fn: Option<FutexGetKeyLogFn>,
) -> CInt {
    if key_addr == 0 || mm_addr == 0 {
        return -EINVAL;
    }
    let Some(key_refs) = key_refs_fn else {
        return -EINVAL;
    };
    let Some(vtop) = vtop_fn else {
        return -EINVAL;
    };
    let Some(fault) = fault_fn else {
        return -EINVAL;
    };
    let Some(log) = log_fn else {
        return -EINVAL;
    };

    let mut base = 0usize;
    let mut offset = 0usize;
    let mut is_private = 0;
    let ret = unsafe {
        futex_key_prepare_result(
            uaddr,
            fshared,
            &raw mut base,
            &raw mut offset,
            &raw mut is_private,
        )
    };
    if ret != 0 {
        return ret;
    }

    unsafe {
        write_volatile(
            key_addr.wrapping_add(key_offset_offset) as *mut CInt,
            offset as CInt,
        );
    }
    if is_private != 0 {
        unsafe {
            write_volatile(key_addr.wrapping_add(key_word_offset) as *mut usize, base);
            write_volatile(key_addr.wrapping_add(key_ptr_offset) as *mut usize, mm_addr);
            key_refs(key_addr);
        }
        return 0;
    }

    unsafe {
        write_volatile(
            key_addr.wrapping_add(key_offset_offset) as *mut CInt,
            (offset | fut_off_mmshared) as CInt,
        );
    }

    loop {
        let mut phys = 0usize;
        let vtop_ret = unsafe { vtop(mm_addr, uaddr, (&raw mut phys) as usize) };
        if vtop_ret == 0 {
            unsafe {
                write_volatile(key_addr.wrapping_add(key_word_offset) as *mut usize, 0);
                write_volatile(key_addr.wrapping_add(key_ptr_offset) as *mut usize, phys);
            }
            return 0;
        }

        let fault_ret = unsafe { fault(mm_addr, uaddr, fault_flags) };
        if fault_ret != 0 {
            unsafe {
                log(FUTEX_GET_KEY_LOG_VTOP_FAILED);
            }
            return -EFAULT;
        }
    }
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
pub unsafe extern "C" fn futex_wake_body_result(
    uaddr: usize,
    fshared: CInt,
    nr_wake: CInt,
    bitset: u32,
    key_addr: usize,
    hb_lock_offset: usize,
    hb_chain_offset: usize,
    q_list_offset: usize,
    q_key_offset: usize,
    q_bitset_offset: usize,
    key_word_offset: usize,
    key_ptr_offset: usize,
    key_offset_offset: usize,
    get_key_fn: Option<FutexWaitGetKeyFn>,
    hash_key_fn: Option<FutexWakeHashKeyFn>,
    lock_fn: Option<FutexWakeLockFn>,
    unlock_fn: Option<FutexWakeUnlockFn>,
    put_key_fn: Option<FutexWaitPutKeyFn>,
    wake_fn: Option<FutexWakeScanFn>,
) -> CInt {
    if key_addr == 0 {
        return -EINVAL;
    }
    let Some(get_key) = get_key_fn else {
        return -EINVAL;
    };
    let Some(hash_key) = hash_key_fn else {
        return -EINVAL;
    };
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };
    let Some(put_key) = put_key_fn else {
        return -EINVAL;
    };
    let Some(wake) = wake_fn else {
        return -EINVAL;
    };

    if futex_wake_bitset_valid_result(bitset) == 0 {
        return -EINVAL;
    }

    let get_ret = unsafe { get_key(uaddr, fshared, key_addr) };
    if get_ret != 0 {
        return get_ret;
    }

    let hb_addr = unsafe { hash_key(key_addr) };
    if hb_addr == 0 {
        unsafe {
            put_key(fshared, key_addr);
        }
        return -EINVAL;
    }

    let target_word =
        unsafe { core::ptr::read_volatile(key_addr.wrapping_add(key_word_offset) as *const usize) };
    let target_ptr =
        unsafe { core::ptr::read_volatile(key_addr.wrapping_add(key_ptr_offset) as *const usize) };
    let target_offset = unsafe {
        core::ptr::read_volatile(key_addr.wrapping_add(key_offset_offset) as *const CInt)
    };
    let lock_addr = hb_addr.wrapping_add(hb_lock_offset);
    let irqstate = unsafe { lock(lock_addr) };
    let ret = unsafe {
        futex_wake_scan_result(
            hb_addr.wrapping_add(hb_chain_offset),
            q_list_offset,
            q_key_offset,
            q_bitset_offset,
            key_word_offset,
            key_ptr_offset,
            key_offset_offset,
            target_word,
            target_ptr,
            target_offset,
            bitset,
            1,
            nr_wake,
            Some(wake),
        )
    };
    unsafe {
        unlock(lock_addr, irqstate);
        put_key(fshared, key_addr);
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn futex_wake_op_body_result(
    uaddr1: usize,
    fshared: CInt,
    uaddr2: usize,
    nr_wake: CInt,
    nr_wake2: CInt,
    op: CInt,
    key1_addr: usize,
    key2_addr: usize,
    hb_lock_offset: usize,
    hb_chain_offset: usize,
    q_list_offset: usize,
    q_key_offset: usize,
    q_bitset_offset: usize,
    key_word_offset: usize,
    key_ptr_offset: usize,
    key_offset_offset: usize,
    get_key_fn: Option<FutexWaitGetKeyFn>,
    hash_key_fn: Option<FutexWakeHashKeyFn>,
    lock_fn: Option<FutexHbLockFn>,
    unlock_fn: Option<FutexHbUnlockFn>,
    atomic_fn: Option<FutexWakeAtomicOpFn>,
    put_key_fn: Option<FutexWaitPutKeyFn>,
    wake_fn: Option<FutexWakeScanFn>,
) -> CInt {
    if key1_addr == 0 || key2_addr == 0 {
        return -EINVAL;
    }
    let Some(get_key) = get_key_fn else {
        return -EINVAL;
    };
    let Some(hash_key) = hash_key_fn else {
        return -EINVAL;
    };
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };
    let Some(atomic) = atomic_fn else {
        return -EINVAL;
    };
    let Some(put_key) = put_key_fn else {
        return -EINVAL;
    };
    let Some(wake) = wake_fn else {
        return -EINVAL;
    };

    loop {
        let mut ret = unsafe { get_key(uaddr1, fshared, key1_addr) };
        if ret != 0 {
            return ret;
        }
        ret = unsafe { get_key(uaddr2, fshared, key2_addr) };
        if ret != 0 {
            unsafe {
                put_key(fshared, key1_addr);
            }
            return ret;
        }

        let hb1_addr = unsafe { hash_key(key1_addr) };
        let hb2_addr = unsafe { hash_key(key2_addr) };
        if hb1_addr == 0 || hb2_addr == 0 {
            unsafe {
                put_key(fshared, key2_addr);
                put_key(fshared, key1_addr);
            }
            return -EINVAL;
        }

        loop {
            unsafe {
                futex_double_lock_hb_result(hb1_addr, hb2_addr, hb_lock_offset, Some(lock));
            }
            let op_ret = unsafe { atomic(op, uaddr2) };
            if op_ret < 0 {
                unsafe {
                    futex_double_unlock_hb_result(hb1_addr, hb2_addr, hb_lock_offset, Some(unlock));
                }
                if op_ret != -EFAULT {
                    unsafe {
                        put_key(fshared, key2_addr);
                        put_key(fshared, key1_addr);
                    }
                    return op_ret;
                }
                if fshared == 0 {
                    continue;
                }
                unsafe {
                    put_key(fshared, key2_addr);
                    put_key(fshared, key1_addr);
                }
                break;
            }

            let key1_word =
                unsafe { read_volatile(key1_addr.wrapping_add(key_word_offset) as *const usize) };
            let key1_ptr =
                unsafe { read_volatile(key1_addr.wrapping_add(key_ptr_offset) as *const usize) };
            let key1_offset =
                unsafe { read_volatile(key1_addr.wrapping_add(key_offset_offset) as *const CInt) };
            ret = unsafe {
                futex_wake_scan_result(
                    hb1_addr.wrapping_add(hb_chain_offset),
                    q_list_offset,
                    q_key_offset,
                    q_bitset_offset,
                    key_word_offset,
                    key_ptr_offset,
                    key_offset_offset,
                    key1_word,
                    key1_ptr,
                    key1_offset,
                    0,
                    0,
                    nr_wake,
                    Some(wake),
                )
            };
            if op_ret > 0 {
                let key2_word = unsafe {
                    read_volatile(key2_addr.wrapping_add(key_word_offset) as *const usize)
                };
                let key2_ptr = unsafe {
                    read_volatile(key2_addr.wrapping_add(key_ptr_offset) as *const usize)
                };
                let key2_offset = unsafe {
                    read_volatile(key2_addr.wrapping_add(key_offset_offset) as *const CInt)
                };
                ret += unsafe {
                    futex_wake_scan_result(
                        hb2_addr.wrapping_add(hb_chain_offset),
                        q_list_offset,
                        q_key_offset,
                        q_bitset_offset,
                        key_word_offset,
                        key_ptr_offset,
                        key_offset_offset,
                        key2_word,
                        key2_ptr,
                        key2_offset,
                        0,
                        0,
                        nr_wake2,
                        Some(wake),
                    )
                };
            }

            unsafe {
                futex_double_unlock_hb_result(hb1_addr, hb2_addr, hb_lock_offset, Some(unlock));
                put_key(fshared, key2_addr);
                put_key(fshared, key1_addr);
            }
            return ret;
        }
    }
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
pub unsafe extern "C" fn futex_requeue_body_result(
    uaddr1: usize,
    fshared: CInt,
    uaddr2: usize,
    nr_wake: CInt,
    nr_requeue: CInt,
    cmpval_addr: usize,
    key1_addr: usize,
    key2_addr: usize,
    ctx_addr: usize,
    hb_lock_offset: usize,
    hb_chain_offset: usize,
    q_list_offset: usize,
    q_key_offset: usize,
    key_word_offset: usize,
    key_ptr_offset: usize,
    key_offset_offset: usize,
    ctx_hb1_offset: usize,
    ctx_hb2_offset: usize,
    ctx_key2_offset: usize,
    get_key_fn: Option<FutexWaitGetKeyFn>,
    hash_key_fn: Option<FutexWakeHashKeyFn>,
    lock_fn: Option<FutexHbLockFn>,
    unlock_fn: Option<FutexHbUnlockFn>,
    get_value_fn: Option<FutexWaitGetValueFn>,
    put_key_fn: Option<FutexWaitPutKeyFn>,
    drop_key_refs_fn: Option<FutexKeyRefsFn>,
    wake_fn: Option<FutexRequeueScanFn>,
    requeue_fn: Option<FutexRequeueScanFn>,
) -> CInt {
    if key1_addr == 0 || key2_addr == 0 || ctx_addr == 0 {
        return -EINVAL;
    }
    let Some(get_key) = get_key_fn else {
        return -EINVAL;
    };
    let Some(hash_key) = hash_key_fn else {
        return -EINVAL;
    };
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };
    let Some(put_key) = put_key_fn else {
        return -EINVAL;
    };
    let Some(drop_key_refs) = drop_key_refs_fn else {
        return -EINVAL;
    };
    let Some(wake) = wake_fn else {
        return -EINVAL;
    };
    let Some(requeue) = requeue_fn else {
        return -EINVAL;
    };
    if cmpval_addr != 0 && get_value_fn.is_none() {
        return -EINVAL;
    }

    let mut ret = unsafe { get_key(uaddr1, fshared, key1_addr) };
    if ret != 0 {
        return ret;
    }

    ret = unsafe { get_key(uaddr2, fshared, key2_addr) };
    if ret != 0 {
        unsafe {
            put_key(fshared, key1_addr);
        }
        return ret;
    }

    let hb1_addr = unsafe { hash_key(key1_addr) };
    let hb2_addr = unsafe { hash_key(key2_addr) };
    if hb1_addr == 0 || hb2_addr == 0 {
        unsafe {
            put_key(fshared, key2_addr);
            put_key(fshared, key1_addr);
        }
        return -EINVAL;
    }

    unsafe {
        futex_double_lock_hb_result(hb1_addr, hb2_addr, hb_lock_offset, Some(lock));
    }

    let mut drop_count: CInt = 0;
    let mut task_count: CInt = 0;
    let mut scan = true;
    if cmpval_addr != 0 {
        let Some(get_value) = get_value_fn else {
            unsafe {
                futex_double_unlock_hb_result(hb1_addr, hb2_addr, hb_lock_offset, Some(unlock));
                put_key(fshared, key2_addr);
                put_key(fshared, key1_addr);
            }
            return -EINVAL;
        };
        let mut curval: u32 = 0;
        ret = unsafe { get_value((&mut curval as *mut u32) as usize, uaddr1) };
        let cmpval = unsafe { read_volatile(cmpval_addr as *const u32) };
        if curval != cmpval {
            ret = -EWOULDBLOCK;
            scan = false;
        }
    }

    if scan {
        unsafe {
            write_volatile(
                ctx_addr.wrapping_add(ctx_hb1_offset) as *mut usize,
                hb1_addr,
            );
            write_volatile(
                ctx_addr.wrapping_add(ctx_hb2_offset) as *mut usize,
                hb2_addr,
            );
            write_volatile(
                ctx_addr.wrapping_add(ctx_key2_offset) as *mut usize,
                key2_addr,
            );
        }
        let target_word =
            unsafe { read_volatile(key1_addr.wrapping_add(key_word_offset) as *const usize) };
        let target_ptr =
            unsafe { read_volatile(key1_addr.wrapping_add(key_ptr_offset) as *const usize) };
        let target_offset =
            unsafe { read_volatile(key1_addr.wrapping_add(key_offset_offset) as *const CInt) };
        task_count = unsafe {
            futex_requeue_scan_result(
                hb1_addr.wrapping_add(hb_chain_offset),
                q_list_offset,
                q_key_offset,
                key_word_offset,
                key_ptr_offset,
                key_offset_offset,
                target_word,
                target_ptr,
                target_offset,
                nr_wake,
                nr_requeue,
                &mut drop_count,
                Some(wake),
                Some(requeue),
                ctx_addr,
            )
        };
    }

    unsafe {
        futex_double_unlock_hb_result(hb1_addr, hb2_addr, hb_lock_offset, Some(unlock));
        while drop_count > 0 {
            drop_key_refs(key1_addr);
            drop_count -= 1;
        }
        put_key(fshared, key2_addr);
        put_key(fshared, key1_addr);
    }

    if ret != 0 {
        ret
    } else {
        task_count
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
pub unsafe extern "C" fn futex_unqueue_me_result(
    q_addr: usize,
    lock_ptr_offset: usize,
    list_offset: usize,
    node_plist_offset: usize,
    key_offset: usize,
    lock_fn: Option<FutexHbLockFn>,
    unlock_fn: Option<FutexHbUnlockFn>,
    drop_key_refs_fn: Option<FutexKeyRefsFn>,
) -> CInt {
    if q_addr == 0 {
        return -EINVAL;
    }
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };
    let Some(drop_key_refs) = drop_key_refs_fn else {
        return -EINVAL;
    };

    let mut ret = 0;
    loop {
        let lock_addr =
            unsafe { read_volatile(q_addr.wrapping_add(lock_ptr_offset) as *const usize) };
        compiler_fence(Ordering::SeqCst);
        if lock_addr == 0 {
            break;
        }

        unsafe {
            lock(lock_addr);
        }
        let current_lock =
            unsafe { read_volatile(q_addr.wrapping_add(lock_ptr_offset) as *const usize) };
        if lock_addr != current_lock {
            unsafe {
                unlock(lock_addr);
            }
            continue;
        }

        ret = unsafe { futex_unqueue_detach_result(q_addr, list_offset, node_plist_offset) };
        unsafe {
            unlock(lock_addr);
        }
        break;
    }

    unsafe {
        drop_key_refs(q_addr.wrapping_add(key_offset));
    }
    ret
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
pub unsafe extern "C" fn futex_queue_me_result(
    q_addr: usize,
    q_list_offset: usize,
    q_task_offset: usize,
    q_th_spin_sleep_pa_offset: usize,
    q_th_status_pa_offset: usize,
    q_th_spin_sleep_lock_pa_offset: usize,
    q_proc_status_pa_offset: usize,
    q_proc_update_lock_pa_offset: usize,
    q_runq_lock_pa_offset: usize,
    q_clv_flags_pa_offset: usize,
    q_intr_id_offset: usize,
    q_intr_vector_offset: usize,
    hb_chain_addr: usize,
    hb_lock_addr: usize,
    prio: CInt,
    debug_spinlock_offset: usize,
    thread_addr: usize,
    thread_spin_sleep_offset: usize,
    thread_status_offset: usize,
    thread_spin_sleep_lock_offset: usize,
    thread_proc_offset: usize,
    thread_cpu_id_offset: usize,
    proc_status_offset: usize,
    proc_update_lock_offset: usize,
    runq_lock_addr: usize,
    clv_flags_addr: usize,
    vector_key: CInt,
    virt_to_phys_fn: Option<FutexVirtToPhysFn>,
    interrupt_id_fn: Option<FutexInterruptIdFn>,
    vector_fn: Option<FutexVectorFn>,
    unlock_fn: Option<FutexHbUnlockFn>,
) -> CInt {
    if q_addr == 0 || hb_chain_addr == 0 || hb_lock_addr == 0 || thread_addr == 0 {
        return -EINVAL;
    }
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return -EINVAL;
    };
    let Some(interrupt_id) = interrupt_id_fn else {
        return -EINVAL;
    };
    let Some(vector) = vector_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };

    unsafe {
        futex_queue_insert_result(
            q_addr,
            q_list_offset,
            hb_chain_addr,
            prio,
            debug_spinlock_offset,
            hb_lock_addr,
        );

        let proc_addr = read_usize_field(thread_addr, thread_proc_offset);
        let cpu_id = read_cint_field(thread_addr, thread_cpu_id_offset);
        futex_queue_publish_waiter_result(
            q_addr,
            q_task_offset,
            q_th_spin_sleep_pa_offset,
            q_th_status_pa_offset,
            q_th_spin_sleep_lock_pa_offset,
            q_proc_status_pa_offset,
            q_proc_update_lock_pa_offset,
            q_runq_lock_pa_offset,
            q_clv_flags_pa_offset,
            q_intr_id_offset,
            q_intr_vector_offset,
            thread_addr,
            virt_to_phys(thread_addr.wrapping_add(thread_spin_sleep_offset)),
            virt_to_phys(thread_addr.wrapping_add(thread_status_offset)),
            virt_to_phys(thread_addr.wrapping_add(thread_spin_sleep_lock_offset)),
            virt_to_phys(proc_addr.wrapping_add(proc_status_offset)),
            virt_to_phys(proc_addr.wrapping_add(proc_update_lock_offset)),
            virt_to_phys(runq_lock_addr),
            virt_to_phys(clv_flags_addr),
            interrupt_id(cpu_id),
            vector(vector_key),
        );
        unlock(hb_lock_addr);
    }

    0
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

#[inline(always)]
unsafe fn plist_node_empty_addr(
    node_addr: usize,
    plist_offset: usize,
    node_list_offset: usize,
) -> bool {
    let node_list = node_addr
        .wrapping_add(plist_offset)
        .wrapping_add(node_list_offset);
    unsafe { read_volatile(node_list as *const usize) == node_list }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wait_queue_me_result(
    hb_addr: usize,
    q_addr: usize,
    q_list_offset: usize,
    q_node_plist_offset: usize,
    q_plist_node_list_offset: usize,
    thread_addr: usize,
    thread_status_offset: usize,
    thread_spin_sleep_offset: usize,
    thread_spin_sleep_lock_offset: usize,
    thread_tid_offset: usize,
    idle_halt_enabled: CInt,
    timeout: u64,
    interruptible_status: CInt,
    running_status: CInt,
    spin_lock_fn: Option<FutexWaitSpinLockFn>,
    spin_unlock_fn: Option<FutexWaitSpinUnlockFn>,
    queue_me_fn: Option<FutexWaitQueueMeFn>,
    schedule_timeout_fn: Option<FutexWaitScheduleTimeoutFn>,
    schedule_direct_fn: Option<FutexWaitScheduleDirectFn>,
    log_fn: Option<FutexWaitQueueLogFn>,
) -> i64 {
    if hb_addr == 0 || q_addr == 0 || thread_addr == 0 {
        return -(EINVAL as i64);
    }
    let Some(spin_lock) = spin_lock_fn else {
        return -(EINVAL as i64);
    };
    let Some(spin_unlock) = spin_unlock_fn else {
        return -(EINVAL as i64);
    };
    let Some(queue_me) = queue_me_fn else {
        return -(EINVAL as i64);
    };
    let Some(schedule_timeout) = schedule_timeout_fn else {
        return -(EINVAL as i64);
    };
    let Some(schedule_direct) = schedule_direct_fn else {
        return -(EINVAL as i64);
    };
    let Some(log) = log_fn else {
        return -(EINVAL as i64);
    };

    unsafe {
        futex_wait_mark_interruptible_result(
            thread_addr,
            thread_status_offset,
            interruptible_status,
        );
    }
    if idle_halt_enabled == 0 || timeout != 0 {
        let lock_addr = thread_addr.wrapping_add(thread_spin_sleep_lock_offset);
        let irqstate = unsafe { spin_lock(lock_addr) };
        unsafe {
            futex_wait_spin_sleep_store_result(thread_addr, thread_spin_sleep_offset, 1);
            spin_unlock(lock_addr, irqstate);
        }
    }

    unsafe {
        queue_me(q_addr, hb_addr);
    }
    let queued = unsafe {
        !plist_node_empty_addr(
            q_addr.wrapping_add(q_list_offset),
            q_node_plist_offset,
            q_plist_node_list_offset,
        )
    };
    let action = futex_wait_schedule_action_result(queued as CInt, timeout);
    let tid = unsafe { read_cint_field(thread_addr, thread_tid_offset) };
    let mut time_remain = 0i64;
    if action == FUTEX_WAIT_SCHEDULE_TIMEOUT {
        unsafe {
            log(FUTEX_WAIT_QUEUE_LOG_TIMEOUT, thread_addr, tid);
            time_remain = schedule_timeout(timeout);
        }
    } else if action == FUTEX_WAIT_SCHEDULE_DIRECT {
        unsafe {
            log(FUTEX_WAIT_QUEUE_LOG_DIRECT, thread_addr, tid);
            schedule_direct();
        }
        time_remain = 0;
    }
    if action != FUTEX_WAIT_SCHEDULE_NONE {
        unsafe {
            log(FUTEX_WAIT_QUEUE_LOG_WOKEN, thread_addr, tid);
        }
    }

    unsafe {
        futex_wait_finish_state_result(
            thread_addr,
            thread_status_offset,
            thread_spin_sleep_offset,
            running_status,
        );
    }
    time_remain
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
pub unsafe extern "C" fn futex_wait_body_result(
    uaddr: usize,
    fshared: CInt,
    val: u32,
    timeout: u64,
    bitset: u32,
    q_addr: usize,
    thread_addr: usize,
    uti_futex_resp: usize,
    q_bitset_offset: usize,
    q_requeue_pi_key_offset: usize,
    q_uti_futex_resp_offset: usize,
    q_key_offset: usize,
    thread_tid_offset: usize,
    setup_fn: Option<FutexWaitSetupCallFn>,
    wait_queue_fn: Option<FutexWaitQueueCallFn>,
    unqueue_fn: Option<FutexWaitUnqueueFn>,
    has_signal_fn: Option<FutexWaitHasSignalFn>,
    put_key_fn: Option<FutexWaitPutKeyFn>,
    log_fn: Option<FutexWaitLogFn>,
) -> CInt {
    if q_addr == 0 || thread_addr == 0 {
        return -EINVAL;
    }
    let Some(setup) = setup_fn else {
        return -EINVAL;
    };
    let Some(wait_queue) = wait_queue_fn else {
        return -EINVAL;
    };
    let Some(unqueue) = unqueue_fn else {
        return -EINVAL;
    };
    let Some(has_signal) = has_signal_fn else {
        return -EINVAL;
    };
    let Some(put_key) = put_key_fn else {
        return -EINVAL;
    };
    let Some(log) = log_fn else {
        return -EINVAL;
    };

    if futex_wake_bitset_valid_result(bitset) == 0 {
        return -EINVAL;
    }

    unsafe {
        futex_wait_prepare_q_result(
            q_addr,
            q_bitset_offset,
            q_requeue_pi_key_offset,
            q_uti_futex_resp_offset,
            bitset,
            uti_futex_resp,
        );
    }
    let tid = unsafe { read_cint_field(thread_addr, thread_tid_offset) };

    loop {
        let mut hb_addr = 0usize;
        let ret = unsafe { setup(uaddr, val, fshared, q_addr, (&raw mut hb_addr) as usize) };
        if ret != 0 {
            unsafe {
                log(FUTEX_WAIT_LOG_SETUP_RET, thread_addr, tid, ret);
            }
            return ret;
        }

        let time_remain = unsafe { wait_queue(hb_addr, q_addr, timeout) };
        let unqueued = unsafe { unqueue(q_addr) };
        let mut has_pending_signal = 0;
        if unqueued != 0 && !(timeout != 0 && time_remain == 0) {
            has_pending_signal = unsafe { has_signal(thread_addr) };
        }
        let post_action = futex_wait_post_action_result(
            unqueued,
            timeout,
            time_remain,
            has_pending_signal,
            (time_remain == -ERESTARTSYS) as CInt,
        );
        if post_action == FUTEX_WAIT_POST_SUCCESS {
            unsafe {
                log(FUTEX_WAIT_LOG_SUCCESS, thread_addr, tid, 0);
                put_key(fshared, q_addr.wrapping_add(q_key_offset));
            }
            return 0;
        }
        if post_action == FUTEX_WAIT_POST_TIMEOUT {
            let ret = -ETIMEDOUT;
            unsafe {
                log(FUTEX_WAIT_LOG_TIMEOUT, thread_addr, tid, ret);
                put_key(fshared, q_addr.wrapping_add(q_key_offset));
            }
            return ret;
        }
        if post_action == FUTEX_WAIT_POST_INTERRUPT {
            let ret = -EINTR;
            unsafe {
                log(FUTEX_WAIT_LOG_INTERRUPT, thread_addr, tid, ret);
                put_key(fshared, q_addr.wrapping_add(q_key_offset));
            }
            return ret;
        }

        unsafe {
            put_key(fshared, q_addr.wrapping_add(q_key_offset));
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_wait_entry_result(
    uaddr: usize,
    fshared: CInt,
    val: u32,
    timeout: u64,
    bitset: u32,
    q_addr: usize,
    thread_addr: usize,
    uti_futex_resp: usize,
    profile_enabled: CInt,
    thread_profile_offset: usize,
    thread_profile_start_ts_offset: usize,
    thread_profile_elapsed_ts_offset: usize,
    timestamp_fn: Option<FutexWaitTimestampFn>,
    wait_body_fn: Option<FutexWaitBodyEntryFn>,
) -> CInt {
    if q_addr == 0 || thread_addr == 0 {
        return -EINVAL;
    }
    let Some(wait_body) = wait_body_fn else {
        return -EINVAL;
    };
    let timestamp = if profile_enabled != 0 {
        let Some(timestamp) = timestamp_fn else {
            return -EINVAL;
        };
        Some(timestamp)
    } else {
        None
    };

    if futex_wake_bitset_valid_result(bitset) == 0 {
        return -EINVAL;
    }

    if let Some(timestamp) = timestamp {
        let profile = unsafe {
            read_volatile(thread_addr.wrapping_add(thread_profile_offset) as *const CInt)
        };
        let start_addr = thread_addr.wrapping_add(thread_profile_start_ts_offset);
        let start = unsafe { read_volatile(start_addr as *const usize) };
        if profile != 0 && start != 0 {
            let now = unsafe { timestamp() };
            let elapsed_addr = thread_addr.wrapping_add(thread_profile_elapsed_ts_offset);
            let elapsed = unsafe { read_volatile(elapsed_addr as *const usize) };
            unsafe {
                write_volatile(
                    elapsed_addr as *mut usize,
                    elapsed.wrapping_add(now.wrapping_sub(start)),
                );
                write_volatile(start_addr as *mut usize, 0);
            }
        }
    }

    let ret = unsafe {
        wait_body(
            uaddr,
            fshared,
            val,
            timeout,
            bitset,
            q_addr,
            thread_addr,
            uti_futex_resp,
        )
    };

    if let Some(timestamp) = timestamp {
        let profile = unsafe {
            read_volatile(thread_addr.wrapping_add(thread_profile_offset) as *const CInt)
        };
        if profile != 0 {
            let now = unsafe { timestamp() };
            unsafe {
                write_volatile(
                    thread_addr.wrapping_add(thread_profile_start_ts_offset) as *mut usize,
                    now,
                );
            }
        }
    }

    ret
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
