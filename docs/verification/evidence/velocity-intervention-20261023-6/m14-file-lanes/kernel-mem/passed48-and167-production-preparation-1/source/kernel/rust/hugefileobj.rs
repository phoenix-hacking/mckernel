use core::{
    ffi::c_void,
    mem::{offset_of, size_of},
    ptr::{read_volatile, write_volatile},
};

use crate::abi::{
    AbiListHead, CInt, CLong, CULong, IhkAtomic, IhkSpinlock, Memobj, MemobjOps, OffT,
    PagerCreateResult, SizeT,
};

const EINVAL: CInt = 22;
const EIO: CInt = 5;
const ENOMEM: CInt = 12;
const PAGE_SHIFT: CInt = 12;
const PTL1_SHIFT: CInt = 12;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_AP_USER: CULong = 0x001000;
const IHK_MC_PG_USER: CInt = 1;
const MEMOBJ_READY: CInt = 0;
const HUGEFILEOBJ_FILE: &[u8] = b"kernel/rust/hugefileobj.rs\0";
const HUGEFILEOBJ_P2ALIGN_FMT: &[u8] = b"hugefileobj_get_page: p2align %ld but expected %ld\n\0";
const HUGEFILEOBJ_GET_ALLOC_FMT: &[u8] =
    b"hugefileobj_get_page: error: could not allocate page for off: %lu, page size: %lu\n\0";
const HUGEFILEOBJ_PRE_ALLOC_OBJ_FMT: &[u8] =
    b"hugefileobj_pre_create: error: allocating hugefileobj\n\0";
const HUGEFILEOBJ_PRE_ALLOC_PATH_FMT: &[u8] = b"hugefileobj_pre_create: error: allocating path\n\0";

unsafe extern "C" {
    fn _kmalloc(size: CInt, flags: CInt, file: *mut i8, line: CInt) -> *mut c_void;
    fn _kfree(ptr: *mut c_void, file: *mut i8, line: CInt);
    fn _ihk_mc_alloc_aligned_pages_node(
        npages: CInt,
        p2align: CInt,
        flag: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
        file: *mut i8,
        line: CInt,
    ) -> *mut c_void;
    fn _ihk_mc_free_pages(ptr: *mut c_void, npages: CInt, is_user: CInt, file: *mut i8, line: CInt);
    fn virt_to_phys(v: *mut c_void) -> CULong;
    fn ihk_mc_spinlock_init(lock: *mut IhkSpinlock);
    fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock);
    fn __ihk_mc_spinlock_unlock_noirq(lock: *mut IhkSpinlock);
    fn memobj_ref(obj: *mut Memobj) -> CInt;
    fn ihk_atomic_dec(v: *mut IhkAtomic);
    fn kprintf(format: *const i8, ...) -> CInt;
}

#[cfg(not(enable_fugaku_hacks))]
#[repr(C)]
struct HugeFileObj {
    memobj: Memobj,
    pgsize: SizeT,
    handle: CULong,
    pgshift: u32,
    padding: u32,
    nr_pages: SizeT,
    pages: *mut *mut c_void,
    lock: IhkSpinlock,
    padding2: CInt,
    obj_list: AbiListHead,
}

#[cfg(not(enable_fugaku_hacks))]
#[no_mangle]
pub static mut hugefileobj_ops: MemobjOps = MemobjOps {
    free: core::ptr::null_mut(),
    get_page: core::ptr::null_mut(),
    copy_page: core::ptr::null_mut(),
    flush_page: core::ptr::null_mut(),
    invalidate_page: core::ptr::null_mut(),
    lookup_page: core::ptr::null_mut(),
    update_page: core::ptr::null_mut(),
};

#[cfg(not(enable_fugaku_hacks))]
static mut HUGEFILEOBJ_LIST_LOCK: IhkSpinlock = IhkSpinlock { head_tail: 0 };
#[cfg(not(enable_fugaku_hacks))]
static mut HUGEFILEOBJ_LIST: AbiListHead = AbiListHead {
    next: core::ptr::null_mut(),
    prev: core::ptr::null_mut(),
};
#[cfg(not(enable_fugaku_hacks))]
static mut HUGEFILEOBJ_GLOBALS_INIT: CInt = 0;

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn kernel_alloc(size: SizeT, flags: CULong) -> *mut c_void {
    _kmalloc(
        size as CInt,
        flags as CInt,
        HUGEFILEOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn kernel_free(ptr: *mut c_void) {
    _kfree(ptr, HUGEFILEOBJ_FILE.as_ptr() as *mut i8, line!() as CInt);
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn alloc_user_pages(
    npages: CInt,
    p2align: CInt,
    flags: CULong,
    virt_addr: CULong,
) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        p2align,
        flags,
        -1,
        IHK_MC_PG_USER,
        virt_addr,
        HUGEFILEOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn free_user_pages(ptr: *mut c_void, npages: CInt) {
    _ihk_mc_free_pages(
        ptr,
        npages,
        IHK_MC_PG_USER,
        HUGEFILEOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    );
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn copy_bytes(mut dst: *mut u8, mut src: *const u8, mut len: SizeT) {
    while len != 0 {
        write_volatile(dst, read_volatile(src));
        dst = dst.add(1);
        src = src.add(1);
        len -= 1;
    }
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn set_bytes(mut dst: *mut u8, value: u8, mut len: SizeT) {
    while len != 0 {
        write_volatile(dst, value);
        dst = dst.add(1);
        len -= 1;
    }
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn list_add(new: *mut AbiListHead, head: *mut AbiListHead) {
    let next = (*head).next;
    (*next).prev = new;
    (*new).next = next;
    (*new).prev = head;
    (*head).next = new;
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn list_empty(head: *mut AbiListHead) -> CInt {
    ((*head).next == head) as CInt
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn list_del(entry: *mut AbiListHead) {
    let prev = (*entry).prev;
    let next = (*entry).next;

    (*next).prev = prev;
    (*prev).next = next;
    (*entry).next = 0x0010_0129usize as *mut AbiListHead;
    (*entry).prev = 0x0020_0229usize as *mut AbiListHead;
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn hugefileobj_from_list(entry: *mut AbiListHead) -> *mut HugeFileObj {
    entry
        .cast::<u8>()
        .sub(offset_of!(HugeFileObj, obj_list))
        .cast::<HugeFileObj>()
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn hugefileobj_ops_ptr() -> *mut MemobjOps {
    let ops = &raw mut hugefileobj_ops;
    (*ops).free = hugefileobj_free as *const () as *mut c_void;
    (*ops).get_page = hugefileobj_get_page as *const () as *mut c_void;
    ops
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn hugefileobj_ensure_globals() {
    if read_volatile(&raw const HUGEFILEOBJ_GLOBALS_INIT) == 0 {
        init_list_head(&raw mut HUGEFILEOBJ_LIST);
        ihk_mc_spinlock_init(&raw mut HUGEFILEOBJ_LIST_LOCK);
        hugefileobj_ops_ptr();
        write_volatile(&raw mut HUGEFILEOBJ_GLOBALS_INIT, 1);
    }
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
fn expected_p2align(pgshift: CInt) -> CInt {
    pgshift - PTL1_SHIFT
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
fn pgsize(pgshift: CInt) -> SizeT {
    1usize << pgshift
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
fn npages_per_page(size: SizeT) -> CInt {
    (size >> PAGE_SHIFT) as CInt
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
fn page_index(off: OffT, pgshift: CInt) -> OffT {
    off >> pgshift
}

#[cfg(not(enable_fugaku_hacks))]
unsafe fn hugefileobj_lookup(handle: CULong) -> *mut HugeFileObj {
    let head = &raw mut HUGEFILEOBJ_LIST;
    let mut entry = (*head).next;

    while entry != head {
        let obj = hugefileobj_from_list(entry);
        if (*obj).handle == handle {
            if memobj_ref(&raw mut (*obj).memobj) > 1 {
                return obj;
            }
            ihk_atomic_dec(&raw mut (*obj).memobj.refcnt);
        }
        entry = (*entry).next;
    }

    core::ptr::null_mut()
}

#[cfg(not(enable_fugaku_hacks))]
unsafe fn hugefileobj_inner_free(obj: *mut HugeFileObj) {
    __ihk_mc_spinlock_lock_noirq(&raw mut (*obj).lock);
    if !(*obj).memobj.path.is_null() {
        kernel_free((*obj).memobj.path.cast::<c_void>());
        (*obj).memobj.path = core::ptr::null_mut();
    }

    if !(*obj).pages.is_null() {
        let npages = npages_per_page((*obj).pgsize);
        let mut index = 0usize;
        while index < (*obj).nr_pages {
            let page = *(*obj).pages.add(index);
            if !page.is_null() {
                free_user_pages(page, npages);
            }
            index += 1;
        }
        kernel_free((*obj).pages.cast::<c_void>());
    }

    __ihk_mc_spinlock_unlock_noirq(&raw mut (*obj).lock);
    kernel_free(obj.cast::<c_void>());
}

#[cfg(not(enable_fugaku_hacks))]
unsafe extern "C" fn hugefileobj_free(memobj: *mut Memobj) {
    let obj = memobj.cast::<HugeFileObj>();
    __ihk_mc_spinlock_lock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);
    list_del(&raw mut (*obj).obj_list);
    __ihk_mc_spinlock_unlock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);
    hugefileobj_inner_free(obj);
}

#[cfg(not(enable_fugaku_hacks))]
unsafe extern "C" fn hugefileobj_get_page(
    memobj: *mut Memobj,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    _pflag: *mut CULong,
    virt_addr: CULong,
) -> CInt {
    if physp.is_null() {
        return -EINVAL;
    }
    let obj = memobj.cast::<HugeFileObj>();
    let expected = expected_p2align((*obj).pgshift as CInt);
    if p2align != expected {
        kprintf(
            HUGEFILEOBJ_P2ALIGN_FMT.as_ptr().cast(),
            p2align as CLong,
            expected as CLong,
        );
        return -ENOMEM;
    }

    let pgind = page_index(off, (*obj).pgshift as CInt);
    let npages = npages_per_page((*obj).pgsize);
    __ihk_mc_spinlock_lock_noirq(&raw mut (*obj).lock);
    let slot = (*obj).pages.add(pgind as usize);
    let mut page = *slot;
    let mut ret = 0;
    if page.is_null() {
        page = alloc_user_pages(
            npages,
            p2align,
            IHK_MC_AP_NOWAIT | IHK_MC_AP_USER,
            virt_addr,
        );
        if page.is_null() {
            kprintf(
                HUGEFILEOBJ_GET_ALLOC_FMT.as_ptr().cast(),
                off as CULong,
                (*obj).pgsize,
            );
            ret = -EIO;
        } else {
            *slot = page;
            set_bytes(page.cast::<u8>(), 0, (*obj).pgsize);
        }
    }

    if ret == 0 {
        *physp = virt_to_phys(page);
    }
    __ihk_mc_spinlock_unlock_noirq(&raw mut (*obj).lock);
    ret
}

#[cfg(not(enable_fugaku_hacks))]
#[no_mangle]
pub unsafe extern "C" fn hugefileobj_cleanup() {
    hugefileobj_ensure_globals();
    loop {
        __ihk_mc_spinlock_lock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);
        if list_empty(&raw mut HUGEFILEOBJ_LIST) != 0 {
            __ihk_mc_spinlock_unlock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);
            break;
        }
        let obj = hugefileobj_from_list(HUGEFILEOBJ_LIST.next);
        list_del(&raw mut (*obj).obj_list);
        __ihk_mc_spinlock_unlock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);
        hugefileobj_inner_free(obj);
    }
}

#[cfg(not(enable_fugaku_hacks))]
#[no_mangle]
pub unsafe extern "C" fn hugefileobj_pre_create(
    result: *mut PagerCreateResult,
    objp: *mut *mut Memobj,
    maxprotp: *mut CInt,
) -> CInt {
    if result.is_null() || objp.is_null() || maxprotp.is_null() {
        return -EINVAL;
    }

    hugefileobj_ensure_globals();
    __ihk_mc_spinlock_lock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);

    let mut obj = hugefileobj_lookup((*result).handle);
    if !obj.is_null() {
        write_volatile(maxprotp, (*result).maxprot);
        write_volatile(objp, &raw mut (*obj).memobj);
        __ihk_mc_spinlock_unlock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);
        return 0;
    }

    obj = kernel_alloc(size_of::<HugeFileObj>(), IHK_MC_AP_NOWAIT).cast::<HugeFileObj>();
    if obj.is_null() {
        kprintf(HUGEFILEOBJ_PRE_ALLOC_OBJ_FMT.as_ptr().cast());
        __ihk_mc_spinlock_unlock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);
        return -ENOMEM;
    }
    set_bytes(obj.cast::<u8>(), 0, size_of::<HugeFileObj>());

    (*obj).handle = (*result).handle;
    (*obj).pgsize = pgsize((*result).pgshift);
    (*obj).pgshift = (*result).pgshift as u32;
    (*obj).pages = core::ptr::null_mut();
    (*obj).nr_pages = 0;
    ihk_mc_spinlock_init(&raw mut (*obj).lock);
    (*obj).memobj.flags = (*result).flags;
    (*obj).memobj.status = MEMOBJ_READY as u32;
    (*obj).memobj.ops = hugefileobj_ops_ptr();
    (*obj).memobj.refcnt.counter = 2;

    if read_volatile((*result).path.as_ptr().cast::<u8>()) != 0 {
        (*obj).memobj.path = kernel_alloc(crate::abi::PATH_MAX, IHK_MC_AP_NOWAIT).cast::<i8>();
        if (*obj).memobj.path.is_null() {
            kprintf(HUGEFILEOBJ_PRE_ALLOC_PATH_FMT.as_ptr().cast());
            kernel_free(obj.cast::<c_void>());
            __ihk_mc_spinlock_unlock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);
            return -ENOMEM;
        }
        copy_bytes(
            (*obj).memobj.path.cast::<u8>(),
            (*result).path.as_ptr().cast::<u8>(),
            crate::abi::PATH_MAX,
        );
    }

    list_add(&raw mut (*obj).obj_list, &raw mut HUGEFILEOBJ_LIST);
    write_volatile(maxprotp, (*result).maxprot);
    write_volatile(objp, &raw mut (*obj).memobj);
    __ihk_mc_spinlock_unlock_noirq(&raw mut HUGEFILEOBJ_LIST_LOCK);
    0
}

#[cfg(not(enable_fugaku_hacks))]
#[no_mangle]
pub unsafe extern "C" fn hugefileobj_create(
    memobj: *mut Memobj,
    len: SizeT,
    off: OffT,
    pgshiftp: *mut CInt,
    _virt_addr: CULong,
) -> CInt {
    if memobj.is_null() || pgshiftp.is_null() {
        return -EINVAL;
    }
    let obj = memobj.cast::<HugeFileObj>();
    let nr_pages = (off.wrapping_add(len as OffT) >> (*obj).pgshift) as SizeT;
    let mut ret = 0;

    __ihk_mc_spinlock_lock_noirq(&raw mut (*obj).lock);
    if (*obj).nr_pages < nr_pages {
        let bytes = nr_pages * size_of::<*mut c_void>();
        let pages = kernel_alloc(bytes, IHK_MC_AP_NOWAIT).cast::<*mut c_void>();
        if pages.is_null() {
            ret = -ENOMEM;
        } else {
            if (*obj).nr_pages != 0 {
                copy_bytes(
                    pages.cast::<u8>(),
                    (*obj).pages.cast::<u8>(),
                    (*obj).nr_pages * size_of::<*mut c_void>(),
                );
            }
            set_bytes(
                pages.add((*obj).nr_pages).cast::<u8>(),
                0,
                (nr_pages - (*obj).nr_pages) * size_of::<*mut c_void>(),
            );
            if (*obj).nr_pages != 0 {
                kernel_free((*obj).pages.cast::<c_void>());
            }
            (*obj).nr_pages = nr_pages;
            (*obj).pages = pages;
        }
    }

    if ret == 0 {
        (*obj).memobj.size = len;
        write_volatile(pgshiftp, (*obj).pgshift as CInt);
    }
    __ihk_mc_spinlock_unlock_noirq(&raw mut (*obj).lock);
    ret
}
