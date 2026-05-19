use core::ptr::write;

use crate::abi::{CInt, CLong, CULong, OffT, SizeT};

const ENOENT: CInt = 2;
const EINTR: CInt = 4;
const EIO: CInt = 5;
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
const MF_ZEROOBJ: CInt = 0x20000;
const MF_SHM: CInt = 0x40000;
const MF_HUGETLBFS: CInt = 0x100000;
const MF_PRIVATE: CInt = 0x200000;
const MF_REMAP_FILE_PAGES: CInt = 0x400000;

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

const VR_STACK: CULong = 0x1;
const VR_PRIVATE: CULong = 0x2000;
const VR_PROT_READ: CULong = 0x00010000;
const VR_PROT_WRITE: CULong = 0x00020000;
const VR_PROT_EXEC: CULong = 0x00040000;

#[inline(always)]
fn page_offset(value: CULong) -> CULong {
    value & (PAGE_SIZE - 1)
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
pub extern "C" fn pager_linux_io_retry_result(ret: CLong) -> CInt {
    (ret == -(EINTR as CLong)) as CInt
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
