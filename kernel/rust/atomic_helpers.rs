use core::ffi::c_void;
use core::sync::atomic::{AtomicI32, AtomicI64, AtomicPtr, AtomicU32, AtomicU64, Ordering};

use crate::abi::{CInt, CLong, CULong};

#[repr(C)]
pub struct IhkAtomic {
    counter: AtomicI32,
}

#[repr(C)]
pub struct IhkAtomic64 {
    counter64: AtomicI64,
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<IhkAtomic>() == 4);
    assert!(align_of::<IhkAtomic>() == 4);
    assert!(offset_of!(IhkAtomic, counter) == 0);
    assert!(size_of::<IhkAtomic64>() == 8);
    assert!(align_of::<IhkAtomic64>() == 8);
    assert!(offset_of!(IhkAtomic64, counter64) == 0);
};

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_read(v: *const IhkAtomic) -> CInt {
    (*v).counter.load(Ordering::SeqCst)
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_set(v: *mut IhkAtomic, i: CInt) {
    (*v).counter.store(i, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_add(i: CInt, v: *mut IhkAtomic) {
    let _ = (*v).counter.fetch_add(i, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_sub(i: CInt, v: *mut IhkAtomic) {
    let _ = (*v).counter.fetch_sub(i, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_inc(v: *mut IhkAtomic) {
    let _ = (*v).counter.fetch_add(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_dec(v: *mut IhkAtomic) {
    let _ = (*v).counter.fetch_sub(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_dec_and_test(v: *mut IhkAtomic) -> CInt {
    ((*v).counter.fetch_sub(1, Ordering::SeqCst) - 1 == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_inc_and_test(v: *mut IhkAtomic) -> CInt {
    ((*v).counter.fetch_add(1, Ordering::SeqCst) + 1 == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_add_return(i: CInt, v: *mut IhkAtomic) -> CInt {
    (*v).counter.fetch_add(i, Ordering::SeqCst) + i
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_sub_return(i: CInt, v: *mut IhkAtomic) -> CInt {
    (*v).counter.fetch_sub(i, Ordering::SeqCst) - i
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_inc_return(v: *mut IhkAtomic) -> CInt {
    unsafe { ihk_atomic_add_return(1, v) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_dec_return(v: *mut IhkAtomic) -> CInt {
    unsafe { ihk_atomic_sub_return(1, v) }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic64_read(v: *const IhkAtomic64) -> CLong {
    (*v).counter64.load(Ordering::SeqCst)
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic64_set(v: *mut IhkAtomic64, i: CLong) {
    (*v).counter64.store(i, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic64_inc(v: *mut IhkAtomic64) {
    let _ = (*v).counter64.fetch_add(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic64_add_return(i: CLong, v: *mut IhkAtomic64) -> CLong {
    (*v).counter64.fetch_add(i, Ordering::SeqCst) + i
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic64_sub_return(i: CLong, v: *mut IhkAtomic64) -> CLong {
    (*v).counter64.fetch_sub(i, Ordering::SeqCst) - i
}

#[no_mangle]
pub unsafe extern "C" fn xchg8(ptr: *mut CULong, x: CULong) -> CULong {
    AtomicU64::from_ptr(ptr).swap(x, Ordering::SeqCst)
}

#[no_mangle]
pub unsafe extern "C" fn xchg4(ptr: *mut CInt, x: CInt) -> CInt {
    AtomicI32::from_ptr(ptr).swap(x, Ordering::SeqCst)
}

#[no_mangle]
pub unsafe extern "C" fn atomic_xchg_ulong(ptr: *mut CULong, x: CULong) -> CULong {
    AtomicU64::from_ptr(ptr).swap(x, Ordering::SeqCst)
}

#[no_mangle]
pub unsafe extern "C" fn atomic_xchg_ptr(ptr: *mut *mut c_void, x: *mut c_void) -> *mut c_void {
    AtomicPtr::from_ptr(ptr).swap(x, Ordering::SeqCst)
}

#[no_mangle]
pub unsafe extern "C" fn atomic_cmpxchg8(
    addr: *mut CULong,
    oldval: CULong,
    newval: CULong,
) -> CULong {
    match AtomicU64::from_ptr(addr).compare_exchange(
        oldval,
        newval,
        Ordering::SeqCst,
        Ordering::SeqCst,
    ) {
        Ok(previous) | Err(previous) => previous,
    }
}

#[no_mangle]
pub unsafe extern "C" fn atomic_cmpxchg4(addr: *mut u32, oldval: u32, newval: u32) -> CULong {
    match AtomicU32::from_ptr(addr).compare_exchange(
        oldval,
        newval,
        Ordering::SeqCst,
        Ordering::SeqCst,
    ) {
        Ok(previous) | Err(previous) => previous as CULong,
    }
}

#[no_mangle]
pub unsafe extern "C" fn atomic_cmpxchg_int(addr: *mut CInt, oldval: CInt, newval: CInt) -> CInt {
    match AtomicI32::from_ptr(addr).compare_exchange(
        oldval,
        newval,
        Ordering::SeqCst,
        Ordering::SeqCst,
    ) {
        Ok(previous) | Err(previous) => previous,
    }
}

#[no_mangle]
pub unsafe extern "C" fn atomic_cmpxchg_ulong(
    addr: *mut CULong,
    oldval: CULong,
    newval: CULong,
) -> CULong {
    match AtomicU64::from_ptr(addr).compare_exchange(
        oldval,
        newval,
        Ordering::SeqCst,
        Ordering::SeqCst,
    ) {
        Ok(previous) | Err(previous) => previous,
    }
}

#[no_mangle]
pub unsafe extern "C" fn atomic_cmpxchg_ptr(
    addr: *mut *mut c_void,
    oldval: *mut c_void,
    newval: *mut c_void,
) -> *mut c_void {
    match AtomicPtr::from_ptr(addr).compare_exchange(
        oldval,
        newval,
        Ordering::SeqCst,
        Ordering::SeqCst,
    ) {
        Ok(previous) | Err(previous) => previous,
    }
}

#[no_mangle]
pub unsafe extern "C" fn compare_and_swap(
    addr: *mut c_void,
    olddata: CULong,
    newdata: CULong,
) -> CInt {
    match AtomicU64::from_ptr(addr.cast::<CULong>()).compare_exchange(
        olddata,
        newdata,
        Ordering::SeqCst,
        Ordering::SeqCst,
    ) {
        Ok(_) => 1,
        Err(_) => 0,
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_add_long(i: CLong, v: *mut CLong) {
    let _ = AtomicI64::from_ptr(v).fetch_add(i, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_add_ulong(i: CLong, v: *mut CULong) {
    let _ = AtomicU64::from_ptr(v).fetch_add(i as CULong, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_atomic_add_long_return(i: CLong, v: *mut CLong) -> CULong {
    (AtomicI64::from_ptr(v).fetch_add(i, Ordering::SeqCst) + i) as CULong
}
