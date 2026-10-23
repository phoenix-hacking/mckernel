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

#[inline(always)]
unsafe fn page_in_memobj_predicate(page: *const Page) -> bool {
    page_mode_in_memobj_result(read_volatile(&(*page).mode) as CInt) != 0
}

#[inline(always)]
unsafe fn page_multi_mapped_predicate(page: *const Page) -> bool {
    page_multi_mapped_result(read_volatile(&(*page).count.counter)) != 0
}

#[inline(always)]
unsafe fn page_count(page: *mut Page) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*page).count.counter)
}

#[inline(always)]
unsafe fn list_del(entry: *mut ListHead) {
    let prev = (*entry).prev;
    let next = (*entry).next;

    (*next).prev = prev;
    (*prev).next = next;
    write(&mut (*entry).next, LIST_POISON1 as *mut ListHead);
    write(&mut (*entry).prev, LIST_POISON2 as *mut ListHead);
}

#[inline(always)]
unsafe fn init_list_head(head: *mut ListHead) {
    write(&mut (*head).next, head);
    write(&mut (*head).prev, head);
}

#[inline(always)]
unsafe fn list_add(entry: *mut ListHead, head: *mut ListHead) {
    let next = (*head).next;

    (*next).prev = entry;
    (*entry).next = next;
    (*entry).prev = head;
    (*head).next = entry;
}

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

#[no_mangle]
pub unsafe extern "C" fn page_to_phys(page: *mut Page) -> CULong {
    if page.is_null() {
        0
    } else {
        read_volatile(&(*page).phys)
    }
}

#[no_mangle]
pub unsafe extern "C" fn page_map_count_inc_result(page: *mut Page) {
    page_count(page).fetch_add(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn page_map_body_result(
    page: *mut Page,
    count_inc_fn: Option<PageMapCountIncFn>,
) {
    if let Some(count_inc) = count_inc_fn {
        count_inc(page);
    }
}

#[no_mangle]
pub unsafe extern "C" fn page_map(page: *mut Page) {
    unsafe {
        page_map_body_result(page, Some(page_map_count_inc_result));
    }
}

#[no_mangle]
pub unsafe extern "C" fn page_unmap_locked_result(page: *mut Page) -> CInt {
    if page_count(page).fetch_sub(1, Ordering::SeqCst) > 1 {
        return 0;
    }

    list_del(&raw mut (*page).hash);
    1
}

#[no_mangle]
pub unsafe extern "C" fn page_insert_hash_init_result(
    page: *mut Page,
    hash_head: *mut ListHead,
    phys: CULong,
) -> CInt {
    if page.is_null() || hash_head.is_null() {
        return 0;
    }

    list_add(&raw mut (*page).hash, hash_head);
    write(&mut (*page).phys, phys);
    write(&mut (*page).mode, 0);
    init_list_head(&raw mut (*page).list);
    page_count(page).store(0, Ordering::SeqCst);
    1
}

#[no_mangle]
pub unsafe extern "C" fn page_hash_lookup_result(
    hash_head: *mut ListHead,
    phys: CULong,
) -> *mut Page {
    if hash_head.is_null() {
        return core::ptr::null_mut();
    }

    let mut pos = (*hash_head).next;
    while pos != hash_head {
        let page = (pos as usize - offset_of!(Page, hash)) as *mut Page;
        if read_volatile(&(*page).phys) == phys {
            return page;
        }
        pos = (*pos).next;
    }

    core::ptr::null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn page_hash_bucket_init_result(hash_head: *mut ListHead) -> CInt {
    if hash_head.is_null() {
        return 0;
    }

    init_list_head(hash_head);
    1
}

#[no_mangle]
pub unsafe extern "C" fn page_hash_tables_init_body_result(
    hash_heads_addr: usize,
    locks_addr: usize,
    bucket_count: CInt,
    hash_head_stride: usize,
    lock_stride: usize,
    lock_init_fn: Option<PageHashLockInitFn>,
    bucket_init_fn: Option<PageHashBucketInitFn>,
) -> CInt {
    if bucket_count < 0 {
        return -EINVAL;
    }
    let (Some(lock_init), Some(bucket_init)) = (lock_init_fn, bucket_init_fn) else {
        return -EINVAL;
    };

    let mut initialized: CInt = 0;
    for index in 0..bucket_count as usize {
        let (Some(hash_head_addr), Some(lock_addr)) = (
            addr_at(hash_heads_addr, hash_head_stride, index),
            addr_at(locks_addr, lock_stride, index),
        ) else {
            return -EINVAL;
        };

        unsafe {
            lock_init(lock_addr);
            initialized += (bucket_init(hash_head_addr as *mut ListHead) != 0) as CInt;
        }
    }

    initialized
}

#[no_mangle]
pub unsafe extern "C" fn page_hash_count_bucket_result(hash_head: *mut ListHead) -> CInt {
    if hash_head.is_null() {
        return 0;
    }

    let mut count = 0;
    let mut pos = (*hash_head).next;
    while pos != hash_head {
        count += 1;
        pos = (*pos).next;
    }
    count
}

#[inline(always)]
fn page_hash_index(phys: CULong, hash_shift: CInt, hash_mask: CULong) -> Option<usize> {
    if !(0..64).contains(&hash_shift) {
        return None;
    }

    Some(((phys >> (hash_shift as u32)) & hash_mask) as usize)
}

#[inline(always)]
fn addr_at(base: usize, stride: usize, index: usize) -> Option<usize> {
    if base == 0 || stride == 0 {
        return None;
    }

    stride
        .checked_mul(index)
        .and_then(|delta| base.checked_add(delta))
}

#[no_mangle]
pub unsafe extern "C" fn page_hash_count_all_result(
    hash_heads_addr: usize,
    locks_addr: usize,
    bucket_count: CInt,
    hash_head_stride: usize,
    lock_stride: usize,
    lock_fn: Option<PageHashLockFn>,
    unlock_fn: Option<PageHashUnlockFn>,
) -> CInt {
    if bucket_count < 0 {
        return -EINVAL;
    }
    let (Some(lock_fn), Some(unlock_fn)) = (lock_fn, unlock_fn) else {
        return -EINVAL;
    };

    let mut total: CInt = 0;
    for index in 0..bucket_count as usize {
        let (Some(hash_head_addr), Some(lock_addr)) = (
            addr_at(hash_heads_addr, hash_head_stride, index),
            addr_at(locks_addr, lock_stride, index),
        ) else {
            return -EINVAL;
        };

        let flags = unsafe { lock_fn(lock_addr) };
        let count = unsafe { page_hash_count_bucket_result(hash_head_addr as *mut ListHead) };
        total = total.saturating_add(count);
        unsafe { unlock_fn(lock_addr, flags) };
    }

    total
}

#[no_mangle]
pub unsafe extern "C" fn page_hash_count_pages_body_result(
    hash_heads_addr: usize,
    locks_addr: usize,
    bucket_count: CInt,
    hash_head_stride: usize,
    lock_stride: usize,
    lock_fn: Option<PageHashLockFn>,
    unlock_fn: Option<PageHashUnlockFn>,
    count_all_fn: Option<PageHashCountAllFn>,
) -> CInt {
    let Some(count_all) = count_all_fn else {
        return -EINVAL;
    };

    count_all(
        hash_heads_addr,
        locks_addr,
        bucket_count,
        hash_head_stride,
        lock_stride,
        lock_fn,
        unlock_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn phys_to_page_lookup_orchestrate_result(
    phys: CULong,
    hash_heads_addr: usize,
    locks_addr: usize,
    hash_shift: CInt,
    hash_mask: CULong,
    hash_head_stride: usize,
    lock_stride: usize,
    lock_fn: Option<PageHashLockFn>,
    unlock_fn: Option<PageHashUnlockFn>,
) -> *mut Page {
    let (Some(lock_fn), Some(unlock_fn), Some(index)) = (
        lock_fn,
        unlock_fn,
        page_hash_index(phys, hash_shift, hash_mask),
    ) else {
        return core::ptr::null_mut();
    };
    let (Some(hash_head_addr), Some(lock_addr)) = (
        addr_at(hash_heads_addr, hash_head_stride, index),
        addr_at(locks_addr, lock_stride, index),
    ) else {
        return core::ptr::null_mut();
    };

    let flags = unsafe { lock_fn(lock_addr) };
    let page = unsafe { page_hash_lookup_result(hash_head_addr as *mut ListHead, phys) };
    unsafe { unlock_fn(lock_addr, flags) };
    page
}

#[no_mangle]
pub unsafe extern "C" fn phys_to_page_insert_hash_orchestrate_result(
    phys: CULong,
    hash_heads_addr: usize,
    locks_addr: usize,
    hash_shift: CInt,
    hash_mask: CULong,
    hash_head_stride: usize,
    lock_stride: usize,
    page_size: usize,
    alloc_flag: CInt,
    lock_fn: Option<PageHashLockFn>,
    unlock_fn: Option<PageHashUnlockFn>,
    alloc_fn: Option<PageHashAllocFn>,
) -> *mut Page {
    let (Some(lock_fn), Some(unlock_fn), Some(alloc_fn), Some(index)) = (
        lock_fn,
        unlock_fn,
        alloc_fn,
        page_hash_index(phys, hash_shift, hash_mask),
    ) else {
        return core::ptr::null_mut();
    };
    let (Some(hash_head_addr), Some(lock_addr)) = (
        addr_at(hash_heads_addr, hash_head_stride, index),
        addr_at(locks_addr, lock_stride, index),
    ) else {
        return core::ptr::null_mut();
    };

    let hash_head = hash_head_addr as *mut ListHead;
    let flags = unsafe { lock_fn(lock_addr) };
    let mut page = unsafe { page_hash_lookup_result(hash_head, phys) };
    if page.is_null() {
        page = unsafe { alloc_fn(page_size, alloc_flag) };
        if !page.is_null() {
            unsafe {
                page_insert_hash_init_result(page, hash_head, phys);
            }
        }
    }
    unsafe { unlock_fn(lock_addr, flags) };
    page
}

#[no_mangle]
pub unsafe extern "C" fn phys_to_page_lookup_body_result(
    phys: CULong,
    hash_heads_addr: usize,
    locks_addr: usize,
    hash_shift: CInt,
    hash_mask: CULong,
    hash_head_stride: usize,
    lock_stride: usize,
    lock_fn: Option<PageHashLockFn>,
    unlock_fn: Option<PageHashUnlockFn>,
    lookup_fn: Option<PhysToPageLookupOrchestrateFn>,
) -> *mut Page {
    let Some(lookup) = lookup_fn else {
        return core::ptr::null_mut();
    };

    lookup(
        phys,
        hash_heads_addr,
        locks_addr,
        hash_shift,
        hash_mask,
        hash_head_stride,
        lock_stride,
        lock_fn,
        unlock_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn phys_to_page_insert_hash_body_result(
    phys: CULong,
    hash_heads_addr: usize,
    locks_addr: usize,
    hash_shift: CInt,
    hash_mask: CULong,
    hash_head_stride: usize,
    lock_stride: usize,
    page_size: usize,
    alloc_flag: CInt,
    lock_fn: Option<PageHashLockFn>,
    unlock_fn: Option<PageHashUnlockFn>,
    alloc_fn: Option<PageHashAllocFn>,
    insert_fn: Option<PhysToPageInsertOrchestrateFn>,
    log_fn: Option<PhysToPageInsertLogFn>,
) -> *mut Page {
    let Some(insert) = insert_fn else {
        return core::ptr::null_mut();
    };

    let page = insert(
        phys,
        hash_heads_addr,
        locks_addr,
        hash_shift,
        hash_mask,
        hash_head_stride,
        lock_stride,
        page_size,
        alloc_flag,
        lock_fn,
        unlock_fn,
        alloc_fn,
    );
    if page.is_null() {
        if let Some(log) = log_fn {
            log(phys);
        }
    }

    page
}

#[no_mangle]
pub unsafe extern "C" fn page_unmap_orchestrate_result(
    page: *mut Page,
    locks_addr: usize,
    hash_shift: CInt,
    hash_mask: CULong,
    lock_stride: usize,
    lock_fn: Option<PageHashLockFn>,
    unlock_fn: Option<PageHashUnlockFn>,
) -> CInt {
    if page.is_null() {
        return 0;
    }
    let phys = unsafe { read_volatile(&(*page).phys) };
    let (Some(lock_fn), Some(unlock_fn), Some(index)) = (
        lock_fn,
        unlock_fn,
        page_hash_index(phys, hash_shift, hash_mask),
    ) else {
        return 0;
    };
    let Some(lock_addr) = addr_at(locks_addr, lock_stride, index) else {
        return 0;
    };

    let flags = unsafe { lock_fn(lock_addr) };
    let unmapped = unsafe { page_unmap_locked_result(page) };
    unsafe { unlock_fn(lock_addr, flags) };
    unmapped
}

#[no_mangle]
pub unsafe extern "C" fn page_unmap_body_result(
    page: *mut Page,
    locks_addr: usize,
    hash_shift: CInt,
    hash_mask: CULong,
    lock_stride: usize,
    lock_fn: Option<PageHashLockFn>,
    unlock_fn: Option<PageHashUnlockFn>,
    orchestrate_fn: Option<PageUnmapOrchestrateFn>,
    log_fn: Option<PageUnmapLogFn>,
) -> CInt {
    if page.is_null() {
        return 0;
    }
    let Some(orchestrate) = orchestrate_fn else {
        return 0;
    };

    if let Some(log) = log_fn {
        log(PAGE_UNMAP_LOG_ENTER, page, 0);
    }

    let ret = orchestrate(
        page,
        locks_addr,
        hash_shift,
        hash_mask,
        lock_stride,
        lock_fn,
        unlock_fn,
    );
    if ret == 0 {
        if let Some(log) = log_fn {
            log(PAGE_UNMAP_LOG_STILL_MAPPED, page, ret);
        }
        return 0;
    }

    if let Some(log) = log_fn {
        log(PAGE_UNMAP_LOG_UNMAPPED, page, ret);
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn is_splitable(page: *mut Page, memobj_flags: u32) -> CInt {
    if !page.is_null() && (page_in_memobj_predicate(page) || page_multi_mapped_predicate(page)) {
        if (memobj_flags & MF_SHM) != 0 {
            return 1;
        }
        return 0;
    }

    1
}
