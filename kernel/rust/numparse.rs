use core::ptr::{read_volatile, write_volatile};

use crate::abi::{CInt, CLong, CULong};
use crate::string::strlen;

const EINVAL: CInt = 22;

#[inline(always)]
unsafe fn read_char(ptr: *const i8) -> u8 {
    read_volatile(ptr) as u8
}

#[inline(always)]
fn tolower(ch: u8) -> u8 {
    ch | 0x20
}

#[inline(always)]
fn is_digit(ch: u8) -> bool {
    ch.is_ascii_digit()
}

#[inline(always)]
fn is_xdigit(ch: u8) -> bool {
    ch.is_ascii_digit() || (b'a'..=b'f').contains(&ch) || (b'A'..=b'F').contains(&ch)
}

#[inline(always)]
fn digit_value(ch: u8) -> CULong {
    if is_digit(ch) {
        (ch - b'0') as CULong
    } else {
        (tolower(ch).wrapping_sub(b'a') + 10) as CULong
    }
}

#[inline(always)]
unsafe fn simple_guess_base(cp: *const i8) -> u32 {
    if read_char(cp) == b'0' {
        if tolower(read_char(cp.add(1))) == b'x' && is_xdigit(read_char(cp.add(2))) {
            16
        } else {
            8
        }
    } else {
        10
    }
}

#[no_mangle]
pub unsafe extern "C" fn simple_strtoul(
    mut cp: *const i8,
    endp: *mut *mut i8,
    mut base: u32,
) -> CULong {
    let mut result: CULong = 0;

    if base == 0 {
        base = simple_guess_base(cp);
    }

    if base == 16 && read_char(cp) == b'0' && tolower(read_char(cp.add(1))) == b'x' {
        cp = cp.add(2);
    }

    while is_xdigit(read_char(cp)) {
        let value = digit_value(read_char(cp));

        if value >= base as CULong {
            break;
        }
        result = result.wrapping_mul(base as CULong).wrapping_add(value);
        cp = cp.add(1);
    }

    if !endp.is_null() {
        write_volatile(endp, cp as *mut i8);
    }
    result
}

#[no_mangle]
pub unsafe extern "C" fn simple_strtol(cp: *const i8, endp: *mut *mut i8, base: u32) -> CLong {
    if read_char(cp) == b'-' {
        0u64.wrapping_sub(simple_strtoul(cp.add(1), endp, base)) as CLong
    } else {
        simple_strtoul(cp, endp, base) as CLong
    }
}

#[no_mangle]
pub unsafe extern "C" fn simple_strtoull(cp: *const i8, endp: *mut *mut i8, base: u32) -> CULong {
    simple_strtoul(cp, endp, base)
}

#[no_mangle]
pub unsafe extern "C" fn simple_strtoll(cp: *const i8, endp: *mut *mut i8, base: u32) -> CLong {
    if read_char(cp) == b'-' {
        0u64.wrapping_sub(simple_strtoull(cp.add(1), endp, base)) as CLong
    } else {
        simple_strtoull(cp, endp, base) as CLong
    }
}

#[no_mangle]
pub unsafe extern "C" fn strict_strtoul(cp: *const i8, base: u32, res: *mut CULong) -> CInt {
    let mut tail = core::ptr::null_mut();

    write_volatile(res, 0);
    let len = strlen(cp);
    if len == 0 {
        return -EINVAL;
    }

    let val = simple_strtoul(cp, &mut tail, base);
    if tail == cp as *mut i8 {
        return -EINVAL;
    }

    let tail_ch = read_char(tail);
    if tail_ch == 0 || (len == tail.offset_from(cp as *mut i8) as usize + 1 && tail_ch == b'\n') {
        write_volatile(res, val);
        return 0;
    }

    -EINVAL
}

#[no_mangle]
pub unsafe extern "C" fn strict_strtol(cp: *const i8, base: u32, res: *mut CLong) -> CInt {
    let ret = if read_char(cp) == b'-' {
        strict_strtoul(cp.add(1), base, res as *mut CULong)
    } else {
        strict_strtoul(cp, base, res as *mut CULong)
    };

    if ret == 0 && read_char(cp) == b'-' {
        write_volatile(
            res,
            0u64.wrapping_sub(read_volatile(res) as CULong) as CLong,
        );
    }

    ret
}

#[no_mangle]
pub unsafe extern "C" fn strict_strtoull(cp: *const i8, base: u32, res: *mut CULong) -> CInt {
    strict_strtoul(cp, base, res)
}

#[no_mangle]
pub unsafe extern "C" fn strict_strtoll(cp: *const i8, base: u32, res: *mut CLong) -> CInt {
    let ret = if read_char(cp) == b'-' {
        strict_strtoull(cp.add(1), base, res as *mut CULong)
    } else {
        strict_strtoull(cp, base, res as *mut CULong)
    };

    if ret == 0 && read_char(cp) == b'-' {
        write_volatile(
            res,
            0u64.wrapping_sub(read_volatile(res) as CULong) as CLong,
        );
    }

    ret
}

#[no_mangle]
pub unsafe extern "C" fn strtol(cp: *const i8, endp: *mut *mut i8, base: u32) -> CULong {
    simple_strtol(cp, endp, base) as CULong
}
