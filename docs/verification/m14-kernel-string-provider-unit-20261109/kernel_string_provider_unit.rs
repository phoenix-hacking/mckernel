#![no_std]
// Exact two actual kernel string roots and their private inline helper only.
// No whole string module, builtins workaround, provider callback or runtime init.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
use abi::{CInt, SizeT};
use core::ffi::c_void;
use core::ptr::{read_volatile, write_volatile};

#[inline(always)]
unsafe fn read_char(ptr: *const i8) -> i8 {
    read_volatile(ptr)
}

#[no_mangle]
pub unsafe extern "C" fn strnlen(mut ptr: *const i8, mut maxlen: SizeT) -> SizeT {
    let head = ptr;

    while read_char(ptr) != 0 && maxlen > 0 {
        ptr = ptr.add(1);
        maxlen -= 1;
    }

    ptr.offset_from(head) as SizeT
}

#[no_mangle]
pub unsafe extern "C" fn memset(s: *mut c_void, c: CInt, mut n: SizeT) -> *mut c_void {
    let mut ptr = s.cast::<u8>();
    let byte = c as u8;

    while n > 0 {
        write_volatile(ptr, byte);
        ptr = ptr.add(1);
        n -= 1;
    }

    s
}
