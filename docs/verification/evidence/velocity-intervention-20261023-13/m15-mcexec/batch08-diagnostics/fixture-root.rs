// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
use core::ffi::{c_int,c_long,c_ulong,c_void};
unsafe extern "C" {fn __errno_location()->*mut c_int;fn perror(s:*const u8);}
#[path="mcexec_diagnostics.rs"]mod mcexec_diagnostics;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! {loop{}}
