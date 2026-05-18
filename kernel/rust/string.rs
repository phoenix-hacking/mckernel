use core::ffi::c_void;
use core::ptr::{null_mut, read_volatile, write_volatile};

use crate::abi::{CInt, CULong, SizeT};

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
pub unsafe extern "C" fn strnlen(mut ptr: *const i8, mut maxlen: SizeT) -> SizeT {
    let head = ptr;

    while read_char(ptr) != 0 && maxlen > 0 {
        ptr = ptr.add(1);
        maxlen -= 1;
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
pub unsafe extern "C" fn strncpy(mut dest: *mut i8, mut src: *const i8, maxlen: SizeT) -> *mut i8 {
    let head = dest;
    let mut len = maxlen as isize;

    if len <= 0 {
        return head;
    }

    loop {
        let ch = read_char(src);
        write_char(dest, ch);
        dest = dest.add(1);
        src = src.add(1);

        if ch != 0 {
            len -= 1;
            if len != 0 {
                continue;
            }
        }
        break;
    }

    if len > 0 {
        loop {
            len -= 1;
            if len == 0 {
                break;
            }
            write_char(dest, 0);
            dest = dest.add(1);
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
pub unsafe extern "C" fn strncmp(mut s1: *const i8, mut s2: *const i8, mut n: SizeT) -> CInt {
    while read_char(s1) != 0 && read_char(s1) == read_char(s2) && n > 1 {
        s1 = s1.add(1);
        s2 = s2.add(1);
        n -= 1;
    }

    char_diff(read_char(s1), read_char(s2))
}

#[no_mangle]
pub unsafe extern "C" fn strchr(s: *const i8, needle: CInt) -> *mut i8 {
    let mut ptr = s as *mut i8;

    loop {
        let ch = read_char(ptr);
        if ch as CInt == needle {
            return ptr;
        }
        if ch == 0 {
            break;
        }
        ptr = ptr.add(1);
    }

    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn strrchr(s: *const i8, needle: CInt) -> *mut i8 {
    let mut ptr = s;
    let mut last = null_mut();

    loop {
        let ch = read_char(ptr);
        if ch as CInt == needle {
            last = ptr as *mut i8;
        }
        ptr = ptr.add(1);
        if ch == 0 {
            break;
        }
    }

    last
}

#[no_mangle]
pub unsafe extern "C" fn strpbrk(s: *const i8, accept: *const i8) -> *mut i8 {
    let mut ptr = s;

    loop {
        let sch = read_char(ptr);
        let mut cursor = accept;

        while read_char(cursor) != 0 {
            if sch == read_char(cursor) {
                return ptr as *mut i8;
            }
            cursor = cursor.add(1);
        }

        ptr = ptr.add(1);
        if sch == 0 {
            break;
        }
    }

    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn strstr(mut haystack: *const i8, needle: *const i8) -> *mut i8 {
    let len = strlen(needle) as CInt;

    while read_char(haystack) != 0 {
        if strncmp(haystack, needle, len as SizeT) == 0 {
            return haystack as *mut i8;
        }
        haystack = haystack.add(1);
    }

    null_mut()
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
pub unsafe extern "C" fn memcpy_long(
    dest: *mut c_void,
    src: *const c_void,
    mut n: SizeT,
) -> *mut c_void {
    let mut dst = dest.cast::<CULong>();
    let mut srcp = src.cast::<CULong>();

    n /= core::mem::size_of::<CULong>();
    while n > 0 {
        write_volatile(dst, read_volatile(srcp));
        dst = dst.add(1);
        srcp = srcp.add(1);
        n -= 1;
    }

    dest
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
pub unsafe extern "C" fn memcmp(s1: *const c_void, s2: *const c_void, mut n: SizeT) -> CInt {
    let mut p1 = s1.cast::<i8>();
    let mut p2 = s2.cast::<i8>();

    while read_char(p1) == read_char(p2) && n > 1 {
        p1 = p1.add(1);
        p2 = p2.add(1);
        n -= 1;
    }

    char_diff(read_char(p1), read_char(p2))
}
