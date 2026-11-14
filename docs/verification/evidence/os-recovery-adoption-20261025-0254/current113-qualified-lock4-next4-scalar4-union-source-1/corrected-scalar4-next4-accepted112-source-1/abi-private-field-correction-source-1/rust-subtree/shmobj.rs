use core::{
    ffi::c_void,
    mem::{offset_of, size_of},
    ptr::{copy_nonoverlapping, read_volatile, write, write_bytes, write_volatile},
};

use crate::abi::{
    AbiListHead, CInt, CLong, CULong, IhkAtomic, IhkAtomic64, IhkSpinlock, Memobj, MemobjOps, OffT,
    ShmInfo, ShmLockUser, ShmObj, ShmidDs, SizeT, IHK_MAX_NUM_CPUS, IHK_MAX_NUM_NUMA_NODES,
    IHK_MAX_NUM_PGSIZES,
};

const EINVAL: CInt = 22;
const ENOENT: CInt = 2;
const ENOMEM: CInt = 12;
const ENOSPC: CInt = 28;
const ERANGE: CInt = 34;
const PAGE_SHIFT: CInt = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);
const PM_NONE: CInt = 0x00;
const PM_MAPPED: CInt = 0x07;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_PG_USER: CInt = 1;
const MF_SHMDT_OK: CInt = 0x0002;
const MF_IS_REMOVABLE: CInt = 0x0004;
const MF_SHM: CInt = 0x40000;
const SHM_DEST: CInt = 0o1000;
const SHMID_INDEX_WORDS: usize = 512;
const IHK_OS_PGSIZE_4KB: usize = 0;
const IHK_OS_PGSIZE_2MB: usize = 2;
const IHK_OS_PGSIZE_1GB: usize = 4;
const SHMOBJ_FILE: &[u8] = b"kernel/rust/shmobj.rs\0";
const SHMOBJ_CREATE_ALLOC_FMT: &[u8] = b"shmobj_create(%p %#lx,%p):kmalloc failed. %d\n\0";
const SHMOBJ_FREE_MISSING_FMT: &[u8] = b"shmobj_free called without going through rmid?\0";
const SHMOBJ_DESTROY_COUNT_FMT: &[u8] =
    b"shmobj_destroy: WARNING: page count for phys 0x%lx is invalid\n\0";
const SHMOBJ_DESTROY_RSS_FMT: &[u8] =
    b"%lx-,shmobj_destroy: calling memory_stat_rss_sub(),phys=%lx,size=%ld,pgsize=%ld\n\0";
const SHMOBJ_GET_INVALID_PAGE_FMT: &[u8] =
    b"shmobj_get_page(%p,%#lx,%d,%p):page %p %#lx %d %d %#lx\n\0";
const SHMOBJ_GET_PANIC: &[u8] = b"shmobj_get_page()\0";
const SHMLOCK_USER_FREE_PANIC: &[u8] = b"shmlock_user_free()\0";

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

static mut SHMOBJ_OPS: MemobjOps = MemobjOps {
    free: core::ptr::null_mut(),
    get_page: core::ptr::null_mut(),
    copy_page: core::ptr::null_mut(),
    flush_page: core::ptr::null_mut(),
    invalidate_page: core::ptr::null_mut(),
    lookup_page: core::ptr::null_mut(),
    update_page: core::ptr::null_mut(),
};
static mut SHMOBJ_LIST_LOCK_BODY: IhkSpinlock = IhkSpinlock { head_tail: 0 };
static mut SHMOBJ_LIST_HEAD: AbiListHead = AbiListHead {
    next: core::ptr::null_mut(),
    prev: core::ptr::null_mut(),
};
static mut SHMLOCK_USERS: AbiListHead = AbiListHead {
    next: core::ptr::null_mut(),
    prev: core::ptr::null_mut(),
};
static mut SHMOBJ_GLOBALS_INIT: CInt = 0;

#[no_mangle]
pub static mut shmlock_users_lock_body: IhkSpinlock = IhkSpinlock { head_tail: 0 };

#[no_mangle]
pub static mut the_seq: CInt = 0;

unsafe extern "C" {
    static mut shmid_index: [CULong; SHMID_INDEX_WORDS];
    static mut the_shm_info: ShmInfo;
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
    fn phys_to_page_insert_hash(phys: CULong) -> *mut c_void;
    fn page_unmap(page: *mut ObjectPage) -> CInt;
    fn ihk_mc_pt_lookup_pte(
        pt: *mut c_void,
        virt: *mut c_void,
        pgshift: CInt,
        pgbasep: *mut *mut c_void,
        pgsizep: *mut SizeT,
        p2alignp: *mut CInt,
    ) -> *mut c_void;
    fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock);
    fn __ihk_mc_spinlock_unlock_noirq(lock: *mut IhkSpinlock);
    fn memobj_ref(obj: *mut Memobj) -> CInt;
    fn memobj_unref(obj: *mut Memobj) -> CInt;
    fn ihk_atomic_read(v: *const IhkAtomic) -> CInt;
    fn ihk_atomic_set(v: *mut IhkAtomic, i: CInt);
    fn ihk_atomic_inc(v: *mut IhkAtomic);
    fn ihk_atomic64_read(v: *const IhkAtomic64) -> CLong;
    fn ihk_atomic64_set(v: *mut IhkAtomic64, i: CLong);
    fn ihk_atomic_add_long(i: CLong, v: *mut CLong);
    fn kprintf(format: *const i8, ...) -> CInt;
    #[link_name = "panic"]
    fn kernel_panic(msg: *const i8) -> !;
}

#[inline(always)]
unsafe fn kernel_alloc(size: SizeT, flags: CULong) -> *mut c_void {
    _kmalloc(
        size as CInt,
        flags as CInt,
        SHMOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn kernel_free(ptr: *mut c_void) {
    _kfree(ptr, SHMOBJ_FILE.as_ptr() as *mut i8, line!() as CInt);
}

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
        SHMOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn free_user_pages(ptr: *mut c_void, npages: CInt) {
    _ihk_mc_free_pages(
        ptr,
        npages,
        IHK_MC_PG_USER,
        SHMOBJ_FILE.as_ptr() as *mut i8,
        line!() as CInt,
    );
}

#[inline(always)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[inline(always)]
unsafe fn ensure_globals() {
    if read_volatile(&raw const SHMOBJ_GLOBALS_INIT) == 0 {
        init_list_head(&raw mut SHMOBJ_LIST_HEAD);
        init_list_head(&raw mut SHMLOCK_USERS);
        write_volatile(&raw mut SHMOBJ_GLOBALS_INIT, 1);
    }
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
unsafe fn user_from_chain(entry: *mut AbiListHead) -> *mut ShmLockUser {
    entry
        .cast::<u8>()
        .sub(offset_of!(ShmLockUser, chain))
        .cast()
}

#[inline(always)]
fn init_pgshift(init_pgshift: CInt) -> CInt {
    if init_pgshift != 0 {
        init_pgshift
    } else {
        PAGE_SHIFT
    }
}

#[inline(always)]
fn pgsize(pgshift: CInt) -> SizeT {
    1usize << pgshift
}

#[inline(always)]
fn real_segsz(segsz: SizeT, pgsize: SizeT) -> SizeT {
    segsz.wrapping_add(pgsize - 1) & !(pgsize - 1)
}

#[inline(always)]
fn page_contains_offset(page_offset: OffT, pgshift: CInt, off: OffT) -> bool {
    page_offset <= off && off < page_offset.wrapping_add(1i64 << pgshift)
}

#[inline(always)]
fn page_npages(p2align: CInt) -> CInt {
    1 << p2align
}

#[inline(always)]
fn page_pgshift(p2align: CInt) -> CInt {
    p2align + PAGE_SHIFT
}

#[inline(always)]
fn destroy_page_npages(pgshift: CInt) -> CInt {
    1 << (pgshift - PAGE_SHIFT)
}

#[inline(always)]
fn destroy_page_size(pgshift: CInt) -> SizeT {
    1usize << pgshift
}

#[inline(always)]
fn validate_get(real_segsz: SizeT, off: OffT, p2align: CInt) -> CInt {
    let off_size = off as SizeT;
    if (off as CULong & !PAGE_MASK) != 0 {
        -EINVAL
    } else if real_segsz <= off_size {
        -ERANGE
    } else if real_segsz.wrapping_sub(off_size) < ((PAGE_SIZE as SizeT) << p2align) {
        -ENOSPC
    } else {
        0
    }
}

#[inline(always)]
fn validate_lookup(real_segsz: SizeT, off: OffT) -> CInt {
    if (off as CULong & !PAGE_MASK) != 0 {
        -EINVAL
    } else if real_segsz <= off as SizeT {
        -ERANGE
    } else {
        0
    }
}

#[inline(always)]
fn rusage_pgsize_to_pgtype(pgsize: SizeT) -> usize {
    match pgsize {
        0x1000 => IHK_OS_PGSIZE_4KB,
        0x20_0000 => IHK_OS_PGSIZE_2MB,
        0x4000_0000 => IHK_OS_PGSIZE_1GB,
        _ => IHK_OS_PGSIZE_4KB,
    }
}

#[inline(always)]
unsafe fn memory_stat_rss_sub_inline(size: SizeT, pgsize: SizeT) {
    let slot = core::ptr::addr_of_mut!(rusage.memory_stat_rss)
        .cast::<CLong>()
        .add(rusage_pgsize_to_pgtype(pgsize));
    ihk_atomic_add_long(-(size as CLong), slot);
}

#[inline(always)]
unsafe fn shmobj_ops_ptr() -> *mut MemobjOps {
    let ops = &raw mut SHMOBJ_OPS;
    (*ops).free = shmobj_free as *const () as *mut c_void;
    (*ops).get_page = shmobj_get_page as *const () as *mut c_void;
    (*ops).lookup_page = shmobj_lookup_page as *const () as *mut c_void;
    (*ops).update_page = shmobj_update_page as *const () as *mut c_void;
    ops
}

#[inline(always)]
unsafe fn page_phys(page: *mut ObjectPage) -> CULong {
    if page.is_null() {
        0
    } else {
        (*page).phys
    }
}

#[inline(always)]
unsafe fn page_list_init(obj: *mut ShmObj) {
    init_list_head(&raw mut (*obj).page_list);
    (*obj).page_list_lock.head_tail = 0;
}

#[inline(always)]
unsafe fn page_list_lock(obj: *mut ShmObj) {
    __ihk_mc_spinlock_lock_noirq(&raw mut (*obj).page_list_lock);
}

#[inline(always)]
unsafe fn page_list_unlock(obj: *mut ShmObj) {
    __ihk_mc_spinlock_unlock_noirq(&raw mut (*obj).page_list_lock);
}

#[inline(always)]
unsafe fn page_list_insert(obj: *mut ShmObj, page: *mut ObjectPage) {
    list_add(&raw mut (*page).list, &raw mut (*obj).page_list);
}

#[inline(always)]
unsafe fn page_list_remove(_obj: *mut ShmObj, page: *mut ObjectPage) {
    list_del(&raw mut (*page).list);
}

#[inline(always)]
unsafe fn page_list_first(obj: *mut ShmObj) -> *mut ObjectPage {
    let head = &raw mut (*obj).page_list;
    if list_empty(head) {
        core::ptr::null_mut()
    } else {
        page_from_list((*head).next)
    }
}

unsafe fn page_list_lookup(obj: *mut ShmObj, off: OffT) -> *mut ObjectPage {
    let head = &raw mut (*obj).page_list;
    let mut entry = (*head).next;

    while entry != head {
        let page = page_from_list(entry);
        if page_contains_offset((*page).offset, (*page).pgshift, off) {
            return page;
        }
        entry = (*entry).next;
    }

    core::ptr::null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn to_shmobj(memobj: *mut Memobj) -> *mut ShmObj {
    memobj.cast()
}

#[no_mangle]
pub unsafe extern "C" fn shmobj_list_lock() {
    ensure_globals();
    __ihk_mc_spinlock_lock_noirq(&raw mut SHMOBJ_LIST_LOCK_BODY);
}

#[no_mangle]
pub unsafe extern "C" fn shmobj_list_unlock() {
    __ihk_mc_spinlock_unlock_noirq(&raw mut SHMOBJ_LIST_LOCK_BODY);
}

#[no_mangle]
pub unsafe extern "C" fn shmlock_users_lock() {
    __ihk_mc_spinlock_lock_noirq(&raw mut shmlock_users_lock_body);
}

#[no_mangle]
pub unsafe extern "C" fn shmlock_users_unlock() {
    __ihk_mc_spinlock_unlock_noirq(&raw mut shmlock_users_lock_body);
}

#[no_mangle]
pub unsafe extern "C" fn shmlock_user_free(user: *mut ShmLockUser) {
    if user.is_null() {
        return;
    }
    if (*user).locked != 0 {
        kernel_panic(SHMLOCK_USER_FREE_PANIC.as_ptr().cast());
    }
    list_del(&raw mut (*user).chain);
    kernel_free(user.cast());
}

#[no_mangle]
pub unsafe extern "C" fn shmlock_user_get(ruid: u32, userp: *mut *mut ShmLockUser) -> CInt {
    ensure_globals();
    if userp.is_null() {
        return -EINVAL;
    }

    let head = &raw mut SHMLOCK_USERS;
    let mut entry = (*head).next;
    while entry != head {
        let user = user_from_chain(entry);
        if (*user).ruid == ruid {
            *userp = user;
            return 0;
        }
        entry = (*entry).next;
    }

    let user = kernel_alloc(size_of::<ShmLockUser>(), IHK_MC_AP_NOWAIT).cast::<ShmLockUser>();
    if user.is_null() {
        return -ENOMEM;
    }

    write_bytes(user.cast::<u8>(), 0, size_of::<ShmLockUser>());
    (*user).ruid = ruid;
    (*user).locked = 0;
    list_add(&raw mut (*user).chain, head);
    *userp = user;
    0
}

#[no_mangle]
pub unsafe extern "C" fn shmobj_create(ds: *mut ShmidDs, objp: *mut *mut Memobj) -> CInt {
    ensure_globals();
    if ds.is_null() || objp.is_null() {
        return -EINVAL;
    }

    let pgshift = init_pgshift((*ds).init_pgshift);
    let pgsize = pgsize(pgshift);
    let obj = kernel_alloc(size_of::<ShmObj>(), IHK_MC_AP_NOWAIT).cast::<ShmObj>();
    if obj.is_null() {
        let error = -ENOMEM;
        kprintf(
            SHMOBJ_CREATE_ALLOC_FMT.as_ptr().cast(),
            ds,
            (*ds).shm_segsz,
            objp,
            error,
        );
        return error;
    }

    write_bytes(obj.cast::<u8>(), 0, size_of::<ShmObj>());
    (*obj).memobj.ops = shmobj_ops_ptr();
    (*obj).memobj.flags = MF_SHM as u32;
    (*obj).memobj.size = (*ds).shm_segsz;
    (*obj).memobj.refcnt.counter = 1;
    copy_nonoverlapping(ds, &raw mut (*obj).ds, 1);
    (*obj).ds.shm_perm.seq = read_volatile(&raw const the_seq) as u16;
    write_volatile(
        &raw mut the_seq,
        read_volatile(&raw const the_seq).wrapping_add(1),
    );
    (*obj).ds.init_pgshift = 0;
    (*obj).index = -1;
    (*obj).pgshift = pgshift;
    (*obj).real_segsz = real_segsz((*obj).ds.shm_segsz, pgsize);
    page_list_init(obj);

    write(objp, &raw mut (*obj).memobj);
    0
}

#[no_mangle]
pub unsafe extern "C" fn shmobj_create_indexed(ds: *mut ShmidDs, objp: *mut *mut ShmObj) -> CInt {
    if objp.is_null() {
        return -EINVAL;
    }

    let mut memobj: *mut Memobj = core::ptr::null_mut();
    let error = shmobj_create(ds, &raw mut memobj);
    if error == 0 {
        (*memobj).flags |= (MF_SHMDT_OK | MF_IS_REMOVABLE) as u32;
        write(objp, to_shmobj(memobj));
    }
    error
}

unsafe fn shmobj_destroy(obj: *mut ShmObj) {
    if !(*obj).user.is_null() {
        let user = (*obj).user;
        (*obj).user = core::ptr::null_mut();
        shmlock_users_lock();
        (*user).locked = (*user).locked.wrapping_sub((*obj).real_segsz);
        if (*user).locked == 0 {
            shmlock_user_free(user);
        }
        shmlock_users_unlock();
    }

    loop {
        let page = page_list_first(obj);
        if page.is_null() {
            break;
        }

        page_list_remove(obj, page);
        let phys = page_phys(page);
        let page_va = phys_to_virt(phys);
        let pgshift = (*page).pgshift;
        let npages = destroy_page_npages(pgshift);
        let count = ihk_atomic_read(&raw const (*page).count);

        if count != 1 {
            kprintf(SHMOBJ_DESTROY_COUNT_FMT.as_ptr().cast(), (*page).phys);
        } else if page_unmap(page) != 0 {
            let free_pgsize = destroy_page_size(pgshift);
            let free_size = destroy_page_size(pgshift);
            free_user_pages(page_va, npages);
            kprintf(
                SHMOBJ_DESTROY_RSS_FMT.as_ptr().cast(),
                phys,
                phys,
                free_size as CLong,
                free_pgsize as CLong,
            );
            memory_stat_rss_sub_inline(free_size, free_pgsize);
            kernel_free(page.cast());
        }
    }

    if (*obj).index < 0 {
        kernel_free(obj.cast());
    } else {
        let word = ((*obj).index / 64) as usize;
        let mask = 1u64 << ((*obj).index % 64);
        list_del(&raw mut (*obj).chain);
        the_shm_info.used_ids -= 1;
        let slot = core::ptr::addr_of_mut!(shmid_index)
            .cast::<CULong>()
            .add(word);
        write_volatile(slot, read_volatile(slot) & !mask);
        kernel_free(obj.cast());
    }
}

unsafe extern "C" fn shmobj_free(memobj: *mut Memobj) {
    let obj = to_shmobj(memobj);
    shmobj_list_lock();
    if ((*obj).ds.shm_perm.mode as CInt & SHM_DEST) == 0 {
        kprintf(SHMOBJ_FREE_MISSING_FMT.as_ptr().cast());
    }
    shmobj_destroy(obj);
    shmobj_list_unlock();
}

unsafe extern "C" fn shmobj_get_page(
    memobj: *mut Memobj,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    _pflag: *mut CULong,
    virt_addr: CULong,
) -> CInt {
    let obj = to_shmobj(memobj);
    if memobj.is_null() || obj.is_null() || physp.is_null() {
        return -EINVAL;
    }

    memobj_ref(memobj);
    let mut error = validate_get((*obj).real_segsz, off, p2align);
    if error != 0 {
        memobj_unref(memobj);
        return error;
    }

    page_list_lock(obj);
    let mut page = page_list_lookup(obj, off);
    if page.is_null() {
        let npages = page_npages(p2align);
        let virt = alloc_user_pages(npages, p2align, IHK_MC_AP_NOWAIT, virt_addr);
        if virt.is_null() {
            page_list_unlock(obj);
            memobj_unref(memobj);
            return -ENOMEM;
        }

        let phys = virt_to_phys(virt);
        page = phys_to_page_insert_hash(phys).cast::<ObjectPage>();
        if (*page).mode as CInt != PM_NONE {
            kprintf(
                SHMOBJ_GET_INVALID_PAGE_FMT.as_ptr().cast(),
                memobj,
                off,
                p2align,
                physp,
                page,
                page_phys(page),
                (*page).mode as CInt,
                ihk_atomic_read(&raw const (*page).count),
                (*page).offset as CULong,
            );
            kernel_panic(SHMOBJ_GET_PANIC.as_ptr().cast());
        }

        write_bytes(virt.cast::<u8>(), 0, (npages as SizeT) * PAGE_SIZE as SizeT);
        (*page).mode = PM_MAPPED as u8;
        (*page).offset = off;
        (*page).pgshift = page_pgshift(p2align);
        ihk_atomic_set(&raw mut (*page).count, 1);
        ihk_atomic64_set(&raw mut (*page).mapped, 0);
        page_list_insert(obj, page);
    }
    page_list_unlock(obj);

    ihk_atomic_inc(&raw mut (*page).count);
    *physp = page_phys(page);
    error = 0;

    memobj_unref(memobj);
    error
}

unsafe extern "C" fn shmobj_lookup_page(
    memobj: *mut Memobj,
    off: OffT,
    _p2align: CInt,
    physp: *mut CULong,
    _pflag: *mut CULong,
) -> CInt {
    let obj = to_shmobj(memobj);
    if memobj.is_null() || obj.is_null() {
        return -EINVAL;
    }

    memobj_ref(memobj);
    let mut error = validate_lookup((*obj).real_segsz, off);
    if error != 0 {
        memobj_unref(memobj);
        return error;
    }

    page_list_lock(obj);
    let page = page_list_lookup(obj, off);
    page_list_unlock(obj);
    if page.is_null() {
        memobj_unref(memobj);
        return -ENOENT;
    }

    if !physp.is_null() {
        *physp = page_phys(page);
    }
    error = 0;
    memobj_unref(memobj);
    error
}

unsafe extern "C" fn shmobj_update_page(
    memobj: *mut Memobj,
    pt: *mut c_void,
    orig_page: *mut ObjectPage,
    vaddr: *mut c_void,
) -> CInt {
    let obj = to_shmobj(memobj);
    if memobj.is_null() {
        return -EINVAL;
    }

    memobj_ref(memobj);
    if pt.is_null() || orig_page.is_null() || vaddr.is_null() {
        memobj_unref(memobj);
        return -ENOENT;
    }

    let base_phys = page_phys(orig_page);
    let mut pte_size: SizeT = 0;
    let mut p2align: CInt = 0;
    let mut pte = ihk_mc_pt_lookup_pte(
        pt,
        vaddr,
        0,
        core::ptr::null_mut(),
        &raw mut pte_size,
        &raw mut p2align,
    );
    if pte.is_null() {
        memobj_unref(memobj);
        return -ENOENT;
    }

    let orig_pgsize = 1usize << (*orig_page).pgshift;
    (*orig_page).pgshift = page_pgshift(p2align);

    let mut page_off = pte_size;
    while page_off < orig_pgsize {
        pte = ihk_mc_pt_lookup_pte(
            pt,
            (vaddr as CULong).wrapping_add(page_off as CULong) as *mut c_void,
            0,
            core::ptr::null_mut(),
            &raw mut pte_size,
            &raw mut p2align,
        );
        if pte.is_null() {
            memobj_unref(memobj);
            return -ENOENT;
        }

        let phys = base_phys.wrapping_add(page_off as CULong);
        let page = phys_to_page_insert_hash(phys).cast::<ObjectPage>();
        (*page).mode = (*orig_page).mode;
        (*page).offset = (*orig_page).offset.wrapping_add(page_off as OffT);
        (*page).pgshift = page_pgshift(p2align);
        ihk_atomic_set(
            &raw mut (*page).count,
            ihk_atomic_read(&raw const (*orig_page).count),
        );
        ihk_atomic64_set(
            &raw mut (*page).mapped,
            ihk_atomic64_read(&raw const (*orig_page).mapped),
        );
        page_list_insert(obj, page);

        page_off = page_off.wrapping_add(pte_size);
    }

    memobj_unref(memobj);
    0
}
