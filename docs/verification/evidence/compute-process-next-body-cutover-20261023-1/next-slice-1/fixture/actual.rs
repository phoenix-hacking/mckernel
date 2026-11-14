#![no_std]
use core::ptr::{read_volatile,write_volatile};
use core::mem::offset_of;
type CInt=i32; type CULong=u64;
#[repr(C)] pub struct List { pub next:*mut List, pub prev:*mut List }
#[repr(C)] pub struct Thread {
 pub cpu_id:i32,pub tid:i32,pub status:i32,pub spin_sleep_lock:u64,pub spin_sleep:i32,
 pub sched_list:List,pub sigpending:List,pub sigcommon:*mut SigCommon,pub proc:*mut Process,pub mod_clone:i32,
}
#[repr(C)] pub struct SigCommon { pub sigpending:List }
#[repr(C)] pub struct Process { pub pid:i32,pub status:i32,pub update_lock:u64,pub clone_count:i32 }
#[repr(C)] pub struct CpuLocalVar {
 pub runq_lock:u64,pub runq_irqstate:u64,pub current:*mut Thread,pub prevpid:i32,pub runq:List,
 pub runq_len:usize,pub runq_reserved:i32,pub flags:u32,pub status:i32,pub in_interrupt:i32,pub nr_ctx_switches:u64,
}
type SchedMigrateSpinLockFn = unsafe extern "C" fn(usize) -> CULong;
type SchedMigrateSpinUnlockFn = unsafe extern "C" fn(usize, CULong);
type SchedMigrateNoirqLockFn = unsafe extern "C" fn(usize);
type SchedMigrateNoirqUnlockFn = unsafe extern "C" fn(usize);
type SchedMigrateVoidFn = unsafe extern "C" fn();
type SchedRunqLogFn = unsafe extern "C" fn(CInt, usize, usize, CInt, CInt);
type SchedRunqIrqSaveFn = unsafe extern "C" fn() -> CULong;
type SchedRunqIrqRestoreFn = unsafe extern "C" fn(CULong);
type SchedRunqHasSignalFn = unsafe extern "C" fn(usize) -> CInt;
const EINVAL: CInt = 22;
const CPU_FLAG_NEED_RESCHED: u32 = 0x1;
const SCHED_RUNQ_LOG_IDLE_HALT: CInt = 6;
const SCHED_RUNQ_LOG_LOST_WAKEUP: CInt = 7;
const SCHED_RUNQ_LOG_SPIN_WOKEN: CInt = 8;
const SCHED_RUNQ_LOG_SLEEP_WOKEN: CInt = 9;
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
unsafe extern "C" {
 fn get_this_cpu_local_var()->*mut CpuLocalVar;
 fn ihk_mc_get_processor_id()->CInt;
 fn process_sched_irq_save_bridge()->CULong;
 fn process_sched_schedule_bridge();
 fn process_sched_runq_log_bridge(event:CInt,arg0:usize,arg1:usize,arg2:CInt,arg3:CInt);
 #[link_name="process_spin_lock_bridge"] fn process_spin_lock_bridge_c(p:CULong)->CULong;
 #[link_name="process_spin_unlock_bridge"] fn process_spin_unlock_bridge_c(p:CULong,s:CULong);
 #[link_name="process_sched_noirq_lock_bridge"] fn process_sched_noirq_lock_bridge_c(p:CULong);
 #[link_name="process_sched_noirq_unlock_bridge"] fn process_sched_noirq_unlock_bridge_c(p:CULong);
    static mut idle_halt: CInt;
    fn process_sched_irq_restore_bridge(irqstate: CULong);
    fn process_sched_zero_free_bridge();
    fn process_sched_pause_bridge();
    fn process_sched_has_signal_bridge(thread_addr: usize) -> CInt;
 fn sched_spin_sleep_or_schedule_body_result(thread:usize,cpu:usize,id:CInt,halt:CInt,need:u32,
 offsets:*const SchedRunqueueOffsets,irq:Option<SchedRunqIrqSaveFn>,restore:Option<SchedRunqIrqRestoreFn>,
 lock:Option<SchedMigrateSpinLockFn>,unlock:Option<SchedMigrateSpinUnlockFn>,nl:Option<SchedMigrateNoirqLockFn>,nu:Option<SchedMigrateNoirqUnlockFn>,
 schedule:Option<SchedMigrateVoidFn>,zero:Option<SchedMigrateVoidFn>,pause:Option<SchedMigrateVoidFn>,signal:Option<SchedRunqHasSignalFn>,log:Option<SchedRunqLogFn>)->CInt;
}
/// Current-CPU spin-sleep boundary; preserve the existing timer/scheduler body.
///
/// # Safety
/// A wait/futex queue is already installed and the current thread's spin_sleep
/// marker is set before testing its wait condition. The caller preserves the
/// original current-CPU/IRQ lifetime contract. The existing shared ABI supplies
/// current and the stack-local immutable offset table; the body does not retain
/// either the table or callback pointers. No lock or pointer ownership transfers.
#[no_mangle]
pub unsafe extern "C" fn spin_sleep_or_schedule() {
    let thread = unsafe { (*get_this_cpu_local_var()).current };
    let cpu = unsafe { get_this_cpu_local_var() };
    // The live LWK ihk/ikc/include/ikc/ihk.h maps ihk_ikc_get_processor_id
    // directly to ihk_mc_get_processor_id.
    let current_cpu_id = unsafe { ihk_mc_get_processor_id() };
    let halt = unsafe { core::ptr::read(core::ptr::addr_of!(idle_halt)) };
    let offsets = sched_runqueue_offsets();
    let _ = unsafe {
        sched_spin_sleep_or_schedule_body_result(
            thread as usize, cpu as usize, current_cpu_id, halt,
            CPU_FLAG_NEED_RESCHED, &offsets,
            Some(process_sched_irq_save_bridge),
            Some(process_sched_irq_restore_bridge),
            Some(sched_process_spin_lock_bridge),
            Some(sched_process_spin_unlock_bridge),
            Some(sched_process_noirq_lock_bridge),
            Some(sched_process_noirq_unlock_bridge),
            Some(process_sched_schedule_bridge),
            Some(process_sched_zero_free_bridge),
            Some(process_sched_pause_bridge),
            Some(process_sched_has_signal_bridge),
            Some(process_sched_runq_log_bridge),
        )
    };
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
unsafe fn list_next(list_addr: usize) -> usize {
    unsafe { read_volatile(list_addr as *const usize) }
}
unsafe fn list_empty_addr(list_addr: usize) -> bool {
    unsafe { list_next(list_addr) == list_addr }
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
#[no_mangle]
pub unsafe extern "C" fn leaf_spin_sleep_or_schedule_body_result(
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
unsafe extern "C" fn futex_wait_schedule_direct_bridge() {
    unsafe {
        spin_sleep_or_schedule();
    }
}
