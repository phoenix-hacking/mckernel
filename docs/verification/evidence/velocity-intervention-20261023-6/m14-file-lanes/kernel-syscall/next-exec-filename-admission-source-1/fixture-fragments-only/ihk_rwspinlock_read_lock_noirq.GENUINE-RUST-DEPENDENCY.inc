#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_read_lock_noirq(lock: *mut IhkRwSpinlock) {
    preempt_disable();
    __ihk_rwspinlock_read_lock(lock);
}
