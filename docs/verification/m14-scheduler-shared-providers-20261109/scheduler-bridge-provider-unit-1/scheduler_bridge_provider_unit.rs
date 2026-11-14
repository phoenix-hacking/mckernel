#![no_std]
// Finite accepted-F02 scheduler bridges and complete existing guarded runqueue logger.
// All lock/vector/timer/IRQ/metadata providers remain genuine unresolved declarations.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod debug {
#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};
    assert!(size_of::<Ddebug>() == 32);
    assert!(align_of::<Ddebug>() == 8);
    assert!(offset_of!(Ddebug, line_flags) == 24);
};
}

mod process_helpers {
use core::ffi::c_void;
use crate::abi::{CInt, CULong, CpuLocalVar, IhkSpinlock, McsRwlockLock};

unsafe extern "C" {
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
    fn __mcs_rwlock_writer_lock_noirq(lock: *mut McsRwlockLock, node: *mut c_void);
    fn __mcs_rwlock_writer_unlock_noirq(lock: *mut McsRwlockLock, node: *mut c_void);
    fn get_cpu_local_var(cpu_id: CInt) -> *mut CpuLocalVar;
    fn xchg4(ptr: *mut CInt, value: CInt) -> CInt;
    fn set_timer(runq_locked: CInt);
    fn ihk_mc_get_vector(vector_key: CInt) -> CInt;
    fn ihk_mc_interrupt_cpu(cpu: CInt, vector: CInt) -> CInt;
    fn kprintf(format: *const i8, ...) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_lock_bridge(lock_addr: CULong) -> CULong {
    __ihk_mc_spinlock_lock(lock_addr as *mut IhkSpinlock)
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_unlock_bridge(lock_addr: CULong, irqstate: CULong) {
    __ihk_mc_spinlock_unlock(lock_addr as *mut IhkSpinlock, irqstate);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_rwlock_bridge(lock_addr: CULong, node_addr: CULong) {
    __mcs_rwlock_writer_lock_noirq(lock_addr as *mut McsRwlockLock, node_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_rwunlock_bridge(lock_addr: CULong, node_addr: CULong) {
    __mcs_rwlock_writer_unlock_noirq(lock_addr as *mut McsRwlockLock, node_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_cpu_local_bridge(cpu_id: CInt) -> CULong {
    get_cpu_local_var(cpu_id) as CULong
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_status_set_bridge(status_addr: CULong, status: CInt) {
    xchg4(status_addr as *mut CInt, status);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_vector_bridge(vector_key: CInt) -> CInt {
    ihk_mc_get_vector(vector_key)
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_interrupt_bridge(cpu: CInt, vector: CInt) {
    ihk_mc_interrupt_cpu(cpu, vector);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_set_timer_bridge(runq_locked: CInt) {
    set_timer(runq_locked);
}

mod remaining_process_range_scheduler_logs {
    use core::ptr::{addr_of, addr_of_mut, read_volatile};
    use crate::abi::{CInt, CULong, Thread};
    use crate::debug::Ddebug;

    unsafe extern "C" {
        static mut process_remaining_range_scheduler_debug: [Ddebug; 18];
    }

    unsafe fn enabled(index: usize) -> bool {
        // SAFETY: The retained 18-entry metadata array is live for the kernel
        // lifetime; selectors use the existing volatile dynamic-debug boundary.
        unsafe {
            let descriptor = addr_of_mut!(process_remaining_range_scheduler_debug)
                .cast::<Ddebug>().add(index);
            read_volatile(addr_of!((*descriptor).line_flags)) >> 24 != 0
        }
    }

    #[no_mangle]
    pub unsafe extern "C" fn process_sched_runq_log_bridge(
        event: CInt, arg0: CULong, _arg1: CULong, arg2: CInt, arg3: CInt,
    ) {
        // SAFETY: All formats are static. Only the enabled wake-entry event
        // dereferences arg0, under the caller's original Thread lifetime.
        unsafe { match event {
            1 => { let _ = super::kprintf(b"no migration in IRQ context\n\0".as_ptr().cast()); }
            2 if enabled(8) => {
                let thread = arg0 as *const Thread;
                let _ = super::kprintf(
                    b"%s: proc->pid=%d, valid_states=%08x, proc->status=%08x, proc->cpu_id=%d,my cpu_id=%d\n\0".as_ptr().cast(),
                    b"__sched_wakeup_thread\0".as_ptr().cast::<i8>(), arg2, arg3,
                    (*thread).status, (*thread).cpu_id, super::ihk_mc_get_processor_id(),
                );
            }
            3 if enabled(9) => { let _ = super::kprintf(
                b"%s: spin wakeup: cpu_id: %d\n\0".as_ptr().cast(),
                b"__sched_wakeup_thread\0".as_ptr().cast::<i8>(), arg2,
            ); }
            4 if enabled(10) => { let _ = super::kprintf(
                b"%s: issuing IPI, thread->cpu_id=%d\n\0".as_ptr().cast(),
                b"__sched_wakeup_thread\0".as_ptr().cast::<i8>(), arg2,
            ); }
            5 if enabled(11) => { let _ = super::kprintf(
                b"runq_add_proc(): tid %d added to CPU[%d]'s runq\n\0".as_ptr().cast(), arg2, arg3,
            ); }
            6 if enabled(12) => { let _ = super::kprintf(
                b"%s: idle_halt -> schedule()\n\0".as_ptr().cast(),
                b"spin_sleep_or_schedule\0".as_ptr().cast::<i8>(),
            ); }
            7 if enabled(13) => { let _ = super::kprintf(
                b"%s: caught a lost wake-up!\n\0".as_ptr().cast(),
                b"spin_sleep_or_schedule\0".as_ptr().cast::<i8>(),
            ); }
            // IHK_OS_MANYCORE maps ihk_ikc_get_processor_id to the same actual
            // ihk_mc_get_processor_id getter in ikc/ihk.h, as in sched_helpers.
            8 if enabled(14) => { let _ = super::kprintf(
                b"%s: woken while spinning, cpu: %d, do_schedule: %d\n\0".as_ptr().cast(),
                b"spin_sleep_or_schedule\0".as_ptr().cast::<i8>(),
                super::ihk_mc_get_processor_id(), arg3,
            ); }
            9 if enabled(15) => { let _ = super::kprintf(
                b"%s: woken while sleeping, cpu: %d\n\0".as_ptr().cast(),
                b"spin_sleep_or_schedule\0".as_ptr().cast::<i8>(),
                super::ihk_mc_get_processor_id(),
            ); }
            10 => { let _ = super::kprintf(
                b"%s: WARNING can't schedule() while no preemption, cnt: %d\n\0".as_ptr().cast(),
                b"schedule\0".as_ptr().cast::<i8>(), arg2,
            ); }
            11 if enabled(16) => { let _ = super::kprintf(
                b"%s: clone_count is %d\n\0".as_ptr().cast(),
                b"runq_add_thread\0".as_ptr().cast::<i8>(), arg2,
            ); }
            _ => {}
        } }
    }
}
}
