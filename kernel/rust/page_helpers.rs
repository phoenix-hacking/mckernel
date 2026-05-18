use core::mem::{align_of, offset_of, size_of};
use core::ptr::read_volatile;

use crate::abi::{CInt, CULong, OffT};

const MF_SHM: u32 = 0x40000;
const PM_WILL_PAGEIO: u8 = 0x02;
const PM_PAGEIO: u8 = 0x03;
const PM_DONE_PAGEIO: u8 = 0x04;
const PM_PAGEIO_EOF: u8 = 0x05;
const PM_PAGEIO_ERROR: u8 = 0x06;
const PM_MAPPED: u8 = 0x07;

#[repr(C)]
struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}

#[repr(C)]
struct IhkAtomic {
    counter: CInt,
}

#[repr(C)]
struct IhkAtomic64 {
    counter64: i64,
}

#[repr(C)]
pub struct Page {
    list: ListHead,
    hash: ListHead,
    mode: u8,
    phys: CULong,
    count: IhkAtomic,
    mapped: IhkAtomic64,
    offset: OffT,
    pgshift: CInt,
}

const _: () = {
    assert!(size_of::<Page>() == 80);
    assert!(align_of::<Page>() == 8);
    assert!(offset_of!(Page, list) == 0);
    assert!(offset_of!(Page, hash) == 16);
    assert!(offset_of!(Page, mode) == 32);
    assert!(offset_of!(Page, phys) == 40);
    assert!(offset_of!(Page, count) == 48);
    assert!(offset_of!(Page, mapped) == 56);
    assert!(offset_of!(Page, offset) == 64);
    assert!(offset_of!(Page, pgshift) == 72);
};

#[inline(always)]
unsafe fn page_is_in_memobj(page: *const Page) -> bool {
    matches!(
        read_volatile(&(*page).mode),
        PM_MAPPED | PM_PAGEIO | PM_WILL_PAGEIO | PM_DONE_PAGEIO | PM_PAGEIO_EOF | PM_PAGEIO_ERROR
    )
}

#[inline(always)]
unsafe fn page_is_multi_mapped(page: *const Page) -> bool {
    read_volatile(&(*page).count.counter) > 1
}

#[no_mangle]
pub unsafe extern "C" fn page_to_phys(page: *mut Page) -> CULong {
    if page.is_null() {
        0
    } else {
        read_volatile(&(*page).phys)
    }
}

#[no_mangle]
pub unsafe extern "C" fn is_splitable(page: *mut Page, memobj_flags: u32) -> CInt {
    if !page.is_null() && (page_is_in_memobj(page) || page_is_multi_mapped(page)) {
        if (memobj_flags & MF_SHM) != 0 {
            return 1;
        }
        return 0;
    }

    1
}
