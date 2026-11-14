#[no_mangle]
pub unsafe extern "C" fn ihk_rwspinlock_read_unlock_noirq(lock: *mut IhkRwSpinlock) {
    __ihk_rwspinlock_read_unlock(lock);
    preempt_enable();
}
