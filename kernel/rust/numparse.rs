use core::ffi::{c_void, VaList};
use core::ptr::{read_volatile, write_volatile};

use crate::abi::{CInt, CLong, CULong, SizeT};
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

const CTYPE_U: u8 = 0x01;
const CTYPE_L: u8 = 0x02;
const CTYPE_D: u8 = 0x04;
const CTYPE_C: u8 = 0x08;
const CTYPE_P: u8 = 0x10;
const CTYPE_S: u8 = 0x20;
const CTYPE_X: u8 = 0x40;
const CTYPE_SP: u8 = 0x80;

#[allow(non_upper_case_globals)]
#[no_mangle]
pub static _ctype: [u8; 256] = make_ctype();

#[inline(always)]
fn ctype_mask(c: CInt) -> u8 {
    _ctype[c as u8 as usize]
}

#[inline(always)]
fn ctype_test(c: CInt, mask: u8) -> CInt {
    ((ctype_mask(c) & mask) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn __ismask(c: CInt) -> u8 {
    ctype_mask(c)
}

#[no_mangle]
pub extern "C" fn isalnum(c: CInt) -> CInt {
    ctype_test(c, CTYPE_U | CTYPE_L | CTYPE_D)
}

#[no_mangle]
pub extern "C" fn isalpha(c: CInt) -> CInt {
    ctype_test(c, CTYPE_U | CTYPE_L)
}

#[no_mangle]
pub extern "C" fn iscntrl(c: CInt) -> CInt {
    ctype_test(c, CTYPE_C)
}

#[no_mangle]
pub extern "C" fn isdigit(c: CInt) -> CInt {
    ctype_test(c, CTYPE_D)
}

#[no_mangle]
pub extern "C" fn isgraph(c: CInt) -> CInt {
    ctype_test(c, CTYPE_P | CTYPE_U | CTYPE_L | CTYPE_D)
}

#[no_mangle]
pub extern "C" fn islower(c: CInt) -> CInt {
    ctype_test(c, CTYPE_L)
}

#[no_mangle]
pub extern "C" fn isprint(c: CInt) -> CInt {
    ctype_test(c, CTYPE_P | CTYPE_U | CTYPE_L | CTYPE_D | CTYPE_SP)
}

#[no_mangle]
pub extern "C" fn ispunct(c: CInt) -> CInt {
    ctype_test(c, CTYPE_P)
}

#[no_mangle]
pub extern "C" fn isspace(c: CInt) -> CInt {
    ctype_test(c, CTYPE_S)
}

#[no_mangle]
pub extern "C" fn isupper(c: CInt) -> CInt {
    ctype_test(c, CTYPE_U)
}

#[no_mangle]
pub extern "C" fn isxdigit(c: CInt) -> CInt {
    ctype_test(c, CTYPE_D | CTYPE_X)
}

#[no_mangle]
pub extern "C" fn isascii(c: CInt) -> CInt {
    ((c as u8) <= 0x7f) as CInt
}

#[no_mangle]
pub extern "C" fn toascii(c: CInt) -> CInt {
    (c as u8 & 0x7f) as CInt
}

#[no_mangle]
pub extern "C" fn __tolower(c: u8) -> u8 {
    if isupper(c as CInt) != 0 {
        c.wrapping_add(b'a' - b'A')
    } else {
        c
    }
}

#[no_mangle]
pub extern "C" fn __toupper(c: u8) -> u8 {
    if islower(c as CInt) != 0 {
        c.wrapping_sub(b'a' - b'A')
    } else {
        c
    }
}

#[no_mangle]
pub extern "C" fn tolower(c: CInt) -> CInt {
    __tolower(c as u8) as CInt
}

#[no_mangle]
pub extern "C" fn toupper(c: CInt) -> CInt {
    __toupper(c as u8) as CInt
}

const fn ctype_at(i: usize) -> u8 {
    match i {
        0..=8 => CTYPE_C,
        9..=13 => CTYPE_C | CTYPE_S,
        14..=31 => CTYPE_C,
        32 => CTYPE_S | CTYPE_SP,
        33..=47 => CTYPE_P,
        48..=57 => CTYPE_D,
        58..=64 => CTYPE_P,
        65..=70 => CTYPE_U | CTYPE_X,
        71..=90 => CTYPE_U,
        91..=96 => CTYPE_P,
        97..=102 => CTYPE_L | CTYPE_X,
        103..=122 => CTYPE_L,
        123..=126 => CTYPE_P,
        127 => CTYPE_C,
        128..=159 => 0,
        160 => CTYPE_S | CTYPE_SP,
        161..=191 => CTYPE_P,
        192..=214 => CTYPE_U,
        215 => CTYPE_P,
        216..=222 => CTYPE_U,
        223..=246 => CTYPE_L,
        247 => CTYPE_P,
        248..=255 => CTYPE_L,
        _ => 0,
    }
}

const fn make_ctype() -> [u8; 256] {
    let mut table = [0u8; 256];
    let mut i = 0usize;

    while i < 256 {
        table[i] = ctype_at(i);
        i += 1;
    }

    table
}

#[repr(C)]
#[derive(Clone, Copy)]
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
fn ascii_lower(ch: u8) -> u8 {
    ch | 0x20
}

#[inline(always)]
fn is_digit(ch: u8) -> bool {
    ch.is_ascii_digit()
}

#[inline(always)]
fn is_space(ch: u8) -> bool {
    matches!(ch, b'\t' | b'\n' | 0x0b | 0x0c | b'\r' | b' ' | 0xa0)
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
        (ascii_lower(ch).wrapping_sub(b'a') + 10) as CULong
    }
}

#[inline(always)]
unsafe fn simple_guess_base(cp: *const i8) -> u32 {
    if read_char(cp) == b'0' {
        if ascii_lower(read_char(cp.add(1))) == b'x' && is_xdigit(read_char(cp.add(2))) {
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

    if base == 16 && read_char(cp) == b'0' && ascii_lower(read_char(cp.add(1))) == b'x' {
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

unsafe fn number_ref_result(
    mut buf: *mut i8,
    end: *mut i8,
    mut num: CULong,
    spec: *const PrintfSpec,
) -> *mut i8 {
    const DIGITS: &[u8; 16] = b"0123456789ABCDEF";
    let mut tmp = core::mem::MaybeUninit::<[i8; 66]>::uninit();
    let tmp_ptr = tmp.as_mut_ptr() as *mut i8;
    let mut flags = read_volatile(&(*spec).flags);
    let mut field_width = read_volatile(&(*spec).field_width);
    let base = read_volatile(&(*spec).base);
    let mut precision = read_volatile(&(*spec).precision);
    let mut sign = 0u8;
    let locase = (flags & SMALL) as u8;
    let need_pfx = (flags & SPECIAL) != 0 && base != 10;
    let mut i: CInt = 0;

    if (flags & LEFT) != 0 {
        flags &= !ZEROPAD;
    }

    if (flags & SIGN) != 0 {
        let signed = num as CLong;

        if signed < 0 {
            sign = b'-';
            num = signed.wrapping_neg() as CULong;
            field_width -= 1;
        } else if (flags & PLUS) != 0 {
            sign = b'+';
            field_width -= 1;
        } else if (flags & SPACE) != 0 {
            sign = b' ';
            field_width -= 1;
        }
    }

    if need_pfx {
        field_width -= 1;
        if base == 16 {
            field_width -= 1;
        }
    }

    if num == 0 {
        write_volatile(tmp_ptr, b'0' as i8);
        i = 1;
    } else if base != 10 {
        let mask = (base - 1) as CULong;
        let shift = if base == 16 { 4 } else { 3 };

        while num != 0 {
            let digit = read_volatile(DIGITS.as_ptr().add((num & mask) as usize));
            write_volatile(tmp_ptr.add(i as usize), (digit | locase) as i8);
            i += 1;
            num >>= shift;
        }
    } else {
        i = put_dec_result(tmp_ptr, num).offset_from(tmp_ptr) as CInt;
    }

    if i > precision {
        precision = i;
    }

    field_width -= precision;
    if (flags & (ZEROPAD | LEFT)) == 0 {
        loop {
            field_width -= 1;
            if field_width < 0 {
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
        if base == 16 {
            write_char_if_room(buf, end, b'X' | locase);
            buf = buf.add(1);
        }
    }

    if (flags & LEFT) == 0 {
        let ch = if (flags & ZEROPAD) != 0 { b'0' } else { b' ' };

        loop {
            field_width -= 1;
            if field_width < 0 {
                break;
            }
            write_char_if_room(buf, end, ch);
            buf = buf.add(1);
        }
    }

    loop {
        precision -= 1;
        if i > precision {
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
        field_width -= 1;
        if field_width < 0 {
            break;
        }
        write_char_if_room(buf, end, b' ');
        buf = buf.add(1);
    }

    buf
}

#[no_mangle]
pub unsafe extern "C" fn number_result(
    buf: *mut i8,
    end: *mut i8,
    num: CULong,
    mut spec: PrintfSpec,
) -> *mut i8 {
    number_ref_result(buf, end, num, &mut spec)
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

unsafe fn string_ref_result(
    mut buf: *mut i8,
    end: *mut i8,
    mut s: *mut i8,
    spec: *const PrintfSpec,
) -> *mut i8 {
    static NULL_STRING: &[u8; 7] = b"<NULL>\0";
    let flags = read_volatile(&(*spec).flags);
    let field_width = read_volatile(&(*spec).field_width);
    let spec_precision = read_volatile(&(*spec).precision);

    if (s as usize) < PAGE_SIZE {
        s = NULL_STRING.as_ptr() as *mut i8;
    }

    let precision = if spec_precision < 0 {
        usize::MAX
    } else {
        spec_precision as usize
    };
    let len = strnlen(s, precision) as CInt;
    let pad = if field_width > len {
        field_width - len
    } else {
        0
    };

    if (flags & LEFT) == 0 {
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

    if (flags & LEFT) != 0 {
        let mut right_pad = pad;
        while right_pad > 0 {
            write_char_if_room(buf, end, b' ');
            buf = buf.add(1);
            right_pad -= 1;
        }
    }

    buf
}

#[no_mangle]
pub unsafe extern "C" fn string_result(
    buf: *mut i8,
    end: *mut i8,
    s: *mut i8,
    mut spec: PrintfSpec,
) -> *mut i8 {
    string_ref_result(buf, end, s, &mut spec)
}

#[no_mangle]
pub unsafe extern "C" fn printf_copy_literal_result(
    mut buf: *mut i8,
    end: *mut i8,
    mut src: *const i8,
    read: CInt,
) -> *mut i8 {
    let mut copied: CInt = 0;

    while copied < read {
        write_char_if_room(buf, end, read_volatile(src) as u8);
        buf = buf.add(1);
        src = src.add(1);
        copied += 1;
    }

    buf
}

unsafe fn printf_char_ref_result(
    mut buf: *mut i8,
    end: *mut i8,
    ch: CInt,
    spec: *const PrintfSpec,
) -> *mut i8 {
    let flags = read_volatile(&(*spec).flags);
    let mut field_width = read_volatile(&(*spec).field_width);

    if (flags & LEFT) == 0 {
        loop {
            field_width -= 1;
            if field_width <= 0 {
                break;
            }
            write_char_if_room(buf, end, b' ');
            buf = buf.add(1);
        }
    }

    write_char_if_room(buf, end, ch as u8);
    buf = buf.add(1);

    loop {
        field_width -= 1;
        if field_width <= 0 {
            break;
        }
        write_char_if_room(buf, end, b' ');
        buf = buf.add(1);
    }

    buf
}

#[no_mangle]
pub unsafe extern "C" fn printf_char_result(
    buf: *mut i8,
    end: *mut i8,
    ch: CInt,
    mut spec: PrintfSpec,
) -> *mut i8 {
    printf_char_ref_result(buf, end, ch, &mut spec)
}

#[no_mangle]
pub unsafe extern "C" fn printf_emit_char_result(buf: *mut i8, end: *mut i8, ch: CInt) -> *mut i8 {
    write_char_if_room(buf, end, ch as u8);
    buf.add(1)
}

#[no_mangle]
pub unsafe extern "C" fn printf_write_nchars_result(
    buf: *mut i8,
    str_: *mut i8,
    out: *mut core::ffi::c_void,
    qualifier: CInt,
) {
    let count = (str_ as isize).wrapping_sub(buf as isize);

    if qualifier == b'l' as CInt {
        write_volatile(out as *mut CLong, count as CLong);
    } else if qualifier == b'Z' as CInt || qualifier == b'z' as CInt {
        write_volatile(out as *mut SizeT, count as SizeT);
    } else {
        write_volatile(out as *mut CInt, count as CInt);
    }
}

#[no_mangle]
pub unsafe extern "C" fn printf_terminate_result(
    _buf: *mut i8,
    size: SizeT,
    end: *mut i8,
    str_: *mut i8,
) {
    if size == 0 {
        return;
    }

    if (str_ as usize) < (end as usize) {
        write_volatile(str_, 0);
    } else {
        write_volatile(end.sub(1), 0);
    }
}

type PrintfReadIntFn = unsafe extern "C" fn(*mut core::ffi::c_void) -> CInt;
type PrintfReadNumberFn = unsafe extern "C" fn(*mut core::ffi::c_void, CInt) -> CULong;
type PrintfReadPointerFn =
    unsafe extern "C" fn(*mut core::ffi::c_void, CInt, CInt) -> *mut core::ffi::c_void;
type ScanfReadOutputFn =
    unsafe extern "C" fn(*mut core::ffi::c_void, CInt, CInt, CInt) -> *mut core::ffi::c_void;

#[inline(always)]
unsafe fn init_printf_spec(spec: *mut PrintfSpec) {
    write_volatile(&mut (*spec).type_, 0);
    write_volatile(&mut (*spec).flags, 0);
    write_volatile(&mut (*spec).field_width, 0);
    write_volatile(&mut (*spec).base, 0);
    write_volatile(&mut (*spec).precision, 0);
    write_volatile(&mut (*spec).qualifier, 0);
}

#[inline(always)]
unsafe fn copy_printf_spec(dst: *mut PrintfSpec, src: *const PrintfSpec) {
    write_volatile(&mut (*dst).type_, read_volatile(&(*src).type_));
    write_volatile(&mut (*dst).flags, read_volatile(&(*src).flags));
    write_volatile(&mut (*dst).field_width, read_volatile(&(*src).field_width));
    write_volatile(&mut (*dst).base, read_volatile(&(*src).base));
    write_volatile(&mut (*dst).precision, read_volatile(&(*src).precision));
    write_volatile(&mut (*dst).qualifier, read_volatile(&(*src).qualifier));
}

unsafe fn pointer_ref_result(
    buf: *mut i8,
    end: *mut i8,
    ext_fmt: *const i8,
    ptr: *mut core::ffi::c_void,
    spec: *const PrintfSpec,
) -> *mut i8 {
    static NULL_POINTER: &[u8; 7] = b"(null)\0";
    let mut local_storage = core::mem::MaybeUninit::<PrintfSpec>::uninit();
    let local = local_storage.as_mut_ptr();

    if ptr.is_null() {
        return string_ref_result(buf, end, NULL_POINTER.as_ptr() as *mut i8, spec);
    }

    copy_printf_spec(local, spec);
    if read_char(ext_fmt) == b'S' {
        write_volatile(
            &mut (*local).field_width,
            (2 * core::mem::size_of::<*const core::ffi::c_void>()) as CInt,
        );
        write_volatile(
            &mut (*local).flags,
            read_volatile(&(*local).flags) | SPECIAL | SMALL | ZEROPAD,
        );
        write_volatile(&mut (*local).base, 16);
        return number_ref_result(buf, end, ptr as CULong, local);
    }

    write_volatile(&mut (*local).flags, read_volatile(&(*local).flags) | SMALL);
    if read_volatile(&(*local).field_width) == -1 {
        write_volatile(
            &mut (*local).field_width,
            (2 * core::mem::size_of::<*const core::ffi::c_void>()) as CInt,
        );
        write_volatile(
            &mut (*local).flags,
            read_volatile(&(*local).flags) | ZEROPAD,
        );
    }
    write_volatile(&mut (*local).base, 16);
    number_ref_result(buf, end, ptr as CULong, local)
}

#[inline(always)]
fn ptr_before(a: *const i8, b: *const i8) -> bool {
    (a as usize) < (b as usize)
}

#[inline(always)]
fn ptr_delta(a: *const i8, b: *const i8) -> CInt {
    (a as isize).wrapping_sub(b as isize) as CInt
}

#[inline(always)]
fn is_alnum(ch: u8) -> bool {
    ch.is_ascii_alphanumeric()
}

#[no_mangle]
pub unsafe extern "C" fn vsnprintf_loop_result(
    buf: *mut i8,
    size: SizeT,
    mut fmt: *const i8,
    ctx: *mut core::ffi::c_void,
    read_int: PrintfReadIntFn,
    read_number: PrintfReadNumberFn,
    read_pointer: PrintfReadPointerFn,
) -> CInt {
    let mut str_ = buf;
    let mut end = buf.wrapping_add(size);
    let mut effective_size = size;
    let mut spec_storage = core::mem::MaybeUninit::<PrintfSpec>::uninit();
    let spec = spec_storage.as_mut_ptr();

    if (size as CInt) < 0 {
        return 0;
    }

    init_printf_spec(spec);

    if ptr_before(end, buf) {
        end = usize::MAX as *mut i8;
        effective_size = (end as usize).wrapping_sub(buf as usize);
    }

    while read_char(fmt) != 0 {
        let old_fmt = fmt;
        let read = format_decode_result(fmt, spec);

        fmt = fmt.wrapping_add(read as usize);

        match read_volatile(&(*spec).type_) {
            FORMAT_TYPE_NONE => {
                str_ = printf_copy_literal_result(str_, end, old_fmt, read);
            }
            FORMAT_TYPE_WIDTH => {
                write_volatile(&mut (*spec).field_width, read_int(ctx));
            }
            FORMAT_TYPE_PRECISION => {
                write_volatile(&mut (*spec).precision, read_int(ctx));
            }
            FORMAT_TYPE_CHAR => {
                str_ = printf_char_ref_result(str_, end, read_int(ctx) & 0xff, spec);
            }
            FORMAT_TYPE_STR => {
                let s = read_pointer(
                    ctx,
                    read_volatile(&(*spec).type_),
                    read_volatile(&(*spec).qualifier),
                ) as *mut i8;
                str_ = string_ref_result(str_, end, s, spec);
            }
            FORMAT_TYPE_PTR => {
                let ptr = read_pointer(
                    ctx,
                    read_volatile(&(*spec).type_),
                    read_volatile(&(*spec).qualifier),
                );
                str_ = pointer_ref_result(str_, end, fmt.wrapping_add(1), ptr, spec);
                while is_alnum(read_char(fmt)) {
                    fmt = fmt.wrapping_add(1);
                }
            }
            FORMAT_TYPE_PERCENT_CHAR => {
                str_ = printf_emit_char_result(str_, end, b'%' as CInt);
            }
            FORMAT_TYPE_INVALID => {
                str_ = printf_emit_char_result(str_, end, b'%' as CInt);
            }
            FORMAT_TYPE_NRCHARS => {
                let out = read_pointer(
                    ctx,
                    read_volatile(&(*spec).type_),
                    read_volatile(&(*spec).qualifier),
                );
                printf_write_nchars_result(buf, str_, out, read_volatile(&(*spec).qualifier));
            }
            _ => {
                let num = read_number(ctx, read_volatile(&(*spec).type_));
                str_ = number_ref_result(str_, end, num, spec);
            }
        }
    }

    printf_terminate_result(buf, effective_size, end, str_);
    ptr_delta(str_, buf)
}

unsafe fn printf_read_number_from_va(args: &mut VaList<'_>, spec: *const PrintfSpec) -> CULong {
    let type_ = read_volatile(&(*spec).type_);
    let flags = read_volatile(&(*spec).flags);

    match type_ {
        FORMAT_TYPE_LONG_LONG => {
            if (flags & SIGN) != 0 {
                args.arg::<i64>() as CULong
            } else {
                args.arg::<u64>() as CULong
            }
        }
        FORMAT_TYPE_ULONG => args.arg::<CULong>(),
        FORMAT_TYPE_LONG => args.arg::<CLong>() as CULong,
        FORMAT_TYPE_SIZE_T => args.arg::<SizeT>() as CULong,
        FORMAT_TYPE_PTRDIFF => args.arg::<isize>() as CULong,
        FORMAT_TYPE_UBYTE => (args.arg::<CInt>() as u8) as CULong,
        FORMAT_TYPE_BYTE => (args.arg::<CInt>() as i8) as CULong,
        FORMAT_TYPE_USHORT => (args.arg::<CInt>() as u16) as CULong,
        FORMAT_TYPE_SHORT => (args.arg::<CInt>() as i16) as CULong,
        FORMAT_TYPE_INT => args.arg::<CInt>() as CULong,
        _ => args.arg::<u32>() as CULong,
    }
}

unsafe fn printf_read_pointer_from_va(
    args: &mut VaList<'_>,
    type_: CInt,
    qualifier: CInt,
) -> *mut c_void {
    match type_ {
        FORMAT_TYPE_STR => args.arg::<*mut i8>().cast::<c_void>(),
        FORMAT_TYPE_NRCHARS => {
            if qualifier == b'l' as CInt {
                args.arg::<*mut CLong>().cast::<c_void>()
            } else if qualifier == b'Z' as CInt || qualifier == b'z' as CInt {
                args.arg::<*mut SizeT>().cast::<c_void>()
            } else {
                args.arg::<*mut CInt>().cast::<c_void>()
            }
        }
        _ => args.arg::<*mut c_void>(),
    }
}

pub(crate) unsafe fn vsnprintf_va_list_result(
    buf: *mut i8,
    size: SizeT,
    mut fmt: *const i8,
    args: &mut VaList<'_>,
) -> CInt {
    let mut str_ = buf;
    let mut end = buf.wrapping_add(size);
    let mut effective_size = size;
    let mut spec_storage = core::mem::MaybeUninit::<PrintfSpec>::uninit();
    let spec = spec_storage.as_mut_ptr();

    if (size as CInt) < 0 {
        return 0;
    }

    init_printf_spec(spec);

    if ptr_before(end, buf) {
        end = usize::MAX as *mut i8;
        effective_size = (end as usize).wrapping_sub(buf as usize);
    }

    while read_char(fmt) != 0 {
        let old_fmt = fmt;
        let read = format_decode_result(fmt, spec);

        fmt = fmt.wrapping_add(read as usize);

        match read_volatile(&(*spec).type_) {
            FORMAT_TYPE_NONE => {
                str_ = printf_copy_literal_result(str_, end, old_fmt, read);
            }
            FORMAT_TYPE_WIDTH => {
                write_volatile(&mut (*spec).field_width, args.arg::<CInt>());
            }
            FORMAT_TYPE_PRECISION => {
                write_volatile(&mut (*spec).precision, args.arg::<CInt>());
            }
            FORMAT_TYPE_CHAR => {
                str_ = printf_char_ref_result(str_, end, args.arg::<CInt>() & 0xff, spec);
            }
            FORMAT_TYPE_STR => {
                let s = printf_read_pointer_from_va(
                    args,
                    read_volatile(&(*spec).type_),
                    read_volatile(&(*spec).qualifier),
                ) as *mut i8;
                str_ = string_ref_result(str_, end, s, spec);
            }
            FORMAT_TYPE_PTR => {
                let ptr = printf_read_pointer_from_va(
                    args,
                    read_volatile(&(*spec).type_),
                    read_volatile(&(*spec).qualifier),
                );
                str_ = pointer_ref_result(str_, end, fmt.wrapping_add(1), ptr, spec);
                while is_alnum(read_char(fmt)) {
                    fmt = fmt.wrapping_add(1);
                }
            }
            FORMAT_TYPE_PERCENT_CHAR => {
                str_ = printf_emit_char_result(str_, end, b'%' as CInt);
            }
            FORMAT_TYPE_INVALID => {
                str_ = printf_emit_char_result(str_, end, b'%' as CInt);
            }
            FORMAT_TYPE_NRCHARS => {
                let out = printf_read_pointer_from_va(
                    args,
                    read_volatile(&(*spec).type_),
                    read_volatile(&(*spec).qualifier),
                );
                printf_write_nchars_result(buf, str_, out, read_volatile(&(*spec).qualifier));
            }
            _ => {
                let num = printf_read_number_from_va(args, spec);
                str_ = number_ref_result(str_, end, num, spec);
            }
        }
    }

    printf_terminate_result(buf, effective_size, end, str_);
    ptr_delta(str_, buf)
}

#[inline(always)]
fn scnprintf_return(count: CInt, size: SizeT) -> CInt {
    if (count as SizeT) >= size {
        size.wrapping_sub(1) as CInt
    } else {
        count
    }
}

#[no_mangle]
pub unsafe extern "C" fn vsnprintf(
    buf: *mut i8,
    size: SizeT,
    fmt: *const i8,
    args: VaList<'_>,
) -> CInt {
    let mut copied = args.clone();
    vsnprintf_va_list_result(buf, size, fmt, &mut copied)
}

#[no_mangle]
pub unsafe extern "C" fn vscnprintf(
    buf: *mut i8,
    size: SizeT,
    fmt: *const i8,
    args: VaList<'_>,
) -> CInt {
    scnprintf_return(vsnprintf(buf, size, fmt, args), size)
}

#[no_mangle]
pub unsafe extern "C" fn snprintf(
    buf: *mut i8,
    size: SizeT,
    fmt: *const i8,
    mut args: ...
) -> CInt {
    vsnprintf_va_list_result(buf, size, fmt, &mut args)
}

#[no_mangle]
pub unsafe extern "C" fn scnprintf(
    buf: *mut i8,
    size: SizeT,
    fmt: *const i8,
    mut args: ...
) -> CInt {
    let count = vsnprintf_va_list_result(buf, size, fmt, &mut args);
    scnprintf_return(count, size)
}

#[no_mangle]
pub unsafe extern "C" fn vsprintf(buf: *mut i8, fmt: *const i8, args: VaList<'_>) -> CInt {
    vsnprintf(buf, CInt::MAX as SizeT, fmt, args)
}

#[no_mangle]
pub unsafe extern "C" fn sprintf(buf: *mut i8, fmt: *const i8, mut args: ...) -> CInt {
    vsnprintf_va_list_result(buf, CInt::MAX as SizeT, fmt, &mut args)
}

#[repr(C)]
struct RustVaListCtx<'a> {
    args: *mut VaList<'a>,
}

unsafe extern "C" fn rust_scanf_read_output(
    ctx: *mut c_void,
    conversion: CInt,
    qualifier: CInt,
    is_sign: CInt,
) -> *mut c_void {
    let state = &mut *(ctx as *mut RustVaListCtx<'_>);
    let args = &mut *state.args;

    match conversion {
        c if c == b'c' as CInt || c == b's' as CInt => args.arg::<*mut i8>().cast::<c_void>(),
        c if c == b'n' as CInt => {
            if qualifier == b'l' as CInt {
                args.arg::<*mut CLong>().cast::<c_void>()
            } else if qualifier == b'Z' as CInt || qualifier == b'z' as CInt {
                args.arg::<*mut SizeT>().cast::<c_void>()
            } else {
                args.arg::<*mut CInt>().cast::<c_void>()
            }
        }
        _ => match qualifier {
            q if q == b'H' as CInt => {
                if is_sign != 0 {
                    args.arg::<*mut i8>().cast::<c_void>()
                } else {
                    args.arg::<*mut u8>().cast::<c_void>()
                }
            }
            q if q == b'h' as CInt => {
                if is_sign != 0 {
                    args.arg::<*mut i16>().cast::<c_void>()
                } else {
                    args.arg::<*mut u16>().cast::<c_void>()
                }
            }
            q if q == b'l' as CInt => {
                if is_sign != 0 {
                    args.arg::<*mut CLong>().cast::<c_void>()
                } else {
                    args.arg::<*mut CULong>().cast::<c_void>()
                }
            }
            q if q == b'L' as CInt => {
                if is_sign != 0 {
                    args.arg::<*mut i64>().cast::<c_void>()
                } else {
                    args.arg::<*mut u64>().cast::<c_void>()
                }
            }
            q if q == b'Z' as CInt || q == b'z' as CInt => {
                args.arg::<*mut SizeT>().cast::<c_void>()
            }
            _ => {
                if is_sign != 0 {
                    args.arg::<*mut CInt>().cast::<c_void>()
                } else {
                    args.arg::<*mut u32>().cast::<c_void>()
                }
            }
        },
    }
}

unsafe fn vsscanf_va_list_result(buf: *const i8, fmt: *const i8, args: &mut VaList<'_>) -> CInt {
    let mut state = RustVaListCtx { args };

    vsscanf_loop_result(
        buf,
        fmt,
        (&mut state as *mut RustVaListCtx<'_>).cast::<c_void>(),
        rust_scanf_read_output,
    )
}

unsafe fn scanf_write_nchars(buf: *const i8, str_: *const i8, out: *mut core::ffi::c_void) {
    write_volatile(out as *mut CInt, str_.offset_from(buf) as CInt);
}

unsafe fn scanf_store_signed(out: *mut core::ffi::c_void, qualifier: CInt, value: CLong) {
    if qualifier == b'H' as CInt {
        write_volatile(out as *mut i8, value as i8);
    } else if qualifier == b'h' as CInt {
        write_volatile(out as *mut i16, value as i16);
    } else if qualifier == b'l' as CInt {
        write_volatile(out as *mut CLong, value);
    } else if qualifier == b'L' as CInt {
        write_volatile(out as *mut i64, value as i64);
    } else {
        write_volatile(out as *mut CInt, value as CInt);
    }
}

unsafe fn scanf_store_unsigned(out: *mut core::ffi::c_void, qualifier: CInt, value: CULong) {
    if qualifier == b'H' as CInt {
        write_volatile(out as *mut u8, value as u8);
    } else if qualifier == b'h' as CInt {
        write_volatile(out as *mut u16, value as u16);
    } else if qualifier == b'l' as CInt {
        write_volatile(out as *mut CULong, value);
    } else if qualifier == b'L' as CInt {
        write_volatile(out as *mut u64, value as u64);
    } else if qualifier == b'Z' as CInt || qualifier == b'z' as CInt {
        write_volatile(out as *mut SizeT, value as SizeT);
    } else {
        write_volatile(out as *mut u32, value as u32);
    }
}

#[no_mangle]
pub unsafe extern "C" fn vsscanf_loop_result(
    buf: *const i8,
    mut fmt: *const i8,
    ctx: *mut core::ffi::c_void,
    read_output: ScanfReadOutputFn,
) -> CInt {
    let mut str_ = buf;
    let mut num = 0;

    while read_char(fmt) != 0 && read_char(str_) != 0 {
        if is_space(read_char(fmt)) {
            while is_space(read_char(fmt)) {
                fmt = fmt.add(1);
            }
            while is_space(read_char(str_)) {
                str_ = str_.add(1);
            }
        }

        if read_char(fmt) != b'%' && read_char(fmt) != 0 {
            if read_char(fmt) != read_char(str_) {
                break;
            }
            fmt = fmt.add(1);
            str_ = str_.add(1);
            continue;
        }

        if read_char(fmt) == 0 {
            break;
        }
        fmt = fmt.add(1);

        if read_char(fmt) == b'*' {
            while read_char(fmt) != 0 && !is_space(read_char(fmt)) {
                fmt = fmt.add(1);
            }
            while read_char(str_) != 0 && !is_space(read_char(str_)) {
                str_ = str_.add(1);
            }
            continue;
        }

        let mut field_width: CInt = -1;
        if is_digit(read_char(fmt)) {
            let mut width_ptr = fmt;
            field_width = skip_atoi_result(&mut width_ptr);
            fmt = width_ptr;
        }

        let mut qualifier: CInt = -1;
        match read_char(fmt) {
            b'h' | b'l' | b'L' | b'Z' | b'z' => {
                qualifier = read_char(fmt) as CInt;
                fmt = fmt.add(1);
                if qualifier == read_char(fmt) as CInt {
                    if qualifier == b'h' as CInt {
                        qualifier = b'H' as CInt;
                        fmt = fmt.add(1);
                    } else if qualifier == b'l' as CInt {
                        qualifier = b'L' as CInt;
                        fmt = fmt.add(1);
                    }
                }
            }
            _ => {}
        }

        let mut base: u32 = 10;
        let mut is_sign = 0;
        if read_char(fmt) == 0 || read_char(str_) == 0 {
            break;
        }

        let conversion = read_char(fmt);
        fmt = fmt.add(1);
        match conversion {
            b'c' => {
                let mut out = read_output(ctx, b'c' as CInt, qualifier, 0) as *mut i8;
                if field_width == -1 {
                    field_width = 1;
                }
                loop {
                    write_volatile(out, read_char(str_) as i8);
                    out = out.add(1);
                    str_ = str_.add(1);
                    field_width -= 1;
                    if field_width <= 0 || read_char(str_) == 0 {
                        break;
                    }
                }
                num += 1;
                continue;
            }
            b's' => {
                let mut out = read_output(ctx, b's' as CInt, qualifier, 0) as *mut i8;
                if field_width == -1 {
                    field_width = CInt::MAX;
                }
                while is_space(read_char(str_)) {
                    str_ = str_.add(1);
                }
                while read_char(str_) != 0 && !is_space(read_char(str_)) && field_width != 0 {
                    write_volatile(out, read_char(str_) as i8);
                    out = out.add(1);
                    str_ = str_.add(1);
                    field_width -= 1;
                }
                write_volatile(out, 0);
                num += 1;
                continue;
            }
            b'n' => {
                let out = read_output(ctx, b'n' as CInt, qualifier, 0);
                scanf_write_nchars(buf, str_, out);
                continue;
            }
            b'o' => {
                base = 8;
            }
            b'x' | b'X' => {
                base = 16;
            }
            b'i' => {
                base = 0;
                is_sign = 1;
            }
            b'd' => {
                is_sign = 1;
            }
            b'u' => {}
            b'%' => {
                if read_char(str_) != b'%' {
                    return num;
                }
                str_ = str_.add(1);
                continue;
            }
            _ => {
                return num;
            }
        }

        while is_space(read_char(str_)) {
            str_ = str_.add(1);
        }

        let mut digit = read_char(str_);
        if is_sign != 0 && digit == b'-' {
            digit = read_char(str_.add(1));
        }

        if digit == 0
            || (base == 16 && !is_xdigit(digit))
            || (base == 10 && !is_digit(digit))
            || (base == 8 && (!is_digit(digit) || digit > b'7'))
            || (base == 0 && !is_digit(digit))
        {
            break;
        }

        let out = read_output(ctx, conversion as CInt, qualifier, is_sign);
        let mut next = core::ptr::null_mut();
        if qualifier == b'Z' as CInt || qualifier == b'z' as CInt {
            let value = simple_strtoul(str_, &mut next, base);
            scanf_store_unsigned(out, qualifier, value);
        } else if is_sign != 0 {
            let value = simple_strtol(str_, &mut next, base);
            scanf_store_signed(out, qualifier, value);
        } else {
            let value = simple_strtoul(str_, &mut next, base);
            scanf_store_unsigned(out, qualifier, value);
        }
        num += 1;

        if next.is_null() {
            break;
        }
        str_ = next;
    }

    if read_char(fmt) == b'%' && read_char(fmt.add(1)) == b'n' {
        let out = read_output(ctx, b'n' as CInt, -1, 0);
        scanf_write_nchars(buf, str_, out);
    }

    num
}

#[no_mangle]
pub unsafe extern "C" fn vsscanf(buf: *const i8, fmt: *const i8, args: VaList<'_>) -> CInt {
    let mut copied = args.clone();
    vsscanf_va_list_result(buf, fmt, &mut copied)
}

#[no_mangle]
pub unsafe extern "C" fn sscanf(buf: *const i8, fmt: *const i8, mut args: ...) -> CInt {
    vsscanf_va_list_result(buf, fmt, &mut args)
}
