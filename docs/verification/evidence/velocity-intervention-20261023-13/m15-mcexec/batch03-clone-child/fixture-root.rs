// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// ABI structs extracted verbatim; all external orchestration providers are fixture stubs.
#![no_std]
use core::ffi::{c_int,c_long,c_ulong,c_void};
#[repr(C)]
pub struct McexecThreadData {
    next: *mut McexecThreadData,
    thread_id: usize,
    cpu: i32,
    ret: i32,
    tid: i32,
    terminate: i32,
    remote_tid: i32,
    remote_cpu: i32,
    joined: i32,
    detached: i32,
    lock: *mut u8,
    init_ready: *mut u8,
}
#[repr(C)]
pub struct ForkSync {
    status: i32,
    success: i32,
}
#[repr(C)]
pub struct ForkSyncContainer {
    pid: i32,
    next: *mut ForkSyncContainer,
    fs: *mut ForkSync,
}
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
unsafe extern "C" {
 #[link_name="fd"] static mut MCEXEC_FD:c_int;
 #[link_name="n_threads"] static mut MCEXEC_N_THREADS:c_int;
 #[link_name="thread_data"] static mut MCEXEC_THREAD_DATA:*mut McexecThreadData;
 #[link_name="fork_sync_top"] static mut MCEXEC_FORK_SYNC_TOP:*mut ForkSyncContainer;
 fn malloc(n:usize)->*mut u8;
 fn free(p:*mut u8);
 fn close(fd:c_int)->c_int;
 fn __errno_location()->*mut c_int;
 fn ioctl(fd:c_int,request:c_ulong,...)->c_int;
 fn getpid()->c_int;
 fn mcexec_opendev_body()->c_int;
 fn mcexec_opendev_dev_bridge()->*mut u8;
 fn init_sigaction();
 fn init_worker_threads(fd:c_int)->c_int;
 fn mcexec_join_all_threads_body();
}
#[path="mcexec_clone_child.rs"]
mod mcexec_clone_child;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! { loop {} }
