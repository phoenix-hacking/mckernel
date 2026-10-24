#[no_mangle]
pub unsafe extern "C" fn __ihk_rwspinlock_read_unlock(lock: *mut IhkRwSpinlock) {
    let _ = (*lock).counter.fetch_sub(1, Ordering::SeqCst);
}
