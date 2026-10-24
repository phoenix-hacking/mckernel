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
