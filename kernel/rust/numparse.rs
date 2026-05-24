use core::ptr::{read_volatile, write_volatile};

use crate::abi::{CInt, CLong, CULong};
use crate::string::{strlen, strnlen};

const EINVAL: CInt = 22;
const PAGE_SIZE: usize = 4096;
const ZEROPAD: CInt = 1;
const SIGN: CInt = 2;
const PLUS: CInt = 4;
const SPACE: CInt = 8;
const LEFT: CInt = 16;
const SMALL: CInt = 32;
const SPECIAL: CInt = 64;

const FORMAT_TYPE_NONE: CInt = 0;
const FORMAT_TYPE_WIDTH: CInt = 1;
const FORMAT_TYPE_PRECISION: CInt = 2;
const FORMAT_TYPE_CHAR: CInt = 3;
const FORMAT_TYPE_STR: CInt = 4;
const FORMAT_TYPE_PTR: CInt = 5;
const FORMAT_TYPE_PERCENT_CHAR: CInt = 6;
const FORMAT_TYPE_INVALID: CInt = 7;
const FORMAT_TYPE_LONG_LONG: CInt = 8;
const FORMAT_TYPE_ULONG: CInt = 9;
const FORMAT_TYPE_LONG: CInt = 10;
const FORMAT_TYPE_UBYTE: CInt = 11;
const FORMAT_TYPE_BYTE: CInt = 12;
const FORMAT_TYPE_USHORT: CInt = 13;
const FORMAT_TYPE_SHORT: CInt = 14;
const FORMAT_TYPE_UINT: CInt = 15;
const FORMAT_TYPE_INT: CInt = 16;
const FORMAT_TYPE_NRCHARS: CInt = 17;
const FORMAT_TYPE_SIZE_T: CInt = 18;
const FORMAT_TYPE_PTRDIFF: CInt = 19;
const FORMAT_TYPE_FLOAT: CInt = 20;

#[repr(C)]
pub struct PrintfSpec {
    pub type_: CInt,
    pub flags: CInt,
    pub field_width: CInt,
    pub base: CInt,
    pub precision: CInt,
    pub qualifier: CInt,
}

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

#[no_mangle]
pub unsafe extern "C" fn skip_atoi_result(s: *mut *const i8) -> CInt {
    let mut cp = read_volatile(s);
    let mut value: CInt = 0;

    while is_digit(read_char(cp)) {
        value = value
            .wrapping_mul(10)
            .wrapping_add((read_char(cp) - b'0') as CInt);
        cp = cp.add(1);
    }

    write_volatile(s, cp);
    value
}

#[inline(always)]
unsafe fn put_digit(buf: *mut i8, digit: u32) -> *mut i8 {
    write_volatile(buf, digit.wrapping_add(b'0' as u32) as i8);
    buf.add(1)
}

#[no_mangle]
pub unsafe extern "C" fn put_dec_trunc_result(mut buf: *mut i8, mut q: u32) -> *mut i8 {
    let mut d1 = (q >> 4) & 0xf;
    let mut d2 = (q >> 8) & 0xf;
    let mut d3 = q >> 12;

    let mut d0 = 6 * (d3 + d2 + d1) + (q & 0xf);
    q = (d0 * 0xcd) >> 11;
    d0 -= 10 * q;
    buf = put_digit(buf, d0);

    d1 += q + 9 * d3 + 5 * d2;
    if d1 != 0 {
        q = (d1 * 0xcd) >> 11;
        d1 -= 10 * q;
        buf = put_digit(buf, d1);

        d2 = q + 2 * d2;
        if d2 != 0 || d3 != 0 {
            q = (d2 * 0xd) >> 7;
            d2 -= 10 * q;
            buf = put_digit(buf, d2);

            d3 = q + 4 * d3;
            if d3 != 0 {
                q = (d3 * 0xcd) >> 11;
                d3 -= 10 * q;
                buf = put_digit(buf, d3);
                if q != 0 {
                    buf = put_digit(buf, q);
                }
            }
        }
    }

    buf
}

#[no_mangle]
pub unsafe extern "C" fn put_dec_full_result(mut buf: *mut i8, mut q: u32) -> *mut i8 {
    let mut d1 = (q >> 4) & 0xf;
    let mut d2 = (q >> 8) & 0xf;
    let mut d3 = q >> 12;

    let mut d0 = 6 * (d3 + d2 + d1) + (q & 0xf);
    q = (d0 * 0xcd) >> 11;
    d0 -= 10 * q;
    buf = put_digit(buf, d0);

    d1 += q + 9 * d3 + 5 * d2;
    q = (d1 * 0xcd) >> 11;
    d1 -= 10 * q;
    buf = put_digit(buf, d1);

    d2 = q + 2 * d2;
    q = (d2 * 0xd) >> 7;
    d2 -= 10 * q;
    buf = put_digit(buf, d2);

    d3 = q + 4 * d3;
    q = (d3 * 0xcd) >> 11;
    d3 -= 10 * q;
    buf = put_digit(buf, d3);
    put_digit(buf, q)
}

#[no_mangle]
pub unsafe extern "C" fn put_dec_result(mut buf: *mut i8, mut num: CULong) -> *mut i8 {
    loop {
        if num < 100_000 {
            return put_dec_trunc_result(buf, num as u32);
        }

        let rem = (num % 100_000) as u32;
        num /= 100_000;
        buf = put_dec_full_result(buf, rem);
    }
}

#[inline(always)]
unsafe fn write_char_if_room(ptr: *mut i8, end: *mut i8, ch: u8) {
    if (ptr as usize) < (end as usize) {
        write_volatile(ptr, ch as i8);
    }
}

#[no_mangle]
pub unsafe extern "C" fn number_result(
    mut buf: *mut i8,
    end: *mut i8,
    mut num: CULong,
    mut spec: PrintfSpec,
) -> *mut i8 {
    const DIGITS: &[u8; 16] = b"0123456789ABCDEF";
    let mut tmp = core::mem::MaybeUninit::<[i8; 66]>::uninit();
    let tmp_ptr = tmp.as_mut_ptr() as *mut i8;
    let mut sign = 0u8;
    let locase = (spec.flags & SMALL) as u8;
    let need_pfx = (spec.flags & SPECIAL) != 0 && spec.base != 10;
    let mut i: CInt = 0;

    if (spec.flags & LEFT) != 0 {
        spec.flags &= !ZEROPAD;
    }

    if (spec.flags & SIGN) != 0 {
        let signed = num as CLong;

        if signed < 0 {
            sign = b'-';
            num = signed.wrapping_neg() as CULong;
            spec.field_width -= 1;
        } else if (spec.flags & PLUS) != 0 {
            sign = b'+';
            spec.field_width -= 1;
        } else if (spec.flags & SPACE) != 0 {
            sign = b' ';
            spec.field_width -= 1;
        }
    }

    if need_pfx {
        spec.field_width -= 1;
        if spec.base == 16 {
            spec.field_width -= 1;
        }
    }

    if num == 0 {
        write_volatile(tmp_ptr, b'0' as i8);
        i = 1;
    } else if spec.base != 10 {
        let mask = (spec.base - 1) as CULong;
        let shift = if spec.base == 16 { 4 } else { 3 };

        while num != 0 {
            let digit = read_volatile(DIGITS.as_ptr().add((num & mask) as usize));
            write_volatile(tmp_ptr.add(i as usize), (digit | locase) as i8);
            i += 1;
            num >>= shift;
        }
    } else {
        i = put_dec_result(tmp_ptr, num).offset_from(tmp_ptr) as CInt;
    }

    if i > spec.precision {
        spec.precision = i;
    }

    spec.field_width -= spec.precision;
    if (spec.flags & (ZEROPAD | LEFT)) == 0 {
        loop {
            spec.field_width -= 1;
            if spec.field_width < 0 {
                break;
            }
            write_char_if_room(buf, end, b' ');
            buf = buf.add(1);
        }
    }

    if sign != 0 {
        write_char_if_room(buf, end, sign);
        buf = buf.add(1);
    }

    if need_pfx {
        write_char_if_room(buf, end, b'0');
        buf = buf.add(1);
        if spec.base == 16 {
            write_char_if_room(buf, end, b'X' | locase);
            buf = buf.add(1);
        }
    }

    if (spec.flags & LEFT) == 0 {
        let ch = if (spec.flags & ZEROPAD) != 0 {
            b'0'
        } else {
            b' '
        };

        loop {
            spec.field_width -= 1;
            if spec.field_width < 0 {
                break;
            }
            write_char_if_room(buf, end, ch);
            buf = buf.add(1);
        }
    }

    loop {
        spec.precision -= 1;
        if i > spec.precision {
            break;
        }
        write_char_if_room(buf, end, b'0');
        buf = buf.add(1);
    }

    loop {
        i -= 1;
        if i < 0 {
            break;
        }
        write_char_if_room(buf, end, read_volatile(tmp_ptr.add(i as usize)) as u8);
        buf = buf.add(1);
    }

    loop {
        spec.field_width -= 1;
        if spec.field_width < 0 {
            break;
        }
        write_char_if_room(buf, end, b' ');
        buf = buf.add(1);
    }

    buf
}

#[no_mangle]
pub unsafe extern "C" fn format_decode_result(fmt: *const i8, spec: *mut PrintfSpec) -> CInt {
    let start = fmt;
    let mut p = fmt;
    let spec_ref = &mut *spec;
    let mut skip_precision = false;

    if spec_ref.type_ == FORMAT_TYPE_WIDTH {
        if spec_ref.field_width < 0 {
            spec_ref.field_width = -spec_ref.field_width;
            spec_ref.flags |= LEFT;
        }
        spec_ref.type_ = FORMAT_TYPE_NONE;
    } else if spec_ref.type_ == FORMAT_TYPE_PRECISION {
        if spec_ref.precision < 0 {
            spec_ref.precision = 0;
        }
        spec_ref.type_ = FORMAT_TYPE_NONE;
        skip_precision = true;
    } else {
        spec_ref.type_ = FORMAT_TYPE_NONE;

        while read_char(p) != 0 {
            if read_char(p) == b'%' {
                break;
            }
            p = p.add(1);
        }

        if p != start || read_char(p) == 0 {
            return p.offset_from(start) as CInt;
        }

        spec_ref.flags = 0;
        loop {
            let found;

            p = p.add(1);
            match read_char(p) {
                b'-' => {
                    spec_ref.flags |= LEFT;
                    found = true;
                }
                b'+' => {
                    spec_ref.flags |= PLUS;
                    found = true;
                }
                b' ' => {
                    spec_ref.flags |= SPACE;
                    found = true;
                }
                b'#' => {
                    spec_ref.flags |= SPECIAL;
                    found = true;
                }
                b'0' => {
                    spec_ref.flags |= ZEROPAD;
                    found = true;
                }
                _ => {
                    found = false;
                }
            }

            if !found {
                break;
            }
        }

        spec_ref.field_width = -1;
        if is_digit(read_char(p)) {
            let mut width_ptr = p;
            spec_ref.field_width = skip_atoi_result(&mut width_ptr);
            p = width_ptr;
        } else if read_char(p) == b'*' {
            spec_ref.type_ = FORMAT_TYPE_WIDTH;
            return p.add(1).offset_from(start) as CInt;
        }
    }

    if !skip_precision {
        spec_ref.precision = -1;
        if read_char(p) == b'.' {
            p = p.add(1);
            if is_digit(read_char(p)) {
                let mut precision_ptr = p;
                spec_ref.precision = skip_atoi_result(&mut precision_ptr);
                p = precision_ptr;
                if spec_ref.precision < 0 {
                    spec_ref.precision = 0;
                }
            } else if read_char(p) == b'*' {
                spec_ref.type_ = FORMAT_TYPE_PRECISION;
                return p.add(1).offset_from(start) as CInt;
            }
        }
    }

    spec_ref.qualifier = -1;
    match read_char(p) {
        b'h' | b'l' | b'L' | b'Z' | b'z' | b't' => {
            spec_ref.qualifier = read_char(p) as CInt;
            p = p.add(1);
            if spec_ref.qualifier == read_char(p) as CInt {
                if spec_ref.qualifier == b'l' as CInt {
                    spec_ref.qualifier = b'L' as CInt;
                    p = p.add(1);
                } else if spec_ref.qualifier == b'h' as CInt {
                    spec_ref.qualifier = b'H' as CInt;
                    p = p.add(1);
                }
            }
        }
        _ => {}
    }

    spec_ref.base = 10;
    match read_char(p) {
        b'c' => {
            spec_ref.type_ = FORMAT_TYPE_CHAR;
            return p.add(1).offset_from(start) as CInt;
        }
        b's' => {
            spec_ref.type_ = FORMAT_TYPE_STR;
            return p.add(1).offset_from(start) as CInt;
        }
        b'f' => {
            spec_ref.base = 16;
            spec_ref.type_ = FORMAT_TYPE_FLOAT;
            return p.add(1).offset_from(start) as CInt;
        }
        b'p' => {
            spec_ref.type_ = FORMAT_TYPE_PTR;
            return p.offset_from(start) as CInt;
        }
        b'n' => {
            spec_ref.type_ = FORMAT_TYPE_NRCHARS;
            return p.add(1).offset_from(start) as CInt;
        }
        b'%' => {
            spec_ref.type_ = FORMAT_TYPE_PERCENT_CHAR;
            return p.add(1).offset_from(start) as CInt;
        }
        b'o' => {
            spec_ref.base = 8;
        }
        b'x' => {
            spec_ref.flags |= SMALL;
            spec_ref.base = 16;
        }
        b'X' => {
            spec_ref.base = 16;
        }
        b'd' | b'i' => {
            spec_ref.flags |= SIGN;
        }
        b'u' => {}
        _ => {
            spec_ref.type_ = FORMAT_TYPE_INVALID;
            return p.offset_from(start) as CInt;
        }
    }

    if spec_ref.qualifier == b'L' as CInt {
        spec_ref.type_ = FORMAT_TYPE_LONG_LONG;
    } else if spec_ref.qualifier == b'l' as CInt {
        if (spec_ref.flags & SIGN) != 0 {
            spec_ref.type_ = FORMAT_TYPE_LONG;
        } else {
            spec_ref.type_ = FORMAT_TYPE_ULONG;
        }
    } else if spec_ref.qualifier == b'Z' as CInt || spec_ref.qualifier == b'z' as CInt {
        spec_ref.type_ = FORMAT_TYPE_SIZE_T;
    } else if spec_ref.qualifier == b't' as CInt {
        spec_ref.type_ = FORMAT_TYPE_PTRDIFF;
    } else if spec_ref.qualifier == b'H' as CInt {
        if (spec_ref.flags & SIGN) != 0 {
            spec_ref.type_ = FORMAT_TYPE_BYTE;
        } else {
            spec_ref.type_ = FORMAT_TYPE_UBYTE;
        }
    } else if spec_ref.qualifier == b'h' as CInt {
        if (spec_ref.flags & SIGN) != 0 {
            spec_ref.type_ = FORMAT_TYPE_SHORT;
        } else {
            spec_ref.type_ = FORMAT_TYPE_USHORT;
        }
    } else if (spec_ref.flags & SIGN) != 0 {
        spec_ref.type_ = FORMAT_TYPE_INT;
    } else {
        spec_ref.type_ = FORMAT_TYPE_UINT;
    }

    p.add(1).offset_from(start) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn string_result(
    mut buf: *mut i8,
    end: *mut i8,
    mut s: *mut i8,
    spec: PrintfSpec,
) -> *mut i8 {
    static NULL_STRING: &[u8; 7] = b"<NULL>\0";

    if (s as usize) < PAGE_SIZE {
        s = NULL_STRING.as_ptr() as *mut i8;
    }

    let precision = if spec.precision < 0 {
        usize::MAX
    } else {
        spec.precision as usize
    };
    let len = strnlen(s, precision) as CInt;
    let pad = if spec.field_width > len {
        spec.field_width - len
    } else {
        0
    };

    if (spec.flags & LEFT) == 0 {
        let mut left_pad = pad;
        while left_pad > 0 {
            write_char_if_room(buf, end, b' ');
            buf = buf.add(1);
            left_pad -= 1;
        }
    }

    let mut copied = 0;
    while copied < len {
        write_char_if_room(buf, end, read_volatile(s.add(copied as usize)) as u8);
        buf = buf.add(1);
        copied += 1;
    }

    if (spec.flags & LEFT) != 0 {
        let mut right_pad = pad;
        while right_pad > 0 {
            write_char_if_room(buf, end, b' ');
            buf = buf.add(1);
            right_pad -= 1;
        }
    }

    buf
}
