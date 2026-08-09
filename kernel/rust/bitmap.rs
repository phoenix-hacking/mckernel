use core::ptr::write_volatile;

type CInt = i32;
type CChar = i8;
type CUInt = u32;
type CULong = u64;

const ENOMEM: CInt = 12;
const EBUSY: CInt = 16;
const EINVAL: CInt = 22;
const ERANGE: CInt = 34;
const EOVERFLOW: CInt = 75;
const BITS_PER_LONG: usize = 64;
const BITS_PER_LONG_I32: CInt = 64;
const CHUNKSZ: CInt = 32;
const REG_OP_ISFREE: CInt = 0;
const REG_OP_ALLOC: CInt = 1;
const REG_OP_RELEASE: CInt = 2;

#[inline(always)]
fn bits_to_longs(bits: CInt) -> usize {
    if bits <= 0 {
        0
    } else {
        (bits as usize + BITS_PER_LONG - 1) / BITS_PER_LONG
    }
}

#[inline(always)]
fn full_words(bits: CInt) -> usize {
    if bits <= 0 {
        0
    } else {
        bits as usize / BITS_PER_LONG
    }
}

#[inline(always)]
fn trailing_bits(bits: CInt) -> usize {
    if bits <= 0 {
        0
    } else {
        bits as usize % BITS_PER_LONG
    }
}

#[inline(always)]
fn bitmap_last_word_mask(bits: CInt) -> CULong {
    let trailing = trailing_bits(bits);
    if trailing == 0 {
        !0
    } else {
        (1u64 << trailing) - 1
    }
}

#[inline(always)]
fn bitmap_first_word_mask(start: CInt) -> CULong {
    !0u64 << (start as usize % BITS_PER_LONG)
}

#[inline(always)]
fn bit_word(bit: CInt) -> usize {
    bit as usize / BITS_PER_LONG
}

#[inline(always)]
unsafe fn zero_words(dst: *mut CULong, words: usize) {
    for k in 0..words {
        write_volatile(dst.add(k), 0);
    }
}

#[inline(always)]
fn align_mask(value: CULong, mask: CULong) -> CULong {
    value.wrapping_add(mask) & !mask
}

#[inline(always)]
fn modulo_nonzero(mut value: CULong, divisor: CULong) -> CULong {
    let mut shifted = divisor;

    while shifted <= (value >> 1) && shifted <= (u64::MAX >> 1) {
        shifted <<= 1;
    }

    loop {
        if value >= shifted {
            value -= shifted;
        }
        if shifted == divisor {
            break;
        }
        shifted >>= 1;
    }

    value
}

#[inline(always)]
unsafe fn test_bit(map: *const CULong, bit: CULong) -> bool {
    let bit = bit as usize;
    ((*map.add(bit / BITS_PER_LONG) >> (bit % BITS_PER_LONG)) & 1) != 0
}

#[inline(always)]
unsafe fn set_bit(map: *mut CULong, bit: CULong) {
    let bit = bit as usize;
    *map.add(bit / BITS_PER_LONG) |= 1u64 << (bit % BITS_PER_LONG);
}

#[inline(always)]
unsafe fn scn_store_nul(buf: *mut CChar, index: usize) {
    write_volatile(buf.add(index), 0);
}

#[inline(always)]
unsafe fn scn_append_byte(buf: *mut CChar, buflen: CUInt, len: CInt, byte: u8) -> CInt {
    if buflen == 0 {
        return len;
    }

    let pos = if len < 0 { 0 } else { len as usize };
    let buflen = buflen as usize;
    if pos + 1 < buflen {
        write_volatile(buf.add(pos), byte as CChar);
        scn_store_nul(buf, pos + 1);
        len + 1
    } else {
        if pos < buflen {
            scn_store_nul(buf, pos);
        }
        len
    }
}

#[inline(always)]
unsafe fn scn_append_decimal(buf: *mut CChar, buflen: CUInt, mut len: CInt, value: CInt) -> CInt {
    let mut digits = core::mem::MaybeUninit::<[u8; 20]>::uninit();
    let digit_ptr = digits.as_mut_ptr() as *mut u8;
    let mut count = 0usize;
    let mut value64 = value as i64;

    if value64 < 0 {
        len = scn_append_byte(buf, buflen, len, b'-');
        value64 = -value64;
    }

    let mut n = value64 as u64;
    loop {
        *digit_ptr.add(count) = b'0' + modulo_nonzero(n, 10) as u8;
        count += 1;
        n /= 10;
        if n == 0 {
            break;
        }
    }

    while count != 0 {
        count -= 1;
        len = scn_append_byte(buf, buflen, len, *digit_ptr.add(count));
    }

    len
}

#[inline(always)]
unsafe fn scn_append_hex_width(
    buf: *mut CChar,
    buflen: CUInt,
    mut len: CInt,
    value: CULong,
    width: CInt,
) -> CInt {
    let mut pos = width - 1;

    while pos >= 0 {
        let digit = ((value >> ((pos as usize) * 4)) & 0xf) as u8;
        let byte = if digit < 10 {
            b'0' + digit
        } else {
            b'a' + (digit - 10)
        };
        len = scn_append_byte(buf, buflen, len, byte);
        pos -= 1;
    }

    len
}

#[inline(always)]
fn is_space(ch: u8) -> bool {
    matches!(ch, b'\t' | b'\n' | 0x0b | 0x0c | b'\r' | b' ' | 0xa0)
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
fn fls32(mut value: u32) -> CInt {
    let mut result = 32;

    if value == 0 {
        return 0;
    }
    if (value & 0xffff_0000) == 0 {
        value <<= 16;
        result -= 16;
    }
    if (value & 0xff00_0000) == 0 {
        value <<= 8;
        result -= 8;
    }
    if (value & 0xf000_0000) == 0 {
        value <<= 4;
        result -= 4;
    }
    if (value & 0xc000_0000) == 0 {
        value <<= 2;
        result -= 2;
    }
    if (value & 0x8000_0000) == 0 {
        result -= 1;
    }

    result
}

#[inline(always)]
unsafe fn find_next_bit(map: *const CULong, size: CULong, offset: CULong) -> CULong {
    let mut bit = offset;

    while bit < size {
        if test_bit(map, bit) {
            return bit;
        }
        bit = bit.wrapping_add(1);
    }

    size
}

#[inline(always)]
unsafe fn find_next_zero_bit(map: *const CULong, size: CULong, offset: CULong) -> CULong {
    let mut bit = offset;

    while bit < size {
        if !test_bit(map, bit) {
            return bit;
        }
        bit = bit.wrapping_add(1);
    }

    size
}

#[inline(always)]
unsafe fn bitmap_pos_to_ord(buf: *const CULong, pos: CInt, bits: CInt) -> CInt {
    if pos < 0 || pos >= bits || !test_bit(buf, pos as CULong) {
        return -1;
    }

    let size = bits as CULong;
    let mut bit = find_next_bit(buf, size, 0) as CInt;
    let mut ord = 0;

    while bit < pos {
        bit = find_next_bit(buf, size, (bit + 1) as CULong) as CInt;
        ord += 1;
    }

    ord
}

#[inline(always)]
unsafe fn bitmap_region_op(bitmap: *mut CULong, pos: CInt, order: CInt, reg_op: CInt) -> CInt {
    let nbits_reg = 1i32.wrapping_shl(order as u32);
    let index = pos / BITS_PER_LONG_I32;
    let offset = pos - (index * BITS_PER_LONG_I32);
    let nlongs_reg = bits_to_longs(nbits_reg);
    let nbitsinlong = if nbits_reg < BITS_PER_LONG_I32 {
        nbits_reg
    } else {
        BITS_PER_LONG_I32
    };
    let mut mask = 1u64 << ((nbitsinlong - 1) as usize);
    mask += mask - 1;
    mask <<= offset as usize;

    match reg_op {
        REG_OP_ISFREE => {
            for i in 0..nlongs_reg {
                if (*bitmap.add(index as usize + i) & mask) != 0 {
                    return 0;
                }
            }
            1
        }
        REG_OP_ALLOC => {
            for i in 0..nlongs_reg {
                *bitmap.add(index as usize + i) |= mask;
            }
            0
        }
        REG_OP_RELEASE => {
            for i in 0..nlongs_reg {
                *bitmap.add(index as usize + i) &= !mask;
            }
            0
        }
        _ => 0,
    }
}

#[no_mangle]
pub extern "C" fn hex_to_bin(ch: CChar) -> CInt {
    let ch = ch as u8;

    if ch.is_ascii_digit() {
        return (ch - b'0') as CInt;
    }
    if (b'a'..=b'f').contains(&ch) {
        return (ch - b'a' + 10) as CInt;
    }
    if (b'A'..=b'F').contains(&ch) {
        return (ch - b'A' + 10) as CInt;
    }

    -1
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_empty(bitmap: *const CULong, bits: CInt) -> CInt {
    let lim = full_words(bits);

    for k in 0..lim {
        if *bitmap.add(k) != 0 {
            return 0;
        }
    }

    if trailing_bits(bits) != 0 && (*bitmap.add(lim) & bitmap_last_word_mask(bits)) != 0 {
        return 0;
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_full(bitmap: *const CULong, bits: CInt) -> CInt {
    let lim = full_words(bits);

    for k in 0..lim {
        if *bitmap.add(k) != !0 {
            return 0;
        }
    }

    if trailing_bits(bits) != 0 && (!*bitmap.add(lim) & bitmap_last_word_mask(bits)) != 0 {
        return 0;
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_equal(
    bitmap1: *const CULong,
    bitmap2: *const CULong,
    bits: CInt,
) -> CInt {
    let lim = full_words(bits);

    for k in 0..lim {
        if *bitmap1.add(k) != *bitmap2.add(k) {
            return 0;
        }
    }

    if trailing_bits(bits) != 0
        && ((*bitmap1.add(lim) ^ *bitmap2.add(lim)) & bitmap_last_word_mask(bits)) != 0
    {
        return 0;
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_complement(dst: *mut CULong, src: *const CULong, bits: CInt) {
    let lim = full_words(bits);

    for k in 0..lim {
        *dst.add(k) = !*src.add(k);
    }

    if trailing_bits(bits) != 0 {
        *dst.add(lim) = !*src.add(lim) & bitmap_last_word_mask(bits);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_shift_right(
    dst: *mut CULong,
    src: *const CULong,
    shift: CInt,
    bits: CInt,
) {
    let lim = bits_to_longs(bits);
    let left = trailing_bits(bits);
    let off = if shift <= 0 {
        0
    } else {
        shift as usize / BITS_PER_LONG
    };
    let rem = if shift <= 0 {
        0
    } else {
        shift as usize % BITS_PER_LONG
    };
    let mask = if left == 0 { 0 } else { (1u64 << left) - 1 };

    if off >= lim {
        zero_words(dst, lim);
        return;
    }

    for k in 0..(lim - off) {
        let src_idx = off + k;
        let mut upper = 0;
        if rem != 0 && src_idx + 1 < lim {
            upper = *src.add(src_idx + 1);
            if src_idx + 1 == lim - 1 && left != 0 {
                upper &= mask;
            }
        }

        let mut lower = *src.add(src_idx);
        if left != 0 && src_idx == lim - 1 {
            lower &= mask;
        }

        let mut value = if rem == 0 {
            lower
        } else {
            (upper << (BITS_PER_LONG - rem)) | (lower >> rem)
        };
        if left != 0 && k == lim - 1 {
            value &= mask;
        }
        *dst.add(k) = value;
    }

    if off != 0 {
        zero_words(dst.add(lim - off), off);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_shift_left(
    dst: *mut CULong,
    src: *const CULong,
    shift: CInt,
    bits: CInt,
) {
    let lim = bits_to_longs(bits);
    let left = trailing_bits(bits);
    let off = if shift <= 0 {
        0
    } else {
        shift as usize / BITS_PER_LONG
    };
    let rem = if shift <= 0 {
        0
    } else {
        shift as usize % BITS_PER_LONG
    };
    let mask = if left == 0 { 0 } else { (1u64 << left) - 1 };

    if off >= lim {
        zero_words(dst, lim);
        return;
    }

    for k in (0..(lim - off)).rev() {
        let lower = if rem != 0 && k > 0 {
            *src.add(k - 1)
        } else {
            0
        };
        let mut upper = *src.add(k);
        if left != 0 && k == lim - 1 {
            upper &= mask;
        }

        let mut value = if rem == 0 {
            upper
        } else {
            (lower >> (BITS_PER_LONG - rem)) | (upper << rem)
        };
        if left != 0 && k + off == lim - 1 {
            value &= mask;
        }
        *dst.add(k + off) = value;
    }

    if off != 0 {
        zero_words(dst, off);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_and(
    dst: *mut CULong,
    bitmap1: *const CULong,
    bitmap2: *const CULong,
    bits: CInt,
) -> CInt {
    let mut result = 0;

    for k in 0..bits_to_longs(bits) {
        let value = *bitmap1.add(k) & *bitmap2.add(k);
        *dst.add(k) = value;
        result |= value;
    }

    (result != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_or(
    dst: *mut CULong,
    bitmap1: *const CULong,
    bitmap2: *const CULong,
    bits: CInt,
) {
    for k in 0..bits_to_longs(bits) {
        *dst.add(k) = *bitmap1.add(k) | *bitmap2.add(k);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_xor(
    dst: *mut CULong,
    bitmap1: *const CULong,
    bitmap2: *const CULong,
    bits: CInt,
) {
    for k in 0..bits_to_longs(bits) {
        *dst.add(k) = *bitmap1.add(k) ^ *bitmap2.add(k);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_andnot(
    dst: *mut CULong,
    bitmap1: *const CULong,
    bitmap2: *const CULong,
    bits: CInt,
) -> CInt {
    let mut result = 0;

    for k in 0..bits_to_longs(bits) {
        let value = *bitmap1.add(k) & !*bitmap2.add(k);
        *dst.add(k) = value;
        result |= value;
    }

    (result != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_intersects(
    bitmap1: *const CULong,
    bitmap2: *const CULong,
    bits: CInt,
) -> CInt {
    let lim = full_words(bits);

    for k in 0..lim {
        if (*bitmap1.add(k) & *bitmap2.add(k)) != 0 {
            return 1;
        }
    }

    if trailing_bits(bits) != 0
        && ((*bitmap1.add(lim) & *bitmap2.add(lim)) & bitmap_last_word_mask(bits)) != 0
    {
        return 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_subset(
    bitmap1: *const CULong,
    bitmap2: *const CULong,
    bits: CInt,
) -> CInt {
    let lim = full_words(bits);

    for k in 0..lim {
        if (*bitmap1.add(k) & !*bitmap2.add(k)) != 0 {
            return 0;
        }
    }

    if trailing_bits(bits) != 0
        && ((*bitmap1.add(lim) & !*bitmap2.add(lim)) & bitmap_last_word_mask(bits)) != 0
    {
        return 0;
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_weight(bitmap: *const CULong, bits: CInt) -> CInt {
    let lim = full_words(bits);
    let mut weight = 0;

    for k in 0..lim {
        weight += (*bitmap.add(k)).count_ones() as CInt;
    }

    if trailing_bits(bits) != 0 {
        weight += ((*bitmap.add(lim) & bitmap_last_word_mask(bits)).count_ones()) as CInt;
    }

    weight
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_zero(dst: *mut CULong, nbits: CInt) {
    zero_words(dst, bits_to_longs(nbits));
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_fill(dst: *mut CULong, nbits: CInt) {
    let nlongs = bits_to_longs(nbits);

    if nlongs == 0 {
        return;
    }

    for k in 0..(nlongs - 1) {
        *dst.add(k) = !0;
    }
    *dst.add(nlongs - 1) = bitmap_last_word_mask(nbits);
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_copy(dst: *mut CULong, src: *const CULong, nbits: CInt) {
    for k in 0..bits_to_longs(nbits) {
        *dst.add(k) = *src.add(k);
    }
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_and(
    dst: *mut CULong,
    src1: *const CULong,
    src2: *const CULong,
    nbits: CInt,
) -> CInt {
    __bitmap_and(dst, src1, src2, nbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_or(
    dst: *mut CULong,
    src1: *const CULong,
    src2: *const CULong,
    nbits: CInt,
) {
    __bitmap_or(dst, src1, src2, nbits);
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_xor(
    dst: *mut CULong,
    src1: *const CULong,
    src2: *const CULong,
    nbits: CInt,
) {
    __bitmap_xor(dst, src1, src2, nbits);
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_andnot(
    dst: *mut CULong,
    src1: *const CULong,
    src2: *const CULong,
    nbits: CInt,
) -> CInt {
    __bitmap_andnot(dst, src1, src2, nbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_complement(dst: *mut CULong, src: *const CULong, nbits: CInt) {
    __bitmap_complement(dst, src, nbits);
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_equal(
    src1: *const CULong,
    src2: *const CULong,
    nbits: CInt,
) -> CInt {
    __bitmap_equal(src1, src2, nbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_intersects(
    src1: *const CULong,
    src2: *const CULong,
    nbits: CInt,
) -> CInt {
    __bitmap_intersects(src1, src2, nbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_subset(
    src1: *const CULong,
    src2: *const CULong,
    nbits: CInt,
) -> CInt {
    __bitmap_subset(src1, src2, nbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_empty(src: *const CULong, nbits: CInt) -> CInt {
    __bitmap_empty(src, nbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_full(src: *const CULong, nbits: CInt) -> CInt {
    __bitmap_full(src, nbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_weight(src: *const CULong, nbits: CInt) -> CInt {
    __bitmap_weight(src, nbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_shift_right(
    dst: *mut CULong,
    src: *const CULong,
    n: CInt,
    nbits: CInt,
) {
    __bitmap_shift_right(dst, src, n, nbits);
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_shift_left(
    dst: *mut CULong,
    src: *const CULong,
    n: CInt,
    nbits: CInt,
) {
    __bitmap_shift_left(dst, src, n, nbits);
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_ord_to_pos(buf: *const CULong, mut ord: CInt, bits: CInt) -> CInt {
    let mut pos = 0;

    if ord >= 0 && ord < bits {
        let size = bits as CULong;
        let mut bit = find_next_bit(buf, size, 0) as CInt;

        while bit < bits && ord > 0 {
            bit = find_next_bit(buf, size, (bit + 1) as CULong) as CInt;
            ord -= 1;
        }

        if bit < bits && ord == 0 {
            pos = bit;
        }
    }

    pos
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_remap(
    dst: *mut CULong,
    src: *const CULong,
    old: *const CULong,
    new: *const CULong,
    bits: CInt,
) {
    if (dst as *const CULong) == src {
        return;
    }

    zero_words(dst, bits_to_longs(bits));

    let size = bits as CULong;
    let weight = __bitmap_weight(new, bits);
    let mut oldbit = find_next_bit(src, size, 0);

    while oldbit < size {
        let ord = bitmap_pos_to_ord(old, oldbit as CInt, bits);
        let newbit = if ord < 0 || weight == 0 {
            oldbit
        } else {
            bitmap_ord_to_pos(new, ord % weight, bits) as CULong
        };

        set_bit(dst, newbit);
        oldbit = find_next_bit(src, size, oldbit + 1);
    }
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_bitremap(
    oldbit: CInt,
    old: *const CULong,
    new: *const CULong,
    bits: CInt,
) -> CInt {
    let weight = __bitmap_weight(new, bits);
    let ord = bitmap_pos_to_ord(old, oldbit, bits);

    if ord < 0 || weight == 0 {
        oldbit
    } else {
        bitmap_ord_to_pos(new, ord % weight, bits)
    }
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_onto(
    dst: *mut CULong,
    orig: *const CULong,
    relmap: *const CULong,
    bits: CInt,
) {
    if (dst as *const CULong) == orig {
        return;
    }

    zero_words(dst, bits_to_longs(bits));

    let size = bits as CULong;
    let mut relbit = find_next_bit(relmap, size, 0);
    let mut ord = 0;

    while relbit < size {
        if test_bit(orig, ord) {
            set_bit(dst, relbit);
        }
        ord += 1;
        relbit = find_next_bit(relmap, size, relbit + 1);
    }
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_fold(dst: *mut CULong, orig: *const CULong, sz: CInt, bits: CInt) {
    if (dst as *const CULong) == orig {
        return;
    }
    if sz <= 0 {
        return;
    }

    zero_words(dst, bits_to_longs(bits));

    let size = bits as CULong;
    let mut oldbit = find_next_bit(orig, size, 0);
    let fold_size = sz as CULong;

    while oldbit < size {
        set_bit(dst, modulo_nonzero(oldbit, fold_size));
        oldbit = find_next_bit(orig, size, oldbit + 1);
    }
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_set(map: *mut CULong, start: CInt, nr: CInt) {
    let mut p = map.add(bit_word(start));
    let size = start + nr;
    let mut remaining = nr;
    let mut bits_to_set = BITS_PER_LONG_I32 - (start % BITS_PER_LONG_I32);
    let mut mask_to_set = bitmap_first_word_mask(start);

    while remaining - bits_to_set >= 0 {
        *p |= mask_to_set;
        remaining -= bits_to_set;
        bits_to_set = BITS_PER_LONG_I32;
        mask_to_set = !0;
        p = p.add(1);
    }

    if remaining != 0 {
        mask_to_set &= bitmap_last_word_mask(size);
        *p |= mask_to_set;
    }
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_clear(map: *mut CULong, start: CInt, nr: CInt) {
    let mut p = map.add(bit_word(start));
    let size = start + nr;
    let mut remaining = nr;
    let mut bits_to_clear = BITS_PER_LONG_I32 - (start % BITS_PER_LONG_I32);
    let mut mask_to_clear = bitmap_first_word_mask(start);

    while remaining - bits_to_clear >= 0 {
        *p &= !mask_to_clear;
        remaining -= bits_to_clear;
        bits_to_clear = BITS_PER_LONG_I32;
        mask_to_clear = !0;
        p = p.add(1);
    }

    if remaining != 0 {
        mask_to_clear &= bitmap_last_word_mask(size);
        *p &= !mask_to_clear;
    }
}

#[no_mangle]
pub unsafe extern "C" fn __bitmap_parse(
    mut buf: *const CChar,
    mut buflen: CUInt,
    _is_user: CInt,
    maskp: *mut CULong,
    nmaskbits: CInt,
) -> CInt {
    let mut c: u8 = 0;
    let mut totaldigits: CInt = 0;
    let mut nchunks: CInt = 0;
    let mut nbits: CInt = 0;

    zero_words(maskp, bits_to_longs(nmaskbits));

    loop {
        let mut chunk: u32 = 0;
        let mut ndigits: CInt = 0;

        while buflen != 0 {
            let old_c = c;
            c = *(buf as *const u8);
            buf = buf.add(1);
            buflen -= 1;

            if is_space(c) {
                continue;
            }
            if totaldigits != 0 && c != 0 && is_space(old_c) {
                return -EINVAL;
            }
            if c == 0 || c == b',' {
                break;
            }
            if !is_xdigit(c) {
                return -EINVAL;
            }
            if (chunk & !((1u32 << (CHUNKSZ - 4)) - 1)) != 0 {
                return -EOVERFLOW;
            }

            chunk = (chunk << 4) | hex_to_bin(c as CChar) as u32;
            ndigits += 1;
            totaldigits += 1;
        }

        if ndigits == 0 {
            return -EINVAL;
        }
        if nchunks == 0 && chunk == 0 {
            if !(buflen != 0 && c == b',') {
                break;
            }
            continue;
        }

        __bitmap_shift_left(maskp, maskp, CHUNKSZ, nmaskbits);
        *maskp |= chunk as CULong;
        nchunks += 1;
        nbits += if nchunks == 1 { fls32(chunk) } else { CHUNKSZ };
        if nbits > nmaskbits {
            return -EOVERFLOW;
        }

        if !(buflen != 0 && c == b',') {
            break;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_parse(
    buf: *const CChar,
    buflen: CUInt,
    maskp: *mut CULong,
    nmaskbits: CInt,
) -> CInt {
    __bitmap_parse(buf, buflen, 0, maskp, nmaskbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_parse_user(
    ubuf: *const CChar,
    ulen: CUInt,
    maskp: *mut CULong,
    nmaskbits: CInt,
) -> CInt {
    __bitmap_parse(ubuf, ulen, 1, maskp, nmaskbits)
}

unsafe fn __bitmap_parselist(
    mut buf: *const CChar,
    mut buflen: CUInt,
    maskp: *mut CULong,
    nmaskbits: CInt,
) -> CInt {
    let mut c: u8 = 0;
    let mut totaldigits: CInt = 0;

    zero_words(maskp, bits_to_longs(nmaskbits));

    loop {
        let mut exp_digit = true;
        let mut in_range = false;
        let mut a: CUInt = 0;
        let mut b: CUInt = 0;

        while buflen != 0 {
            let old_c = c;
            c = *(buf as *const u8);
            buf = buf.add(1);
            buflen -= 1;

            if is_space(c) {
                continue;
            }
            if totaldigits != 0 && c != 0 && is_space(old_c) {
                return -EINVAL;
            }
            if c == 0 || c == b',' {
                break;
            }
            if c == b'-' {
                if exp_digit || in_range {
                    return -EINVAL;
                }
                b = 0;
                in_range = true;
                exp_digit = true;
                continue;
            }
            if !is_digit(c) {
                return -EINVAL;
            }

            b = b.wrapping_mul(10).wrapping_add((c - b'0') as CUInt);
            if !in_range {
                a = b;
            }
            exp_digit = false;
            totaldigits += 1;
        }

        if a > b {
            return -EINVAL;
        }
        if b >= nmaskbits as CUInt {
            return -ERANGE;
        }
        while a <= b {
            set_bit(maskp, a as CULong);
            a += 1;
        }

        if !(buflen != 0 && c == b',') {
            break;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_parselist(
    bp: *const CChar,
    maskp: *mut CULong,
    nmaskbits: CInt,
) -> CInt {
    let mut len: CUInt = 0;

    while *bp.add(len as usize) != 0 && *bp.add(len as usize) != b'\n' as CChar {
        len += 1;
    }

    __bitmap_parselist(bp, len, maskp, nmaskbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_parselist_user(
    ubuf: *const CChar,
    ulen: CUInt,
    maskp: *mut CULong,
    nmaskbits: CInt,
) -> CInt {
    __bitmap_parselist(ubuf, ulen, maskp, nmaskbits)
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_find_next_zero_area(
    map: *mut CULong,
    size: CULong,
    start: CULong,
    nr: CUInt,
    align_mask_arg: CULong,
) -> CULong {
    let map = map as *const CULong;
    let mut search_start = start;

    loop {
        let mut index = find_next_zero_bit(map, size, search_start);
        index = align_mask(index, align_mask_arg);

        let end = index.wrapping_add(nr as CULong);
        if end > size {
            return end;
        }

        let next_set = find_next_bit(map, end, index);
        if next_set < end {
            search_start = next_set.wrapping_add(1);
            continue;
        }

        return index;
    }
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_scnprintf(
    buf: *mut CChar,
    buflen: CUInt,
    maskp: *const CULong,
    nmaskbits: CInt,
) -> CInt {
    let mut len: CInt = 0;

    if buflen == 0 {
        return 0;
    }
    scn_store_nul(buf, 0);

    if maskp.is_null() {
        return 1;
    }

    let mut chunksz = nmaskbits & (CHUNKSZ - 1);
    if chunksz == 0 {
        chunksz = CHUNKSZ;
    }

    let mut bit_index = ((nmaskbits + CHUNKSZ - 1) & !(CHUNKSZ - 1)) - CHUNKSZ;
    let mut needs_sep = false;
    while bit_index >= 0 {
        let chunkmask = (1u64 << (chunksz as usize)) - 1;
        let word = (bit_index / BITS_PER_LONG_I32) as usize;
        let bit = (bit_index % BITS_PER_LONG_I32) as usize;
        let value = (*maskp.add(word) >> bit) & chunkmask;

        if needs_sep {
            len = scn_append_byte(buf, buflen, len, b',');
        }
        len = scn_append_hex_width(buf, buflen, len, value, (chunksz + 3) / 4);

        chunksz = CHUNKSZ;
        needs_sep = true;
        bit_index -= CHUNKSZ;
    }

    len
}

#[inline(always)]
unsafe fn bitmap_scnlist_emit(
    buf: *mut CChar,
    buflen: CUInt,
    rbot: CInt,
    rtop: CInt,
    mut len: CInt,
) -> CInt {
    if len > 0 {
        len = scn_append_byte(buf, buflen, len, b',');
    }
    len = scn_append_decimal(buf, buflen, len, rbot);
    if rbot != rtop {
        len = scn_append_byte(buf, buflen, len, b'-');
        len = scn_append_decimal(buf, buflen, len, rtop);
    }
    len
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_scnlistprintf(
    buf: *mut CChar,
    buflen: CUInt,
    maskp: *const CULong,
    nmaskbits: CInt,
) -> CInt {
    let mut len: CInt = 0;

    if buflen == 0 {
        return 0;
    }
    scn_store_nul(buf, 0);

    if maskp.is_null() {
        return 1;
    }

    let bits = if nmaskbits <= 0 {
        0
    } else {
        nmaskbits as CULong
    };
    let mut cur = find_next_bit(maskp, bits, 0);
    let mut rbot = cur;

    while cur < bits {
        let rtop = cur;
        cur = find_next_bit(maskp, bits, cur + 1);
        if cur >= bits || cur > rtop + 1 {
            len = bitmap_scnlist_emit(buf, buflen, rbot as CInt, rtop as CInt, len);
            rbot = cur;
        }
    }

    len
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_find_free_region(
    bitmap: *mut CULong,
    bits: CInt,
    order: CInt,
) -> CInt {
    let region_bits = 1i32.wrapping_shl(order as u32);
    let mut pos: CInt = 0;

    loop {
        let end = pos.wrapping_add(region_bits);
        if end > bits {
            break;
        }

        if bitmap_region_op(bitmap, pos, order, REG_OP_ISFREE) != 0 {
            bitmap_region_op(bitmap, pos, order, REG_OP_ALLOC);
            return pos;
        }

        pos = end;
    }

    -ENOMEM
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_release_region(bitmap: *mut CULong, pos: CInt, order: CInt) {
    bitmap_region_op(bitmap, pos, order, REG_OP_RELEASE);
}

#[no_mangle]
pub unsafe extern "C" fn bitmap_allocate_region(
    bitmap: *mut CULong,
    pos: CInt,
    order: CInt,
) -> CInt {
    if bitmap_region_op(bitmap, pos, order, REG_OP_ISFREE) == 0 {
        return -EBUSY;
    }

    bitmap_region_op(bitmap, pos, order, REG_OP_ALLOC);
    0
}
