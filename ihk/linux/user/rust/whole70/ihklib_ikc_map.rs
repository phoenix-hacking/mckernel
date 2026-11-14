//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Public IKC-map pair, using the existing passed IKC request layout and OS helpers.

use core::ffi::{c_int, c_ulong, c_void};
use core::ptr::null_mut;
use super::ihklib_ikc::IhkIkcReq;

#[repr(C)]
pub struct IhkIkcCpuMap {
    pub src_cpu: c_int,
    pub dst_cpu: c_int,
}

const _: () = {
    assert!(core::mem::size_of::<IhkIkcCpuMap>() == 8);
    assert!(core::mem::offset_of!(IhkIkcCpuMap, dst_cpu) == 4);
    assert!(core::mem::size_of::<IhkIkcReq>() == 24);
    assert!(core::mem::offset_of!(IhkIkcReq, num_cpus) == 16);
};

unsafe extern "C" {
    fn calloc(count: usize, size: usize) -> *mut c_void;
    fn free(pointer: *mut c_void);
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
}

unsafe fn finish(fd: c_int, req: &IhkIkcReq, result: c_int) -> c_int {
    if fd != -1 {
        // SAFETY: preserve the C cleanup predicate, including encoded negative
        // errors. A nonnegative FD is owned here and has not otherwise closed.
        unsafe { close(fd) };
    }
    // SAFETY: both fields are NULL or this call's independent calloc allocations.
    // The supported ioctl provider borrows arrays and never replaces their pointers.
    unsafe {
        free(req.src_cpus.cast());
        free(req.dst_cpus.cast());
    }
    result
}

unsafe fn transfer(
    index: c_int,
    map: *mut IhkIkcCpuMap,
    count: c_int,
    query: bool,
) -> c_int {
    // SAFETY: the existing helper takes an unchanged integer index.
    let readable = unsafe { super::ihklib_mcstat::readable(index) };
    if readable != 0 {
        return readable;
    }
    if count <= 0 || count > 1024 {
        return -22;
    }
    if map.is_null() {
        return -14;
    }
    // SAFETY: reuse the current Rust public count API with the original ordering.
    let assigned = unsafe { super::os_cpu::ihk_os_get_num_assigned_cpus(index) };
    if assigned != count {
        // The original maps negative count errors as well as mismatches to EINVAL.
        return -22;
    }

    let mut req = IhkIkcReq { src_cpus: null_mut(), dst_cpus: null_mut(), num_cpus: 0 };
    // SAFETY: count is positive and <=1024; multiplication fits usize and calloc
    // returns suitably aligned storage or NULL without taking caller ownership.
    req.src_cpus = unsafe { calloc(count as usize, core::mem::size_of::<c_int>()) }.cast();
    if req.src_cpus.is_null() {
        // SAFETY: all fields remain NULL; preserve original free(NULL) cleanup.
        return unsafe { finish(-1, &req, -12) };
    }
    // SAFETY: the same bounded independent array allocation contract applies.
    req.dst_cpus = unsafe { calloc(count as usize, core::mem::size_of::<c_int>()) }.cast();
    if req.dst_cpus.is_null() {
        // SAFETY: finish owns the first allocation and frees it exactly once.
        return unsafe { finish(-1, &req, -12) };
    }
    if !query {
        for i in 0..count as usize {
            // SAFETY: the caller supplies count readable map entries; each owned
            // array has count initialized elements. No pointer escapes this call.
            unsafe {
                req.src_cpus.add(i).write((*map.add(i)).src_cpu);
                req.dst_cpus.add(i).write((*map.add(i)).dst_cpu);
            }
        }
    }
    req.num_cpus = count;
    // SAFETY: the existing helper returns this call's owned FD or encoded error.
    let fd = unsafe { super::ihklib_mcstat::ihklib_os_open(index) };
    if fd < 0 {
        // SAFETY: arrays remain owned and the original negative-FD cleanup applies.
        return unsafe { finish(fd, &req, fd) };
    }
    let request: c_ulong = if query { 0x112a29 } else { 0x112a28 };
    // SAFETY: req has the passed 24-byte ABI; arrays are live for this synchronous
    // ioctl. The supported provider retains pointers and bounds count by capacity.
    let value = unsafe { ioctl(fd, request, &mut req as *mut IhkIkcReq) };
    if value != 0 {
        // SAFETY: libc errno is read before cleanup can replace it.
        let result = unsafe { -*__errno_location() };
        // SAFETY: no other path has released this call's owned FD or allocations.
        return unsafe { finish(fd, &req, result) };
    }
    if query {
        for i in 0..req.num_cpus {
            // SAFETY: caller provides count writable map entries; the existing
            // driver contract keeps returned count <= capacity and both pointers.
            unsafe {
                (*map.add(i as usize)).src_cpu = req.src_cpus.add(i as usize).read();
                (*map.add(i as usize)).dst_cpu = req.dst_cpus.add(i as usize).read();
            }
        }
    }
    // SAFETY: the request's owned resources remain unreleased until this point.
    unsafe { finish(fd, &req, value) }
}

/// Set the selected OS's complete IKC map using the original validation order.
///
/// # Safety
/// map must contain count readable entries when count is valid. The selected
/// synchronous ioctl provider must retain request pointers and bound its count.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_set_ikc_map(
    index: c_int,
    map: *mut IhkIkcCpuMap,
    count: c_int,
) -> c_int {
    // SAFETY: caller satisfies the documented input array and provider contract.
    unsafe { transfer(index, map, count, false) }
}

/// Query IKC-map entries without copying partial output after an ioctl error.
///
/// # Safety
/// map must contain count writable entries when count is valid. The selected
/// ioctl provider must retain request pointers and return count <= capacity.
#[no_mangle]
pub unsafe extern "C" fn ihk_os_get_ikc_map(
    index: c_int,
    map: *mut IhkIkcCpuMap,
    count: c_int,
) -> c_int {
    // SAFETY: caller satisfies the documented output array and provider contract.
    unsafe { transfer(index, map, count, true) }
}

// Public descriptor ABI paired with abi/mem_map_public_abi_witness.c.
// Check actual exported functions and fields; no fixture representation.
const _: unsafe extern "C" fn(c_int, *mut IhkIkcCpuMap, c_int) -> c_int = ihk_os_set_ikc_map;
const _: unsafe extern "C" fn(c_int, *mut IhkIkcCpuMap, c_int) -> c_int = ihk_os_get_ikc_map;
const _: () = {
    assert!(core::mem::size_of::<IhkIkcCpuMap>() == 8);
    assert!(core::mem::align_of::<IhkIkcCpuMap>() == 4);
    assert!(core::mem::offset_of!(IhkIkcCpuMap, src_cpu) == 0);
    assert!(core::mem::offset_of!(IhkIkcCpuMap, dst_cpu) == 4);
};
const _: fn(&IhkIkcCpuMap) = |value| {
    let _: &c_int = &value.src_cpu;
    let _: &c_int = &value.dst_cpu;
};
