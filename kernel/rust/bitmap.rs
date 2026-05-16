use core::ptr::write_volatile;

type CInt = i32;
type CChar = i8;
type CUInt = u32;
type CULong = u64;

const ENOMEM: CInt = 12;
const EBUSY: CInt = 16;
const BITS_PER_LONG: usize = 64;
const BITS_PER_LONG_I32: CInt = 64;
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
unsafe fn test_bit(map: *const CULong, bit: CULong) -> bool {
    let bit = bit as usize;
    ((*map.add(bit / BITS_PER_LONG) >> (bit % BITS_PER_LONG)) & 1) != 0
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
