use core::ffi::c_void;
use core::ptr::{null_mut, read_volatile, write_volatile};

use crate::abi::{CInt, CLong, CULong, SizeT};

type StringFlattenGetlongFn = unsafe extern "C" fn(*mut CLong, *const CLong) -> CLong;
type StringFlattenStrlenUserFn = unsafe extern "C" fn(*const i8) -> CInt;
type StringFlattenStrcpyFromUserFn = unsafe extern "C" fn(*mut i8, *const i8) -> CInt;
type StringFlattenAllocFn = unsafe extern "C" fn(SizeT, CULong) -> *mut c_void;

const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const STRING_ALLOC_FILE: &[u8] = b"kernel/rust/string.rs\0";
const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const LONG_SIZE: CLong = core::mem::size_of::<CLong>() as CLong;
const PTR_SIZE: CLong = core::mem::size_of::<*mut i8>() as CLong;

unsafe extern "C" {
    fn getlong_user(dest: *mut CLong, src: *const CLong) -> CLong;
    fn strlen_user(src: *const i8) -> CInt;
    fn strcpy_from_user(dst: *mut i8, src: *const i8) -> CInt;
    fn _kmalloc(size: CInt, flags: CInt, file: *mut i8, line: CInt) -> *mut c_void;
}

unsafe extern "C" fn string_flatten_alloc_bridge(size: SizeT, flags: CULong) -> *mut c_void {
    _kmalloc(
        size as CInt,
        flags as CInt,
        STRING_ALLOC_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

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
pub unsafe extern "C" fn __inline_memcpy(
    dest: *mut c_void,
    src: *const c_void,
    n: SizeT,
) -> *mut c_void {
    memcpy(dest, src, n)
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

#[inline(always)]
unsafe fn read_long(base: *const i8, index: CLong) -> CLong {
    read_volatile(base.cast::<CLong>().add(index as usize))
}

#[inline(always)]
unsafe fn write_long(base: *mut i8, index: CLong, value: CLong) {
    write_volatile(base.cast::<CLong>().add(index as usize), value);
}

#[inline(always)]
unsafe fn zero_bytes(mut ptr: *mut i8, mut len: CLong) {
    while len > 0 {
        write_char(ptr, 0);
        ptr = ptr.add(1);
        len -= 1;
    }
}

#[inline(always)]
unsafe fn copy_bytes(mut dst: *mut i8, mut src: *const i8, mut len: CLong) {
    while len > 0 {
        write_char(dst, read_char(src));
        dst = dst.add(1);
        src = src.add(1);
        len -= 1;
    }
}

#[inline(always)]
unsafe fn c_string_after(mut ptr: *mut i8) -> *mut i8 {
    while read_char(ptr) != 0 {
        ptr = ptr.add(1);
    }
    ptr.add(1)
}

#[no_mangle]
pub unsafe extern "C" fn flatten_strings_from_user_body_result(
    pre_strings: *mut i8,
    strings: *mut *mut i8,
    flat: *mut *mut i8,
    alloc_flags: CULong,
    getlong_fn: Option<StringFlattenGetlongFn>,
    strlen_user_fn: Option<StringFlattenStrlenUserFn>,
    strcpy_from_user_fn: Option<StringFlattenStrcpyFromUserFn>,
    alloc_fn: Option<StringFlattenAllocFn>,
) -> CInt {
    if flat.is_null() {
        return -EINVAL;
    }
    let Some(getlong_user) = getlong_fn else {
        return -EINVAL;
    };
    let Some(strlen_user) = strlen_user_fn else {
        return -EINVAL;
    };
    let Some(strcpy_from_user) = strcpy_from_user_fn else {
        return -EINVAL;
    };
    let Some(alloc) = alloc_fn else {
        return -EINVAL;
    };

    if strings.is_null() {
        let full_len = LONG_SIZE + PTR_SIZE;
        let allocated = alloc(full_len as SizeT, alloc_flags).cast::<i8>();
        if allocated.is_null() {
            return -ENOMEM;
        }
        zero_bytes(allocated, full_len);
        write_volatile(flat, allocated);
        return full_len as CInt;
    }

    let mut nr_strings: CLong = 0;
    loop {
        let mut user_ptr_value: CLong = 0;
        let ret = getlong_user(
            &mut user_ptr_value,
            strings.add(nr_strings as usize).cast::<CLong>(),
        );
        if ret < 0 {
            return ret as CInt;
        }
        if user_ptr_value == 0 {
            break;
        }
        nr_strings += 1;
    }

    let mut pre_strings_count: CLong = 0;
    let mut pre_strings_len: CLong = 0;
    let mut full_len = LONG_SIZE + PTR_SIZE;
    if !pre_strings.is_null() {
        pre_strings_count = read_long(pre_strings, 0);
        pre_strings_len =
            read_long(pre_strings, pre_strings_count + 1) - LONG_SIZE * (pre_strings_count + 2);
        full_len += pre_strings_count * LONG_SIZE + pre_strings_len;
    }

    let mut i: CLong = 0;
    while i < nr_strings {
        let mut user_ptr_value: CLong = 0;
        let ret = getlong_user(&mut user_ptr_value, strings.add(i as usize).cast::<CLong>());
        if ret < 0 {
            return ret as CInt;
        }

        let len = strlen_user(user_ptr_value as usize as *const i8);
        if len < 0 {
            return len;
        }
        full_len += PTR_SIZE + len as CLong + 1;
        i += 1;
    }

    full_len = (full_len + LONG_SIZE - 1) & !(LONG_SIZE - 1);
    let allocated = alloc(full_len as SizeT, alloc_flags).cast::<i8>();
    if allocated.is_null() {
        return -ENOMEM;
    }

    write_long(allocated, 0, nr_strings + pre_strings_count);
    let mut out = allocated.add(((nr_strings + pre_strings_count + 2) * LONG_SIZE) as usize);

    if !pre_strings.is_null() {
        let mut pre_i = 0;
        while pre_i < pre_strings_count {
            write_long(
                allocated,
                pre_i + 1,
                read_long(pre_strings, pre_i + 1) + nr_strings * LONG_SIZE,
            );
            pre_i += 1;
        }
        copy_bytes(
            out,
            pre_strings.add(read_long(pre_strings, 1) as usize),
            pre_strings_len,
        );
        out = out.add(pre_strings_len as usize);
    }

    i = 0;
    while i < nr_strings {
        let mut user_ptr_value: CLong = 0;
        write_long(
            allocated,
            i + pre_strings_count + 1,
            out.offset_from(allocated) as CLong,
        );

        let ret = getlong_user(&mut user_ptr_value, strings.add(i as usize).cast::<CLong>());
        if ret < 0 {
            return ret as CInt;
        }

        let _ = strcpy_from_user(out, user_ptr_value as usize as *const i8);
        out = c_string_after(out);
        i += 1;
    }

    write_long(
        allocated,
        nr_strings + pre_strings_count + 1,
        out.offset_from(allocated) as CLong,
    );
    write_volatile(flat, allocated);

    let len = out.offset_from(allocated) as CLong;
    if len < full_len {
        zero_bytes(out, full_len - len);
    }

    len as CInt
}

#[no_mangle]
pub unsafe extern "C" fn flatten_strings_from_user(
    pre_strings: *mut i8,
    strings: *mut *mut i8,
    flat: *mut *mut i8,
) -> CInt {
    flatten_strings_from_user_body_result(
        pre_strings,
        strings,
        flat,
        IHK_MC_AP_NOWAIT,
        Some(getlong_user),
        Some(strlen_user),
        Some(strcpy_from_user),
        Some(string_flatten_alloc_bridge),
    )
}
