use core::ffi::c_void;

use crate::abi::CULong;

const GOLDEN_RATIO_PRIME_32: u32 = 0x9e37_0001;

#[no_mangle]
pub extern "C" fn hash_64(val: u64, bits: u32) -> u64 {
    let mut hash = val;

    let mut n = hash;
    n <<= 18;
    hash = hash.wrapping_sub(n);
    n <<= 33;
    hash = hash.wrapping_sub(n);
    n <<= 3;
    hash = hash.wrapping_add(n);
    n <<= 3;
    hash = hash.wrapping_sub(n);
    n <<= 4;
    hash = hash.wrapping_add(n);
    n <<= 2;
    hash = hash.wrapping_add(n);

    hash >> (64 - bits)
}

#[no_mangle]
pub extern "C" fn hash_32(val: u32, bits: u32) -> u32 {
    val.wrapping_mul(GOLDEN_RATIO_PRIME_32) >> (32 - bits)
}

#[no_mangle]
pub extern "C" fn hash_long(val: CULong, bits: u32) -> CULong {
    hash_64(val, bits)
}

#[no_mangle]
pub extern "C" fn hash_ptr(ptr: *mut c_void, bits: u32) -> CULong {
    hash_long(ptr as CULong, bits)
}
