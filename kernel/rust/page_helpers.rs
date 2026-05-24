use core::mem::{align_of, offset_of, size_of};
use core::ptr::{read_volatile, write};
use core::sync::atomic::{AtomicI32, Ordering};

use crate::abi::{CInt, CULong, OffT};

type PageHashLockFn = unsafe extern "C" fn(usize) -> CULong;
type PageHashUnlockFn = unsafe extern "C" fn(usize, CULong);
type PageHashAllocFn = unsafe extern "C" fn(usize, CInt) -> *mut Page;

const MF_SHM: u32 = 0x40000;
const EINVAL: CInt = 22;
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
unsafe fn page_is_in_memobj(page: *const Page) -> bool {
    page_mode_in_memobj_result(read_volatile(&(*page).mode) as CInt) != 0
}

#[inline(always)]
unsafe fn page_is_multi_mapped(page: *const Page) -> bool {
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
pub unsafe extern "C" fn is_splitable(page: *mut Page, memobj_flags: u32) -> CInt {
    if !page.is_null() && (page_is_in_memobj(page) || page_is_multi_mapped(page)) {
        if (memobj_flags & MF_SHM) != 0 {
            return 1;
        }
        return 0;
    }

    1
}
