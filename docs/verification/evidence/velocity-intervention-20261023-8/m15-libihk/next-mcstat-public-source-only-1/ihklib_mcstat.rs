//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Next source increment only; no second executable queue or current-library selection.
//! Rusage layout copied from the existing selected Rust mcstat consumer.
use core::ffi::{c_char, c_int, c_ulong};
const IHK_MAX_NUM_PGSIZES: usize = 8;
const IHK_MAX_NUM_NUMA_NODES: usize = 1024;
const IHK_MAX_NUM_CPUS: usize = 1024;
#[repr(C)]
pub struct IhkOsRusage {
    memory_stat_rss: [c_ulong; IHK_MAX_NUM_PGSIZES],
    memory_stat_mapped_file: [c_ulong; IHK_MAX_NUM_PGSIZES],
    memory_max_usage: c_ulong,
    memory_kmem_usage: c_ulong,
    memory_kmem_max_usage: c_ulong,
    memory_numa_stat: [c_ulong; IHK_MAX_NUM_NUMA_NODES],
    cpuacct_stat_system: c_ulong,
    cpuacct_stat_user: c_ulong,
    cpuacct_usage: c_ulong,
    cpuacct_usage_percpu: [c_ulong; IHK_MAX_NUM_CPUS],
    num_threads: c_int,
    max_num_threads: c_int,
}
#[repr(C)]
struct RusageRequest { rusage: *mut IhkOsRusage, size_rusage: usize }
unsafe extern "C" {
    fn access(path: *const c_char, mode: c_int) -> c_int;
    fn open(path: *const c_char, flags: c_int, ...) -> c_int;
    fn snprintf(out: *mut c_char, size: usize, format: *const c_char, ...) -> c_int;
    fn ioctl(fd: c_int, command: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
}
unsafe fn neg_errno() -> c_int { unsafe { -*__errno_location() } }
unsafe fn readable(index: c_int) -> c_int {
    let mut path = [0 as c_char; 4096];
    unsafe { snprintf(path.as_mut_ptr(), path.len(), b"/dev/mcos%d\0".as_ptr().cast(), index); }
    let result = unsafe { access(path.as_ptr(), 4) };
    if result != 0 { unsafe { neg_errno() } } else { result }
}
#[no_mangle]
pub unsafe extern "C" fn ihklib_os_open(index: c_int) -> c_int {
    let result = unsafe { readable(index) };
    if result != 0 { return result; }
    let mut path = [0 as c_char; 4096];
    unsafe { snprintf(path.as_mut_ptr(), path.len(), b"/dev/mcos%d\0".as_ptr().cast(), index); }
    let fd = unsafe { open(path.as_ptr(), 0) };
    if fd == -1 { unsafe { neg_errno() } } else { fd }
}
unsafe fn finish(fd: c_int, result: c_int) -> c_int {
    if fd != -1 { unsafe { close(fd); } }
    result
}
#[no_mangle]
pub unsafe extern "C" fn ihk_os_get_num_numa_nodes(index: c_int) -> c_int {
    let fd = unsafe { ihklib_os_open(index) };
    if fd < 0 { return unsafe { finish(fd, fd) }; }
    let result = unsafe { ioctl(fd, 0x112a34 as c_ulong) };
    let result = if result < 0 { unsafe { neg_errno() } } else { result };
    unsafe { finish(fd, result) }
}
#[cfg(not(ihklib_rusage_disabled))]
#[no_mangle]
pub unsafe extern "C" fn ihk_os_getrusage(index: c_int, usage: *mut IhkOsRusage, size: usize) -> c_int {
    if usage.is_null() { return -14; }
    if size != core::mem::size_of::<IhkOsRusage>() { return -22; }
    let mut storage = core::mem::MaybeUninit::<RusageRequest>::zeroed();
    let request = storage.as_mut_ptr();
    unsafe {
        core::ptr::addr_of_mut!((*request).rusage).write(usage);
        core::ptr::addr_of_mut!((*request).size_rusage).write(size);
    }
    let fd = unsafe { ihklib_os_open(index) };
    if fd < 0 { return unsafe { finish(fd, fd) }; }
    let result = unsafe { ioctl(fd, 0x11290106 as c_ulong, request) };
    let result = if result != 0 { unsafe { neg_errno() } } else { result };
    unsafe { finish(fd, result) }
}
#[cfg(ihklib_rusage_disabled)]
#[no_mangle]
pub unsafe extern "C" fn ihk_os_getrusage(_index: c_int, _usage: *mut IhkOsRusage, _size: usize) -> c_int { -38 }
// Future fixture can query the ACTUAL implementation's layout; not production exports.
#[cfg(ihklib_mcstat_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_mcstat_rusage_size() -> usize { core::mem::size_of::<IhkOsRusage>() }
#[cfg(ihklib_mcstat_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_mcstat_rusage_threads_offset() -> usize { core::mem::offset_of!(IhkOsRusage, num_threads) }
#[cfg(ihklib_mcstat_fixture)]
#[no_mangle]
pub extern "C" fn ihklib_mcstat_request_size() -> usize { core::mem::size_of::<RusageRequest>() }
