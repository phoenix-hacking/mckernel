use core::ffi::c_void;
use core::mem::{size_of,offset_of};
use core::ptr::null_mut;
use core::sync::atomic::{AtomicI32,Ordering};
use crate::abi::{AbiListHead,CInt,CULong,CpuLocalVar,IhkAtomic,IhkSpinlock,KmallocHeader,SizeT};
use crate::string::{strcmp,strcpy,strlen};
type MemKmallocIrqSaveFn = unsafe extern "C" fn() -> CULong;
type MemKmallocIrqRestoreFn = unsafe extern "C" fn(CULong);
type MemKmallocAllocPagesFn = unsafe extern "C" fn(CInt, CULong, CInt) -> *mut c_void;
type MemKmallocGetCpuLocalVarFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type MemKmallocSpinLockFn = unsafe extern "C" fn(CULong) -> CULong;
type MemKmallocSpinUnlockFn = unsafe extern "C" fn(CULong, CULong);
type MemKmallocCorruptionFn = unsafe extern "C" fn(*mut c_void);
type MemKmallocBaseAllocFn = unsafe extern "C" fn(CInt, CULong) -> *mut c_void;
type MemKmallocBaseFreeFn = unsafe extern "C" fn(*mut c_void);
type MemKmallocSpinInitFn = unsafe extern "C" fn(CULong);
type MemKmallocTrackLogFn = unsafe extern "C" fn(CInt, *mut c_void, *mut i8, CInt, CInt);
type MemKmallocInvalidFreeFn = unsafe extern "C" fn(*mut c_void, *mut i8, CInt);
#[repr(C)]
pub struct KmallocTrackAddrEntry {
    addr: *mut c_void,
    runcount: CInt,
    list: AbiListHead,
    entry: *mut KmallocTrackEntry,
    hash: AbiListHead,
}

#[repr(C)]
pub struct KmallocTrackEntry {
    file: *mut i8,
    line: CInt,
    size: CInt,
    alloc_count: IhkAtomic,
    hash: AbiListHead,
    addr_list: AbiListHead,
    addr_list_lock: IhkSpinlock,
}

unsafe extern "C" {
fn ihk_mc_get_processor_id()->CInt;
fn get_this_cpu_local_var()->*mut CpuLocalVar;
fn kprintf(format:*const i8,...)->CInt;
fn mem_kmalloc_track_base_alloc_bridge(size:CInt,flag:CULong)->*mut c_void;
fn mem_kmalloc_track_base_free_bridge(ptr:*mut c_void);
fn mem_kmalloc_track_lock_bridge(lock:CULong)->CULong;
fn mem_kmalloc_track_unlock_bridge(lock:CULong,flags:CULong);
fn mem_kmalloc_track_spin_init_bridge(lock:CULong);
fn mem_kmalloc_track_log_bridge(event:CInt,ptr:*mut c_void,file:*mut i8,line:CInt,size:CInt);
fn mem_kmalloc_invalid_free_bridge(ptr:*mut c_void,file:*mut i8,line:CInt);
#[link_name="memdebug"] static mut MEMDEBUG:*mut i8;
#[link_name="kmalloc_track_hash"] static mut KMALLOC_TRACK_HASH:[AbiListHead;256];
#[link_name="kmalloc_track_hash_locks"] static mut KMALLOC_TRACK_HASH_LOCKS:[IhkSpinlock;256];
#[link_name="kmalloc_addr_hash"] static mut KMALLOC_ADDR_HASH:[AbiListHead;256];
#[link_name="kmalloc_addr_hash_locks"] static mut KMALLOC_ADDR_HASH_LOCKS:[IhkSpinlock;256];
#[link_name="kmalloc_runcount"] static mut KMALLOC_RUNCOUNT:CInt;
}
const KMALLOC_FRONT_MAGIC: u32 = 0x5c5c5c5c;
const KMALLOC_END_MAGIC: u32 = 0x6d6d6d6d;
const KMALLOC_MIN_SIZE: CInt = 1 << 5;
const KMALLOC_MIN_MASK: CInt = KMALLOC_MIN_SIZE - 1;
const EINVAL: CInt = 22;
const PAGE_SHIFT: CULong = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const IHK_MC_PG_KERNEL: CInt = 0;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const KMALLOC_OOM_FMT: &[u8] = b"kmalloc: out of memory %s:%d no_preempt=%d\n\0";
const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;
const KMALLOC_TRACK_HASH_MASK: CInt = 255;
const KMALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED: CInt = 1;
const KMALLOC_TRACK_LOG_FILE_ALLOC_FAILED: CInt = 2;
const KMALLOC_TRACK_LOG_ENTRY_ADDED: CInt = 3;
const KMALLOC_TRACK_LOG_ADDR_ALLOC_FAILED: CInt = 4;
const KMALLOC_TRACK_LOG_ADDR_ADDED: CInt = 5;
const KMALLOC_TRACK_LOG_ADDR_REMOVED: CInt = 6;
const KMALLOC_TRACK_LOG_ENTRY_REMOVED: CInt = 7;
const _: () = {
    assert!(size_of::<IhkMcPaOps>() == 32);
#[inline(always)]
unsafe fn kmalloc_list(chunk: *mut KmallocHeader) -> *mut AbiListHead {
    (&raw mut (*chunk).link.list).cast::<AbiListHead>()
}

#[inline(always)]
unsafe fn list_to_kmalloc_header(node: *mut AbiListHead) -> *mut KmallocHeader {
    node.cast::<u8>()
        .sub(offset_of!(KmallocHeader, link))
        .cast::<KmallocHeader>()
}

#[inline(always)]
unsafe fn list_add(new: *mut AbiListHead, prev: *mut AbiListHead, next: *mut AbiListHead) {
    (*next).prev = new;
    (*new).next = next;
    (*new).prev = prev;
    (*prev).next = new;
}

#[inline(always)]
unsafe fn list_add_tail(new: *mut AbiListHead, head: *mut AbiListHead) {
    list_add(new, (*head).prev, head);
}

#[inline(always)]
unsafe fn list_add_after(new: *mut AbiListHead, head: *mut AbiListHead) {
    list_add(new, head, (*head).next);
}

#[inline(always)]
unsafe fn list_del(entry: *mut AbiListHead) {
    let next = (*entry).next;
    let prev = (*entry).prev;
    (*next).prev = prev;
    (*prev).next = next;
}

#[inline(always)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[inline(always)]
unsafe fn list_del_poison(entry: *mut AbiListHead) {
    list_del(entry);
    (*entry).next = LIST_POISON1 as *mut AbiListHead;
    (*entry).prev = LIST_POISON2 as *mut AbiListHead;
}

#[inline(always)]
unsafe fn kmalloc_track_hash(size: CInt, file: *mut i8, line: CInt) -> CInt {
    let len = if file.is_null() {
        0
    } else {
        strlen(file.cast_const()) as CInt
    };
    len.wrapping_add(line).wrapping_add(size) & KMALLOC_TRACK_HASH_MASK
}

#[inline(always)]
unsafe fn kmalloc_addr_hash(ptr: *mut c_void) -> CInt {
    ((ptr as CULong) >> 5 & KMALLOC_TRACK_HASH_MASK as CULong) as CInt
}

#[inline(always)]
unsafe fn kmalloc_track_entry_alloc_count(entry: *mut KmallocTrackEntry) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*entry).alloc_count.counter)
}

#[inline(always)]
unsafe fn kmalloc_track_entry_from_hash(node: *mut AbiListHead) -> *mut KmallocTrackEntry {
    node.cast::<u8>()
        .sub(offset_of!(KmallocTrackEntry, hash))
        .cast::<KmallocTrackEntry>()
}

#[inline(always)]
unsafe fn kmalloc_track_addr_from_hash(node: *mut AbiListHead) -> *mut KmallocTrackAddrEntry {
    node.cast::<u8>()
        .sub(offset_of!(KmallocTrackAddrEntry, hash))
        .cast::<KmallocTrackAddrEntry>()
}

#[inline(always)]
unsafe fn kmalloc_track_log(
    log_fn: Option<MemKmallocTrackLogFn>,
    event: CInt,
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    size: CInt,
) {
    if let Some(log) = log_fn {
        log(event, ptr, file, line, size);
    }
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_track_find_entry_result(
    size: CInt,
    file: *mut i8,
    line: CInt,
    track_hash: *mut AbiListHead,
) -> *mut KmallocTrackEntry {
    if file.is_null() || track_hash.is_null() {
        return null_mut();
    }

    let hash = kmalloc_track_hash(size, file, line);
    let head = track_hash.add(hash as usize);
    let mut node = (*head).next;

    while node != head {
        let entry = kmalloc_track_entry_from_hash(node);
        if (*entry).size == size && (*entry).line == line && strcmp((*entry).file, file) == 0 {
            return entry;
        }
        node = (*node).next;
    }

    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_track_alloc_result(
    size: CInt,
    flag: CULong,
    file: *mut i8,
    line: CInt,
    memdebug: *mut i8,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    runcount: CInt,
    base_alloc_fn: Option<MemKmallocBaseAllocFn>,
    base_free_fn: Option<MemKmallocBaseFreeFn>,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    spin_init_fn: Option<MemKmallocSpinInitFn>,
    log_fn: Option<MemKmallocTrackLogFn>,
) -> *mut c_void {
    let Some(base_alloc) = base_alloc_fn else {
        return null_mut();
    };

    let result = base_alloc(size, flag);
    if memdebug.is_null() || result.is_null() {
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
    let (Some(base_free), Some(lock), Some(unlock), Some(spin_init)) =
        (base_free_fn, lock_fn, unlock_fn, spin_init_fn)
    else {
        return result;
    };

    let hash = kmalloc_track_hash(size, file, line);
    let track_lock = track_locks.add(hash as usize);
    let irq_flags = lock(track_lock as CULong);
    let mut entry = kmalloc_track_find_entry_result(size, file, line, track_hash);

    if entry.is_null() {
        entry = base_alloc(size_of::<KmallocTrackEntry>() as CInt, IHK_MC_AP_NOWAIT)
            .cast::<KmallocTrackEntry>();
        if entry.is_null() {
            unlock(track_lock as CULong, irq_flags);
            kmalloc_track_log(
                log_fn,
                KMALLOC_TRACK_LOG_ENTRY_ALLOC_FAILED,
                result,
                file,
                line,
                size,
            );
            return result;
        }

        (*entry).line = line;
        (*entry).size = size;
        kmalloc_track_entry_alloc_count(entry).store(1, Ordering::Relaxed);
        spin_init((&raw mut (*entry).addr_list_lock) as CULong);
        init_list_head(&raw mut (*entry).addr_list);

        let file_len = strlen(file.cast_const()) as CInt;
        (*entry).file = base_alloc(file_len.wrapping_add(1), IHK_MC_AP_NOWAIT).cast::<i8>();
        if (*entry).file.is_null() {
            kmalloc_track_log(
                log_fn,
                KMALLOC_TRACK_LOG_FILE_ALLOC_FAILED,
                result,
                file,
                line,
                size,
            );
            base_free(entry.cast::<c_void>());
            unlock(track_lock as CULong, irq_flags);
            return result;
        }

        strcpy((*entry).file, file.cast_const());
        init_list_head(&raw mut (*entry).hash);
        list_add_after(&raw mut (*entry).hash, track_hash.add(hash as usize));
        kmalloc_track_log(
            log_fn,
            KMALLOC_TRACK_LOG_ENTRY_ADDED,
            result,
            file,
            line,
            size,
        );
    } else {
        kmalloc_track_entry_alloc_count(entry).fetch_add(1, Ordering::Relaxed);
    }
    unlock(track_lock as CULong, irq_flags);

    let addr_entry = base_alloc(size_of::<KmallocTrackAddrEntry>() as CInt, IHK_MC_AP_NOWAIT)
        .cast::<KmallocTrackAddrEntry>();
    if addr_entry.is_null() {
        kmalloc_track_log(
            log_fn,
            KMALLOC_TRACK_LOG_ADDR_ALLOC_FAILED,
            result,
            file,
            line,
            size,
        );
        return result;
    }

    (*addr_entry).addr = result;
    (*addr_entry).runcount = runcount;
    (*addr_entry).entry = entry;
    init_list_head(&raw mut (*addr_entry).list);
    init_list_head(&raw mut (*addr_entry).hash);

    let irq_flags = lock((&raw mut (*entry).addr_list_lock) as CULong);
    list_add_after(&raw mut (*addr_entry).list, &raw mut (*entry).addr_list);
    unlock((&raw mut (*entry).addr_list_lock) as CULong, irq_flags);

    let addr_hash_index = kmalloc_addr_hash(result);
    let addr_lock = addr_locks.add(addr_hash_index as usize);
    let irq_flags = lock(addr_lock as CULong);
    list_add_after(
        &raw mut (*addr_entry).hash,
        addr_hash.add(addr_hash_index as usize),
    );
    unlock(addr_lock as CULong, irq_flags);
    kmalloc_track_log(
        log_fn,
        KMALLOC_TRACK_LOG_ADDR_ADDED,
        result,
        file,
        line,
        size,
    );

    result
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_track_free_result(
    ptr: *mut c_void,
    file: *mut i8,
    line: CInt,
    memdebug: *mut i8,
    track_hash: *mut AbiListHead,
    track_locks: *mut IhkSpinlock,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    base_free_fn: Option<MemKmallocBaseFreeFn>,
    lock_fn: Option<MemKmallocSpinLockFn>,
    unlock_fn: Option<MemKmallocSpinUnlockFn>,
    invalid_free_fn: Option<MemKmallocInvalidFreeFn>,
    log_fn: Option<MemKmallocTrackLogFn>,
) -> CInt {
    if ptr.is_null() {
        return 0;
    }
    let Some(base_free) = base_free_fn else {
        return -EINVAL;
    };
    if memdebug.is_null() {
        base_free(ptr);
        return 0;
    }
    if addr_hash.is_null() || addr_locks.is_null() || track_hash.is_null() || track_locks.is_null()
    {
        return -EINVAL;
    }
    let (Some(lock), Some(unlock)) = (lock_fn, unlock_fn) else {
        return -EINVAL;
    };

    let addr_hash_index = kmalloc_addr_hash(ptr);
    let addr_lock = addr_locks.add(addr_hash_index as usize);
    let irq_flags = lock(addr_lock as CULong);
    let head = addr_hash.add(addr_hash_index as usize);
    let mut node = (*head).next;
    let mut addr_entry: *mut KmallocTrackAddrEntry = null_mut();

    while node != head {
        let candidate = kmalloc_track_addr_from_hash(node);
        if (*candidate).addr == ptr {
            addr_entry = candidate;
            break;
        }
        node = (*node).next;
    }

    if !addr_entry.is_null() {
        list_del(&raw mut (*addr_entry).hash);
    }
    unlock(addr_lock as CULong, irq_flags);

    if addr_entry.is_null() {
        if let Some(invalid_free) = invalid_free_fn {
            invalid_free(ptr, file, line);
        }
        return -EINVAL;
    }

    let entry = (*addr_entry).entry;
    let irq_flags = lock((&raw mut (*entry).addr_list_lock) as CULong);
    list_del(&raw mut (*addr_entry).list);
    unlock((&raw mut (*entry).addr_list_lock) as CULong, irq_flags);
    kmalloc_track_log(
        log_fn,
        KMALLOC_TRACK_LOG_ADDR_REMOVED,
        ptr,
        (*entry).file,
        (*entry).line,
        (*entry).size,
    );
    base_free(addr_entry.cast::<c_void>());

    let hash = kmalloc_track_hash((*entry).size, (*entry).file, (*entry).line);
    let track_lock = track_locks.add(hash as usize);
    let irq_flags = lock(track_lock as CULong);
    let old_count = kmalloc_track_entry_alloc_count(entry).fetch_sub(1, Ordering::Relaxed);
    if old_count != 1 {
        unlock(track_lock as CULong, irq_flags);
        base_free(ptr);
        return 0;
    }

    list_del(&raw mut (*entry).hash);
    unlock(track_lock as CULong, irq_flags);
    kmalloc_track_log(
        log_fn,
        KMALLOC_TRACK_LOG_ENTRY_REMOVED,
        ptr,
        (*entry).file,
        (*entry).line,
        (*entry).size,
    );
    base_free((*entry).file.cast::<c_void>());
    base_free(entry.cast::<c_void>());
    base_free(ptr);
    0
}

#[inline(always)]
unsafe fn kmalloc_track_hash_ptr() -> *mut AbiListHead {
    (&raw mut KMALLOC_TRACK_HASH).cast::<AbiListHead>()
}

#[inline(always)]
unsafe fn kmalloc_track_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut KMALLOC_TRACK_HASH_LOCKS).cast::<IhkSpinlock>()
}

#[inline(always)]
unsafe fn kmalloc_addr_hash_ptr() -> *mut AbiListHead {
    (&raw mut KMALLOC_ADDR_HASH).cast::<AbiListHead>()
}

#[inline(always)]
unsafe fn kmalloc_addr_locks_ptr() -> *mut IhkSpinlock {
    (&raw mut KMALLOC_ADDR_HASH_LOCKS).cast::<IhkSpinlock>()
}

#[no_mangle]
pub unsafe extern "C" fn _kmalloc(
    size: CInt,
    flag: CULong,
    file: *mut i8,
    line: CInt,
) -> *mut c_void {
    kmalloc_track_alloc_result(
        size,
        flag,
        file,
        line,
        MEMDEBUG,
        kmalloc_track_hash_ptr(),
        kmalloc_track_locks_ptr(),
        kmalloc_addr_hash_ptr(),
        kmalloc_addr_locks_ptr(),
        KMALLOC_RUNCOUNT,
        Some(mem_kmalloc_track_base_alloc_bridge),
        Some(mem_kmalloc_track_base_free_bridge),
        Some(mem_kmalloc_track_lock_bridge),
        Some(mem_kmalloc_track_unlock_bridge),
        Some(mem_kmalloc_track_spin_init_bridge),
        Some(mem_kmalloc_track_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn _kfree(ptr: *mut c_void, file: *mut i8, line: CInt) {
    let _ = kmalloc_track_free_result(
        ptr,
        file,
        line,
        MEMDEBUG,
        kmalloc_track_hash_ptr(),
        kmalloc_track_locks_ptr(),
        kmalloc_addr_hash_ptr(),
        kmalloc_addr_locks_ptr(),
        Some(mem_kmalloc_track_base_free_bridge),
        Some(mem_kmalloc_track_lock_bridge),
        Some(mem_kmalloc_track_unlock_bridge),
        Some(mem_kmalloc_invalid_free_bridge),
        Some(mem_kmalloc_track_log_bridge),
    );
}

unsafe fn kmalloc_no_preempt_counter() -> CInt {
    let cpu = unsafe { get_this_cpu_local_var() };
    if cpu.is_null() {
        -1
    } else {
        unsafe { (*cpu).no_preempt.counter }
    }
}

#[no_mangle]
pub unsafe extern "C" fn kmalloc_tracked(
    size: CInt,
    flag: CULong,
    file: *mut i8,
    line: CInt,
) -> *mut c_void {
    let ptr = unsafe { _kmalloc(size, flag, file, line) };
    if ptr.is_null() {
        unsafe {
            kprintf(
                KMALLOC_OOM_FMT.as_ptr().cast::<i8>(),
                file,
                line,
                kmalloc_no_preempt_counter(),
            );
        }
    }
    ptr
}

#[no_mangle]
pub unsafe extern "C" fn kfree_tracked(ptr: *mut c_void, file: *mut i8, line: CInt) {
    unsafe {
        _kfree(ptr, file, line);
    }
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_init_chunk_result(h: *mut KmallocHeader, size: CInt) {
    (*h).size = size;
    (*h).front_magic = KMALLOC_FRONT_MAGIC;
    (*h).end_magic = KMALLOC_END_MAGIC;
    (*h).cpu_id = ihk_mc_get_processor_id();
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_insert_chunk_result(
    free_list: *mut AbiListHead,
    chunk: *mut KmallocHeader,
) {
    let mut next_chunk: *mut KmallocHeader = null_mut();
    let mut node = (*free_list).next;

    while node != free_list {
        let chunk_iter = list_to_kmalloc_header(node);
        if (chunk as usize) < (chunk_iter as usize) {
            next_chunk = chunk_iter;
            break;
        }
        node = (*node).next;
    }

    if !next_chunk.is_null() {
        list_add_tail(kmalloc_list(chunk), kmalloc_list(next_chunk));
    } else {
        list_add_tail(kmalloc_list(chunk), free_list);
    }
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_consolidate_list_result(list: *mut AbiListHead) {
    loop {
        let mut chunk_iter: *mut KmallocHeader = null_mut();
        let mut chunk: *mut KmallocHeader = null_mut();
        let mut next_chunk: *mut KmallocHeader = null_mut();
        let mut node = (*list).next;

        while node != list {
            let candidate = list_to_kmalloc_header(node);

            if !chunk_iter.is_null()
                && (chunk_iter as usize)
                    + core::mem::size_of::<KmallocHeader>()
                    + (*chunk_iter).size as usize
                    == candidate as usize
            {
                chunk = chunk_iter;
                next_chunk = candidate;
                break;
            }

            chunk_iter = candidate;
            node = (*node).next;
        }

        if chunk.is_null() {
            return;
        }

        (*chunk).size += (*next_chunk).size + core::mem::size_of::<KmallocHeader>() as CInt;
        list_del(kmalloc_list(next_chunk));
    }
}

#[inline(always)]
fn kmalloc_aligned_size(size: CInt) -> CInt {
    if (size & KMALLOC_MIN_MASK) != 0 {
        size.wrapping_add(KMALLOC_MIN_SIZE - 1) & !KMALLOC_MIN_MASK
    } else {
        size
    }
}

#[inline(always)]
unsafe fn kmalloc_find_fit(free_list: *mut AbiListHead, size: CInt) -> *mut KmallocHeader {
    let mut node = (*free_list).next;

    while node != free_list {
        let chunk_iter = list_to_kmalloc_header(node);
        if (*chunk_iter).size >= size {
            return chunk_iter;
        }
        node = (*node).next;
    }

    null_mut()
}

#[inline(always)]
unsafe fn kmalloc_split_if_needed(chunk: *mut KmallocHeader, size: CInt) {
    let header_size = size_of::<KmallocHeader>() as CInt;

    if (*chunk).size > size.wrapping_add(header_size) {
        let leftover = (chunk.cast::<u8>())
            .add(size_of::<KmallocHeader>())
            .add(size as usize)
            .cast::<KmallocHeader>();
        ___kmalloc_init_chunk_result(
            leftover,
            (*chunk).size.wrapping_sub(size).wrapping_sub(header_size),
        );
        list_add_after(kmalloc_list(leftover), kmalloc_list(chunk));
        (*chunk).size = size;
    }
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_body_result(
    size: CInt,
    flag: CULong,
    free_list: *mut AbiListHead,
    irq_save_fn: Option<MemKmallocIrqSaveFn>,
    irq_restore_fn: Option<MemKmallocIrqRestoreFn>,
    alloc_pages_fn: Option<MemKmallocAllocPagesFn>,
) -> *mut c_void {
    if free_list.is_null() {
        return null_mut();
    }
    let Some(irq_save) = irq_save_fn else {
        return null_mut();
    };
    let Some(irq_restore) = irq_restore_fn else {
        return null_mut();
    };
    let Some(alloc_pages) = alloc_pages_fn else {
        return null_mut();
    };

    let irq_flags = irq_save();
    let size = kmalloc_aligned_size(size);
    let mut chunk = kmalloc_find_fit(free_list, size);

    if chunk.is_null() {
        let npages = ((size as CULong)
            .wrapping_add(size_of::<KmallocHeader>() as CULong)
            .wrapping_add(PAGE_SIZE - 1))
            >> PAGE_SHIFT;
        chunk = alloc_pages(npages as CInt, flag, IHK_MC_PG_KERNEL).cast::<KmallocHeader>();

        if chunk.is_null() {
            irq_restore(irq_flags);
            return null_mut();
        }

        ___kmalloc_init_chunk_result(
            chunk,
            (npages
                .wrapping_mul(PAGE_SIZE)
                .wrapping_sub(size_of::<KmallocHeader>() as CULong)) as CInt,
        );
        ___kmalloc_insert_chunk_result(free_list, chunk);
    }

    kmalloc_split_if_needed(chunk, size);
    list_del_poison(kmalloc_list(chunk));
    irq_restore(irq_flags);

    (chunk.cast::<u8>())
        .add(size_of::<KmallocHeader>())
        .cast::<c_void>()
}

#[no_mangle]
pub unsafe extern "C" fn ___kfree_body_result(
    ptr: *mut c_void,
    free_list: *mut AbiListHead,
    remote_free_list_lock_offset: CULong,
    remote_free_list_offset: CULong,
    irq_save_fn: Option<MemKmallocIrqSaveFn>,
    irq_restore_fn: Option<MemKmallocIrqRestoreFn>,
    get_cpu_local_var_fn: Option<MemKmallocGetCpuLocalVarFn>,
    remote_lock_fn: Option<MemKmallocSpinLockFn>,
    remote_unlock_fn: Option<MemKmallocSpinUnlockFn>,
    corruption_fn: Option<MemKmallocCorruptionFn>,
) -> CInt {
    if ptr.is_null() {
        return 0;
    }
    if free_list.is_null() {
        return -EINVAL;
    }
    let Some(irq_save) = irq_save_fn else {
        return -EINVAL;
    };
    let Some(irq_restore) = irq_restore_fn else {
        return -EINVAL;
    };

    let chunk = (ptr.cast::<u8>())
        .sub(size_of::<KmallocHeader>())
        .cast::<KmallocHeader>();
    let irq_flags = irq_save();

    if (*chunk).front_magic != KMALLOC_FRONT_MAGIC || (*chunk).end_magic != KMALLOC_END_MAGIC {
        if let Some(corruption) = corruption_fn {
            corruption(ptr);
        }
        return -EINVAL;
    }

    if (*chunk).cpu_id == ihk_mc_get_processor_id() {
        ___kmalloc_insert_chunk_result(free_list, chunk);
        ___kmalloc_consolidate_list_result(free_list);
    } else {
        let Some(get_cpu_local_var) = get_cpu_local_var_fn else {
            irq_restore(irq_flags);
            return -EINVAL;
        };
        let Some(remote_lock) = remote_lock_fn else {
            irq_restore(irq_flags);
            return -EINVAL;
        };
        let Some(remote_unlock) = remote_unlock_fn else {
            irq_restore(irq_flags);
            return -EINVAL;
        };

        let remote_cpu = get_cpu_local_var((*chunk).cpu_id);
        if remote_cpu.is_null() {
            irq_restore(irq_flags);
            return -EINVAL;
        }

        let lock_addr = (remote_cpu as CULong).wrapping_add(remote_free_list_lock_offset);
        let remote_list = (remote_cpu.cast::<u8>())
            .add(remote_free_list_offset as usize)
            .cast::<AbiListHead>();
        let remote_irq_flags = remote_lock(lock_addr);
        list_add_after(kmalloc_list(chunk), remote_list);
        remote_unlock(lock_addr, remote_irq_flags);
    }

    irq_restore(irq_flags);
    0
}
