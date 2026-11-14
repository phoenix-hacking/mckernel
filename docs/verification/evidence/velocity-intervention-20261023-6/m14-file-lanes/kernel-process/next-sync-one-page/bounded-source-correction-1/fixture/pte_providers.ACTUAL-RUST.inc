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

unsafe fn pte_load(ptep: *const CULong) -> CULong {
    read_volatile(ptep)
}
#[no_mangle]
pub unsafe extern "C" fn pte_is_null(ptep: *const CULong) -> CInt {
    (pte_load(ptep) == PTE_NULL) as CInt
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
pub unsafe extern "C" fn pte_get_phys(ptep: *const CULong) -> CULong {
    pte_load(ptep) & PT_PHYSMASK
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
