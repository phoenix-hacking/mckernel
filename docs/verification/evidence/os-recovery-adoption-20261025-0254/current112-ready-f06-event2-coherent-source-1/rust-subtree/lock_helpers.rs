use core::ffi::c_void;
use core::ptr;
use core::sync::atomic::{AtomicI32, AtomicI64, AtomicPtr, AtomicU32, AtomicU64, Ordering};

use crate::abi::{CInt, CULong};
use crate::spinlock_helpers;

const IHK_RWSPINLOCK_WRITELOCKED: i32 = 0xff << 24;
const Q_LOCKED_VAL: u32 = 1;

extern "C" {
    fn preempt_disable();
    fn preempt_enable();
    fn cpu_pause();
    fn cpu_disable_interrupt_save() -> CULong;
    fn cpu_restore_interrupt(flags: CULong);
}

#[repr(C)]
pub struct IhkRwSpinlock {
    counter: AtomicI32,
}

#[repr(C, align(64))]
pub struct McsLockNode {
    locked: AtomicU64,
    next: AtomicPtr<McsLockNode>,
    irqsave: CULong,
}

#[repr(C, align(64))]
pub struct McsRwlockNodeIrqsave {
    irqsave: CULong,
}

#[repr(C, align(64))]
pub struct McsRwlockLock {
    slock: spinlock_helpers::IhkSpinlock,
}

#[repr(C)]
pub struct IhkMcRwlock {
    lock: AtomicI64,
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<IhkRwSpinlock>() == 4);
    assert!(align_of::<IhkRwSpinlock>() == 4);
    assert!(offset_of!(IhkRwSpinlock, counter) == 0);
    assert!(size_of::<McsLockNode>() == 64);
    assert!(align_of::<McsLockNode>() == 64);
    assert!(offset_of!(McsLockNode, locked) == 0);
    assert!(offset_of!(McsLockNode, next) == 8);
    assert!(offset_of!(McsLockNode, irqsave) == 16);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(align_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(offset_of!(McsRwlockNodeIrqsave, irqsave) == 0);
    assert!(size_of::<McsRwlockLock>() == 64);
    assert!(align_of::<McsRwlockLock>() == 64);
    assert!(offset_of!(McsRwlockLock, slock) == 0);
    assert!(size_of::<IhkMcRwlock>() == 8);
    assert!(align_of::<IhkMcRwlock>() == 8);
    assert!(offset_of!(IhkMcRwlock, lock) == 0);
};

#[inline(always)]
unsafe fn mc_rwlock_write(lock: *mut IhkMcRwlock) -> *mut AtomicI32 {
    (lock as *mut u8).add(core::mem::size_of::<u32>()) as *mut AtomicI32
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_init(lock: *mut IhkRwSpinlock) {
    (*lock).counter.store(0, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_rwspinlock_read_lock(lock: *mut IhkRwSpinlock) {
    loop {
        let desired = (*lock).counter.load(Ordering::SeqCst) & !IHK_RWSPINLOCK_WRITELOCKED;
        let new_val = desired + 1;

        if (new_val as u32) < IHK_RWSPINLOCK_WRITELOCKED as u32
            && (*lock)
                .counter
                .compare_exchange(desired, new_val, Ordering::SeqCst, Ordering::SeqCst)
                .is_ok()
        {
            return;
        }
        cpu_pause();
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_rwspinlock_read_trylock(lock: *mut IhkRwSpinlock) -> CInt {
    let desired = (*lock).counter.load(Ordering::SeqCst) & !IHK_RWSPINLOCK_WRITELOCKED;
    let new_val = desired + 1;

    ((new_val as u32) < IHK_RWSPINLOCK_WRITELOCKED as u32
        && (*lock)
            .counter
            .compare_exchange(desired, new_val, Ordering::SeqCst, Ordering::SeqCst)
            .is_ok()) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_rwspinlock_read_unlock(lock: *mut IhkRwSpinlock) {
    let _ = (*lock).counter.fetch_sub(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_rwspinlock_write_lock(lock: *mut IhkRwSpinlock) {
    loop {
        if (*lock)
            .counter
            .compare_exchange(
                0,
                IHK_RWSPINLOCK_WRITELOCKED,
                Ordering::SeqCst,
                Ordering::SeqCst,
            )
            .is_ok()
        {
            return;
        }
        cpu_pause();
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_rwspinlock_write_unlock(lock: *mut IhkRwSpinlock) {
    (*lock).counter.store(0, Ordering::Release);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_read_lock_noirq(lock: *mut IhkRwSpinlock) {
    preempt_disable();
    __ihk_rwspinlock_read_lock(lock);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_read_trylock_noirq(lock: *mut IhkRwSpinlock) -> CInt {
    preempt_disable();
    let rc = __ihk_rwspinlock_read_trylock(lock);

    if rc == 0 {
        preempt_enable();
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_write_lock_noirq(lock: *mut IhkRwSpinlock) {
    preempt_disable();
    __ihk_rwspinlock_write_lock(lock);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_read_unlock_noirq(lock: *mut IhkRwSpinlock) {
    __ihk_rwspinlock_read_unlock(lock);
    preempt_enable();
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_write_unlock_noirq(lock: *mut IhkRwSpinlock) {
    __ihk_rwspinlock_write_unlock(lock);
    preempt_enable();
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_read_lock(lock: *mut IhkRwSpinlock) -> CULong {
    let irqstate = cpu_disable_interrupt_save();

    ihk_rwspinlock_read_lock_noirq(lock);
    irqstate
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_write_lock(lock: *mut IhkRwSpinlock) -> CULong {
    let irqstate = cpu_disable_interrupt_save();

    ihk_rwspinlock_write_lock_noirq(lock);
    irqstate
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_read_unlock(lock: *mut IhkRwSpinlock, irqstate: CULong) {
    ihk_rwspinlock_read_unlock_noirq(lock);
    cpu_restore_interrupt(irqstate);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_write_unlock(lock: *mut IhkRwSpinlock, irqstate: CULong) {
    ihk_rwspinlock_write_unlock_noirq(lock);
    cpu_restore_interrupt(irqstate);
}

#[no_mangle]
pub unsafe extern "C" fn linux_spin_lock(lock: *mut c_void) {
    let lock_word = lock as *mut AtomicU32;

    while (*lock_word)
        .compare_exchange(0, Q_LOCKED_VAL, Ordering::SeqCst, Ordering::SeqCst)
        .is_err()
    {
        cpu_pause();
    }
}

#[no_mangle]
pub unsafe extern "C" fn linux_spin_unlock(lock: *mut c_void) {
    let lock_word = lock as *mut AtomicU32;

    (*lock_word).store(0, Ordering::Release);
}

#[no_mangle]
pub unsafe extern "C" fn linux_spin_lock_irqsave(lock: *mut c_void, flags: *mut CULong) {
    *flags = cpu_disable_interrupt_save();
    linux_spin_lock(lock);
}

#[no_mangle]
pub unsafe extern "C" fn linux_spin_unlock_irqrestore(lock: *mut c_void, flags: CULong) {
    linux_spin_unlock(lock);
    cpu_restore_interrupt(flags);
}

#[no_mangle]
pub unsafe extern "C" fn mcs_lock_init(node: *mut McsLockNode) {
    (*node).locked.store(0, Ordering::SeqCst);
    (*node).next.store(ptr::null_mut(), Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_lock_lock(lock: *mut McsLockNode, node: *mut McsLockNode) {
    (*node).next.store(ptr::null_mut(), Ordering::SeqCst);
    (*node).locked.store(0, Ordering::SeqCst);

    let pred = (*lock).next.swap(node, Ordering::SeqCst);
    if pred.is_null() {
        return;
    }

    (*pred).next.store(node, Ordering::Release);
    while (*node).locked.load(Ordering::Acquire) == 0 {
        cpu_pause();
    }
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_lock_unlock(lock: *mut McsLockNode, node: *mut McsLockNode) {
    let mut next = (*node).next.load(Ordering::Acquire);

    if next.is_null() {
        if (*lock)
            .next
            .compare_exchange(node, ptr::null_mut(), Ordering::SeqCst, Ordering::SeqCst)
            .is_ok()
        {
            return;
        }

        while {
            next = (*node).next.load(Ordering::Acquire);
            next.is_null()
        } {
            cpu_pause();
        }
    }

    (*next).locked.store(1, Ordering::Release);
}

#[no_mangle]
pub unsafe extern "C" fn mcs_lock_lock_noirq(lock: *mut McsLockNode, node: *mut McsLockNode) {
    preempt_disable();
    __mcs_lock_lock(lock, node);
}

#[no_mangle]
pub unsafe extern "C" fn mcs_lock_unlock_noirq(lock: *mut McsLockNode, node: *mut McsLockNode) {
    __mcs_lock_unlock(lock, node);
    preempt_enable();
}

#[no_mangle]
pub unsafe extern "C" fn mcs_lock_lock(lock: *mut McsLockNode, node: *mut McsLockNode) {
    (*node).irqsave = cpu_disable_interrupt_save();
    mcs_lock_lock_noirq(lock, node);
}

#[no_mangle]
pub unsafe extern "C" fn mcs_lock_unlock(lock: *mut McsLockNode, node: *mut McsLockNode) {
    mcs_lock_unlock_noirq(lock, node);
    cpu_restore_interrupt((*node).irqsave);
}

#[no_mangle]
pub unsafe extern "C" fn mcs_rwlock_init(lock: *mut McsRwlockLock) {
    spinlock_helpers::ihk_mc_spinlock_init(&mut (*lock).slock);
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_rwlock_writer_lock_noirq(
    lock: *mut McsRwlockLock,
    _node: *mut core::ffi::c_void,
) {
    spinlock_helpers::__ihk_mc_spinlock_lock_noirq(&mut (*lock).slock);
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_rwlock_writer_unlock_noirq(
    lock: *mut McsRwlockLock,
    _node: *mut core::ffi::c_void,
) {
    spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(&mut (*lock).slock);
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_rwlock_reader_lock_noirq(
    lock: *mut McsRwlockLock,
    _node: *mut core::ffi::c_void,
) {
    spinlock_helpers::__ihk_mc_spinlock_lock_noirq(&mut (*lock).slock);
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_rwlock_reader_unlock_noirq(
    lock: *mut McsRwlockLock,
    _node: *mut core::ffi::c_void,
) {
    spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(&mut (*lock).slock);
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_rwlock_writer_lock(
    lock: *mut McsRwlockLock,
    node: *mut McsRwlockNodeIrqsave,
) {
    (*node).irqsave = spinlock_helpers::__ihk_mc_spinlock_lock(&mut (*lock).slock);
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_rwlock_writer_unlock(
    lock: *mut McsRwlockLock,
    node: *mut McsRwlockNodeIrqsave,
) {
    spinlock_helpers::__ihk_mc_spinlock_unlock(&mut (*lock).slock, (*node).irqsave);
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_rwlock_reader_lock(
    lock: *mut McsRwlockLock,
    node: *mut McsRwlockNodeIrqsave,
) {
    (*node).irqsave = spinlock_helpers::__ihk_mc_spinlock_lock(&mut (*lock).slock);
}

#[no_mangle]
pub unsafe extern "C" fn __mcs_rwlock_reader_unlock(
    lock: *mut McsRwlockLock,
    node: *mut McsRwlockNodeIrqsave,
) {
    spinlock_helpers::__ihk_mc_spinlock_unlock(&mut (*lock).slock, (*node).irqsave);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_rwlock_init(rw: *mut IhkMcRwlock) {
    (*rw).lock.store(1i64 << 32, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_read_lock(rw: *mut IhkMcRwlock) {
    loop {
        let next = (*rw).lock.fetch_sub(1, Ordering::SeqCst) - 1;
        if next >= 0 {
            return;
        }
        let _ = (*rw).lock.fetch_add(1, Ordering::SeqCst);
        while (*rw).lock.load(Ordering::Acquire) < 1 {
            cpu_pause();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_write_lock(rw: *mut IhkMcRwlock) {
    loop {
        let next = (*mc_rwlock_write(rw)).fetch_sub(1, Ordering::SeqCst) - 1;
        if next == 0 {
            return;
        }
        let _ = (*mc_rwlock_write(rw)).fetch_add(1, Ordering::SeqCst);
        while (*mc_rwlock_write(rw)).load(Ordering::Acquire) != 1 {
            cpu_pause();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_read_trylock(rw: *mut IhkMcRwlock) -> CInt {
    let next = (*rw).lock.fetch_sub(1, Ordering::SeqCst) - 1;
    if next >= 0 {
        1
    } else {
        let _ = (*rw).lock.fetch_add(1, Ordering::SeqCst);
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_write_trylock(rw: *mut IhkMcRwlock) -> CInt {
    let next = (*mc_rwlock_write(rw)).fetch_sub(1, Ordering::SeqCst) - 1;
    if next == 0 {
        1
    } else {
        let _ = (*mc_rwlock_write(rw)).fetch_add(1, Ordering::SeqCst);
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_read_unlock(rw: *mut IhkMcRwlock) {
    let _ = (*rw).lock.fetch_add(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_write_unlock(rw: *mut IhkMcRwlock) {
    let _ = (*mc_rwlock_write(rw)).fetch_add(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_write_can_lock(rw: *mut IhkMcRwlock) -> CInt {
    ((*mc_rwlock_write(rw)).load(Ordering::SeqCst) == 1) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_read_can_lock(rw: *mut IhkMcRwlock) -> CInt {
    ((*rw).lock.load(Ordering::SeqCst) > 0) as CInt
}
