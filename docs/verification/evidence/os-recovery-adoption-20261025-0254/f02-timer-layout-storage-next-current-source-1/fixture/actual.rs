// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] pub mod abi;
mod sched_helpers {
 use core::ptr::{read_volatile, write_volatile};
 use crate::abi::{CInt,CULong,CpuLocalVar};
 const EINVAL:CInt=22;
 const PS_RUNNING:CInt=1;
type TimerSpinLockFn = unsafe extern "C" fn(usize) -> CULong;
type TimerSpinUnlockFn = unsafe extern "C" fn(usize, CULong);
type TimerLapicEnableFn = unsafe extern "C" fn(u32);
type TimerLapicDisableFn = unsafe extern "C" fn();
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
unsafe extern "C" {
 fn get_this_cpu_local_var()->*mut CpuLocalVar;
 static mut time_sharing:CInt;
 static process_timer_runtime_offsets:TimerRuntimeOffsets;
 fn process_timer_spin_lock_bridge(lock_addr:usize)->CULong;
 fn process_timer_spin_unlock_bridge(lock_addr:usize,irqstate:CULong);
 fn process_timer_lapic_enable_bridge(clocks:u32);
 fn process_timer_lapic_disable_bridge();
 fn timer_set_timer_body_result(cpu:usize,sharing:CInt,locked:CInt,
  offsets:*const TimerRuntimeOffsets,lock:Option<TimerSpinLockFn>,
  unlock:Option<TimerSpinUnlockFn>,enable:Option<TimerLapicEnableFn>,
  disable:Option<TimerLapicDisableFn>)->CInt;
}
#[no_mangle]
pub unsafe extern "C" fn set_timer(runq_locked: CInt) {
    let v = unsafe { get_this_cpu_local_var() };
    let sharing = unsafe { core::ptr::read(core::ptr::addr_of!(time_sharing)) };
    let _ = unsafe {
        timer_set_timer_body_result(
            v as usize,
            sharing,
            runq_locked,
            core::ptr::addr_of!(process_timer_runtime_offsets),
            Some(process_timer_spin_lock_bridge),
            Some(process_timer_spin_unlock_bridge),
            Some(process_timer_lapic_enable_bridge),
            Some(process_timer_lapic_disable_bridge),
        )
    };
}
unsafe fn list_next(list_addr: usize) -> usize {
    unsafe { read_volatile(list_addr as *const usize) }
}
unsafe fn list_empty_addr(list_addr: usize) -> bool {
    unsafe { list_next(list_addr) == list_addr }
}
#[no_mangle]
pub unsafe extern "C" fn leaf_timer_set_timer_body_result(
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
}

include!("timer_layout_storage.ACTUAL.rs.inc");
