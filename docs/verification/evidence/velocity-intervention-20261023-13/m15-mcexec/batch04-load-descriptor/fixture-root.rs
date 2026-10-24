// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
use core::ffi::{c_int,c_long,c_ulong,c_void};
unsafe extern "C" {
 fn malloc(n:usize)->*mut u8;
 fn sysconf(name:c_int)->c_long;
 fn mcexec_numa_local_body(cpu:*mut c_ulong,mask:*mut c_ulong,nonlocal:c_int);
 fn mcexec_numa_all_body(mask:*mut c_ulong);
}
#[path="mcexec_load_descriptor.rs"]
mod mcexec_load_descriptor;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! { loop {} }
