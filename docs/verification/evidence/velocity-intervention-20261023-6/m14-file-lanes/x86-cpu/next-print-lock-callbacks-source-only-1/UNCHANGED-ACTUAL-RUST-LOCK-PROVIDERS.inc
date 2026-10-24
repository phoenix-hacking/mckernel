#[no_mangle]
pub unsafe extern "C" fn kprintf_lock() -> CULong {
    __ihk_mc_spinlock_lock(&raw mut KMSG_LOCK)
}

#[no_mangle]
pub unsafe extern "C" fn kprintf_unlock(irqflags: CULong) {
    __ihk_mc_spinlock_unlock(&raw mut KMSG_LOCK, irqflags);
}
