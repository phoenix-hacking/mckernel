#![no_std]
#![allow(dead_code)]
#[path="actual_abi.rs"] mod abi;
#[path="actual_waitq_entry.rs"] mod waitq;
use abi::{AbiListHead,CInt,CULong,CpuLocalVar,Thread,Waitq};
use core::mem::{offset_of,MaybeUninit};
use core::ptr::{read_volatile,write_volatile};
const EINVAL:CInt=22; const PS_UNINTERRUPTIBLE:CInt=0x4;
const CPU_FLAG_NEED_RESCHED:u32=1;const CPU_FLAG_NEED_MIGRATE:u32=2;
const CPU_STATUS_RUNNING:CInt=2;const IHK_GV_IKC:CInt=1;
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
unsafe extern "C" {
 fn get_this_cpu_local_var()->*mut CpuLocalVar;
 fn ihk_mc_get_processor_id()->CInt;
 fn process_sched_cpu_local_bridge(cpu_id:CInt)->usize;
 #[link_name="process_spin_lock_bridge"] fn process_spin_lock_bridge_c(lock_addr:CULong)->CULong;
 #[link_name="process_spin_unlock_bridge"] fn process_spin_unlock_bridge_c(lock_addr:CULong,irqstate:CULong);
 #[link_name="process_sched_noirq_lock_bridge"] fn process_sched_noirq_lock_bridge_c(lock_addr:CULong);
 #[link_name="process_sched_noirq_unlock_bridge"] fn process_sched_noirq_unlock_bridge_c(lock_addr:CULong);
 fn process_sched_vector_bridge(vector_key:CInt)->CInt;
 fn process_sched_interrupt_bridge(cpu:CInt,vector:CInt);
 fn process_sched_schedule_bridge();
    fn process_sched_waitq_init_bridge(waitq_addr: usize);
    fn process_sched_waitq_prepare_bridge(waitq_addr: usize, entry_addr: usize, status: CInt);
    fn process_sched_waitq_finish_bridge(waitq_addr: usize, entry_addr: usize);
    fn process_sched_migrate_log_bridge(thread_addr: usize, tid: CInt, cpu_id: CInt);
 fn sched_request_migrate_body_result(
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
) -> CInt;
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
unsafe fn list_prev_addr(list_addr: usize) -> usize {
    unsafe { read_volatile(list_addr.wrapping_add(core::mem::size_of::<usize>()) as *const usize) }
}
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
/// Publish a stack-local migration request using the existing scheduler body.
///
/// # Safety
/// The caller preserves the existing scheduler/current-CPU contract and supplies
/// a live thread and CPU. As in the C wrapper, schedule completes the request
/// before returning; waitq_finish then detaches the entry before either stack
/// object expires. The body acquires migq_lock before runq_lock and retains it
/// through target notification. Callbacks must not retain the offset table.
#[no_mangle]
pub unsafe extern "C" fn sched_request_migrate(cpu_id: CInt, thread: *mut Thread) {
    let cpu = unsafe { process_sched_cpu_local_bridge(cpu_id) };
    let mut request = MaybeUninit::<SchedMigrateRequest>::uninit();
    let mut entry = MaybeUninit::<crate::waitq::WaitqEntry>::uninit();
    unsafe {
        crate::waitq::waitq_init_locked_entry(
            entry.as_mut_ptr(), (*get_this_cpu_local_var()).current.cast(),
        );
    }
    let current_cpu_id = unsafe { ihk_mc_get_processor_id() };
    let offsets = SchedMigrateOffsets {
        req_list_offset: offset_of!(SchedMigrateRequest, list),
        req_thread_offset: offset_of!(SchedMigrateRequest, thread),
        req_wq_offset: offset_of!(SchedMigrateRequest, wq),
        thread_cpu_id_offset: offset_of!(Thread, cpu_id),
        thread_tid_offset: offset_of!(Thread, tid),
        cpu_migq_lock_offset: offset_of!(CpuLocalVar, migq_lock),
        cpu_migq_offset: offset_of!(CpuLocalVar, migq),
        cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
        cpu_flags_offset: offset_of!(CpuLocalVar, flags),
        cpu_status_offset: offset_of!(CpuLocalVar, status),
    };
    let _ = unsafe {
        sched_request_migrate_body_result(
            cpu_id, cpu, request.as_mut_ptr() as usize, entry.as_mut_ptr() as usize,
            thread as usize, current_cpu_id, PS_UNINTERRUPTIBLE, CPU_FLAG_NEED_RESCHED,
            CPU_FLAG_NEED_MIGRATE, CPU_STATUS_RUNNING, IHK_GV_IKC, &offsets,
            Some(sched_process_spin_lock_bridge),
            Some(sched_process_spin_unlock_bridge),
            Some(sched_process_noirq_lock_bridge),
            Some(sched_process_noirq_unlock_bridge),
            Some(process_sched_waitq_init_bridge),
            Some(process_sched_waitq_prepare_bridge),
            Some(process_sched_waitq_finish_bridge),
            Some(process_sched_vector_bridge), Some(process_sched_interrupt_bridge),
            Some(process_sched_schedule_bridge), Some(process_sched_migrate_log_bridge),
        )
    };
}

#[no_mangle]
pub unsafe extern "C" fn leaf_sched_request_migrate_body_result(
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

#[no_mangle]
pub static LEAF_REQUEST_LAYOUT:[usize;12]=[
 offset_of!(SchedMigrateRequest,list),offset_of!(SchedMigrateRequest,thread),offset_of!(SchedMigrateRequest,wq),
 offset_of!(Thread,cpu_id),offset_of!(Thread,tid),offset_of!(CpuLocalVar,migq_lock),offset_of!(CpuLocalVar,migq),
 offset_of!(CpuLocalVar,runq_lock),offset_of!(CpuLocalVar,flags),offset_of!(CpuLocalVar,status),
 core::mem::size_of::<SchedMigrateRequest>(),core::mem::align_of::<SchedMigrateRequest>()];
