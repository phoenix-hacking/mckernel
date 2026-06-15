use core::{
    ffi::c_char,
    mem::offset_of,
    ptr::null_mut,
    sync::atomic::{AtomicI32, Ordering},
};

use crate::abi::{
    AbiListHead, CInt, CLong, CULong, CpuLocalVar, IhkSpinlock, Thread, TimeSpec, TimeVal, Timer,
    Waitq,
};
use crate::page_alloc::IhkMcNumaNode;
use crate::sched_helpers::TimerRuntimeOffsets;

const LOOP_TIMEOUT: u64 = 500;
const NS_PER_SEC: CLong = 1_000_000_000;
const US_PER_SEC: CLong = 1_000_000;
const WAKE_LOOP_PANIC: &[u8] = b"wake_timers_loop: helper failed\0";

extern "C" {
    fn ihk_mc_spinlock_init(lock: *mut IhkSpinlock);
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, irqstate: CULong);
    fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock);
    fn __ihk_mc_spinlock_unlock_noirq(lock: *mut IhkSpinlock);
    fn ihk_mc_get_processor_id() -> CInt;
    fn get_cpu_local_var(id: CInt) -> *mut CpuLocalVar;
    fn schedule();
    fn ihk_mc_get_numa_node_by_distance(i: CInt) -> *mut IhkMcNumaNode;
    fn ihk_numa_zero_free_pages(node: *mut IhkMcNumaNode);
    fn cpu_pause();
    fn waitq_wakeup(waitq: *mut Waitq);
    #[link_name = "panic"]
    fn kernel_panic(message: *const c_char) -> !;
}

#[no_mangle]
pub static mut timers: AbiListHead = AbiListHead {
    next: null_mut(),
    prev: null_mut(),
};

#[no_mangle]
pub static mut timers_lock: IhkSpinlock = IhkSpinlock { head_tail: 0 };

static TIMER_RUNTIME_OFFSETS: TimerRuntimeOffsets = TimerRuntimeOffsets {
    thread_status_offset: offset_of!(Thread, status),
    thread_sched_list_offset: offset_of!(Thread, sched_list),
    thread_spin_sleep_lock_offset: offset_of!(Thread, spin_sleep_lock),
    thread_spin_sleep_offset: offset_of!(Thread, spin_sleep),
    thread_itimer_enabled_offset: offset_of!(Thread, itimer_enabled),
    cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
    cpu_runq_offset: offset_of!(CpuLocalVar, runq),
    cpu_runq_len_offset: offset_of!(CpuLocalVar, runq_len),
    cpu_current_offset: offset_of!(CpuLocalVar, current),
    cpu_timer_enabled_offset: offset_of!(CpuLocalVar, timer_enabled),
    cpu_backlog_list_offset: offset_of!(CpuLocalVar, backlog_list),
    timer_timeout_offset: offset_of!(Timer, timeout),
    timer_waitq_offset: offset_of!(Timer, processes),
    timer_list_offset: offset_of!(Timer, list),
    timer_thread_offset: offset_of!(Timer, thread),
};

#[no_mangle]
pub unsafe extern "C" fn ts_add(ats: *mut TimeSpec, bts: *const TimeSpec) {
    unsafe {
        (*ats).tv_sec = (*ats).tv_sec.wrapping_add((*bts).tv_sec);
        (*ats).tv_nsec = (*ats).tv_nsec.wrapping_add((*bts).tv_nsec);
        while (*ats).tv_nsec >= NS_PER_SEC {
            (*ats).tv_sec = (*ats).tv_sec.wrapping_add(1);
            (*ats).tv_nsec = (*ats).tv_nsec.wrapping_sub(NS_PER_SEC);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ts_sub(ats: *mut TimeSpec, bts: *const TimeSpec) {
    unsafe {
        (*ats).tv_sec = (*ats).tv_sec.wrapping_sub((*bts).tv_sec);
        (*ats).tv_nsec = (*ats).tv_nsec.wrapping_sub((*bts).tv_nsec);
        while (*ats).tv_nsec < 0 {
            (*ats).tv_sec = (*ats).tv_sec.wrapping_sub(1);
            (*ats).tv_nsec = (*ats).tv_nsec.wrapping_add(NS_PER_SEC);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn tv_add(ats: *mut TimeVal, bts: *const TimeVal) {
    unsafe {
        (*ats).tv_sec = (*ats).tv_sec.wrapping_add((*bts).tv_sec);
        (*ats).tv_usec = (*ats).tv_usec.wrapping_add((*bts).tv_usec);
        while (*ats).tv_usec >= US_PER_SEC {
            (*ats).tv_sec = (*ats).tv_sec.wrapping_add(1);
            (*ats).tv_usec = (*ats).tv_usec.wrapping_sub(US_PER_SEC);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn tv_sub(ats: *mut TimeVal, bts: *const TimeVal) {
    unsafe {
        (*ats).tv_sec = (*ats).tv_sec.wrapping_sub((*bts).tv_sec);
        (*ats).tv_usec = (*ats).tv_usec.wrapping_sub((*bts).tv_usec);
        while (*ats).tv_usec < 0 {
            (*ats).tv_sec = (*ats).tv_sec.wrapping_sub(1);
            (*ats).tv_usec = (*ats).tv_usec.wrapping_add(US_PER_SEC);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn tv_to_ts(ats: *mut TimeSpec, bts: *const TimeVal) {
    unsafe {
        (*ats).tv_sec = (*bts).tv_sec;
        (*ats).tv_nsec = (*bts).tv_usec.wrapping_mul(1000);
    }
}

#[no_mangle]
pub unsafe extern "C" fn ts_to_tv(ats: *mut TimeVal, bts: *const TimeSpec) {
    unsafe {
        (*ats).tv_sec = (*bts).tv_sec;
        (*ats).tv_usec = (*bts).tv_nsec / 1000;
    }
}

unsafe extern "C" fn timer_spin_init_bridge(lock_addr: usize) {
    unsafe {
        ihk_mc_spinlock_init(lock_addr as *mut IhkSpinlock);
    }
}

unsafe extern "C" fn timer_spin_lock_bridge(lock_addr: usize) -> CULong {
    unsafe { __ihk_mc_spinlock_lock(lock_addr as *mut IhkSpinlock) }
}

unsafe extern "C" fn timer_spin_unlock_bridge(lock_addr: usize, irqstate: CULong) {
    unsafe {
        __ihk_mc_spinlock_unlock(lock_addr as *mut IhkSpinlock, irqstate);
    }
}

unsafe extern "C" fn timer_spin_lock_noirq_bridge(lock_addr: usize) -> CULong {
    unsafe {
        __ihk_mc_spinlock_lock_noirq(lock_addr as *mut IhkSpinlock);
    }
    0
}

unsafe extern "C" fn timer_spin_unlock_noirq_bridge(lock_addr: usize, _irqstate: CULong) {
    unsafe {
        __ihk_mc_spinlock_unlock_noirq(lock_addr as *mut IhkSpinlock);
    }
}

unsafe extern "C" fn timer_rdtsc_bridge() -> u64 {
    let low: u32;
    let high: u32;

    unsafe {
        core::arch::asm!(
            "rdtsc",
            out("eax") low,
            out("edx") high,
            options(nomem, nostack, preserves_flags)
        );
    }
    ((high as u64) << 32) | (low as u64)
}

unsafe extern "C" fn timer_set_status_bridge(status_addr: usize, status: CInt) {
    unsafe {
        AtomicI32::from_ptr(status_addr as *mut CInt).swap(status, Ordering::SeqCst);
    }
}

unsafe extern "C" fn timer_schedule_bridge() {
    unsafe {
        schedule();
    }
}

unsafe extern "C" fn timer_zero_free_bridge() {
    unsafe {
        ihk_numa_zero_free_pages(ihk_mc_get_numa_node_by_distance(0));
    }
}

unsafe extern "C" fn timer_pause_bridge() {
    unsafe {
        cpu_pause();
    }
}

unsafe extern "C" fn timer_waitq_wakeup_bridge(waitq_addr: usize) {
    unsafe {
        waitq_wakeup(waitq_addr as *mut Waitq);
    }
}

unsafe extern "C" fn timer_log_wake_bridge(_timer_addr: usize, _thread_addr: usize) {}

#[no_mangle]
pub unsafe extern "C" fn init_timers() {
    unsafe {
        crate::sched_helpers::timer_init_timers_result(
            &raw mut timers_lock as usize,
            &raw mut timers as usize,
            Some(timer_spin_init_bridge),
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn schedule_timeout(timeout: u64) -> u64 {
    let cpu_local = unsafe { get_cpu_local_var(ihk_mc_get_processor_id()) };
    let thread = unsafe { (*cpu_local).current };

    unsafe {
        crate::sched_helpers::timer_schedule_timeout_body_result(
            thread as usize,
            cpu_local as usize,
            timeout,
            LOOP_TIMEOUT,
            &TIMER_RUNTIME_OFFSETS,
            Some(timer_rdtsc_bridge),
            Some(timer_spin_lock_bridge),
            Some(timer_spin_unlock_bridge),
            Some(timer_set_status_bridge),
            Some(timer_schedule_bridge),
            Some(timer_zero_free_bridge),
            Some(timer_pause_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn wake_timers_loop() {
    let ret = unsafe {
        crate::sched_helpers::timer_wake_loop_body_result(
            &raw mut timers_lock as usize,
            &raw mut timers as usize,
            LOOP_TIMEOUT,
            0,
            &TIMER_RUNTIME_OFFSETS,
            Some(timer_rdtsc_bridge),
            Some(timer_pause_bridge),
            Some(timer_spin_lock_noirq_bridge),
            Some(timer_spin_unlock_noirq_bridge),
            Some(timer_waitq_wakeup_bridge),
            Some(timer_log_wake_bridge),
        )
    };
    if ret < 0 {
        unsafe {
            kernel_panic(WAKE_LOOP_PANIC.as_ptr().cast());
        }
    }
}
