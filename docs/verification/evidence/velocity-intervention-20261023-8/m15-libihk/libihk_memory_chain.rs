//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Public CPU API successor for the selected WITH_KRM=OFF Linux x86_64 profile.
#![no_std]
#[cfg(ihklib_with_krm)]
compile_error!("WITH_KRM CPU reservation policy must be ported before selecting this successor");
use core::ffi::{c_char, c_int, c_ulong};
#[repr(C)]
pub struct IhkCpuReq { pub cpus: *mut c_int, pub num_cpus: c_int }
const MAX_CPUS: c_int = 1024;
const RESERVE_CPU: c_ulong = 0x112902;
const RELEASE_CPU: c_ulong = 0x112903;
const QUERY_CPU: c_ulong = 0x112906;
const GET_NUM_CPUS: c_ulong = 0x11290c;
unsafe extern "C" {
    fn access(path: *const c_char, mode: c_int) -> c_int;
    fn open(path: *const c_char, flags: c_int, ...) -> c_int;
    fn snprintf(out: *mut c_char, size: usize, format: *const c_char, ...) -> c_int;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
    fn abort() -> !;
}
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! { unsafe { abort() } }
unsafe fn neg_errno() -> c_int { unsafe { -*__errno_location() } }
unsafe fn device_readable(index: c_int) -> c_int {
    let mut path = [0 as c_char; 4096];
    unsafe { snprintf(path.as_mut_ptr(), path.len(), b"/dev/mcd%d\0".as_ptr().cast(), index); }
    if unsafe { access(path.as_ptr(), 4) } != 0 { unsafe { neg_errno() } } else { 0 }
}
#[no_mangle]
pub unsafe extern "C" fn ihklib_device_open(index: c_int) -> c_int {
    let ret = unsafe { device_readable(index) };
    if ret != 0 { return ret; }
    let mut path = [0 as c_char; 4096];
    unsafe { snprintf(path.as_mut_ptr(), path.len(), b"/dev/mcd%d\0".as_ptr().cast(), index); }
    let fd = unsafe { open(path.as_ptr(), 0) };
    if fd == -1 { unsafe { neg_errno() } } else { fd }
}
// Preserve the C cleanup condition, including a failed device_open result other
// than -1: close() may alter errno, while the already captured return is retained.
unsafe fn finish(fd: c_int, ret: c_int) -> c_int {
    if fd != -1 { unsafe { close(fd); } }
    ret
}
unsafe fn change_cpu(index: c_int, cpus: *mut c_int, count: c_int, request: c_ulong) -> c_int {
    let ret = unsafe { device_readable(index) };
    if ret != 0 { return ret; }
    if count < 0 || count > MAX_CPUS { return -22; }
    if count != 0 && cpus.is_null() { return -14; }
    if count == 0 { return 0; }
    let mut req = core::mem::MaybeUninit::<IhkCpuReq>::zeroed();
    let request_ptr = req.as_mut_ptr();
    unsafe {
        core::ptr::addr_of_mut!((*request_ptr).cpus).write(cpus);
        core::ptr::addr_of_mut!((*request_ptr).num_cpus).write(count);
    }
    let fd = unsafe { ihklib_device_open(index) };
    if fd < 0 { return unsafe { finish(fd, fd) }; }
    let rc = unsafe { ioctl(fd, request, request_ptr) };
    let ret = if rc != 0 { unsafe { neg_errno() } } else { rc };
    unsafe { finish(fd, ret) }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_reserve_cpu(index: c_int, cpus: *mut c_int, count: c_int) -> c_int {
    unsafe { change_cpu(index, cpus, count, RESERVE_CPU) }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_release_cpu(index: c_int, cpus: *mut c_int, count: c_int) -> c_int {
    unsafe { change_cpu(index, cpus, count, RELEASE_CPU) }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_get_num_reserved_cpus(index: c_int) -> c_int {
    let fd = unsafe { ihklib_device_open(index) };
    if fd < 0 { return unsafe { finish(fd, fd) }; }
    let rc = unsafe { ioctl(fd, GET_NUM_CPUS) };
    let ret = if rc < 0 { unsafe { neg_errno() } } else { rc };
    unsafe { finish(fd, ret) }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_query_cpu(index: c_int, cpus: *mut c_int, count: c_int) -> c_int {
    let ret = unsafe { device_readable(index) };
    if ret != 0 { return ret; }
    if cpus.is_null() || count < 0 || count > MAX_CPUS { return -22; }
    let fd = unsafe { ihklib_device_open(index) };
    if fd < 0 { return unsafe { finish(fd, fd) }; }
    let actual = unsafe { ioctl(fd, GET_NUM_CPUS) };
    if actual < 0 { let ret = unsafe { neg_errno() }; return unsafe { finish(fd, ret) }; }
    if actual != count { return unsafe { finish(fd, -22) }; }
    if count == 0 { return unsafe { finish(fd, 0) }; }
    let mut req = core::mem::MaybeUninit::<IhkCpuReq>::zeroed();
    let request_ptr = req.as_mut_ptr();
    unsafe {
        core::ptr::addr_of_mut!((*request_ptr).cpus).write(cpus);
        core::ptr::addr_of_mut!((*request_ptr).num_cpus).write(count);
    }
    let rc = unsafe { ioctl(fd, QUERY_CPU, request_ptr) };
    let ret = if rc != 0 { unsafe { neg_errno() } } else { rc };
    unsafe { finish(fd, ret) }
}
// ABI witnesses use the actual Rust type, not a parallel fixture representation.
#[cfg(ihklib_cpu_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_cpu_req_size() -> usize { core::mem::size_of::<IhkCpuReq>() }
#[cfg(ihklib_cpu_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_cpu_req_alignment() -> usize { core::mem::align_of::<IhkCpuReq>() }
#[cfg(ihklib_cpu_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_cpu_req_count_offset() -> usize { core::mem::offset_of!(IhkCpuReq, num_cpus) }

#[path = "ihklib_memory_os_dependencies.rs"]
mod ihklib_memory_os;
