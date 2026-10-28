use core::sync::atomic::{AtomicU16, AtomicU32, Ordering};

use crate::abi::{CInt, CULong};

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
fn pack_tickets(head: u16, tail: u16) -> u32 {
    head as u32 | ((tail as u32) << 16)
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
pub unsafe extern "C" fn __ihk_mc_spinlock_trylock_noirq(lock: *mut IhkSpinlock) -> CInt {
    let cur = (*lock).head_tail.load(Ordering::SeqCst);
    let head = ticket_head(cur);
    let tail = ticket_tail(cur);

    if head != tail {
        return 0;
    }

    preempt_disable();
    let next = pack_tickets(head, tail.wrapping_add(TICKET_INC));
    match (*lock)
        .head_tail
        .compare_exchange(cur, next, Ordering::SeqCst, Ordering::SeqCst)
    {
        Ok(_) => 1,
        Err(_) => {
            preempt_enable();
            0
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_mc_spinlock_trylock(
    lock: *mut IhkSpinlock,
    result: *mut CInt,
) -> CULong {
    let flags = cpu_disable_interrupt_save();

    *result = __ihk_mc_spinlock_trylock_noirq(lock);
    flags
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

#[no_mangle]
pub extern "C" fn irqflags_can_interrupt(flags: CULong) -> CInt {
    ((flags & 0x200) != 0) as CInt
}
