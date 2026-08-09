use core::{
    ffi::c_void,
    mem::{size_of, transmute},
    ptr::{read_volatile, write, write_volatile},
};

use crate::abi::{
    CInt, CLong, CULong, Coretable, Elf64Ehdr, Elf64Phdr, ElfCoreNote, ElfPrpsinfo64,
    ElfPrstatus64, IkcScdPacket, IkcScdPacketSysfs, IkcScdPacketTraditional, Memobj, OffT,
    ProcfsRead, SizeT, SysfsBitmapParam, SysfsReqCreateParam, SysfsReqLookupParam,
    SysfsReqMkdirParam, SysfsReqSetupParam, SysfsReqSymlinkParam, SysfsReqUnlinkParam,
};

const ENOENT: CInt = 2;
const EINTR: CInt = 4;
const EIO: CInt = 5;
const EAGAIN: CInt = 11;
const ENXIO: CInt = 6;
const ENOMEM: CInt = 12;
const EFAULT: CInt = 14;
const EINVAL: CInt = 22;
const EFBIG: CInt = 27;
const ENOSPC: CInt = 28;
const ERANGE: CInt = 34;
const ENAMETOOLONG: CInt = 36;
const ERESTART: CInt = 85;

const PAGE_SHIFT: CInt = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);
const PAGE_P2ALIGN: CInt = 0;
const PTL1_SHIFT: CInt = 12;
const AUXV_LEN: CInt = 38;

const PM_NONE: CInt = 0x00;
const PM_WILL_PAGEIO: CInt = 0x02;
const PM_PAGEIO: CInt = 0x03;
const PM_DONE_PAGEIO: CInt = 0x04;
const PM_PAGEIO_EOF: CInt = 0x05;
const PM_PAGEIO_ERROR: CInt = 0x06;
const PM_MAPPED: CInt = 0x07;

const MF_HAS_PAGER: CInt = 0x0001;
const MF_SHMDT_OK: CInt = 0x0002;
const MF_IS_REMOVABLE: CInt = 0x0004;
const MF_PREFETCH: CInt = 0x0008;
const MF_ZEROFILL: CInt = 0x0010;
const MF_REG_FILE: CInt = 0x1000;
const MF_DEV_FILE: CInt = 0x2000;
const MF_PREMAP: CInt = 0x8000;
const MF_XPMEM: CInt = 0x10000;
const MF_ZEROOBJ: CInt = 0x20000;
const MF_SHM: CInt = 0x40000;
const MF_HUGETLBFS: CInt = 0x100000;
const MF_PRIVATE: CInt = 0x200000;
const MF_REMAP_FILE_PAGES: CInt = 0x400000;

const SHM_DEST: CInt = 0o1000;

const MAP_PRIVATE: CInt = 0x02;

const MEMOBJ_READY: CInt = 0;
const MEMOBJ_TO_BE_PREFETCHED: CInt = 1;

const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_AP_USER: CULong = 0x001000;

const FILEOBJ_PAGE_HASH_MASK: CInt = 511;
const FILEOBJ_PAGE_ACTION_START_IO: CInt = 1;
const FILEOBJ_PAGE_ACTION_MAP_DONE: CInt = 2;
const FILEOBJ_PAGE_ACTION_USE_EXISTING: CInt = 3;
const FILEOBJ_PAGE_ACTION_ERROR: CInt = 4;
const FILEOBJ_LOG_PAGEIO_SCHEDULE: CInt = 4;
const FILEOBJ_LOG_PAGEIO_EOF: CInt = 5;
const FILEOBJ_LOG_PAGEIO_READ_ERROR: CInt = 6;
const FILEOBJ_LOG_FREE_INVALID_COUNT: CInt = 7;
const FILEOBJ_LOG_FREE_RSS_SUB: CInt = 8;
const FILEOBJ_LOG_FREE_RELEASE_ERROR: CInt = 9;
const FILEOBJ_LOG_FREE_DONE: CInt = 10;
const FILEOBJ_CREATE_LOG_PATH_ALLOC_FAILED: CInt = 11;
const FILEOBJ_CREATE_LOG_PREMAP_START: CInt = 12;
const FILEOBJ_CREATE_LOG_PREMAP_ARRAY_ALLOC_FAILED: CInt = 13;
const FILEOBJ_CREATE_LOG_PREMAP_PAGE_ALLOC_FAILED: CInt = 14;
const FILEOBJ_CREATE_LOG_PREMAP_RSS_ADD: CInt = 15;
const FILEOBJ_CREATE_LOG_PREMAP_INTERLEAVED_DONE: CInt = 16;
const FILEOBJ_GET_LOG_PREMAP_ALLOC_FAILED: CInt = 17;
const FILEOBJ_GET_LOG_PREMAP_ALLOCATED: CInt = 18;
const FILEOBJ_GET_LOG_PREMAP_RSS_ADD: CInt = 19;
const FILEOBJ_GET_LOG_PREMAP_RESOLVED: CInt = 20;
const FILEOBJ_GET_LOG_KMALLOC_FAILED: CInt = 21;
const FILEOBJ_GET_LOG_ALLOC_FAILED: CInt = 22;
const FILEOBJ_GET_LOG_NEW_PAGE: CInt = 23;
const FILEOBJ_GET_LOG_MAP_DONE: CInt = 24;
const FILEOBJ_GET_LOG_USE_PAGE: CInt = 25;
const FILEOBJ_GET_LOG_RETURN: CInt = 26;

const PFN_VALID: CULong = 1 << 63;
const PFN_PRESENT: CULong = 1;
const PFN_PFN: CULong = ((1 << 56) - 1) & !(PAGE_SIZE - 1);
const VR_WRITE_COMBINED: CULong = 0x400;

const SYSFS_SNOOPING_OPS_D32: CLong = 1;
const SYSFS_SNOOPING_OPS_D64: CLong = 2;
const SYSFS_SNOOPING_OPS_U32: CLong = 3;
const SYSFS_SNOOPING_OPS_U64: CLong = 4;
const SYSFS_SNOOPING_OPS_S: CLong = 5;
const SYSFS_SNOOPING_OPS_PBL: CLong = 6;
const SYSFS_SNOOPING_OPS_PB: CLong = 7;
const SYSFS_SNOOPING_OPS_U32K: CLong = 8;
const SYSFS_SPECIAL_KIND_DIRECT: CInt = 1;
const SYSFS_SPECIAL_KIND_STRING: CInt = 2;
const SYSFS_SPECIAL_KIND_BITMAP: CInt = 3;

const PF_WRITE: CULong = 1 << 1;
const PF_USER: CULong = 1 << 2;
const PF_POPULATE: CULong = 1 << 30;

const PS_RUNNING: CInt = 0x1;
const PS_INTERRUPTIBLE: CInt = 0x2;
const PS_UNINTERRUPTIBLE: CInt = 0x4;
const PS_ZOMBIE: CInt = 0x8;
const PS_EXITED: CInt = 0x10;
const PS_STOPPED: CInt = 0x20;
const PS_TRACED: CInt = 0x40;

const ELFCLASS64: u8 = 2;
const ELFDATA2LSB: u8 = 1;
const ELF_VERSION_CURRENT: u8 = 1;
const ELFOSABI_NONE: u8 = 0;
const ELF_ABIVERSION_NONE: u8 = 0;
const ET_CORE: u16 = 4;
const EM_X86_64: u16 = 62;
const EV_CURRENT: u32 = 1;
const NT_PRSTATUS: u32 = 1;
const NT_PRPSINFO: u32 = 3;
const NT_AUXV: u32 = 6;
const PT_LOAD: u32 = 1;
const PT_NOTE: u32 = 4;
const PF_X: u32 = 1;
const PF_W: u32 = 2;
const PF_R: u32 = 4;
const VR_RESERVED: CULong = 0x2;
const VR_MEMTYPE_UC: CULong = 0x0100_0000;
const VR_DONTDUMP: CULong = 0x2000_0000;

const PROCFS_STATUS_RUNNING: CInt = 0;
const PROCFS_STATUS_STOPPED: CInt = 1;
const PROCFS_STATUS_TRACED: CInt = 2;
const PROCFS_STATUS_EXITED: CInt = 3;
const PROCFS_MAPS_PATH_NONE: CInt = 0;
const PROCFS_MAPS_PATH_VDSO: CInt = 1;
const PROCFS_MAPS_PATH_VVAR: CInt = 2;
const PROCFS_MAPS_PATH_STACK: CInt = 3;
const PROCFS_MAPS_PATH_HEAP: CInt = 4;
const PROCFS_LOCK_ACTION_BACKLOG: CInt = 1;
const PROCFS_LOCK_ACTION_EAGAIN: CInt = 2;
const PROCFS_ENTRY_UNKNOWN: CInt = 0;
const PROCFS_ENTRY_MCKERNEL: CInt = 1;
const PROCFS_ENTRY_STAT: CInt = 2;
const PROCFS_ENTRY_CPUINFO: CInt = 3;
const PROCFS_ENTRY_MEM: CInt = 4;
const PROCFS_ENTRY_MAPS: CInt = 5;
const PROCFS_ENTRY_PAGEMAP: CInt = 6;
const PROCFS_ENTRY_STATUS: CInt = 7;
const PROCFS_ENTRY_AUXV: CInt = 8;
const PROCFS_ENTRY_CMDLINE: CInt = 9;
const PROCFS_ENTRY_COMM: CInt = 10;

const VR_STACK: CULong = 0x1;
const VR_AP_USER: CULong = 0x4;
const VR_DEMAND_PAGING: CULong = 0x1000;
const VR_PRIVATE: CULong = 0x2000;
const VR_LOCKED: CULong = 0x4000;
const VR_PROT_READ: CULong = 0x00010000;
const VR_PROT_WRITE: CULong = 0x00020000;
const VR_PROT_EXEC: CULong = 0x00040000;

const SYSFS_HANDLER_UNKNOWN: CInt = 0;
const SYSFS_HANDLER_SHOW: CInt = 1;
const SYSFS_HANDLER_STORE: CInt = 2;
const SYSFS_HANDLER_RELEASE: CInt = 3;
const SYSFS_REQUEST_PHASE_NONE: CInt = 0;
const SYSFS_REQUEST_PHASE_SEND: CInt = 1;
const SYSFS_REQUEST_PHASE_RESPONSE: CInt = 2;
const SYSFS_INIT_STAGE_NONE: CInt = 0;
const SYSFS_INIT_STAGE_SIZE: CInt = 1;
const SYSFS_INIT_STAGE_DATA_ALLOC: CInt = 2;
const SYSFS_INIT_STAGE_PARAM_ALLOC: CInt = 3;
const SYSFS_INIT_STAGE_REQUEST: CInt = 4;
const SYSFS_REQUEST_LOG_SEND_ERROR: CInt = 1;
const SYSFS_REQUEST_LOG_RESPONSE_ERROR: CInt = 2;
const SYSFSS_REQ_LOG_CALLBACK_ERROR: CInt = 1;
const SYSFSS_REQ_LOG_SEND_ERROR: CInt = 2;
const SYSFSS_REQ_LOG_PACKET_ERROR: CInt = 3;
const SYSFSS_REQ_LOG_DEBUG: CInt = 4;
const SCD_MSG_SYSFS_REQ_CREATE: CInt = 0x30;
const SCD_MSG_SYSFS_REQ_MKDIR: CInt = 0x32;
const SCD_MSG_SYSFS_REQ_SYMLINK: CInt = 0x34;
const SCD_MSG_SYSFS_REQ_LOOKUP: CInt = 0x36;
const SCD_MSG_SYSFS_REQ_UNLINK: CInt = 0x38;
const SCD_MSG_SYSFS_REQ_SHOW: CInt = 0x3a;
const SCD_MSG_SYSFS_RESP_SHOW: CInt = 0x3b;
const SCD_MSG_SYSFS_REQ_STORE: CInt = 0x3c;
const SCD_MSG_SYSFS_RESP_STORE: CInt = 0x3d;
const SCD_MSG_SYSFS_REQ_RELEASE: CInt = 0x3e;
const SCD_MSG_SYSFS_RESP_RELEASE: CInt = 0x3f;
const SCD_MSG_SYSFS_REQ_SETUP: CInt = 0x40;
const SCD_MSG_PROCFS_ANSWER: CInt = 0x13;
const SCD_MSG_PROCFS_TID_CREATE: CInt = 0x44;
const SCD_MSG_PROCFS_RELEASE: CInt = 0x15;
const MLOCKADDRS_SIZE: CInt = 128;
const MPOL_SHM_PREMAP: CULong = 0x08;

#[inline(always)]
fn page_offset(value: CULong) -> CULong {
    value & (PAGE_SIZE - 1)
}

unsafe fn cstr_eq(mut actual: *const u8, expected: &[u8]) -> bool {
    if actual.is_null() {
        return false;
    }

    let mut i = 0;
    loop {
        let ch = *actual;
        let want = if i < expected.len() { expected[i] } else { 0 };

        if ch != want {
            return false;
        }
        if ch == 0 {
            return true;
        }

        actual = actual.add(1);
        i += 1;
    }
}

#[no_mangle]
pub extern "C" fn memobj_unref_should_free_result(refcnt: CInt) -> CInt {
    (refcnt == 0) as CInt
}

#[no_mangle]
pub extern "C" fn memobj_op_present_result(op: CULong) -> CInt {
    (op != 0) as CInt
}

#[no_mangle]
pub extern "C" fn memobj_missing_page_op_result() -> CInt {
    -ENXIO
}

#[no_mangle]
pub extern "C" fn memobj_missing_copy_page_result() -> CULong {
    (-(ENXIO as CLong)) as CULong
}

#[no_mangle]
pub extern "C" fn memobj_default_page_op_result() -> CInt {
    0
}

#[no_mangle]
pub extern "C" fn memobj_has_pager_flags_result(flags: u32) -> CInt {
    ((flags & MF_HAS_PAGER as u32) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn memobj_is_removable_flags_result(flags: u32) -> CInt {
    ((flags & MF_IS_REMOVABLE as u32) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn memobj_flushable_page_result(has_page: CInt, page_in_memobj: CInt) -> CInt {
    (has_page != 0 && page_in_memobj != 0) as CInt
}

#[no_mangle]
pub extern "C" fn memobj_flushable_obj_result(has_memobj: CInt, flags: u32) -> CInt {
    (has_memobj != 0 && (flags & (MF_ZEROFILL | MF_PRIVATE) as u32) == 0) as CInt
}

#[no_mangle]
pub extern "C" fn memobj_is_freeable_result(has_memobj: CInt, flags: u32) -> CInt {
    (has_memobj == 0 || (flags & MF_XPMEM as u32) == 0) as CInt
}

#[no_mangle]
pub extern "C" fn memobj_callable_remap_file_pages_result(has_memobj: CInt, flags: u32) -> CInt {
    (has_memobj != 0 && (flags & MF_REMAP_FILE_PAGES as u32) != 0) as CInt
}

type MemobjGetPageFn =
    unsafe extern "C" fn(*mut Memobj, OffT, CInt, *mut CULong, *mut CULong, CULong) -> CInt;
type MemobjCopyPageFn = unsafe extern "C" fn(*mut Memobj, CULong, CInt) -> CULong;
type MemobjPageOpFn = unsafe extern "C" fn(*mut Memobj, CULong, SizeT) -> CInt;
type MemobjLookupPageFn =
    unsafe extern "C" fn(*mut Memobj, OffT, CInt, *mut CULong, *mut CULong) -> CInt;
type MemobjUpdatePageFn =
    unsafe extern "C" fn(*mut Memobj, *mut c_void, *mut c_void, *mut c_void) -> CInt;

#[no_mangle]
pub unsafe extern "C" fn memobj_get_page(
    obj: *mut Memobj,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    pflag: *mut CULong,
    virt_addr: CULong,
) -> CInt {
    let op = (*(*obj).ops).get_page;
    if memobj_op_present_result(op as CULong) != 0 {
        let get_page: MemobjGetPageFn = transmute(op);
        return get_page(obj, off, p2align, physp, pflag, virt_addr);
    }
    memobj_missing_page_op_result()
}

#[no_mangle]
pub unsafe extern "C" fn memobj_copy_page(
    obj: *mut Memobj,
    orgphys: CULong,
    p2align: CInt,
) -> CULong {
    let op = (*(*obj).ops).copy_page;
    if memobj_op_present_result(op as CULong) != 0 {
        let copy_page: MemobjCopyPageFn = transmute(op);
        return copy_page(obj, orgphys, p2align);
    }
    memobj_missing_copy_page_result()
}

#[no_mangle]
pub unsafe extern "C" fn memobj_flush_page(obj: *mut Memobj, phys: CULong, pgsize: SizeT) -> CInt {
    let op = (*(*obj).ops).flush_page;
    if memobj_op_present_result(op as CULong) != 0 {
        let flush_page: MemobjPageOpFn = transmute(op);
        return flush_page(obj, phys, pgsize);
    }
    memobj_default_page_op_result()
}

#[no_mangle]
pub unsafe extern "C" fn memobj_invalidate_page(
    obj: *mut Memobj,
    phys: CULong,
    pgsize: SizeT,
) -> CInt {
    let op = (*(*obj).ops).invalidate_page;
    if memobj_op_present_result(op as CULong) != 0 {
        let invalidate_page: MemobjPageOpFn = transmute(op);
        return invalidate_page(obj, phys, pgsize);
    }
    memobj_default_page_op_result()
}

#[no_mangle]
pub unsafe extern "C" fn memobj_lookup_page(
    obj: *mut Memobj,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    pflag: *mut CULong,
) -> CInt {
    let op = (*(*obj).ops).lookup_page;
    if memobj_op_present_result(op as CULong) != 0 {
        let lookup_page: MemobjLookupPageFn = transmute(op);
        return lookup_page(obj, off, p2align, physp, pflag);
    }
    memobj_missing_page_op_result()
}

#[no_mangle]
pub unsafe extern "C" fn memobj_update_page(
    obj: *mut Memobj,
    pt: *mut c_void,
    orig_page: *mut c_void,
    vaddr: *mut c_void,
) -> CInt {
    let op = (*(*obj).ops).update_page;
    if memobj_op_present_result(op as CULong) != 0 {
        let update_page: MemobjUpdatePageFn = transmute(op);
        return update_page(obj, pt, orig_page, vaddr);
    }
    memobj_missing_page_op_result()
}

#[no_mangle]
pub unsafe extern "C" fn memobj_has_pager(obj: *mut Memobj) -> CInt {
    memobj_has_pager_flags_result((*obj).flags)
}

#[no_mangle]
pub unsafe extern "C" fn memobj_is_removable(obj: *mut Memobj) -> CInt {
    memobj_is_removable_flags_result((*obj).flags)
}

#[no_mangle]
pub unsafe extern "C" fn is_flushable(page: *mut c_void, memobj: *mut Memobj) -> CInt {
    let page_in_memobj = if page.is_null() {
        0
    } else {
        crate::page_helpers::page_is_in_memobj(page.cast())
    };

    if memobj_flushable_page_result((!page.is_null()) as CInt, page_in_memobj) == 0 {
        return 0;
    }

    memobj_flushable_obj_result(
        (!memobj.is_null()) as CInt,
        if memobj.is_null() { 0 } else { (*memobj).flags },
    )
}

#[no_mangle]
pub unsafe extern "C" fn is_freeable(memobj: *mut Memobj) -> CInt {
    memobj_is_freeable_result(
        (!memobj.is_null()) as CInt,
        if memobj.is_null() { 0 } else { (*memobj).flags },
    )
}

#[no_mangle]
pub unsafe extern "C" fn is_callable_remap_file_pages(memobj: *mut Memobj) -> CInt {
    memobj_callable_remap_file_pages_result(
        (!memobj.is_null()) as CInt,
        if memobj.is_null() { 0 } else { (*memobj).flags },
    )
}

#[no_mangle]
pub extern "C" fn fileobj_page_hash_result(off: OffT) -> CInt {
    ((off >> PAGE_SHIFT) as CInt) & FILEOBJ_PAGE_HASH_MASK
}

#[no_mangle]
pub extern "C" fn fileobj_page_mode_valid_result(mode: CInt) -> CInt {
    (mode == PM_WILL_PAGEIO
        || mode == PM_PAGEIO
        || mode == PM_DONE_PAGEIO
        || mode == PM_PAGEIO_EOF
        || mode == PM_PAGEIO_ERROR
        || mode == PM_MAPPED) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_lookup_ref_keep_result(refcnt_after_inc: CInt) -> CInt {
    (refcnt_after_inc > 1) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_create_base_flags_result(mmap_flags: CInt) -> CInt {
    MF_HAS_PAGER
        | MF_REG_FILE
        | MF_REMAP_FILE_PAGES
        | if (mmap_flags & MAP_PRIVATE) != 0 {
            MF_PRIVATE
        } else {
            0
        }
}

#[no_mangle]
pub extern "C" fn fileobj_apply_result_flags_result(base_flags: CInt, pager_flags: CInt) -> CInt {
    base_flags | pager_flags
}

#[no_mangle]
pub extern "C" fn fileobj_status_from_flags_result(flags: CInt) -> CInt {
    if (flags & MF_PREFETCH) != 0 {
        MEMOBJ_TO_BE_PREFETCHED
    } else {
        MEMOBJ_READY
    }
}

#[no_mangle]
pub extern "C" fn fileobj_hugetlbfs_result(flags: CInt) -> CInt {
    ((flags & MF_HUGETLBFS) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_premap_zerofill_result(flags: CInt) -> CInt {
    ((flags & MF_PREMAP) != 0 && (flags & MF_ZEROFILL) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_premap_npages_result(size: SizeT) -> CInt {
    (size.wrapping_add((PAGE_SIZE - 1) as SizeT) >> PAGE_SHIFT) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_validate_p2align_result(p2align: CInt) -> CInt {
    if p2align != PAGE_P2ALIGN {
        -ENOMEM
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_get_page_action_result(
    has_page: CInt,
    page_mode: CInt,
    errorp: *mut CInt,
) -> CInt {
    write(errorp, 0);

    if has_page == 0 || page_mode == PM_WILL_PAGEIO || page_mode == PM_PAGEIO {
        write(errorp, -ERESTART);
        return FILEOBJ_PAGE_ACTION_START_IO;
    }

    if page_mode == PM_DONE_PAGEIO {
        return FILEOBJ_PAGE_ACTION_MAP_DONE;
    }

    if page_mode == PM_PAGEIO_EOF {
        write(errorp, -ERANGE);
        return FILEOBJ_PAGE_ACTION_ERROR;
    }

    if page_mode == PM_PAGEIO_ERROR {
        write(errorp, -EIO);
        return FILEOBJ_PAGE_ACTION_ERROR;
    }

    FILEOBJ_PAGE_ACTION_USE_EXISTING
}

#[no_mangle]
pub extern "C" fn fileobj_pageio_zero_result(flags: CInt) -> CInt {
    ((flags & MF_ZEROFILL) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_pageio_mode_after_read_result(ssize: CLong, pgsize: SizeT) -> CInt {
    if ssize == 0 {
        PM_PAGEIO_EOF
    } else if ssize as SizeT != pgsize {
        PM_PAGEIO_ERROR
    } else {
        PM_DONE_PAGEIO
    }
}

#[no_mangle]
pub extern "C" fn fileobj_flush_skip_result(flags: CInt, has_page: CInt) -> CInt {
    ((flags & MF_ZEROFILL) != 0 || has_page == 0) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_initial_refcnt_result() -> CInt {
    1
}

#[no_mangle]
pub extern "C" fn fileobj_initial_sref_result() -> CULong {
    1
}

#[no_mangle]
pub extern "C" fn fileobj_premap_start_node_result(nr_numa_nodes: CInt) -> CInt {
    nr_numa_nodes / 2
}

#[no_mangle]
pub extern "C" fn fileobj_premap_next_node_result(node: CInt, nr_numa_nodes: CInt) -> CInt {
    let next = node + 1;

    if next == nr_numa_nodes {
        nr_numa_nodes / 2
    } else {
        next
    }
}

#[no_mangle]
pub extern "C" fn fileobj_pages_bytes_result(nr_pages: CInt) -> SizeT {
    (nr_pages as SizeT) * core::mem::size_of::<*mut u8>()
}

#[no_mangle]
pub extern "C" fn fileobj_premap_page_index_result(off: OffT) -> CInt {
    (off >> PAGE_SHIFT) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_alloc_npages_result(p2align: CInt) -> CInt {
    1 << p2align
}

#[no_mangle]
pub extern "C" fn fileobj_alloc_flags_result(flags: CInt) -> CULong {
    IHK_MC_AP_NOWAIT
        | if (flags & MF_ZEROFILL) != 0 {
            IHK_MC_AP_USER
        } else {
            0
        }
}

#[no_mangle]
pub extern "C" fn fileobj_alloc_size_result(npages: CInt) -> SizeT {
    (npages as SizeT) * PAGE_SIZE as SizeT
}

#[no_mangle]
pub extern "C" fn fileobj_pageio_pgsize_result(p2align: CInt) -> SizeT {
    (PAGE_SIZE as SizeT) << p2align
}

#[no_mangle]
pub extern "C" fn fileobj_pageio_should_schedule_result(attempts: CInt) -> CInt {
    (attempts > 49) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_new_page_mode_result() -> CInt {
    PM_WILL_PAGEIO
}

#[no_mangle]
pub extern "C" fn fileobj_mapped_mode_result() -> CInt {
    PM_MAPPED
}

#[no_mangle]
pub extern "C" fn fileobj_path_present_result(value: CULong) -> CInt {
    (value != 0) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_invalid_page_count_result(count: CInt) -> CInt {
    (count != 1) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_should_free_hashed_page_result(
    count: CInt,
    page_unmap_result: CInt,
) -> CInt {
    (count == 1 && page_unmap_result != 0) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_premap_page_present_result(page: CULong) -> CInt {
    (page != 0) as CInt
}

#[no_mangle]
pub extern "C" fn fileobj_lookup_page_error_result(has_page: CInt) -> CInt {
    if has_page != 0 {
        0
    } else {
        -1
    }
}

#[no_mangle]
pub extern "C" fn fileobj_next_sref_result(sref: CULong) -> CULong {
    sref.wrapping_add(1)
}

#[no_mangle]
pub extern "C" fn fileobj_premap_interleave_result(mpol_flags: CULong) -> CInt {
    ((mpol_flags & MPOL_SHM_PREMAP) != 0) as CInt
}

pub type FileobjPhysToPageFn = Option<unsafe extern "C" fn(phys: CULong) -> *mut c_void>;
pub type FileobjPageOffsetFn = Option<unsafe extern "C" fn(page: *mut c_void) -> OffT>;
pub type FileobjWriteFn = Option<
    unsafe extern "C" fn(handle: CULong, offset: OffT, pgsize: SizeT, phys: CULong) -> CLong,
>;
pub type FileobjLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        memobj: *mut c_void,
        obj: *mut c_void,
        phys: CULong,
        pgsize: SizeT,
        result: CLong,
    ),
>;
pub type FileobjLockFn = Option<unsafe extern "C" fn(lock: *mut c_void, node: *mut c_void)>;
pub type FileobjUnlockFn = Option<unsafe extern "C" fn(lock: *mut c_void, node: *mut c_void)>;
pub type FileobjLookupFn =
    Option<unsafe extern "C" fn(obj: *mut c_void, hash: CInt, off: OffT) -> *mut c_void>;
pub type FileobjPagePhysFn = Option<unsafe extern "C" fn(page: *mut c_void) -> CULong>;
pub type FileobjListFirstFn = Option<unsafe extern "C" fn(head: *mut c_void) -> *mut c_void>;
pub type FileobjListNextFn =
    Option<unsafe extern "C" fn(head: *mut c_void, obj: *mut c_void) -> *mut c_void>;
pub type FileobjHandleFn = Option<unsafe extern "C" fn(obj: *mut c_void) -> CULong>;
pub type FileobjRefFn = Option<unsafe extern "C" fn(obj: *mut c_void) -> CInt>;
pub type FileobjDecFn = Option<unsafe extern "C" fn(obj: *mut c_void)>;
pub type FileobjPageModeFn = Option<unsafe extern "C" fn(page: *mut c_void) -> CInt>;
pub type FileobjPageSetModeFn = Option<unsafe extern "C" fn(page: *mut c_void, mode: CInt)>;
pub type FileobjPageioZeroFn = Option<unsafe extern "C" fn(phys: CULong)>;
pub type FileobjPageioReadFn =
    Option<unsafe extern "C" fn(handle: CULong, off: OffT, pgsize: SizeT, phys: CULong) -> CLong>;
pub type FileobjVoidFn = Option<unsafe extern "C" fn()>;
pub type FileobjPageioLogFn = Option<
    unsafe extern "C" fn(event: CInt, obj: *mut c_void, off: OffT, pgsize: SizeT, value: CLong),
>;
pub type FileobjPageioPanicFn =
    Option<unsafe extern "C" fn(obj: *mut c_void, off: OffT, pgsize: SizeT, mode: CInt)>;
pub type FileobjPtrVoidFn = Option<unsafe extern "C" fn(ptr: *mut c_void)>;
pub type FileobjPtrResultFn = Option<unsafe extern "C" fn(ptr: *mut c_void) -> *mut c_void>;
pub type FileobjAllocFn = Option<unsafe extern "C" fn(size: SizeT, flags: CULong) -> *mut c_void>;
pub type FileobjCopyFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, src: *const c_void, len: SizeT)>;
pub type FileobjPtrSetFn = Option<unsafe extern "C" fn(ptr: *mut c_void, value: *mut c_void)>;
pub type FileobjSizeSetFn = Option<unsafe extern "C" fn(ptr: *mut c_void, value: SizeT)>;
pub type FileobjIntSetFn = Option<unsafe extern "C" fn(ptr: *mut c_void, value: CInt)>;
pub type FileobjUlongGetFn = Option<unsafe extern "C" fn(ptr: *mut c_void) -> CULong>;
pub type FileobjUlongSetFn = Option<unsafe extern "C" fn(ptr: *mut c_void, value: CULong)>;
pub type FileobjCreateLogFn =
    Option<unsafe extern "C" fn(event: CInt, obj: *mut c_void, path: *const c_void, value: CLong)>;
pub type FileobjMemzeroFn = Option<unsafe extern "C" fn(ptr: *mut c_void, len: SizeT)>;
pub type FileobjAllocPagesNodeFn = Option<
    unsafe extern "C" fn(
        npages: CInt,
        p2align: CInt,
        flags: CULong,
        node: CInt,
        virt_addr: CULong,
    ) -> *mut c_void,
>;
pub type FileobjAllocPagesFn =
    Option<unsafe extern "C" fn(npages: CInt, flags: CULong, virt_addr: CULong) -> *mut c_void>;
pub type FileobjPageArraySetFn =
    Option<unsafe extern "C" fn(pages: *mut c_void, index: CInt, page: *mut c_void)>;
pub type FileobjPageArrayCmpxchgFn = Option<
    unsafe extern "C" fn(
        pages: *mut c_void,
        index: CInt,
        old: *mut c_void,
        new_value: *mut c_void,
    ) -> *mut c_void,
>;
pub type FileobjRssAddFn = Option<unsafe extern "C" fn(size: SizeT, pgsize: SizeT)>;
pub type FileobjCreatePremapLogFn =
    Option<unsafe extern "C" fn(event: CInt, obj: *mut c_void, page: *mut c_void, value: CLong)>;
pub type FileobjGetLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        obj: *mut c_void,
        off: OffT,
        p2align: CInt,
        virt_addr: CULong,
        physp_addr: CULong,
        page: *mut c_void,
        phys: CULong,
        value: CLong,
    ),
>;
pub type FileobjPtrPhysFn = Option<unsafe extern "C" fn(ptr: *mut c_void) -> CULong>;
pub type FileobjPhysToPageInsertFn = Option<unsafe extern "C" fn(phys: CULong) -> *mut c_void>;
pub type FileobjPageOffsetSetFn = Option<unsafe extern "C" fn(page: *mut c_void, off: OffT)>;
pub type FileobjLongSetFn = Option<unsafe extern "C" fn(page: *mut c_void, value: CLong)>;
pub type FileobjPageHashInsertFn =
    Option<unsafe extern "C" fn(obj: *mut c_void, page: *mut c_void, hash: CInt)>;
pub type FileobjPageioArgsSetFn =
    Option<unsafe extern "C" fn(args: *mut c_void, obj: *mut c_void, off: OffT, pgsize: SizeT)>;
pub type FileobjPgioSetFn =
    Option<unsafe extern "C" fn(thread: *mut c_void, pageio_fn: *mut c_void, args: *mut c_void)>;
pub type FileobjGetRegularLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        obj: *mut c_void,
        off: OffT,
        p2align: CInt,
        virt_addr: CULong,
        physp_addr: CULong,
        page: *mut c_void,
        phys: CULong,
        value: CULong,
        size: SizeT,
        mode: CInt,
        count: CInt,
    ),
>;
pub type FileobjGetRegularPanicFn =
    Option<unsafe extern "C" fn(obj: *mut c_void, off: OffT, page: *mut c_void, mode: CInt)>;
pub type FileobjPhysToVirtFn = Option<unsafe extern "C" fn(phys: CULong) -> *mut c_void>;
pub type FileobjIntFn = Option<unsafe extern "C" fn(ptr: *mut c_void) -> CInt>;
pub type FileobjFreePagesFn = Option<unsafe extern "C" fn(addr: *mut c_void, npages: CInt)>;
pub type FileobjRssSubFn = Option<unsafe extern "C" fn(size: SizeT, pgsize: SizeT)>;
pub type FileobjReleaseFn = Option<unsafe extern "C" fn(handle: CULong, sref: CULong) -> CInt>;
pub type FileobjPageArrayAtFn =
    Option<unsafe extern "C" fn(pages: *mut c_void, index: CInt) -> *mut c_void>;
pub type FileobjFreeLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        obj: *mut c_void,
        page: *mut c_void,
        phys: CULong,
        value: CLong,
        flags: CULong,
    ),
>;

#[no_mangle]
pub unsafe extern "C" fn fileobj_flush_page_body_result(
    memobj: *mut c_void,
    obj: *mut c_void,
    flags: CInt,
    handle: CULong,
    phys: CULong,
    pgsize: SizeT,
    phys_to_page_fn: FileobjPhysToPageFn,
    page_offset_fn: FileobjPageOffsetFn,
    write_fn: FileobjWriteFn,
    log_fn: FileobjLogFn,
) -> CInt {
    let phys_to_page_fn = match phys_to_page_fn {
        Some(phys_to_page_fn) => phys_to_page_fn,
        None => return -EINVAL,
    };
    let page_offset_fn = match page_offset_fn {
        Some(page_offset_fn) => page_offset_fn,
        None => return -EINVAL,
    };
    let write_fn = match write_fn {
        Some(write_fn) => write_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };

    if fileobj_flush_skip_result(flags, 1) != 0 {
        return 0;
    }

    let page = phys_to_page_fn(phys);
    if fileobj_flush_skip_result(flags, (!page.is_null()) as CInt) != 0 {
        log_fn(1, memobj, obj, phys, pgsize, 0);
        return 0;
    }

    let ss = write_fn(handle, page_offset_fn(page), pgsize, phys);
    if ss != pgsize as CLong {
        log_fn(2, memobj, obj, phys, pgsize, ss);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_invalidate_page_body_result(
    memobj: *mut c_void,
    phys: CULong,
    pgsize: SizeT,
    log_fn: FileobjLogFn,
) -> CInt {
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };

    log_fn(3, memobj, core::ptr::null_mut(), phys, pgsize, 0);
    0
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_lookup_page_body_result(
    obj: *mut c_void,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    lock: *mut c_void,
    lock_node: *mut c_void,
    lock_fn: FileobjLockFn,
    unlock_fn: FileobjUnlockFn,
    lookup_fn: FileobjLookupFn,
    page_phys_fn: FileobjPagePhysFn,
) -> CInt {
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let lookup_fn = match lookup_fn {
        Some(lookup_fn) => lookup_fn,
        None => return -EINVAL,
    };
    let page_phys_fn = match page_phys_fn {
        Some(page_phys_fn) => page_phys_fn,
        None => return -EINVAL,
    };
    if obj.is_null() || physp.is_null() || lock.is_null() || lock_node.is_null() {
        return -EINVAL;
    }

    let hash = fileobj_page_hash_result(off);
    let mut error = fileobj_validate_p2align_result(p2align);
    if error != 0 {
        return error;
    }

    lock_fn(lock, lock_node);
    let page = lookup_fn(obj, hash, off);
    error = fileobj_lookup_page_error_result((!page.is_null()) as CInt);
    if error == 0 {
        *physp = page_phys_fn(page);
    }
    unlock_fn(lock, lock_node);

    error
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_obj_list_lookup_body_result(
    handle: CULong,
    list_head: *mut c_void,
    first_fn: FileobjListFirstFn,
    next_fn: FileobjListNextFn,
    handle_fn: FileobjHandleFn,
    ref_fn: FileobjRefFn,
    dec_fn: FileobjDecFn,
) -> *mut c_void {
    let (Some(first_fn), Some(next_fn), Some(handle_fn), Some(ref_fn), Some(dec_fn)) =
        (first_fn, next_fn, handle_fn, ref_fn, dec_fn)
    else {
        return core::ptr::null_mut();
    };
    if list_head.is_null() {
        return core::ptr::null_mut();
    }

    let mut obj = first_fn(list_head);
    while !obj.is_null() {
        if handle_fn(obj) == handle {
            if fileobj_lookup_ref_keep_result(ref_fn(obj)) != 0 {
                return obj;
            }
            dec_fn(obj);
        }
        obj = next_fn(list_head, obj);
    }

    core::ptr::null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_create_publish_body_result(
    obj: *mut c_void,
    is_new: CInt,
    mmap_flags: CInt,
    pager_flags: CInt,
    result_size: SizeT,
    list_insert_fn: FileobjPtrVoidFn,
    size_set_fn: FileobjSizeSetFn,
    flags_set_fn: FileobjIntSetFn,
    status_set_fn: FileobjIntSetFn,
    refcnt_set_fn: FileobjIntSetFn,
    sref_get_fn: FileobjUlongGetFn,
    sref_set_fn: FileobjUlongSetFn,
) -> CInt {
    let (
        Some(list_insert_fn),
        Some(size_set_fn),
        Some(flags_set_fn),
        Some(status_set_fn),
        Some(refcnt_set_fn),
        Some(sref_get_fn),
        Some(sref_set_fn),
    ) = (
        list_insert_fn,
        size_set_fn,
        flags_set_fn,
        status_set_fn,
        refcnt_set_fn,
        sref_get_fn,
        sref_set_fn,
    )
    else {
        return -EINVAL;
    };
    if obj.is_null() {
        return -EINVAL;
    }

    if is_new != 0 {
        let flags = fileobj_apply_result_flags_result(
            fileobj_create_base_flags_result(mmap_flags),
            pager_flags,
        );
        list_insert_fn(obj);
        size_set_fn(obj, result_size);
        flags_set_fn(obj, flags);
        status_set_fn(obj, fileobj_status_from_flags_result(flags));
        refcnt_set_fn(obj, fileobj_initial_refcnt_result());
        sref_set_fn(obj, fileobj_initial_sref_result());
    } else {
        sref_set_fn(obj, fileobj_next_sref_result(sref_get_fn(obj)));
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_create_path_body_result(
    obj: *mut c_void,
    path_first: CInt,
    path_src: *const c_void,
    path_len: SizeT,
    alloc_flags: CULong,
    alloc_fn: FileobjAllocFn,
    copy_fn: FileobjCopyFn,
    path_set_fn: FileobjPtrSetFn,
    log_fn: FileobjCreateLogFn,
) -> CInt {
    let (Some(alloc_fn), Some(copy_fn), Some(path_set_fn), Some(log_fn)) =
        (alloc_fn, copy_fn, path_set_fn, log_fn)
    else {
        return -EINVAL;
    };
    if obj.is_null() {
        return -EINVAL;
    }

    if fileobj_path_present_result(path_first as CULong) == 0 {
        return 0;
    }

    if path_src.is_null() || path_len == 0 {
        return -EINVAL;
    }

    let path = alloc_fn(path_len, alloc_flags);
    if path.is_null() {
        log_fn(
            FILEOBJ_CREATE_LOG_PATH_ALLOC_FAILED,
            obj,
            path_src,
            path_len as CLong,
        );
        return -ENOMEM;
    }

    path_set_fn(obj, path);
    copy_fn(path, path_src, path_len);
    0
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_create_premap_body_result(
    obj: *mut c_void,
    flags: CInt,
    result_size: SizeT,
    mpol_flags: CULong,
    nr_numa_nodes: CInt,
    virt_addr: CULong,
    alloc_flags: CULong,
    alloc_fn: FileobjAllocFn,
    pages_set_fn: FileobjPtrSetFn,
    nr_pages_set_fn: FileobjIntSetFn,
    zero_fn: FileobjMemzeroFn,
    alloc_pages_node_fn: FileobjAllocPagesNodeFn,
    page_set_fn: FileobjPageArraySetFn,
    rss_add_fn: FileobjRssAddFn,
    log_fn: FileobjCreatePremapLogFn,
) -> CInt {
    let (
        Some(alloc_fn),
        Some(pages_set_fn),
        Some(nr_pages_set_fn),
        Some(zero_fn),
        Some(alloc_pages_node_fn),
        Some(page_set_fn),
        Some(rss_add_fn),
        Some(log_fn),
    ) = (
        alloc_fn,
        pages_set_fn,
        nr_pages_set_fn,
        zero_fn,
        alloc_pages_node_fn,
        page_set_fn,
        rss_add_fn,
        log_fn,
    )
    else {
        return -EINVAL;
    };
    if obj.is_null() {
        return -EINVAL;
    }

    if fileobj_premap_zerofill_result(flags) == 0 {
        return 0;
    }

    let nr_pages = fileobj_premap_npages_result(result_size);
    let mut node = fileobj_premap_start_node_result(nr_numa_nodes);
    log_fn(
        FILEOBJ_CREATE_LOG_PREMAP_START,
        obj,
        core::ptr::null_mut(),
        node as CLong,
    );

    let pages_len = fileobj_pages_bytes_result(nr_pages);
    let pages = alloc_fn(pages_len, alloc_flags);
    if pages.is_null() {
        log_fn(
            FILEOBJ_CREATE_LOG_PREMAP_ARRAY_ALLOC_FAILED,
            obj,
            core::ptr::null_mut(),
            0,
        );
        return 0;
    }

    pages_set_fn(obj, pages);
    nr_pages_set_fn(obj, nr_pages);
    zero_fn(pages, pages_len);

    if fileobj_premap_interleave_result(mpol_flags) != 0 {
        let mut j = 0;
        while j < nr_pages {
            let page = alloc_pages_node_fn(1, PAGE_P2ALIGN, alloc_flags, node, virt_addr);
            if page.is_null() {
                log_fn(
                    FILEOBJ_CREATE_LOG_PREMAP_PAGE_ALLOC_FAILED,
                    obj,
                    core::ptr::null_mut(),
                    j as CLong,
                );
                return 0;
            }
            page_set_fn(pages, j, page);
            log_fn(
                FILEOBJ_CREATE_LOG_PREMAP_RSS_ADD,
                obj,
                page,
                PAGE_SIZE as CLong,
            );
            rss_add_fn(PAGE_SIZE as SizeT, PAGE_SIZE as SizeT);
            zero_fn(page, PAGE_SIZE as SizeT);
            node = fileobj_premap_next_node_result(node, nr_numa_nodes);
            j += 1;
        }
        log_fn(
            FILEOBJ_CREATE_LOG_PREMAP_INTERLEAVED_DONE,
            obj,
            core::ptr::null_mut(),
            nr_pages as CLong,
        );
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_get_premap_body_result(
    obj: *mut c_void,
    pages: *mut c_void,
    off: OffT,
    p2align: CInt,
    virt_addr: CULong,
    physp: *mut CULong,
    alloc_flags: CULong,
    alloc_pages_fn: FileobjAllocPagesFn,
    zero_fn: FileobjMemzeroFn,
    page_at_fn: FileobjPageArrayAtFn,
    cmpxchg_fn: FileobjPageArrayCmpxchgFn,
    free_pages_fn: FileobjFreePagesFn,
    phys_fn: FileobjPtrPhysFn,
    rss_add_fn: FileobjRssAddFn,
    log_fn: FileobjGetLogFn,
) -> CInt {
    let (
        Some(alloc_pages_fn),
        Some(zero_fn),
        Some(page_at_fn),
        Some(cmpxchg_fn),
        Some(free_pages_fn),
        Some(phys_fn),
        Some(rss_add_fn),
        Some(log_fn),
    ) = (
        alloc_pages_fn,
        zero_fn,
        page_at_fn,
        cmpxchg_fn,
        free_pages_fn,
        phys_fn,
        rss_add_fn,
        log_fn,
    )
    else {
        return -EINVAL;
    };
    if obj.is_null() || pages.is_null() || physp.is_null() {
        return -EINVAL;
    }

    let page_ind = fileobj_premap_page_index_result(off);
    let mut virt = page_at_fn(pages, page_ind);
    if virt.is_null() {
        let new_virt = alloc_pages_fn(1, alloc_flags, virt_addr);
        if new_virt.is_null() {
            log_fn(
                FILEOBJ_GET_LOG_PREMAP_ALLOC_FAILED,
                obj,
                off,
                p2align,
                virt_addr,
                physp as CULong,
                core::ptr::null_mut(),
                0,
                -(ENOMEM as CLong),
            );
            return -ENOMEM;
        }

        zero_fn(new_virt, PAGE_SIZE as SizeT);
        virt = cmpxchg_fn(pages, page_ind, core::ptr::null_mut(), new_virt);
        if !virt.is_null() {
            free_pages_fn(new_virt, 1);
        } else {
            virt = new_virt;
            let phys = phys_fn(virt);
            log_fn(
                FILEOBJ_GET_LOG_PREMAP_ALLOCATED,
                obj,
                off,
                p2align,
                virt_addr,
                physp as CULong,
                virt,
                phys,
                0,
            );
            log_fn(
                FILEOBJ_GET_LOG_PREMAP_RSS_ADD,
                obj,
                off,
                p2align,
                virt_addr,
                physp as CULong,
                virt,
                phys,
                PAGE_SIZE as CLong,
            );
            rss_add_fn(PAGE_SIZE as SizeT, PAGE_SIZE as SizeT);
        }
    }

    virt = page_at_fn(pages, page_ind);
    let phys = phys_fn(virt);
    *physp = phys;
    log_fn(
        FILEOBJ_GET_LOG_PREMAP_RESOLVED,
        obj,
        off,
        p2align,
        virt_addr,
        physp as CULong,
        virt,
        phys,
        0,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_get_regular_body_result(
    obj: *mut c_void,
    flags: CInt,
    off: OffT,
    p2align: CInt,
    virt_addr: CULong,
    physp: *mut CULong,
    thread: *mut c_void,
    pageio_fn: *mut c_void,
    lock: *mut c_void,
    lock_node: *mut c_void,
    args_size: SizeT,
    args_alloc_flags: CULong,
    lock_fn: FileobjLockFn,
    unlock_fn: FileobjUnlockFn,
    lookup_fn: FileobjLookupFn,
    alloc_fn: FileobjAllocFn,
    free_fn: FileobjPtrVoidFn,
    alloc_pages_fn: FileobjAllocPagesFn,
    phys_fn: FileobjPtrPhysFn,
    page_insert_lookup_fn: FileobjPhysToPageInsertFn,
    page_mode_fn: FileobjPageModeFn,
    page_offset_set_fn: FileobjPageOffsetSetFn,
    page_count_set_fn: FileobjLongSetFn,
    page_mapped_set_fn: FileobjLongSetFn,
    hash_insert_fn: FileobjPageHashInsertFn,
    page_mode_set_fn: FileobjPageSetModeFn,
    memobj_ref_fn: FileobjRefFn,
    args_set_fn: FileobjPageioArgsSetFn,
    pgio_set_fn: FileobjPgioSetFn,
    page_count_inc_fn: FileobjPtrVoidFn,
    page_phys_fn: FileobjPagePhysFn,
    page_count_fn: FileobjIntFn,
    page_remove_fn: FileobjPtrVoidFn,
    phys_to_virt_fn: FileobjPhysToVirtFn,
    page_unmap_fn: FileobjIntFn,
    free_pages_fn: FileobjFreePagesFn,
    log_fn: FileobjGetRegularLogFn,
    panic_fn: FileobjGetRegularPanicFn,
) -> CInt {
    let (
        Some(lock_fn),
        Some(unlock_fn),
        Some(lookup_fn),
        Some(alloc_fn),
        Some(free_fn),
        Some(alloc_pages_fn),
        Some(phys_fn),
        Some(page_insert_lookup_fn),
        Some(page_mode_fn),
        Some(page_offset_set_fn),
        Some(page_count_set_fn),
        Some(page_mapped_set_fn),
        Some(hash_insert_fn),
        Some(page_mode_set_fn),
        Some(memobj_ref_fn),
        Some(args_set_fn),
        Some(pgio_set_fn),
        Some(page_count_inc_fn),
        Some(page_phys_fn),
        Some(page_count_fn),
        Some(page_remove_fn),
        Some(phys_to_virt_fn),
        Some(page_unmap_fn),
        Some(free_pages_fn),
        Some(log_fn),
        Some(panic_fn),
    ) = (
        lock_fn,
        unlock_fn,
        lookup_fn,
        alloc_fn,
        free_fn,
        alloc_pages_fn,
        phys_fn,
        page_insert_lookup_fn,
        page_mode_fn,
        page_offset_set_fn,
        page_count_set_fn,
        page_mapped_set_fn,
        hash_insert_fn,
        page_mode_set_fn,
        memobj_ref_fn,
        args_set_fn,
        pgio_set_fn,
        page_count_inc_fn,
        page_phys_fn,
        page_count_fn,
        page_remove_fn,
        phys_to_virt_fn,
        page_unmap_fn,
        free_pages_fn,
        log_fn,
        panic_fn,
    )
    else {
        return -EINVAL;
    };
    if obj.is_null()
        || physp.is_null()
        || thread.is_null()
        || pageio_fn.is_null()
        || lock.is_null()
        || lock_node.is_null()
        || args_size == 0
    {
        return -EINVAL;
    }

    let hash = fileobj_page_hash_result(off);
    let mut error: CInt = -1;
    let virt: *mut c_void;
    let mut phys_state: CULong = !0;
    lock_fn(lock, lock_node);
    let mut page = lookup_fn(obj, hash, off);
    let page_mode = if page.is_null() {
        PM_NONE
    } else {
        page_mode_fn(page)
    };
    let action = fileobj_get_page_action_result((!page.is_null()) as CInt, page_mode, &mut error);

    if action == FILEOBJ_PAGE_ACTION_START_IO {
        let args = alloc_fn(args_size, args_alloc_flags);
        if args.is_null() {
            error = -ENOMEM;
            log_fn(
                FILEOBJ_GET_LOG_KMALLOC_FAILED,
                obj,
                off,
                p2align,
                virt_addr,
                physp as CULong,
                core::ptr::null_mut(),
                phys_state,
                error as CULong,
                0,
                0,
                0,
            );
            unlock_fn(lock, lock_node);
            log_fn(
                FILEOBJ_GET_LOG_RETURN,
                obj,
                off,
                p2align,
                virt_addr,
                physp as CULong,
                page,
                phys_state,
                error as CULong,
                0,
                0,
                0,
            );
            return error;
        }

        if page.is_null() {
            let npages = fileobj_alloc_npages_result(p2align);
            virt = alloc_pages_fn(npages, fileobj_alloc_flags_result(flags), virt_addr);
            if virt.is_null() {
                error = -ENOMEM;
                log_fn(
                    FILEOBJ_GET_LOG_ALLOC_FAILED,
                    obj,
                    off,
                    p2align,
                    virt_addr,
                    physp as CULong,
                    core::ptr::null_mut(),
                    phys_state,
                    error as CULong,
                    0,
                    0,
                    0,
                );
                free_fn(args);
                unlock_fn(lock, lock_node);
                log_fn(
                    FILEOBJ_GET_LOG_RETURN,
                    obj,
                    off,
                    p2align,
                    virt_addr,
                    physp as CULong,
                    page,
                    phys_state,
                    error as CULong,
                    0,
                    0,
                    0,
                );
                return error;
            }

            phys_state = phys_fn(virt);
            page = page_insert_lookup_fn(phys_state);
            log_fn(
                FILEOBJ_GET_LOG_NEW_PAGE,
                obj,
                off,
                p2align,
                virt_addr,
                physp as CULong,
                page,
                phys_state,
                virt as CULong,
                fileobj_alloc_size_result(npages),
                0,
                0,
            );
            let mode = page_mode_fn(page);
            if mode != PM_NONE {
                panic_fn(obj, off, page, mode);
            }
            page_offset_set_fn(page, off);
            page_count_set_fn(page, 1);
            page_mapped_set_fn(page, 0);
            hash_insert_fn(obj, page, hash);
            page_mode_set_fn(page, fileobj_new_page_mode_result());
        }

        memobj_ref_fn(obj);
        args_set_fn(args, obj, off, fileobj_pageio_pgsize_result(p2align));
        pgio_set_fn(thread, pageio_fn, args);
    } else if action == FILEOBJ_PAGE_ACTION_MAP_DONE {
        page_mode_set_fn(page, fileobj_mapped_mode_result());
        let page_phys = page_phys_fn(page);
        log_fn(
            FILEOBJ_GET_LOG_MAP_DONE,
            obj,
            off,
            p2align,
            virt_addr,
            physp as CULong,
            page,
            page_phys,
            0,
            0,
            fileobj_mapped_mode_result(),
            page_count_fn(page),
        );
        page_count_inc_fn(page);
        let page_phys = page_phys_fn(page);
        log_fn(
            FILEOBJ_GET_LOG_USE_PAGE,
            obj,
            off,
            p2align,
            virt_addr,
            physp as CULong,
            page,
            page_phys,
            0,
            0,
            page_mode_fn(page),
            page_count_fn(page),
        );
        error = 0;
        *physp = page_phys;
    } else if action == FILEOBJ_PAGE_ACTION_ERROR {
        page_remove_fn(page);
        virt = phys_to_virt_fn(page_phys_fn(page));
        if page_unmap_fn(page) != 0 {
            free_pages_fn(virt, 1);
            free_fn(page);
        }
    } else {
        page_count_inc_fn(page);
        let page_phys = page_phys_fn(page);
        log_fn(
            FILEOBJ_GET_LOG_USE_PAGE,
            obj,
            off,
            p2align,
            virt_addr,
            physp as CULong,
            page,
            page_phys,
            0,
            0,
            page_mode_fn(page),
            page_count_fn(page),
        );
        error = 0;
        *physp = page_phys;
    }

    unlock_fn(lock, lock_node);
    log_fn(
        FILEOBJ_GET_LOG_RETURN,
        obj,
        off,
        p2align,
        virt_addr,
        physp as CULong,
        page,
        phys_state,
        error as CULong,
        0,
        0,
        0,
    );
    error
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_do_pageio_body_result(
    obj: *mut c_void,
    flags: CInt,
    handle: CULong,
    off: OffT,
    pgsize: SizeT,
    lock: *mut c_void,
    lock_node: *mut c_void,
    lock_fn: FileobjLockFn,
    unlock_fn: FileobjUnlockFn,
    lookup_fn: FileobjLookupFn,
    page_mode_fn: FileobjPageModeFn,
    page_set_mode_fn: FileobjPageSetModeFn,
    page_phys_fn: FileobjPagePhysFn,
    zero_fn: FileobjPageioZeroFn,
    read_fn: FileobjPageioReadFn,
    schedule_fn: FileobjVoidFn,
    pause_fn: FileobjVoidFn,
    log_fn: FileobjPageioLogFn,
    panic_fn: FileobjPageioPanicFn,
) -> CInt {
    let (
        Some(lock_fn),
        Some(unlock_fn),
        Some(lookup_fn),
        Some(page_mode_fn),
        Some(page_set_mode_fn),
        Some(page_phys_fn),
        Some(zero_fn),
        Some(read_fn),
        Some(schedule_fn),
        Some(pause_fn),
        Some(log_fn),
        Some(panic_fn),
    ) = (
        lock_fn,
        unlock_fn,
        lookup_fn,
        page_mode_fn,
        page_set_mode_fn,
        page_phys_fn,
        zero_fn,
        read_fn,
        schedule_fn,
        pause_fn,
        log_fn,
        panic_fn,
    )
    else {
        return -EINVAL;
    };
    if obj.is_null() || lock.is_null() || lock_node.is_null() {
        return -EINVAL;
    }

    let hash = fileobj_page_hash_result(off);
    let mut attempts = 0;

    lock_fn(lock, lock_node);
    let page = lookup_fn(obj, hash, off);
    if page.is_null() {
        unlock_fn(lock, lock_node);
        return 0;
    }

    while page_mode_fn(page) == PM_PAGEIO {
        unlock_fn(lock, lock_node);
        attempts += 1;
        if fileobj_pageio_should_schedule_result(attempts) != 0 {
            log_fn(
                FILEOBJ_LOG_PAGEIO_SCHEDULE,
                obj,
                off,
                pgsize,
                attempts as CLong,
            );
            schedule_fn();
        }
        pause_fn();
        lock_fn(lock, lock_node);
    }

    if page_mode_fn(page) == PM_WILL_PAGEIO {
        if fileobj_pageio_zero_result(flags) != 0 {
            zero_fn(page_phys_fn(page));
        } else {
            page_set_mode_fn(page, PM_PAGEIO);
            let phys = page_phys_fn(page);
            unlock_fn(lock, lock_node);
            let ss = read_fn(handle, off, pgsize, phys);
            lock_fn(lock, lock_node);

            let mode = page_mode_fn(page);
            if mode != PM_PAGEIO {
                panic_fn(obj, off, pgsize, mode);
                unlock_fn(lock, lock_node);
                return -EINVAL;
            }

            let new_mode = fileobj_pageio_mode_after_read_result(ss, pgsize);
            page_set_mode_fn(page, new_mode);
            if new_mode == PM_PAGEIO_EOF {
                log_fn(FILEOBJ_LOG_PAGEIO_EOF, obj, off, pgsize, ss);
                unlock_fn(lock, lock_node);
                return 0;
            }
            if new_mode == PM_PAGEIO_ERROR {
                log_fn(FILEOBJ_LOG_PAGEIO_READ_ERROR, obj, off, pgsize, ss);
                unlock_fn(lock, lock_node);
                return 0;
            }
        }

        page_set_mode_fn(page, PM_DONE_PAGEIO);
    }

    unlock_fn(lock, lock_node);
    0
}

#[no_mangle]
pub unsafe extern "C" fn fileobj_free_body_result(
    obj: *mut c_void,
    flags: CInt,
    handle: CULong,
    sref: CULong,
    pages: *mut c_void,
    nr_pages: CInt,
    path: *mut c_void,
    list_lock: *mut c_void,
    lock_node: *mut c_void,
    lock_fn: FileobjLockFn,
    unlock_fn: FileobjUnlockFn,
    list_remove_fn: FileobjPtrVoidFn,
    page_first_fn: FileobjPtrResultFn,
    page_remove_fn: FileobjPtrVoidFn,
    page_phys_fn: FileobjPagePhysFn,
    phys_to_virt_fn: FileobjPhysToVirtFn,
    page_count_fn: FileobjIntFn,
    page_unmap_fn: FileobjIntFn,
    free_pages_fn: FileobjFreePagesFn,
    rss_sub_fn: FileobjRssSubFn,
    free_fn: FileobjPtrVoidFn,
    release_fn: FileobjReleaseFn,
    page_at_fn: FileobjPageArrayAtFn,
    log_fn: FileobjFreeLogFn,
) -> CInt {
    let (
        Some(lock_fn),
        Some(unlock_fn),
        Some(list_remove_fn),
        Some(page_first_fn),
        Some(page_remove_fn),
        Some(page_phys_fn),
        Some(phys_to_virt_fn),
        Some(page_count_fn),
        Some(page_unmap_fn),
        Some(free_pages_fn),
        Some(rss_sub_fn),
        Some(free_fn),
        Some(release_fn),
        Some(page_at_fn),
        Some(log_fn),
    ) = (
        lock_fn,
        unlock_fn,
        list_remove_fn,
        page_first_fn,
        page_remove_fn,
        page_phys_fn,
        phys_to_virt_fn,
        page_count_fn,
        page_unmap_fn,
        free_pages_fn,
        rss_sub_fn,
        free_fn,
        release_fn,
        page_at_fn,
        log_fn,
    )
    else {
        return -EINVAL;
    };
    if obj.is_null() || list_lock.is_null() || lock_node.is_null() {
        return -EINVAL;
    }

    lock_fn(list_lock, lock_node);
    list_remove_fn(obj);
    unlock_fn(list_lock, lock_node);

    loop {
        let page = page_first_fn(obj);
        if page.is_null() {
            break;
        }

        page_remove_fn(page);
        let phys = page_phys_fn(page);
        let virt = phys_to_virt_fn(phys);
        let count = page_count_fn(page);
        if fileobj_invalid_page_count_result(count) != 0 {
            log_fn(
                FILEOBJ_LOG_FREE_INVALID_COUNT,
                obj,
                page,
                phys,
                count as CLong,
                flags as CULong,
            );
        } else if fileobj_should_free_hashed_page_result(count, page_unmap_fn(page)) != 0 {
            free_pages_fn(virt, 1);
            rss_sub_fn(PAGE_SIZE as SizeT, PAGE_SIZE as SizeT);
            log_fn(
                FILEOBJ_LOG_FREE_RSS_SUB,
                obj,
                page,
                phys,
                PAGE_SIZE as CLong,
                flags as CULong,
            );
            free_fn(page);
        }
    }

    if fileobj_premap_zerofill_result(flags) != 0 {
        let mut i = 0;
        while i < nr_pages {
            let page = page_at_fn(pages, i);
            if fileobj_premap_page_present_result(page as CULong) != 0 {
                free_pages_fn(page, 1);
                rss_sub_fn(PAGE_SIZE as SizeT, PAGE_SIZE as SizeT);
                log_fn(
                    FILEOBJ_LOG_FREE_RSS_SUB,
                    obj,
                    page,
                    page as CULong,
                    PAGE_SIZE as CLong,
                    flags as CULong,
                );
            }
            i += 1;
        }
        if !pages.is_null() {
            free_fn(pages);
        }
    }

    if fileobj_path_present_result(path as CULong) != 0 {
        free_fn(path);
    }

    let release_error = release_fn(handle, sref);
    if release_error != 0 {
        log_fn(
            FILEOBJ_LOG_FREE_RELEASE_ERROR,
            obj,
            core::ptr::null_mut(),
            handle,
            release_error as CLong,
            flags as CULong,
        );
    }

    log_fn(
        FILEOBJ_LOG_FREE_DONE,
        obj,
        core::ptr::null_mut(),
        handle,
        release_error as CLong,
        flags as CULong,
    );
    free_fn(obj);

    release_error
}

#[no_mangle]
pub extern "C" fn devobj_npages_result(len: SizeT) -> SizeT {
    len.wrapping_add((PAGE_SIZE - 1) as SizeT) / PAGE_SIZE as SizeT
}

#[no_mangle]
pub extern "C" fn devobj_pfn_table_npages_result(npages: SizeT) -> SizeT {
    let uintptr_per_page = PAGE_SIZE as SizeT / core::mem::size_of::<CULong>();

    npages.wrapping_add(uintptr_per_page - 1) / uintptr_per_page
}

#[no_mangle]
pub extern "C" fn devobj_pfn_table_bytes_result(pfn_npages: SizeT) -> SizeT {
    pfn_npages * PAGE_SIZE as SizeT
}

#[no_mangle]
pub extern "C" fn devobj_pgoff_result(off: OffT) -> OffT {
    off >> PAGE_SHIFT
}

#[no_mangle]
pub unsafe extern "C" fn devobj_get_page_index_result(
    pgoff: OffT,
    base_pgoff: OffT,
    npages: SizeT,
    ixp: *mut CInt,
) -> CInt {
    let end = (base_pgoff as CULong).wrapping_add(npages as CULong);

    if pgoff < base_pgoff || end <= pgoff as CULong {
        return -EFBIG;
    }

    write(ixp, pgoff.wrapping_sub(base_pgoff) as CInt);
    0
}

#[no_mangle]
pub extern "C" fn devobj_cached_pfn_needs_fetch_result(pfn: CULong) -> CInt {
    ((pfn & PFN_VALID) == 0) as CInt
}

#[no_mangle]
pub extern "C" fn devobj_pfn_present_result(pfn: CULong) -> CInt {
    ((pfn & PFN_PRESENT) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn devobj_pfn_attr_result(pfn: CULong) -> CULong {
    pfn & !PFN_PFN
}

#[no_mangle]
pub extern "C" fn devobj_pfn_phys_result(pfn: CULong) -> CULong {
    pfn & PFN_PFN
}

#[no_mangle]
pub extern "C" fn devobj_pfn_absent_error_result(pfn: CULong) -> CInt {
    if (pfn & PFN_PRESENT) != 0 {
        0
    } else {
        -EFAULT
    }
}

#[no_mangle]
pub extern "C" fn devobj_base_flags_result() -> CInt {
    MF_HAS_PAGER | MF_REMAP_FILE_PAGES | MF_DEV_FILE
}

#[no_mangle]
pub extern "C" fn devobj_initial_refcnt_result() -> CInt {
    1
}

#[no_mangle]
pub extern "C" fn devobj_pfn_request_offset_result(off: OffT) -> OffT {
    off & !((PAGE_SIZE - 1) as OffT)
}

#[no_mangle]
pub extern "C" fn devobj_should_store_pfn_result(current_pfn: CULong) -> CInt {
    (current_pfn == 0) as CInt
}

#[no_mangle]
pub extern "C" fn devobj_map_size_result() -> SizeT {
    PAGE_SIZE as SizeT
}

#[no_mangle]
pub extern "C" fn devobj_path_present_result(value: CULong) -> CInt {
    (value != 0) as CInt
}

#[no_mangle]
pub extern "C" fn devobj_pfn_table_present_result(pfn_table: CULong) -> CInt {
    (pfn_table != 0) as CInt
}

#[no_mangle]
pub extern "C" fn devobj_mapped_pfn_result(mapped_pfn: CULong, attr: CULong) -> CULong {
    devobj_pfn_phys_result(mapped_pfn) | attr
}

pub type DevobjUnmapFn = Option<unsafe extern "C" fn(handle: CULong) -> CInt>;
pub type DevobjFreePagesFn = Option<unsafe extern "C" fn(addr: *mut c_void, npages: SizeT)>;
pub type DevobjFreeFn = Option<unsafe extern "C" fn(addr: *mut c_void)>;
pub type DevobjLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        memobj: *mut c_void,
        obj: *mut c_void,
        off: OffT,
        pgoff: OffT,
        p2align: CInt,
        ix: CInt,
        error: CInt,
        pfn: CULong,
    ),
>;
pub type DevobjProfileFn = Option<unsafe extern "C" fn()>;
pub type DevobjLockFn = Option<unsafe extern "C" fn(lock: *mut c_void) -> CULong>;
pub type DevobjUnlockFn = Option<unsafe extern "C" fn(lock: *mut c_void, irqstate: CULong)>;
pub type DevobjPfnLoadFn = Option<unsafe extern "C" fn(obj: *mut c_void, ix: CInt) -> CULong>;
pub type DevobjFetchPfnFn = Option<
    unsafe extern "C" fn(
        memobj: *mut c_void,
        obj: *mut c_void,
        handle: CULong,
        off: OffT,
        p2align: CInt,
        pfnp: *mut CULong,
    ) -> CInt,
>;
pub type DevobjWriteCombinedFn = Option<unsafe extern "C" fn(pfn: CULong) -> CInt>;
pub type DevobjMapMemoryFn = Option<unsafe extern "C" fn(phys: CULong, size: SizeT) -> CULong>;
pub type DevobjPfnStoreFn = Option<unsafe extern "C" fn(obj: *mut c_void, ix: CInt, pfn: CULong)>;

#[no_mangle]
pub unsafe extern "C" fn devobj_free_body_result(
    obj: *mut c_void,
    path: *mut c_void,
    pfn_table: *mut c_void,
    handle: CULong,
    npages: SizeT,
    unmap_fn: DevobjUnmapFn,
    free_pages_fn: DevobjFreePagesFn,
    free_fn: DevobjFreeFn,
    log_fn: DevobjLogFn,
) -> CInt {
    let unmap_fn = match unmap_fn {
        Some(unmap_fn) => unmap_fn,
        None => return -EINVAL,
    };
    let free_pages_fn = match free_pages_fn {
        Some(free_pages_fn) => free_pages_fn,
        None => return -EINVAL,
    };
    let free_fn = match free_fn {
        Some(free_fn) => free_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if obj.is_null() {
        return -EINVAL;
    }

    let pfn_npages = devobj_pfn_table_npages_result(npages);
    let error = unmap_fn(handle);
    if error != 0 {
        log_fn(1, core::ptr::null_mut(), obj, 0, 0, 0, 0, error, handle);
    }

    if devobj_pfn_table_present_result(pfn_table as CULong) != 0 {
        free_pages_fn(pfn_table, pfn_npages);
    }
    if devobj_path_present_result(path as CULong) != 0 {
        free_fn(path);
    }
    free_fn(obj);
    log_fn(2, core::ptr::null_mut(), obj, 0, 0, 0, 0, 0, handle);

    0
}

#[no_mangle]
pub unsafe extern "C" fn devobj_get_page_body_result(
    memobj: *mut c_void,
    obj: *mut c_void,
    handle: CULong,
    off: OffT,
    p2align: CInt,
    pfn_pgoff: OffT,
    npages: SizeT,
    pfn_table_lock: *mut c_void,
    physp: *mut CULong,
    flagp: *mut CULong,
    profile_fn: DevobjProfileFn,
    lock_fn: DevobjLockFn,
    unlock_fn: DevobjUnlockFn,
    pfn_load_fn: DevobjPfnLoadFn,
    fetch_pfn_fn: DevobjFetchPfnFn,
    write_combined_fn: DevobjWriteCombinedFn,
    map_memory_fn: DevobjMapMemoryFn,
    pfn_store_fn: DevobjPfnStoreFn,
    log_fn: DevobjLogFn,
) -> CInt {
    let profile_fn = match profile_fn {
        Some(profile_fn) => profile_fn,
        None => return -EINVAL,
    };
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let pfn_load_fn = match pfn_load_fn {
        Some(pfn_load_fn) => pfn_load_fn,
        None => return -EINVAL,
    };
    let fetch_pfn_fn = match fetch_pfn_fn {
        Some(fetch_pfn_fn) => fetch_pfn_fn,
        None => return -EINVAL,
    };
    let write_combined_fn = match write_combined_fn {
        Some(write_combined_fn) => write_combined_fn,
        None => return -EINVAL,
    };
    let map_memory_fn = match map_memory_fn {
        Some(map_memory_fn) => map_memory_fn,
        None => return -EINVAL,
    };
    let pfn_store_fn = match pfn_store_fn {
        Some(pfn_store_fn) => pfn_store_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if obj.is_null() || pfn_table_lock.is_null() || physp.is_null() || flagp.is_null() {
        return -EINVAL;
    }

    let pgoff = devobj_pgoff_result(off);
    let mut ix: CInt = 0;
    let mut error = devobj_get_page_index_result(pgoff, pfn_pgoff, npages, &mut ix);
    if error != 0 {
        log_fn(3, memobj, obj, off, pgoff, p2align, 0, error, 0);
        return error;
    }

    profile_fn();

    let mut irqstate = lock_fn(pfn_table_lock);
    let mut pfn = pfn_load_fn(obj, ix);
    unlock_fn(pfn_table_lock, irqstate);

    if devobj_cached_pfn_needs_fetch_result(pfn) != 0 {
        pfn = 0;
        error = fetch_pfn_fn(memobj, obj, handle, off, p2align, &mut pfn);
        if error != 0 {
            log_fn(4, memobj, obj, off, pgoff, p2align, ix, error, pfn);
            return error;
        }

        if devobj_pfn_present_result(pfn) != 0 {
            let attr = devobj_pfn_attr_result(pfn);
            if write_combined_fn(pfn) != 0 {
                *flagp |= VR_WRITE_COMBINED;
            }
            pfn = map_memory_fn(devobj_pfn_phys_result(pfn), devobj_map_size_result());
            pfn = devobj_mapped_pfn_result(pfn, attr);
        }

        irqstate = lock_fn(pfn_table_lock);
        pfn_store_fn(obj, ix, pfn);
        unlock_fn(pfn_table_lock, irqstate);
    }

    error = devobj_pfn_absent_error_result(pfn);
    if error != 0 {
        log_fn(5, memobj, obj, off, pgoff, p2align, ix, error, pfn);
        return error;
    }

    *physp = devobj_pfn_phys_result(pfn);
    0
}

pub type ProcfsThreadPhysFn = Option<unsafe extern "C" fn(addr: *mut c_void) -> CULong>;
pub type ProcfsThreadSendFn =
    Option<unsafe extern "C" fn(channel: *mut c_void, packet: *mut IkcScdPacket) -> CInt>;
pub type ProcfsThreadPauseFn = Option<unsafe extern "C" fn()>;
pub type ProcfsAnswerSendFn =
    Option<unsafe extern "C" fn(channel: *mut c_void, packet: *mut IkcScdPacket)>;

#[repr(C)]
pub struct ProcfsBuffer {
    next_pa: CULong,
    pos: CULong,
    size: CULong,
}

pub type ProcfsBufAllocFn =
    Option<unsafe extern "C" fn(phys: *mut CULong, pos: CLong) -> *mut ProcfsBuffer>;
pub type ProcfsBufFreeTopFn = Option<unsafe extern "C" fn(top: *mut ProcfsBuffer)>;
pub type ProcfsBufCopyFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, src: *const c_void, len: SizeT) -> *mut c_void>;
pub type ProcfsBufPhysToVirtFn = Option<unsafe extern "C" fn(phys: CULong) -> *mut ProcfsBuffer>;
pub type ProcfsBufFreePageFn = Option<unsafe extern "C" fn(pbuf: *mut ProcfsBuffer)>;
pub type ProcfsBufPhysFn = Option<unsafe extern "C" fn(pbuf: *mut ProcfsBuffer) -> CULong>;
pub type ProcfsBufPageAllocFn =
    Option<unsafe extern "C" fn(npages: CInt, flags: CULong) -> *mut c_void>;
pub type ProcfsMemPageFaultFn =
    Option<unsafe extern "C" fn(vm: *mut c_void, offset: CULong, reason: CULong) -> CInt>;
pub type ProcfsMemVirtToPhysFn = Option<
    unsafe extern "C" fn(page_table: *mut c_void, offset: CULong, physp: *mut CULong) -> CInt,
>;
pub type ProcfsMemIsMemoryFn = Option<unsafe extern "C" fn(start: CULong, end: CULong) -> CInt>;
pub type ProcfsMemPhysToVirtFn = Option<unsafe extern "C" fn(phys: CULong) -> *mut c_void>;
pub type ProcfsMemCopyFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, src: *const c_void, len: SizeT) -> *mut c_void>;
pub type ProcfsPagemapValueFn =
    Option<unsafe extern "C" fn(page_table: *mut c_void, addr: CULong) -> CULong>;
pub type ProcfsRangeUlongFn =
    Option<unsafe extern "C" fn(range: *mut c_void, field: CInt) -> CULong>;
pub type ProcfsRangePathFn = Option<unsafe extern "C" fn(range: *mut c_void) -> *const u8>;
pub type ProcfsRangeNextFn =
    Option<unsafe extern "C" fn(vm: *mut c_void, range: *mut c_void) -> *mut c_void>;
pub type ProcfsBacklogFn = Option<unsafe extern "C" fn(arg: *mut c_void) -> CInt>;
pub type ProcfsBacklogAllocFn =
    Option<unsafe extern "C" fn(size: CULong, flags: CULong) -> *mut c_void>;
pub type ProcfsBacklogCopyFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, src: *mut IkcScdPacket, size: CULong)>;
pub type ProcfsBacklogAddFn =
    Option<unsafe extern "C" fn(backlog_fn: ProcfsBacklogFn, arg: *mut c_void) -> CInt>;
pub type ProcfsBacklogFreeFn = Option<unsafe extern "C" fn(arg: *mut c_void)>;

#[repr(C)]
pub struct ProcfsStatusBodyInput {
    pub(crate) pid: CInt,
    pub(crate) ruid: CInt,
    pub(crate) euid: CInt,
    pub(crate) suid: CInt,
    pub(crate) fsuid: CInt,
    pub(crate) rgid: CInt,
    pub(crate) egid: CInt,
    pub(crate) sgid: CInt,
    pub(crate) fsgid: CInt,
    pub(crate) status: CInt,
    pub(crate) nr_threads: CInt,
    pub(crate) lockedsize: CULong,
    pub(crate) cpu_bitmask: *const u8,
    pub(crate) cpu_list: *const u8,
    pub(crate) numa_bitmask: *const u8,
    pub(crate) numa_list: *const u8,
}

#[repr(C)]
pub struct ProcfsStatBodyInput {
    pub(crate) tid: CInt,
    pub(crate) comm: *const u8,
    pub(crate) state: u8,
    pub(crate) ppid: CInt,
    pub(crate) pid: CInt,
    pub(crate) nr_threads: CInt,
    pub(crate) cpu_id: CInt,
}

unsafe fn zero_ikc_scd_packet(packet: *mut IkcScdPacket) {
    let words = size_of::<IkcScdPacket>() / size_of::<CULong>();
    let bytes = size_of::<IkcScdPacket>() % size_of::<CULong>();
    let wordp = packet.cast::<CULong>();
    let mut index = 0;

    while index < words {
        write_volatile(wordp.add(index), 0);
        index += 1;
    }

    let bytep = wordp.add(words).cast::<u8>();
    let mut byte = 0;
    while byte < bytes {
        write_volatile(bytep.add(byte), 0);
        byte += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn procfs_buf_release_result(
    mut phys: CULong,
    phys_to_virt_fn: ProcfsBufPhysToVirtFn,
    free_page_fn: ProcfsBufFreePageFn,
) -> CInt {
    let phys_to_virt = match phys_to_virt_fn {
        Some(phys_to_virt) => phys_to_virt,
        None => return -EINVAL,
    };
    let free_page = match free_page_fn {
        Some(free_page) => free_page,
        None => return -EINVAL,
    };

    while phys != CULong::MAX {
        let pbuf = phys_to_virt(phys);
        if pbuf.is_null() {
            return -EINVAL;
        }
        let next = (*pbuf).next_pa;
        free_page(pbuf);
        phys = next;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn procfs_buf_alloc_result(
    phys: *mut CULong,
    pos: CLong,
    alloc_fn: ProcfsBufPageAllocFn,
    phys_fn: ProcfsBufPhysFn,
    alloc_flags: CULong,
) -> *mut ProcfsBuffer {
    let alloc = match alloc_fn {
        Some(alloc) => alloc,
        None => return core::ptr::null_mut(),
    };
    if !phys.is_null() && phys_fn.is_none() {
        return core::ptr::null_mut();
    }

    let pbuf = alloc(1, alloc_flags).cast::<ProcfsBuffer>();
    if pbuf.is_null() {
        return core::ptr::null_mut();
    }

    (*pbuf).next_pa = CULong::MAX;
    (*pbuf).pos = pos as CULong;
    (*pbuf).size = 0;
    if !phys.is_null() {
        if let Some(phys_cb) = phys_fn {
            write(phys, phys_cb(pbuf));
        } else {
            return core::ptr::null_mut();
        }
    }
    pbuf
}

#[no_mangle]
pub unsafe extern "C" fn procfs_buf_add_result(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    buf: *const c_void,
    len: CInt,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    let alloc = match alloc_fn {
        Some(alloc) => alloc,
        None => return -EINVAL,
    };
    let free_top = match free_top_fn {
        Some(free_top) => free_top,
        None => return -EINVAL,
    };
    let copy = match copy_fn {
        Some(copy) => copy,
        None => return -EINVAL,
    };
    if top.is_null() || cur.is_null() || buf.is_null() || len < 0 {
        return -EINVAL;
    }

    let bufmax = PAGE_SIZE as SizeT - size_of::<ProcfsBuffer>();
    if (*top).is_null() {
        let first = alloc(core::ptr::null_mut(), 0);
        if first.is_null() {
            return -ENOMEM;
        }
        write(top, first);
        write(cur, first);
    }
    if (*cur).is_null() {
        return -EINVAL;
    }

    let mut offset: SizeT = 0;
    let mut remaining = len as SizeT;
    while remaining != 0 {
        let curp = *cur;
        let mut room = bufmax - (*curp).size as SizeT;
        if room == 0 {
            let next_pos = (*curp).pos.wrapping_add(bufmax as CULong) as CLong;
            let next = alloc(&raw mut (*curp).next_pa, next_pos);
            if next.is_null() {
                free_top(*top);
                write(top, core::ptr::null_mut());
                write(cur, core::ptr::null_mut());
                return -ENOMEM;
            }
            write(cur, next);
            room = bufmax;
        }

        let amount = if room > remaining { remaining } else { room };
        let curp = *cur;
        let dst = curp
            .cast::<u8>()
            .add(size_of::<ProcfsBuffer>() + (*curp).size as SizeT)
            .cast::<c_void>();
        let src = buf.cast::<u8>().add(offset).cast::<c_void>();
        copy(dst, src, amount);
        (*curp).size = (*curp).size.wrapping_add(amount as CULong);
        remaining -= amount;
        offset += amount;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn procfs_release_request_result(
    request: *mut ProcfsRead,
    phys_to_virt_fn: ProcfsBufPhysToVirtFn,
    free_page_fn: ProcfsBufFreePageFn,
) -> CInt {
    if request.is_null() {
        return -EINVAL;
    }

    let error = procfs_buf_release_result((*request).pbuf, phys_to_virt_fn, free_page_fn);
    if error != 0 {
        return error;
    }
    (*request).ret = 0;
    0
}

#[no_mangle]
pub unsafe extern "C" fn procfs_finish_request_result(
    request: *mut ProcfsRead,
    ret: CInt,
    eof: CInt,
    buf_top: *mut ProcfsBuffer,
    phys_fn: ProcfsBufPhysFn,
) -> CInt {
    if request.is_null() {
        return -EINVAL;
    }

    (*request).ret = ret;
    (*request).eof = eof;
    if procfs_buffer_chain_attach_result((*request).pbuf, buf_top as CULong) != 0 {
        let phys = match phys_fn {
            Some(phys) => phys,
            None => return -EINVAL,
        };
        (*request).pbuf = phys(buf_top);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn procfs_backlog_result(
    request: *mut IkcScdPacket,
    backlog_fn: ProcfsBacklogFn,
    alloc_fn: ProcfsBacklogAllocFn,
    copy_fn: ProcfsBacklogCopyFn,
    add_fn: ProcfsBacklogAddFn,
    free_fn: ProcfsBacklogFreeFn,
    packet_size: CULong,
    alloc_flags: CULong,
) -> CInt {
    let alloc = match alloc_fn {
        Some(alloc) => alloc,
        None => return -EINVAL,
    };
    let copy = match copy_fn {
        Some(copy) => copy,
        None => return -EINVAL,
    };
    let add = match add_fn {
        Some(add) => add,
        None => return -EINVAL,
    };
    let free = match free_fn {
        Some(free) => free,
        None => return -EINVAL,
    };
    if request.is_null() || backlog_fn.is_none() {
        return -EINVAL;
    }

    let arg = alloc(packet_size, alloc_flags);
    if arg.is_null() {
        return -ENOMEM;
    }

    copy(arg, request, packet_size);
    let err = add(backlog_fn, arg);
    if err != 0 {
        free(arg);
    }
    err
}

#[no_mangle]
pub unsafe extern "C" fn procfs_thread_ctl_result(
    channel: *mut c_void,
    packet: *mut IkcScdPacket,
    donep: *mut CInt,
    msg: CInt,
    osnum: CInt,
    cpu_id: CInt,
    pid: CInt,
    tid: CInt,
    phys_fn: ProcfsThreadPhysFn,
    send_fn: ProcfsThreadSendFn,
    pause_fn: ProcfsThreadPauseFn,
) -> CInt {
    let phys = match phys_fn {
        Some(phys) => phys,
        None => return -EINVAL,
    };
    let send = match send_fn {
        Some(send) => send,
        None => return -EINVAL,
    };
    if packet.is_null() || donep.is_null() {
        return -EINVAL;
    }

    zero_ikc_scd_packet(packet);
    let traditional = (&raw mut (*packet).body).cast::<IkcScdPacketTraditional>();
    (*traditional).arg = tid as CULong;
    (*packet).msg = msg;
    (*traditional).osnum = osnum;
    (*traditional).ref_ = cpu_id;
    (*traditional).pid = pid;
    (*traditional).resp_pa = phys(donep.cast::<c_void>());
    (*packet).err = 0;

    let error = send(channel, packet);
    if msg == SCD_MSG_PROCFS_TID_CREATE {
        while read_volatile(donep) == 0 {
            match pause_fn {
                Some(pause) => pause(),
                None => return if error != 0 { error } else { -EINVAL },
            }
        }
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn procfs_answer_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    err: CInt,
    send_fn: ProcfsAnswerSendFn,
) -> CInt {
    let send = match send_fn {
        Some(send) => send,
        None => return -EINVAL,
    };
    if request.is_null() {
        return -EINVAL;
    }

    let mut packet = core::mem::MaybeUninit::<IkcScdPacket>::uninit();
    zero_ikc_scd_packet(packet.as_mut_ptr());
    let answer = packet.as_mut_ptr();
    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let answer_body = (&raw mut (*answer).body).cast::<IkcScdPacketTraditional>();

    (*answer).msg = SCD_MSG_PROCFS_ANSWER;
    (*answer_body).ref_ = (*request_body).ref_;
    (*answer_body).arg = (*request_body).arg;
    (*answer).err = err;
    (*answer).reply = (*request).reply;
    (*answer_body).pid = (*request_body).pid;
    send(channel, answer);
    0
}

#[no_mangle]
pub extern "C" fn sysfs_path_error_result(
    n: CLong,
    path_is_absolute: CInt,
    capacity: SizeT,
) -> CInt {
    if (n as SizeT) >= capacity {
        -ENAMETOOLONG
    } else if path_is_absolute == 0 {
        -ENOENT
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn sysfs_special_kind_result(client_ops: CLong) -> CInt {
    match client_ops {
        SYSFS_SNOOPING_OPS_D32
        | SYSFS_SNOOPING_OPS_D64
        | SYSFS_SNOOPING_OPS_U32
        | SYSFS_SNOOPING_OPS_U64
        | SYSFS_SNOOPING_OPS_U32K => SYSFS_SPECIAL_KIND_DIRECT,
        SYSFS_SNOOPING_OPS_S => SYSFS_SPECIAL_KIND_STRING,
        SYSFS_SNOOPING_OPS_PBL | SYSFS_SNOOPING_OPS_PB => SYSFS_SPECIAL_KIND_BITMAP,
        _ => -EINVAL,
    }
}

#[no_mangle]
pub extern "C" fn sysfs_string_nbits_result(len: SizeT) -> CInt {
    len.wrapping_add(1).wrapping_mul(8) as CInt
}

#[no_mangle]
pub extern "C" fn sysfs_response_error_result(ssize: CLong) -> CInt {
    if ssize < 0 {
        ssize as CInt
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn sysfs_param_sizes_valid_result(
    create_size: SizeT,
    mkdir_size: SizeT,
    symlink_size: SizeT,
    lookup_size: SizeT,
    unlink_size: SizeT,
    setup_size: SizeT,
) -> CInt {
    (create_size <= PAGE_SIZE as SizeT
        && mkdir_size <= PAGE_SIZE as SizeT
        && symlink_size <= PAGE_SIZE as SizeT
        && lookup_size <= PAGE_SIZE as SizeT
        && unlink_size <= PAGE_SIZE as SizeT
        && setup_size <= PAGE_SIZE as SizeT) as CInt
}

#[no_mangle]
pub extern "C" fn sysfs_data_bufsize_result() -> SizeT {
    PAGE_SIZE as SizeT
}

#[no_mangle]
pub extern "C" fn sysfs_packet_error_result(send_error: CInt, packet_error: CInt) -> CInt {
    (send_error != 0 || packet_error != 0) as CInt
}

#[no_mangle]
pub extern "C" fn sysfs_request_busy_result(busy: CInt) -> CInt {
    (busy != 0) as CInt
}

#[no_mangle]
pub extern "C" fn sysfs_handle_pointer_valid_result(handlep: CULong) -> CInt {
    (handlep != 0) as CInt
}

#[no_mangle]
pub extern "C" fn sysfs_default_response_ssize_result() -> CLong {
    -(EIO as CLong)
}

#[no_mangle]
pub extern "C" fn sysfs_release_response_error_result() -> CInt {
    0
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_packet_prepare_result(
    packet: *mut IkcScdPacket,
    msg: CInt,
    err: CInt,
    arg1: CLong,
    arg2: CLong,
) -> CInt {
    if packet.is_null() {
        return -EINVAL;
    }

    let sysfs = core::ptr::addr_of_mut!((*packet).body).cast::<IkcScdPacketSysfs>();
    write(core::ptr::addr_of_mut!((*packet).msg), msg);
    write(core::ptr::addr_of_mut!((*packet).err), err);
    write(core::ptr::addr_of_mut!((*sysfs).sysfs_arg1), arg1);
    write(core::ptr::addr_of_mut!((*sysfs).sysfs_arg2), arg2);

    0
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_request_packet_prepare_result(
    packet: *mut IkcScdPacket,
    msg: CInt,
    arg1: CLong,
) -> CInt {
    if packet.is_null() {
        return -EINVAL;
    }

    let sysfs = core::ptr::addr_of_mut!((*packet).body).cast::<IkcScdPacketSysfs>();
    write(core::ptr::addr_of_mut!((*packet).msg), msg);
    write(core::ptr::addr_of_mut!((*sysfs).sysfs_arg1), arg1);

    0
}

#[no_mangle]
pub extern "C" fn sysfs_request_handler_kind_result(msg: CInt) -> CInt {
    match msg {
        SCD_MSG_SYSFS_REQ_SHOW => SYSFS_HANDLER_SHOW,
        SCD_MSG_SYSFS_REQ_STORE => SYSFS_HANDLER_STORE,
        SCD_MSG_SYSFS_REQ_RELEASE => SYSFS_HANDLER_RELEASE,
        _ => SYSFS_HANDLER_UNKNOWN,
    }
}

#[no_mangle]
pub extern "C" fn sysfs_pointer_missing_result(ptr: CULong) -> CInt {
    (ptr == 0) as CInt
}

#[no_mangle]
pub extern "C" fn sysfs_should_call_show_result(show: CULong) -> CInt {
    (show != 0) as CInt
}

#[no_mangle]
pub extern "C" fn sysfs_should_call_store_result(store: CULong) -> CInt {
    (store != 0) as CInt
}

#[no_mangle]
pub extern "C" fn sysfs_should_call_release_result(release: CULong) -> CInt {
    (release != 0) as CInt
}

pub type SysfsRequestSendFn = Option<unsafe extern "C" fn(msg: CInt, arg1: CLong) -> CInt>;
pub type SysfsRequestPauseFn = Option<unsafe extern "C" fn()>;
pub type SysfsRequestBarrierFn = Option<unsafe extern "C" fn()>;
pub type SysfsRequestLogFn = Option<unsafe extern "C" fn(event: CInt, msg: CInt, error: CInt)>;
pub type SysfsInitAllocFn =
    Option<unsafe extern "C" fn(npages: CInt, flags: CULong) -> *mut c_void>;
pub type SysfsInitFreeFn = Option<unsafe extern "C" fn(addr: *mut c_void, npages: CInt)>;
pub type SysfsInitPhysFn = Option<unsafe extern "C" fn(addr: *mut c_void) -> CLong>;

#[inline(always)]
unsafe fn sysfs_c_strlen(mut ptr: *const i8) -> SizeT {
    let mut len = 0;
    while *ptr != 0 {
        len += 1;
        ptr = ptr.add(1);
    }
    len
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_setup_special_create_result(
    param: *mut SysfsReqCreateParam,
    pbp: *mut SysfsBitmapParam,
    phys_fn: SysfsInitPhysFn,
) -> CInt {
    let phys = match phys_fn {
        Some(phys) => phys,
        None => return -EINVAL,
    };
    if param.is_null() || pbp.is_null() {
        return -EINVAL;
    }

    let cinstance = (*param).client_instance as *mut c_void;
    match sysfs_special_kind_result((*param).client_ops) {
        SYSFS_SPECIAL_KIND_DIRECT => {
            (*param).client_instance = phys(cinstance);
            0
        }
        SYSFS_SPECIAL_KIND_STRING => {
            (*pbp).nbits = sysfs_string_nbits_result(sysfs_c_strlen(cinstance as *const i8));
            (*pbp).ptr = phys(cinstance) as *mut c_void;
            (*param).client_instance = phys(pbp as *mut c_void);
            0
        }
        SYSFS_SPECIAL_KIND_BITMAP => {
            let source = cinstance as *mut SysfsBitmapParam;
            (*pbp).nbits = (*source).nbits;
            (*pbp).padding = (*source).padding;
            (*pbp).ptr = phys((*source).ptr) as *mut c_void;
            (*param).client_instance = phys(pbp as *mut c_void);
            0
        }
        _ => -EINVAL,
    }
}

#[inline(always)]
fn sysfs_request_known_msg(msg: CInt) -> bool {
    matches!(
        msg,
        SCD_MSG_SYSFS_REQ_CREATE
            | SCD_MSG_SYSFS_REQ_MKDIR
            | SCD_MSG_SYSFS_REQ_SYMLINK
            | SCD_MSG_SYSFS_REQ_LOOKUP
            | SCD_MSG_SYSFS_REQ_UNLINK
            | SCD_MSG_SYSFS_REQ_SETUP
    )
}

#[inline(always)]
unsafe fn sysfs_request_busy_value(msg: CInt, param: *mut c_void) -> CInt {
    match msg {
        SCD_MSG_SYSFS_REQ_CREATE => read_volatile(&(*(param as *mut SysfsReqCreateParam)).busy),
        SCD_MSG_SYSFS_REQ_MKDIR => read_volatile(&(*(param as *mut SysfsReqMkdirParam)).busy),
        SCD_MSG_SYSFS_REQ_SYMLINK => read_volatile(&(*(param as *mut SysfsReqSymlinkParam)).busy),
        SCD_MSG_SYSFS_REQ_LOOKUP => read_volatile(&(*(param as *mut SysfsReqLookupParam)).busy),
        SCD_MSG_SYSFS_REQ_UNLINK => read_volatile(&(*(param as *mut SysfsReqUnlinkParam)).busy),
        SCD_MSG_SYSFS_REQ_SETUP => read_volatile(&(*(param as *mut SysfsReqSetupParam)).busy),
        _ => 0,
    }
}

#[inline(always)]
unsafe fn sysfs_request_error_value(msg: CInt, param: *mut c_void) -> CInt {
    match msg {
        SCD_MSG_SYSFS_REQ_CREATE => (*(param as *mut SysfsReqCreateParam)).error,
        SCD_MSG_SYSFS_REQ_MKDIR => (*(param as *mut SysfsReqMkdirParam)).error,
        SCD_MSG_SYSFS_REQ_SYMLINK => (*(param as *mut SysfsReqSymlinkParam)).error,
        SCD_MSG_SYSFS_REQ_LOOKUP => (*(param as *mut SysfsReqLookupParam)).error,
        SCD_MSG_SYSFS_REQ_UNLINK => (*(param as *mut SysfsReqUnlinkParam)).error,
        SCD_MSG_SYSFS_REQ_SETUP => (*(param as *mut SysfsReqSetupParam)).error,
        _ => -EINVAL,
    }
}

#[inline(always)]
unsafe fn sysfs_request_handle_value(msg: CInt, param: *mut c_void) -> CLong {
    match msg {
        SCD_MSG_SYSFS_REQ_MKDIR => (*(param as *mut SysfsReqMkdirParam)).handle,
        SCD_MSG_SYSFS_REQ_LOOKUP => (*(param as *mut SysfsReqLookupParam)).handle,
        _ => 0,
    }
}

#[inline(always)]
unsafe fn sysfs_store_phase(phasep: *mut CInt, phase: CInt) {
    if !phasep.is_null() {
        write(phasep, phase);
    }
}

#[inline(always)]
unsafe fn sysfs_store_init_stage(stagep: *mut CInt, stage: CInt) {
    if !stagep.is_null() {
        write(stagep, stage);
    }
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_request_body_result(
    msg: CInt,
    param: *mut c_void,
    param_rpa: CLong,
    send_fn: SysfsRequestSendFn,
    pause_fn: SysfsRequestPauseFn,
    barrier_fn: SysfsRequestBarrierFn,
    handlep: *mut CLong,
    phasep: *mut CInt,
) -> CInt {
    sysfs_store_phase(phasep, SYSFS_REQUEST_PHASE_NONE);

    if param.is_null() || !sysfs_request_known_msg(msg) {
        return -EINVAL;
    }

    let send = match send_fn {
        Some(send) => send,
        None => {
            sysfs_store_phase(phasep, SYSFS_REQUEST_PHASE_SEND);
            return -EIO;
        }
    };

    let error = send(msg, param_rpa);
    if error != 0 {
        sysfs_store_phase(phasep, SYSFS_REQUEST_PHASE_SEND);
        return error;
    }

    while sysfs_request_busy_result(sysfs_request_busy_value(msg, param)) != 0 {
        match pause_fn {
            Some(pause) => pause(),
            None => {
                sysfs_store_phase(phasep, SYSFS_REQUEST_PHASE_SEND);
                return -EIO;
            }
        }
    }
    if let Some(barrier) = barrier_fn {
        barrier();
    }

    let response_error = sysfs_request_error_value(msg, param);
    if response_error != 0 {
        sysfs_store_phase(phasep, SYSFS_REQUEST_PHASE_RESPONSE);
        return response_error;
    }

    if !handlep.is_null() {
        write(handlep, sysfs_request_handle_value(msg, param));
    }
    0
}

#[inline(always)]
unsafe fn sysfs_request_emit_log(log_fn: SysfsRequestLogFn, event: CInt, msg: CInt, error: CInt) {
    if let Some(log) = log_fn {
        log(event, msg, error);
    }
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_request_logged_result(
    msg: CInt,
    param: *mut c_void,
    param_rpa: CLong,
    send_fn: SysfsRequestSendFn,
    pause_fn: SysfsRequestPauseFn,
    barrier_fn: SysfsRequestBarrierFn,
    handle_dstp: *mut CLong,
    log_fn: SysfsRequestLogFn,
    phasep: *mut CInt,
) -> CInt {
    let mut handle: CLong = 0;
    let mut phase = SYSFS_REQUEST_PHASE_NONE;
    let handlep = if sysfs_handle_pointer_valid_result(handle_dstp as CULong) != 0 {
        &mut handle as *mut CLong
    } else {
        core::ptr::null_mut()
    };

    let error = sysfs_request_body_result(
        msg,
        param,
        param_rpa,
        send_fn,
        pause_fn,
        barrier_fn,
        handlep,
        &mut phase as *mut CInt,
    );
    sysfs_store_phase(phasep, phase);
    if error != 0 {
        if phase == SYSFS_REQUEST_PHASE_SEND {
            sysfs_request_emit_log(log_fn, SYSFS_REQUEST_LOG_SEND_ERROR, msg, error);
        } else if phase == SYSFS_REQUEST_PHASE_RESPONSE {
            sysfs_request_emit_log(log_fn, SYSFS_REQUEST_LOG_RESPONSE_ERROR, msg, error);
        }
        return error;
    }

    if !handlep.is_null() && !handle_dstp.is_null() {
        write(handle_dstp, handle);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_init_body_result(
    create_size: SizeT,
    mkdir_size: SizeT,
    symlink_size: SizeT,
    lookup_size: SizeT,
    unlink_size: SizeT,
    setup_size: SizeT,
    data_bufp: *mut *mut c_void,
    data_bufsizep: *mut SizeT,
    alloc_fn: SysfsInitAllocFn,
    free_fn: SysfsInitFreeFn,
    phys_fn: SysfsInitPhysFn,
    send_fn: SysfsRequestSendFn,
    pause_fn: SysfsRequestPauseFn,
    barrier_fn: SysfsRequestBarrierFn,
    stagep: *mut CInt,
    phasep: *mut CInt,
) -> CInt {
    sysfs_store_init_stage(stagep, SYSFS_INIT_STAGE_NONE);
    sysfs_store_phase(phasep, SYSFS_REQUEST_PHASE_NONE);

    if sysfs_param_sizes_valid_result(
        create_size,
        mkdir_size,
        symlink_size,
        lookup_size,
        unlink_size,
        setup_size,
    ) == 0
    {
        sysfs_store_init_stage(stagep, SYSFS_INIT_STAGE_SIZE);
        return -EINVAL;
    }

    let alloc = match alloc_fn {
        Some(alloc) => alloc,
        None => return -EINVAL,
    };
    let free = match free_fn {
        Some(free) => free,
        None => return -EINVAL,
    };
    let phys = match phys_fn {
        Some(phys) => phys,
        None => return -EINVAL,
    };
    if data_bufp.is_null() || data_bufsizep.is_null() {
        return -EINVAL;
    }

    let data_bufsize = sysfs_data_bufsize_result();
    write(data_bufsizep, data_bufsize);

    let data_buf = alloc(1, IHK_MC_AP_NOWAIT);
    if data_buf.is_null() {
        sysfs_store_init_stage(stagep, SYSFS_INIT_STAGE_DATA_ALLOC);
        return -ENOMEM;
    }
    write(data_bufp, data_buf);

    let param = alloc(1, IHK_MC_AP_NOWAIT);
    if param.is_null() {
        sysfs_store_init_stage(stagep, SYSFS_INIT_STAGE_PARAM_ALLOC);
        return -ENOMEM;
    }

    let setup = param as *mut SysfsReqSetupParam;
    (*setup).busy = 1;
    (*setup).buf_rpa = phys(data_buf);
    (*setup).bufsize = data_bufsize as CLong;

    let error = sysfs_request_body_result(
        SCD_MSG_SYSFS_REQ_SETUP,
        param,
        phys(param),
        send_fn,
        pause_fn,
        barrier_fn,
        core::ptr::null_mut(),
        phasep,
    );
    free(param, 1);
    if error != 0 {
        sysfs_store_init_stage(stagep, SYSFS_INIT_STAGE_REQUEST);
    }
    error
}

pub type SysfssShowFn = Option<
    unsafe extern "C" fn(
        ops: *mut c_void,
        instance: *mut c_void,
        buf: *mut c_void,
        bufsize: SizeT,
    ) -> CLong,
>;
pub type SysfssStoreFn = Option<
    unsafe extern "C" fn(
        ops: *mut c_void,
        instance: *mut c_void,
        buf: *mut c_void,
        size: SizeT,
    ) -> CLong,
>;
pub type SysfssReleaseFn = Option<unsafe extern "C" fn(ops: *mut c_void, instance: *mut c_void)>;
pub type SysfssSendFn =
    Option<unsafe extern "C" fn(msg: CInt, err: CInt, arg1: CLong, arg2: CLong) -> CInt>;
pub type SysfssPacketShowFn =
    Option<unsafe extern "C" fn(nodeh: CLong, ops: *mut c_void, instance: *mut c_void)>;
pub type SysfssPacketStoreFn = Option<
    unsafe extern "C" fn(nodeh: CLong, ops: *mut c_void, instance: *mut c_void, size: SizeT),
>;
pub type SysfssPacketReleaseFn =
    Option<unsafe extern "C" fn(nodeh: CLong, ops: *mut c_void, instance: *mut c_void)>;
pub type SysfssPacketUnknownFn =
    Option<unsafe extern "C" fn(msg: CInt, error: CInt, arg1: CLong, arg2: CLong, arg3: CLong)>;
pub type SysfssReqLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        nodeh: CLong,
        ops: *mut c_void,
        instance: *mut c_void,
        size: SizeT,
        error: CInt,
        packet_err: CInt,
        ssize: CLong,
    ),
>;

#[inline(always)]
unsafe fn store_sysfs_response(
    ssizep: *mut CLong,
    packet_errp: *mut CInt,
    ssize: CLong,
    err: CInt,
) {
    if !ssizep.is_null() {
        write(ssizep, ssize);
    }
    if !packet_errp.is_null() {
        write(packet_errp, err);
    }
}

#[inline(always)]
unsafe fn sysfss_send(
    send_fn: SysfssSendFn,
    msg: CInt,
    err: CInt,
    arg1: CLong,
    arg2: CLong,
) -> CInt {
    match send_fn {
        Some(send) => send(msg, err, arg1, arg2),
        None => -EIO,
    }
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_req_show_body_result(
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    data_buf: *mut c_void,
    data_bufsize: SizeT,
    show_fn: SysfssShowFn,
    send_fn: SysfssSendFn,
    ssizep: *mut CLong,
    packet_errp: *mut CInt,
) -> CInt {
    let ssize = match show_fn {
        Some(show) => show(ops, instance, data_buf, data_bufsize),
        None => sysfs_default_response_ssize_result(),
    };
    let packet_err = sysfs_response_error_result(ssize);
    let send_error = sysfss_send(send_fn, SCD_MSG_SYSFS_RESP_SHOW, packet_err, nodeh, ssize);
    store_sysfs_response(ssizep, packet_errp, ssize, packet_err);
    send_error
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_req_store_body_result(
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    data_buf: *mut c_void,
    size: SizeT,
    store_fn: SysfssStoreFn,
    send_fn: SysfssSendFn,
    ssizep: *mut CLong,
    packet_errp: *mut CInt,
) -> CInt {
    let ssize = match store_fn {
        Some(store) => store(ops, instance, data_buf, size),
        None => sysfs_default_response_ssize_result(),
    };
    let packet_err = sysfs_response_error_result(ssize);
    let send_error = sysfss_send(send_fn, SCD_MSG_SYSFS_RESP_STORE, packet_err, nodeh, ssize);
    store_sysfs_response(ssizep, packet_errp, ssize, packet_err);
    send_error
}

#[inline(always)]
unsafe fn sysfss_req_emit_log(
    log_fn: SysfssReqLogFn,
    event: CInt,
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    size: SizeT,
    error: CInt,
    packet_err: CInt,
    ssize: CLong,
) {
    if let Some(log) = log_fn {
        log(event, nodeh, ops, instance, size, error, packet_err, ssize);
    }
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_req_show_logged_result(
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    data_buf: *mut c_void,
    data_bufsize: SizeT,
    show: CULong,
    show_fn: SysfssShowFn,
    send_fn: SysfssSendFn,
    log_fn: SysfssReqLogFn,
    ssizep: *mut CLong,
    packet_errp: *mut CInt,
) -> CInt {
    let call_show_fn = if sysfs_should_call_show_result(show) != 0 {
        show_fn
    } else {
        None
    };
    let mut ssize = 0;
    let mut packet_err = 0;
    let error = sysfss_req_show_body_result(
        nodeh,
        ops,
        instance,
        data_buf,
        data_bufsize,
        call_show_fn,
        send_fn,
        &mut ssize as *mut CLong,
        &mut packet_err as *mut CInt,
    );

    if call_show_fn.is_some() && ssize < 0 {
        sysfss_req_emit_log(
            log_fn,
            SYSFSS_REQ_LOG_CALLBACK_ERROR,
            nodeh,
            ops,
            instance,
            data_bufsize,
            error,
            packet_err,
            ssize,
        );
    }
    if error != 0 {
        sysfss_req_emit_log(
            log_fn,
            SYSFSS_REQ_LOG_SEND_ERROR,
            nodeh,
            ops,
            instance,
            data_bufsize,
            error,
            packet_err,
            ssize,
        );
    }
    if sysfs_packet_error_result(error, packet_err) != 0 {
        sysfss_req_emit_log(
            log_fn,
            SYSFSS_REQ_LOG_PACKET_ERROR,
            nodeh,
            ops,
            instance,
            data_bufsize,
            error,
            packet_err,
            ssize,
        );
    }
    sysfss_req_emit_log(
        log_fn,
        SYSFSS_REQ_LOG_DEBUG,
        nodeh,
        ops,
        instance,
        data_bufsize,
        error,
        packet_err,
        ssize,
    );
    store_sysfs_response(ssizep, packet_errp, ssize, packet_err);
    error
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_req_store_logged_result(
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    data_buf: *mut c_void,
    size: SizeT,
    store: CULong,
    store_fn: SysfssStoreFn,
    send_fn: SysfssSendFn,
    log_fn: SysfssReqLogFn,
    ssizep: *mut CLong,
    packet_errp: *mut CInt,
) -> CInt {
    let call_store_fn = if sysfs_should_call_store_result(store) != 0 {
        store_fn
    } else {
        None
    };
    let mut ssize = 0;
    let mut packet_err = 0;
    let error = sysfss_req_store_body_result(
        nodeh,
        ops,
        instance,
        data_buf,
        size,
        call_store_fn,
        send_fn,
        &mut ssize as *mut CLong,
        &mut packet_err as *mut CInt,
    );

    if call_store_fn.is_some() && ssize < 0 {
        sysfss_req_emit_log(
            log_fn,
            SYSFSS_REQ_LOG_CALLBACK_ERROR,
            nodeh,
            ops,
            instance,
            size,
            error,
            packet_err,
            ssize,
        );
    }
    if error != 0 {
        sysfss_req_emit_log(
            log_fn,
            SYSFSS_REQ_LOG_SEND_ERROR,
            nodeh,
            ops,
            instance,
            size,
            error,
            packet_err,
            ssize,
        );
    }
    if sysfs_packet_error_result(error, packet_err) != 0 {
        sysfss_req_emit_log(
            log_fn,
            SYSFSS_REQ_LOG_PACKET_ERROR,
            nodeh,
            ops,
            instance,
            size,
            error,
            packet_err,
            ssize,
        );
    }
    sysfss_req_emit_log(
        log_fn,
        SYSFSS_REQ_LOG_DEBUG,
        nodeh,
        ops,
        instance,
        size,
        error,
        packet_err,
        ssize,
    );
    store_sysfs_response(ssizep, packet_errp, ssize, packet_err);
    error
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_req_release_body_result(
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    release_fn: SysfssReleaseFn,
    send_fn: SysfssSendFn,
    packet_errp: *mut CInt,
) -> CInt {
    if let Some(release) = release_fn {
        release(ops, instance);
    }
    let packet_err = sysfs_release_response_error_result();
    let send_error = sysfss_send(send_fn, SCD_MSG_SYSFS_RESP_RELEASE, packet_err, nodeh, 0);
    if !packet_errp.is_null() {
        write(packet_errp, packet_err);
    }
    send_error
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_req_release_logged_result(
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    release: CULong,
    release_fn: SysfssReleaseFn,
    send_fn: SysfssSendFn,
    log_fn: SysfssReqLogFn,
    packet_errp: *mut CInt,
) -> CInt {
    let call_release_fn = if sysfs_should_call_release_result(release) != 0 {
        release_fn
    } else {
        None
    };
    let mut packet_err = 0;
    let error = sysfss_req_release_body_result(
        nodeh,
        ops,
        instance,
        call_release_fn,
        send_fn,
        &mut packet_err as *mut CInt,
    );
    if error != 0 {
        sysfss_req_emit_log(
            log_fn,
            SYSFSS_REQ_LOG_SEND_ERROR,
            nodeh,
            ops,
            instance,
            0,
            error,
            packet_err,
            0,
        );
    }
    if sysfs_packet_error_result(error, packet_err) != 0 {
        sysfss_req_emit_log(
            log_fn,
            SYSFSS_REQ_LOG_PACKET_ERROR,
            nodeh,
            ops,
            instance,
            0,
            error,
            packet_err,
            0,
        );
    }
    sysfss_req_emit_log(
        log_fn,
        SYSFSS_REQ_LOG_DEBUG,
        nodeh,
        ops,
        instance,
        0,
        error,
        packet_err,
        0,
    );
    if !packet_errp.is_null() {
        write(packet_errp, packet_err);
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_packet_handler_body_result(
    msg: CInt,
    error: CInt,
    arg1: CLong,
    arg2: CLong,
    arg3: CLong,
    show_fn: SysfssPacketShowFn,
    store_fn: SysfssPacketStoreFn,
    release_fn: SysfssPacketReleaseFn,
    kindp: *mut CInt,
) -> CInt {
    let kind = sysfs_request_handler_kind_result(msg);

    if !kindp.is_null() {
        write(kindp, kind);
    }

    match kind {
        SYSFS_HANDLER_SHOW => match show_fn {
            Some(show) => {
                show(arg1, arg2 as *mut c_void, arg3 as *mut c_void);
                0
            }
            None => -EIO,
        },
        SYSFS_HANDLER_STORE => match store_fn {
            Some(store) => {
                store(
                    arg1,
                    arg2 as *mut c_void,
                    arg3 as *mut c_void,
                    error as SizeT,
                );
                0
            }
            None => -EIO,
        },
        SYSFS_HANDLER_RELEASE => match release_fn {
            Some(release) => {
                release(arg1, arg2 as *mut c_void, arg3 as *mut c_void);
                0
            }
            None => -EIO,
        },
        _ => -EINVAL,
    }
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_packet_handler_logged_result(
    msg: CInt,
    error: CInt,
    arg1: CLong,
    arg2: CLong,
    arg3: CLong,
    show_fn: SysfssPacketShowFn,
    store_fn: SysfssPacketStoreFn,
    release_fn: SysfssPacketReleaseFn,
    unknown_fn: SysfssPacketUnknownFn,
    kindp: *mut CInt,
) -> CInt {
    let mut kind = SYSFS_HANDLER_UNKNOWN;
    let result = sysfss_packet_handler_body_result(
        msg,
        error,
        arg1,
        arg2,
        arg3,
        show_fn,
        store_fn,
        release_fn,
        &mut kind as *mut CInt,
    );
    if !kindp.is_null() {
        write(kindp, kind);
    }
    if kind == SYSFS_HANDLER_UNKNOWN {
        if let Some(unknown) = unknown_fn {
            unknown(msg, error, arg1, arg2, arg3);
        }
    }
    result
}

#[no_mangle]
pub extern "C" fn procfs_mem_reason_result(readwrite: CInt) -> CULong {
    if readwrite != 0 {
        PF_POPULATE | PF_WRITE | PF_USER
    } else {
        PF_POPULATE | PF_USER
    }
}

#[no_mangle]
pub extern "C" fn procfs_mem_chunk_size_result(offset: CULong, left: CULong) -> CInt {
    let pos = page_offset(offset);
    let size = PAGE_SIZE - pos;

    if size > left {
        left as CInt
    } else {
        size as CInt
    }
}

#[no_mangle]
pub unsafe extern "C" fn procfs_mem_copy_body_result(
    vm: *mut c_void,
    page_table: *mut c_void,
    buf: *mut c_void,
    mut offset: CULong,
    count: CULong,
    readwrite: CInt,
    page_fault_fn: ProcfsMemPageFaultFn,
    virt_to_phys_fn: ProcfsMemVirtToPhysFn,
    is_memory_fn: ProcfsMemIsMemoryFn,
    phys_to_virt_fn: ProcfsMemPhysToVirtFn,
    copy_fn: ProcfsMemCopyFn,
) -> CInt {
    let page_fault = match page_fault_fn {
        Some(page_fault) => page_fault,
        None => return -EINVAL,
    };
    let virt_to_phys = match virt_to_phys_fn {
        Some(virt_to_phys) => virt_to_phys,
        None => return -EINVAL,
    };
    let is_memory = match is_memory_fn {
        Some(is_memory) => is_memory,
        None => return -EINVAL,
    };
    let phys_to_virt = match phys_to_virt_fn {
        Some(phys_to_virt) => phys_to_virt,
        None => return -EINVAL,
    };
    let copy = match copy_fn {
        Some(copy) => copy,
        None => return -EINVAL,
    };
    if vm.is_null() || page_table.is_null() || buf.is_null() {
        return -EINVAL;
    }

    let reason = procfs_mem_reason_result(readwrite);
    let mut left = count;
    let mut ans: CInt = 0;
    if procfs_zero_length_result(left) != 0 {
        return 0;
    }

    while left != 0 {
        let mut phys: CULong = 0;
        let size = procfs_mem_chunk_size_result(offset, left);
        let usize_size = size as SizeT;

        if page_fault(vm, offset, reason) != 0 {
            return if ans == 0 { -EIO } else { ans };
        }
        if virt_to_phys(page_table, offset, &raw mut phys) != 0 {
            return if ans == 0 { -EIO } else { ans };
        }
        if is_memory(phys, phys.wrapping_add(usize_size as CULong)) == 0 {
            return -EIO;
        }

        let va = phys_to_virt(phys);
        let procfs_buf = buf.cast::<u8>().add(ans as SizeT).cast::<c_void>();
        if readwrite != 0 {
            copy(va, procfs_buf, usize_size);
        } else {
            copy(procfs_buf, va, usize_size);
        }
        offset = offset.wrapping_add(usize_size as CULong);
        left = left.wrapping_sub(usize_size as CULong);
        ans = ans.wrapping_add(size);
    }
    ans
}

unsafe fn procfs_add_bytes(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    bytes: *const u8,
    len: SizeT,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    let ptr = if bytes.is_null() && len == 0 {
        b"\0".as_ptr()
    } else {
        bytes
    };
    if ptr.is_null() || len > CInt::MAX as SizeT {
        return -EINVAL;
    }
    procfs_buf_add_result(
        top,
        cur,
        ptr.cast::<c_void>(),
        len as CInt,
        alloc_fn,
        free_top_fn,
        copy_fn,
    )
}

unsafe fn procfs_add_cstr(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    text: *const u8,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    if text.is_null() {
        return -EINVAL;
    }
    procfs_add_bytes(
        top,
        cur,
        text,
        sysfs_c_strlen(text.cast::<i8>()),
        alloc_fn,
        free_top_fn,
        copy_fn,
    )
}

unsafe fn procfs_cpu_line(cpu: CInt, line: *mut u8) -> CInt {
    if cpu < 0 {
        return -EINVAL;
    }

    if line.is_null() {
        return -EINVAL;
    }

    *line.add(0) = b'c';
    *line.add(1) = b'p';
    *line.add(2) = b'u';
    let mut pos = 3usize;
    let mut value = cpu as u32;
    let mut digits = [0u8; 10];
    let digits_ptr = digits.as_mut_ptr();
    let mut nr_digits = 0usize;

    loop {
        *digits_ptr.add(nr_digits) = b'0' + (value % 10) as u8;
        nr_digits += 1;
        value /= 10;
        if value == 0 {
            break;
        }
    }
    let digits_read = digits.as_ptr();
    while nr_digits != 0 {
        nr_digits -= 1;
        *line.add(pos) = *digits_read.add(nr_digits);
        pos += 1;
    }
    *line.add(pos) = b'\n';
    (pos + 1) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn procfs_root_entry_body_result(
    entry_kind: CInt,
    version: *const u8,
    buildid: *const u8,
    num_processors: CInt,
    count: CInt,
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    match entry_kind {
        PROCFS_ENTRY_MCKERNEL => {
            let mut error = procfs_add_cstr(top, cur, version, alloc_fn, free_top_fn, copy_fn);
            if error != 0 {
                return error;
            }
            error = procfs_add_bytes(top, cur, b"-".as_ptr(), 1, alloc_fn, free_top_fn, copy_fn);
            if error != 0 {
                return error;
            }
            error = procfs_add_cstr(top, cur, buildid, alloc_fn, free_top_fn, copy_fn);
            if error != 0 {
                return error;
            }
            procfs_add_bytes(top, cur, b"\n".as_ptr(), 1, alloc_fn, free_top_fn, copy_fn)
        }
        PROCFS_ENTRY_STAT => {
            if count < 0 || num_processors < 0 {
                return -EINVAL;
            }
            let mut cpu = 0;
            while cpu < num_processors {
                let mut line = core::mem::MaybeUninit::<[u8; 32]>::uninit();
                let line_ptr = line.as_mut_ptr().cast::<u8>();
                let len = procfs_cpu_line(cpu, line_ptr);
                if len < 0 {
                    return len;
                }
                if procfs_format_error_result(len, count) != 0 {
                    return -EIO;
                }
                let error = procfs_add_bytes(
                    top,
                    cur,
                    line_ptr,
                    len as SizeT,
                    alloc_fn,
                    free_top_fn,
                    copy_fn,
                );
                if error != 0 {
                    return error;
                }
                cpu += 1;
            }
            0
        }
        _ => -EINVAL,
    }
}

#[no_mangle]
pub unsafe extern "C" fn procfs_pid_simple_entry_body_result(
    entry_kind: CInt,
    saved_auxv: *const c_void,
    saved_cmdline: *const u8,
    saved_cmdline_len: u32,
    comm_fallback: *const u8,
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    match entry_kind {
        PROCFS_ENTRY_AUXV => procfs_add_bytes(
            top,
            cur,
            saved_auxv.cast::<u8>(),
            procfs_auxv_limit_result() as SizeT,
            alloc_fn,
            free_top_fn,
            copy_fn,
        ),
        PROCFS_ENTRY_CMDLINE => {
            let limit = procfs_cmdline_limit_result(saved_cmdline as CULong, saved_cmdline_len);
            let source = if procfs_pointer_present_result(saved_cmdline as CULong) != 0 {
                saved_cmdline
            } else {
                b"\0".as_ptr()
            };
            procfs_add_bytes(
                top,
                cur,
                source,
                limit as SizeT,
                alloc_fn,
                free_top_fn,
                copy_fn,
            )
        }
        PROCFS_ENTRY_COMM => {
            let basename = procfs_comm_basename_result(saved_cmdline as CULong);
            let comm = procfs_comm_name_result(comm_fallback as CULong, basename) as *const u8;
            let mut error = procfs_add_cstr(top, cur, comm, alloc_fn, free_top_fn, copy_fn);
            if error != 0 {
                return error;
            }
            error = procfs_add_bytes(top, cur, b"\n".as_ptr(), 1, alloc_fn, free_top_fn, copy_fn);
            error
        }
        _ => -EINVAL,
    }
}

#[no_mangle]
pub unsafe extern "C" fn procfs_pagemap_range_result(
    offset: CULong,
    count: CInt,
    startp: *mut CULong,
    endp: *mut CULong,
) -> CInt {
    if (offset % core::mem::size_of::<CULong>() as CULong) != 0
        || ((count as CULong) % core::mem::size_of::<CULong>() as CULong) != 0
    {
        return -EINVAL;
    }

    let start = (offset / core::mem::size_of::<CULong>() as CULong) << PAGE_SHIFT;
    let end = start
        .wrapping_add(((count as CULong) / core::mem::size_of::<CULong>() as CULong) << PAGE_SHIFT);
    write(startp, start);
    write(endp, end);
    0
}

#[no_mangle]
pub unsafe extern "C" fn procfs_pagemap_body_result(
    page_table: *mut c_void,
    buf: *mut CULong,
    mut start: CULong,
    end: CULong,
    count: CInt,
    value_fn: ProcfsPagemapValueFn,
) -> CInt {
    let value = match value_fn {
        Some(value) => value,
        None => return -EINVAL,
    };
    if page_table.is_null() || buf.is_null() {
        return -EINVAL;
    }

    let mut out = buf;
    while start < end {
        write(out, value(page_table, start));
        start = procfs_pagemap_next_result(start);
        out = out.add(1);
    }
    count
}

const PROCFS_RANGE_FIELD_START: CInt = 1;
const PROCFS_RANGE_FIELD_END: CInt = 2;
const PROCFS_RANGE_FIELD_FLAG: CInt = 3;

fn procfs_u64_dec_len(mut value: CULong) -> SizeT {
    let mut len = 1usize;

    while value >= 10 {
        value /= 10;
        len += 1;
    }
    len
}

fn procfs_i64_dec_len(value: CLong) -> SizeT {
    if value < 0 {
        1 + procfs_u64_dec_len(value.wrapping_neg() as CULong)
    } else {
        procfs_u64_dec_len(value as CULong)
    }
}

fn procfs_u64_hex_len(mut value: CULong) -> SizeT {
    let mut len = 1usize;

    while value >= 16 {
        value >>= 4;
        len += 1;
    }
    len
}

fn procfs_line_len_valid(len: SizeT, count: CInt) -> CInt {
    if len > CInt::MAX as SizeT {
        return -EINVAL;
    }
    if procfs_format_error_result(len as CInt, count) != 0 {
        return -EIO;
    }
    0
}

unsafe fn procfs_add_literal(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    literal: &'static [u8],
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    procfs_add_bytes(
        top,
        cur,
        literal.as_ptr(),
        literal.len(),
        alloc_fn,
        free_top_fn,
        copy_fn,
    )
}

unsafe fn procfs_add_byte(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    byte: u8,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    procfs_add_bytes(
        top,
        cur,
        (&byte as *const u8).cast::<u8>(),
        1,
        alloc_fn,
        free_top_fn,
        copy_fn,
    )
}

unsafe fn procfs_add_u64_dec_width(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    value: CULong,
    min_width: SizeT,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    let mut out = core::mem::MaybeUninit::<[u8; 32]>::uninit();
    let outp = out.as_mut_ptr().cast::<u8>();
    let mut digits = core::mem::MaybeUninit::<[u8; 20]>::uninit();
    let digitp = digits.as_mut_ptr().cast::<u8>();
    let digit_read = digitp as *const u8;
    let mut tmp = value;
    let mut nr_digits = 0usize;
    let mut pos = 0usize;
    let width = {
        let dec_len = procfs_u64_dec_len(value);
        if min_width > dec_len {
            min_width
        } else {
            dec_len
        }
    };

    loop {
        *digitp.add(nr_digits) = b'0' + (tmp % 10) as u8;
        nr_digits += 1;
        tmp /= 10;
        if tmp == 0 {
            break;
        }
    }
    while pos + nr_digits < width {
        *outp.add(pos) = b' ';
        pos += 1;
    }
    while nr_digits != 0 {
        nr_digits -= 1;
        *outp.add(pos) = *digit_read.add(nr_digits);
        pos += 1;
    }
    procfs_add_bytes(top, cur, outp, pos, alloc_fn, free_top_fn, copy_fn)
}

unsafe fn procfs_add_u64_dec(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    value: CULong,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    procfs_add_u64_dec_width(top, cur, value, 0, alloc_fn, free_top_fn, copy_fn)
}

unsafe fn procfs_add_i64_dec(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    value: CLong,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    if value < 0 {
        let error = procfs_add_literal(top, cur, b"-", alloc_fn, free_top_fn, copy_fn);
        if error != 0 {
            return error;
        }
        procfs_add_u64_dec(
            top,
            cur,
            value.wrapping_neg() as CULong,
            alloc_fn,
            free_top_fn,
            copy_fn,
        )
    } else {
        procfs_add_u64_dec(top, cur, value as CULong, alloc_fn, free_top_fn, copy_fn)
    }
}

unsafe fn procfs_add_u64_hex_width(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    value: CULong,
    min_width: SizeT,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    let mut out = core::mem::MaybeUninit::<[u8; 32]>::uninit();
    let outp = out.as_mut_ptr().cast::<u8>();
    let width = {
        let hex_len = procfs_u64_hex_len(value);
        if min_width > hex_len {
            min_width
        } else {
            hex_len
        }
    };
    let hex = b"0123456789abcdef".as_ptr();
    let mut tmp = value;
    let mut pos = width;

    while pos != 0 {
        pos -= 1;
        *outp.add(pos) = *hex.add((tmp & 0xf) as usize);
        tmp >>= 4;
    }
    procfs_add_bytes(top, cur, outp, width, alloc_fn, free_top_fn, copy_fn)
}

fn procfs_maps_default_path(path_kind: CInt) -> (&'static [u8], SizeT) {
    match path_kind {
        PROCFS_MAPS_PATH_VDSO => (b"[vdso]", 6),
        PROCFS_MAPS_PATH_VVAR => (b"[vvar]", 6),
        PROCFS_MAPS_PATH_STACK => (b"[stack]", 7),
        PROCFS_MAPS_PATH_HEAP => (b"[heap]", 6),
        _ => (b"", 0),
    }
}

unsafe fn procfs_add_maps_path(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    path: *const u8,
    default_path: &'static [u8],
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    if !path.is_null() {
        procfs_add_cstr(top, cur, path, alloc_fn, free_top_fn, copy_fn)
    } else {
        procfs_add_literal(top, cur, default_path, alloc_fn, free_top_fn, copy_fn)
    }
}

unsafe fn procfs_add_maps_line(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    start: CULong,
    end: CULong,
    flags: CULong,
    path: *const u8,
    default_path: &'static [u8],
    path_len: SizeT,
    count: CInt,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    let line_len = 12 + 1 + 12 + 1 + 4 + b" 0 0:0 0\t\t\t".len() + path_len + 1;
    let mut error = procfs_line_len_valid(line_len, count);

    if error != 0 {
        return error;
    }
    error = procfs_add_u64_hex_width(top, cur, start, 12, alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b"-", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_u64_hex_width(top, cur, end, 12, alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b" ", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(
        top,
        cur,
        procfs_maps_read_char_result(flags),
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(
        top,
        cur,
        procfs_maps_write_char_result(flags),
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(
        top,
        cur,
        procfs_maps_exec_char_result(flags),
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(
        top,
        cur,
        procfs_maps_private_char_result(flags),
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b" 0 0:0 0\t\t\t", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_maps_path(top, cur, path, default_path, alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    procfs_add_literal(top, cur, b"\n", alloc_fn, free_top_fn, copy_fn)
}

#[no_mangle]
pub unsafe extern "C" fn procfs_maps_body_result(
    vm: *mut c_void,
    mut range: *mut c_void,
    vdso_addr: CULong,
    vvar_addr: CULong,
    brk_start: CULong,
    brk_end_allocated: CULong,
    count: CInt,
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
    range_ulong_fn: ProcfsRangeUlongFn,
    range_path_fn: ProcfsRangePathFn,
    range_next_fn: ProcfsRangeNextFn,
) -> CInt {
    let (Some(range_ulong), Some(range_path), Some(range_next)) =
        (range_ulong_fn, range_path_fn, range_next_fn)
    else {
        return -EINVAL;
    };

    while !range.is_null() {
        let start = range_ulong(range, PROCFS_RANGE_FIELD_START);
        let end = range_ulong(range, PROCFS_RANGE_FIELD_END);
        let flags = range_ulong(range, PROCFS_RANGE_FIELD_FLAG);
        let path = range_path(range);
        let path_kind = procfs_maps_path_kind_result(
            start,
            end,
            flags,
            vdso_addr,
            vvar_addr,
            brk_start,
            brk_end_allocated,
        );
        let (default_path, default_len) = procfs_maps_default_path(path_kind);
        let path_len = if path.is_null() {
            default_len
        } else {
            sysfs_c_strlen(path.cast::<i8>())
        };
        let error = procfs_add_maps_line(
            top,
            cur,
            start,
            end,
            flags,
            path,
            default_path,
            path_len,
            count,
            alloc_fn,
            free_top_fn,
            copy_fn,
        );
        if error != 0 {
            return error;
        }
        range = range_next(vm, range);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn procfs_locked_size_body_result(
    vm: *mut c_void,
    mut range: *mut c_void,
    range_ulong_fn: ProcfsRangeUlongFn,
    range_next_fn: ProcfsRangeNextFn,
) -> CULong {
    let (Some(range_ulong), Some(range_next)) = (range_ulong_fn, range_next_fn) else {
        return 0;
    };
    let mut lockedsize = 0;

    while !range.is_null() {
        lockedsize = procfs_locked_size_add_result(
            lockedsize,
            range_ulong(range, PROCFS_RANGE_FIELD_START),
            range_ulong(range, PROCFS_RANGE_FIELD_END),
            range_ulong(range, PROCFS_RANGE_FIELD_FLAG),
        );
        range = range_next(vm, range);
    }
    lockedsize
}

fn procfs_status_state_name(status: CInt) -> &'static [u8] {
    match procfs_status_state_result(status) {
        PROCFS_STATUS_STOPPED => b"T (stopped)",
        PROCFS_STATUS_TRACED => b"T (tracing stop)",
        PROCFS_STATUS_EXITED => b"Z (zombie)",
        _ => b"R (running)",
    }
}

unsafe fn procfs_add_status_head(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    input: *const ProcfsStatusBodyInput,
    state: &'static [u8],
    count: CInt,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    let locked_kb = procfs_locked_kb_result((*input).lockedsize);
    let len = b"Pid:\t".len()
        + procfs_i64_dec_len((*input).pid as CLong)
        + b"\nUid:\t".len()
        + procfs_i64_dec_len((*input).ruid as CLong)
        + 1
        + procfs_i64_dec_len((*input).euid as CLong)
        + 1
        + procfs_i64_dec_len((*input).suid as CLong)
        + 1
        + procfs_i64_dec_len((*input).fsuid as CLong)
        + b"\nGid:\t".len()
        + procfs_i64_dec_len((*input).rgid as CLong)
        + 1
        + procfs_i64_dec_len((*input).egid as CLong)
        + 1
        + procfs_i64_dec_len((*input).sgid as CLong)
        + 1
        + procfs_i64_dec_len((*input).fsgid as CLong)
        + b"\nState:\t".len()
        + state.len()
        + b"\nVmLck:\t".len()
        + {
            let dec = procfs_u64_dec_len(locked_kb);
            if dec > 9 {
                dec
            } else {
                9
            }
        }
        + b" kB\nThreads:\t".len()
        + procfs_i64_dec_len((*input).nr_threads as CLong)
        + 1;
    let mut error = procfs_line_len_valid(len, count);

    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b"Pid:\t", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).pid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b"\nUid:\t", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).ruid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(top, cur, b'\t', alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).euid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(top, cur, b'\t', alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).suid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(top, cur, b'\t', alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).fsuid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b"\nGid:\t", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).rgid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(top, cur, b'\t', alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).egid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(top, cur, b'\t', alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).sgid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(top, cur, b'\t', alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).fsgid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b"\nState:\t", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, state, alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b"\nVmLck:\t", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_u64_dec_width(top, cur, locked_kb, 9, alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b" kB\nThreads:\t", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).nr_threads as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    procfs_add_literal(top, cur, b"\n", alloc_fn, free_top_fn, copy_fn)
}

unsafe fn procfs_add_status_cstr_line(
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    prefix: &'static [u8],
    value: *const u8,
    count: CInt,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    if value.is_null() {
        return -EINVAL;
    }
    let value_len = sysfs_c_strlen(value.cast::<i8>());
    let error = procfs_line_len_valid(prefix.len() + value_len + 1, count);

    if error != 0 {
        return error;
    }
    let mut add_error = procfs_add_literal(top, cur, prefix, alloc_fn, free_top_fn, copy_fn);
    if add_error != 0 {
        return add_error;
    }
    add_error = procfs_add_cstr(top, cur, value, alloc_fn, free_top_fn, copy_fn);
    if add_error != 0 {
        return add_error;
    }
    procfs_add_literal(top, cur, b"\n", alloc_fn, free_top_fn, copy_fn)
}

#[no_mangle]
pub unsafe extern "C" fn procfs_status_body_result(
    input: *const ProcfsStatusBodyInput,
    count: CInt,
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    if input.is_null() {
        return -EINVAL;
    }
    let state = procfs_status_state_name((*input).status);
    let mut error = procfs_add_status_head(
        top,
        cur,
        input,
        state,
        count,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );

    if error != 0 {
        return error;
    }
    error = procfs_add_status_cstr_line(
        top,
        cur,
        b"Cpus_allowed:\t",
        (*input).cpu_bitmask,
        count,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_status_cstr_line(
        top,
        cur,
        b"Cpus_allowed_list:\t",
        (*input).cpu_list,
        count,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_status_cstr_line(
        top,
        cur,
        b"Mems_allowed:\t",
        (*input).numa_bitmask,
        count,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    procfs_add_status_cstr_line(
        top,
        cur,
        b"Mems_allowed_list:\t",
        (*input).numa_list,
        count,
        alloc_fn,
        free_top_fn,
        copy_fn,
    )
}

const PROCFS_STAT_AFTER_PID_BEFORE_THREADS: &[u8] = b" 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ";
const PROCFS_STAT_AFTER_THREADS_BEFORE_CPU: &[u8] = b" 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ";
const PROCFS_STAT_AFTER_CPU: &[u8] = b" 0 0 0 0 0\n";

#[no_mangle]
pub unsafe extern "C" fn procfs_stat_body_result(
    input: *const ProcfsStatBodyInput,
    count: CInt,
    top: *mut *mut ProcfsBuffer,
    cur: *mut *mut ProcfsBuffer,
    alloc_fn: ProcfsBufAllocFn,
    free_top_fn: ProcfsBufFreeTopFn,
    copy_fn: ProcfsBufCopyFn,
) -> CInt {
    if input.is_null() || (*input).comm.is_null() {
        return -EINVAL;
    }
    let comm_len = sysfs_c_strlen((*input).comm.cast::<i8>());
    let line_len = procfs_i64_dec_len((*input).tid as CLong)
        + b" (".len()
        + comm_len
        + b") ".len()
        + 1
        + 1
        + procfs_i64_dec_len((*input).ppid as CLong)
        + 1
        + procfs_i64_dec_len((*input).pid as CLong)
        + PROCFS_STAT_AFTER_PID_BEFORE_THREADS.len()
        + procfs_i64_dec_len((*input).nr_threads as CLong)
        + PROCFS_STAT_AFTER_THREADS_BEFORE_CPU.len()
        + procfs_i64_dec_len((*input).cpu_id as CLong)
        + PROCFS_STAT_AFTER_CPU.len();
    let mut error = procfs_line_len_valid(line_len, count);

    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).tid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b" (", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_cstr(top, cur, (*input).comm, alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b") ", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_byte(top, cur, (*input).state, alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b" ", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).ppid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(top, cur, b" ", alloc_fn, free_top_fn, copy_fn);
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).pid as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(
        top,
        cur,
        PROCFS_STAT_AFTER_PID_BEFORE_THREADS,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).nr_threads as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_literal(
        top,
        cur,
        PROCFS_STAT_AFTER_THREADS_BEFORE_CPU,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    error = procfs_add_i64_dec(
        top,
        cur,
        (*input).cpu_id as CLong,
        alloc_fn,
        free_top_fn,
        copy_fn,
    );
    if error != 0 {
        return error;
    }
    procfs_add_literal(
        top,
        cur,
        PROCFS_STAT_AFTER_CPU,
        alloc_fn,
        free_top_fn,
        copy_fn,
    )
}

#[no_mangle]
pub extern "C" fn procfs_status_state_result(status: CInt) -> CInt {
    if status == PS_STOPPED {
        PROCFS_STATUS_STOPPED
    } else if status == PS_TRACED {
        PROCFS_STATUS_TRACED
    } else if status == PS_EXITED {
        PROCFS_STATUS_EXITED
    } else {
        PROCFS_STATUS_RUNNING
    }
}

#[no_mangle]
pub extern "C" fn procfs_thread_stat_state_result(status: CInt, in_syscall_offload: CInt) -> u8 {
    match status & 0x3f {
        PS_INTERRUPTIBLE => b'S',
        PS_UNINTERRUPTIBLE => b'D',
        PS_ZOMBIE => b'Z',
        PS_EXITED => b'X',
        PS_STOPPED => b'T',
        PS_RUNNING | _ => {
            if in_syscall_offload > 0 {
                b'S'
            } else {
                b'R'
            }
        }
    }
}

#[no_mangle]
pub extern "C" fn procfs_default_count_result() -> CInt {
    PAGE_SIZE as CInt
}

#[no_mangle]
pub extern "C" fn procfs_remote_count_result(mapped_addr: CULong, count: CInt) -> CInt {
    count + (mapped_addr & (PAGE_SIZE - 1)) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_remote_npages_result(count: CInt) -> CInt {
    (count + (PAGE_SIZE as CInt - 1)) / PAGE_SIZE as CInt
}

#[no_mangle]
pub extern "C" fn procfs_format_error_result(ans: CInt, count: CInt) -> CInt {
    (ans < 0 || ans > count) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_locked_kb_result(lockedsize: CULong) -> CULong {
    lockedsize.wrapping_add(1023) >> 10
}

#[no_mangle]
pub extern "C" fn procfs_maps_read_char_result(flags: CULong) -> u8 {
    if (flags & VR_PROT_READ) != 0 {
        b'r'
    } else {
        b'-'
    }
}

#[no_mangle]
pub extern "C" fn procfs_maps_write_char_result(flags: CULong) -> u8 {
    if (flags & VR_PROT_WRITE) != 0 {
        b'w'
    } else {
        b'-'
    }
}

#[no_mangle]
pub extern "C" fn procfs_maps_exec_char_result(flags: CULong) -> u8 {
    if (flags & VR_PROT_EXEC) != 0 {
        b'x'
    } else {
        b'-'
    }
}

#[no_mangle]
pub extern "C" fn procfs_maps_private_char_result(flags: CULong) -> u8 {
    if (flags & VR_PRIVATE) != 0 {
        b'p'
    } else {
        b's'
    }
}

#[no_mangle]
pub extern "C" fn procfs_maps_path_kind_result(
    range_start: CULong,
    range_end: CULong,
    range_flags: CULong,
    vdso_addr: CULong,
    vvar_addr: CULong,
    brk_start: CULong,
    brk_end_allocated: CULong,
) -> CInt {
    if range_start == vdso_addr {
        PROCFS_MAPS_PATH_VDSO
    } else if range_start == vvar_addr {
        PROCFS_MAPS_PATH_VVAR
    } else if (range_flags & VR_STACK) != 0 {
        PROCFS_MAPS_PATH_STACK
    } else if range_start >= brk_start && range_end <= brk_end_allocated {
        PROCFS_MAPS_PATH_HEAP
    } else {
        PROCFS_MAPS_PATH_NONE
    }
}

#[no_mangle]
pub extern "C" fn procfs_pagemap_next_result(start: CULong) -> CULong {
    start.wrapping_add(PAGE_SIZE)
}

#[no_mangle]
pub extern "C" fn procfs_auxv_limit_result() -> u32 {
    (AUXV_LEN as u32) * core::mem::size_of::<CULong>() as u32
}

#[no_mangle]
pub extern "C" fn procfs_cmdline_limit_result(
    saved_cmdline: CULong,
    saved_cmdline_len: u32,
) -> u32 {
    if saved_cmdline != 0 {
        saved_cmdline_len
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn procfs_is_release_result(msg: CInt) -> CInt {
    (msg == SCD_MSG_PROCFS_RELEASE) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_root_matched_result(sscanf_ret: CInt) -> CInt {
    (sscanf_ret == 1) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_osnum_match_result(osnum: CInt, requested_osnum: CInt) -> CInt {
    (osnum == requested_osnum) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_zero_length_result(left: CULong) -> CInt {
    (left == 0) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_locked_size_add_result(
    lockedsize: CULong,
    range_start: CULong,
    range_end: CULong,
    flags: CULong,
) -> CULong {
    if (flags & VR_LOCKED) != 0 {
        lockedsize.wrapping_add(range_end.wrapping_sub(range_start))
    } else {
        lockedsize
    }
}

#[no_mangle]
pub extern "C" fn procfs_bitmask_next_offset_result(offset: CInt, written: CInt) -> CInt {
    offset.wrapping_add(written).wrapping_add(1)
}

#[no_mangle]
pub extern "C" fn procfs_pbuf_is_empty_result(pbuf: CULong) -> CInt {
    (pbuf == CULong::MAX) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_backlog_needed_result(resultp: CULong) -> CInt {
    (resultp == 0) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_lock_failed_action_result(resultp: CULong) -> CInt {
    if procfs_backlog_needed_result(resultp) != 0 {
        PROCFS_LOCK_ACTION_BACKLOG
    } else {
        PROCFS_LOCK_ACTION_EAGAIN
    }
}

#[no_mangle]
pub extern "C" fn procfs_lock_retry_result() -> CInt {
    -EAGAIN
}

#[no_mangle]
pub extern "C" fn procfs_thread_tid_result(task_match: CInt, parsed_tid: CInt, pid: CInt) -> CInt {
    if task_match != 0 {
        parsed_tid
    } else {
        pid
    }
}

#[no_mangle]
pub extern "C" fn procfs_task_missing_terminal_result(task_match: CInt) -> CInt {
    (task_match != 0) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_pointer_present_result(ptr: CULong) -> CInt {
    (ptr != 0) as CInt
}

#[no_mangle]
pub extern "C" fn procfs_buffer_chain_attach_result(pbuf: CULong, buf_top: CULong) -> CInt {
    (procfs_pbuf_is_empty_result(pbuf) != 0 && buf_top != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn procfs_entry_kind_result(name: *const u8) -> CInt {
    if cstr_eq(name, b"mckernel\0") {
        PROCFS_ENTRY_MCKERNEL
    } else if cstr_eq(name, b"stat\0") {
        PROCFS_ENTRY_STAT
    } else if cstr_eq(name, b"cpuinfo\0") {
        PROCFS_ENTRY_CPUINFO
    } else if cstr_eq(name, b"mem\0") {
        PROCFS_ENTRY_MEM
    } else if cstr_eq(name, b"maps\0") {
        PROCFS_ENTRY_MAPS
    } else if cstr_eq(name, b"pagemap\0") {
        PROCFS_ENTRY_PAGEMAP
    } else if cstr_eq(name, b"status\0") {
        PROCFS_ENTRY_STATUS
    } else if cstr_eq(name, b"auxv\0") {
        PROCFS_ENTRY_AUXV
    } else if cstr_eq(name, b"cmdline\0") {
        PROCFS_ENTRY_CMDLINE
    } else if cstr_eq(name, b"comm\0") {
        PROCFS_ENTRY_COMM
    } else {
        PROCFS_ENTRY_UNKNOWN
    }
}

#[no_mangle]
pub unsafe extern "C" fn procfs_comm_basename_result(saved_cmdline: CULong) -> CULong {
    let ptr = saved_cmdline as *const u8;

    if ptr.is_null() {
        return 0;
    }

    let mut cur = ptr;
    let mut base = ptr;
    loop {
        let ch = *cur;

        if ch == b'/' {
            base = cur.add(1);
        }
        if ch == 0 {
            break;
        }
        cur = cur.add(1);
    }

    base as CULong
}

#[no_mangle]
pub extern "C" fn procfs_comm_name_result(fallback: CULong, basename: CULong) -> CULong {
    if basename != 0 {
        basename
    } else {
        fallback
    }
}

#[no_mangle]
pub extern "C" fn pager_linux_io_retry_result(ret: CLong) -> CInt {
    (ret == -(EINTR as CLong)) as CInt
}

#[no_mangle]
pub extern "C" fn pager_linux_io_stop_result(ret: CLong) -> CInt {
    (ret <= 0) as CInt
}

#[no_mangle]
pub extern "C" fn pager_linux_io_first_result(done: CLong) -> CInt {
    (done == 0) as CInt
}

#[no_mangle]
pub extern "C" fn pager_linux_io_advance_result(done: CLong, ret: CLong) -> CLong {
    done.wrapping_add(ret)
}

#[no_mangle]
pub extern "C" fn pager_linux_io_remaining_result(remaining: SizeT, ret: CLong) -> SizeT {
    remaining.wrapping_sub(ret as SizeT)
}

#[no_mangle]
pub extern "C" fn pager_linux_io_next_buf_result(buf: CULong, ret: CLong) -> CULong {
    buf.wrapping_add(ret as CULong)
}

#[no_mangle]
pub extern "C" fn pager_linux_io_complete_result(done: CLong, target: SizeT) -> CInt {
    (done as SizeT == target) as CInt
}

#[no_mangle]
pub extern "C" fn pager_copy_fault_retry_result(faulted: CInt) -> CInt {
    (faulted == 0) as CInt
}

#[no_mangle]
pub extern "C" fn pager_copy_fault_error_result(ret: CInt) -> CInt {
    if ret != 0 {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn pager_myalloc_fits_result(allocated: SizeT, request: SizeT, size: SizeT) -> CInt {
    (allocated.wrapping_add(request) < size) as CInt
}

#[no_mangle]
pub extern "C" fn pager_myalloc_next_alloced_result(allocated: SizeT, request: SizeT) -> SizeT {
    allocated.wrapping_add(request)
}

#[no_mangle]
pub extern "C" fn pager_copy_size_error_result(size: SizeT) -> CInt {
    if size > PAGE_SIZE as SizeT {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn pager_fault_addr_result(addr: CULong) -> CULong {
    addr & PAGE_MASK
}

#[no_mangle]
pub extern "C" fn pager_read_chunk_size_result(off: SizeT, size: SizeT) -> SizeT {
    let chunk = size.wrapping_sub(off);

    if chunk > PAGE_SIZE as SizeT {
        PAGE_SIZE as SizeT
    } else {
        chunk
    }
}

#[no_mangle]
pub extern "C" fn pager_arealist_tail_room_result(tail_count: CInt) -> CInt {
    if tail_count < MLOCKADDRS_SIZE - 1 {
        MLOCKADDRS_SIZE - tail_count
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn pager_arealist_count_add_result(count: CInt, add: CInt) -> CInt {
    count.wrapping_add(add)
}

#[no_mangle]
pub extern "C" fn pager_addrpair_size_result(start: CULong, end: CULong) -> CLong {
    end.wrapping_sub(start) as CLong
}

#[no_mangle]
pub extern "C" fn pager_file_pos_result(off: CLong, total_size: CLong) -> CLong {
    off.wrapping_add(total_size)
}

#[no_mangle]
pub extern "C" fn pager_arealist_write_result(
    written: CLong,
    count: CInt,
    entry_size: SizeT,
) -> CLong {
    if written as SizeT != (count as SizeT).wrapping_mul(entry_size) {
        -1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn pager_mlock_more_result(start: CULong) -> CInt {
    (start == CULong::MAX) as CInt
}

#[no_mangle]
pub extern "C" fn pager_mlock_next_start_result(end: CULong) -> CULong {
    end
}

#[no_mangle]
pub extern "C" fn pager_mlock_container_empty_result(
    from: CULong,
    tail: CULong,
    ccount: CInt,
    tail_count: CInt,
) -> CInt {
    (from == tail && ccount == tail_count) as CInt
}

#[no_mangle]
pub extern "C" fn pager_mlock_needs_next_result(ccount: CInt, cur_count: CInt) -> CInt {
    (ccount == cur_count) as CInt
}

#[no_mangle]
pub extern "C" fn pager_mlock_reset_count_result() -> CInt {
    1
}

#[no_mangle]
pub extern "C" fn pager_mlock_next_count_result(count: CInt) -> CInt {
    count.wrapping_add(1)
}

#[no_mangle]
pub extern "C" fn pager_pagein_data_pos_result(
    swap_count: u32,
    mlock_count: u32,
    header_size: SizeT,
    area_size: SizeT,
) -> CLong {
    header_size
        .wrapping_add((swap_count as SizeT).wrapping_mul(area_size))
        .wrapping_add((mlock_count as SizeT).wrapping_mul(area_size)) as CLong
}

#[no_mangle]
pub extern "C" fn pager_pageout_args_result(
    fname: CULong,
    buf: CULong,
    size: SizeT,
    user_start: CULong,
    user_end: CULong,
) -> CInt {
    let user_len = user_end.wrapping_sub(user_start);

    if fname < user_start
        || fname >= user_end
        || buf < user_start
        || buf >= user_end
        || size > user_len as SizeT
    {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn pager_skip_anon_range_result(
    has_memobj: CInt,
    start: CULong,
    text_start: CULong,
    stack_start: CULong,
    user_start: CULong,
    user_end: CULong,
    flags: CULong,
) -> CInt {
    (has_memobj != 0
        || start == text_start
        || start == stack_start
        || start < user_start
        || start >= user_end
        || (flags & VR_PROT_WRITE) == 0
        || (flags & VR_AP_USER) == 0) as CInt
}

#[no_mangle]
pub extern "C" fn pager_range_locked_result(flags: CULong) -> CInt {
    ((flags & VR_LOCKED) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn pager_skip_physical_removal_result(flags: CInt) -> CInt {
    ((flags & 0x04) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn pager_fd_valid_result(fd: CInt) -> CInt {
    (fd >= 0) as CInt
}

#[no_mangle]
pub extern "C" fn pager_should_unlink_swap_result(result: CLong) -> CInt {
    (result != 0) as CInt
}

#[no_mangle]
pub extern "C" fn pager_io_short_result(result: CLong) -> CLong {
    if result >= 0 {
        -(EIO as CLong)
    } else {
        result
    }
}

#[no_mangle]
pub extern "C" fn zeroobj_initial_flags_result() -> CInt {
    MF_ZEROOBJ
}

#[no_mangle]
pub extern "C" fn zeroobj_initial_refcnt_result() -> CInt {
    2
}

#[no_mangle]
pub extern "C" fn zeroobj_initial_page_mode_result() -> CInt {
    PM_MAPPED
}

#[no_mangle]
pub extern "C" fn zeroobj_initial_page_offset_result() -> OffT {
    0
}

#[no_mangle]
pub extern "C" fn zeroobj_get_page_validate_result(
    off: OffT,
    p2align: CInt,
    has_page: CInt,
) -> CInt {
    if (off as CULong & !PAGE_MASK) != 0 {
        -EINVAL
    } else if p2align != PAGE_P2ALIGN {
        -ENOMEM
    } else if has_page == 0 {
        -ENOMEM
    } else {
        0
    }
}

pub type ZeroobjVoidFn = Option<unsafe extern "C" fn(arg: *mut c_void)>;
pub type ZeroobjAllocFn = Option<unsafe extern "C" fn(size: SizeT, flags: CULong) -> *mut c_void>;
pub type ZeroobjPageAllocFn =
    Option<unsafe extern "C" fn(npages: CInt, flags: CULong) -> *mut c_void>;
pub type ZeroobjFreePageFn = Option<unsafe extern "C" fn(virt: *mut c_void, npages: CInt)>;
pub type ZeroobjMemsetFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, value: CInt, len: SizeT) -> *mut c_void>;
pub type ZeroobjPhysFn = Option<unsafe extern "C" fn(addr: *mut c_void) -> CULong>;
pub type ZeroobjPageInsertFn = Option<unsafe extern "C" fn(phys: CULong) -> *mut c_void>;
pub type ZeroobjPageModeFn = Option<unsafe extern "C" fn(page: *mut c_void) -> CInt>;
pub type ZeroobjObjInitFn = Option<unsafe extern "C" fn(obj: *mut c_void, ops: *mut c_void)>;
pub type ZeroobjPageInitFn = Option<unsafe extern "C" fn(page: *mut c_void)>;
pub type ZeroobjPageListInsertFn =
    Option<unsafe extern "C" fn(obj: *mut c_void, page: *mut c_void)>;
pub type ZeroobjPublishFn = Option<unsafe extern "C" fn(obj: *mut c_void)>;
pub type ZeroobjAllocSingletonFn = Option<unsafe extern "C" fn() -> CInt>;
pub type ZeroobjGetSingletonFn = Option<unsafe extern "C" fn() -> *mut c_void>;
pub type ZeroobjRefFn = Option<unsafe extern "C" fn(memobj: *mut c_void)>;
pub type ZeroobjLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        error: CInt,
        obj: *mut c_void,
        page: *mut c_void,
        phys: CULong,
    ),
>;

#[no_mangle]
pub unsafe extern "C" fn zeroobj_alloc_body_result(
    existing_obj: *mut c_void,
    obj_size: SizeT,
    ops: *mut c_void,
    lock: *mut c_void,
    log_fn: ZeroobjLogFn,
    lock_fn: ZeroobjVoidFn,
    unlock_fn: ZeroobjVoidFn,
    alloc_fn: ZeroobjAllocFn,
    free_fn: ZeroobjVoidFn,
    memset_fn: ZeroobjMemsetFn,
    obj_init_fn: ZeroobjObjInitFn,
    page_alloc_fn: ZeroobjPageAllocFn,
    page_free_fn: ZeroobjFreePageFn,
    phys_fn: ZeroobjPhysFn,
    page_insert_fn: ZeroobjPageInsertFn,
    page_mode_fn: ZeroobjPageModeFn,
    duplicate_page_fn: ZeroobjVoidFn,
    page_init_fn: ZeroobjPageInitFn,
    page_list_insert_fn: ZeroobjPageListInsertFn,
    publish_fn: ZeroobjPublishFn,
) -> CInt {
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let alloc_fn = match alloc_fn {
        Some(alloc_fn) => alloc_fn,
        None => return -EINVAL,
    };
    let free_fn = match free_fn {
        Some(free_fn) => free_fn,
        None => return -EINVAL,
    };
    let memset_fn = match memset_fn {
        Some(memset_fn) => memset_fn,
        None => return -EINVAL,
    };
    let obj_init_fn = match obj_init_fn {
        Some(obj_init_fn) => obj_init_fn,
        None => return -EINVAL,
    };
    let page_alloc_fn = match page_alloc_fn {
        Some(page_alloc_fn) => page_alloc_fn,
        None => return -EINVAL,
    };
    let page_free_fn = match page_free_fn {
        Some(page_free_fn) => page_free_fn,
        None => return -EINVAL,
    };
    let phys_fn = match phys_fn {
        Some(phys_fn) => phys_fn,
        None => return -EINVAL,
    };
    let page_insert_fn = match page_insert_fn {
        Some(page_insert_fn) => page_insert_fn,
        None => return -EINVAL,
    };
    let page_mode_fn = match page_mode_fn {
        Some(page_mode_fn) => page_mode_fn,
        None => return -EINVAL,
    };
    let duplicate_page_fn = match duplicate_page_fn {
        Some(duplicate_page_fn) => duplicate_page_fn,
        None => return -EINVAL,
    };
    let page_init_fn = match page_init_fn {
        Some(page_init_fn) => page_init_fn,
        None => return -EINVAL,
    };
    let page_list_insert_fn = match page_list_insert_fn {
        Some(page_list_insert_fn) => page_list_insert_fn,
        None => return -EINVAL,
    };
    let publish_fn = match publish_fn {
        Some(publish_fn) => publish_fn,
        None => return -EINVAL,
    };
    if lock.is_null() || ops.is_null() {
        return -EINVAL;
    }

    let mut obj: *mut c_void = core::ptr::null_mut();
    let mut virt: *mut c_void = core::ptr::null_mut();
    let mut error = 0;

    lock_fn(lock);
    if !existing_obj.is_null() {
        log_fn(1, 0, existing_obj, core::ptr::null_mut(), 0);
    } else {
        obj = alloc_fn(obj_size, IHK_MC_AP_NOWAIT);
        if obj.is_null() {
            error = -ENOMEM;
            log_fn(2, error, core::ptr::null_mut(), core::ptr::null_mut(), 0);
        } else {
            memset_fn(obj, 0, obj_size);
            obj_init_fn(obj, ops);

            virt = page_alloc_fn(1, IHK_MC_AP_NOWAIT);
            if virt.is_null() {
                error = -ENOMEM;
                log_fn(3, error, obj, core::ptr::null_mut(), 0);
            } else {
                let phys = phys_fn(virt);
                let page = page_insert_fn(phys);
                if page_mode_fn(page) != PM_NONE {
                    error = -EINVAL;
                    duplicate_page_fn(page);
                } else {
                    memset_fn(virt, 0, PAGE_SIZE as SizeT);
                    page_init_fn(page);
                    page_list_insert_fn(obj, page);
                    virt = core::ptr::null_mut();
                    publish_fn(obj);
                    obj = core::ptr::null_mut();
                }
            }
        }
    }

    unlock_fn(lock);
    if !virt.is_null() {
        page_free_fn(virt, 1);
    }
    if !obj.is_null() {
        free_fn(obj);
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn zeroobj_create_body_result(
    objp: *mut *mut c_void,
    existing_obj: *mut c_void,
    alloc_fn: ZeroobjAllocSingletonFn,
    get_singleton_fn: ZeroobjGetSingletonFn,
    ref_fn: ZeroobjRefFn,
    log_fn: ZeroobjLogFn,
) -> CInt {
    let alloc_fn = match alloc_fn {
        Some(alloc_fn) => alloc_fn,
        None => return -EINVAL,
    };
    let get_singleton_fn = match get_singleton_fn {
        Some(get_singleton_fn) => get_singleton_fn,
        None => return -EINVAL,
    };
    let ref_fn = match ref_fn {
        Some(ref_fn) => ref_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if objp.is_null() {
        return -EINVAL;
    }

    let mut obj = existing_obj;
    if obj.is_null() {
        let error = alloc_fn();
        if error != 0 {
            return error;
        }
        obj = get_singleton_fn();
        if obj.is_null() {
            log_fn(2, -ENOMEM, core::ptr::null_mut(), core::ptr::null_mut(), 0);
            return -ENOMEM;
        }
    }

    *objp = obj;
    ref_fn(obj);
    0
}

#[no_mangle]
pub extern "C" fn zeroobj_get_page_body_result() -> CInt {
    0
}

#[no_mangle]
pub extern "C" fn shmobj_init_pgshift_result(init_pgshift: CInt) -> CInt {
    if init_pgshift != 0 {
        init_pgshift
    } else {
        PAGE_SHIFT
    }
}

#[no_mangle]
pub extern "C" fn shmobj_pgsize_result(pgshift: CInt) -> SizeT {
    1usize << pgshift
}

#[no_mangle]
pub extern "C" fn shmobj_initial_flags_result() -> CInt {
    MF_SHM
}

#[no_mangle]
pub extern "C" fn shmobj_indexed_flags_result(flags: CInt) -> CInt {
    flags | MF_SHMDT_OK | MF_IS_REMOVABLE
}

#[no_mangle]
pub extern "C" fn shmobj_real_segsz_result(segsz: SizeT, pgsize: SizeT) -> SizeT {
    segsz.wrapping_add(pgsize - 1) & !(pgsize - 1)
}

#[no_mangle]
pub extern "C" fn shmobj_page_contains_offset_result(
    page_offset: OffT,
    pgshift: CInt,
    off: OffT,
) -> CInt {
    (page_offset <= off && off < page_offset.wrapping_add(1i64 << pgshift)) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_destroy_page_npages_result(pgshift: CInt) -> CInt {
    (1usize << (pgshift - PAGE_SHIFT)) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_destroy_page_size_result(pgshift: CInt) -> SizeT {
    1usize << pgshift
}

#[no_mangle]
pub extern "C" fn shmobj_destroy_index_word_result(index: CInt) -> CInt {
    index / 64
}

#[no_mangle]
pub extern "C" fn shmobj_destroy_index_mask_result(index: CInt) -> CULong {
    1u64 << (index % 64)
}

#[no_mangle]
pub extern "C" fn shmlock_user_locked_result(locked: SizeT) -> CInt {
    (locked != 0) as CInt
}

#[no_mangle]
pub extern "C" fn shmlock_user_match_result(user_ruid: CInt, ruid: CInt) -> CInt {
    (user_ruid == ruid) as CInt
}

#[no_mangle]
pub extern "C" fn shmlock_user_is_list_head_result(chain: CULong, head: CULong) -> CInt {
    (chain == head) as CInt
}

#[no_mangle]
pub extern "C" fn shmlock_user_after_unlock_result(locked: SizeT, size: SizeT) -> SizeT {
    locked.wrapping_sub(size)
}

#[no_mangle]
pub extern "C" fn shmlock_user_should_free_result(locked: SizeT) -> CInt {
    (locked == 0) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_has_user_result(user: CULong) -> CInt {
    (user != 0) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_destroy_page_count_invalid_result(count: CInt) -> CInt {
    (count != 1) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_destroy_page_should_free_result(
    count: CInt,
    page_unmap_result: CInt,
) -> CInt {
    (count == 1 && page_unmap_result != 0) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_should_free_direct_result(index: CInt) -> CInt {
    (index < 0) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_destroy_missing_flag_result(mode: CInt) -> CInt {
    ((mode & SHM_DEST) == 0) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_initial_refcnt_result() -> CInt {
    1
}

#[no_mangle]
pub extern "C" fn shmobj_initial_index_result() -> CInt {
    -1
}

#[no_mangle]
pub extern "C" fn shmobj_initial_ds_pgshift_result() -> CInt {
    0
}

#[no_mangle]
pub extern "C" fn shmobj_get_page_validate_result(
    real_segsz: SizeT,
    off: OffT,
    p2align: CInt,
) -> CInt {
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

#[no_mangle]
pub extern "C" fn shmobj_lookup_page_validate_result(real_segsz: SizeT, off: OffT) -> CInt {
    if (off as CULong & !PAGE_MASK) != 0 {
        -EINVAL
    } else if real_segsz <= off as SizeT {
        -ERANGE
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn shmobj_page_npages_result(p2align: CInt) -> CInt {
    1 << p2align
}

#[no_mangle]
pub extern "C" fn shmobj_page_pgshift_result(p2align: CInt) -> CInt {
    p2align + PAGE_SHIFT
}

#[no_mangle]
pub extern "C" fn shmobj_need_alloc_page_result(page: CULong) -> CInt {
    (page == 0) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_new_page_mode_result() -> CInt {
    PM_MAPPED
}

#[no_mangle]
pub extern "C" fn shmobj_new_page_count_result() -> CInt {
    1
}

#[no_mangle]
pub extern "C" fn shmobj_new_page_mapped_result() -> CLong {
    0
}

#[no_mangle]
pub extern "C" fn shmobj_page_mode_valid_for_new_result(mode: CInt) -> CInt {
    (mode == PM_NONE) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_lookup_page_missing_error_result(page: CULong) -> CInt {
    if page != 0 {
        0
    } else {
        -ENOENT
    }
}

#[no_mangle]
pub extern "C" fn shmobj_lookup_should_store_phys_result(physp: CULong) -> CInt {
    (physp != 0) as CInt
}

pub type ShmobjRefFn = Option<unsafe extern "C" fn(memobj: *mut c_void)>;
pub type ShmobjUnrefFn = Option<unsafe extern "C" fn(memobj: *mut c_void)>;
pub type ShmobjPageListLockFn = Option<unsafe extern "C" fn(obj: *mut c_void)>;
pub type ShmobjPageListUnlockFn = Option<unsafe extern "C" fn(obj: *mut c_void)>;
pub type ShmobjPageLookupFn =
    Option<unsafe extern "C" fn(obj: *mut c_void, off: OffT) -> *mut c_void>;
pub type ShmobjPagePhysFn = Option<unsafe extern "C" fn(page: *mut c_void) -> CULong>;
pub type ShmobjLookupLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        memobj: *mut c_void,
        off: OffT,
        p2align: CInt,
        physp: *mut CULong,
        error: CInt,
        phys: CULong,
    ),
>;

#[no_mangle]
pub unsafe extern "C" fn shmobj_lookup_page_body_result(
    memobj: *mut c_void,
    obj: *mut c_void,
    real_segsz: SizeT,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    resolved_physp: *mut CULong,
    ref_fn: ShmobjRefFn,
    unref_fn: ShmobjUnrefFn,
    lock_fn: ShmobjPageListLockFn,
    unlock_fn: ShmobjPageListUnlockFn,
    lookup_fn: ShmobjPageLookupFn,
    page_phys_fn: ShmobjPagePhysFn,
    log_fn: ShmobjLookupLogFn,
) -> CInt {
    let ref_fn = match ref_fn {
        Some(ref_fn) => ref_fn,
        None => return -EINVAL,
    };
    let unref_fn = match unref_fn {
        Some(unref_fn) => unref_fn,
        None => return -EINVAL,
    };
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let lookup_fn = match lookup_fn {
        Some(lookup_fn) => lookup_fn,
        None => return -EINVAL,
    };
    let page_phys_fn = match page_phys_fn {
        Some(page_phys_fn) => page_phys_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if memobj.is_null() || obj.is_null() {
        return -EINVAL;
    }

    ref_fn(memobj);
    let mut phys = !0 as CULong;
    let mut error = shmobj_lookup_page_validate_result(real_segsz, off);
    if error == -EINVAL {
        log_fn(1, memobj, off, p2align, physp, error, phys);
        unref_fn(memobj);
        return error;
    }
    if error == -ERANGE {
        log_fn(2, memobj, off, p2align, physp, error, phys);
        unref_fn(memobj);
        return error;
    }

    lock_fn(obj);
    let page = lookup_fn(obj, off);
    unlock_fn(obj);
    error = shmobj_lookup_page_missing_error_result(page as CULong);
    if error != 0 {
        log_fn(3, memobj, off, p2align, physp, error, phys);
        unref_fn(memobj);
        return error;
    }

    phys = page_phys_fn(page);
    if !resolved_physp.is_null() {
        *resolved_physp = phys;
    }
    if shmobj_lookup_should_store_phys_result(physp as CULong) != 0 {
        *physp = phys;
    }

    unref_fn(memobj);
    0
}

#[no_mangle]
pub extern "C" fn shmobj_update_args_result(
    has_pt: CInt,
    has_orig_page: CInt,
    has_vaddr: CInt,
) -> CInt {
    if has_pt != 0 && has_orig_page != 0 && has_vaddr != 0 {
        0
    } else {
        -ENOENT
    }
}

#[no_mangle]
pub extern "C" fn shmobj_update_orig_pgsize_result(pgshift: CInt) -> SizeT {
    1usize << pgshift
}

#[no_mangle]
pub extern "C" fn shmobj_update_page_phys_result(base_phys: CULong, page_off: SizeT) -> CULong {
    base_phys.wrapping_add(page_off as CULong)
}

#[no_mangle]
pub extern "C" fn shmobj_update_page_offset_result(orig_offset: OffT, page_off: SizeT) -> OffT {
    orig_offset.wrapping_add(page_off as OffT)
}

#[no_mangle]
pub extern "C" fn shmobj_pte_missing_result(pte: CULong) -> CInt {
    if pte == 0 {
        -ENOENT
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn shmobj_update_has_more_pages_result(page_off: SizeT, orig_pgsize: SizeT) -> CInt {
    (page_off < orig_pgsize) as CInt
}

#[no_mangle]
pub extern "C" fn shmobj_update_next_page_off_result(page_off: SizeT, pte_size: SizeT) -> SizeT {
    page_off.wrapping_add(pte_size)
}

pub type ShmobjPteLookupFn = Option<
    unsafe extern "C" fn(
        pt: *mut c_void,
        vaddr: *mut c_void,
        pte_sizep: *mut SizeT,
        p2alignp: *mut CInt,
    ) -> *mut c_void,
>;
pub type ShmobjPagePgshiftFn = Option<unsafe extern "C" fn(page: *mut c_void) -> CInt>;
pub type ShmobjPageSetPgshiftFn = Option<unsafe extern "C" fn(page: *mut c_void, pgshift: CInt)>;
pub type ShmobjPageModeFn = Option<unsafe extern "C" fn(page: *mut c_void) -> CInt>;
pub type ShmobjPageSetModeFn = Option<unsafe extern "C" fn(page: *mut c_void, mode: CInt)>;
pub type ShmobjPageOffsetFn = Option<unsafe extern "C" fn(page: *mut c_void) -> OffT>;
pub type ShmobjPageSetOffsetFn = Option<unsafe extern "C" fn(page: *mut c_void, offset: OffT)>;
pub type ShmobjPageCountFn = Option<unsafe extern "C" fn(page: *mut c_void) -> CInt>;
pub type ShmobjPageSetCountFn = Option<unsafe extern "C" fn(page: *mut c_void, count: CInt)>;
pub type ShmobjPageMappedFn = Option<unsafe extern "C" fn(page: *mut c_void) -> CLong>;
pub type ShmobjPageSetMappedFn = Option<unsafe extern "C" fn(page: *mut c_void, mapped: CLong)>;
pub type ShmobjPageInsertHashFn = Option<unsafe extern "C" fn(phys: CULong) -> *mut c_void>;
pub type ShmobjPageListInsertFn = Option<unsafe extern "C" fn(obj: *mut c_void, page: *mut c_void)>;
pub type ShmobjUpdateLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        memobj: *mut c_void,
        pt: *mut c_void,
        orig_page: *mut c_void,
        vaddr: *mut c_void,
        error: CInt,
    ),
>;

#[no_mangle]
pub unsafe extern "C" fn shmobj_update_page_body_result(
    memobj: *mut c_void,
    obj: *mut c_void,
    pt: *mut c_void,
    orig_page: *mut c_void,
    vaddr: *mut c_void,
    ref_fn: ShmobjRefFn,
    unref_fn: ShmobjUnrefFn,
    page_phys_fn: ShmobjPagePhysFn,
    pte_lookup_fn: ShmobjPteLookupFn,
    page_pgshift_fn: ShmobjPagePgshiftFn,
    page_set_pgshift_fn: ShmobjPageSetPgshiftFn,
    page_mode_fn: ShmobjPageModeFn,
    page_set_mode_fn: ShmobjPageSetModeFn,
    page_offset_fn: ShmobjPageOffsetFn,
    page_set_offset_fn: ShmobjPageSetOffsetFn,
    page_count_fn: ShmobjPageCountFn,
    page_set_count_fn: ShmobjPageSetCountFn,
    page_mapped_fn: ShmobjPageMappedFn,
    page_set_mapped_fn: ShmobjPageSetMappedFn,
    page_insert_hash_fn: ShmobjPageInsertHashFn,
    page_list_insert_fn: ShmobjPageListInsertFn,
    log_fn: ShmobjUpdateLogFn,
) -> CInt {
    let ref_fn = match ref_fn {
        Some(ref_fn) => ref_fn,
        None => return -EINVAL,
    };
    let unref_fn = match unref_fn {
        Some(unref_fn) => unref_fn,
        None => return -EINVAL,
    };
    let page_phys_fn = match page_phys_fn {
        Some(page_phys_fn) => page_phys_fn,
        None => return -EINVAL,
    };
    let pte_lookup_fn = match pte_lookup_fn {
        Some(pte_lookup_fn) => pte_lookup_fn,
        None => return -EINVAL,
    };
    let page_pgshift_fn = match page_pgshift_fn {
        Some(page_pgshift_fn) => page_pgshift_fn,
        None => return -EINVAL,
    };
    let page_set_pgshift_fn = match page_set_pgshift_fn {
        Some(page_set_pgshift_fn) => page_set_pgshift_fn,
        None => return -EINVAL,
    };
    let page_mode_fn = match page_mode_fn {
        Some(page_mode_fn) => page_mode_fn,
        None => return -EINVAL,
    };
    let page_set_mode_fn = match page_set_mode_fn {
        Some(page_set_mode_fn) => page_set_mode_fn,
        None => return -EINVAL,
    };
    let page_offset_fn = match page_offset_fn {
        Some(page_offset_fn) => page_offset_fn,
        None => return -EINVAL,
    };
    let page_set_offset_fn = match page_set_offset_fn {
        Some(page_set_offset_fn) => page_set_offset_fn,
        None => return -EINVAL,
    };
    let page_count_fn = match page_count_fn {
        Some(page_count_fn) => page_count_fn,
        None => return -EINVAL,
    };
    let page_set_count_fn = match page_set_count_fn {
        Some(page_set_count_fn) => page_set_count_fn,
        None => return -EINVAL,
    };
    let page_mapped_fn = match page_mapped_fn {
        Some(page_mapped_fn) => page_mapped_fn,
        None => return -EINVAL,
    };
    let page_set_mapped_fn = match page_set_mapped_fn {
        Some(page_set_mapped_fn) => page_set_mapped_fn,
        None => return -EINVAL,
    };
    let page_insert_hash_fn = match page_insert_hash_fn {
        Some(page_insert_hash_fn) => page_insert_hash_fn,
        None => return -EINVAL,
    };
    let page_list_insert_fn = match page_list_insert_fn {
        Some(page_list_insert_fn) => page_list_insert_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if memobj.is_null() {
        return -EINVAL;
    }

    ref_fn(memobj);

    let mut error = shmobj_update_args_result(
        (!pt.is_null()) as CInt,
        (!orig_page.is_null()) as CInt,
        (!vaddr.is_null()) as CInt,
    );
    if error != 0 {
        log_fn(4, memobj, pt, orig_page, vaddr, error);
        unref_fn(memobj);
        return error;
    }

    let base_phys = page_phys_fn(orig_page);
    let mut pte_size: SizeT = 0;
    let mut p2align: CInt = 0;
    let mut pte = pte_lookup_fn(pt, vaddr, &mut pte_size, &mut p2align);
    error = shmobj_pte_missing_result(pte as CULong);
    if error != 0 {
        log_fn(5, memobj, pt, orig_page, vaddr, error);
        unref_fn(memobj);
        return error;
    }

    let orig_pgsize = shmobj_update_orig_pgsize_result(page_pgshift_fn(orig_page));
    page_set_pgshift_fn(orig_page, shmobj_page_pgshift_result(p2align));

    let mut page_off = pte_size;
    while shmobj_update_has_more_pages_result(page_off, orig_pgsize) != 0 {
        pte = pte_lookup_fn(
            pt,
            (vaddr as CULong).wrapping_add(page_off as CULong) as *mut c_void,
            &mut pte_size,
            &mut p2align,
        );
        error = shmobj_pte_missing_result(pte as CULong);
        if error != 0 {
            log_fn(5, memobj, pt, orig_page, vaddr, error);
            unref_fn(memobj);
            return error;
        }

        let phys = shmobj_update_page_phys_result(base_phys, page_off);
        let page = page_insert_hash_fn(phys);
        page_set_mode_fn(page, page_mode_fn(orig_page));
        page_set_offset_fn(
            page,
            shmobj_update_page_offset_result(page_offset_fn(orig_page), page_off),
        );
        page_set_pgshift_fn(page, shmobj_page_pgshift_result(p2align));
        page_set_count_fn(page, page_count_fn(orig_page));
        page_set_mapped_fn(page, page_mapped_fn(orig_page));
        page_list_insert_fn(obj, page);

        page_off = shmobj_update_next_page_off_result(page_off, pte_size);
    }

    unref_fn(memobj);
    0
}

pub type ShmobjAllocPageFn = Option<
    unsafe extern "C" fn(
        npages: CInt,
        p2align: CInt,
        flags: CULong,
        virt_addr: CULong,
    ) -> *mut c_void,
>;
pub type ShmobjFreePageFn = Option<unsafe extern "C" fn(virt: *mut c_void, npages: CInt)>;
pub type ShmobjVirtToPhysFn = Option<unsafe extern "C" fn(virt: *mut c_void) -> CULong>;
pub type ShmobjMemsetFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, value: CInt, len: SizeT) -> *mut c_void>;
pub type ShmobjPageCountIncFn = Option<unsafe extern "C" fn(page: *mut c_void)>;
pub type ShmobjPanicFn = Option<unsafe extern "C" fn()>;
pub type ShmobjGetLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        memobj: *mut c_void,
        off: OffT,
        p2align: CInt,
        physp: *mut CULong,
        error: CInt,
        page: *mut c_void,
        phys: CULong,
    ),
>;

#[no_mangle]
pub unsafe extern "C" fn shmobj_get_page_body_result(
    memobj: *mut c_void,
    obj: *mut c_void,
    real_segsz: SizeT,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    virt_addr: CULong,
    ref_fn: ShmobjRefFn,
    unref_fn: ShmobjUnrefFn,
    lock_fn: ShmobjPageListLockFn,
    unlock_fn: ShmobjPageListUnlockFn,
    lookup_fn: ShmobjPageLookupFn,
    alloc_page_fn: ShmobjAllocPageFn,
    free_page_fn: ShmobjFreePageFn,
    virt_to_phys_fn: ShmobjVirtToPhysFn,
    page_insert_hash_fn: ShmobjPageInsertHashFn,
    page_mode_fn: ShmobjPageModeFn,
    page_set_mode_fn: ShmobjPageSetModeFn,
    page_set_offset_fn: ShmobjPageSetOffsetFn,
    page_set_pgshift_fn: ShmobjPageSetPgshiftFn,
    page_set_count_fn: ShmobjPageSetCountFn,
    page_set_mapped_fn: ShmobjPageSetMappedFn,
    page_list_insert_fn: ShmobjPageListInsertFn,
    page_count_inc_fn: ShmobjPageCountIncFn,
    page_phys_fn: ShmobjPagePhysFn,
    memset_fn: ShmobjMemsetFn,
    panic_fn: ShmobjPanicFn,
    log_fn: ShmobjGetLogFn,
) -> CInt {
    let ref_fn = match ref_fn {
        Some(ref_fn) => ref_fn,
        None => return -EINVAL,
    };
    let unref_fn = match unref_fn {
        Some(unref_fn) => unref_fn,
        None => return -EINVAL,
    };
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let lookup_fn = match lookup_fn {
        Some(lookup_fn) => lookup_fn,
        None => return -EINVAL,
    };
    let alloc_page_fn = match alloc_page_fn {
        Some(alloc_page_fn) => alloc_page_fn,
        None => return -EINVAL,
    };
    let free_page_fn = match free_page_fn {
        Some(free_page_fn) => free_page_fn,
        None => return -EINVAL,
    };
    let virt_to_phys_fn = match virt_to_phys_fn {
        Some(virt_to_phys_fn) => virt_to_phys_fn,
        None => return -EINVAL,
    };
    let page_insert_hash_fn = match page_insert_hash_fn {
        Some(page_insert_hash_fn) => page_insert_hash_fn,
        None => return -EINVAL,
    };
    let page_mode_fn = match page_mode_fn {
        Some(page_mode_fn) => page_mode_fn,
        None => return -EINVAL,
    };
    let page_set_mode_fn = match page_set_mode_fn {
        Some(page_set_mode_fn) => page_set_mode_fn,
        None => return -EINVAL,
    };
    let page_set_offset_fn = match page_set_offset_fn {
        Some(page_set_offset_fn) => page_set_offset_fn,
        None => return -EINVAL,
    };
    let page_set_pgshift_fn = match page_set_pgshift_fn {
        Some(page_set_pgshift_fn) => page_set_pgshift_fn,
        None => return -EINVAL,
    };
    let page_set_count_fn = match page_set_count_fn {
        Some(page_set_count_fn) => page_set_count_fn,
        None => return -EINVAL,
    };
    let page_set_mapped_fn = match page_set_mapped_fn {
        Some(page_set_mapped_fn) => page_set_mapped_fn,
        None => return -EINVAL,
    };
    let page_list_insert_fn = match page_list_insert_fn {
        Some(page_list_insert_fn) => page_list_insert_fn,
        None => return -EINVAL,
    };
    let page_count_inc_fn = match page_count_inc_fn {
        Some(page_count_inc_fn) => page_count_inc_fn,
        None => return -EINVAL,
    };
    let page_phys_fn = match page_phys_fn {
        Some(page_phys_fn) => page_phys_fn,
        None => return -EINVAL,
    };
    let memset_fn = match memset_fn {
        Some(memset_fn) => memset_fn,
        None => return -EINVAL,
    };
    let panic_fn = match panic_fn {
        Some(panic_fn) => panic_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if memobj.is_null() || obj.is_null() || physp.is_null() {
        return -EINVAL;
    }

    let mut phys = !0 as CULong;

    ref_fn(memobj);
    let mut error = shmobj_get_page_validate_result(real_segsz, off, p2align);
    if error == -EINVAL {
        log_fn(
            6,
            memobj,
            off,
            p2align,
            physp,
            error,
            core::ptr::null_mut(),
            phys,
        );
        unref_fn(memobj);
        return error;
    }
    if error == -ERANGE {
        log_fn(
            7,
            memobj,
            off,
            p2align,
            physp,
            error,
            core::ptr::null_mut(),
            phys,
        );
        unref_fn(memobj);
        return error;
    }
    if error == -ENOSPC {
        log_fn(
            8,
            memobj,
            off,
            p2align,
            physp,
            error,
            core::ptr::null_mut(),
            phys,
        );
        unref_fn(memobj);
        return error;
    }

    lock_fn(obj);
    let mut page = lookup_fn(obj, off);
    if shmobj_need_alloc_page_result(page as CULong) != 0 {
        let npages = shmobj_page_npages_result(p2align);
        let virt = alloc_page_fn(npages, p2align, IHK_MC_AP_NOWAIT, virt_addr);
        if virt.is_null() {
            unlock_fn(obj);
            error = -ENOMEM;
            log_fn(
                9,
                memobj,
                off,
                p2align,
                physp,
                error,
                core::ptr::null_mut(),
                phys,
            );
            unref_fn(memobj);
            return error;
        }

        phys = virt_to_phys_fn(virt);
        page = page_insert_hash_fn(phys);
        if shmobj_page_mode_valid_for_new_result(page_mode_fn(page)) == 0 {
            error = -EINVAL;
            log_fn(10, memobj, off, p2align, physp, error, page, phys);
            panic_fn();
            unlock_fn(obj);
            unref_fn(memobj);
            free_page_fn(virt, npages);
            return error;
        }

        memset_fn(
            virt,
            0,
            (shmobj_page_npages_result(p2align) as SizeT) * PAGE_SIZE as SizeT,
        );
        page_set_mode_fn(page, shmobj_new_page_mode_result());
        page_set_offset_fn(page, off);
        page_set_pgshift_fn(page, shmobj_page_pgshift_result(p2align));
        page_set_count_fn(page, shmobj_new_page_count_result());
        page_set_mapped_fn(page, shmobj_new_page_mapped_result());
        page_list_insert_fn(obj, page);
        log_fn(11, memobj, off, p2align, physp, 0, page, phys);
    }
    unlock_fn(obj);

    page_count_inc_fn(page);
    *physp = page_phys_fn(page);
    unref_fn(memobj);
    0
}

pub type ShmobjUserClearFn = Option<unsafe extern "C" fn(obj: *mut c_void)>;
pub type ShmobjUserLockedFn = Option<unsafe extern "C" fn(user: *mut c_void) -> SizeT>;
pub type ShmobjUserSetLockedFn = Option<unsafe extern "C" fn(user: *mut c_void, locked: SizeT)>;
pub type ShmobjUserFreeFn = Option<unsafe extern "C" fn(user: *mut c_void)>;
pub type ShmobjPageFirstFn = Option<unsafe extern "C" fn(obj: *mut c_void) -> *mut c_void>;
pub type ShmobjPageRemoveFn = Option<unsafe extern "C" fn(obj: *mut c_void, page: *mut c_void)>;
pub type ShmobjPhysToVirtFn = Option<unsafe extern "C" fn(phys: CULong) -> *mut c_void>;
pub type ShmobjPageUnmapFn = Option<unsafe extern "C" fn(page: *mut c_void) -> CInt>;
pub type ShmobjRssSubFn = Option<unsafe extern "C" fn(size: SizeT, pgsize: SizeT)>;
pub type ShmobjFreeFn = Option<unsafe extern "C" fn(ptr: *mut c_void)>;
pub type ShmobjIndexedFreeFn =
    Option<unsafe extern "C" fn(obj: *mut c_void, word: CInt, mask: CULong)>;
pub type ShmobjDestroyLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        obj: *mut c_void,
        page: *mut c_void,
        phys: CULong,
        size: SizeT,
        pgsize: SizeT,
    ),
>;
pub type ShmobjDestroyFn = Option<unsafe extern "C" fn(obj: *mut c_void)>;
pub type ShmobjFreeLogFn = Option<unsafe extern "C" fn(event: CInt, memobj: *mut c_void)>;
pub type ShmobjAllocFn = Option<unsafe extern "C" fn(size: SizeT, flags: CULong) -> *mut c_void>;
pub type ShmobjNextSeqFn = Option<unsafe extern "C" fn() -> CInt>;
pub type ShmobjCreateInitFn = Option<
    unsafe extern "C" fn(
        obj: *mut c_void,
        ds: *mut c_void,
        pgshift: CInt,
        pgsize: SizeT,
        real_segsz: SizeT,
        seq: CInt,
    ) -> *mut c_void,
>;
pub type ShmobjCreateLogFn =
    Option<unsafe extern "C" fn(event: CInt, ds: *mut c_void, objp: *mut c_void, error: CInt)>;
pub type ShmobjCreateFn =
    Option<unsafe extern "C" fn(ds: *mut c_void, objp: *mut *mut c_void) -> CInt>;
pub type ShmobjMemobjFlagsFn = Option<unsafe extern "C" fn(memobj: *mut c_void) -> CInt>;
pub type ShmobjMemobjSetFlagsFn = Option<unsafe extern "C" fn(memobj: *mut c_void, flags: CInt)>;
pub type ShmobjToShmobjFn = Option<unsafe extern "C" fn(memobj: *mut c_void) -> *mut c_void>;
pub type ShmlockUserFirstFn = Option<unsafe extern "C" fn() -> *mut c_void>;
pub type ShmlockUserNextFn = Option<unsafe extern "C" fn(user: *mut c_void) -> *mut c_void>;
pub type ShmlockUserRuidFn = Option<unsafe extern "C" fn(user: *mut c_void) -> CInt>;
pub type ShmlockUserInitFn = Option<unsafe extern "C" fn(user: *mut c_void, ruid: CInt)>;
pub type ShmlockUserListFn = Option<unsafe extern "C" fn(user: *mut c_void)>;

#[no_mangle]
pub unsafe extern "C" fn shmobj_create_body_result(
    ds: *mut c_void,
    objp: *mut *mut c_void,
    segsz: SizeT,
    init_pgshift: CInt,
    obj_size: SizeT,
    alloc_fn: ShmobjAllocFn,
    free_fn: ShmobjFreeFn,
    memset_fn: ShmobjMemsetFn,
    next_seq_fn: ShmobjNextSeqFn,
    init_fn: ShmobjCreateInitFn,
    log_fn: ShmobjCreateLogFn,
) -> CInt {
    let (
        Some(alloc_fn),
        Some(free_fn),
        Some(memset_fn),
        Some(next_seq_fn),
        Some(init_fn),
        Some(log_fn),
    ) = (alloc_fn, free_fn, memset_fn, next_seq_fn, init_fn, log_fn)
    else {
        return -EINVAL;
    };
    if ds.is_null() || objp.is_null() {
        return -EINVAL;
    }

    let pgshift = shmobj_init_pgshift_result(init_pgshift);
    let pgsize = shmobj_pgsize_result(pgshift);
    let real_segsz = shmobj_real_segsz_result(segsz, pgsize);
    let obj = alloc_fn(obj_size, IHK_MC_AP_NOWAIT);
    if obj.is_null() {
        let error = -ENOMEM;
        log_fn(15, ds, objp as *mut c_void, error);
        return error;
    }

    memset_fn(obj, 0, obj_size);
    let seq = next_seq_fn();
    let memobj = init_fn(obj, ds, pgshift, pgsize, real_segsz, seq);
    if memobj.is_null() {
        free_fn(obj);
        return -EINVAL;
    }

    write(objp, memobj);
    0
}

#[no_mangle]
pub unsafe extern "C" fn shmobj_create_indexed_body_result(
    ds: *mut c_void,
    objp: *mut *mut c_void,
    create_fn: ShmobjCreateFn,
    flags_fn: ShmobjMemobjFlagsFn,
    set_flags_fn: ShmobjMemobjSetFlagsFn,
    to_shmobj_fn: ShmobjToShmobjFn,
) -> CInt {
    let (Some(create_fn), Some(flags_fn), Some(set_flags_fn), Some(to_shmobj_fn)) =
        (create_fn, flags_fn, set_flags_fn, to_shmobj_fn)
    else {
        return -EINVAL;
    };
    if ds.is_null() || objp.is_null() {
        return -EINVAL;
    }

    let mut memobj: *mut c_void = core::ptr::null_mut();
    let error = create_fn(ds, &mut memobj);
    if error == 0 {
        let flags = shmobj_indexed_flags_result(flags_fn(memobj));
        set_flags_fn(memobj, flags);
        write(objp, to_shmobj_fn(memobj));
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn shmlock_user_free_body_result(
    user: *mut c_void,
    user_locked_fn: ShmobjUserLockedFn,
    list_del_fn: ShmlockUserListFn,
    free_fn: ShmobjFreeFn,
    panic_fn: ShmobjPanicFn,
) -> CInt {
    let (Some(user_locked_fn), Some(list_del_fn), Some(free_fn), Some(panic_fn)) =
        (user_locked_fn, list_del_fn, free_fn, panic_fn)
    else {
        return -EINVAL;
    };
    if user.is_null() {
        return -EINVAL;
    }

    if shmlock_user_locked_result(user_locked_fn(user)) != 0 {
        panic_fn();
    }
    list_del_fn(user);
    free_fn(user);

    0
}

#[no_mangle]
pub unsafe extern "C" fn shmlock_user_get_body_result(
    ruid: CInt,
    userp: *mut *mut c_void,
    user_size: SizeT,
    first_fn: ShmlockUserFirstFn,
    next_fn: ShmlockUserNextFn,
    ruid_fn: ShmlockUserRuidFn,
    alloc_fn: ShmobjAllocFn,
    init_fn: ShmlockUserInitFn,
    list_add_fn: ShmlockUserListFn,
) -> CInt {
    let (
        Some(first_fn),
        Some(next_fn),
        Some(ruid_fn),
        Some(alloc_fn),
        Some(init_fn),
        Some(list_add_fn),
    ) = (first_fn, next_fn, ruid_fn, alloc_fn, init_fn, list_add_fn)
    else {
        return -EINVAL;
    };
    if userp.is_null() {
        return -EINVAL;
    }

    let mut user = first_fn();
    while !user.is_null() {
        if shmlock_user_match_result(ruid_fn(user), ruid) != 0 {
            break;
        }
        user = next_fn(user);
    }

    if user.is_null() {
        user = alloc_fn(user_size, IHK_MC_AP_NOWAIT);
        if user.is_null() {
            return -ENOMEM;
        }
        init_fn(user, ruid);
        list_add_fn(user);
    }

    write(userp, user);
    0
}

#[no_mangle]
pub extern "C" fn gencore_align32_result(value: SizeT) -> SizeT {
    ((value + 3) / 4) * 4
}

#[no_mangle]
pub extern "C" fn gencore_alignpage_result(value: SizeT) -> SizeT {
    ((value + PAGE_SIZE as SizeT - 1) / PAGE_SIZE as SizeT) * PAGE_SIZE as SizeT
}

#[no_mangle]
pub extern "C" fn gencore_range_inaccessible_result(flags: CULong) -> CInt {
    ((flags & (VR_RESERVED | VR_MEMTYPE_UC | VR_DONTDUMP)) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn gencore_prstatus_size_result() -> CInt {
    (size_of::<ElfCoreNote>()
        + gencore_align32_result(5)
        + gencore_align32_result(size_of::<ElfPrstatus64>())) as CInt
}

#[no_mangle]
pub extern "C" fn gencore_prpsinfo_size_result() -> CInt {
    (size_of::<ElfCoreNote>()
        + gencore_align32_result(5)
        + gencore_align32_result(size_of::<ElfPrpsinfo64>())) as CInt
}

#[no_mangle]
pub extern "C" fn gencore_auxv_size_result() -> CInt {
    (size_of::<ElfCoreNote>() + gencore_align32_result(5) + size_of::<CULong>() * AUXV_LEN as usize)
        as CInt
}

#[no_mangle]
pub unsafe extern "C" fn gencore_fill_elf_header_body_result(
    eh: *mut Elf64Ehdr,
    segs: CInt,
) -> CInt {
    if eh.is_null() {
        return -EINVAL;
    }

    let eh = &mut *eh;
    eh.e_ident[0] = 0x7f;
    eh.e_ident[1] = b'E';
    eh.e_ident[2] = b'L';
    eh.e_ident[3] = b'F';
    eh.e_ident[4] = ELFCLASS64;
    eh.e_ident[5] = ELFDATA2LSB;
    eh.e_ident[6] = ELF_VERSION_CURRENT;
    eh.e_ident[7] = ELFOSABI_NONE;
    eh.e_ident[8] = ELF_ABIVERSION_NONE;
    eh.e_type = ET_CORE;
    eh.e_machine = EM_X86_64;
    eh.e_version = EV_CURRENT;
    eh.e_entry = 0;
    eh.e_phoff = 64;
    eh.e_shoff = 0;
    eh.e_flags = 0;
    eh.e_ehsize = 64;
    eh.e_phentsize = 56;
    eh.e_phnum = segs as u16;
    eh.e_shentsize = 0;
    eh.e_shnum = 0;
    eh.e_shstrndx = 0;

    0
}

pub type GencoreArchFillPrstatusFn = Option<
    unsafe extern "C" fn(prstatus: *mut c_void, thread: *mut c_void, regs: *mut c_void, sig: CInt),
>;

#[no_mangle]
pub unsafe extern "C" fn gencore_fill_prstatus_body_result(
    head: *mut ElfCoreNote,
    thread: *mut c_void,
    regs: *mut c_void,
    sig: CInt,
    arch_fill_prstatus_fn: GencoreArchFillPrstatusFn,
) -> CInt {
    let Some(arch_fill_prstatus_fn) = arch_fill_prstatus_fn else {
        return -EINVAL;
    };
    if head.is_null() || thread.is_null() {
        return -EINVAL;
    }

    write_volatile(core::ptr::addr_of_mut!((*head).namesz), 5);
    write_volatile(
        core::ptr::addr_of_mut!((*head).descsz),
        size_of::<ElfPrstatus64>() as u32,
    );
    write_volatile(core::ptr::addr_of_mut!((*head).type_), NT_PRSTATUS);
    let name = head.add(1).cast::<u8>();
    let core_name = b"CORE\0";
    for (idx, byte) in core_name.iter().copied().enumerate() {
        write_volatile(name.add(idx), byte);
    }
    let prstatus = name.add(gencore_align32_result(5)).cast::<ElfPrstatus64>();
    arch_fill_prstatus_fn(prstatus.cast::<c_void>(), thread, regs, sig);

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_fill_prpsinfo_body_result(
    head: *mut ElfCoreNote,
    status: CInt,
    pid: CInt,
    cmdline: *const i8,
) -> CInt {
    if head.is_null() || cmdline.is_null() {
        return -EINVAL;
    }

    (*head).namesz = 5;
    (*head).descsz = size_of::<ElfPrpsinfo64>() as u32;
    (*head).type_ = NT_PRPSINFO;
    let name = head.add(1).cast::<u8>();
    let core_name = b"CORE\0";
    for (idx, byte) in core_name.iter().copied().enumerate() {
        write_volatile(name.add(idx), byte);
    }
    let prpsinfo = name.add(gencore_align32_result(5)).cast::<ElfPrpsinfo64>();
    (*prpsinfo).pr_state = status as i8;
    (*prpsinfo).pr_pid = pid;
    for idx in 0..16 {
        write_volatile(
            (*prpsinfo).pr_fname.as_mut_ptr().add(idx),
            read_volatile(cmdline.add(idx)),
        );
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_fill_auxv_body_result(
    head: *mut ElfCoreNote,
    saved_auxv: *const CULong,
) -> CInt {
    if head.is_null() || saved_auxv.is_null() {
        return -EINVAL;
    }

    (*head).namesz = 5;
    (*head).descsz = (size_of::<CULong>() * AUXV_LEN as usize) as u32;
    (*head).type_ = NT_AUXV;
    let name = head.add(1).cast::<u8>();
    let core_name = b"CORE\0";
    for (idx, byte) in core_name.iter().copied().enumerate() {
        write_volatile(name.add(idx), byte);
    }
    let auxv = name.add(gencore_align32_result(5)).cast::<CULong>();
    for idx in 0..AUXV_LEN as usize {
        write_volatile(auxv.add(idx), read_volatile(saved_auxv.add(idx)));
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_fill_note_phdr_body_result(
    ph: *mut Elf64Phdr,
    offset: CULong,
    notesize: CLong,
) -> CInt {
    if ph.is_null() {
        return -EINVAL;
    }

    write_volatile(core::ptr::addr_of_mut!((*ph).p_type), PT_NOTE);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_flags), 0);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_offset), offset);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_vaddr), 0);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_paddr), 0);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_filesz), notesize as u64);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_memsz), notesize as u64);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_align), 0);

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_fill_load_phdr_body_result(
    ph: *mut Elf64Phdr,
    flags: CULong,
    offset: CULong,
    start: CULong,
    size: CULong,
) -> CInt {
    if ph.is_null() {
        return -EINVAL;
    }

    let ph_flags = if flags & VR_PROT_READ != 0 { PF_R } else { 0 }
        | if flags & VR_PROT_WRITE != 0 { PF_W } else { 0 }
        | if flags & VR_PROT_EXEC != 0 { PF_X } else { 0 };
    write_volatile(core::ptr::addr_of_mut!((*ph).p_type), PT_LOAD);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_flags), ph_flags);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_offset), offset);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_vaddr), start);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_paddr), 0);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_filesz), size);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_memsz), size);
    write_volatile(core::ptr::addr_of_mut!((*ph).p_align), PAGE_SIZE);

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_fill_initial_coretable_body_result(
    ct: *mut Coretable,
    eh_phys: CULong,
    ph_phys: CULong,
    note_phys: CULong,
    phsize: CLong,
    alignednotesize: CLong,
) -> CInt {
    if ct.is_null() {
        return -EINVAL;
    }

    write_volatile(core::ptr::addr_of_mut!((*ct.add(0)).addr), eh_phys);
    write_volatile(core::ptr::addr_of_mut!((*ct.add(0)).len), 64);
    write_volatile(core::ptr::addr_of_mut!((*ct.add(1)).addr), ph_phys);
    write_volatile(core::ptr::addr_of_mut!((*ct.add(1)).len), phsize);
    write_volatile(core::ptr::addr_of_mut!((*ct.add(2)).addr), note_phys);
    write_volatile(core::ptr::addr_of_mut!((*ct.add(2)).len), alignednotesize);

    0
}

pub type GencorePtVirtToPhysFn =
    Option<unsafe extern "C" fn(page_table: *mut c_void, vaddr: CULong, phys: *mut CULong) -> CInt>;
pub type GencoreVirtToPhysFn = Option<unsafe extern "C" fn(vaddr: CULong) -> CULong>;
pub type GencoreCoretableLogFn =
    Option<unsafe extern "C" fn(index: CInt, len: CLong, addr: CULong, start: CULong)>;
pub type GencoreLookupRangeFn = Option<unsafe extern "C" fn(vm: *mut c_void) -> *mut c_void>;
pub type GencoreNextRangeFn =
    Option<unsafe extern "C" fn(vm: *mut c_void, range: *mut c_void) -> *mut c_void>;
pub type GencoreRangeUlongFn = Option<unsafe extern "C" fn(range: *mut c_void) -> CULong>;
pub type GencoreRangeOffsetFn = Option<unsafe extern "C" fn(range: *mut c_void) -> CLong>;
pub type GencoreRangeLogFn =
    Option<unsafe extern "C" fn(start: CULong, end: CULong, flags: CULong, objoff: CLong)>;

#[no_mangle]
pub unsafe extern "C" fn gencore_count_range_chunks_body_result(
    start: CULong,
    end: CULong,
    flags: CULong,
    page_table: *mut c_void,
    chunksp: *mut CInt,
    pt_virt_to_phys_fn: GencorePtVirtToPhysFn,
) -> CInt {
    if chunksp.is_null() {
        return -EINVAL;
    }

    if flags & VR_DEMAND_PAGING == 0 {
        write_volatile(chunksp, read_volatile(chunksp).wrapping_add(1));
        return 0;
    }

    let Some(pt_virt_to_phys_fn) = pt_virt_to_phys_fn else {
        return -EINVAL;
    };

    let mut p = start;
    let mut phys = 0;
    let mut prevzero = 0;
    while p < end {
        if pt_virt_to_phys_fn(page_table, p, &mut phys) != 0 {
            prevzero = 1;
        } else {
            if prevzero == 1 {
                write_volatile(chunksp, read_volatile(chunksp).wrapping_add(1));
            }
            write_volatile(chunksp, read_volatile(chunksp).wrapping_add(1));
            prevzero = 0;
        }
        p = p.wrapping_add(PAGE_SIZE);
    }
    if prevzero == 1 {
        write_volatile(chunksp, read_volatile(chunksp).wrapping_add(1));
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_scan_ranges_for_counts_body_result(
    vm: *mut c_void,
    page_table: *mut c_void,
    chunksp: *mut CInt,
    segsp: *mut CInt,
    lookup_fn: GencoreLookupRangeFn,
    next_fn: GencoreNextRangeFn,
    start_fn: GencoreRangeUlongFn,
    end_fn: GencoreRangeUlongFn,
    flag_fn: GencoreRangeUlongFn,
    objoff_fn: GencoreRangeOffsetFn,
    log_fn: GencoreRangeLogFn,
    pt_virt_to_phys_fn: GencorePtVirtToPhysFn,
) -> CInt {
    let (
        Some(lookup_fn),
        Some(next_fn),
        Some(start_fn),
        Some(end_fn),
        Some(flag_fn),
        Some(objoff_fn),
        Some(log_fn),
    ) = (
        lookup_fn, next_fn, start_fn, end_fn, flag_fn, objoff_fn, log_fn,
    )
    else {
        return -EINVAL;
    };
    if chunksp.is_null() || segsp.is_null() {
        return -EINVAL;
    }

    let mut range = lookup_fn(vm);
    while !range.is_null() {
        let next_range = next_fn(vm, range);
        let start = start_fn(range);
        let end = end_fn(range);
        let flags = flag_fn(range);
        let objoff = objoff_fn(range);
        log_fn(start, end, flags, objoff);

        if gencore_range_inaccessible_result(flags) == 0 {
            let error = gencore_count_range_chunks_body_result(
                start,
                end,
                flags,
                page_table,
                chunksp,
                pt_virt_to_phys_fn,
            );
            if error != 0 {
                return error;
            }
            write_volatile(segsp, read_volatile(segsp).wrapping_add(1));
        }

        range = next_range;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_fill_load_phdrs_body_result(
    vm: *mut c_void,
    ph: *mut Elf64Phdr,
    indexp: *mut CInt,
    offsetp: *mut CULong,
    lookup_fn: GencoreLookupRangeFn,
    next_fn: GencoreNextRangeFn,
    start_fn: GencoreRangeUlongFn,
    end_fn: GencoreRangeUlongFn,
    flag_fn: GencoreRangeUlongFn,
) -> CInt {
    let (Some(lookup_fn), Some(next_fn), Some(start_fn), Some(end_fn), Some(flag_fn)) =
        (lookup_fn, next_fn, start_fn, end_fn, flag_fn)
    else {
        return -EINVAL;
    };
    if ph.is_null() || indexp.is_null() || offsetp.is_null() {
        return -EINVAL;
    }

    let mut index = read_volatile(indexp);
    let mut offset = read_volatile(offsetp);
    let mut range = lookup_fn(vm);
    while !range.is_null() {
        let next_range = next_fn(vm, range);
        let start = start_fn(range);
        let end = end_fn(range);
        let flags = flag_fn(range);

        if gencore_range_inaccessible_result(flags) == 0 {
            let size = end.wrapping_sub(start);
            let error = gencore_fill_load_phdr_body_result(
                ph.add(index as usize),
                flags,
                offset,
                start,
                size,
            );
            if error != 0 {
                return error;
            }
            index = index.wrapping_add(1);
            offset = offset.wrapping_add(size);
        }

        range = next_range;
    }

    write_volatile(indexp, index);
    write_volatile(offsetp, offset);
    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_emit_demand_coretable_body_result(
    ct: *mut Coretable,
    indexp: *mut CInt,
    start: CULong,
    end: CULong,
    page_table: *mut c_void,
    pt_virt_to_phys_fn: GencorePtVirtToPhysFn,
    log_fn: GencoreCoretableLogFn,
) -> CInt {
    let (Some(pt_virt_to_phys_fn), Some(log_fn)) = (pt_virt_to_phys_fn, log_fn) else {
        return -EINVAL;
    };
    if ct.is_null() || indexp.is_null() {
        return -EINVAL;
    }

    let mut index = read_volatile(indexp);
    let mut p = start;
    let mut zero_start = start;
    let mut zero_size = 0;
    let mut phys = 0;
    let mut prevzero = 0;

    while p < end {
        if pt_virt_to_phys_fn(page_table, p, &mut phys) != 0 {
            if prevzero == 0 {
                zero_size = PAGE_SIZE;
                zero_start = p;
            } else {
                zero_size = zero_size.wrapping_add(PAGE_SIZE);
            }
            prevzero = 1;
        } else {
            if prevzero == 1 {
                write_volatile(core::ptr::addr_of_mut!((*ct.add(index as usize)).addr), 0);
                write_volatile(
                    core::ptr::addr_of_mut!((*ct.add(index as usize)).len),
                    zero_size as CLong,
                );
                log_fn(index, zero_size as CLong, 0, zero_start);
                index = index.wrapping_add(1);
            }
            write_volatile(
                core::ptr::addr_of_mut!((*ct.add(index as usize)).addr),
                phys,
            );
            write_volatile(
                core::ptr::addr_of_mut!((*ct.add(index as usize)).len),
                PAGE_SIZE as CLong,
            );
            log_fn(index, PAGE_SIZE as CLong, phys, p);
            index = index.wrapping_add(1);
            prevzero = 0;
        }
        p = p.wrapping_add(PAGE_SIZE);
    }

    if prevzero == 1 {
        write_volatile(core::ptr::addr_of_mut!((*ct.add(index as usize)).addr), 0);
        write_volatile(
            core::ptr::addr_of_mut!((*ct.add(index as usize)).len),
            zero_size as CLong,
        );
        log_fn(index, zero_size as CLong, 0, zero_start);
        index = index.wrapping_add(1);
    }

    write_volatile(indexp, index);
    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_emit_linear_coretable_body_result(
    ct: *mut Coretable,
    indexp: *mut CInt,
    start: CULong,
    end: CULong,
    user_start: CULong,
    user_end: CULong,
    page_table: *mut c_void,
    pt_virt_to_phys_fn: GencorePtVirtToPhysFn,
    virt_to_phys_fn: GencoreVirtToPhysFn,
    log_fn: GencoreCoretableLogFn,
) -> CInt {
    let (Some(pt_virt_to_phys_fn), Some(virt_to_phys_fn), Some(log_fn)) =
        (pt_virt_to_phys_fn, virt_to_phys_fn, log_fn)
    else {
        return -EINVAL;
    };
    if ct.is_null() || indexp.is_null() {
        return -EINVAL;
    }

    let mut phys = 0;
    if user_start <= start && end <= user_end {
        let error = pt_virt_to_phys_fn(page_table, start, &mut phys);
        if error != 0 {
            if error != -EFAULT {
                return error;
            }
            phys = 0;
        }
    } else {
        phys = virt_to_phys_fn(start);
    }

    let index = read_volatile(indexp);
    let len = end.wrapping_sub(start) as CLong;
    write_volatile(
        core::ptr::addr_of_mut!((*ct.add(index as usize)).addr),
        phys,
    );
    write_volatile(core::ptr::addr_of_mut!((*ct.add(index as usize)).len), len);
    log_fn(index, len, phys, start);
    write_volatile(indexp, index.wrapping_add(1));

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_emit_coretable_ranges_body_result(
    vm: *mut c_void,
    ct: *mut Coretable,
    indexp: *mut CInt,
    user_start: CULong,
    user_end: CULong,
    page_table: *mut c_void,
    error_startp: *mut CULong,
    lookup_fn: GencoreLookupRangeFn,
    next_fn: GencoreNextRangeFn,
    start_fn: GencoreRangeUlongFn,
    end_fn: GencoreRangeUlongFn,
    flag_fn: GencoreRangeUlongFn,
    pt_virt_to_phys_fn: GencorePtVirtToPhysFn,
    virt_to_phys_fn: GencoreVirtToPhysFn,
    log_fn: GencoreCoretableLogFn,
) -> CInt {
    let (Some(lookup_fn), Some(next_fn), Some(start_fn), Some(end_fn), Some(flag_fn)) =
        (lookup_fn, next_fn, start_fn, end_fn, flag_fn)
    else {
        return -EINVAL;
    };
    if ct.is_null() || indexp.is_null() {
        return -EINVAL;
    }

    let mut range = lookup_fn(vm);
    while !range.is_null() {
        let next_range = next_fn(vm, range);
        let start = start_fn(range);
        let end = end_fn(range);
        let flags = flag_fn(range);

        if gencore_range_inaccessible_result(flags) == 0 {
            let error = if flags & VR_DEMAND_PAGING != 0 {
                gencore_emit_demand_coretable_body_result(
                    ct,
                    indexp,
                    start,
                    end,
                    page_table,
                    pt_virt_to_phys_fn,
                    log_fn,
                )
            } else {
                gencore_emit_linear_coretable_body_result(
                    ct,
                    indexp,
                    start,
                    end,
                    user_start,
                    user_end,
                    page_table,
                    pt_virt_to_phys_fn,
                    virt_to_phys_fn,
                    log_fn,
                )
            };
            if error != 0 {
                if !error_startp.is_null() {
                    write_volatile(error_startp, start);
                }
                return error;
            }
        }

        range = next_range;
    }

    0
}

pub type GencorePhysToVirtFn = Option<unsafe extern "C" fn(phys: CULong) -> *mut c_void>;
pub type GencoreFreeFn = Option<unsafe extern "C" fn(ptr: *mut c_void)>;
pub type GencoreAllocFn = Option<unsafe extern "C" fn(size: SizeT, flags: CULong) -> *mut c_void>;
pub type GencoreZeroFn = Option<unsafe extern "C" fn(ptr: *mut c_void, size: SizeT)>;
pub type GencoreGetNoteSizeFn = Option<unsafe extern "C" fn(proc: *mut c_void) -> CInt>;
pub type GencoreFillNoteFn =
    Option<unsafe extern "C" fn(note: *mut c_void, proc: *mut c_void, cmdline: *mut i8, sig: CInt)>;
pub type GencoreAllocErrorLogFn = Option<unsafe extern "C" fn(stage: CInt)>;
pub type GencorePtErrorLogFn = Option<unsafe extern "C" fn(start: CULong, error: CInt)>;
pub type GencoreFirstThreadFn = Option<unsafe extern "C" fn(proc: *mut c_void) -> *mut c_void>;
pub type GencoreNextThreadFn =
    Option<unsafe extern "C" fn(proc: *mut c_void, thread: *mut c_void) -> *mut c_void>;
pub type GencoreThreadTidFn = Option<unsafe extern "C" fn(thread: *mut c_void) -> CInt>;
pub type GencoreThreadRegsFn = Option<unsafe extern "C" fn(thread: *mut c_void) -> *mut c_void>;
pub type GencoreArchThreadInfoSizeFn = Option<unsafe extern "C" fn() -> CInt>;
pub type GencoreFillPrstatusNoteFn =
    Option<unsafe extern "C" fn(note: *mut c_void, thread: *mut c_void, sig: CInt)>;
pub type GencoreArchFillThreadInfoFn =
    Option<unsafe extern "C" fn(note: *mut c_void, thread: *mut c_void, regs: *mut c_void)>;
pub type GencoreFillProcNoteFn =
    Option<unsafe extern "C" fn(note: *mut c_void, proc: *mut c_void, cmdline: *mut i8)>;
pub type GencoreFillAuxvNoteFn = Option<unsafe extern "C" fn(note: *mut c_void, proc: *mut c_void)>;

const GENCORE_ALLOC_STAGE_ELF_HEADER: CInt = 0;
const GENCORE_ALLOC_STAGE_PROGRAM_HEADER: CInt = 1;
const GENCORE_ALLOC_STAGE_NOTE: CInt = 2;
const GENCORE_ALLOC_STAGE_CORETABLE: CInt = 3;

unsafe fn gencore_cleanup_generated(
    eh: *mut c_void,
    ct: *mut c_void,
    ph: *mut c_void,
    note: *mut c_void,
    free_fn: unsafe extern "C" fn(ptr: *mut c_void),
) {
    free_fn(eh);
    free_fn(ct);
    free_fn(ph);
    free_fn(note);
}

#[no_mangle]
pub unsafe extern "C" fn gencore_note_size_threads_body_result(
    proc: *mut c_void,
    pid: CInt,
    first_fn: GencoreFirstThreadFn,
    next_fn: GencoreNextThreadFn,
    tid_fn: GencoreThreadTidFn,
    arch_size_fn: GencoreArchThreadInfoSizeFn,
) -> CInt {
    let (Some(first_fn), Some(next_fn), Some(tid_fn), Some(arch_size_fn)) =
        (first_fn, next_fn, tid_fn, arch_size_fn)
    else {
        return -EINVAL;
    };
    if proc.is_null() {
        return -EINVAL;
    }

    let mut note = 0;
    let mut thread = first_fn(proc);
    while !thread.is_null() {
        note += gencore_prstatus_size_result();
        note += arch_size_fn();
        if tid_fn(thread) == pid {
            note += gencore_prpsinfo_size_result();
            note += gencore_auxv_size_result();
        }
        thread = next_fn(proc, thread);
    }

    note
}

#[no_mangle]
pub unsafe extern "C" fn gencore_fill_note_threads_body_result(
    note: *mut c_void,
    proc: *mut c_void,
    cmdline: *mut i8,
    sig: CInt,
    pid: CInt,
    end_notep: *mut *mut c_void,
    first_fn: GencoreFirstThreadFn,
    next_fn: GencoreNextThreadFn,
    tid_fn: GencoreThreadTidFn,
    regs_fn: GencoreThreadRegsFn,
    arch_size_fn: GencoreArchThreadInfoSizeFn,
    fill_prstatus_fn: GencoreFillPrstatusNoteFn,
    arch_fill_fn: GencoreArchFillThreadInfoFn,
    fill_prpsinfo_fn: GencoreFillProcNoteFn,
    fill_auxv_fn: GencoreFillAuxvNoteFn,
) -> CInt {
    let (
        Some(first_fn),
        Some(next_fn),
        Some(tid_fn),
        Some(regs_fn),
        Some(arch_size_fn),
        Some(fill_prstatus_fn),
        Some(arch_fill_fn),
        Some(fill_prpsinfo_fn),
        Some(fill_auxv_fn),
    ) = (
        first_fn,
        next_fn,
        tid_fn,
        regs_fn,
        arch_size_fn,
        fill_prstatus_fn,
        arch_fill_fn,
        fill_prpsinfo_fn,
        fill_auxv_fn,
    )
    else {
        return -EINVAL;
    };
    if note.is_null() || proc.is_null() || cmdline.is_null() {
        return -EINVAL;
    }

    let mut cursor = note.cast::<u8>();
    let mut thread = first_fn(proc);
    while !thread.is_null() {
        fill_prstatus_fn(cursor.cast::<c_void>(), thread, sig);
        cursor = cursor.add(gencore_prstatus_size_result() as usize);

        arch_fill_fn(cursor.cast::<c_void>(), thread, regs_fn(thread));
        cursor = cursor.add(arch_size_fn() as usize);

        if tid_fn(thread) == pid {
            fill_prpsinfo_fn(cursor.cast::<c_void>(), proc, cmdline);
            cursor = cursor.add(gencore_prpsinfo_size_result() as usize);
            fill_auxv_fn(cursor.cast::<c_void>(), proc);
            cursor = cursor.add(gencore_auxv_size_result() as usize);
        }

        thread = next_fn(proc, thread);
    }
    if !end_notep.is_null() {
        write_volatile(end_notep, cursor.cast::<c_void>());
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_freecore_body_result(
    coretablep: *mut *mut Coretable,
    phys_to_virt_fn: GencorePhysToVirtFn,
    free_fn: GencoreFreeFn,
) -> CInt {
    let (Some(phys_to_virt_fn), Some(free_fn)) = (phys_to_virt_fn, free_fn) else {
        return -EINVAL;
    };
    if coretablep.is_null() {
        return -EINVAL;
    }
    let ct = *coretablep;
    if ct.is_null() {
        return -EINVAL;
    }

    free_fn(phys_to_virt_fn((*ct.add(2)).addr));
    free_fn(phys_to_virt_fn((*ct.add(1)).addr));
    free_fn(phys_to_virt_fn((*ct.add(0)).addr));
    free_fn(ct.cast::<c_void>());

    0
}

#[no_mangle]
pub unsafe extern "C" fn gencore_generate_image_body_result(
    proc: *mut c_void,
    vm: *mut c_void,
    page_table: *mut c_void,
    coretablep: *mut *mut Coretable,
    chunksp: *mut CInt,
    segs: CInt,
    user_start: CULong,
    user_end: CULong,
    cmdline: *mut i8,
    sig: CInt,
    eh_size: SizeT,
    phdr_size: SizeT,
    coretable_size: SizeT,
    alloc_fn: GencoreAllocFn,
    zero_fn: GencoreZeroFn,
    free_fn: GencoreFreeFn,
    get_note_size_fn: GencoreGetNoteSizeFn,
    fill_note_fn: GencoreFillNoteFn,
    virt_to_phys_fn: GencoreVirtToPhysFn,
    lookup_fn: GencoreLookupRangeFn,
    next_fn: GencoreNextRangeFn,
    start_fn: GencoreRangeUlongFn,
    end_fn: GencoreRangeUlongFn,
    flag_fn: GencoreRangeUlongFn,
    pt_virt_to_phys_fn: GencorePtVirtToPhysFn,
    coretable_log_fn: GencoreCoretableLogFn,
    alloc_error_log_fn: GencoreAllocErrorLogFn,
    pt_error_log_fn: GencorePtErrorLogFn,
) -> CInt {
    let (
        Some(alloc_fn),
        Some(zero_fn),
        Some(free_fn),
        Some(get_note_size_fn),
        Some(fill_note_fn),
        Some(virt_to_phys_fn),
        Some(coretable_log_fn),
        Some(alloc_error_log_fn),
        Some(pt_error_log_fn),
    ) = (
        alloc_fn,
        zero_fn,
        free_fn,
        get_note_size_fn,
        fill_note_fn,
        virt_to_phys_fn,
        coretable_log_fn,
        alloc_error_log_fn,
        pt_error_log_fn,
    )
    else {
        return -EINVAL;
    };
    if proc.is_null()
        || vm.is_null()
        || coretablep.is_null()
        || chunksp.is_null()
        || cmdline.is_null()
        || segs <= 0
    {
        return -EINVAL;
    }

    let eh: *mut c_void;
    let mut ph = core::ptr::null_mut::<c_void>();
    let mut note = core::ptr::null_mut::<c_void>();
    let mut ct = core::ptr::null_mut::<Coretable>();
    let mut offset: CULong = 0;
    let mut index: CInt;

    eh = alloc_fn(eh_size, IHK_MC_AP_NOWAIT);
    if eh.is_null() {
        alloc_error_log_fn(GENCORE_ALLOC_STAGE_ELF_HEADER);
        return -ENOMEM;
    }
    zero_fn(eh, eh_size);
    offset = offset.wrapping_add(eh_size as CULong);
    let mut error = gencore_fill_elf_header_body_result(eh.cast::<Elf64Ehdr>(), segs);
    if error != 0 {
        gencore_cleanup_generated(eh, ct.cast::<c_void>(), ph, note, free_fn);
        return error;
    }

    let phsize = phdr_size.wrapping_mul(segs as SizeT);
    ph = alloc_fn(phsize, IHK_MC_AP_NOWAIT);
    if ph.is_null() {
        alloc_error_log_fn(GENCORE_ALLOC_STAGE_PROGRAM_HEADER);
        gencore_cleanup_generated(eh, ct.cast::<c_void>(), ph, note, free_fn);
        return -ENOMEM;
    }
    zero_fn(ph, phsize);
    offset = offset.wrapping_add(phsize as CULong);

    let notesize = get_note_size_fn(proc);
    let alignednotesize =
        (gencore_alignpage_result(offset.wrapping_add(notesize as CULong) as SizeT) as CULong)
            .wrapping_sub(offset);
    note = alloc_fn(alignednotesize as SizeT, IHK_MC_AP_NOWAIT);
    if note.is_null() {
        alloc_error_log_fn(GENCORE_ALLOC_STAGE_NOTE);
        gencore_cleanup_generated(eh, ct.cast::<c_void>(), ph, note, free_fn);
        return -ENOMEM;
    }
    zero_fn(note, alignednotesize as SizeT);
    fill_note_fn(note, proc, cmdline, sig);

    error = gencore_fill_note_phdr_body_result(ph.cast::<Elf64Phdr>(), offset, notesize as CLong);
    if error != 0 {
        gencore_cleanup_generated(eh, ct.cast::<c_void>(), ph, note, free_fn);
        return error;
    }
    offset = offset.wrapping_add(alignednotesize);

    index = 1;
    error = gencore_fill_load_phdrs_body_result(
        vm,
        ph.cast::<Elf64Phdr>(),
        &mut index,
        &mut offset,
        lookup_fn,
        next_fn,
        start_fn,
        end_fn,
        flag_fn,
    );
    if error != 0 {
        gencore_cleanup_generated(eh, ct.cast::<c_void>(), ph, note, free_fn);
        return error;
    }

    let ct_bytes = coretable_size.wrapping_mul(read_volatile(chunksp) as SizeT);
    ct = alloc_fn(ct_bytes, IHK_MC_AP_NOWAIT).cast::<Coretable>();
    if ct.is_null() {
        alloc_error_log_fn(GENCORE_ALLOC_STAGE_CORETABLE);
        gencore_cleanup_generated(eh, ct.cast::<c_void>(), ph, note, free_fn);
        return -ENOMEM;
    }
    zero_fn(ct.cast::<c_void>(), ct_bytes);

    error = gencore_fill_initial_coretable_body_result(
        ct,
        virt_to_phys_fn(eh as CULong),
        virt_to_phys_fn(ph as CULong),
        virt_to_phys_fn(note as CULong),
        phsize as CLong,
        alignednotesize as CLong,
    );
    if error != 0 {
        gencore_cleanup_generated(eh, ct.cast::<c_void>(), ph, note, free_fn);
        return error;
    }

    for entry in 0..3 {
        coretable_log_fn(
            entry,
            read_volatile(core::ptr::addr_of!((*ct.add(entry as usize)).len)),
            read_volatile(core::ptr::addr_of!((*ct.add(entry as usize)).addr)),
            match entry {
                0 => eh as CULong,
                1 => ph as CULong,
                _ => note as CULong,
            },
        );
    }

    index = 3;
    let mut error_start = 0;
    error = gencore_emit_coretable_ranges_body_result(
        vm,
        ct,
        &mut index,
        user_start,
        user_end,
        page_table,
        &mut error_start,
        lookup_fn,
        next_fn,
        start_fn,
        end_fn,
        flag_fn,
        pt_virt_to_phys_fn,
        Some(virt_to_phys_fn),
        Some(coretable_log_fn),
    );
    if error != 0 {
        pt_error_log_fn(error_start, error);
        gencore_cleanup_generated(eh, ct.cast::<c_void>(), ph, note, free_fn);
        return error;
    }

    write_volatile(coretablep, ct);
    0
}

#[no_mangle]
pub unsafe extern "C" fn shmobj_destroy_body_result(
    obj: *mut c_void,
    user: *mut c_void,
    real_segsz: SizeT,
    index: CInt,
    user_clear_fn: ShmobjUserClearFn,
    user_locked_fn: ShmobjUserLockedFn,
    user_set_locked_fn: ShmobjUserSetLockedFn,
    users_lock_fn: ShmobjPageListLockFn,
    users_unlock_fn: ShmobjPageListUnlockFn,
    user_free_fn: ShmobjUserFreeFn,
    page_first_fn: ShmobjPageFirstFn,
    page_remove_fn: ShmobjPageRemoveFn,
    page_phys_fn: ShmobjPagePhysFn,
    phys_to_virt_fn: ShmobjPhysToVirtFn,
    page_pgshift_fn: ShmobjPagePgshiftFn,
    page_count_fn: ShmobjPageCountFn,
    page_unmap_fn: ShmobjPageUnmapFn,
    free_page_fn: ShmobjFreePageFn,
    rss_sub_fn: ShmobjRssSubFn,
    free_fn: ShmobjFreeFn,
    indexed_free_fn: ShmobjIndexedFreeFn,
    log_fn: ShmobjDestroyLogFn,
) -> CInt {
    let user_clear_fn = match user_clear_fn {
        Some(user_clear_fn) => user_clear_fn,
        None => return -EINVAL,
    };
    let user_locked_fn = match user_locked_fn {
        Some(user_locked_fn) => user_locked_fn,
        None => return -EINVAL,
    };
    let user_set_locked_fn = match user_set_locked_fn {
        Some(user_set_locked_fn) => user_set_locked_fn,
        None => return -EINVAL,
    };
    let users_lock_fn = match users_lock_fn {
        Some(users_lock_fn) => users_lock_fn,
        None => return -EINVAL,
    };
    let users_unlock_fn = match users_unlock_fn {
        Some(users_unlock_fn) => users_unlock_fn,
        None => return -EINVAL,
    };
    let user_free_fn = match user_free_fn {
        Some(user_free_fn) => user_free_fn,
        None => return -EINVAL,
    };
    let page_first_fn = match page_first_fn {
        Some(page_first_fn) => page_first_fn,
        None => return -EINVAL,
    };
    let page_remove_fn = match page_remove_fn {
        Some(page_remove_fn) => page_remove_fn,
        None => return -EINVAL,
    };
    let page_phys_fn = match page_phys_fn {
        Some(page_phys_fn) => page_phys_fn,
        None => return -EINVAL,
    };
    let phys_to_virt_fn = match phys_to_virt_fn {
        Some(phys_to_virt_fn) => phys_to_virt_fn,
        None => return -EINVAL,
    };
    let page_pgshift_fn = match page_pgshift_fn {
        Some(page_pgshift_fn) => page_pgshift_fn,
        None => return -EINVAL,
    };
    let page_count_fn = match page_count_fn {
        Some(page_count_fn) => page_count_fn,
        None => return -EINVAL,
    };
    let page_unmap_fn = match page_unmap_fn {
        Some(page_unmap_fn) => page_unmap_fn,
        None => return -EINVAL,
    };
    let free_page_fn = match free_page_fn {
        Some(free_page_fn) => free_page_fn,
        None => return -EINVAL,
    };
    let rss_sub_fn = match rss_sub_fn {
        Some(rss_sub_fn) => rss_sub_fn,
        None => return -EINVAL,
    };
    let free_fn = match free_fn {
        Some(free_fn) => free_fn,
        None => return -EINVAL,
    };
    let indexed_free_fn = match indexed_free_fn {
        Some(indexed_free_fn) => indexed_free_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if obj.is_null() {
        return -EINVAL;
    }

    if shmobj_has_user_result(user as CULong) != 0 {
        user_clear_fn(obj);
        users_lock_fn(obj);
        let locked = shmlock_user_after_unlock_result(user_locked_fn(user), real_segsz);
        user_set_locked_fn(user, locked);
        if shmlock_user_should_free_result(locked) != 0 {
            user_free_fn(user);
        }
        users_unlock_fn(obj);
    }

    loop {
        let page = page_first_fn(obj);
        if page.is_null() {
            break;
        }
        page_remove_fn(obj, page);
        let phys = page_phys_fn(page);
        let page_va = phys_to_virt_fn(phys);
        let pgshift = page_pgshift_fn(page);
        let npages = shmobj_destroy_page_npages_result(pgshift);
        let count = page_count_fn(page);

        if shmobj_destroy_page_count_invalid_result(count) != 0 {
            log_fn(12, obj, page, phys, 0, 0);
        } else if shmobj_destroy_page_should_free_result(count, page_unmap_fn(page)) != 0 {
            let free_pgsize = shmobj_destroy_page_size_result(pgshift);
            let free_size = shmobj_destroy_page_size_result(pgshift);
            free_page_fn(page_va, npages);
            log_fn(13, obj, page, phys, free_size, free_pgsize);
            rss_sub_fn(free_size, free_pgsize);
            free_fn(page);
        }
    }

    if shmobj_should_free_direct_result(index) != 0 {
        free_fn(obj);
    } else {
        indexed_free_fn(
            obj,
            shmobj_destroy_index_word_result(index),
            shmobj_destroy_index_mask_result(index),
        );
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn shmobj_free_body_result(
    memobj: *mut c_void,
    obj: *mut c_void,
    mode: CInt,
    list_lock_fn: ShmobjPageListLockFn,
    list_unlock_fn: ShmobjPageListUnlockFn,
    destroy_fn: ShmobjDestroyFn,
    log_fn: ShmobjFreeLogFn,
) -> CInt {
    let list_lock_fn = match list_lock_fn {
        Some(list_lock_fn) => list_lock_fn,
        None => return -EINVAL,
    };
    let list_unlock_fn = match list_unlock_fn {
        Some(list_unlock_fn) => list_unlock_fn,
        None => return -EINVAL,
    };
    let destroy_fn = match destroy_fn {
        Some(destroy_fn) => destroy_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if obj.is_null() {
        return -EINVAL;
    }

    list_lock_fn(obj);
    if shmobj_destroy_missing_flag_result(mode) != 0 {
        log_fn(14, memobj);
    }
    destroy_fn(obj);
    list_unlock_fn(obj);
    0
}

#[no_mangle]
pub extern "C" fn hugefileobj_expected_p2align_result(pgshift: CInt) -> CInt {
    pgshift - PTL1_SHIFT
}

#[no_mangle]
pub extern "C" fn hugefileobj_validate_p2align_result(p2align: CInt, pgshift: CInt) -> CInt {
    if p2align == hugefileobj_expected_p2align_result(pgshift) {
        0
    } else {
        -ENOMEM
    }
}

#[no_mangle]
pub extern "C" fn hugefileobj_page_index_result(off: OffT, pgshift: CInt) -> OffT {
    off >> pgshift
}

#[no_mangle]
pub extern "C" fn hugefileobj_npages_per_page_result(pgsize: SizeT) -> CInt {
    (pgsize >> PAGE_SHIFT) as CInt
}

#[no_mangle]
pub extern "C" fn hugefileobj_pgsize_result(pgshift: CInt) -> SizeT {
    1usize << pgshift
}

#[no_mangle]
pub extern "C" fn hugefileobj_initial_status_result() -> CInt {
    MEMOBJ_READY
}

#[no_mangle]
pub extern "C" fn hugefileobj_initial_refcnt_result() -> CInt {
    2
}

#[no_mangle]
pub extern "C" fn hugefileobj_pointer_present_result(ptr: CULong) -> CInt {
    (ptr != 0) as CInt
}

#[no_mangle]
pub extern "C" fn hugefileobj_pointer_missing_result(ptr: CULong) -> CInt {
    (ptr == 0) as CInt
}

#[no_mangle]
pub extern "C" fn hugefileobj_page_present_result(page: CULong) -> CInt {
    (page != 0) as CInt
}

#[no_mangle]
pub extern "C" fn hugefileobj_page_array_bytes_result(nr_pages: SizeT) -> SizeT {
    nr_pages * core::mem::size_of::<*mut u8>()
}

#[no_mangle]
pub extern "C" fn hugefileobj_create_nr_pages_result(off: OffT, len: SizeT, pgshift: CInt) -> CInt {
    (off.wrapping_add(len as OffT) >> pgshift) as CInt
}

#[no_mangle]
pub extern "C" fn hugefileobj_needs_grow_result(
    current_nr_pages: SizeT,
    needed_nr_pages: CInt,
) -> CInt {
    (current_nr_pages < needed_nr_pages as SizeT) as CInt
}

#[no_mangle]
pub extern "C" fn hugefileobj_copy_bytes_result(current_nr_pages: SizeT) -> SizeT {
    current_nr_pages * core::mem::size_of::<*mut u8>()
}

#[no_mangle]
pub extern "C" fn hugefileobj_zero_bytes_result(old_nr_pages: SizeT, new_nr_pages: SizeT) -> SizeT {
    new_nr_pages.wrapping_sub(old_nr_pages) * core::mem::size_of::<*mut u8>()
}

#[no_mangle]
pub extern "C" fn hugefileobj_zero_start_index_result(old_nr_pages: SizeT) -> SizeT {
    old_nr_pages
}

pub type HugefileobjVoidFn = Option<unsafe extern "C" fn(arg: *mut c_void)>;
pub type HugefileobjBoolFn = Option<unsafe extern "C" fn(arg: *mut c_void) -> CInt>;
pub type HugefileobjFirstFn = Option<unsafe extern "C" fn(arg: *mut c_void) -> *mut c_void>;
pub type HugefileobjAllocFn =
    Option<unsafe extern "C" fn(size: SizeT, flags: CULong) -> *mut c_void>;
pub type HugefileobjAllocPageFn = Option<
    unsafe extern "C" fn(
        npages: CInt,
        p2align: CInt,
        flags: CULong,
        virt_addr: CULong,
    ) -> *mut c_void,
>;
pub type HugefileobjFreePageFn = Option<unsafe extern "C" fn(page: *mut c_void, npages: CInt)>;
pub type HugefileobjMemcpyFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, src: *const c_void, len: SizeT) -> *mut c_void>;
pub type HugefileobjMemsetFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, value: CInt, len: SizeT) -> *mut c_void>;
pub type HugefileobjPhysFn = Option<unsafe extern "C" fn(addr: *mut c_void) -> CULong>;
pub type HugefileobjPageAtFn =
    Option<unsafe extern "C" fn(obj: *mut c_void, index: CLong) -> *mut c_void>;
pub type HugefileobjSetPageFn =
    Option<unsafe extern "C" fn(obj: *mut c_void, index: CLong, page: *mut c_void)>;
pub type HugefileobjLookupFn = Option<unsafe extern "C" fn(handle: CULong) -> *mut c_void>;
pub type HugefileobjToMemobjFn = Option<unsafe extern "C" fn(obj: *mut c_void) -> *mut c_void>;
pub type HugefileobjNextFn =
    Option<unsafe extern "C" fn(head: *mut c_void, obj: *mut c_void) -> *mut c_void>;
pub type HugefileobjHandleFn = Option<unsafe extern "C" fn(obj: *mut c_void) -> CULong>;
pub type HugefileobjRefFn = Option<unsafe extern "C" fn(obj: *mut c_void) -> CInt>;
pub type HugefileobjSetHandleFn = Option<unsafe extern "C" fn(obj: *mut c_void, handle: CULong)>;
pub type HugefileobjSetPgsizeFn = Option<unsafe extern "C" fn(obj: *mut c_void, pgsize: SizeT)>;
pub type HugefileobjSetPgshiftFn = Option<unsafe extern "C" fn(obj: *mut c_void, pgshift: CInt)>;
pub type HugefileobjSetFlagsFn = Option<unsafe extern "C" fn(obj: *mut c_void, flags: u32)>;
pub type HugefileobjSetStatusFn = Option<unsafe extern "C" fn(obj: *mut c_void, status: CInt)>;
pub type HugefileobjSetOpsFn = Option<unsafe extern "C" fn(obj: *mut c_void, ops: *mut c_void)>;
pub type HugefileobjSetRefcntFn = Option<unsafe extern "C" fn(obj: *mut c_void, refcnt: CInt)>;
pub type HugefileobjSetPathFn = Option<unsafe extern "C" fn(obj: *mut c_void, path: *mut c_void)>;
pub type HugefileobjCopyPathFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, src: *const c_void, len: SizeT)>;
pub type HugefileobjDecFn = Option<unsafe extern "C" fn(obj: *mut c_void)>;
pub type HugefileobjPreCreateLogFn = Option<unsafe extern "C" fn(event: CInt, obj: *mut c_void)>;
pub type HugefileobjAllocErrorFn = Option<unsafe extern "C" fn(stage: CInt)>;
pub type HugefileobjSetSizeFn = Option<unsafe extern "C" fn(obj: *mut c_void, size: SizeT)>;
pub type HugefileobjSetNrPagesFn = Option<unsafe extern "C" fn(obj: *mut c_void, nr_pages: SizeT)>;
pub type HugefileobjSetPagesFn = Option<unsafe extern "C" fn(obj: *mut c_void, pages: *mut c_void)>;
pub type HugefileobjLogFn = Option<
    unsafe extern "C" fn(
        event: CInt,
        obj: *mut c_void,
        off: OffT,
        index: CLong,
        pgsize: SizeT,
        virt_addr: CULong,
    ),
>;

const HUGEFILEOBJ_LOG_PRE_CREATE_FOUND: CInt = 6;
const HUGEFILEOBJ_LOG_PRE_CREATE_CREATED: CInt = 7;
const HUGEFILEOBJ_PRE_CREATE_ALLOC_OBJ: CInt = 1;
const HUGEFILEOBJ_PRE_CREATE_ALLOC_PATH: CInt = 2;

#[no_mangle]
pub unsafe extern "C" fn hugefileobj_free_body_result(
    obj: *mut c_void,
    lock: *mut c_void,
    lock_fn: HugefileobjVoidFn,
    unlock_fn: HugefileobjVoidFn,
    list_del_fn: HugefileobjVoidFn,
    free_fn: HugefileobjVoidFn,
) -> CInt {
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let list_del_fn = match list_del_fn {
        Some(list_del_fn) => list_del_fn,
        None => return -EINVAL,
    };
    let free_fn = match free_fn {
        Some(free_fn) => free_fn,
        None => return -EINVAL,
    };
    if obj.is_null() || lock.is_null() {
        return -EINVAL;
    }

    lock_fn(lock);
    list_del_fn(obj);
    unlock_fn(lock);
    free_fn(obj);

    0
}

#[no_mangle]
pub unsafe extern "C" fn hugefileobj_cleanup_body_result(
    lock: *mut c_void,
    list_head: *mut c_void,
    lock_fn: HugefileobjVoidFn,
    unlock_fn: HugefileobjVoidFn,
    list_empty_fn: HugefileobjBoolFn,
    first_fn: HugefileobjFirstFn,
    list_del_fn: HugefileobjVoidFn,
    free_fn: HugefileobjVoidFn,
) -> CInt {
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let list_empty_fn = match list_empty_fn {
        Some(list_empty_fn) => list_empty_fn,
        None => return -EINVAL,
    };
    let first_fn = match first_fn {
        Some(first_fn) => first_fn,
        None => return -EINVAL,
    };
    let list_del_fn = match list_del_fn {
        Some(list_del_fn) => list_del_fn,
        None => return -EINVAL,
    };
    let free_fn = match free_fn {
        Some(free_fn) => free_fn,
        None => return -EINVAL,
    };
    if lock.is_null() || list_head.is_null() {
        return -EINVAL;
    }

    let mut count = 0;
    loop {
        lock_fn(lock);
        if list_empty_fn(list_head) != 0 {
            unlock_fn(lock);
            break;
        }

        let obj = first_fn(list_head);
        if obj.is_null() {
            unlock_fn(lock);
            return -EINVAL;
        }
        list_del_fn(obj);
        unlock_fn(lock);

        free_fn(obj);
        count += 1;
    }

    count
}

#[no_mangle]
pub unsafe extern "C" fn hugefileobj_inner_free_body_result(
    obj: *mut c_void,
    lock: *mut c_void,
    path: *mut c_void,
    pages: *mut c_void,
    nr_pages: SizeT,
    pgsize: SizeT,
    lock_fn: HugefileobjVoidFn,
    unlock_fn: HugefileobjVoidFn,
    free_fn: HugefileobjVoidFn,
    free_page_fn: HugefileobjFreePageFn,
    page_at_fn: HugefileobjPageAtFn,
    clear_path_fn: HugefileobjVoidFn,
    log_fn: HugefileobjLogFn,
) -> CInt {
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let free_fn = match free_fn {
        Some(free_fn) => free_fn,
        None => return -EINVAL,
    };
    let free_page_fn = match free_page_fn {
        Some(free_page_fn) => free_page_fn,
        None => return -EINVAL,
    };
    let page_at_fn = match page_at_fn {
        Some(page_at_fn) => page_at_fn,
        None => return -EINVAL,
    };
    let clear_path_fn = match clear_path_fn {
        Some(clear_path_fn) => clear_path_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if obj.is_null() || lock.is_null() {
        return -EINVAL;
    }

    let npages = hugefileobj_npages_per_page_result(pgsize);
    lock_fn(lock);
    if hugefileobj_pointer_present_result(path as CULong) != 0 {
        free_fn(path);
        clear_path_fn(obj);
    }

    if hugefileobj_pointer_present_result(pages as CULong) != 0 {
        let mut index = 0usize;
        while index < nr_pages {
            let page = page_at_fn(obj, index as CLong);
            if hugefileobj_page_present_result(page as CULong) != 0 {
                free_page_fn(page, npages);
                log_fn(3, obj, 0, index as CLong, pgsize, 0);
            }
            index += 1;
        }

        free_fn(pages);
    }

    unlock_fn(lock);
    free_fn(obj);

    0
}

#[no_mangle]
pub unsafe extern "C" fn hugefileobj_get_page_body_result(
    obj: *mut c_void,
    lock: *mut c_void,
    off: OffT,
    p2align: CInt,
    pgshift: CInt,
    pgsize: SizeT,
    virt_addr: CULong,
    physp: *mut CULong,
    lock_fn: HugefileobjVoidFn,
    unlock_fn: HugefileobjVoidFn,
    page_at_fn: HugefileobjPageAtFn,
    set_page_fn: HugefileobjSetPageFn,
    alloc_page_fn: HugefileobjAllocPageFn,
    memset_fn: HugefileobjMemsetFn,
    phys_fn: HugefileobjPhysFn,
    log_fn: HugefileobjLogFn,
) -> CInt {
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let page_at_fn = match page_at_fn {
        Some(page_at_fn) => page_at_fn,
        None => return -EINVAL,
    };
    let set_page_fn = match set_page_fn {
        Some(set_page_fn) => set_page_fn,
        None => return -EINVAL,
    };
    let alloc_page_fn = match alloc_page_fn {
        Some(alloc_page_fn) => alloc_page_fn,
        None => return -EINVAL,
    };
    let memset_fn = match memset_fn {
        Some(memset_fn) => memset_fn,
        None => return -EINVAL,
    };
    let phys_fn = match phys_fn {
        Some(phys_fn) => phys_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if obj.is_null() || lock.is_null() || physp.is_null() {
        return -EINVAL;
    }

    let ret = hugefileobj_validate_p2align_result(p2align, pgshift);
    if ret != 0 {
        log_fn(
            5,
            obj,
            off,
            p2align as CLong,
            pgsize,
            hugefileobj_expected_p2align_result(pgshift) as CULong,
        );
        return ret;
    }

    let pgind = hugefileobj_page_index_result(off, pgshift);
    let npages = hugefileobj_npages_per_page_result(pgsize);
    lock_fn(lock);
    let mut page = page_at_fn(obj, pgind as CLong);
    let mut result = 0;
    if hugefileobj_page_present_result(page as CULong) == 0 {
        page = alloc_page_fn(
            npages,
            p2align,
            IHK_MC_AP_NOWAIT | IHK_MC_AP_USER,
            virt_addr,
        );
        if page.is_null() {
            log_fn(1, obj, off, pgind as CLong, pgsize, virt_addr);
            result = -EIO;
        } else {
            set_page_fn(obj, pgind as CLong, page);
            memset_fn(page, 0, pgsize);
            log_fn(2, obj, off, pgind as CLong, pgsize, virt_addr);
        }
    }

    if result == 0 {
        *physp = phys_fn(page);
    }
    unlock_fn(lock);

    result
}

#[no_mangle]
pub unsafe extern "C" fn hugefileobj_create_body_result(
    obj: *mut c_void,
    lock: *mut c_void,
    len: SizeT,
    off: OffT,
    pgshift: CInt,
    pgsize: SizeT,
    current_nr_pages: SizeT,
    current_pages: *mut c_void,
    pgshiftp: *mut CInt,
    virt_addr: CULong,
    alloc_flags: CULong,
    lock_fn: HugefileobjVoidFn,
    unlock_fn: HugefileobjVoidFn,
    alloc_fn: HugefileobjAllocFn,
    free_fn: HugefileobjVoidFn,
    memcpy_fn: HugefileobjMemcpyFn,
    memset_fn: HugefileobjMemsetFn,
    set_nr_pages_fn: HugefileobjSetNrPagesFn,
    set_pages_fn: HugefileobjSetPagesFn,
    set_size_fn: HugefileobjSetSizeFn,
    log_fn: HugefileobjLogFn,
) -> CInt {
    let lock_fn = match lock_fn {
        Some(lock_fn) => lock_fn,
        None => return -EINVAL,
    };
    let unlock_fn = match unlock_fn {
        Some(unlock_fn) => unlock_fn,
        None => return -EINVAL,
    };
    let alloc_fn = match alloc_fn {
        Some(alloc_fn) => alloc_fn,
        None => return -EINVAL,
    };
    let free_fn = match free_fn {
        Some(free_fn) => free_fn,
        None => return -EINVAL,
    };
    let memcpy_fn = match memcpy_fn {
        Some(memcpy_fn) => memcpy_fn,
        None => return -EINVAL,
    };
    let memset_fn = match memset_fn {
        Some(memset_fn) => memset_fn,
        None => return -EINVAL,
    };
    let set_nr_pages_fn = match set_nr_pages_fn {
        Some(set_nr_pages_fn) => set_nr_pages_fn,
        None => return -EINVAL,
    };
    let set_pages_fn = match set_pages_fn {
        Some(set_pages_fn) => set_pages_fn,
        None => return -EINVAL,
    };
    let set_size_fn = match set_size_fn {
        Some(set_size_fn) => set_size_fn,
        None => return -EINVAL,
    };
    let log_fn = match log_fn {
        Some(log_fn) => log_fn,
        None => return -EINVAL,
    };
    if obj.is_null() || lock.is_null() || pgshiftp.is_null() {
        return -EINVAL;
    }

    let nr_pages = hugefileobj_create_nr_pages_result(off, len, pgshift);
    let mut ret = 0;
    lock_fn(lock);
    if hugefileobj_needs_grow_result(current_nr_pages, nr_pages) != 0 {
        let pages = alloc_fn(
            hugefileobj_page_array_bytes_result(nr_pages as SizeT),
            alloc_flags,
        );
        if pages.is_null() {
            ret = -ENOMEM;
        } else {
            if hugefileobj_pointer_present_result(current_nr_pages as CULong) != 0 {
                memcpy_fn(
                    pages,
                    current_pages as *const c_void,
                    hugefileobj_copy_bytes_result(current_nr_pages),
                );
            }

            let zero_start = (pages as *mut *mut c_void)
                .add(hugefileobj_zero_start_index_result(current_nr_pages))
                as *mut c_void;
            memset_fn(
                zero_start,
                0,
                hugefileobj_zero_bytes_result(current_nr_pages, nr_pages as SizeT),
            );

            if hugefileobj_pointer_present_result(current_nr_pages as CULong) != 0 {
                free_fn(current_pages);
            }

            set_nr_pages_fn(obj, nr_pages as SizeT);
            set_pages_fn(obj, pages);
            log_fn(4, obj, off, nr_pages as CLong, pgsize, virt_addr);
        }
    }

    if ret == 0 {
        set_size_fn(obj, len);
        *pgshiftp = pgshift;
    }
    unlock_fn(lock);

    ret
}

#[no_mangle]
pub unsafe extern "C" fn hugefileobj_lookup_body_result(
    handle: CULong,
    list_head: *mut c_void,
    first_fn: HugefileobjFirstFn,
    next_fn: HugefileobjNextFn,
    handle_fn: HugefileobjHandleFn,
    ref_fn: HugefileobjRefFn,
    dec_fn: HugefileobjDecFn,
) -> *mut c_void {
    let (Some(first_fn), Some(next_fn), Some(handle_fn), Some(ref_fn), Some(dec_fn)) =
        (first_fn, next_fn, handle_fn, ref_fn, dec_fn)
    else {
        return core::ptr::null_mut();
    };
    if list_head.is_null() {
        return core::ptr::null_mut();
    }

    let mut obj = first_fn(list_head);
    while !obj.is_null() {
        if handle_fn(obj) == handle {
            if fileobj_lookup_ref_keep_result(ref_fn(obj)) != 0 {
                return obj;
            }
            dec_fn(obj);
        }
        obj = next_fn(list_head, obj);
    }

    core::ptr::null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn hugefileobj_pre_create_body_result(
    lock: *mut c_void,
    handle: CULong,
    maxprot: CInt,
    flags: u32,
    pgshift: CInt,
    path: *const i8,
    obj_size: SizeT,
    path_size: SizeT,
    ops: *mut c_void,
    objp: *mut *mut c_void,
    maxprotp: *mut CInt,
    lock_fn: HugefileobjVoidFn,
    unlock_fn: HugefileobjVoidFn,
    lookup_fn: HugefileobjLookupFn,
    alloc_fn: HugefileobjAllocFn,
    free_fn: HugefileobjVoidFn,
    to_memobj_fn: HugefileobjToMemobjFn,
    set_handle_fn: HugefileobjSetHandleFn,
    set_pgsize_fn: HugefileobjSetPgsizeFn,
    set_pgshift_fn: HugefileobjSetPgshiftFn,
    set_pages_fn: HugefileobjSetPagesFn,
    set_nr_pages_fn: HugefileobjSetNrPagesFn,
    init_lock_fn: HugefileobjVoidFn,
    set_flags_fn: HugefileobjSetFlagsFn,
    set_status_fn: HugefileobjSetStatusFn,
    set_ops_fn: HugefileobjSetOpsFn,
    set_refcnt_fn: HugefileobjSetRefcntFn,
    set_path_fn: HugefileobjSetPathFn,
    copy_path_fn: HugefileobjCopyPathFn,
    list_add_fn: HugefileobjVoidFn,
    log_fn: HugefileobjPreCreateLogFn,
    alloc_error_fn: HugefileobjAllocErrorFn,
) -> CInt {
    let (
        Some(lock_fn),
        Some(unlock_fn),
        Some(lookup_fn),
        Some(alloc_fn),
        Some(free_fn),
        Some(to_memobj_fn),
        Some(set_handle_fn),
        Some(set_pgsize_fn),
        Some(set_pgshift_fn),
        Some(set_pages_fn),
        Some(set_nr_pages_fn),
        Some(init_lock_fn),
        Some(set_flags_fn),
        Some(set_status_fn),
        Some(set_ops_fn),
        Some(set_refcnt_fn),
        Some(set_path_fn),
        Some(copy_path_fn),
        Some(list_add_fn),
        Some(log_fn),
        Some(alloc_error_fn),
    ) = (
        lock_fn,
        unlock_fn,
        lookup_fn,
        alloc_fn,
        free_fn,
        to_memobj_fn,
        set_handle_fn,
        set_pgsize_fn,
        set_pgshift_fn,
        set_pages_fn,
        set_nr_pages_fn,
        init_lock_fn,
        set_flags_fn,
        set_status_fn,
        set_ops_fn,
        set_refcnt_fn,
        set_path_fn,
        copy_path_fn,
        list_add_fn,
        log_fn,
        alloc_error_fn,
    )
    else {
        return -EINVAL;
    };
    if lock.is_null() || objp.is_null() || maxprotp.is_null() || path.is_null() || ops.is_null() {
        return -EINVAL;
    }

    let mut ret = 0;
    lock_fn(lock);

    let mut obj = lookup_fn(handle);
    if !obj.is_null() {
        log_fn(HUGEFILEOBJ_LOG_PRE_CREATE_FOUND, obj);
        write_volatile(maxprotp, maxprot);
        write_volatile(objp, to_memobj_fn(obj));
        unlock_fn(lock);
        return 0;
    }

    obj = alloc_fn(obj_size, IHK_MC_AP_NOWAIT);
    if obj.is_null() {
        alloc_error_fn(HUGEFILEOBJ_PRE_CREATE_ALLOC_OBJ);
        ret = -ENOMEM;
    } else {
        set_handle_fn(obj, handle);
        set_pgsize_fn(obj, hugefileobj_pgsize_result(pgshift));
        set_pgshift_fn(obj, pgshift);
        set_pages_fn(obj, core::ptr::null_mut());
        set_nr_pages_fn(obj, 0);
        init_lock_fn(obj);
        set_flags_fn(obj, flags);
        set_status_fn(obj, hugefileobj_initial_status_result());
        set_ops_fn(obj, ops);
        set_refcnt_fn(obj, hugefileobj_initial_refcnt_result());

        if read_volatile(path.cast::<u8>()) != 0 {
            let path_buf = alloc_fn(path_size, IHK_MC_AP_NOWAIT);
            if path_buf.is_null() {
                alloc_error_fn(HUGEFILEOBJ_PRE_CREATE_ALLOC_PATH);
                free_fn(obj);
                ret = -ENOMEM;
            } else {
                set_path_fn(obj, path_buf);
                copy_path_fn(path_buf, path.cast::<c_void>(), path_size);
            }
        }

        if ret == 0 {
            list_add_fn(obj);
            log_fn(HUGEFILEOBJ_LOG_PRE_CREATE_CREATED, obj);
            write_volatile(maxprotp, maxprot);
            write_volatile(objp, to_memobj_fn(obj));
        }
    }

    unlock_fn(lock);
    ret
}
