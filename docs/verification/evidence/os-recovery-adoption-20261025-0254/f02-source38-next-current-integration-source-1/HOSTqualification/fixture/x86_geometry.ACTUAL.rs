use core::ffi::c_void;
use crate::abi::{CInt,CULong,SizeT};
unsafe extern "C" { static x86_clear_l3_use_1gb_page: *const CInt; }
const ENOMEM: i32 = 12;
const PTL1_SHIFT: i32 = 12;
const PTL2_SHIFT: i32 = 21;
const PTL3_SHIFT: i32 = 30;
const PTL1_SIZE: CULong = 1 << PTL1_SHIFT;
const PTL2_SIZE: CULong = 1 << PTL2_SHIFT;
const PTL3_SIZE: CULong = 1 << PTL3_SHIFT;

#[no_mangle]
pub unsafe extern "C" fn x86_smaller_page_size_result(
    cursize: CULong,
    use_1gb_page: i32,
    newsizep: *mut CULong,
    p2alignp: *mut i32,
) -> i32 {
    let (newsize, p2align, error) = if cursize > PTL3_SIZE && use_1gb_page != 0 {
        (PTL3_SIZE, PTL3_SHIFT - PTL1_SHIFT, 0)
    } else if cursize > PTL2_SIZE {
        (PTL2_SIZE, PTL2_SHIFT - PTL1_SHIFT, 0)
    } else if cursize > PTL1_SIZE {
        (PTL1_SIZE, 0, 0)
    } else {
        (0, -1, -ENOMEM)
    };

    if !newsizep.is_null() {
        unsafe {
            *newsizep = newsize;
        }
    }
    if !p2alignp.is_null() {
        unsafe {
            *p2alignp = p2align;
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn arch_get_smaller_page_size(
    _args: *mut c_void,
    cursize: SizeT,
    newsizep: *mut SizeT,
    p2alignp: *mut CInt,
) -> CInt {
    unsafe {
        x86_smaller_page_size_result(
            cursize as CULong,
            x86_use_1gb_page_bridge(),
            newsizep.cast::<CULong>(),
            p2alignp,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_use_1gb_page_bridge() -> CInt {
    // SAFETY: Typed readonly C address cells bind the real existing storage.
    // Reads match original plain C loads; there is no borrowed Rust reference.
    unsafe { core::ptr::read(x86_clear_l3_use_1gb_page) }
}
