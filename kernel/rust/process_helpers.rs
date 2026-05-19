use core::ffi::c_void;

use crate::abi::{CInt, CULong};

const EINVAL: CInt = 22;
const EACCES: CInt = 13;
const EFAULT: CInt = 14;
const ENOMEM: CInt = 12;
const EPERM: CInt = 1;

const PAGE_SIZE: CULong = 4096;

const VERIFY_READ: CInt = 0;
const VERIFY_WRITE: CInt = 1;

const VR_IO_NOCACHE: CULong = 0x100;
const VR_REMOTE: CULong = 0x200;
const VR_WRITE_COMBINED: CULong = 0x400;
const VR_PRIVATE: CULong = 0x2000;
const VR_PROT_NONE: CULong = 0x0000_0000;
const VR_PROT_READ: CULong = 0x0001_0000;
const VR_PROT_WRITE: CULong = 0x0002_0000;
const VR_PROT_EXEC: CULong = 0x0004_0000;
const VR_PROT_MASK: CULong = 0x0007_0000;

const MF_HUGETLBFS: u32 = 0x100000;

const PTATTR_ACTIVE: CULong = 0x01;
const PTATTR_WRITABLE: CULong = 0x02;
const PTATTR_USER: CULong = 0x04;
const PTATTR_NO_EXECUTE: CULong = 0x8000_0000_0000_0000;
const PTATTR_UNCACHABLE: CULong = 0x10000;
const PTATTR_FOR_USER: CULong = 0x20000;
const PTATTR_WRITE_COMBINED: CULong = 0x40000;
const IHK_PTA_REMOTE: CULong = 0;

#[no_mangle]
pub extern "C" fn common_vrflag_to_ptattr(
    flag: CULong,
    _fault: CULong,
    _ptep: *mut c_void,
) -> CULong {
    let mut attr = PTATTR_USER | PTATTR_FOR_USER;

    if (flag & VR_REMOTE) != 0 {
        attr |= IHK_PTA_REMOTE;
    } else if (flag & VR_IO_NOCACHE) != 0 {
        attr |= PTATTR_UNCACHABLE;
    }

    if (flag & VR_PROT_MASK) != VR_PROT_NONE {
        attr |= PTATTR_ACTIVE;
    }

    if (flag & VR_PROT_WRITE) != 0 {
        attr |= PTATTR_WRITABLE;
    }

    if (flag & VR_PROT_EXEC) == 0 {
        attr |= PTATTR_NO_EXECUTE;
    }

    if (flag & VR_WRITE_COMBINED) != 0 {
        attr |= PTATTR_WRITE_COMBINED;
    }

    attr
}

#[no_mangle]
pub extern "C" fn process_split_pgshift_result(pgshift: CInt, addr: CULong) -> CInt {
    if pgshift > 0
        && (pgshift as usize) < CULong::BITS as usize
        && (addr & ((1u64 << pgshift) - 1)) != 0
    {
        0
    } else {
        pgshift
    }
}

#[no_mangle]
pub extern "C" fn process_add_range_bounds_result(
    user_start: CULong,
    user_end: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    if start < user_start || user_end < end {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_extend_up_result(
    current_end: CULong,
    user_end: CULong,
    has_next: CInt,
    next_start: CULong,
    newend: CULong,
) -> CInt {
    if newend <= current_end {
        -EINVAL
    } else if user_end < newend {
        -EPERM
    } else if has_next != 0 && next_start < newend {
        -ENOMEM
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_change_prot_newflag_result(oldflag: CULong, protflag: CULong) -> CULong {
    (oldflag & !VR_PROT_MASK) | (protflag & VR_PROT_MASK)
}

#[no_mangle]
pub unsafe extern "C" fn process_attr_delta_result(
    oldattr: CULong,
    newattr: CULong,
    clrattrp: *mut CULong,
    setattrp: *mut CULong,
) {
    *clrattrp = oldattr & !newattr;
    *setattrp = newattr & !oldattr;
}

#[no_mangle]
pub extern "C" fn process_private_file_setattr_result(
    has_memobj: CInt,
    range_flags: CULong,
    memobj_flags: u32,
    setattr: CULong,
) -> CULong {
    if has_memobj != 0 && (range_flags & VR_PRIVATE) != 0 && (memobj_flags & MF_HUGETLBFS) == 0 {
        setattr & !PTATTR_WRITABLE
    } else {
        setattr
    }
}

#[no_mangle]
pub extern "C" fn process_remove_region_alignment_result(start: CULong, end: CULong) -> CInt {
    if (start & (PAGE_SIZE - 1)) != 0 || (end & (PAGE_SIZE - 1)) != 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_access_initial_result(
    has_range: CInt,
    range_start: CULong,
    addr: CULong,
) -> CInt {
    if has_range == 0 || range_start > addr {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_access_adjacent_result(
    range_end: CULong,
    has_next: CInt,
    next_start: CULong,
) -> CInt {
    if has_next == 0 || range_end != next_start {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_access_permission_result(verify_type: CInt, flags: CULong) -> CInt {
    if (verify_type == VERIFY_WRITE && (flags & VR_PROT_WRITE) == 0)
        || (verify_type == VERIFY_READ && (flags & VR_PROT_READ) == 0)
    {
        -EACCES
    } else {
        0
    }
}
