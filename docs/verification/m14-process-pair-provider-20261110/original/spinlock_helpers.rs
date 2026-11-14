use core::sync::atomic::AtomicU32;
use crate::abi::CULong;
#[repr(C)]
pub struct IhkSpinlock {
    head_tail: AtomicU32,
}
unsafe extern "C" {
    pub fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    pub fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
}
const _: () = {
    assert!(core::mem::size_of::<IhkSpinlock>() == 4);
    assert!(core::mem::align_of::<IhkSpinlock>() == 4);
    assert!(core::mem::offset_of!(IhkSpinlock, head_tail) == 0);
};
