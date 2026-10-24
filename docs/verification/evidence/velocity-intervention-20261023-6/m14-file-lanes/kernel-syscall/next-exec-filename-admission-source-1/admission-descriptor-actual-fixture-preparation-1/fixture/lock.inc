use core::sync::atomic::{AtomicI32,Ordering};
const IHK_RWSPINLOCK_WRITELOCKED:i32=0xff<<24;
extern "C" {fn preempt_disable();fn preempt_enable();fn cpu_pause();}
#[repr(C)]
pub struct IhkRwSpinlock {
    counter: AtomicI32,
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
pub unsafe extern "C" fn __ihk_rwspinlock_read_unlock(lock: *mut IhkRwSpinlock) {
    let _ = (*lock).counter.fetch_sub(1, Ordering::SeqCst);
}
#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_read_lock_noirq(lock: *mut IhkRwSpinlock) {
    preempt_disable();
    __ihk_rwspinlock_read_lock(lock);
}
#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_read_unlock_noirq(lock: *mut IhkRwSpinlock) {
    __ihk_rwspinlock_read_unlock(lock);
    preempt_enable();
}
