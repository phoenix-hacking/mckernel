use crate::abi::{AbiListHead,CInt,CULong,IhkAtomic,IhkSpinlock};use crate::string::{strlen,strcmp,strcpy};
use core::ffi::c_void;use core::ptr::null_mut;use core::mem::{size_of,offset_of};use core::sync::atomic::{AtomicI32,Ordering};
const IHK_MC_AP_NOWAIT:CULong=2;
const PAGEALLOC_TRACK_HASH_MASK: CInt = 255;
const PAGEALLOC_TRACK_HASH_SIZE: usize = (PAGEALLOC_TRACK_HASH_MASK as usize) + 1;
const PAGEALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED: CInt = 1;
const PAGEALLOC_TRACK_LOG_FILE_ALLOC_FAILED: CInt = 2;
const PAGEALLOC_TRACK_LOG_ENTRY_ADDED: CInt = 3;
const PAGEALLOC_TRACK_LOG_ADDR_ALLOC_FAILED: CInt = 4;
const PAGEALLOC_TRACK_LOG_ADDR_ADDED: CInt = 5;
const PAGEALLOC_TRACK_LOG_ADDR_REMOVED: CInt = 6;
const PAGEALLOC_TRACK_LOG_ENTRY_REMOVED: CInt = 7;
const PAGEALLOC_TRACK_LOG_COVERING_FOUND: CInt = 8;
const PAGEALLOC_TRACK_LOG_ADDR_NEXT_ADDED: CInt = 9;
const PAGEALLOC_TRACK_LOG_ADDR_MODIFIED: CInt = 10;
type MemPageallocBaseAllocFn =
    unsafe extern "C" fn(CInt, CInt, CULong, CInt, CInt, CULong) -> *mut c_void;
type MemPageallocBaseFreeFn = unsafe extern "C" fn(*mut c_void, CInt, CInt);
type MemPageallocMetaAllocFn = unsafe extern "C" fn(CInt, CULong) -> *mut c_void;
type MemPageallocMetaFreeFn = unsafe extern "C" fn(*mut c_void);
type MemPageallocSpinInitFn = unsafe extern "C" fn(CULong);
type MemPageallocTrackLogFn = unsafe extern "C" fn(CInt, *mut c_void, *mut i8, CInt, CInt);
type MemKmallocSpinLockFn=unsafe extern "C" fn(CULong)->CULong;
type MemKmallocSpinUnlockFn=unsafe extern "C" fn(CULong,CULong);
extern "C" {
    fn mem_pagealloc_track_base_alloc_bridge(
        npages: CInt,
        p2align: CInt,
        flag: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
    ) -> *mut c_void;
    fn mem_pagealloc_track_meta_alloc_bridge(size: CInt, flag: CULong) -> *mut c_void;
    fn mem_pagealloc_track_meta_free_bridge(ptr: *mut c_void);
    fn mem_pagealloc_track_lock_bridge(lock_addr: CULong) -> CULong;
    fn mem_pagealloc_track_unlock_bridge(lock_addr: CULong, irqflags: CULong);
    fn mem_pagealloc_track_spin_init_bridge(lock_addr: CULong);
    fn mem_pagealloc_track_log_bridge(
        event: CInt,
        ptr: *mut c_void,
        file: *mut i8,
        line: CInt,
        npages: CInt,
    );
    #[link_name = "memdebug"]
    static mut MEMDEBUG: *mut i8;
    #[link_name = "pagealloc_track_hash"]
    static mut PAGEALLOC_TRACK_HASH: [AbiListHead; PAGEALLOC_TRACK_HASH_SIZE];
    #[link_name = "pagealloc_track_hash_locks"]
    static mut PAGEALLOC_TRACK_HASH_LOCKS: [IhkSpinlock; PAGEALLOC_TRACK_HASH_SIZE];
    #[link_name = "pagealloc_addr_hash"]
    static mut PAGEALLOC_ADDR_HASH: [AbiListHead; PAGEALLOC_TRACK_HASH_SIZE];
    #[link_name = "pagealloc_addr_hash_locks"]
    static mut PAGEALLOC_ADDR_HASH_LOCKS: [IhkSpinlock; PAGEALLOC_TRACK_HASH_SIZE];
    #[link_name = "pagealloc_track_initialized"]
    static mut PAGEALLOC_TRACK_INITIALIZED: CInt;
    #[link_name = "pagealloc_runcount"]
    static mut PAGEALLOC_RUNCOUNT: CInt;
}
#[repr(C)]
pub struct PageallocTrackAddrEntry {
    addr: *mut c_void,
    runcount: CInt,
    list: AbiListHead,
    entry: *mut PageallocTrackEntry,
    hash: AbiListHead,
    npages: CInt,
}
#[repr(C)]
pub struct PageallocTrackEntry {
    file: *mut i8,
    line: CInt,
    alloc_count: IhkAtomic,
    hash: AbiListHead,
    addr_list: AbiListHead,
    addr_list_lock: IhkSpinlock,
}
#[inline(always)]
unsafe fn list_add(new: *mut AbiListHead, prev: *mut AbiListHead, next: *mut AbiListHead) {
    (*next).prev = new;
    (*new).next = next;
    (*new).prev = prev;
    (*prev).next = new;
}
#[inline(always)]
unsafe fn list_add_after(new: *mut AbiListHead, head: *mut AbiListHead) {
    list_add(new, head, (*head).next);
}
#[inline(always)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}
#[inline(always)]
unsafe fn pagealloc_track_hash(file: *mut i8, line: CInt) -> CInt {
    let len = if file.is_null() {
        0
    } else {
        strlen(file.cast_const()) as CInt
    };
    len.wrapping_add(line) & PAGEALLOC_TRACK_HASH_MASK
}
#[inline(always)]
unsafe fn pagealloc_addr_hash(ptr: *mut c_void) -> CInt {
    ((ptr as CULong) >> 5 & PAGEALLOC_TRACK_HASH_MASK as CULong) as CInt
}
#[inline(always)]
unsafe fn pagealloc_track_entry_alloc_count(entry: *mut PageallocTrackEntry) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*entry).alloc_count.counter)
}
#[inline(always)]
unsafe fn pagealloc_track_entry_from_hash(node: *mut AbiListHead) -> *mut PageallocTrackEntry {
    node.cast::<u8>()
        .sub(offset_of!(PageallocTrackEntry, hash))
        .cast::<PageallocTrackEntry>()
}
#[inline(always)]
unsafe fn pagealloc_track_log(
    log_fn: Option<MemPageallocTrackLogFn>,
    event: CInt,
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    npages: CInt,
) {
    if let Some(log) = log_fn {
        log(event, ptr, file, line, npages);
    }
}
#[inline(always)]
unsafe fn pagealloc_entry_addr_list_lock(entry: *mut PageallocTrackEntry) -> CULong {
    (&raw mut (*entry).addr_list_lock) as CULong
}
#[inline(always)]
unsafe fn pagealloc_rehash_addr_entry(
    addr_entry: *mut PageallocTrackAddrEntry,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    lock: MemKmallocSpinLockFn,
    unlock: MemKmallocSpinUnlockFn,
) {
    let addr_hash_index = pagealloc_addr_hash((*addr_entry).addr);
    let addr_lock = addr_locks.add(addr_hash_index as usize);
    let irq_flags = lock(addr_lock as CULong);
    list_add_after(
        &raw mut (*addr_entry).hash,
        addr_hash.add(addr_hash_index as usize),
    );
    unlock(addr_lock as CULong, irq_flags);
}
#[no_mangle]
pub unsafe extern "C" fn pagealloc_track_find_entry_result(
    file: *mut i8,
    line: CInt,
    track_hash: *mut AbiListHead,
) -> *mut PageallocTrackEntry {
    if file.is_null() || track_hash.is_null() {
        return null_mut();
    }

    let hash = pagealloc_track_hash(file, line);
    let head = track_hash.add(hash as usize);
    let mut node = (*head).next;

    while node != head {
        let entry = pagealloc_track_entry_from_hash(node);
        if (*entry).line == line && strcmp((*entry).file, file) == 0 {
            return entry;
        }
        node = (*node).next;
    }

    null_mut()
}
#[no_mangle]
pub unsafe extern "C" fn pagealloc_track_alloc_result(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
    is_user: CInt,
    virt_addr: CULong,
    file: *mut i8,
    line: CInt,
    memdebug: *mut i8,
    track_initialized: CInt,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    runcount: CInt,
    base_alloc_fn: Option<MemPageallocBaseAllocFn>,
    meta_alloc_fn: Option<MemPageallocMetaAllocFn>,
    meta_free_fn: Option<MemPageallocMetaFreeFn>,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    spin_init_fn: Option<MemPageallocSpinInitFn>,
    log_fn: Option<MemPageallocTrackLogFn>,
) -> *mut c_void {
    let Some(base_alloc) = base_alloc_fn else {
        return null_mut();
    };

    let result = base_alloc(npages, p2align, flag, node, is_user, virt_addr);
    if memdebug.is_null() || track_initialized == 0 || result.is_null() {
        return result;
    }
    if file.is_null()
        || track_hash.is_null()
        || track_locks.is_null()
        || addr_hash.is_null()
        || addr_locks.is_null()
    {
        return result;
    }
    let (Some(meta_alloc), Some(meta_free), Some(lock), Some(unlock), Some(spin_init)) = (
        meta_alloc_fn,
        meta_free_fn,
        lock_fn,
        unlock_fn,
        spin_init_fn,
    ) else {
        return result;
    };

    let hash = pagealloc_track_hash(file, line);
    let track_lock = track_locks.add(hash as usize);
    let irq_flags = lock(track_lock as CULong);
    let mut entry = pagealloc_track_find_entry_result(file, line, track_hash);

    if entry.is_null() {
        entry = meta_alloc(size_of::<PageallocTrackEntry>() as CInt, IHK_MC_AP_NOWAIT)
            .cast::<PageallocTrackEntry>();
        if entry.is_null() {
            unlock(track_lock as CULong, irq_flags);
            pagealloc_track_log(
                log_fn,
                PAGEALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED,
                result,
                file,
                line,
                npages,
            );
            return result;
        }

        (*entry).line = line;
        pagealloc_track_entry_alloc_count(entry).store(1, Ordering::Relaxed);
        spin_init(pagealloc_entry_addr_list_lock(entry));
        init_list_head(&raw mut (*entry).addr_list);

        let file_len = strlen(file.cast_const()) as CInt;
        (*entry).file = meta_alloc(file_len.wrapping_add(1), IHK_MC_AP_NOWAIT).cast::<i8>();
        if (*entry).file.is_null() {
            pagealloc_track_log(
                log_fn,
                PAGEALLOC_TRACK_LOG_FILE_ALLOC_FAILED,
                result,
                file,
                line,
                npages,
            );
            meta_free(entry.cast::<c_void>());
            unlock(track_lock as CULong, irq_flags);
            return result;
        }

        strcpy((*entry).file, file.cast_const());
        init_list_head(&raw mut (*entry).hash);
        list_add_after(&raw mut (*entry).hash, track_hash.add(hash as usize));
        pagealloc_track_log(
            log_fn,
            PAGEALLOC_TRACK_LOG_ENTRY_ADDED,
            result,
            file,
            line,
            npages,
        );
    } else {
        pagealloc_track_entry_alloc_count(entry).fetch_add(1, Ordering::Relaxed);
    }
    unlock(track_lock as CULong, irq_flags);

    let addr_entry = meta_alloc(
        size_of::<PageallocTrackAddrEntry>() as CInt,
        IHK_MC_AP_NOWAIT,
    )
    .cast::<PageallocTrackAddrEntry>();
    if addr_entry.is_null() {
        pagealloc_track_log(
            log_fn,
            PAGEALLOC_TRACK_LOG_ADDR_ALLOC_FAILED,
            result,
            file,
            line,
            npages,
        );
        return result;
    }

    (*addr_entry).addr = result;
    (*addr_entry).runcount = runcount;
    (*addr_entry).entry = entry;
    (*addr_entry).npages = npages;
    init_list_head(&raw mut (*addr_entry).list);
    init_list_head(&raw mut (*addr_entry).hash);

    let irq_flags = lock(pagealloc_entry_addr_list_lock(entry));
    list_add_after(&raw mut (*addr_entry).list, &raw mut (*entry).addr_list);
    unlock(pagealloc_entry_addr_list_lock(entry), irq_flags);

    pagealloc_rehash_addr_entry(addr_entry, addr_hash, addr_locks, lock, unlock);
    pagealloc_track_log(
        log_fn,
        PAGEALLOC_TRACK_LOG_ADDR_ADDED,
        result,
        file,
        line,
        npages,
    );

    result
}
#[inline(always)]
unsafe fn pagealloc_track_hash_ptr() -> *mut AbiListHead {
    (&raw mut PAGEALLOC_TRACK_HASH).cast::<AbiListHead>()
}
#[inline(always)]
unsafe fn pagealloc_track_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut PAGEALLOC_TRACK_HASH_LOCKS).cast::<IhkSpinlock>()
}
#[inline(always)]
unsafe fn pagealloc_addr_hash_ptr() -> *mut AbiListHead {
    (&raw mut PAGEALLOC_ADDR_HASH).cast::<AbiListHead>()
}
#[inline(always)]
unsafe fn pagealloc_addr_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut PAGEALLOC_ADDR_HASH_LOCKS).cast::<IhkSpinlock>()
}
#[no_mangle]
pub unsafe extern "C" fn _ihk_mc_alloc_aligned_pages_node(
    npages: CInt,
    p2align: CInt,
    flag: CULong,
    node: CInt,
    is_user: CInt,
    virt_addr: CULong,
    file: *mut i8,
    line: CInt,
) -> *mut c_void {
    pagealloc_track_alloc_result(
        npages,
        p2align,
        flag,
        node,
        is_user,
        virt_addr,
        file,
        line,
        MEMDEBUG,
        PAGEALLOC_TRACK_INITIALIZED,
        pagealloc_track_hash_ptr(),
        pagealloc_track_locks_ptr(),
        pagealloc_addr_hash_ptr(),
        pagealloc_addr_locks_ptr(),
        PAGEALLOC_RUNCOUNT,
        Some(mem_pagealloc_track_base_alloc_bridge),
        Some(mem_pagealloc_track_meta_alloc_bridge),
        Some(mem_pagealloc_track_meta_free_bridge),
        Some(mem_pagealloc_track_lock_bridge),
        Some(mem_pagealloc_track_unlock_bridge),
        Some(mem_pagealloc_track_spin_init_bridge),
        Some(mem_pagealloc_track_log_bridge),
    )
}
