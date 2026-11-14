use core::mem::{align_of, offset_of, size_of};
use core::ptr::{read_volatile, write};
use core::sync::atomic::{AtomicI32, Ordering};

use crate::abi::{CInt, CULong, OffT};

type PageHashLockFn = unsafe extern "C" fn(usize) -> CULong;
type PageHashUnlockFn = unsafe extern "C" fn(usize, CULong);
type PageHashLockInitFn = unsafe extern "C" fn(usize);
type PageHashBucketInitFn = unsafe extern "C" fn(*mut ListHead) -> CInt;
type PageHashAllocFn = unsafe extern "C" fn(usize, CInt) -> *mut Page;
type PageMapCountIncFn = unsafe extern "C" fn(*mut Page);
type PageHashCountAllFn = unsafe extern "C" fn(
    usize,
    usize,
    CInt,
    usize,
    usize,
    Option<PageHashLockFn>,
    Option<PageHashUnlockFn>,
) -> CInt;
type PhysToPageLookupOrchestrateFn = unsafe extern "C" fn(
    CULong,
    usize,
    usize,
    CInt,
    CULong,
    usize,
    usize,
    Option<PageHashLockFn>,
    Option<PageHashUnlockFn>,
) -> *mut Page;
type PhysToPageInsertOrchestrateFn = unsafe extern "C" fn(
    CULong,
    usize,
    usize,
    CInt,
    CULong,
    usize,
    usize,
    usize,
    CInt,
    Option<PageHashLockFn>,
    Option<PageHashUnlockFn>,
    Option<PageHashAllocFn>,
) -> *mut Page;
type PhysToPageInsertLogFn = unsafe extern "C" fn(CULong);
type PageUnmapOrchestrateFn = unsafe extern "C" fn(
    *mut Page,
    usize,
    CInt,
    CULong,
    usize,
    Option<PageHashLockFn>,
    Option<PageHashUnlockFn>,
) -> CInt;
type PageUnmapLogFn = unsafe extern "C" fn(CInt, *mut Page, CInt);

const MF_SHM: u32 = 0x40000;
const EINVAL: CInt = 22;
const PAGE_UNMAP_LOG_ENTER: CInt = 1;
const PAGE_UNMAP_LOG_STILL_MAPPED: CInt = 2;
const PAGE_UNMAP_LOG_UNMAPPED: CInt = 3;
const PM_WILL_PAGEIO: u8 = 0x02;
const PM_PAGEIO: u8 = 0x03;
const PM_DONE_PAGEIO: u8 = 0x04;
const PM_PAGEIO_EOF: u8 = 0x05;
const PM_PAGEIO_ERROR: u8 = 0x06;
const PM_MAPPED: u8 = 0x07;
const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;

#[repr(C)]
pub struct ListHead {
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

#[no_mangle]
pub extern "C" fn page_mode_in_memobj_result(mode: CInt) -> CInt {
    matches!(
        mode as u8,
        PM_MAPPED | PM_PAGEIO | PM_WILL_PAGEIO | PM_DONE_PAGEIO | PM_PAGEIO_EOF | PM_PAGEIO_ERROR
    ) as CInt
}
#[no_mangle]
pub extern "C" fn page_multi_mapped_result(count: CInt) -> CInt {
    (count > 1) as CInt
}
#[no_mangle]
pub unsafe extern "C" fn page_is_in_memobj_body_result(page: *mut Page) -> CInt {
    if page.is_null() {
        return 0;
    }

    page_mode_in_memobj_result(unsafe { read_volatile(&(*page).mode) } as CInt)
}
#[no_mangle]
pub unsafe extern "C" fn page_is_multi_mapped_body_result(page: *mut Page) -> CInt {
    if page.is_null() {
        return 0;
    }

    page_multi_mapped_result(unsafe { read_volatile(&(*page).count.counter) })
}
#[no_mangle]
pub unsafe extern "C" fn page_is_in_memobj(page: *mut Page) -> CInt {
    unsafe { page_is_in_memobj_body_result(page) }
}
#[no_mangle]
pub unsafe extern "C" fn page_is_multi_mapped(page: *mut Page) -> CInt {
    unsafe { page_is_multi_mapped_body_result(page) }
}
pub fn fixture_layout()->[usize;5] { [
 size_of::<Page>(),align_of::<Page>(),offset_of!(Page,mode),
 offset_of!(Page,count),size_of::<IhkAtomic>() ] }
