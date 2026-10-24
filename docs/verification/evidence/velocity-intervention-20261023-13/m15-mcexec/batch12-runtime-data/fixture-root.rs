// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
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
pub struct McexecListHead {
    next: *mut McexecListHead,
    prev: *mut McexecListHead,
}
#[path="mcexec_runtime_data.rs"]mod mcexec_runtime_data;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! {loop{}}
