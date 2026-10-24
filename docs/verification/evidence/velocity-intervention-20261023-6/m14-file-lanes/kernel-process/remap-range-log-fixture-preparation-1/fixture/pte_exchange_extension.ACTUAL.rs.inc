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

unsafe fn pte_store(ptep: *mut CULong, value: CULong) {
    write_volatile(ptep, value);
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
extern "C" {
 pub fn pte_is_null(ptep:*const CULong)->CInt;
 pub fn pte_is_fileoff(ptep:*const CULong,pgsize:SizeT)->CInt;
 pub fn pte_is_dirty(ptep:*const CULong,pgsize:SizeT)->CInt;
 pub fn pte_get_phys(ptep:*const CULong)->CULong;
}
