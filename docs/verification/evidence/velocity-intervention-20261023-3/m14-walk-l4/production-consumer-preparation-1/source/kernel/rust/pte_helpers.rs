use core::ptr::{read_volatile, write_volatile};
use core::sync::atomic::{AtomicU64, Ordering};

use crate::abi::{CInt, CULong, OffT, SizeT, VmRegions};

const PAGE_SHIFT: u32 = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);
const PM_STATUS_OFFSET: u32 = 61;
const PM_STATUS_MASK: CULong = 0xe000_0000_0000_0000;
const PM_PSHIFT_OFFSET: u32 = 55;
const PM_PSHIFT_MASK: CULong = 0x1f80_0000_0000_0000;
const PM_PFRAME_MASK: CULong = 0x007f_ffff_ffff_ffff;

const PTL4_SHIFT: u32 = 39;
const PTL3_SHIFT: u32 = 30;
const PTL2_SHIFT: u32 = 21;
const PTL1_SHIFT: u32 = 12;
const PTL4_SIZE: SizeT = 1 << PTL4_SHIFT;
const PTL3_SIZE: SizeT = 1 << PTL3_SHIFT;
const PTL2_SIZE: SizeT = 1 << PTL2_SHIFT;
const PTL1_SIZE: SizeT = 1 << PTL1_SHIFT;

const PT_PHYSMASK: CULong = ((1u64 << 52) - 1) & PAGE_MASK;
const PTE_NULL: CULong = 0;
const PF_PRESENT: CULong = 0x01;
const PF_WRITABLE: CULong = 0x02;
const PFLX_PWT: CULong = 0x08;
const PFLX_PCD: CULong = 0x10;
const PFL1_PWT: CULong = PFLX_PWT;
const PFL1_PCD: CULong = PFLX_PCD;
const PFL1_DIRTY: CULong = 0x40;
const PFL1_FILEOFF: CULong = 1 << 11;
const PFL2_DIRTY: CULong = 0x40;
const PFL2_SIZE: CULong = 0x80;
const PFL2_FILEOFF: CULong = 1 << 11;
const PFL3_DIRTY: CULong = 0x40;
const PFL3_SIZE: CULong = 0x80;
const PFL3_FILEOFF: CULong = 1 << 11;

const PTATTR_DIRTY: CULong = 0x40;
const PTATTR_LARGEPAGE: CULong = 0x80;
const PTATTR_FILEOFF: CULong = PFL2_FILEOFF;
const PTATTR_UNCACHABLE: CULong = 0x10000;
const PTATTR_WRITE_COMBINED: CULong = 0x40000;
const EINVAL: CInt = 22;

extern "C" {
    static attr_mask: CULong;
}

#[inline(always)]
unsafe fn pte_load(ptep: *const CULong) -> CULong {
    read_volatile(ptep)
}

#[inline(always)]
unsafe fn pte_store(ptep: *mut CULong, value: CULong) {
    write_volatile(ptep, value);
}

#[no_mangle]
pub unsafe extern "C" fn STACK_TOP(region: *const VmRegions) -> CULong {
    (*region).user_end
}

#[no_mangle]
pub extern "C" fn PM_STATUS(nr: CULong) -> CULong {
    nr.wrapping_shl(PM_STATUS_OFFSET) & PM_STATUS_MASK
}

#[no_mangle]
pub extern "C" fn PM_PSHIFT(x: CULong) -> CULong {
    x.wrapping_shl(PM_PSHIFT_OFFSET) & PM_PSHIFT_MASK
}

#[no_mangle]
pub extern "C" fn PM_PFRAME(x: CULong) -> CULong {
    x & PM_PFRAME_MASK
}

#[no_mangle]
pub extern "C" fn ALIGN_DOWN(x: CULong, align: CULong) -> CULong {
    x & !align.wrapping_sub(1)
}

#[no_mangle]
pub extern "C" fn ALIGN_UP(x: CULong, align: CULong) -> CULong {
    ALIGN_DOWN(x.wrapping_add(align).wrapping_sub(1), align)
}

#[no_mangle]
pub extern "C" fn pfn_is_write_combined(pfn: CULong) -> CInt {
    ((pfn & PFL1_PWT) != 0 && (pfn & PFL1_PCD) == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn pte_is_null(ptep: *const CULong) -> CInt {
    (pte_load(ptep) == PTE_NULL) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn pte_is_present(ptep: *const CULong) -> CInt {
    ((pte_load(ptep) & PF_PRESENT) != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn pte_is_writable(ptep: *const CULong) -> CInt {
    ((pte_load(ptep) & PF_WRITABLE) != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn pte_is_dirty(ptep: *const CULong, pgsize: SizeT) -> CInt {
    let pte = pte_load(ptep);
    let mask = match pgsize {
        PTL1_SIZE => PFL1_DIRTY,
        PTL2_SIZE => PFL2_DIRTY,
        PTL3_SIZE => PFL3_DIRTY,
        _ => PTATTR_DIRTY,
    };

    ((pte & mask) != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn pte_is_fileoff(ptep: *const CULong, pgsize: SizeT) -> CInt {
    let pte = pte_load(ptep);
    let mask = match pgsize {
        PTL1_SIZE => PFL1_FILEOFF,
        PTL2_SIZE => PFL2_FILEOFF,
        PTL3_SIZE => PFL3_FILEOFF,
        _ => PTATTR_FILEOFF,
    };

    ((pte & mask) != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn pte_update_phys(ptep: *mut CULong, phys: CULong) {
    let pte = pte_load(ptep);

    pte_store(ptep, (pte & !PT_PHYSMASK) | (phys & PT_PHYSMASK));
}

#[no_mangle]
pub unsafe extern "C" fn pte_get_phys(ptep: *const CULong) -> CULong {
    pte_load(ptep) & PT_PHYSMASK
}

#[no_mangle]
pub unsafe extern "C" fn pte_get_off(ptep: *const CULong, _pgsize: SizeT) -> OffT {
    (pte_load(ptep) & PAGE_MASK) as OffT
}

#[no_mangle]
pub unsafe extern "C" fn pte_get_attr(ptep: *const CULong, pgsize: SizeT) -> CULong {
    let pte = pte_load(ptep);
    let mut attr = pte & attr_mask;

    if (pte & PFLX_PWT) != 0 {
        if (pte & PFLX_PCD) != 0 {
            attr |= PTATTR_UNCACHABLE;
        } else {
            attr |= PTATTR_WRITE_COMBINED;
        }
    }
    if (pgsize == PTL2_SIZE && (pte & PFL2_SIZE) != 0)
        || (pgsize == PTL3_SIZE && (pte & PFL3_SIZE) != 0)
    {
        attr |= PTATTR_LARGEPAGE;
    }

    attr
}

#[no_mangle]
pub unsafe extern "C" fn pte_make_null(ptep: *mut CULong, _pgsize: SizeT) {
    pte_store(ptep, PTE_NULL);
}

#[no_mangle]
pub unsafe extern "C" fn pte_make_fileoff(
    off: OffT,
    ptattr: CULong,
    pgsize: SizeT,
    ptep: *mut CULong,
) {
    let mut attr = ptattr & !PAGE_MASK;

    match pgsize {
        PTL1_SIZE => attr |= PFL1_FILEOFF,
        PTL2_SIZE => attr |= PFL2_FILEOFF | PFL2_SIZE,
        PTL3_SIZE => attr |= PFL3_FILEOFF | PFL3_SIZE,
        _ => attr |= PTATTR_FILEOFF,
    }

    pte_store(ptep, ((off as CULong) & PAGE_MASK) | attr);
}

#[no_mangle]
pub unsafe extern "C" fn pte_xchg(ptep: *mut CULong, valp: *mut CULong) {
    let new_value = read_volatile(valp);
    let old_value = AtomicU64::from_ptr(ptep).swap(new_value, Ordering::SeqCst);
    write_volatile(valp, old_value);
}

#[no_mangle]
pub unsafe extern "C" fn pte_clear_dirty(ptep: *mut CULong, pgsize: SizeT) {
    let mask = match pgsize {
        PTL2_SIZE => !PFL2_DIRTY,
        PTL3_SIZE => !PFL3_DIRTY,
        _ => !PFL1_DIRTY,
    };

    let _ = AtomicU64::from_ptr(ptep).fetch_and(mask, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn pte_set_dirty(ptep: *mut CULong, pgsize: SizeT) {
    let mask = match pgsize {
        PTL2_SIZE => PFL2_DIRTY,
        PTL3_SIZE => PFL3_DIRTY,
        _ => PFL1_DIRTY,
    };

    let _ = AtomicU64::from_ptr(ptep).fetch_or(mask, Ordering::SeqCst);
}

#[no_mangle]
pub extern "C" fn pte_is_contiguous(_ptep: *const CULong) -> CInt {
    0
}

#[no_mangle]
pub extern "C" fn pgsize_is_contiguous(_pgsize: SizeT) -> CInt {
    0
}

#[no_mangle]
pub extern "C" fn pgsize_to_tbllv(pgsize: SizeT) -> CInt {
    match pgsize {
        PTL1_SIZE => 1,
        PTL2_SIZE => 2,
        PTL3_SIZE => 3,
        PTL4_SIZE => 4,
        _ => 0,
    }
}

#[no_mangle]
pub extern "C" fn pgsize_to_pgshift(pgsize: SizeT) -> CInt {
    match pgsize {
        PTL1_SIZE => PTL1_SHIFT as CInt,
        PTL2_SIZE => PTL2_SHIFT as CInt,
        PTL3_SIZE => PTL3_SHIFT as CInt,
        PTL4_SIZE => PTL4_SHIFT as CInt,
        _ => -EINVAL,
    }
}

#[no_mangle]
pub extern "C" fn tbllv_to_pgsize(level: CInt) -> SizeT {
    match level {
        1 => PTL1_SIZE,
        2 => PTL2_SIZE,
        3 => PTL3_SIZE,
        4 => PTL4_SIZE,
        _ => 0,
    }
}

#[no_mangle]
pub extern "C" fn tbllv_to_contpgsize(_level: CInt) -> SizeT {
    0
}

#[no_mangle]
pub extern "C" fn tbllv_to_contpgshift(_level: CInt) -> CInt {
    0
}

#[no_mangle]
pub extern "C" fn get_contiguous_head(ptep: *mut CULong, _pgsize: SizeT) -> *mut CULong {
    ptep
}

#[no_mangle]
pub extern "C" fn get_contiguous_tail(ptep: *mut CULong, _pgsize: SizeT) -> *mut CULong {
    ptep
}

#[no_mangle]
pub extern "C" fn page_is_contiguous_head(_ptep: *const CULong, _pgsize: SizeT) -> CInt {
    0
}

#[no_mangle]
pub extern "C" fn page_is_contiguous_tail(_ptep: *const CULong, _pgsize: SizeT) -> CInt {
    0
}

#[no_mangle]
pub extern "C" fn arch_adjust_allocate_page_size(
    _pt: *mut core::ffi::c_void,
    _fault_addr: CULong,
    _ptep: *mut CULong,
    _pgaddrp: *mut *mut core::ffi::c_void,
    _pgsizep: *mut SizeT,
) {
}
