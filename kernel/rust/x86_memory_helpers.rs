use core::ffi::c_void;
use core::ptr::{read_volatile, write_volatile};
use core::sync::atomic::{AtomicU64, Ordering};

use crate::abi::CULong;

const PTATTR_LARGEPAGE: CULong = 0x80;
const PTATTR_UNCACHABLE: CULong = 0x10000;
const PTATTR_WRITE_COMBINED: CULong = 0x40000;

const EINVAL: i32 = 22;
const ENOMEM: i32 = 12;
const ENOTSUPP: i32 = 524;
const ENOENT: i32 = 2;

const PTL1_SHIFT: i32 = 12;
const PTL2_SHIFT: i32 = 21;
const PTL3_SHIFT: i32 = 30;
const LARGE_PAGE_SHIFT: i32 = 21;

const PTL1_SIZE: CULong = 1 << PTL1_SHIFT;
const PTL2_SIZE: CULong = 1 << PTL2_SHIFT;
const PTL3_SIZE: CULong = 1 << PTL3_SHIFT;
const PAGE_MASK: CULong = !(PTL1_SIZE - 1);
const LARGE_PAGE_MASK: CULong = !((1 << LARGE_PAGE_SHIFT) - 1);
const PT_PHYSMASK: CULong = (((1 as CULong) << 52) - 1) & PAGE_MASK;

const PFLX_PWT: CULong = 0x08;
const PFLX_PCD: CULong = 0x10;
const PFL2_PRESENT: CULong = 0x01;
const PFL2_SIZE: CULong = 0x80;
const PFL2_PDIR_ATTR: CULong = 0x07;
const PFL_FILEOFF: CULong = 1 << 11;
const PT_ENTRIES: CULong = 512;
const PTE_NULL: CULong = 0;
const NOPHYS: CULong = !0;

const X86_VISIT_PTE_SKIP: i32 = 0;
const X86_VISIT_PTE_DIRECT: i32 = 1;
const X86_VISIT_PTE_ALLOC_AND_WALK: i32 = 2;
const X86_VISIT_PTE_WALK: i32 = 3;
const X86_VISIT_PTE_SPLIT_ERROR: i32 = 4;

const X86_CLEAR_RANGE_SKIP: i32 = 0;
const X86_CLEAR_RANGE_SPLIT_ERROR: i32 = 1;
const X86_CLEAR_RANGE_CLEAR_LARGE: i32 = 2;
const X86_CLEAR_RANGE_WALK: i32 = 3;

const X86_CLEAR_OLD_FLUSH_MEMOBJ: i32 = 0x01;
const X86_CLEAR_OLD_FREE_ANON: i32 = 0x02;
const X86_CLEAR_OLD_XPMEM_KEEP: i32 = 0x04;
const X86_CLEAR_OLD_TRY_UNMAP: i32 = 0x08;

const X86_CHANGE_ATTR_ENOENT: i32 = 0;
const X86_CHANGE_ATTR_APPLY: i32 = 1;
const X86_CHANGE_ATTR_SPLIT_ERROR: i32 = 2;
const X86_CHANGE_ATTR_WALK: i32 = 3;

const X86_SET_RANGE_APPLY: i32 = 0;
const X86_SET_RANGE_ALLOC_AND_WALK: i32 = 1;
const X86_SET_RANGE_MAP_LARGE: i32 = 2;
const X86_SET_RANGE_BUSY: i32 = 3;
const X86_SET_RANGE_WALK: i32 = 4;

const X86_LOOKUP_PTE_MISS: i32 = 0;
const X86_LOOKUP_PTE_WALK: i32 = 1;
const X86_LOOKUP_PTE_HIT: i32 = 2;
const X86_VTOP_MISS: i32 = 0;
const X86_VTOP_WALK: i32 = 1;
const X86_VTOP_HIT: i32 = 2;
const X86_DESTROY_PT_SKIP: i32 = 0;
const X86_DESTROY_PT_DESCEND: i32 = 1;

type X86WalkPteCallback =
    unsafe extern "C" fn(*mut c_void, *mut CULong, CULong, CULong, CULong) -> i32;
type X86WalkPhysCheckFn = unsafe extern "C" fn(CULong) -> i32;

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
pub unsafe extern "C" fn x86_walk_step_result(
    current_ret: i32,
    error: i32,
    next_retp: *mut i32,
) -> i32 {
    let mut next_ret = current_ret;
    let mut stop = 0;

    if error == 0 {
        next_ret = 0;
    } else if error != -ENOENT {
        next_ret = error;
        stop = 1;
    }

    if !next_retp.is_null() {
        unsafe {
            *next_retp = next_ret;
        }
    }
    stop
}

#[no_mangle]
pub unsafe extern "C" fn x86_walk_pte_range_result(
    pt_addr: CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    span: CULong,
    shift: i32,
    funcp: Option<X86WalkPteCallback>,
    args: *mut c_void,
    phys_check_fn: Option<X86WalkPhysCheckFn>,
    phys_mask: CULong,
) -> i32 {
    if pt_addr == 0 {
        return -ENOENT;
    }
    let Some(func) = funcp else {
        return -ENOENT;
    };

    let mut six = 0;
    let mut eix = 0;
    unsafe {
        x86_walk_bounds_result(start, end, base, span, shift, &mut six, &mut eix);
    }

    let pt = pt_addr as *mut CULong;
    let mut ret = -ENOENT;
    let mut i = six;
    while i < eix {
        let ptep = unsafe { pt.add(i as usize) };

        if let Some(check) = phys_check_fn {
            let entry = unsafe { read_volatile(ptep) };
            if unsafe { check(entry & phys_mask) } == -1 {
                i += 1;
                continue;
            }
        }

        let off = (i as CULong) << (shift as u32);
        let error = unsafe { func(args, ptep, base.wrapping_add(off), start, end) };
        if unsafe { x86_walk_step_result(ret, error, &mut ret) } != 0 {
            break;
        }
        i += 1;
    }

    ret
}

#[no_mangle]
pub unsafe extern "C" fn x86_virt_to_phys_level_result(
    entry: CULong,
    virt: CULong,
    level_shift: i32,
    size_flag: CULong,
    physp: *mut CULong,
    sizep: *mut CULong,
) -> i32 {
    let level_size = (1 as CULong) << (level_shift as u32);

    if (entry & PFL2_PRESENT) == 0 {
        return X86_VTOP_MISS;
    }

    if (size_flag != 0 && (entry & size_flag) != 0) || level_shift == PTL1_SHIFT {
        if !physp.is_null() {
            unsafe {
                *physp = (entry & PT_PHYSMASK) | (virt & (level_size - 1));
            }
        }
        if !sizep.is_null() {
            unsafe {
                *sizep = level_size;
            }
        }
        return X86_VTOP_HIT;
    }

    X86_VTOP_WALK
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

#[no_mangle]
pub unsafe extern "C" fn x86_split_large_page_source_result(
    entry: CULong,
    pgsize: CULong,
    phys_basep: *mut CULong,
    child_entryp: *mut CULong,
    rss_pgsizep: *mut CULong,
) -> i32 {
    let mut child_entry = 0;
    let mut rss_pgsize = 0;
    let error = unsafe {
        x86_split_large_page_prepare_result(
            entry,
            pgsize,
            &mut child_entry,
            &mut rss_pgsize,
            core::ptr::null_mut(),
        )
    };
    if error != 0 {
        return -EINVAL;
    }

    if !phys_basep.is_null() {
        unsafe {
            *phys_basep = if (entry & x86_fileoff_flag(pgsize)) != 0 {
                NOPHYS
            } else {
                entry & PT_PHYSMASK
            };
        }
    }
    if !child_entryp.is_null() {
        unsafe {
            *child_entryp = child_entry;
        }
    }
    if !rss_pgsizep.is_null() {
        unsafe {
            *rss_pgsizep = rss_pgsize;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_large_page_child_map_result(
    phys_base: CULong,
    pgsize: CULong,
    index: i32,
    physp: *mut CULong,
) -> i32 {
    if phys_base == NOPHYS || pgsize == PTL2_SIZE {
        return 0;
    }

    if !physp.is_null() {
        unsafe {
            *physp = phys_base + ((index as CULong) * pgsize / PT_ENTRIES);
        }
    }

    1
}

#[no_mangle]
pub extern "C" fn x86_split_large_page_publish_result(child_pt_phys: CULong) -> CULong {
    (child_pt_phys & PT_PHYSMASK) | PFL2_PDIR_ATTR
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_large_page_source_unmap_result(
    phys_base: CULong,
    pgsize: CULong,
    physp: *mut CULong,
) -> i32 {
    if phys_base == NOPHYS || pgsize == PTL2_SIZE {
        return 0;
    }

    if !physp.is_null() {
        unsafe {
            *physp = phys_base;
        }
    }

    1
}

#[no_mangle]
pub extern "C" fn x86_clear_pt_page_aligned_addr_result(virt: CULong, largepage: i32) -> CULong {
    if largepage != 0 {
        virt & LARGE_PAGE_MASK
    } else {
        virt & PAGE_MASK
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_pt_page_target_result(
    l2_entry: CULong,
    largepage: i32,
    clear_l2p: *mut i32,
) -> i32 {
    if (l2_entry & PFL2_PRESENT) == 0 {
        return -EINVAL;
    }

    if !clear_l2p.is_null() {
        unsafe {
            *clear_l2p = (largepage != 0) as i32;
        }
    }

    0
}

#[no_mangle]
pub extern "C" fn x86_visit_pte_action_result(
    entry: CULong,
    skip_null: i32,
    start: CULong,
    end: CULong,
    base: CULong,
    level_size: CULong,
    target_shift: i32,
    pgshift: i32,
    size_flag: CULong,
    direct_requires_size: i32,
    direct_enabled: i32,
    can_allocate: i32,
) -> i32 {
    let is_null = entry == PTE_NULL;
    let is_large = size_flag != 0 && (entry & size_flag) != 0;
    let full_cover = start <= base && (base.wrapping_add(level_size) <= end || end == 0);
    let pgshift_match = pgshift == 0 || pgshift == target_shift;

    if is_null {
        if skip_null != 0 {
            return X86_VISIT_PTE_SKIP;
        }
        if direct_enabled != 0 && direct_requires_size == 0 && full_cover && pgshift_match {
            return X86_VISIT_PTE_DIRECT;
        }
        return if can_allocate != 0 {
            X86_VISIT_PTE_ALLOC_AND_WALK
        } else {
            X86_VISIT_PTE_SKIP
        };
    }

    if direct_enabled != 0 && (direct_requires_size == 0 || is_large) && full_cover && pgshift_match
    {
        return X86_VISIT_PTE_DIRECT;
    }

    if is_large {
        X86_VISIT_PTE_SPLIT_ERROR
    } else {
        X86_VISIT_PTE_WALK
    }
}

#[no_mangle]
pub extern "C" fn x86_clear_range_validate_result(
    start: CULong,
    end: CULong,
    user_start: CULong,
    user_end: CULong,
) -> i32 {
    if start < user_start || user_end < end || end <= start {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn x86_clear_range_free_physical_result(
    free_physical: i32,
    is_dev_file: i32,
    is_premap: i32,
    is_straight_main: i32,
) -> i32 {
    (free_physical != 0 && is_dev_file == 0 && is_premap == 0 && is_straight_main == 0) as i32
}

#[no_mangle]
pub extern "C" fn x86_clear_range_entry_action_result(
    entry: CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    level_size: CULong,
    size_flag: CULong,
) -> i32 {
    if entry == PTE_NULL {
        return X86_CLEAR_RANGE_SKIP;
    }

    if (entry & size_flag) != 0 {
        if base < start || end < base.wrapping_add(level_size) {
            return X86_CLEAR_RANGE_SPLIT_ERROR;
        }
        return X86_CLEAR_RANGE_CLEAR_LARGE;
    }

    X86_CLEAR_RANGE_WALK
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_old_entry_result(
    entry: CULong,
    pgsize: CULong,
    physp: *mut CULong,
    fileoffp: *mut i32,
    dirtyp: *mut i32,
) {
    if !physp.is_null() {
        unsafe {
            *physp = entry & PT_PHYSMASK;
        }
    }
    if !fileoffp.is_null() {
        unsafe {
            *fileoffp = ((entry & x86_fileoff_flag(pgsize)) != 0) as i32;
        }
    }
    if !dirtyp.is_null() {
        unsafe {
            *dirtyp = ((entry & 0x40) != 0) as i32;
        }
    }
}

#[no_mangle]
pub extern "C" fn x86_clear_range_old_action_result(
    is_fileoff: i32,
    free_physical: i32,
    has_page: i32,
    page_in_memobj: i32,
    entry_dirty: i32,
    has_memobj: i32,
    memobj_no_flush: i32,
    memobj_xpmem: i32,
) -> i32 {
    if is_fileoff != 0 {
        return 0;
    }

    let mut action = 0;

    if has_page != 0
        && page_in_memobj != 0
        && entry_dirty != 0
        && has_memobj != 0
        && memobj_no_flush == 0
    {
        action |= X86_CLEAR_OLD_FLUSH_MEMOBJ;
    }

    if free_physical != 0 {
        if has_page == 0 {
            if has_memobj == 0 || memobj_xpmem == 0 {
                action |= X86_CLEAR_OLD_FREE_ANON;
            } else {
                action |= X86_CLEAR_OLD_XPMEM_KEEP;
            }
        } else {
            action |= X86_CLEAR_OLD_TRY_UNMAP;
        }
    }

    action
}

#[no_mangle]
pub extern "C" fn x86_change_attr_leaf_action_result(entry: CULong, fileoff_flag: CULong) -> i32 {
    if entry == PTE_NULL || (fileoff_flag != 0 && (entry & fileoff_flag) != 0) {
        return X86_CHANGE_ATTR_ENOENT;
    }

    X86_CHANGE_ATTR_APPLY
}

#[no_mangle]
pub extern "C" fn x86_change_attr_entry_action_result(
    entry: CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    level_size: CULong,
    size_flag: CULong,
    fileoff_flag: CULong,
) -> i32 {
    if entry == PTE_NULL || (fileoff_flag != 0 && (entry & fileoff_flag) != 0) {
        return X86_CHANGE_ATTR_ENOENT;
    }

    if size_flag != 0 && (entry & size_flag) != 0 {
        if base < start || end < base.wrapping_add(level_size) {
            return X86_CHANGE_ATTR_SPLIT_ERROR;
        }
        return X86_CHANGE_ATTR_APPLY;
    }

    X86_CHANGE_ATTR_WALK
}

#[no_mangle]
pub extern "C" fn x86_set_range_leaf_action_result(entry: CULong) -> i32 {
    if entry == PTE_NULL {
        X86_SET_RANGE_APPLY
    } else {
        X86_SET_RANGE_BUSY
    }
}

#[no_mangle]
pub extern "C" fn x86_set_range_entry_action_result(
    entry: CULong,
    base: CULong,
    start: CULong,
    end: CULong,
    diff: CULong,
    pgshift: i32,
    target_shift: i32,
    level_size: CULong,
    size_flag: CULong,
    direct_enabled: i32,
) -> i32 {
    let full_cover = start <= base && base.wrapping_add(level_size) <= end;
    let diff_aligned = (diff & level_size.wrapping_sub(1)) == 0;
    let pgshift_match = pgshift == 0 || pgshift == target_shift;

    if entry == PTE_NULL {
        if direct_enabled != 0 && full_cover && diff_aligned && pgshift_match {
            return X86_SET_RANGE_MAP_LARGE;
        }
        return X86_SET_RANGE_ALLOC_AND_WALK;
    }

    if size_flag != 0 && (entry & size_flag) != 0 {
        return X86_SET_RANGE_BUSY;
    }

    X86_SET_RANGE_WALK
}

#[no_mangle]
pub unsafe extern "C" fn x86_set_range_map_entry_result(
    phys_base: CULong,
    base: CULong,
    start: CULong,
    attr: CULong,
    level_shift: i32,
    attr_mask: CULong,
    physp: *mut CULong,
    entryp: *mut CULong,
) -> i32 {
    let phys = phys_base.wrapping_add(base.wrapping_sub(start));
    let entry = if level_shift == PTL1_SHIFT {
        phys | x86_attr_to_l1attr_result(attr, attr_mask)
    } else if level_shift == PTL2_SHIFT {
        phys | x86_attr_to_l2attr_result(attr | PTATTR_LARGEPAGE, attr_mask)
    } else if level_shift == PTL3_SHIFT {
        phys | x86_attr_to_l3attr_result(attr | PTATTR_LARGEPAGE, attr_mask)
    } else {
        return -EINVAL;
    };

    if !physp.is_null() {
        unsafe {
            *physp = phys;
        }
    }
    if !entryp.is_null() {
        unsafe {
            *entryp = entry;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_pte_store_result(ptep: *mut CULong, entry: CULong) -> i32 {
    if ptep.is_null() {
        return -EINVAL;
    }

    unsafe {
        write_volatile(ptep, entry);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_pte_publish_table_result(ptep: *mut CULong, entry: CULong) -> CULong {
    if ptep.is_null() {
        return NOPHYS;
    }

    let atomic = unsafe { &*(ptep.cast::<AtomicU64>()) };
    match atomic.compare_exchange(PTE_NULL, entry, Ordering::SeqCst, Ordering::SeqCst) {
        Ok(old) | Err(old) => old,
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_pte_clear_result(ptep: *mut CULong) -> CULong {
    if ptep.is_null() {
        return NOPHYS;
    }

    let atomic = unsafe { &*(ptep.cast::<AtomicU64>()) };
    atomic.swap(PTE_NULL, Ordering::SeqCst)
}

#[no_mangle]
pub unsafe extern "C" fn x86_pte_apply_attr_result(
    ptep: *mut CULong,
    clrpte: CULong,
    setpte: CULong,
) -> CULong {
    if ptep.is_null() {
        return NOPHYS;
    }

    let entry = unsafe { *ptep };
    let updated = (entry & !clrpte) | setpte;
    unsafe {
        write_volatile(ptep, updated);
    }
    updated
}

#[no_mangle]
pub extern "C" fn x86_lookup_default_pgshift_result(pgshift: i32, use_1gb_page: i32) -> i32 {
    if pgshift != 0 {
        pgshift
    } else if use_1gb_page != 0 {
        PTL3_SHIFT
    } else {
        PTL2_SHIFT
    }
}

#[no_mangle]
pub extern "C" fn x86_lookup_l4_empty_pgshift_result(pgshift: i32) -> i32 {
    if pgshift > PTL3_SHIFT {
        PTL3_SHIFT
    } else {
        pgshift
    }
}

#[no_mangle]
pub extern "C" fn x86_lookup_level_action_result(
    entry: CULong,
    pgshift: i32,
    level_shift: i32,
    size_flag: CULong,
) -> i32 {
    if entry == PTE_NULL || (size_flag != 0 && (entry & size_flag) != 0) {
        if pgshift >= level_shift {
            X86_LOOKUP_PTE_HIT
        } else {
            X86_LOOKUP_PTE_MISS
        }
    } else {
        X86_LOOKUP_PTE_WALK
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_lookup_shape_result(
    virt: CULong,
    pgshift: i32,
    basep: *mut CULong,
    sizep: *mut CULong,
    p2alignp: *mut i32,
) {
    let size = (1 as CULong) << (pgshift as u32);
    let base = virt & !(size - 1);

    if !basep.is_null() {
        unsafe {
            *basep = base;
        }
    }
    if !sizep.is_null() {
        unsafe {
            *sizep = size;
        }
    }
    if !p2alignp.is_null() {
        unsafe {
            *p2alignp = pgshift - PTL1_SHIFT;
        }
    }
}

fn x86_fileoff_flag(_pgsize: CULong) -> CULong {
    PFL_FILEOFF
}

#[no_mangle]
pub unsafe extern "C" fn x86_move_pte_preflight_result(
    entry: CULong,
    pgsize: CULong,
    src: CULong,
    dest: CULong,
    pgaddr: CULong,
    mapped_destp: *mut CULong,
) -> i32 {
    if (entry & x86_fileoff_flag(pgsize)) != 0 {
        return -ENOTSUPP;
    }

    if !mapped_destp.is_null() {
        unsafe {
            *mapped_destp = dest.wrapping_add(pgaddr.wrapping_sub(src));
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn x86_move_pte_entry_parts_result(
    entry: CULong,
    physp: *mut CULong,
    attrp: *mut CULong,
) {
    if !physp.is_null() {
        unsafe {
            *physp = entry & PT_PHYSMASK;
        }
    }
    if !attrp.is_null() {
        unsafe {
            *attrp = entry & !PT_PHYSMASK;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_destroy_pt_entry_action_result(
    level: i32,
    entry: CULong,
    lower_physp: *mut CULong,
) -> i32 {
    if !lower_physp.is_null() {
        unsafe {
            *lower_physp = 0;
        }
    }

    if level <= 1 || (entry & PFL2_PRESENT) == 0 || (entry & PFL2_SIZE) != 0 {
        return X86_DESTROY_PT_SKIP;
    }

    if !lower_physp.is_null() {
        unsafe {
            *lower_physp = entry & PT_PHYSMASK;
        }
    }
    X86_DESTROY_PT_DESCEND
}
