use core::sync::atomic::{AtomicI32, Ordering};

use crate::abi::CInt;

const MCKERNEL_KREF_MARK: i32 = 1 << 30;

#[repr(C)]
pub struct IhkAtomic {
    counter: AtomicI32,
}

#[repr(C)]
pub struct KRef {
    refcount: IhkAtomic,
}

type KRefReleaseFn = Option<unsafe extern "C" fn(kref: *mut KRef)>;

#[repr(C)]
pub struct MemObjOps {
    free: Option<unsafe extern "C" fn(obj: *mut MemObj)>,
}

#[repr(C)]
pub struct MemObj {
    ops: *mut MemObjOps,
    flags: u32,
    status: u32,
    size: usize,
    refcnt: IhkAtomic,
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<IhkAtomic>() == 4);
    assert!(align_of::<IhkAtomic>() == 4);

    assert!(offset_of!(KRef, refcount) == 0);
    assert!(size_of::<KRef>() == 4);
    assert!(align_of::<KRef>() == 4);

    assert!(offset_of!(MemObjOps, free) == 0);
    assert!(size_of::<MemObjOps>() == 8);
    assert!(align_of::<MemObjOps>() == 8);

    assert!(offset_of!(MemObj, ops) == 0);
    assert!(offset_of!(MemObj, flags) == 8);
    assert!(offset_of!(MemObj, status) == 12);
    assert!(offset_of!(MemObj, size) == 16);
    assert!(offset_of!(MemObj, refcnt) == 24);
    assert!(size_of::<MemObj>() == 32);
    assert!(align_of::<MemObj>() == 8);
};

#[inline(always)]
unsafe fn atomic_load(v: *const IhkAtomic) -> i32 {
    (*v).counter.load(Ordering::SeqCst)
}

#[inline(always)]
unsafe fn atomic_store(v: *mut IhkAtomic, value: i32) {
    (*v).counter.store(value, Ordering::SeqCst);
}

#[inline(always)]
unsafe fn atomic_inc_return(v: *mut IhkAtomic) -> i32 {
    (*v).counter.fetch_add(1, Ordering::SeqCst) + 1
}

#[inline(always)]
unsafe fn atomic_dec_return(v: *mut IhkAtomic) -> i32 {
    (*v).counter.fetch_sub(1, Ordering::SeqCst) - 1
}

#[no_mangle]
pub unsafe extern "C" fn kref_init(kref: *mut KRef) {
    atomic_store(&raw mut (*kref).refcount, MCKERNEL_KREF_MARK + 1);
}

#[no_mangle]
pub unsafe extern "C" fn kref_read(kref: *const KRef) -> u32 {
    (atomic_load(&raw const (*kref).refcount) as u32) & !(MCKERNEL_KREF_MARK as u32)
}

#[no_mangle]
pub unsafe extern "C" fn kref_is_mckernel(kref: *const KRef) -> u32 {
    (atomic_load(&raw const (*kref).refcount) as u32) & (MCKERNEL_KREF_MARK as u32)
}

#[no_mangle]
pub unsafe extern "C" fn kref_get(kref: *mut KRef) {
    let _ = atomic_inc_return(&raw mut (*kref).refcount);
}

#[no_mangle]
pub unsafe extern "C" fn kref_put(kref: *mut KRef, release: KRefReleaseFn) -> CInt {
    let new_count = atomic_dec_return(&raw mut (*kref).refcount);

    if new_count == MCKERNEL_KREF_MARK {
        if let Some(release_fn) = release {
            release_fn(kref);
        }
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn memobj_ref(obj: *mut MemObj) -> CInt {
    atomic_inc_return(&raw mut (*obj).refcnt)
}

#[no_mangle]
pub unsafe extern "C" fn memobj_unref(obj: *mut MemObj) -> CInt {
    let new_count = atomic_dec_return(&raw mut (*obj).refcnt);

    if new_count == 0 && !(*obj).ops.is_null() {
        if let Some(free_fn) = (*(*obj).ops).free {
            free_fn(obj);
        }
    }

    new_count
}
