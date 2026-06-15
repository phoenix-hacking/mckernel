#![no_std]

use core::ffi::{c_char, c_int, c_uint};

const SIZE: usize = 10_000;

#[no_mangle]
pub static mut a: [f64; SIZE] = [0.0; SIZE];
#[no_mangle]
pub static mut b: [f64; SIZE] = [0.0; SIZE];
#[no_mangle]
pub static mut c: [f64; SIZE] = [0.0; SIZE];

unsafe extern "C" {
    fn getpid() -> c_int;
    fn printf(format: *const c_char, ...) -> c_int;
    fn sleep(seconds: c_uint) -> c_uint;
}

fn cstr(bytes: &'static [u8]) -> *const c_char {
    bytes.as_ptr() as *const c_char
}

#[no_mangle]
pub unsafe extern "C" fn main() -> c_int {
    unsafe {
        printf(cstr(b"invoked\n\0"));
    }

    let mut i = 0;
    while i < 3 {
        unsafe {
            sleep(1);
            printf(cstr(b"wakeup %d\n\0"), i);
        }
        i += 1;
    }

    unsafe {
        printf(cstr(b"getpid 1000 times\n\0"));
    }

    i = 0;
    while i < 1000 {
        unsafe {
            getpid();
        }
        i += 1;
    }

    i = 0;
    while i < SIZE {
        unsafe {
            *(core::ptr::addr_of_mut!(a) as *mut f64).add(i) = 0.0;
            *(core::ptr::addr_of_mut!(b) as *mut f64).add(i) = 1.0;
            *(core::ptr::addr_of_mut!(c) as *mut f64).add(i) = 3.0;
        }
        i += 1;
    }

    let mut j = 0;
    while j < 1000 {
        i = 0;
        while i < SIZE {
            unsafe {
                *(core::ptr::addr_of_mut!(a) as *mut f64).add(i) =
                    *(core::ptr::addr_of!(b) as *const f64).add(i)
                        / *(core::ptr::addr_of!(c) as *const f64).add(i);
            }
            i += 1;
        }
        j += 1;
    }

    unsafe {
        printf(cstr(b"done\n\0"));
    }
    0
}
