#![no_std]
#![feature(c_variadic)]
// Exact finite current kprintf+formatter partition; no runtime/storage/lock provider.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod string {
use crate::abi::SizeT;
unsafe extern "C" {
    pub fn strnlen(ptr: *const i8, maxlen: SizeT) -> SizeT;
}
}

mod numparse {
use core::ffi::{c_void, VaList};
use core::ptr::{read_volatile, write_volatile};
use crate::abi::{CInt, CLong, CULong, SizeT};
use crate::string::strnlen;

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
fn is_digit(ch: u8) -> bool {
    ch.is_ascii_digit()
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

#[no_mangle]
pub unsafe extern "C" fn snprintf(
    buf: *mut i8,
    size: SizeT,
    fmt: *const i8,
    mut args: ...
) -> CInt {
    vsnprintf_va_list_result(buf, size, fmt, &mut args)
}
}

mod debug {
use core::ffi::VaList;
use core::ptr::{read_volatile, write_volatile};
use crate::abi::{CInt, CULong, SizeT};

const EINVAL: CInt = 22;
const IHK_OS_EVENTFD_TYPE_KMSG: CInt = 101;
const IHK_KMSG_SIZE: CInt = (4 << 20) - 4096;
const IHK_KMSG_HIGH_WATER_MARK: CInt = IHK_KMSG_SIZE / 2;
const IHK_KMSG_NOTIFY_DELAY: CInt = 400;
const KPRINTF_LOCAL_BUF_LEN: SizeT = 1024;

#[repr(C)]
pub struct IhkKmsgBuf {
    pub lock: CInt,
    pub tail: CInt,
    pub len: CInt,
    pub head: CInt,
    pub padding: [i8; 4096 - core::mem::size_of::<CInt>() * 4],
    pub str_: [i8; IHK_KMSG_SIZE as usize],
}

const _: () = {
    use core::mem::{offset_of, size_of};
    assert!(size_of::<IhkKmsgBuf>() == 4 << 20);
    assert!(offset_of!(IhkKmsgBuf, str_) == 4096);
};
unsafe extern "C" {
    static mut kmsg_buf: *mut IhkKmsgBuf;
    fn kprintf_lock() -> CULong;
    fn kprintf_unlock(irqflags: CULong);
    fn cpu_disable_interrupt_save() -> CULong;
    fn cpu_restore_interrupt(flags: CULong);
    fn cpu_pause();
    fn cpu_interrupt_disabled() -> CInt;
    fn ihk_mc_delay_us(us: CInt);
    fn ihk_mc_get_processor_id() -> CInt;
    fn eventfd(type_: CInt);
}

#[inline(always)]
unsafe fn kmsg() -> *mut IhkKmsgBuf {
    read_volatile(&raw const kmsg_buf)
}

#[inline(always)]
unsafe fn kmsg_used(buf: *const IhkKmsgBuf) -> CInt {
    let tail = (*buf).tail as u32;
    let head = (*buf).head as u32;
    let len = (*buf).len as u32;

    if len == 0 {
        0
    } else if tail >= head {
        tail.wrapping_sub(head) as CInt
    } else {
        tail.wrapping_add(len).wrapping_sub(head) as CInt
    }
}

#[inline(always)]
unsafe fn kmsg_margin(buf: *const IhkKmsgBuf) -> CInt {
    let tail = (*buf).tail as u32;
    let head = (*buf).head as u32;
    let len = (*buf).len as u32;

    if len == 0 {
        0
    } else if head == tail {
        len as CInt
    } else if head > tail {
        head.wrapping_sub(tail) as CInt
    } else {
        head.wrapping_add(len).wrapping_sub(tail) as CInt
    }
}

#[inline(always)]
unsafe fn debug_spin_lock_irqsave(lock: *mut CInt) -> CULong {
    let flags = cpu_disable_interrupt_save();
    while core::sync::atomic::AtomicI32::from_ptr(lock)
        .compare_exchange(
            0,
            1,
            core::sync::atomic::Ordering::SeqCst,
            core::sync::atomic::Ordering::SeqCst,
        )
        .is_err()
    {
        cpu_pause();
    }
    flags
}

#[inline(always)]
unsafe fn debug_spin_unlock_irqrestore(lock: *mut CInt, flags: CULong) {
    write_volatile(lock, 0);
    cpu_restore_interrupt(flags);
}

unsafe fn memcpy_ringbuf(src: *const i8, len: CInt) {
    let buf = kmsg();
    if buf.is_null() || (*buf).len <= 0 {
        return;
    }

    let mut i = 0;
    while i < len {
        *(*buf).str_.as_mut_ptr().add((*buf).tail as usize) = *src.add(i as usize);
        let next = (*buf).tail + 1;
        (*buf).tail = if next >= (*buf).len { 0 } else { next };
        i += 1;
    }
}

unsafe fn notify_kmsg_if_needed(buf: *const IhkKmsgBuf) {
    if cpu_interrupt_disabled() == 0 && kmsg_used(buf) > IHK_KMSG_HIGH_WATER_MARK {
        eventfd(IHK_OS_EVENTFD_TYPE_KMSG);
        ihk_mc_delay_us(IHK_KMSG_NOTIFY_DELAY);
    }
}

unsafe fn vkprintf_locked(format: *const i8, args: &mut VaList<'_>, take_outer_lock: bool) -> CInt {
    let msg = kmsg();
    if msg.is_null() {
        return -EINVAL;
    }

    let mut local = [0i8; KPRINTF_LOCAL_BUF_LEN];
    let mut len = crate::numparse::snprintf(
        local.as_mut_ptr(),
        KPRINTF_LOCAL_BUF_LEN,
        c"[%3d]: ".as_ptr().cast(),
        ihk_mc_get_processor_id(),
    );
    len += crate::numparse::vsnprintf_va_list_result(
        local.as_mut_ptr().add(len as usize),
        KPRINTF_LOCAL_BUF_LEN - len as SizeT - 2,
        format,
        args,
    );

    let flags_outer = if take_outer_lock { kprintf_lock() } else { 0 };
    let flags_inner = debug_spin_lock_irqsave(&raw mut (*msg).lock);
    let overflow = kmsg_margin(msg) <= len;

    memcpy_ringbuf(local.as_ptr(), len);
    if overflow {
        let next = (*msg).tail + 1;
        (*msg).head = if next >= (*msg).len { 0 } else { next };
    }

    debug_spin_unlock_irqrestore(&raw mut (*msg).lock, flags_inner);
    if take_outer_lock {
        kprintf_unlock(flags_outer);
    }
    notify_kmsg_if_needed(msg);

    len
}

#[no_mangle]
pub unsafe extern "C" fn kprintf(format: *const i8, mut args: ...) -> CInt {
    vkprintf_locked(format, &mut args, true)
}
}
