use crate::abi::CULong;
use crate::spinlock_helpers;
#[repr(C, align(64))]
pub struct McsRwlockNodeIrqsave {
    irqsave: CULong,
}
#[repr(C, align(64))]
pub struct McsRwlockLock {
    slock: spinlock_helpers::IhkSpinlock,
}
const _: () = {
    use core::mem::{size_of,align_of,offset_of};
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(align_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(offset_of!(McsRwlockNodeIrqsave, irqsave) == 0);
    assert!(size_of::<McsRwlockLock>() == 64);
    assert!(align_of::<McsRwlockLock>() == 64);
    assert!(offset_of!(McsRwlockLock, slock) == 0);
};
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
