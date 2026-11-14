#![no_std]
// Finite exact current lock/init, native IRQ and preemption source partition; codegen only.
// No function/hardware/boot/init execution or whole-module provider substitution.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod debug {
use core::ptr::null_mut;
use crate::abi::{CInt, CULong, IhkSpinlock};

const IHK_KMSG_SIZE: CInt = (4 << 20) - 4096;

#[repr(C)]
pub struct IhkKmsgBuf {
    pub lock: CInt,
    pub tail: CInt,
    pub len: CInt,
    pub head: CInt,
    pub padding: [i8; 4096 - core::mem::size_of::<CInt>() * 4],
    pub str_: [i8; IHK_KMSG_SIZE as usize],
}

const _: () = {
    use core::mem::{offset_of, size_of};
    assert!(size_of::<IhkKmsgBuf>() == 4 << 20);
    assert!(offset_of!(IhkKmsgBuf, str_) == 4096);
};

#[no_mangle]
pub static mut kmsg_buf: *mut IhkKmsgBuf = null_mut();

static mut KMSG_LOCK: IhkSpinlock = IhkSpinlock { head_tail: 0 };

unsafe extern "C" {
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
    fn ihk_mc_spinlock_init(lock: *mut IhkSpinlock);
}

#[no_mangle]
pub unsafe extern "C" fn kprintf_lock() -> CULong {
    __ihk_mc_spinlock_lock(&raw mut KMSG_LOCK)
}

#[no_mangle]
pub unsafe extern "C" fn kprintf_unlock(irqflags: CULong) {
    __ihk_mc_spinlock_unlock(&raw mut KMSG_LOCK, irqflags);
}

#[no_mangle]
pub unsafe extern "C" fn kmsg_init() {
    ihk_mc_spinlock_init(&raw mut KMSG_LOCK);
}
}

mod spinlock_helpers {
use core::sync::atomic::{AtomicU16, AtomicU32, Ordering};
use crate::abi::CULong;

#[repr(C)]
pub struct IhkSpinlock {
    head_tail: AtomicU32,
}

const TICKET_INC: u16 = 2;
const TAIL_INC: u32 = (TICKET_INC as u32) << 16;

extern "C" {
    fn preempt_disable();
    fn preempt_enable();
    fn cpu_pause();
    fn cpu_disable_interrupt_save() -> CULong;
    fn cpu_restore_interrupt(flags: CULong);
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<IhkSpinlock>() == 4);
    assert!(align_of::<IhkSpinlock>() == 4);
    assert!(offset_of!(IhkSpinlock, head_tail) == 0);
};

#[inline(always)]
fn ticket_head(value: u32) -> u16 {
    value as u16
}

#[inline(always)]
fn ticket_tail(value: u32) -> u16 {
    (value >> 16) as u16
}

#[inline(always)]
unsafe fn head_atomic(lock: *mut IhkSpinlock) -> *mut AtomicU16 {
    lock as *mut AtomicU16
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_spinlock_init(lock: *mut IhkSpinlock) {
    (*lock).head_tail.store(0, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock) {
    preempt_disable();
    let ticket = (*lock).head_tail.fetch_add(TAIL_INC, Ordering::SeqCst);
    let wait_for = ticket_tail(ticket);

    if ticket_head(ticket) == wait_for {
        return;
    }

    loop {
        if ticket_head((*lock).head_tail.load(Ordering::Acquire)) == wait_for {
            return;
        }
        cpu_pause();
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong {
    let flags = cpu_disable_interrupt_save();

    __ihk_mc_spinlock_lock_noirq(lock);
    flags
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_mc_spinlock_unlock_noirq(lock: *mut IhkSpinlock) {
    let _ = (*head_atomic(lock)).fetch_add(TICKET_INC, Ordering::SeqCst);
    preempt_enable();
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong) {
    __ihk_mc_spinlock_unlock_noirq(lock);
    cpu_restore_interrupt(flags);
}
}

mod x86_cpu_helpers {
use crate::abi::{CInt, CULong};

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_restore_interrupt(flags: CULong) {
    core::arch::asm!("push {flags}", "popfq", flags = in(reg) flags);
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_pause() {
    core::arch::asm!("pause", options(nomem, nostack, preserves_flags));
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_disable_interrupt_save() -> CULong {
    let flags: CULong;

    core::arch::asm!("pushfq", "pop {flags}", "cli", flags = lateout(reg) flags);

    flags
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn cpu_interrupt_disabled() -> CInt {
    let flags: CULong;

    core::arch::asm!(
        "pushfq",
        "pop {flags}",
        flags = lateout(reg) flags,
        options(preserves_flags),
    );

    if flags & 0x200 == 0 {
        1
    } else {
        0
    }
}
}

mod cls {
use core::sync::atomic::{AtomicI32, Ordering};
use crate::abi::{CInt, CpuLocalVar};

unsafe extern "C" {
    fn get_cpu_local_var(id: CInt) -> *mut CpuLocalVar;
    fn ihk_mc_get_processor_id() -> CInt;
}

#[no_mangle]
pub static mut cpu_local_var_initialized: CInt = 0;

#[inline(always)]
unsafe fn atomic_counter(counter: *mut crate::abi::IhkAtomic) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*counter).counter)
}

#[inline(always)]
unsafe fn this_cpu_local_var() -> *mut CpuLocalVar {
    get_cpu_local_var(ihk_mc_get_processor_id())
}

#[no_mangle]
pub unsafe extern "C" fn preempt_enable() {
    if cpu_local_var_initialized != 0 {
        let v = this_cpu_local_var();
        atomic_counter(&raw mut (*v).no_preempt).fetch_sub(1, Ordering::SeqCst);
    }
}

#[no_mangle]
pub unsafe extern "C" fn preempt_disable() {
    if cpu_local_var_initialized != 0 {
        let v = this_cpu_local_var();
        atomic_counter(&raw mut (*v).no_preempt).fetch_add(1, Ordering::SeqCst);
    }
}
}
