use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of_mut, read_volatile, write_volatile};

use crate::abi::{CInt, CULong, SizeT};

const SHMID_INDEX_WORDS: usize = 512;
const BITS_PER_LONG: CInt = 64;
const SHMID_SEQ_MASK: CInt = (1 << 16) - 1;
const EACCES: CInt = 13;
const ENOMEM: CInt = 12;
const EPERM: CInt = 1;
const SHM_RDONLY: CInt = 0o10000;

type CUInt = u32;
type KeyT = i32;
type UidT = u32;
type GidT = u32;
type TimeT = i64;
type PidT = i32;

#[repr(C)]
struct IhkAtomic {
    counter: CInt,
}

#[repr(C)]
struct MemObj {
    ops: *mut c_void,
    flags: CUInt,
    status: CUInt,
    size: SizeT,
    refcnt: IhkAtomic,
    pages: *mut *mut c_void,
    nr_pages: CInt,
    path: *mut i8,
}

#[repr(C)]
struct IpcPerm {
    key: KeyT,
    uid: UidT,
    gid: GidT,
    cuid: UidT,
    cgid: GidT,
    mode: u16,
    padding: [u8; 2],
    seq: u16,
    padding2: [u8; 22],
}

#[repr(C)]
struct ShmidDs {
    shm_perm: IpcPerm,
    shm_segsz: SizeT,
    shm_atime: TimeT,
    shm_dtime: TimeT,
    shm_ctime: TimeT,
    shm_cpid: PidT,
    shm_lpid: PidT,
    shm_nattch: u64,
    padding: [u8; 12],
    init_pgshift: CInt,
}

#[repr(C)]
struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}

#[repr(C)]
struct IhkSpinlock {
    head_tail: CUInt,
}

#[repr(C)]
pub struct ShmObj {
    memobj: MemObj,
    index: CInt,
    pgshift: CInt,
    real_segsz: SizeT,
    user: *mut c_void,
    ds: ShmidDs,
    page_list: ListHead,
    page_list_lock: IhkSpinlock,
    chain: ListHead,
}

const _: () = {
    assert!(size_of::<IhkAtomic>() == 4);
    assert!(align_of::<IhkAtomic>() == 4);
    assert!(offset_of!(IhkAtomic, counter) == 0);
    assert!(size_of::<MemObj>() == 56);
    assert!(align_of::<MemObj>() == 8);
    assert!(offset_of!(MemObj, flags) == 8);
    assert!(offset_of!(MemObj, refcnt) == 24);
    assert!(offset_of!(MemObj, pages) == 32);
    assert!(offset_of!(MemObj, path) == 48);
    assert!(size_of::<IpcPerm>() == 48);
    assert!(align_of::<IpcPerm>() == 4);
    assert!(offset_of!(IpcPerm, seq) == 24);
    assert!(size_of::<ShmidDs>() == 112);
    assert!(align_of::<ShmidDs>() == 8);
    assert!(offset_of!(ShmidDs, init_pgshift) == 108);
    assert!(size_of::<ListHead>() == 16);
    assert!(align_of::<ListHead>() == 8);
    assert!(size_of::<IhkSpinlock>() == 4);
    assert!(align_of::<IhkSpinlock>() == 4);
    assert!(size_of::<ShmObj>() == 232);
    assert!(align_of::<ShmObj>() == 8);
    assert!(offset_of!(ShmObj, index) == 56);
    assert!(offset_of!(ShmObj, ds) == 80);
    assert!(offset_of!(ShmObj, chain) == 216);
};

unsafe extern "C" {
    static mut shmid_index: [CULong; SHMID_INDEX_WORDS];
}

#[inline(always)]
unsafe fn shmid_index_words() -> *mut CULong {
    addr_of_mut!(shmid_index).cast::<CULong>()
}

#[no_mangle]
pub unsafe extern "C" fn get_shmid_max_index() -> CInt {
    let words = shmid_index_words();
    let mut i = SHMID_INDEX_WORDS;

    while i != 0 {
        i -= 1;
        let value = read_volatile(words.add(i));
        if value != 0 {
            return (i as CInt * BITS_PER_LONG)
                + (BITS_PER_LONG - 1 - value.leading_zeros() as CInt);
        }
    }

    -1
}

#[no_mangle]
pub unsafe extern "C" fn get_shmid_index() -> CInt {
    let words = shmid_index_words();
    let mut index: CInt = 0;

    loop {
        let word_index = index / BITS_PER_LONG;
        let bit = index % BITS_PER_LONG;
        let slot = words.add(word_index as usize);
        let mask = 1u64 << bit as usize;
        let value = read_volatile(slot);

        if (value & mask) == 0 {
            write_volatile(slot, value | mask);
            return index;
        }

        index += 1;
    }
}

#[no_mangle]
pub extern "C" fn shmid_to_index(shmid: CInt) -> CInt {
    shmid >> 16
}

#[no_mangle]
pub extern "C" fn shmid_to_seq(shmid: CInt) -> CInt {
    shmid & SHMID_SEQ_MASK
}

#[no_mangle]
pub unsafe extern "C" fn make_shmid(obj: *const ShmObj) -> CInt {
    (*obj).index.wrapping_shl(16) | CInt::from((*obj).ds.shm_perm.seq)
}

#[inline(always)]
fn shm_owner(euid: UidT, uid: UidT, cuid: UidT) -> bool {
    euid == uid || euid == cuid
}

#[inline(always)]
fn shm_group(egid: GidT, gid: GidT, cgid: GidT) -> bool {
    egid == gid || egid == cgid
}

#[no_mangle]
pub extern "C" fn shmget_existing_access_result(
    euid: UidT,
    egid: GidT,
    shmflg: CInt,
    uid: UidT,
    cuid: UidT,
    gid: GidT,
    cgid: GidT,
    mode: u16,
) -> CInt {
    if euid == 0 {
        return 0;
    }

    let mut req = (shmflg | (shmflg << 3) | (shmflg << 6)) & 0o700;
    if shm_owner(euid, uid, cuid) {
        /* Owner bits are already selected. */
    } else if shm_group(egid, gid, cgid) {
        req >>= 3;
    } else {
        req >>= 6;
    }

    if (req & !(mode as CInt)) != 0 {
        -EACCES
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn shmat_access_result(
    euid: UidT,
    egid: GidT,
    shmflg: CInt,
    uid: UidT,
    cuid: UidT,
    gid: GidT,
    cgid: GidT,
    mode: u16,
) -> CInt {
    let mut req = 0o4;

    if (shmflg & SHM_RDONLY) == 0 {
        req |= 0o2;
    }

    if euid == 0 {
        req = 0;
    } else if shm_owner(euid, uid, cuid) {
        req <<= 6;
    } else if shm_group(egid, gid, cgid) {
        req <<= 3;
    }

    if (req & !(mode as CInt)) != 0 {
        -EACCES
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn shmctl_ipc_stat_access_result(
    euid: UidT,
    egid: GidT,
    uid: UidT,
    cuid: UidT,
    gid: GidT,
    cgid: GidT,
    mode: u16,
) -> CInt {
    let req = if euid == 0 {
        0
    } else if shm_owner(euid, uid, cuid) {
        0o400
    } else if shm_group(egid, gid, cgid) {
        0o040
    } else {
        0o004
    };

    if (req & !(mode as CInt)) != 0 {
        -EACCES
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn shm_owner_result(euid: UidT, uid: UidT, cuid: UidT) -> CInt {
    if shm_owner(euid, uid, cuid) {
        0
    } else {
        -EPERM
    }
}

#[no_mangle]
pub extern "C" fn shm_owner_or_cap_result(
    has_cap: CInt,
    euid: UidT,
    uid: UidT,
    cuid: UidT,
) -> CInt {
    if has_cap != 0 || shm_owner(euid, uid, cuid) {
        0
    } else {
        -EPERM
    }
}

#[no_mangle]
pub extern "C" fn shmlock_rlimit_result(
    has_cap: CInt,
    rlim_cur: CULong,
    user_locked: CULong,
    size: CULong,
) -> CInt {
    if has_cap == 0 && rlim_cur == 0 {
        return -EPERM;
    }

    if has_cap == 0
        && rlim_cur != CULong::MAX
        && (rlim_cur < user_locked || rlim_cur - user_locked < size)
    {
        -ENOMEM
    } else {
        0
    }
}
