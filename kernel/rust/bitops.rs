use core::ffi::c_void;
use core::ptr::read_volatile;
use core::sync::atomic::{AtomicU32, Ordering};

use crate::abi::{CInt, CULong};

const BITS_PER_LONG: CULong = 64;
const BITS_PER_LONG_USIZE: usize = 64;

#[inline(always)]
unsafe fn read_word(addr: *const CULong, word: CULong) -> CULong {
    read_volatile(addr.add(word as usize))
}

#[inline(always)]
fn bitop_word(bit: CULong) -> CULong {
    bit / BITS_PER_LONG
}

#[no_mangle]
pub extern "C" fn ihk_bit_word(nr: CULong) -> CULong {
    bitop_word(nr)
}

#[no_mangle]
pub extern "C" fn ihk_align_mask(x: CULong, mask: CULong) -> CULong {
    x.wrapping_add(mask) & !mask
}

#[no_mangle]
pub extern "C" fn ihk_align(x: CULong, align: CULong) -> CULong {
    ihk_align_mask(x, align.wrapping_sub(1))
}

#[no_mangle]
pub extern "C" fn ihk_is_aligned(x: CULong, align: CULong) -> CInt {
    ((x & align.wrapping_sub(1)) == 0) as CInt
}

#[inline(always)]
fn word_floor(bit: CULong) -> CULong {
    bit & !(BITS_PER_LONG - 1)
}

#[inline(always)]
fn low_bits_mask(bits: CULong) -> CULong {
    if bits >= BITS_PER_LONG {
        !0
    } else {
        !0 >> (BITS_PER_LONG_USIZE - bits as usize)
    }
}

#[inline(always)]
fn high_bits_mask(offset: CULong) -> CULong {
    if offset == 0 {
        !0
    } else {
        !0 << offset as usize
    }
}

#[inline(always)]
fn __ffs_word(mut word: CULong) -> CULong {
    let mut num = 0;

    if (word & 0xffff_ffff) == 0 {
        num += 32;
        word >>= 32;
    }
    if (word & 0xffff) == 0 {
        num += 16;
        word >>= 16;
    }
    if (word & 0xff) == 0 {
        num += 8;
        word >>= 8;
    }
    if (word & 0xf) == 0 {
        num += 4;
        word >>= 4;
    }
    if (word & 0x3) == 0 {
        num += 2;
        word >>= 2;
    }
    if (word & 0x1) == 0 {
        num += 1;
    }

    num
}

#[no_mangle]
pub extern "C" fn fls(x: CInt) -> CInt {
    let value = x as u32;
    if value == 0 {
        0
    } else {
        (32 - value.leading_zeros()) as CInt
    }
}

#[no_mangle]
pub extern "C" fn ffs(x: CInt) -> CInt {
    let value = x as u32;
    if value == 0 {
        0
    } else {
        (value.trailing_zeros() + 1) as CInt
    }
}

#[no_mangle]
pub extern "C" fn __ffs(word: CULong) -> CULong {
    __ffs_word(word)
}

#[no_mangle]
pub extern "C" fn ffz(word: CULong) -> CULong {
    __ffs_word(!word)
}

#[inline(always)]
unsafe fn atomic_bit_word(addr: *mut CULong, nr: CInt) -> *mut AtomicU32 {
    (addr as *mut AtomicU32).offset((nr >> 5) as isize)
}

#[inline(always)]
fn bit32_mask(nr: CInt) -> u32 {
    1u32 << ((nr & 31) as u32)
}

#[no_mangle]
pub unsafe extern "C" fn set_bit(nr: CInt, addr: *mut CULong) {
    let word = unsafe { &*atomic_bit_word(addr, nr) };
    word.fetch_or(bit32_mask(nr), Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn clear_bit(nr: CInt, addr: *mut CULong) {
    let word = unsafe { &*atomic_bit_word(addr, nr) };
    word.fetch_and(!bit32_mask(nr), Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn test_bit(nr: CInt, addr: *const c_void) -> CInt {
    let words = addr as *const u32;
    let word = unsafe { read_volatile(words.offset((nr >> 5) as isize)) };
    if (word & bit32_mask(nr)) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn find_next_bit(
    addr: *const CULong,
    size: CULong,
    offset: CULong,
) -> CULong {
    if offset >= size {
        return size;
    }

    let mut word = bitop_word(offset);
    let mut result = word_floor(offset);
    let mut remaining = size - result;
    let offset_in_word = offset % BITS_PER_LONG;
    let mut tmp: CULong;

    if offset_in_word != 0 {
        tmp = read_word(addr, word) & high_bits_mask(offset_in_word);
        word += 1;
        if remaining < BITS_PER_LONG {
            tmp &= low_bits_mask(remaining);
            if tmp == 0 {
                return result + remaining;
            }
            return result + __ffs_word(tmp);
        }
        if tmp != 0 {
            return result + __ffs_word(tmp);
        }
        remaining -= BITS_PER_LONG;
        result += BITS_PER_LONG;
    }

    while (remaining & !(BITS_PER_LONG - 1)) != 0 {
        tmp = read_word(addr, word);
        word += 1;
        if tmp != 0 {
            return result + __ffs_word(tmp);
        }
        result += BITS_PER_LONG;
        remaining -= BITS_PER_LONG;
    }

    if remaining == 0 {
        return result;
    }

    tmp = read_word(addr, word) & low_bits_mask(remaining);
    if tmp == 0 {
        result + remaining
    } else {
        result + __ffs_word(tmp)
    }
}

#[no_mangle]
pub unsafe extern "C" fn find_next_zero_bit(
    addr: *const CULong,
    size: CULong,
    offset: CULong,
) -> CULong {
    if offset >= size {
        return size;
    }

    let mut word = bitop_word(offset);
    let mut result = word_floor(offset);
    let mut remaining = size - result;
    let offset_in_word = offset % BITS_PER_LONG;
    let mut tmp: CULong;

    if offset_in_word != 0 {
        tmp = read_word(addr, word) | !high_bits_mask(offset_in_word);
        word += 1;
        if remaining < BITS_PER_LONG {
            tmp |= !low_bits_mask(remaining);
            if tmp == !0 {
                return result + remaining;
            }
            return result + __ffs_word(!tmp);
        }
        if tmp != !0 {
            return result + __ffs_word(!tmp);
        }
        remaining -= BITS_PER_LONG;
        result += BITS_PER_LONG;
    }

    while (remaining & !(BITS_PER_LONG - 1)) != 0 {
        tmp = read_word(addr, word);
        word += 1;
        if tmp != !0 {
            return result + __ffs_word(!tmp);
        }
        result += BITS_PER_LONG;
        remaining -= BITS_PER_LONG;
    }

    if remaining == 0 {
        return result;
    }

    tmp = read_word(addr, word) | !low_bits_mask(remaining);
    if tmp == !0 {
        result + remaining
    } else {
        result + __ffs_word(!tmp)
    }
}

#[no_mangle]
pub unsafe extern "C" fn find_first_bit(addr: *const CULong, size: CULong) -> CULong {
    let mut word = 0;
    let mut result = 0;
    let mut remaining = size;
    let mut tmp: CULong;

    while (remaining & !(BITS_PER_LONG - 1)) != 0 {
        tmp = read_word(addr, word);
        word += 1;
        if tmp != 0 {
            return result + __ffs_word(tmp);
        }
        result += BITS_PER_LONG;
        remaining -= BITS_PER_LONG;
    }

    if remaining == 0 {
        return result;
    }

    tmp = read_word(addr, word) & low_bits_mask(remaining);
    if tmp == 0 {
        result + remaining
    } else {
        result + __ffs_word(tmp)
    }
}

#[no_mangle]
pub unsafe extern "C" fn find_first_zero_bit(addr: *const CULong, size: CULong) -> CULong {
    let mut word = 0;
    let mut result = 0;
    let mut remaining = size;
    let mut tmp: CULong;

    while (remaining & !(BITS_PER_LONG - 1)) != 0 {
        tmp = read_word(addr, word);
        word += 1;
        if tmp != !0 {
            return result + __ffs_word(!tmp);
        }
        result += BITS_PER_LONG;
        remaining -= BITS_PER_LONG;
    }

    if remaining == 0 {
        return result;
    }

    tmp = read_word(addr, word) | !low_bits_mask(remaining);
    if tmp == !0 {
        result + remaining
    } else {
        result + __ffs_word(!tmp)
    }
}

#[no_mangle]
pub extern "C" fn __sw_hweight32(w: u32) -> u32 {
    let mut res = w - ((w >> 1) & 0x5555_5555);
    res = (res & 0x3333_3333) + ((res >> 2) & 0x3333_3333);
    res = (res + (res >> 4)) & 0x0f0f_0f0f;
    res = res + (res >> 8);
    (res + (res >> 16)) & 0x0000_00ff
}

#[no_mangle]
pub extern "C" fn __sw_hweight16(w: u32) -> u32 {
    let mut res = w - ((w >> 1) & 0x5555);
    res = (res & 0x3333) + ((res >> 2) & 0x3333);
    res = (res + (res >> 4)) & 0x0f0f;
    (res + (res >> 8)) & 0x00ff
}

#[no_mangle]
pub extern "C" fn __sw_hweight8(w: u32) -> u32 {
    let mut res = w - ((w >> 1) & 0x55);
    res = (res & 0x33) + ((res >> 2) & 0x33);
    (res + (res >> 4)) & 0x0f
}

#[no_mangle]
pub extern "C" fn __sw_hweight64(w: u64) -> CULong {
    let mut res = w - ((w >> 1) & 0x5555_5555_5555_5555);
    res = (res & 0x3333_3333_3333_3333) + ((res >> 2) & 0x3333_3333_3333_3333);
    res = (res + (res >> 4)) & 0x0f0f_0f0f_0f0f_0f0f;
    res = res + (res >> 8);
    res = res + (res >> 16);
    (res + (res >> 32)) & 0x0000_0000_0000_00ff
}

#[no_mangle]
pub extern "C" fn hweight_long(w: CULong) -> CULong {
    __sw_hweight64(w)
}
