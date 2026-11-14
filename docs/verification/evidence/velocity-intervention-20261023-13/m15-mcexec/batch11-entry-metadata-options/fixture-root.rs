// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
use core::ffi::{c_int,c_ulong,c_void};
unsafe extern "C" {
 #[link_name="fd"]static mut MCEXEC_FD:c_int;
 fn __errno_location()->*mut c_int;
 fn ioctl(fd:c_int,cmd:c_ulong,...)->c_int;
 fn getpid()->c_int;fn perror(s:*const u8);
 fn mcexec_main_body(argc:c_int,args:*mut *mut u8)->c_int;
}
fn decimal_len_i32(value: i32) -> usize {
    if value == 0 {
        return 1;
    }

    let mut len = 0usize;
    let mut val = value as i64;
    if val < 0 {
        len += 1;
        val = -val;
    }
    while val > 0 {
        len += 1;
        val /= 10;
    }
    len
}
unsafe fn write_i32_decimal(dst: *mut u8, value: i32) -> usize {
    let mut out = dst;
    let mut val = value as i64;

    if val == 0 {
        unsafe {
            *out = b'0';
        }
        return 1;
    }

    if val < 0 {
        unsafe {
            *out = b'-';
            out = out.add(1);
        }
        val = -val;
    }

    let mut tmp = [0u8; 20];
    let mut digits = 0usize;
    while val > 0 {
        unsafe {
            *tmp.as_mut_ptr().add(digits) = b'0' + (val % 10) as u8;
        }
        digits += 1;
        val /= 10;
    }

    let mut idx = digits;
    while idx > 0 {
        idx -= 1;
        unsafe {
            *out = *tmp.as_ptr().add(idx);
            out = out.add(1);
        }
    }
    if value < 0 {
        digits + 1
    } else {
        digits
    }
}
#[path="mcexec_entry_metadata_options.rs"]mod mcexec_entry_metadata_options;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! {loop{}}
