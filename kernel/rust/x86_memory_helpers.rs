use crate::abi::CULong;

const PTATTR_LARGEPAGE: CULong = 0x80;
const PTATTR_UNCACHABLE: CULong = 0x10000;
const PTATTR_WRITE_COMBINED: CULong = 0x40000;

const ENOMEM: i32 = 12;

const PTL1_SHIFT: i32 = 12;
const PTL2_SHIFT: i32 = 21;
const PTL3_SHIFT: i32 = 30;

const PTL1_SIZE: CULong = 1 << PTL1_SHIFT;
const PTL2_SIZE: CULong = 1 << PTL2_SHIFT;
const PTL3_SIZE: CULong = 1 << PTL3_SHIFT;

const PFLX_PWT: CULong = 0x08;
const PFLX_PCD: CULong = 0x10;

#[no_mangle]
pub extern "C" fn x86_attr_to_l3attr_result(attr: CULong, attr_mask: CULong) -> CULong {
    let result = attr & (attr_mask | PTATTR_LARGEPAGE);

    if (attr & PTATTR_UNCACHABLE) != 0 && (attr & PTATTR_LARGEPAGE) != 0 {
        result | PFLX_PCD | PFLX_PWT
    } else {
        result
    }
}

#[no_mangle]
pub extern "C" fn x86_attr_to_l2attr_result(attr: CULong, attr_mask: CULong) -> CULong {
    let result = attr & (attr_mask | PTATTR_LARGEPAGE);

    if (attr & PTATTR_UNCACHABLE) != 0 && (attr & PTATTR_LARGEPAGE) != 0 {
        result | PFLX_PCD | PFLX_PWT
    } else {
        result
    }
}

#[no_mangle]
pub extern "C" fn x86_attr_to_l1attr_result(attr: CULong, attr_mask: CULong) -> CULong {
    if (attr & PTATTR_UNCACHABLE) != 0 {
        (attr & attr_mask) | PFLX_PCD | PFLX_PWT
    } else if (attr & PTATTR_WRITE_COMBINED) != 0 {
        (attr & attr_mask) | PFLX_PWT
    } else {
        attr & attr_mask
    }
}

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
