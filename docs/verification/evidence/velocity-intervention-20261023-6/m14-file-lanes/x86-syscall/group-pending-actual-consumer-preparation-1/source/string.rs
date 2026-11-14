use core::ffi::c_void;
use core::ptr::{null_mut,read_volatile,write_volatile};
use crate::abi::{CInt,CLong,CULong,SizeT};

#[inline(always)]
unsafe fn read_char(ptr: *const i8) -> i8 {
    read_volatile(ptr)
}

#[inline(always)]
unsafe fn write_char(ptr: *mut i8, value: i8) {
    write_volatile(ptr, value);
}

#[inline(always)]
fn char_diff(left: i8, right: i8) -> CInt {
    left as CInt - right as CInt
}

#[no_mangle]
pub unsafe extern "C" fn strlen(mut ptr: *const i8) -> SizeT {
    let head = ptr;

    while read_char(ptr) != 0 {
        ptr = ptr.add(1);
    }

    ptr.offset_from(head) as SizeT
}

#[no_mangle]
pub unsafe extern "C" fn strcpy(mut dest: *mut i8, mut src: *const i8) -> *mut i8 {
    let head = dest;

    loop {
        let ch = read_char(src);
        write_char(dest, ch);
        dest = dest.add(1);
        src = src.add(1);
        if ch == 0 {
            break;
        }
    }

    head
}

#[no_mangle]
pub unsafe extern "C" fn strcmp(mut s1: *const i8, mut s2: *const i8) -> CInt {
    while read_char(s1) != 0 && read_char(s1) == read_char(s2) {
        s1 = s1.add(1);
        s2 = s2.add(1);
    }

    char_diff(read_char(s1), read_char(s2))
}

#[no_mangle]
pub unsafe extern "C" fn memcpy(
    dest: *mut c_void,
    src: *const c_void,
    mut n: SizeT,
) -> *mut c_void {
    let mut dst = dest.cast::<u8>();
    let mut srcp = src.cast::<u8>();

    while n > 0 {
        write_volatile(dst, read_volatile(srcp));
        dst = dst.add(1);
        srcp = srcp.add(1);
        n -= 1;
    }

    dest
}

#[no_mangle]
pub unsafe extern "C" fn __inline_memcpy(
    dest: *mut c_void,
    src: *const c_void,
    n: SizeT,
) -> *mut c_void {
    memcpy(dest, src, n)
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

#[no_mangle]
pub unsafe extern "C" fn __inline_memset(
    s: *mut c_void,
    c: CULong,
    mut count: SizeT,
) -> *mut c_void {
    let mut ptr = s.cast::<u8>();
    let bytes = (c as u32).to_le_bytes();

    while count >= 4 {
        write_volatile(ptr, bytes[0]);
        write_volatile(ptr.add(1), bytes[1]);
        write_volatile(ptr.add(2), bytes[2]);
        write_volatile(ptr.add(3), bytes[3]);
        ptr = ptr.add(4);
        count -= 4;
    }
    if count >= 2 {
        write_volatile(ptr, bytes[0]);
        write_volatile(ptr.add(1), bytes[1]);
        ptr = ptr.add(2);
        count -= 2;
    }
    if count != 0 {
        write_volatile(ptr, bytes[0]);
    }

    s
}
