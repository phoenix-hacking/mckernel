#![no_std]
// Exact finite accepted-F02 general wakeup wrapper+engine partition; source/codegen only.
// Genuine downstream lock/status/timer/vector/CPU/log providers remain external.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod sched_helpers {
use core::mem::{offset_of, MaybeUninit};
use core::ptr::{read_volatile, write_volatile};
use crate::abi::{CInt, CULong, CpuLocalVar, Process, SigCommon, Thread};

unsafe extern "C" {
    fn process_sched_cpu_local_bridge(cpu_id: CInt) -> usize;
    fn ihk_mc_get_processor_id() -> CInt;
    #[link_name = "process_spin_lock_bridge"]
    fn process_spin_lock_bridge_c(lock_addr: CULong) -> CULong;
    #[link_name = "process_spin_unlock_bridge"]
    fn process_spin_unlock_bridge_c(lock_addr: CULong, irqstate: CULong);
    fn process_sched_rwlock_bridge(lock_addr: usize, node_addr: usize);
    fn process_sched_rwunlock_bridge(lock_addr: usize, node_addr: usize);
    fn process_sched_status_set_bridge(status_addr: usize, status: CInt);
    fn process_sched_set_timer_bridge(runq_locked: CInt);
    fn process_sched_vector_bridge(vector_key: CInt) -> CInt;
    fn process_sched_interrupt_bridge(cpu: CInt, vector: CInt);
    fn process_sched_runq_log_bridge(event: CInt, arg0: usize, arg1: usize, arg2: CInt, arg3: CInt);
}

type SchedMigrateSpinLockFn = unsafe extern "C" fn(usize) -> CULong;
type SchedMigrateSpinUnlockFn = unsafe extern "C" fn(usize, CULong);
type SchedRunqRwlockFn = unsafe extern "C" fn(usize, usize);
type SchedRunqStatusSetFn = unsafe extern "C" fn(usize, CInt);
type SchedRunqSetTimerFn = unsafe extern "C" fn(CInt);
type SchedMigrateVectorFn = unsafe extern "C" fn(CInt) -> CInt;
type SchedMigrateInterruptFn = unsafe extern "C" fn(CInt, CInt);
type SchedRunqLogFn = unsafe extern "C" fn(CInt, usize, usize, CInt, CInt);

const EINVAL: CInt = 22;
const PS_RUNNING: CInt = 0x1;
const PS_EXITED: CInt = 0x10;
const CPU_FLAG_NEED_RESCHED: u32 = 0x1;
const IHK_GV_IKC: CInt = 1;
const SCHED_RUNQ_LOG_WAKE_ENTRY: CInt = 2;
const SCHED_RUNQ_LOG_SPIN_WAKEUP: CInt = 3;
const SCHED_RUNQ_LOG_REMOTE_IPI: CInt = 4;

#[repr(C, align(64))]
struct McsRwlockNode {
    count: CInt,
    type_: u8,
    locked: u8,
    dmy1: u8,
    dmy2: u8,
    next: *mut McsRwlockNode,
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

const _: () = {
    assert!(core::mem::size_of::<SchedRunqueueOffsets>() == 208);
    assert!(core::mem::align_of::<SchedRunqueueOffsets>() == 8);
};

unsafe extern "C" fn sched_process_spin_lock_bridge(lock_addr: usize) -> CULong {
    unsafe { process_spin_lock_bridge_c(lock_addr as CULong) }
}

unsafe extern "C" fn sched_process_spin_unlock_bridge(lock_addr: usize, irqstate: CULong) {
    unsafe { process_spin_unlock_bridge_c(lock_addr as CULong, irqstate) }
}

const fn sched_runqueue_offsets() -> SchedRunqueueOffsets {
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

#[no_mangle]
pub unsafe extern "C" fn __sched_wakeup_thread(
    thread: *mut Thread,
    valid_states: CInt,
    runq_locked: CInt,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let cpu_addr = unsafe { process_sched_cpu_local_bridge((*thread).cpu_id) };
    let mut updatelock = MaybeUninit::<McsRwlockNode>::uninit();
    let offsets = sched_runqueue_offsets();
    unsafe {
        sched_wakeup_thread_body_result(
            thread as usize,
            cpu_addr,
            updatelock.as_mut_ptr() as usize,
            ihk_mc_get_processor_id(),
            valid_states,
            runq_locked,
            PS_RUNNING,
            PS_EXITED,
            CPU_FLAG_NEED_RESCHED,
            IHK_GV_IKC,
            &offsets,
            Some(sched_process_spin_lock_bridge),
            Some(sched_process_spin_unlock_bridge),
            Some(process_sched_rwlock_bridge),
            Some(process_sched_rwunlock_bridge),
            Some(process_sched_status_set_bridge),
            Some(process_sched_set_timer_bridge),
            Some(process_sched_vector_bridge),
            Some(process_sched_interrupt_bridge),
            Some(process_sched_runq_log_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn sched_wakeup_thread(thread: *mut Thread, valid_states: CInt) -> CInt {
    unsafe { __sched_wakeup_thread(thread, valid_states, 0) }
}
}
