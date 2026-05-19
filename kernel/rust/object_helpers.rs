use core::ptr::write;

use crate::abi::{CInt, CLong, CULong, OffT, SizeT};

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

const PFN_VALID: CULong = 1 << 63;
const PFN_PRESENT: CULong = 1;
const PFN_PFN: CULong = ((1 << 56) - 1) & !(PAGE_SIZE - 1);

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
const VR_PRIVATE: CULong = 0x2000;
const VR_LOCKED: CULong = 0x4000;
const VR_PROT_READ: CULong = 0x00010000;
const VR_PROT_WRITE: CULong = 0x00020000;
const VR_PROT_EXEC: CULong = 0x00040000;

const SYSFS_HANDLER_UNKNOWN: CInt = 0;
const SYSFS_HANDLER_SHOW: CInt = 1;
const SYSFS_HANDLER_STORE: CInt = 2;
const SYSFS_HANDLER_RELEASE: CInt = 3;
const SCD_MSG_SYSFS_REQ_SHOW: CInt = 0x3a;
const SCD_MSG_SYSFS_REQ_STORE: CInt = 0x3c;
const SCD_MSG_SYSFS_REQ_RELEASE: CInt = 0x3e;
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
