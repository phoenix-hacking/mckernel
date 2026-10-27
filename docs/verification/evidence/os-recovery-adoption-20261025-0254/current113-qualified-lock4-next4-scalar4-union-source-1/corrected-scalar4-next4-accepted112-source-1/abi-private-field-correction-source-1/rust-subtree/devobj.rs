use core::{
    ffi::c_void,
    mem::size_of,
    ptr::{read_volatile, write, write_volatile},
};

use crate::abi::{
    CInt, CLong, CULong, IhkSpinlock, Memobj, MemobjOps, OffT, PagerMapResult, SizeT,
    X86UserContext,
};

const EFAULT: CInt = 14;
const EINVAL: CInt = 22;
const EFBIG: CInt = 27;
const ENOMEM: CInt = 12;
const PAGE_SHIFT: CInt = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const PAGE_P2ALIGN: CInt = 0;
const PFN_VALID: CULong = 1 << 63;
const PFN_PRESENT: CULong = 1;
const PFN_PFN: CULong = ((1 << 56) - 1) & !(PAGE_SIZE - 1);
const VR_WRITE_COMBINED: CULong = 0x400;
const PAGER_REQ_MAP: CULong = 0x0005;
const PAGER_REQ_PFN: CULong = 0x0006;
const PAGER_REQ_UNMAP: CULong = 0x0007;
const NR_MMAP: CInt = 9;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_PG_KERNEL: CInt = 0;
const MF_HAS_PAGER: CInt = 0x0001;
const MF_DEV_FILE: CInt = 0x2000;
const MF_REMAP_FILE_PAGES: CInt = 0x400000;
#[cfg(enable_profile)]
const PROFILE_PAGE_FAULT_DEV_FILE: CInt = 4004;
const DEVOBJ_FILE: &[u8] = b"kernel/rust/devobj.rs\0";
const DEVOBJ_RELEASE_FAILED_FMT: &[u8] = b"devobj_free(%p %lx): release failed. %d\n\0";
const DEVOBJ_OUT_OF_RANGE_FMT: &[u8] =
    b"devobj_get_page: error: out of range: off: %lu, page off: %lu obj->npages: %lu\n\0";
const DEVOBJ_FETCH_FAILED_FMT: &[u8] =
    b"devobj_get_page(%p %lx,%lx,%d):PAGER_REQ_PFN failed. %d\n\0";
const DEVOBJ_NOT_PRESENT_FMT: &[u8] = b"devobj_get_page(%p %lx,%lx,%d):not present. %lx\n\0";

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
    fn syscall_generic_forwarding(n: CInt, ctx: *mut X86UserContext) -> CLong;
    fn ihk_mc_map_memory(os: *mut c_void, phys: CULong, size: CULong) -> CULong;
    fn pfn_is_write_combined(pfn: CULong) -> CInt;
    fn ihk_mc_spinlock_init(lock: *mut IhkSpinlock);
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
    fn kprintf(format: *const i8, ...) -> CInt;
}

#[cfg(enable_profile)]
unsafe extern "C" {
    fn profile_event_add(type_: CInt, tsc: CULong);
}

#[cfg(not(enable_fugaku_hacks))]
#[repr(C)]
struct DevObj {
    memobj: Memobj,
    refcnt: CLong,
    handle: CULong,
    pfn_pgoff: OffT,
    pfn_table: *mut CULong,
    pfn_table_lock: IhkSpinlock,
    npages: SizeT,
}

#[cfg(not(enable_fugaku_hacks))]
static mut DEVOBJ_OPS: MemobjOps = MemobjOps {
    free: core::ptr::null_mut(),
    get_page: core::ptr::null_mut(),
    copy_page: core::ptr::null_mut(),
    flush_page: core::ptr::null_mut(),
    invalidate_page: core::ptr::null_mut(),
    lookup_page: core::ptr::null_mut(),
    update_page: core::ptr::null_mut(),
};

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn kernel_alloc(size: SizeT, flags: CULong) -> *mut c_void {
    _kmalloc(
        size as CInt,
        flags as CInt,
        DEVOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn kernel_free(ptr: *mut c_void) {
    _kfree(ptr, DEVOBJ_FILE.as_ptr() as *mut i8, line!() as CInt);
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn alloc_kernel_pages(npages: SizeT, flags: CULong) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages as CInt,
        PAGE_P2ALIGN,
        flags,
        -1,
        IHK_MC_PG_KERNEL,
        CULong::MAX,
        DEVOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn free_kernel_pages(ptr: *mut c_void, npages: SizeT) {
    _ihk_mc_free_pages(
        ptr,
        npages as CInt,
        IHK_MC_PG_KERNEL,
        DEVOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    );
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn zero_bytes(mut ptr: *mut u8, mut len: SizeT) {
    while len != 0 {
        write_volatile(ptr, 0);
        ptr = ptr.add(1);
        len -= 1;
    }
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn copy_bytes(mut dst: *mut i8, mut src: *const i8, mut len: SizeT) {
    while len != 0 {
        write_volatile(dst, read_volatile(src));
        dst = dst.add(1);
        src = src.add(1);
        len -= 1;
    }
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
unsafe fn devobj_ops_ptr() -> *mut MemobjOps {
    let ops = &raw mut DEVOBJ_OPS;
    (*ops).free = devobj_free as *const () as *mut c_void;
    (*ops).get_page = devobj_get_page as *const () as *mut c_void;
    ops
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
fn devobj_npages(len: SizeT) -> SizeT {
    len.wrapping_add((PAGE_SIZE - 1) as SizeT) / PAGE_SIZE as SizeT
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
fn devobj_pfn_table_npages(npages: SizeT) -> SizeT {
    let uintptr_per_page = PAGE_SIZE as SizeT / size_of::<CULong>();
    npages.wrapping_add(uintptr_per_page - 1) / uintptr_per_page
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
fn devobj_pgoff(off: OffT) -> OffT {
    off >> PAGE_SHIFT
}

#[cfg(not(enable_fugaku_hacks))]
#[inline(always)]
fn devobj_get_page_index(pgoff: OffT, base_pgoff: OffT, npages: SizeT) -> Result<CInt, CInt> {
    let end = (base_pgoff as CULong).wrapping_add(npages as CULong);
    if pgoff < base_pgoff || end <= pgoff as CULong {
        Err(-EFBIG)
    } else {
        Ok(pgoff.wrapping_sub(base_pgoff) as CInt)
    }
}

#[cfg(not(enable_fugaku_hacks))]
unsafe fn devobj_unmap(handle: CULong) -> CInt {
    let mut ctx: X86UserContext = core::mem::zeroed();
    ctx.gpr.rdi = PAGER_REQ_UNMAP;
    ctx.gpr.rsi = handle;
    ctx.gpr.rdx = 1;
    syscall_generic_forwarding(NR_MMAP, &raw mut ctx) as CInt
}

#[cfg(not(enable_fugaku_hacks))]
unsafe extern "C" fn devobj_free(memobj: *mut Memobj) {
    let obj = memobj.cast::<DevObj>();
    let handle = (*obj).handle;
    let error = devobj_unmap(handle);
    if error != 0 {
        kprintf(
            DEVOBJ_RELEASE_FAILED_FMT.as_ptr().cast(),
            obj,
            handle,
            error,
        );
    }

    if !(*obj).pfn_table.is_null() {
        free_kernel_pages(
            (*obj).pfn_table.cast::<c_void>(),
            devobj_pfn_table_npages((*obj).npages),
        );
    }
    if !(*memobj).path.is_null() {
        kernel_free((*memobj).path.cast::<c_void>());
    }
    kernel_free(obj.cast::<c_void>());
}

#[cfg(not(enable_fugaku_hacks))]
unsafe extern "C" fn devobj_get_page(
    memobj: *mut Memobj,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    flag: *mut CULong,
    _virt_addr: CULong,
) -> CInt {
    let obj = memobj.cast::<DevObj>();
    if physp.is_null() || flag.is_null() {
        return -EINVAL;
    }

    #[cfg(enable_profile)]
    profile_event_add(PROFILE_PAGE_FAULT_DEV_FILE, PAGE_SIZE);

    let pgoff = devobj_pgoff(off);
    let ix = match devobj_get_page_index(pgoff, (*obj).pfn_pgoff, (*obj).npages) {
        Ok(ix) => ix,
        Err(error) => {
            kprintf(
                DEVOBJ_OUT_OF_RANGE_FMT.as_ptr().cast(),
                off as CULong,
                pgoff as CULong,
                (*obj).npages,
            );
            return error;
        }
    };

    let mut irqstate = __ihk_mc_spinlock_lock(&raw mut (*obj).pfn_table_lock);
    let mut pfn = *(*obj).pfn_table.add(ix as usize);
    __ihk_mc_spinlock_unlock(&raw mut (*obj).pfn_table_lock, irqstate);

    if (pfn & PFN_VALID) == 0 {
        let mut ctx: X86UserContext = core::mem::zeroed();
        pfn = 0;
        ctx.gpr.rdi = PAGER_REQ_PFN;
        ctx.gpr.rsi = (*obj).handle;
        ctx.gpr.rdx = (off & !((PAGE_SIZE - 1) as OffT)) as CULong;
        ctx.gpr.r10 = virt_to_phys((&raw mut pfn).cast::<c_void>());

        let error = syscall_generic_forwarding(NR_MMAP, &raw mut ctx) as CInt;
        if error != 0 {
            kprintf(
                DEVOBJ_FETCH_FAILED_FMT.as_ptr().cast(),
                memobj,
                (*obj).handle,
                off as CULong,
                p2align,
                error,
            );
            return error;
        }

        if (pfn & PFN_PRESENT) != 0 {
            let attr = pfn & !PFN_PFN;
            if pfn_is_write_combined(pfn) != 0 {
                *flag |= VR_WRITE_COMBINED;
            }
            let mapped = ihk_mc_map_memory(core::ptr::null_mut(), pfn & PFN_PFN, PAGE_SIZE);
            pfn = (mapped & PFN_PFN) | attr;
        }

        irqstate = __ihk_mc_spinlock_lock(&raw mut (*obj).pfn_table_lock);
        let slot = (*obj).pfn_table.add(ix as usize);
        if read_volatile(slot) == 0 {
            write_volatile(slot, pfn);
        }
        __ihk_mc_spinlock_unlock(&raw mut (*obj).pfn_table_lock, irqstate);
    }

    if (pfn & PFN_PRESENT) == 0 {
        kprintf(
            DEVOBJ_NOT_PRESENT_FMT.as_ptr().cast(),
            memobj,
            (*obj).handle,
            off as CULong,
            p2align,
            pfn,
        );
        return -EFAULT;
    }

    *physp = pfn & PFN_PFN;
    0
}

#[cfg(not(enable_fugaku_hacks))]
#[no_mangle]
pub unsafe extern "C" fn devobj_create(
    fd: CInt,
    len: SizeT,
    off: OffT,
    objp: *mut *mut Memobj,
    maxprotp: *mut CInt,
    prot: CInt,
    populate_flags: CInt,
) -> CInt {
    if objp.is_null() || maxprotp.is_null() {
        return -EINVAL;
    }

    let npages = devobj_npages(len);
    let pfn_npages = devobj_pfn_table_npages(npages);
    let mut result: PagerMapResult = core::mem::zeroed();
    let obj = kernel_alloc(size_of::<DevObj>(), IHK_MC_AP_NOWAIT).cast::<DevObj>();
    if obj.is_null() {
        return -ENOMEM;
    }
    zero_bytes(obj.cast::<u8>(), size_of::<DevObj>());

    (*obj).pfn_table = alloc_kernel_pages(pfn_npages, IHK_MC_AP_NOWAIT).cast::<CULong>();
    if (*obj).pfn_table.is_null() {
        kernel_free(obj.cast::<c_void>());
        return -ENOMEM;
    }
    zero_bytes(
        (*obj).pfn_table.cast::<u8>(),
        pfn_npages * PAGE_SIZE as SizeT,
    );

    let mut ctx: X86UserContext = core::mem::zeroed();
    ctx.gpr.rdi = PAGER_REQ_MAP;
    ctx.gpr.rsi = fd as CULong;
    ctx.gpr.rdx = len as CULong;
    ctx.gpr.r10 = off as CULong;
    ctx.gpr.r8 = virt_to_phys((&raw mut result).cast::<c_void>());
    ctx.gpr.r9 = (prot | populate_flags) as CULong;

    let error = syscall_generic_forwarding(NR_MMAP, &raw mut ctx) as CInt;
    if error != 0 {
        free_kernel_pages((*obj).pfn_table.cast::<c_void>(), pfn_npages);
        kernel_free(obj.cast::<c_void>());
        return error;
    }

    (*obj).memobj.ops = devobj_ops_ptr();
    (*obj).memobj.flags = (MF_HAS_PAGER | MF_REMAP_FILE_PAGES | MF_DEV_FILE) as u32;
    (*obj).memobj.size = len;
    (*obj).memobj.refcnt.counter = 1;
    (*obj).handle = result.handle;

    if result.path[0] != 0 {
        (*obj).memobj.path = kernel_alloc(crate::abi::PATH_MAX, IHK_MC_AP_NOWAIT).cast::<i8>();
        if (*obj).memobj.path.is_null() {
            free_kernel_pages((*obj).pfn_table.cast::<c_void>(), pfn_npages);
            kernel_free(obj.cast::<c_void>());
            return -ENOMEM;
        }
        copy_bytes(
            (*obj).memobj.path,
            result.path.as_ptr(),
            crate::abi::PATH_MAX,
        );
    }

    (*obj).pfn_pgoff = devobj_pgoff(off);
    (*obj).npages = npages;
    ihk_mc_spinlock_init(&raw mut (*obj).pfn_table_lock);

    *objp = &raw mut (*obj).memobj;
    write(maxprotp, result.maxprot);
    0
}
