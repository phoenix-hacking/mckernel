use core::{ffi::c_void, mem::size_of, ptr::write_volatile};

use crate::abi::{
    AbiListHead, CInt, CULong, IhkAtomic, IhkAtomic64, IhkSpinlock, Memobj, MemobjOps, OffT, SizeT,
};

const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const PAGE_SHIFT: CInt = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const PAGE_P2ALIGN: CInt = 0;
const PM_NONE: CInt = 0x00;
const PM_MAPPED: CInt = 0x07;
const MF_ZEROOBJ: CInt = 0x20000;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_PG_KERNEL: CInt = 0;
const ZEROOBJ_FILE: &[u8] = b"kernel/rust/zeroobj.rs\0";
const ZEROOBJ_FREE_FMT: &[u8] = b"trying to free zeroobj, this should never happen\n\0";
const ZEROOBJ_DUP_PANIC: &[u8] = b"alloc_zeroobj:dup alloc\0";

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
    fn phys_to_page_insert_hash(phys: CULong) -> *mut c_void;
    fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock);
    fn __ihk_mc_spinlock_unlock_noirq(lock: *mut IhkSpinlock);
    fn memobj_ref(obj: *mut Memobj) -> CInt;
    fn kprintf(format: *const i8, ...) -> CInt;
    #[link_name = "panic"]
    fn kernel_panic(msg: *const i8) -> !;
}

#[repr(C)]
struct ObjectPage {
    list: AbiListHead,
    hash: AbiListHead,
    mode: u8,
    phys: CULong,
    count: IhkAtomic,
    mapped: IhkAtomic64,
    offset: OffT,
    pgshift: CInt,
}

#[repr(C)]
struct ZeroObj {
    memobj: Memobj,
    page_list: AbiListHead,
}

static mut ZEROOBJ_OPS: MemobjOps = MemobjOps {
    free: core::ptr::null_mut(),
    get_page: core::ptr::null_mut(),
    copy_page: core::ptr::null_mut(),
    flush_page: core::ptr::null_mut(),
    invalidate_page: core::ptr::null_mut(),
    lookup_page: core::ptr::null_mut(),
    update_page: core::ptr::null_mut(),
};
static mut THE_ZEROOBJ_LOCK: IhkSpinlock = IhkSpinlock { head_tail: 0 };
static mut THE_ZEROOBJ: *mut ZeroObj = core::ptr::null_mut();

#[inline(always)]
unsafe fn kernel_alloc(size: SizeT, flags: CULong) -> *mut c_void {
    _kmalloc(
        size as CInt,
        flags as CInt,
        ZEROOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn kernel_free(ptr: *mut c_void) {
    _kfree(ptr, ZEROOBJ_FILE.as_ptr() as *mut i8, line!() as CInt);
}

#[inline(always)]
unsafe fn alloc_kernel_pages(npages: CInt, flags: CULong) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        PAGE_P2ALIGN,
        flags,
        -1,
        IHK_MC_PG_KERNEL,
        CULong::MAX,
        ZEROOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn free_kernel_pages(ptr: *mut c_void, npages: CInt) {
    _ihk_mc_free_pages(
        ptr,
        npages,
        IHK_MC_PG_KERNEL,
        ZEROOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    );
}

#[inline(always)]
unsafe fn zero_bytes(mut ptr: *mut u8, mut len: SizeT) {
    while len != 0 {
        write_volatile(ptr, 0);
        ptr = ptr.add(1);
        len -= 1;
    }
}

#[inline(always)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[inline(always)]
unsafe fn list_add(new: *mut AbiListHead, head: *mut AbiListHead) {
    let next = (*head).next;
    (*next).prev = new;
    (*new).next = next;
    (*new).prev = head;
    (*head).next = new;
}

#[inline(always)]
unsafe fn zeroobj_ops_ptr() -> *mut MemobjOps {
    let ops = &raw mut ZEROOBJ_OPS;
    (*ops).get_page = zeroobj_get_page as *const () as *mut c_void;
    (*ops).free = zeroobj_free as *const () as *mut c_void;
    ops
}

unsafe extern "C" fn zeroobj_free(_obj: *mut Memobj) {
    kprintf(ZEROOBJ_FREE_FMT.as_ptr().cast());
}

unsafe fn alloc_zeroobj() -> CInt {
    let mut obj: *mut ZeroObj;
    let mut virt: *mut c_void = core::ptr::null_mut();
    let mut error = 0;
    let lock = &raw mut THE_ZEROOBJ_LOCK;

    __ihk_mc_spinlock_lock_noirq(lock);
    if !THE_ZEROOBJ.is_null() {
        __ihk_mc_spinlock_unlock_noirq(lock);
        return 0;
    }

    obj = kernel_alloc(size_of::<ZeroObj>(), IHK_MC_AP_NOWAIT).cast::<ZeroObj>();
    if obj.is_null() {
        error = -ENOMEM;
    } else {
        zero_bytes(obj.cast::<u8>(), size_of::<ZeroObj>());
        (*obj).memobj.ops = zeroobj_ops_ptr();
        (*obj).memobj.flags = MF_ZEROOBJ as u32;
        (*obj).memobj.size = 0;
        (*obj).memobj.refcnt.counter = 2;
        init_list_head(&raw mut (*obj).page_list);

        virt = alloc_kernel_pages(1, IHK_MC_AP_NOWAIT);
        if virt.is_null() {
            error = -ENOMEM;
        } else {
            let phys = virt_to_phys(virt);
            let page = phys_to_page_insert_hash(phys).cast::<ObjectPage>();
            if (*page).mode as CInt != PM_NONE {
                kernel_panic(ZEROOBJ_DUP_PANIC.as_ptr().cast());
            }

            zero_bytes(virt.cast::<u8>(), PAGE_SIZE as SizeT);
            (*page).mode = PM_MAPPED as u8;
            (*page).offset = 0;
            (*page).count.counter = 1;
            (*page).mapped.counter64 = 0;
            list_add(&raw mut (*page).list, &raw mut (*obj).page_list);
            virt = core::ptr::null_mut();

            THE_ZEROOBJ = obj;
            obj = core::ptr::null_mut();
        }
    }
    __ihk_mc_spinlock_unlock_noirq(lock);

    if !virt.is_null() {
        free_kernel_pages(virt, 1);
    }
    if !obj.is_null() {
        kernel_free(obj.cast::<c_void>());
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn zeroobj_create(objp: *mut *mut Memobj) -> CInt {
    if objp.is_null() {
        return -EINVAL;
    }

    if THE_ZEROOBJ.is_null() {
        let error = alloc_zeroobj();
        if error != 0 {
            return error;
        }
    }

    let obj = &raw mut (*THE_ZEROOBJ).memobj;
    *objp = obj;
    memobj_ref(obj);
    0
}

unsafe extern "C" fn zeroobj_get_page(
    _memobj: *mut Memobj,
    _off: OffT,
    _p2align: CInt,
    _physp: *mut CULong,
    _pflag: *mut CULong,
    _virt_addr: CULong,
) -> CInt {
    0
}
