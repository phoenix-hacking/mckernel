use core::{
    ffi::c_void,
    mem::{offset_of, size_of},
    ptr::{copy_nonoverlapping, read_volatile, write, write_bytes, write_volatile},
    sync::atomic::{AtomicPtr, Ordering},
};

use crate::abi::{
    AbiListHead, CInt, CLong, CULong, CpuLocalVar, IhkAtomic, IhkAtomic64, McsLockNode, Memobj,
    MemobjOps, OffT, PagerCreateResult, SizeT, Thread, X86UserContext, IHK_MAX_NUM_CPUS,
    IHK_MAX_NUM_NUMA_NODES, IHK_MAX_NUM_PGSIZES, PATH_MAX,
};

const EIO: CInt = 5;
const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const ERANGE: CInt = 34;
const ERESTART: CInt = 85;
const ESRCH: CInt = 3;
const PAGE_SHIFT: CInt = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const PAGE_P2ALIGN: CInt = 0;
const FILEOBJ_PAGE_HASH_SHIFT: usize = 9;
const FILEOBJ_PAGE_HASH_SIZE: usize = 1 << FILEOBJ_PAGE_HASH_SHIFT;
const FILEOBJ_PAGE_HASH_MASK: usize = FILEOBJ_PAGE_HASH_SIZE - 1;
const PM_NONE: CInt = 0x00;
const PM_WILL_PAGEIO: CInt = 0x02;
const PM_PAGEIO: CInt = 0x03;
const PM_DONE_PAGEIO: CInt = 0x04;
const PM_PAGEIO_EOF: CInt = 0x05;
const PM_PAGEIO_ERROR: CInt = 0x06;
const PM_MAPPED: CInt = 0x07;
const PAGER_REQ_CREATE: CULong = 0x0001;
const PAGER_REQ_RELEASE: CULong = 0x0002;
const PAGER_REQ_READ: CULong = 0x0003;
const PAGER_REQ_WRITE: CULong = 0x0004;
const NR_MMAP: CInt = 9;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_AP_USER: CULong = 0x001000;
const IHK_MC_PG_USER: CInt = 1;
const MAP_PRIVATE: CInt = 0x02;
const MF_HAS_PAGER: CInt = 0x0001;
const MF_PREFETCH: CInt = 0x0008;
const MF_ZEROFILL: CInt = 0x0010;
const MF_REG_FILE: CInt = 0x1000;
const MF_PREMAP: CInt = 0x8000;
const MF_HUGETLBFS: CInt = 0x100000;
const MF_PRIVATE: CInt = 0x200000;
const MF_REMAP_FILE_PAGES: CInt = 0x400000;
const MEMOBJ_READY: CInt = 0;
const MEMOBJ_TO_BE_PREFETCHED: CInt = 1;
const MPOL_SHM_PREMAP: CULong = 0x08;
const FILEOBJ_FILE: &[u8] = b"kernel/rust/fileobj.rs\0";
const CREATE_FAILED_FMT: &[u8] = b"fileobj_create(%d):create failed. %d\n\0";
const CREATE_KMALLOC_FMT: &[u8] = b"fileobj_create(%d):kmalloc failed. %d\n\0";
const CREATE_PATH_FMT: &[u8] = b"fileobj_create: error: allocating path\n\0";
const CREATE_PREMAP_ARRAY_FMT: &[u8] = b"fileobj_create: WARNING: failed to allocate pages\n\0";
const CREATE_PREMAP_PAGE_FMT: &[u8] = b"fileobj_create: ERROR: allocating pages[%d]\n\0";
const PAGE_LOOKUP_FMT: &[u8] = b"page_list_lookup(%p,%lx): mode %x\n\0";
const PAGE_LOOKUP_PANIC: &[u8] = b"page_list_lookup:invalid obj page\0";
const GET_PREMAP_ALLOC_FMT: &[u8] = b"fileobj_get_page(%p,%lx,%x,%lx,%lx):alloc failed. %d\n\0";
const GET_REGULAR_KMALLOC_FMT: &[u8] =
    b"fileobj_get_page(%p,%lx,%x,%lx,%lx):kmalloc failed. %d\n\0";
const GET_REGULAR_ALLOC_FMT: &[u8] = b"fileobj_get_page(%p,%lx,%x,%lx,%lx):alloc failed. %d\n\0";
const GET_INVALID_NEW_PAGE: &[u8] = b"fileobj_get_page:invalid new page\0";
const PAGEIO_INVALID_FMT: &[u8] = b"fileobj_do_pageio(%p,%lx,%lx):invalid mode %x\n\0";
const PAGEIO_INVALID_PANIC: &[u8] = b"fileobj_do_pageio:invalid page mode\0";
const PAGEIO_READ_FAILED_FMT: &[u8] = b"fileobj_do_pageio(%p,%lx,%lx):read failed. %ld\n\0";
const FLUSH_MISSING_FMT: &[u8] =
    b"fileobj_flush_page: warning: tried to flush non-existing page for phys addr: 0x%lx\n\0";
const INVALIDATE_UNSUPPORTED_FMT: &[u8] =
    b"fileobj_invalidate_page: WARNING: file mapping invalidation not supported\n\0";
const FREE_INVALID_COUNT_FMT: &[u8] =
    b"fileobj_free: WARNING: page count is %d for phys 0x%lx is invalid, flags: 0x%lx\n\0";

#[cfg(enable_profile)]
const PROFILE_PAGE_FAULT_FILE: CInt = 4005;
#[cfg(enable_profile)]
const PROFILE_PAGE_FAULT_FILE_CLR: CInt = 4006;

#[repr(C)]
struct ObjectPage {
    list: AbiListHead,
    hash: AbiListHead,
    mode: u8,
    padding: [u8; 7],
    phys: CULong,
    count: IhkAtomic,
    padding2: CInt,
    mapped: IhkAtomic64,
    offset: OffT,
    pgshift: CInt,
    padding3: CInt,
}

#[repr(C)]
struct FileObj {
    memobj: Memobj,
    sref: CULong,
    handle: CULong,
    list: AbiListHead,
    page_hash: [AbiListHead; FILEOBJ_PAGE_HASH_SIZE],
    page_hash_locks: [McsLockNode; FILEOBJ_PAGE_HASH_SIZE],
}

#[repr(C)]
struct PageIoArgs {
    fileobj: *mut FileObj,
    objoff: OffT,
    pgsize: SizeT,
}

#[repr(C)]
struct RusagePercpu {
    user_tsc: CULong,
    system_tsc: CULong,
}

#[repr(C)]
struct RusageGlobal {
    memory_stat_rss: [CLong; IHK_MAX_NUM_PGSIZES],
    memory_stat_mapped_file: [CLong; IHK_MAX_NUM_PGSIZES],
    rss_current: CLong,
    memory_max_usage: CULong,
    max_num_threads: CULong,
    num_threads: CULong,
    memory_kmem_usage: CULong,
    memory_kmem_max_usage: CULong,
    memory_numa_stat: [CULong; IHK_MAX_NUM_NUMA_NODES],
    cpu: [RusagePercpu; IHK_MAX_NUM_CPUS],
    total_memory: CULong,
    total_memory_usage: CULong,
    total_memory_max_usage: CULong,
    num_numa_nodes: CULong,
    num_processors: CULong,
    ns_per_tsc: CULong,
}

static mut FILEOBJ_OPS: MemobjOps = MemobjOps {
    free: core::ptr::null_mut(),
    get_page: core::ptr::null_mut(),
    copy_page: core::ptr::null_mut(),
    flush_page: core::ptr::null_mut(),
    invalidate_page: core::ptr::null_mut(),
    lookup_page: core::ptr::null_mut(),
    update_page: core::ptr::null_mut(),
};

#[no_mangle]
pub static mut fileobj_list_lock: McsLockNode = McsLockNode {
    locked: 0,
    next: core::ptr::null_mut(),
    irqsave: 0,
};

static mut FILEOBJ_LIST: AbiListHead = AbiListHead {
    next: core::ptr::null_mut(),
    prev: core::ptr::null_mut(),
};
static mut FILEOBJ_GLOBALS_INIT: CInt = 0;

unsafe extern "C" {
    static mut rusage: RusageGlobal;

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
    fn phys_to_virt(phys: CULong) -> *mut c_void;
    fn phys_to_page(phys: CULong) -> *mut ObjectPage;
    fn page_to_phys(page: *mut ObjectPage) -> CULong;
    fn phys_to_page_insert_hash(phys: CULong) -> *mut c_void;
    fn page_unmap(page: *mut ObjectPage) -> CInt;
    fn mcs_lock_init(lock: *mut McsLockNode);
    fn mcs_lock_lock(lock: *mut McsLockNode, node: *mut McsLockNode);
    fn mcs_lock_unlock(lock: *mut McsLockNode, node: *mut McsLockNode);
    fn mcs_lock_lock_noirq(lock: *mut McsLockNode, node: *mut McsLockNode);
    fn mcs_lock_unlock_noirq(lock: *mut McsLockNode, node: *mut McsLockNode);
    fn memobj_ref(obj: *mut Memobj) -> CInt;
    fn memobj_unref(obj: *mut Memobj) -> CInt;
    fn ihk_atomic_read(v: *const IhkAtomic) -> CInt;
    fn ihk_atomic_set(v: *mut IhkAtomic, i: CInt);
    fn ihk_atomic_inc(v: *mut IhkAtomic);
    fn ihk_atomic_dec(v: *mut IhkAtomic);
    fn ihk_atomic64_set(v: *mut IhkAtomic64, i: CLong);
    fn ihk_atomic_add_long(i: CLong, v: *mut CLong);
    fn syscall_generic_forwarding(n: CInt, ctx: *mut X86UserContext) -> CLong;
    fn hugefileobj_pre_create(
        result: *mut PagerCreateResult,
        objp: *mut *mut Memobj,
        maxprotp: *mut CInt,
    ) -> CInt;
    fn get_cpu_local_var_result(id: CInt) -> *mut CpuLocalVar;
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_mc_get_nr_numa_nodes() -> CInt;
    fn schedule();
    fn cpu_pause();
    fn kprintf(format: *const i8, ...) -> CInt;
    #[link_name = "panic"]
    fn kernel_panic(msg: *const i8) -> !;
}

#[cfg(enable_profile)]
unsafe extern "C" {
    fn profile_event_add(type_: CInt, tsc: CULong);
}

#[inline(always)]
unsafe fn kernel_alloc(size: SizeT, flags: CULong) -> *mut c_void {
    _kmalloc(
        size as CInt,
        flags as CInt,
        FILEOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn kernel_free(ptr: *mut c_void) {
    _kfree(ptr, FILEOBJ_FILE.as_ptr() as *mut i8, line!() as CInt);
}

#[inline(always)]
unsafe fn alloc_user_pages(npages: CInt, flags: CULong, virt_addr: CULong) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        PAGE_P2ALIGN,
        flags,
        -1,
        IHK_MC_PG_USER,
        virt_addr,
        FILEOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn alloc_user_pages_node(
    npages: CInt,
    p2align: CInt,
    flags: CULong,
    node: CInt,
    virt_addr: CULong,
) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        p2align,
        flags,
        node,
        IHK_MC_PG_USER,
        virt_addr,
        FILEOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn free_user_pages(ptr: *mut c_void, npages: CInt) {
    _ihk_mc_free_pages(
        ptr,
        npages,
        IHK_MC_PG_USER,
        FILEOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    );
}

#[inline(always)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[inline(always)]
unsafe fn list_empty(head: *mut AbiListHead) -> bool {
    (*head).next == head
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
unsafe fn list_del(entry: *mut AbiListHead) {
    let prev = (*entry).prev;
    let next = (*entry).next;

    (*next).prev = prev;
    (*prev).next = next;
    (*entry).next = 0x0010_0129usize as *mut AbiListHead;
    (*entry).prev = 0x0020_0229usize as *mut AbiListHead;
}

#[inline(always)]
unsafe fn page_from_list(entry: *mut AbiListHead) -> *mut ObjectPage {
    entry.cast::<u8>().sub(offset_of!(ObjectPage, list)).cast()
}

#[inline(always)]
unsafe fn fileobj_from_list(entry: *mut AbiListHead) -> *mut FileObj {
    entry.cast::<u8>().sub(offset_of!(FileObj, list)).cast()
}

#[inline(always)]
unsafe fn fileobj_ops_ptr() -> *mut MemobjOps {
    let ops = &raw mut FILEOBJ_OPS;
    (*ops).free = fileobj_free as *const () as *mut c_void;
    (*ops).get_page = fileobj_get_page as *const () as *mut c_void;
    (*ops).flush_page = fileobj_flush_page as *const () as *mut c_void;
    (*ops).invalidate_page = fileobj_invalidate_page as *const () as *mut c_void;
    (*ops).lookup_page = fileobj_lookup_page as *const () as *mut c_void;
    ops
}

#[inline(always)]
unsafe fn ensure_globals() {
    if read_volatile(&raw const FILEOBJ_GLOBALS_INIT) == 0 {
        mcs_lock_init(&raw mut fileobj_list_lock);
        init_list_head(&raw mut FILEOBJ_LIST);
        fileobj_ops_ptr();
        write_volatile(&raw mut FILEOBJ_GLOBALS_INIT, 1);
    }
}

#[inline(always)]
fn page_hash(off: OffT) -> usize {
    ((off >> PAGE_SHIFT) as usize) & FILEOBJ_PAGE_HASH_MASK
}

#[inline(always)]
fn page_mode_valid(mode: CInt) -> bool {
    mode == PM_WILL_PAGEIO
        || mode == PM_PAGEIO
        || mode == PM_DONE_PAGEIO
        || mode == PM_PAGEIO_EOF
        || mode == PM_PAGEIO_ERROR
        || mode == PM_MAPPED
}

#[inline(always)]
fn base_flags(mmap_flags: CInt) -> CInt {
    MF_HAS_PAGER
        | MF_REG_FILE
        | MF_REMAP_FILE_PAGES
        | if (mmap_flags & MAP_PRIVATE) != 0 {
            MF_PRIVATE
        } else {
            0
        }
}

#[inline(always)]
fn status_from_flags(flags: CInt) -> CInt {
    if (flags & MF_PREFETCH) != 0 {
        MEMOBJ_TO_BE_PREFETCHED
    } else {
        MEMOBJ_READY
    }
}

#[inline(always)]
fn premap_zerofill(flags: CInt) -> bool {
    (flags & (MF_PREMAP | MF_ZEROFILL)) == (MF_PREMAP | MF_ZEROFILL)
}

#[inline(always)]
fn premap_npages(size: SizeT) -> CInt {
    ((size + (PAGE_SIZE as SizeT - 1)) >> PAGE_SHIFT) as CInt
}

#[inline(always)]
fn validate_p2align(p2align: CInt) -> CInt {
    if p2align != PAGE_P2ALIGN {
        -ENOMEM
    } else {
        0
    }
}

#[inline(always)]
fn alloc_npages(p2align: CInt) -> CInt {
    1 << p2align
}

#[inline(always)]
fn alloc_flags(flags: CInt) -> CULong {
    IHK_MC_AP_NOWAIT
        | if (flags & MF_ZEROFILL) != 0 {
            IHK_MC_AP_USER
        } else {
            0
        }
}

#[inline(always)]
fn pageio_pgsize(p2align: CInt) -> SizeT {
    (PAGE_SIZE as SizeT) << p2align
}

#[inline(always)]
fn pageio_mode_after_read(ret: CLong, pgsize: SizeT) -> CInt {
    if ret == 0 {
        PM_PAGEIO_EOF
    } else if ret != pgsize as CLong {
        PM_PAGEIO_ERROR
    } else {
        PM_DONE_PAGEIO
    }
}

#[inline(always)]
unsafe fn current_thread() -> *mut Thread {
    let cpu = ihk_mc_get_processor_id();
    let cpu_local = get_cpu_local_var_result(cpu);
    (*cpu_local).current
}

#[inline(always)]
fn rusage_pgsize_to_pgtype(pgsize: SizeT) -> usize {
    match pgsize {
        0x1000 => 0,
        0x20_0000 => 2,
        0x4000_0000 => 4,
        _ => 0,
    }
}

#[inline(always)]
unsafe fn mapped_file_rss_add(size: SizeT, pgsize: SizeT) {
    let slot = core::ptr::addr_of_mut!(rusage.memory_stat_mapped_file)
        .cast::<CLong>()
        .add(rusage_pgsize_to_pgtype(pgsize));
    ihk_atomic_add_long(size as CLong, slot);
}

#[inline(always)]
unsafe fn mapped_file_rss_sub(size: SizeT, pgsize: SizeT) {
    let slot = core::ptr::addr_of_mut!(rusage.memory_stat_mapped_file)
        .cast::<CLong>()
        .add(rusage_pgsize_to_pgtype(pgsize));
    ihk_atomic_add_long(-(size as CLong), slot);
}

unsafe fn page_hash_init(obj: *mut FileObj) {
    for i in 0..FILEOBJ_PAGE_HASH_SIZE {
        mcs_lock_init((*obj).page_hash_locks.as_mut_ptr().add(i));
        init_list_head((*obj).page_hash.as_mut_ptr().add(i));
    }
}

unsafe fn page_hash_insert(obj: *mut FileObj, page: *mut ObjectPage, hash: usize) {
    list_add(
        &raw mut (*page).list,
        (*obj).page_hash.as_mut_ptr().add(hash),
    );
}

unsafe fn page_hash_remove(page: *mut ObjectPage) {
    list_del(&raw mut (*page).list);
}

unsafe fn page_hash_lookup(obj: *mut FileObj, hash: usize, off: OffT) -> *mut ObjectPage {
    let head = (*obj).page_hash.as_mut_ptr().add(hash);
    let mut entry = (*head).next;

    while entry != head {
        let page = page_from_list(entry);
        if !page_mode_valid((*page).mode as CInt) {
            kprintf(
                PAGE_LOOKUP_FMT.as_ptr().cast(),
                obj,
                off as CULong,
                (*page).mode as CInt,
            );
            kernel_panic(PAGE_LOOKUP_PANIC.as_ptr().cast());
        }
        if (*page).offset == off {
            return page;
        }
        entry = (*entry).next;
    }

    core::ptr::null_mut()
}

unsafe fn page_hash_first(obj: *mut FileObj) -> *mut ObjectPage {
    for i in 0..FILEOBJ_PAGE_HASH_SIZE {
        let head = (*obj).page_hash.as_mut_ptr().add(i);
        if !list_empty(head) {
            return page_from_list((*head).next);
        }
    }
    core::ptr::null_mut()
}

unsafe fn obj_list_lookup(handle: CULong) -> *mut FileObj {
    let head = &raw mut FILEOBJ_LIST;
    let mut entry = (*head).next;

    while entry != head {
        let obj = fileobj_from_list(entry);
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

unsafe fn pager_release(handle: CULong, sref: CULong) -> CInt {
    let mut ctx: X86UserContext = core::mem::zeroed();
    ctx.gpr.rdi = PAGER_REQ_RELEASE;
    ctx.gpr.rsi = handle;
    ctx.gpr.rdx = sref;
    syscall_generic_forwarding(NR_MMAP, &raw mut ctx) as CInt
}

unsafe fn pager_read(handle: CULong, offset: OffT, pgsize: SizeT, phys: CULong) -> CLong {
    let mut ctx: X86UserContext = core::mem::zeroed();
    ctx.gpr.rdi = PAGER_REQ_READ;
    ctx.gpr.rsi = handle;
    ctx.gpr.rdx = offset as CULong;
    ctx.gpr.r10 = pgsize as CULong;
    ctx.gpr.r8 = phys;
    syscall_generic_forwarding(NR_MMAP, &raw mut ctx)
}

unsafe fn pager_write(handle: CULong, offset: OffT, pgsize: SizeT, phys: CULong) -> CLong {
    let mut ctx: X86UserContext = core::mem::zeroed();
    ctx.gpr.rdi = PAGER_REQ_WRITE;
    ctx.gpr.rsi = handle;
    ctx.gpr.rdx = offset as CULong;
    ctx.gpr.r10 = pgsize as CULong;
    ctx.gpr.r8 = phys;
    syscall_generic_forwarding(NR_MMAP, &raw mut ctx)
}

unsafe fn create_premap(obj: *mut FileObj, result_size: SizeT, virt_addr: CULong) {
    let memobj = &raw mut (*obj).memobj;
    if !premap_zerofill((*memobj).flags as CInt) {
        return;
    }

    let nr_pages = premap_npages(result_size);
    let pages_bytes = nr_pages as SizeT * size_of::<*mut c_void>();
    let pages = kernel_alloc(pages_bytes, IHK_MC_AP_NOWAIT).cast::<*mut c_void>();
    if pages.is_null() {
        kprintf(CREATE_PREMAP_ARRAY_FMT.as_ptr().cast());
        return;
    }

    (*memobj).pages = pages;
    (*memobj).nr_pages = nr_pages;
    write_bytes(pages.cast::<u8>(), 0, pages_bytes);

    let thread = current_thread();
    if thread.is_null() || (*thread).proc.is_null() {
        return;
    }
    if ((*(*thread).proc).mpol_flags & MPOL_SHM_PREMAP) == 0 {
        return;
    }

    let nr_nodes = ihk_mc_get_nr_numa_nodes();
    let mut node = nr_nodes / 2;
    for i in 0..nr_pages {
        let page = alloc_user_pages_node(1, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, node, virt_addr);
        if page.is_null() {
            kprintf(CREATE_PREMAP_PAGE_FMT.as_ptr().cast(), i);
            return;
        }
        write(pages.add(i as usize), page);
        mapped_file_rss_add(PAGE_SIZE as SizeT, PAGE_SIZE as SizeT);
        write_bytes(page.cast::<u8>(), 0, PAGE_SIZE as SizeT);
        node += 1;
        if node == nr_nodes {
            node = nr_nodes / 2;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_create(
    fd: CInt,
    objp: *mut *mut Memobj,
    maxprotp: *mut CInt,
    flags: CInt,
    virt_addr: CULong,
) -> CInt {
    if objp.is_null() || maxprotp.is_null() {
        return -EINVAL;
    }
    ensure_globals();

    let mut result: PagerCreateResult = core::mem::zeroed();
    let mut ctx: X86UserContext = core::mem::zeroed();
    ctx.gpr.rdi = PAGER_REQ_CREATE;
    ctx.gpr.rsi = fd as CULong;
    ctx.gpr.rdx = virt_to_phys((&raw mut result).cast::<c_void>());

    let mut error = syscall_generic_forwarding(NR_MMAP, &raw mut ctx) as CInt;
    if error != 0 {
        if error != -ESRCH {
            kprintf(CREATE_FAILED_FMT.as_ptr().cast(), fd, error);
        }
        return error;
    }

    if (result.flags as CInt & MF_HUGETLBFS) != 0 {
        return hugefileobj_pre_create(&raw mut result, objp, maxprotp);
    }

    let mut newobj: *mut FileObj = core::ptr::null_mut();
    let mut node: McsLockNode = core::mem::zeroed();

    mcs_lock_lock(&raw mut fileobj_list_lock, &raw mut node);
    let mut obj = obj_list_lookup(result.handle);
    if obj.is_null() {
        mcs_lock_unlock(&raw mut fileobj_list_lock, &raw mut node);

        newobj = kernel_alloc(size_of::<FileObj>(), IHK_MC_AP_NOWAIT).cast::<FileObj>();
        if newobj.is_null() {
            error = -ENOMEM;
            kprintf(CREATE_KMALLOC_FMT.as_ptr().cast(), fd, error);
            return error;
        }
        write_bytes(newobj.cast::<u8>(), 0, size_of::<FileObj>());
        (*newobj).memobj.ops = fileobj_ops_ptr();
        (*newobj).handle = result.handle;
        page_hash_init(newobj);

        mcs_lock_lock_noirq(&raw mut fileobj_list_lock, &raw mut node);
        obj = obj_list_lookup(result.handle);
    }

    if obj.is_null() {
        obj = newobj;
        list_add(&raw mut (*obj).list, &raw mut FILEOBJ_LIST);
        let obj_flags = base_flags(flags) | result.flags as CInt;
        (*obj).memobj.size = result.size;
        (*obj).memobj.flags = obj_flags as u32;
        (*obj).memobj.status = status_from_flags(obj_flags) as u32;
        ihk_atomic_set(&raw mut (*obj).memobj.refcnt, 1);
        (*obj).sref = 1;

        if result.path[0] != 0 {
            let path = kernel_alloc(PATH_MAX, IHK_MC_AP_NOWAIT).cast::<i8>();
            if path.is_null() {
                error = -ENOMEM;
                kprintf(CREATE_PATH_FMT.as_ptr().cast());
                list_del(&raw mut (*obj).list);
                mcs_lock_unlock_noirq(&raw mut fileobj_list_lock, &raw mut node);
                kernel_free(newobj.cast::<c_void>());
                return error;
            }
            (*obj).memobj.path = path;
            copy_nonoverlapping(result.path.as_ptr(), path, PATH_MAX);
        }

        create_premap(obj, result.size, virt_addr);
        newobj = core::ptr::null_mut();
    } else {
        (*obj).sref = (*obj).sref.wrapping_add(1);
    }

    mcs_lock_unlock_noirq(&raw mut fileobj_list_lock, &raw mut node);
    *objp = &raw mut (*obj).memobj;
    write(maxprotp, result.maxprot);

    if !newobj.is_null() {
        kernel_free(newobj.cast::<c_void>());
    }
    0
}

unsafe extern "C" fn fileobj_free(memobj: *mut Memobj) {
    let obj = memobj.cast::<FileObj>();
    let mut node: McsLockNode = core::mem::zeroed();

    mcs_lock_lock_noirq(&raw mut fileobj_list_lock, &raw mut node);
    list_del(&raw mut (*obj).list);
    mcs_lock_unlock_noirq(&raw mut fileobj_list_lock, &raw mut node);

    loop {
        let page = page_hash_first(obj);
        if page.is_null() {
            break;
        }

        page_hash_remove(page);
        let phys = page_to_phys(page);
        let page_va = phys_to_virt(phys);
        let count = ihk_atomic_read(&raw const (*page).count);
        if count != 1 {
            kprintf(
                FREE_INVALID_COUNT_FMT.as_ptr().cast(),
                count,
                (*page).phys,
                (*memobj).flags as CULong,
            );
        } else if page_unmap(page) != 0 {
            free_user_pages(page_va, 1);
            mapped_file_rss_sub(PAGE_SIZE as SizeT, PAGE_SIZE as SizeT);
            kernel_free(page.cast::<c_void>());
        }
    }

    if premap_zerofill((*memobj).flags as CInt) {
        for i in 0..(*memobj).nr_pages {
            let page = if (*memobj).pages.is_null() {
                core::ptr::null_mut()
            } else {
                *(*memobj).pages.add(i as usize)
            };
            if !page.is_null() {
                mapped_file_rss_sub(PAGE_SIZE as SizeT, PAGE_SIZE as SizeT);
                free_user_pages(page, 1);
            }
        }
        if !(*memobj).pages.is_null() {
            kernel_free((*memobj).pages.cast::<c_void>());
        }
    }

    if !(*memobj).path.is_null() {
        kernel_free((*memobj).path.cast::<c_void>());
    }

    let _ = pager_release((*obj).handle, (*obj).sref);
    kernel_free(obj.cast::<c_void>());
}

unsafe extern "C" fn fileobj_do_pageio(args0: *mut c_void) {
    let args = args0.cast::<PageIoArgs>();
    let obj = (*args).fileobj;
    let off = (*args).objoff;
    let pgsize = (*args).pgsize;
    let hash = page_hash(off);
    let mut node: McsLockNode = core::mem::zeroed();
    let lock = (*obj).page_hash_locks.as_mut_ptr().add(hash);
    let mut attempts = 0;

    mcs_lock_lock(lock, &raw mut node);
    let page = page_hash_lookup(obj, hash, off);
    if page.is_null() {
        mcs_lock_unlock(lock, &raw mut node);
        memobj_unref(&raw mut (*obj).memobj);
        kernel_free(args0);
        return;
    }

    while (*page).mode as CInt == PM_PAGEIO {
        mcs_lock_unlock(lock, &raw mut node);
        attempts += 1;
        if attempts > 49 {
            schedule();
        }
        cpu_pause();
        mcs_lock_lock(lock, &raw mut node);
    }

    if (*page).mode as CInt == PM_WILL_PAGEIO {
        if ((*obj).memobj.flags as CInt & MF_ZEROFILL) != 0 {
            let virt = phys_to_virt(page_to_phys(page));
            write_bytes(virt.cast::<u8>(), 0, PAGE_SIZE as SizeT);
            #[cfg(enable_profile)]
            profile_event_add(PROFILE_PAGE_FAULT_FILE_CLR, PAGE_SIZE);
        } else {
            (*page).mode = PM_PAGEIO as u8;
            let phys = page_to_phys(page);
            mcs_lock_unlock(lock, &raw mut node);
            let ret = pager_read((*obj).handle, off, pgsize, phys);
            mcs_lock_lock(lock, &raw mut node);

            if (*page).mode as CInt != PM_PAGEIO {
                kprintf(
                    PAGEIO_INVALID_FMT.as_ptr().cast(),
                    obj,
                    off as CULong,
                    pgsize,
                    (*page).mode as CInt,
                );
                kernel_panic(PAGEIO_INVALID_PANIC.as_ptr().cast());
            }

            let mode = pageio_mode_after_read(ret, pgsize);
            (*page).mode = mode as u8;
            if mode == PM_PAGEIO_EOF {
                mcs_lock_unlock(lock, &raw mut node);
                memobj_unref(&raw mut (*obj).memobj);
                kernel_free(args0);
                return;
            } else if mode == PM_PAGEIO_ERROR {
                kprintf(
                    PAGEIO_READ_FAILED_FMT.as_ptr().cast(),
                    obj,
                    off as CULong,
                    pgsize,
                    ret,
                );
                mcs_lock_unlock(lock, &raw mut node);
                memobj_unref(&raw mut (*obj).memobj);
                kernel_free(args0);
                return;
            }
        }
        (*page).mode = PM_DONE_PAGEIO as u8;
    }

    mcs_lock_unlock(lock, &raw mut node);
    memobj_unref(&raw mut (*obj).memobj);
    kernel_free(args0);
}

unsafe fn get_premap_page(
    obj: *mut FileObj,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    virt_addr: CULong,
) -> CInt {
    let memobj = &raw mut (*obj).memobj;
    let page_ind = (off >> PAGE_SHIFT) as usize;
    let slot = (*memobj).pages.add(page_ind);

    if (*slot).is_null() {
        let new_virt = alloc_user_pages(1, IHK_MC_AP_NOWAIT | IHK_MC_AP_USER, virt_addr);
        if new_virt.is_null() {
            kprintf(
                GET_PREMAP_ALLOC_FMT.as_ptr().cast(),
                obj,
                off as CULong,
                p2align,
                virt_addr,
                physp as CULong,
                -ENOMEM,
            );
            return -ENOMEM;
        }
        write_bytes(new_virt.cast::<u8>(), 0, PAGE_SIZE as SizeT);
        let atomic_slot = slot.cast::<AtomicPtr<c_void>>();
        match (*atomic_slot).compare_exchange(
            core::ptr::null_mut(),
            new_virt,
            Ordering::SeqCst,
            Ordering::SeqCst,
        ) {
            Ok(_) => {
                mapped_file_rss_add(PAGE_SIZE as SizeT, PAGE_SIZE as SizeT);
            }
            Err(_) => {
                free_user_pages(new_virt, 1);
            }
        }
    }

    let virt = *slot;
    *physp = virt_to_phys(virt);
    0
}

unsafe extern "C" fn fileobj_get_page(
    memobj: *mut Memobj,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    _pflag: *mut CULong,
    virt_addr: CULong,
) -> CInt {
    if memobj.is_null() || physp.is_null() {
        return -EINVAL;
    }

    let obj = memobj.cast::<FileObj>();
    let mut error = validate_p2align(p2align);
    if error != 0 {
        return error;
    }

    #[cfg(enable_profile)]
    profile_event_add(PROFILE_PAGE_FAULT_FILE, PAGE_SIZE);

    if premap_zerofill((*memobj).flags as CInt) {
        return get_premap_page(obj, off, p2align, physp, virt_addr);
    }

    let thread = current_thread();
    if thread.is_null() {
        return -EINVAL;
    }

    let mut node: McsLockNode = core::mem::zeroed();
    let hash = page_hash(off);
    let lock = (*obj).page_hash_locks.as_mut_ptr().add(hash);

    mcs_lock_lock(lock, &raw mut node);
    let mut page = page_hash_lookup(obj, hash, off);
    let mode = if page.is_null() {
        PM_NONE
    } else {
        (*page).mode as CInt
    };

    if page.is_null() || mode == PM_WILL_PAGEIO || mode == PM_PAGEIO {
        error = -ERESTART;
        let args = kernel_alloc(size_of::<PageIoArgs>(), IHK_MC_AP_NOWAIT).cast::<PageIoArgs>();
        if args.is_null() {
            error = -ENOMEM;
            kprintf(
                GET_REGULAR_KMALLOC_FMT.as_ptr().cast(),
                obj,
                off as CULong,
                p2align,
                virt_addr,
                physp as CULong,
                error,
            );
            mcs_lock_unlock(lock, &raw mut node);
            return error;
        }

        if page.is_null() {
            let npages = alloc_npages(p2align);
            let virt = alloc_user_pages(npages, alloc_flags((*memobj).flags as CInt), virt_addr);
            if virt.is_null() {
                error = -ENOMEM;
                kprintf(
                    GET_REGULAR_ALLOC_FMT.as_ptr().cast(),
                    obj,
                    off as CULong,
                    p2align,
                    virt_addr,
                    physp as CULong,
                    error,
                );
                kernel_free(args.cast::<c_void>());
                mcs_lock_unlock(lock, &raw mut node);
                return error;
            }
            let phys = virt_to_phys(virt);
            page = phys_to_page_insert_hash(phys).cast::<ObjectPage>();
            if (*page).mode as CInt != PM_NONE {
                kernel_panic(GET_INVALID_NEW_PAGE.as_ptr().cast());
            }
            (*page).offset = off;
            ihk_atomic_set(&raw mut (*page).count, 1);
            ihk_atomic64_set(&raw mut (*page).mapped, 0);
            page_hash_insert(obj, page, hash);
            (*page).mode = PM_WILL_PAGEIO as u8;
        }

        memobj_ref(memobj);
        (*args).fileobj = obj;
        (*args).objoff = off;
        (*args).pgsize = pageio_pgsize(p2align);
        (*thread).pgio_fp = fileobj_do_pageio as *const () as *mut c_void;
        (*thread).pgio_arg = args.cast::<c_void>();
        mcs_lock_unlock(lock, &raw mut node);
        return error;
    } else if mode == PM_DONE_PAGEIO {
        (*page).mode = PM_MAPPED as u8;
    } else if mode == PM_PAGEIO_EOF {
        error = -ERANGE;
        page_hash_remove(page);
        let virt = phys_to_virt(page_to_phys(page));
        if page_unmap(page) != 0 {
            free_user_pages(virt, 1);
            kernel_free(page.cast::<c_void>());
        }
        mcs_lock_unlock(lock, &raw mut node);
        return error;
    } else if mode == PM_PAGEIO_ERROR {
        error = -EIO;
        page_hash_remove(page);
        let virt = phys_to_virt(page_to_phys(page));
        if page_unmap(page) != 0 {
            free_user_pages(virt, 1);
            kernel_free(page.cast::<c_void>());
        }
        mcs_lock_unlock(lock, &raw mut node);
        return error;
    }

    ihk_atomic_inc(&raw mut (*page).count);
    *physp = page_to_phys(page);
    mcs_lock_unlock(lock, &raw mut node);
    0
}

unsafe extern "C" fn fileobj_flush_page(memobj: *mut Memobj, phys: CULong, pgsize: SizeT) -> CInt {
    if memobj.is_null() {
        return -EINVAL;
    }

    let obj = memobj.cast::<FileObj>();
    if ((*obj).memobj.flags as CInt & MF_ZEROFILL) != 0 {
        return 0;
    }

    let page = phys_to_page(phys);
    if page.is_null() {
        kprintf(FLUSH_MISSING_FMT.as_ptr().cast(), phys);
        return 0;
    }

    let _ = pager_write((*obj).handle, (*page).offset, pgsize, phys);
    0
}

unsafe extern "C" fn fileobj_invalidate_page(
    _memobj: *mut Memobj,
    _phys: CULong,
    _pgsize: SizeT,
) -> CInt {
    kprintf(INVALIDATE_UNSUPPORTED_FMT.as_ptr().cast());
    0
}

unsafe extern "C" fn fileobj_lookup_page(
    memobj: *mut Memobj,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    _pflag: *mut CULong,
) -> CInt {
    if memobj.is_null() || physp.is_null() {
        return -EINVAL;
    }

    let obj = memobj.cast::<FileObj>();
    let error = validate_p2align(p2align);
    if error != 0 {
        return error;
    }

    let hash = page_hash(off);
    let lock = (*obj).page_hash_locks.as_mut_ptr().add(hash);
    let mut node: McsLockNode = core::mem::zeroed();
    mcs_lock_lock(lock, &raw mut node);
    let page = page_hash_lookup(obj, hash, off);
    if page.is_null() {
        mcs_lock_unlock(lock, &raw mut node);
        return -1;
    }
    *physp = page_to_phys(page);
    mcs_lock_unlock(lock, &raw mut node);
    0
}
