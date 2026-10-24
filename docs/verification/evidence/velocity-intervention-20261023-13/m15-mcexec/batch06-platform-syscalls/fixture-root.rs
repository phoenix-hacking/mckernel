// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Reused errno/generic bodies and ABI structs below are exact reference extractions.
#![no_std]
use core::ffi::{c_int,c_long,c_ulong,c_void};
#[repr(C)]
pub struct McexecSyscallRequest {
    rtid: c_int,
    ttid: c_int,
    valid: c_ulong,
    number: c_ulong,
    args: [c_ulong; 6],
}
#[repr(C)]
pub struct McexecSyscallWaitDesc {
    cpu: c_ulong,
    sr: McexecSyscallRequest,
    pid: c_int,
}
#[repr(C)]
struct McexecTimespec {
    tv_sec: c_long,
    tv_nsec: c_long,
}
unsafe extern "C" {
 fn __errno_location()->*mut c_int;
 fn access(p:*const u8,m:c_int)->c_int;
 fn readlink(p:*const u8,b:*mut u8,n:usize)->isize;
 fn ioctl(fd:c_int,r:c_ulong,...)->c_int;
 fn syscall(number:c_long,...)->c_long;
    fn mcexec_path_readlinkat_bridge(
        dirfd: c_int,
        path: *const u8,
        buf: *mut u8,
        size: usize,
    ) -> c_long;
    fn mcexec_path_readlink_bridge(path: *const u8, buf: *mut u8, size: usize) -> c_long;
    fn mcexec_path_fstatat_bridge(
        dirfd: c_int,
        path: *const u8,
        statbuf: *mut c_void,
        flags: c_int,
    ) -> c_long;
    fn mcexec_path_stat_bridge(path: *const u8, statbuf: *mut c_void) -> c_long;
    fn mcexec_path_faccessat_bridge(
        dirfd: c_int,
        path: *const u8,
        mode: c_int,
        flags: c_int,
    ) -> c_long;
    fn mcexec_path_access_bridge(path: *const u8, mode: c_int) -> c_long;
    fn mcexec_path_getxattr_bridge(
        path: *const u8,
        name: *const u8,
        value: *mut c_void,
        size: usize,
    ) -> c_long;
    fn mcexec_path_lgetxattr_bridge(
        path: *const u8,
        name: *const u8,
        value: *mut c_void,
        size: usize,
    ) -> c_long;
    fn mcexec_path_openat_log_bridge(dirfd: c_int, path: *const u8, tid: c_int);
    fn mcexec_path_open_log_bridge(path: *const u8);
    fn mcexec_path_openat_bridge(
        dirfd: c_int,
        path: *const u8,
        flags: c_ulong,
        mode: c_ulong,
    ) -> c_long;
    fn mcexec_path_open_bridge(path: *const u8, flags: c_ulong, mode: c_ulong) -> c_long;
    fn mcexec_cred_get_bridge(fd: c_int, arg: c_ulong);
    fn mcexec_cred_setfsuid_bridge(uid: c_ulong) -> c_long;
    fn mcexec_cred_setfsgid_bridge(gid: c_ulong) -> c_long;
    fn mcexec_cred_setresuid_bridge(ruid: c_ulong, euid: c_ulong, suid: c_ulong) -> c_long;
    fn mcexec_cred_setresgid_bridge(rgid: c_ulong, egid: c_ulong, sgid: c_ulong) -> c_long;
    fn mcexec_cred_setreuid_bridge(ruid: c_ulong, euid: c_ulong) -> c_long;
    fn mcexec_cred_setregid_bridge(rgid: c_ulong, egid: c_ulong) -> c_long;
    fn mcexec_cred_setuid_bridge(uid: c_ulong) -> c_long;
    fn mcexec_cred_setgid_bridge(gid: c_ulong) -> c_long;
    fn mcexec_do_generic_syscall_raw_bridge(w: *const McexecSyscallWaitDesc) -> c_long;
    fn mcexec_do_generic_syscall_start_bridge(number: c_ulong);
    fn mcexec_do_generic_syscall_done_bridge(number: c_ulong, ret: c_long);
    fn mcexec_do_generic_syscall_bridge(w: *const McexecSyscallWaitDesc) -> c_long;
    fn mcexec_perf_event_open_bridge() -> c_long;
    fn mcexec_clock_gettime_bridge(clock_id: c_int, tv: *mut McexecTimespec) -> c_long;
    fn mcexec_clock_gettime_log_bridge(sec: c_long, nsec: c_long);
}
#[no_mangle]
pub extern "C" fn mcexec_errno_return_result(ret: i64, errno_value: i32) -> i64 {
    if ret == -1 {
        -(errno_value as i64)
    } else {
        ret
    }
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_do_generic_syscall_body(w: *const McexecSyscallWaitDesc) -> c_long {
    let number = unsafe { (*w).sr.number };
    unsafe { mcexec_do_generic_syscall_start_bridge(number) };
    let ret = unsafe { mcexec_do_generic_syscall_raw_bridge(w) };
    let shaped = mcexec_errno_return_result(ret, unsafe { *__errno_location() });
    unsafe { mcexec_do_generic_syscall_done_bridge(number, shaped) };
    shaped
}
#[cfg(mcexec_platform_candidate)]
#[path="mcexec_platform_syscalls.rs"]
mod mcexec_platform_syscalls;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! {loop{}}
