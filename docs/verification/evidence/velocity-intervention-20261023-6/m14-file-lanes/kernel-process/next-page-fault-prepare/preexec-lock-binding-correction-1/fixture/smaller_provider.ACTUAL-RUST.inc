use crate::abi::CULong;
const PTL3_SIZE:CULong=1<<30;const PTL2_SIZE:CULong=1<<21;const PTL1_SIZE:CULong=1<<12;const PTL3_SHIFT:i32=30;const PTL2_SHIFT:i32=21;const PTL1_SHIFT:i32=12;const ENOMEM:i32=12;
#[no_mangle]
pub unsafe extern "C" fn fixture_actual_smaller_page_size(
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
