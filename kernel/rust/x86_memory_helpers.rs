use crate::abi::CULong;

const PTATTR_LARGEPAGE: CULong = 0x80;
const PTATTR_UNCACHABLE: CULong = 0x10000;
const PTATTR_WRITE_COMBINED: CULong = 0x40000;

const EINVAL: i32 = 22;
const ENOMEM: i32 = 12;

const PTL1_SHIFT: i32 = 12;
const PTL2_SHIFT: i32 = 21;
const PTL3_SHIFT: i32 = 30;

const PTL1_SIZE: CULong = 1 << PTL1_SHIFT;
const PTL2_SIZE: CULong = 1 << PTL2_SHIFT;
const PTL3_SIZE: CULong = 1 << PTL3_SHIFT;

const PFLX_PWT: CULong = 0x08;
const PFLX_PCD: CULong = 0x10;
const PFL2_SIZE: CULong = 0x80;
const PT_ENTRIES: CULong = 512;

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
pub extern "C" fn x86_set_pte_value_result(
    phys: CULong,
    attr: CULong,
    attr_mask: CULong,
) -> CULong {
    if (attr & PTATTR_LARGEPAGE) != 0 {
        phys | x86_attr_to_l2attr_result(attr, attr_mask) | PFL2_SIZE
    } else {
        phys | x86_attr_to_l1attr_result(attr, attr_mask)
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_set_pte_value_result(
    pgsize: CULong,
    phys: CULong,
    attr: CULong,
    attr_mask: CULong,
    use_1gb_page: i32,
    entryp: *mut CULong,
) -> i32 {
    let entry = if pgsize == PTL1_SIZE {
        phys | x86_attr_to_l1attr_result(attr, attr_mask)
    } else if pgsize == PTL2_SIZE {
        if (phys & (PTL2_SIZE - 1)) != 0 {
            return -1;
        }
        phys | x86_attr_to_l2attr_result(attr | PTATTR_LARGEPAGE, attr_mask)
    } else if pgsize == PTL3_SIZE && use_1gb_page != 0 {
        if (phys & (PTL3_SIZE - 1)) != 0 {
            return -1;
        }
        phys | x86_attr_to_l3attr_result(attr | PTATTR_LARGEPAGE, attr_mask)
    } else {
        return -EINVAL;
    };

    if !entryp.is_null() {
        unsafe {
            *entryp = entry;
        }
    }
    0
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

#[no_mangle]
pub extern "C" fn x86_early_alloc_align_end_result(end_addr: CULong) -> CULong {
    (end_addr + PTL1_SIZE - 1) & !(PTL1_SIZE - 1)
}

#[no_mangle]
pub extern "C" fn x86_early_alloc_exhausted_result(
    current_phys: CULong,
    bootstrap_end: CULong,
) -> i32 {
    (current_phys >= bootstrap_end) as i32
}

#[no_mangle]
pub extern "C" fn x86_early_alloc_next_result(current: CULong, nr_pages: i32) -> CULong {
    current + ((nr_pages as CULong) * PTL1_SIZE)
}

#[no_mangle]
pub unsafe extern "C" fn x86_pt_indices_result(
    virt: CULong,
    l4idxp: *mut i32,
    l3idxp: *mut i32,
    l2idxp: *mut i32,
    l1idxp: *mut i32,
) {
    if !l4idxp.is_null() {
        unsafe {
            *l4idxp = ((virt >> 39) & (PT_ENTRIES - 1)) as i32;
        }
    }
    if !l3idxp.is_null() {
        unsafe {
            *l3idxp = ((virt >> PTL3_SHIFT) & (PT_ENTRIES - 1)) as i32;
        }
    }
    if !l2idxp.is_null() {
        unsafe {
            *l2idxp = ((virt >> PTL2_SHIFT) & (PT_ENTRIES - 1)) as i32;
        }
    }
    if !l1idxp.is_null() {
        unsafe {
            *l1idxp = ((virt >> PTL1_SHIFT) & (PT_ENTRIES - 1)) as i32;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_walk_bounds_result(
    start: CULong,
    end: CULong,
    base: CULong,
    span: CULong,
    shift: i32,
    sixp: *mut i32,
    eixp: *mut i32,
) {
    let size = 1u64 << shift;
    let six = if start <= base {
        0
    } else {
        ((start - base) >> shift) as i32
    };
    let eix = if end == 0 || (span != 0 && base.wrapping_add(span) <= end) {
        PT_ENTRIES as i32
    } else {
        (((end - base) + (size - 1)) >> shift) as i32
    };

    if !sixp.is_null() {
        unsafe {
            *sixp = six;
        }
    }
    if !eixp.is_null() {
        unsafe {
            *eixp = eix;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_large_page_prepare_result(
    entry: CULong,
    pgsize: CULong,
    child_entryp: *mut CULong,
    rss_pgsizep: *mut CULong,
    step_p: *mut CULong,
) -> i32 {
    if pgsize != PTL3_SIZE && pgsize != PTL2_SIZE {
        return -EINVAL;
    }

    if !child_entryp.is_null() {
        unsafe {
            *child_entryp = if pgsize == PTL2_SIZE {
                entry & !PFL2_SIZE
            } else {
                entry
            };
        }
    }
    if !rss_pgsizep.is_null() {
        unsafe {
            *rss_pgsizep = pgsize / PT_ENTRIES;
        }
    }
    if !step_p.is_null() {
        unsafe {
            *step_p = pgsize / PT_ENTRIES;
        }
    }

    0
}

#[no_mangle]
pub extern "C" fn x86_split_large_page_next_entry_result(entry: CULong, pgsize: CULong) -> CULong {
    entry + pgsize / PT_ENTRIES
}
