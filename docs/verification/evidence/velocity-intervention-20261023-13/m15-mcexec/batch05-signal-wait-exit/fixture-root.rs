// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
use core::ffi::{c_int,c_long,c_ulong,c_void};
unsafe extern "C" { fn getpid()->c_int;fn __errno_location()->*mut c_int;fn sendsig(sig:c_int,info:*mut c_void,context:*mut c_void); }
#[path="mcexec_signal_wait_exit.rs"]
mod mcexec_signal_wait_exit;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! {loop{}}
