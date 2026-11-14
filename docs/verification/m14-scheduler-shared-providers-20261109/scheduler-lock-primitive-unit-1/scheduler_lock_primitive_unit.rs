#![no_std]
// Exact three original lock/atomic providers; existing spin implementations stay U.
mod abi {
pub type CInt = i32;
}

mod spinlock_helpers {
use core::sync::atomic::AtomicU32;
#[repr(C)]
pub struct IhkSpinlock {
    head_tail: AtomicU32,
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<IhkSpinlock>() == 4);
    assert!(align_of::<IhkSpinlock>() == 4);
    assert!(offset_of!(IhkSpinlock, head_tail) == 0);
};

unsafe extern "C" {
    pub fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock);
    pub fn __ihk_mc_spinlock_unlock_noirq(lock: *mut IhkSpinlock);
}
}

mod lock_helpers {
use crate::spinlock_helpers;
#[repr(C, align(64))]
pub struct McsRwlockLock {
    slock: spinlock_helpers::IhkSpinlock,
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<McsRwlockLock>() == 64);
    assert!(align_of::<McsRwlockLock>() == 64);
    assert!(offset_of!(McsRwlockLock, slock) == 0);
};

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
}

mod atomic_helpers {
use core::sync::atomic::{AtomicI32, Ordering};
use crate::abi::CInt;

#[no_mangle]
pub unsafe extern "C" fn xchg4(ptr: *mut CInt, x: CInt) -> CInt {
    AtomicI32::from_ptr(ptr).swap(x, Ordering::SeqCst)
}
}
