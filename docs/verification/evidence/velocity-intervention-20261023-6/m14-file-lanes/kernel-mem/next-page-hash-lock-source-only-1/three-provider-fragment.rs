/// Exact existing physical-page hash IRQ-save ticket-lock provider.
/// Caller retains the initialized aligned lock; saved flags are returned unchanged.
#[no_mangle]
pub unsafe extern "C" fn page_hash_lock_bridge(lock_addr: CULong) -> CULong {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_lock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}

/// Same release/preempt-enable/IRQ-restore provider and exact captured flags.
#[no_mangle]
pub unsafe extern "C" fn page_hash_unlock_bridge(lock_addr: CULong, flags: CULong) {
    unsafe {
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock, flags,
        )
    }
}

/// Exact existing lock initialization; no allocator or bucket ownership changes.
#[no_mangle]
pub unsafe extern "C" fn page_hash_lock_init_bridge(lock_addr: CULong) {
    unsafe {
        crate::spinlock_helpers::ihk_mc_spinlock_init(
            lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
        )
    }
}

