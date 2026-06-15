use core::ffi::c_void;
use core::mem::{offset_of, size_of, MaybeUninit};
use core::ptr::{write, write_bytes};

use crate::abi::{
    AddressSpace, CInt, CLong, CULong, CpuLocalVar, Mckfd, OffT, Process, ProcessVm, SizeT,
    Thread, VmRange, VmRegions, XpmemAccessPermit, XpmemAttachment, XpmemHashlist,
    XpmemPartitionPrefix, XpmemPerm, XpmemSegment, XpmemThreadGroupPrefix, VM_RANGE_CACHE_SIZE,
};
use crate::atomic_helpers::{
    ihk_atomic_dec_return, ihk_atomic_inc_return, ihk_atomic_read, ihk_atomic_set, ihk_atomic_sub,
    IhkAtomic as RustIhkAtomic,
};
use crate::lock_helpers::{IhkRwSpinlock, McsRwlockLock, McsRwlockNodeIrqsave};

const EINVAL: CInt = 22;
const EACCES: CInt = 13;
const ENOENT: CInt = 2;
const EBUSY: CInt = 16;
const EFAULT: CInt = 14;
const ENOMEM: CInt = 12;

const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const PAGE_SIZE: CULong = 1 << 12;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);

const __NR_OPEN: CInt = 2;
const __NR_OPENAT: CInt = 257;

const PROT_READ: CULong = 0x01;
const PROT_WRITE: CULong = 0x02;
const MAP_SHARED: CULong = 0x01;
const MAP_FIXED: CULong = 0x10;
const MAP_ANONYMOUS: CULong = 0x20;
const VR_XPMEM: CULong = 0x4000_0000;

const XPMEM_CMD_VERSION: CULong = 0x0000_7800;
const XPMEM_CMD_MAKE: CULong = 0x0000_7801;
const XPMEM_CMD_REMOVE: CULong = 0x0000_7802;
const XPMEM_CMD_GET: CULong = 0x0000_7803;
const XPMEM_CMD_RELEASE: CULong = 0x0000_7804;
const XPMEM_CMD_ATTACH: CULong = 0x0000_7805;
const XPMEM_CMD_DETACH: CULong = 0x0000_7806;
const XPMEM_CURRENT_VERSION: CInt = 0x0002_6003;

const XPMEM_TG_HASHTABLE_SIZE: CInt = 8;
const XPMEM_AP_HASHTABLE_SIZE: CInt = 8;
const XPMEM_MAX_UNIQ_ID: CInt = CInt::MAX >> 1;

const XPMEM_RDONLY: CInt = 0x1;
const XPMEM_RDWR: CInt = 0x2;
const XPMEM_PERMIT_MODE: CInt = 0x1;
const XPMEM_PERM_IRUSR: CInt = 0o400;
const XPMEM_PERM_IWUSR: CInt = 0o200;
const XPMEM_FLAG_DESTROYING: CInt = 0x00040;
const XPMEM_FLAG_DESTROYED: CInt = 0x00080;
const XPMEM_FLAG_VALIDPTES: CInt = 0x00200;
const XPMEM_ERRNO_NOPROC: CInt = 2004;
const XPMEM_DETACH_LOOKUP_CONTINUE: CInt = 1;
const XPMEM_LOOKUP_SKIP: CInt = 0;
const XPMEM_LOOKUP_TAKE: CInt = 1;
const XPMEM_LOOKUP_STOP: CInt = 2;
const VR_PROT_WRITE: CULong = 0x00020000;
const PF_WRITE: CULong = 1 << 1;
const PF_USER: CULong = 1 << 2;
const PF_POPULATE: CULong = 1 << 30;
const XPMEM_OPEN_LOG_CALL: CInt = 1;
const XPMEM_OPEN_LOG_SYSCALL_ERROR: CInt = 2;
const XPMEM_OPEN_LOG_OPEN_ERROR: CInt = 3;
const XPMEM_OPEN_LOG_ALLOC: CInt = 4;
const XPMEM_OPEN_LOG_N_OPENED: CInt = 5;
const XPMEM_OPEN_LOG_RETURN: CInt = 6;
const XPMEM_CLOSE_LOG_CALL: CInt = 1;
const XPMEM_CLOSE_LOG_N_OPENED: CInt = 2;
const XPMEM_CLOSE_LOG_RETURN: CInt = 3;
const XPMEM_FLUSH_LOG_TG_VM: CInt = 1;
const XPMEM_REMOVE_SEG_LOG_CALL: CInt = 1;
const XPMEM_REMOVE_SEG_LOG_RETURN: CInt = 2;
const XPMEM_REMOVE_SEGS_LOG_CALL: CInt = 1;
const XPMEM_REMOVE_SEGS_LOG_RETURN: CInt = 2;
const XPMEM_RELEASE_AP_LOG_CALL: CInt = 1;
const XPMEM_RELEASE_AP_LOG_RETURN: CInt = 2;
const XPMEM_DESTROYABLE_LOG_CALL: CInt = 1;
const XPMEM_DESTROYABLE_LOG_RETURN: CInt = 2;
const XPMEM_REF_KIND_TG: CInt = 1;
const XPMEM_REF_KIND_SEG: CInt = 2;
const XPMEM_REF_KIND_AP: CInt = 3;
const XPMEM_REF_KIND_ATT: CInt = 4;
const XPMEM_TG_LOOKUP_LOG_CALL: CInt = 1;
const XPMEM_TG_LOOKUP_LOG_PART: CInt = 2;
const XPMEM_TG_LOOKUP_LOG_RETURN: CInt = 3;

unsafe extern "C" {
    fn __kmalloc(size: CInt, flags: CInt) -> *mut c_void;
    fn __kfree(ptr: *mut c_void);
    fn ihk_mc_get_processor_id() -> CInt;
    fn get_cpu_local_var(id: CInt) -> *mut CpuLocalVar;
    fn syscall_generic_forwarding(syscall_num: CInt, ctx: *mut c_void) -> CLong;
    fn ihk_mc_syscall_arg1(ctx: *const c_void) -> CULong;
    fn ihk_mc_syscall_arg2(ctx: *const c_void) -> CULong;
    fn copy_from_user(dst: *mut c_void, src: *const c_void, size: SizeT) -> CInt;
    fn copy_to_user(dst: *mut c_void, src: *const c_void, size: SizeT) -> CInt;
    fn do_mmap(
        addr: CULong,
        len: SizeT,
        prot: CInt,
        flags: CInt,
        fd: CInt,
        offset: OffT,
        vm_flags: CInt,
        private_data: *mut c_void,
    ) -> CLong;
    fn next_process_memory_range(vm: *mut ProcessVm, range: *mut VmRange) -> *mut VmRange;
    fn split_process_memory_range(
        vm: *mut ProcessVm,
        range: *mut VmRange,
        addr: CULong,
        new_range: *mut *mut VmRange,
    ) -> CInt;
    fn ihk_mc_pt_clear_range(
        page_table: *mut c_void,
        vm: *mut ProcessVm,
        start: *mut c_void,
        end: *mut c_void,
    ) -> CInt;
    fn rb_erase(node: *mut c_void, root: *mut c_void);
    fn memobj_unref(ptr: *mut c_void) -> CInt;
    fn begin_free_pages_pending();
    fn finish_free_pages_pending();
    static xpmem_page_in_remote_on_attach: CInt;
    fn lookup_process_memory_range(vm: *mut ProcessVm, start: CULong, end: CULong) -> *mut VmRange;
    fn page_fault_process_vm(vm: *mut ProcessVm, addr: *mut c_void, reason: CULong) -> CInt;
    fn page_fault_process_memory_range(
        vm: *mut ProcessVm,
        range: *mut VmRange,
        addr: *mut c_void,
        reason: CULong,
    ) -> CInt;
    fn ihk_mc_pt_lookup_pte(
        page_table: *mut c_void,
        vaddr: *mut c_void,
        pgshift: CInt,
        base: *mut *mut c_void,
        pgsize: *mut SizeT,
        p2align: *mut CInt,
    ) -> *mut c_void;
    fn ihk_mc_pt_set_pte(
        page_table: *mut c_void,
        pte: *mut c_void,
        pgsize: SizeT,
        phys: CULong,
        attr: CInt,
    ) -> CInt;
    fn ihk_mc_pt_set_range(
        page_table: *mut c_void,
        vm: *mut ProcessVm,
        start: *mut c_void,
        end: *mut c_void,
        phys: CULong,
        attr: CInt,
        pgshift: CInt,
        vmr: *mut VmRange,
        replace: CInt,
    ) -> CInt;
    fn arch_get_smaller_page_size(
        args: *mut c_void,
        origsize: SizeT,
        sizep: *mut SizeT,
        p2alignp: *mut CInt,
    ) -> CInt;
    fn arch_adjust_allocate_page_size(
        pt: *mut c_void,
        fault_addr: CULong,
        pte: *mut c_void,
        pgaddrp: *mut *mut c_void,
        pgsizep: *mut SizeT,
    );
    fn arch_vrflag_to_ptattr(flag: CULong, fault: CULong, ptep: *mut c_void) -> CInt;
    fn flush_tlb_single(addr: CULong);
}

type XpmemInitFn = unsafe extern "C" fn() -> CInt;
type XpmemForwardFn = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;
type XpmemOpenFn = unsafe extern "C" fn() -> CInt;
type XpmemAllocFn = unsafe extern "C" fn(SizeT) -> *mut c_void;
type XpmemLockFn = unsafe extern "C" fn(*mut c_void) -> CLong;
type XpmemUnlockFn = unsafe extern "C" fn(*mut c_void, CLong);
type XpmemAtomicIncFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type XpmemAtomicSetFn = unsafe extern "C" fn(*mut c_void, CInt);
type XpmemAtomicReadFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type XpmemAtomicDecFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type XpmemBugOnFn = unsafe extern "C" fn(CInt);
type XpmemVoidFn = unsafe extern "C" fn();
type XpmemMckfdVoidFn = unsafe extern "C" fn(*mut c_void);
type XpmemOpenLogFn = unsafe extern "C" fn(CInt, CInt, *const u8, CInt, CLong, *mut c_void);
type XpmemCloseLogFn = unsafe extern "C" fn(CInt, *mut c_void, CInt);
type XpmemTgRefFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type XpmemRwlockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type XpmemListFn = unsafe extern "C" fn(*mut c_void);
type XpmemSpinFn = unsafe extern "C" fn(*mut c_void);
type XpmemTgVoidFn = unsafe extern "C" fn(*mut c_void);
type XpmemFlushLogFn = unsafe extern "C" fn(CInt, *mut c_void, CLong);
type XpmemObjectVoidFn = unsafe extern "C" fn(*mut c_void);
type XpmemRemoveSegLogFn = unsafe extern "C" fn(CInt, *mut c_void, *mut c_void, CLong);
type XpmemRemoveSegFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type XpmemRemoveSegsLogFn = unsafe extern "C" fn(CInt, *mut c_void, *mut c_void, CLong);
type XpmemDetachAttFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type XpmemReleaseApLogFn = unsafe extern "C" fn(CInt, *mut c_void, *mut c_void, CLong);
type XpmemIdRefFn = unsafe extern "C" fn(CLong) -> *mut c_void;
type XpmemRefByIdFn = unsafe extern "C" fn(*mut c_void, CLong) -> *mut c_void;
type XpmemRwspinNoirqFn = unsafe extern "C" fn(*mut c_void);
type XpmemRwspinLockFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type XpmemRwspinUnlockFn = unsafe extern "C" fn(*mut c_void, CULong);
type XpmemLookupRangeFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> *mut c_void;
type XpmemNextRangeFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> *mut c_void;
type XpmemSplitRangeFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, *mut *mut c_void) -> CInt;
type XpmemRangeActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type XpmemRemoveProcessRangeLogFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, CInt, CInt);
type XpmemPtClearRangeFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong) -> CInt;
type XpmemRangeEraseFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type XpmemFreeProcessRangeLogFn =
    unsafe extern "C" fn(CInt, *mut c_void, *mut c_void, CULong, CULong, CInt);
type XpmemFaultRangeWithPageInFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong, CInt) -> CInt;
type XpmemUpdatePageTableLogFn = unsafe extern "C" fn(CInt, *mut c_void, *mut c_void, CULong, CInt);
type XpmemValidateAccessCallbackFn =
    unsafe extern "C" fn(*mut c_void, OffT, SizeT, CInt, *mut CULong) -> CInt;
type XpmemMmapFn =
    unsafe extern "C" fn(CULong, SizeT, CULong, CULong, CInt, OffT, CULong, *mut c_void) -> CULong;
type XpmemUnpinPagesFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, SizeT);
type XpmemMunmapFn = unsafe extern "C" fn(*mut c_void, CULong, SizeT) -> CInt;
type XpmemRemoveRangeFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, *mut CInt) -> CInt;
type XpmemClearRangeFn = unsafe extern "C" fn(*mut c_void, CULong, CULong);
type XpmemPageFaultVmFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CInt;
type XpmemPageFaultRangeFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong) -> CInt;
type XpmemPinPageFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, CULong, CInt) -> CInt;
type XpmemEnsureValidPageFn = unsafe extern "C" fn(*mut c_void, CULong, CInt) -> CInt;
type XpmemPtLookupPteFn = unsafe extern "C" fn(
    *mut c_void,
    CULong,
    CInt,
    *mut *mut c_void,
    *mut SizeT,
    *mut CInt,
) -> *mut c_void;
type XpmemVaddrToPteFn = unsafe extern "C" fn(*mut c_void, CULong, *mut SizeT) -> *mut c_void;
type XpmemPtePresentFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type XpmemAtomicSubFn = unsafe extern "C" fn(CInt, *mut c_void);
type XpmemPtePhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type XpmemGetSmallerPageSizeFn = unsafe extern "C" fn(SizeT, *mut SizeT, *mut CInt) -> CInt;
type XpmemAdjustPageSizeFn =
    unsafe extern "C" fn(*mut c_void, CULong, *mut c_void, *mut *mut c_void, *mut SizeT);
type XpmemVrflagToPtattrFn = unsafe extern "C" fn(CULong, CULong) -> CULong;
type XpmemPgsizeContiguousFn = unsafe extern "C" fn(SizeT) -> CInt;
type XpmemPtSetPteFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, SizeT, CULong, CULong) -> CInt;
type XpmemPtSetRangeFn = unsafe extern "C" fn(
    *mut c_void,
    *mut c_void,
    CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    *mut c_void,
    CInt,
) -> CInt;
type XpmemFlushTlbSingleFn = unsafe extern "C" fn(CULong);
type XpmemFaultLogFn = unsafe extern "C" fn(CInt, CULong, CULong, CULong, SizeT, CInt);
type XpmemObjectIdFn = unsafe extern "C" fn(*mut c_void) -> CLong;
type XpmemListAddTailFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type XpmemCheckPermitFn = unsafe extern "C" fn(CInt, *mut c_void) -> CInt;
type XpmemCopyFromUserFn = unsafe extern "C" fn(*mut c_void, CULong, SizeT) -> CInt;
type XpmemCopyToUserFn = unsafe extern "C" fn(CULong, *const c_void, SizeT) -> CInt;
type XpmemMakeFn = unsafe extern "C" fn(CULong, SizeT, CInt, *mut c_void, *mut CLong) -> CInt;
type XpmemRemoveFn = unsafe extern "C" fn(CLong) -> CInt;
type XpmemGetFn = unsafe extern "C" fn(CLong, CInt, CInt, *mut c_void, *mut CLong) -> CInt;
type XpmemReleaseFn = unsafe extern "C" fn(CLong) -> CInt;
type XpmemAttachFn =
    unsafe extern "C" fn(*mut c_void, CLong, OffT, SizeT, CULong, CInt, CInt, *mut CULong) -> CInt;
type XpmemDetachFn = unsafe extern "C" fn(CULong) -> CInt;
type XpmemDestroyableLogFn = unsafe extern "C" fn(CInt);
type XpmemRefcntPtrFn = unsafe extern "C" fn(*mut c_void, CInt) -> *mut c_void;
type XpmemRefcntLogFn = unsafe extern "C" fn(CInt, CInt);
type XpmemTgLookupLogFn = unsafe extern "C" fn(CInt, CInt, CInt, *mut c_void, *mut c_void);

#[repr(C)]
struct XpmemCmdMake {
    vaddr: CULong,
    size: SizeT,
    permit_type: CInt,
    _padding: CInt,
    permit_value: CULong,
    segid: CLong,
}

#[repr(C)]
struct XpmemCmdRemove {
    segid: CLong,
}

#[repr(C)]
struct XpmemCmdGet {
    segid: CLong,
    flags: CInt,
    permit_type: CInt,
    permit_value: CULong,
    apid: CLong,
}

#[repr(C)]
struct XpmemCmdRelease {
    apid: CLong,
}

#[repr(C)]
struct XpmemCmdAttach {
    apid: CLong,
    offset: OffT,
    size: SizeT,
    vaddr: CULong,
    fd: CInt,
    flags: CInt,
}

#[repr(C)]
struct XpmemCmdDetach {
    vaddr: CULong,
}

#[no_mangle]
pub static mut xpmem_my_part: *mut c_void = core::ptr::null_mut();

#[no_mangle]
pub static xpmem_vm_range_private_data_offset: SizeT = offset_of!(VmRange, private_data);

#[no_mangle]
pub static xpmem_partition_offsets: XpmemPartitionOffsets = XpmemPartitionOffsets {
    part_size: size_of::<XpmemPartitionPrefix>()
        + size_of::<XpmemHashlist>() * XPMEM_TG_HASHTABLE_SIZE as usize,
    part_n_opened_offset: offset_of!(XpmemPartitionPrefix, n_opened),
    part_tg_hashtable_offset: size_of::<XpmemPartitionPrefix>(),
    hashlist_stride: size_of::<XpmemHashlist>(),
    hashlist_lock_offset: offset_of!(XpmemHashlist, lock),
    hashlist_list_offset: offset_of!(XpmemHashlist, list),
};

#[no_mangle]
pub static xpmem_tg_lookup_offsets: XpmemTgLookupOffsets = XpmemTgLookupOffsets {
    part_tg_hashtable_offset: size_of::<XpmemPartitionPrefix>(),
    hashlist_stride: size_of::<XpmemHashlist>(),
    hashlist_list_offset: offset_of!(XpmemHashlist, list),
    tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
    tg_flags_offset: offset_of!(XpmemThreadGroupPrefix, flags),
    tg_hashlist_offset: offset_of!(XpmemThreadGroupPrefix, tg_hashlist),
};

static XPMEM_OPEN_OFFSETS: XpmemOpenOffsets = XpmemOpenOffsets {
    proc_mckfd_lock_offset: offset_of!(Process, mckfd_lock),
    proc_mckfd_offset: offset_of!(Process, mckfd),
    part_n_opened_offset: offset_of!(XpmemPartitionPrefix, n_opened),
    mckfd_size: size_of::<Mckfd>(),
    mckfd_next_offset: offset_of!(Mckfd, next),
    mckfd_fd_offset: offset_of!(Mckfd, fd),
    mckfd_sig_no_offset: offset_of!(Mckfd, padding),
    mckfd_data_offset: offset_of!(Mckfd, data),
    mckfd_ioctl_cb_offset: offset_of!(Mckfd, ioctl_cb),
    mckfd_close_cb_offset: offset_of!(Mckfd, close_cb),
    mckfd_dup_cb_offset: offset_of!(Mckfd, dup_cb),
};

static XPMEM_CLOSE_OFFSETS: XpmemCloseOffsets = XpmemCloseOffsets {
    part_n_opened_offset: offset_of!(XpmemPartitionPrefix, n_opened),
    mckfd_fd_offset: offset_of!(Mckfd, fd),
    mckfd_data_offset: offset_of!(Mckfd, data),
};

static XPMEM_OPEN_TG_OFFSETS: XpmemOpenTgOffsets = XpmemOpenTgOffsets {
    proc_pid_offset: offset_of!(Process, pid),
    proc_ruid_offset: offset_of!(Process, ruid),
    proc_rgid_offset: offset_of!(Process, rgid),
    tg_size: size_of::<XpmemThreadGroupPrefix>()
        + size_of::<XpmemHashlist>() * XPMEM_AP_HASHTABLE_SIZE as usize,
    tg_lock_offset: offset_of!(XpmemThreadGroupPrefix, lock),
    tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
    tg_uid_offset: offset_of!(XpmemThreadGroupPrefix, uid),
    tg_gid_offset: offset_of!(XpmemThreadGroupPrefix, gid),
    tg_uniq_segid_offset: offset_of!(XpmemThreadGroupPrefix, uniq_segid),
    tg_uniq_apid_offset: offset_of!(XpmemThreadGroupPrefix, uniq_apid),
    tg_seg_list_lock_offset: offset_of!(XpmemThreadGroupPrefix, seg_list_lock),
    tg_seg_list_offset: offset_of!(XpmemThreadGroupPrefix, seg_list),
    tg_n_pinned_offset: offset_of!(XpmemThreadGroupPrefix, n_pinned),
    tg_tg_hashlist_offset: offset_of!(XpmemThreadGroupPrefix, tg_hashlist),
    tg_group_leader_offset: offset_of!(XpmemThreadGroupPrefix, group_leader),
    tg_vm_offset: offset_of!(XpmemThreadGroupPrefix, vm),
    tg_ap_hashtable_offset: size_of::<XpmemThreadGroupPrefix>(),
    part_tg_hashtable_offset: size_of::<XpmemPartitionPrefix>(),
    hashlist_stride: size_of::<XpmemHashlist>(),
    hashlist_lock_offset: offset_of!(XpmemHashlist, lock),
    hashlist_list_offset: offset_of!(XpmemHashlist, list),
};

static XPMEM_FLUSH_OFFSETS: XpmemFlushOffsets = XpmemFlushOffsets {
    part_tg_hashtable_offset: size_of::<XpmemPartitionPrefix>(),
    hashlist_stride: size_of::<XpmemHashlist>(),
    hashlist_lock_offset: offset_of!(XpmemHashlist, lock),
    hashlist_list_offset: offset_of!(XpmemHashlist, list),
    mckfd_data_offset: offset_of!(Mckfd, data),
    proc_pid_offset: offset_of!(Process, pid),
    tg_lock_offset: offset_of!(XpmemThreadGroupPrefix, lock),
    tg_flags_offset: offset_of!(XpmemThreadGroupPrefix, flags),
    tg_hashlist_offset: offset_of!(XpmemThreadGroupPrefix, tg_hashlist),
    tg_vm_offset: offset_of!(XpmemThreadGroupPrefix, vm),
};

static XPMEM_REMOVE_SEG_OFFSETS: XpmemRemoveSegOffsets = XpmemRemoveSegOffsets {
    tg_seg_list_lock_offset: offset_of!(XpmemThreadGroupPrefix, seg_list_lock),
    seg_lock_offset: offset_of!(XpmemSegment, lock),
    seg_flags_offset: offset_of!(XpmemSegment, flags),
    seg_list_offset: offset_of!(XpmemSegment, seg_list),
};

static XPMEM_REMOVE_SEGS_OFFSETS: XpmemRemoveSegsOffsets = XpmemRemoveSegsOffsets {
    tg_seg_list_lock_offset: offset_of!(XpmemThreadGroupPrefix, seg_list_lock),
    tg_seg_list_offset: offset_of!(XpmemThreadGroupPrefix, seg_list),
    seg_list_offset: offset_of!(XpmemSegment, seg_list),
};

static XPMEM_RELEASE_AP_OFFSETS: XpmemReleaseApOffsets = XpmemReleaseApOffsets {
    tg_ap_hashtable_offset: size_of::<XpmemThreadGroupPrefix>(),
    hashlist_stride: size_of::<XpmemHashlist>(),
    hashlist_lock_offset: offset_of!(XpmemHashlist, lock),
    ap_lock_offset: offset_of!(XpmemAccessPermit, lock),
    ap_apid_offset: offset_of!(XpmemAccessPermit, apid),
    ap_flags_offset: offset_of!(XpmemAccessPermit, flags),
    ap_seg_offset: offset_of!(XpmemAccessPermit, seg),
    ap_att_list_offset: offset_of!(XpmemAccessPermit, att_list),
    ap_ap_list_offset: offset_of!(XpmemAccessPermit, ap_list),
    ap_hashlist_offset: offset_of!(XpmemAccessPermit, ap_hashlist),
    att_att_list_offset: offset_of!(XpmemAttachment, att_list),
    seg_lock_offset: offset_of!(XpmemSegment, lock),
    seg_tg_offset: offset_of!(XpmemSegment, tg),
};

static XPMEM_RELEASE_APS_OFFSETS: XpmemReleaseApsOffsets = XpmemReleaseApsOffsets {
    tg_ap_hashtable_offset: size_of::<XpmemThreadGroupPrefix>(),
    hashlist_stride: size_of::<XpmemHashlist>(),
    hashlist_lock_offset: offset_of!(XpmemHashlist, lock),
    hashlist_list_offset: offset_of!(XpmemHashlist, list),
    ap_hashlist_offset: offset_of!(XpmemAccessPermit, ap_hashlist),
};

static XPMEM_SEG_LOOKUP_OFFSETS: XpmemSegLookupOffsets = XpmemSegLookupOffsets {
    tg_seg_list_lock_offset: offset_of!(XpmemThreadGroupPrefix, seg_list_lock),
    tg_seg_list_offset: offset_of!(XpmemThreadGroupPrefix, seg_list),
    seg_segid_offset: offset_of!(XpmemSegment, segid),
    seg_flags_offset: offset_of!(XpmemSegment, flags),
    seg_list_offset: offset_of!(XpmemSegment, seg_list),
};

static XPMEM_AP_LOOKUP_OFFSETS: XpmemApLookupOffsets = XpmemApLookupOffsets {
    tg_ap_hashtable_offset: size_of::<XpmemThreadGroupPrefix>(),
    hashlist_stride: size_of::<XpmemHashlist>(),
    hashlist_lock_offset: offset_of!(XpmemHashlist, lock),
    hashlist_list_offset: offset_of!(XpmemHashlist, list),
    ap_apid_offset: offset_of!(XpmemAccessPermit, apid),
    ap_flags_offset: offset_of!(XpmemAccessPermit, flags),
    ap_hashlist_offset: offset_of!(XpmemAccessPermit, ap_hashlist),
};

static XPMEM_TG_DEREF_OFFSETS: XpmemDerefOffsets = XpmemDerefOffsets {
    refcnt_offset: offset_of!(XpmemThreadGroupPrefix, refcnt),
    flags_offset: offset_of!(XpmemThreadGroupPrefix, flags),
};

static XPMEM_SEG_DEREF_OFFSETS: XpmemDerefOffsets = XpmemDerefOffsets {
    refcnt_offset: offset_of!(XpmemSegment, refcnt),
    flags_offset: offset_of!(XpmemSegment, flags),
};

static XPMEM_AP_DEREF_OFFSETS: XpmemDerefOffsets = XpmemDerefOffsets {
    refcnt_offset: offset_of!(XpmemAccessPermit, refcnt),
    flags_offset: offset_of!(XpmemAccessPermit, flags),
};

static XPMEM_ATT_DEREF_OFFSETS: XpmemDerefOffsets = XpmemDerefOffsets {
    refcnt_offset: offset_of!(XpmemAttachment, refcnt),
    flags_offset: offset_of!(XpmemAttachment, flags),
};

static XPMEM_MAKE_SEGID_OFFSETS: XpmemMakeIdOffsets = XpmemMakeIdOffsets {
    tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
    tg_uniq_offset: offset_of!(XpmemThreadGroupPrefix, uniq_segid),
};

static XPMEM_MAKE_APID_OFFSETS: XpmemMakeIdOffsets = XpmemMakeIdOffsets {
    tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
    tg_uniq_offset: offset_of!(XpmemThreadGroupPrefix, uniq_apid),
};

static XPMEM_VALIDATE_ACCESS_OFFSETS: XpmemValidateAccessOffsets = XpmemValidateAccessOffsets {
    proc_pid_offset: offset_of!(Process, pid),
    proc_vm_offset: offset_of!(Process, vm),
    ap_mode_offset: offset_of!(XpmemAccessPermit, mode),
    ap_tg_offset: offset_of!(XpmemAccessPermit, tg),
    ap_seg_offset: offset_of!(XpmemAccessPermit, seg),
    tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
    seg_vaddr_offset: offset_of!(XpmemSegment, vaddr),
    seg_size_offset: offset_of!(XpmemSegment, size),
};

static XPMEM_PERM_OFFSETS: XpmemPermOffsets = XpmemPermOffsets {
    proc_ruid_offset: offset_of!(Process, ruid),
    proc_rgid_offset: offset_of!(Process, rgid),
    perm_uid_offset: offset_of!(XpmemPerm, uid),
    perm_gid_offset: offset_of!(XpmemPerm, gid),
    perm_mode_offset: offset_of!(XpmemPerm, mode),
    seg_permit_type_offset: offset_of!(XpmemSegment, permit_type),
    seg_permit_value_offset: offset_of!(XpmemSegment, permit_value),
    seg_tg_offset: offset_of!(XpmemSegment, tg),
    tg_uid_offset: offset_of!(XpmemThreadGroupPrefix, uid),
    tg_gid_offset: offset_of!(XpmemThreadGroupPrefix, gid),
};

static XPMEM_MAKE_SEGMENT_OFFSETS: XpmemMakeSegmentOffsets = XpmemMakeSegmentOffsets {
    proc_pid_offset: offset_of!(Process, pid),
    seg_size: size_of::<XpmemSegment>(),
    seg_lock_offset: offset_of!(XpmemSegment, lock),
    seg_segid_offset: offset_of!(XpmemSegment, segid),
    seg_vaddr_offset: offset_of!(XpmemSegment, vaddr),
    seg_size_offset: offset_of!(XpmemSegment, size),
    seg_permit_type_offset: offset_of!(XpmemSegment, permit_type),
    seg_permit_value_offset: offset_of!(XpmemSegment, permit_value),
    seg_tg_offset: offset_of!(XpmemSegment, tg),
    seg_ap_list_offset: offset_of!(XpmemSegment, ap_list),
    seg_seg_list_offset: offset_of!(XpmemSegment, seg_list),
    tg_seg_list_lock_offset: offset_of!(XpmemThreadGroupPrefix, seg_list_lock),
    tg_seg_list_offset: offset_of!(XpmemThreadGroupPrefix, seg_list),
};

static XPMEM_GET_OFFSETS: XpmemGetOffsets = XpmemGetOffsets {
    proc_pid_offset: offset_of!(Process, pid),
    ap_size: size_of::<XpmemAccessPermit>(),
    ap_lock_offset: offset_of!(XpmemAccessPermit, lock),
    ap_apid_offset: offset_of!(XpmemAccessPermit, apid),
    ap_mode_offset: offset_of!(XpmemAccessPermit, mode),
    ap_seg_offset: offset_of!(XpmemAccessPermit, seg),
    ap_tg_offset: offset_of!(XpmemAccessPermit, tg),
    ap_att_list_offset: offset_of!(XpmemAccessPermit, att_list),
    ap_ap_list_offset: offset_of!(XpmemAccessPermit, ap_list),
    ap_hashlist_offset: offset_of!(XpmemAccessPermit, ap_hashlist),
    seg_lock_offset: offset_of!(XpmemSegment, lock),
    seg_ap_list_offset: offset_of!(XpmemSegment, ap_list),
    tg_ap_hashtable_offset: size_of::<XpmemThreadGroupPrefix>(),
    hashlist_stride: size_of::<XpmemHashlist>(),
    hashlist_lock_offset: offset_of!(XpmemHashlist, lock),
    hashlist_list_offset: offset_of!(XpmemHashlist, list),
};

static XPMEM_TG_ID_OFFSETS: XpmemTgIdOffsets = XpmemTgIdOffsets {
    tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
};

static XPMEM_DETACH_OFFSETS: XpmemDetachOffsets = XpmemDetachOffsets {
    vm_memory_range_lock_offset: offset_of!(ProcessVm, memory_range_lock),
    range_start_offset: offset_of!(VmRange, start),
    range_private_data_offset: offset_of!(VmRange, private_data),
    att_at_lock_offset: offset_of!(XpmemAttachment, at_lock),
    att_at_vaddr_offset: offset_of!(XpmemAttachment, at_vaddr),
    att_at_size_offset: offset_of!(XpmemAttachment, at_size),
    att_flags_offset: offset_of!(XpmemAttachment, flags),
    att_ap_offset: offset_of!(XpmemAttachment, ap),
    att_vm_offset: offset_of!(XpmemAttachment, vm),
    att_att_list_offset: offset_of!(XpmemAttachment, att_list),
    ap_lock_offset: offset_of!(XpmemAccessPermit, lock),
    ap_tg_offset: offset_of!(XpmemAccessPermit, tg),
    ap_seg_offset: offset_of!(XpmemAccessPermit, seg),
    tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
};

static XPMEM_DETACH_ATT_OFFSETS: XpmemDetachAttOffsets = XpmemDetachAttOffsets {
    vm_memory_range_lock_offset: offset_of!(ProcessVm, memory_range_lock),
    range_start_offset: offset_of!(VmRange, start),
    range_end_offset: offset_of!(VmRange, end),
    range_private_data_offset: offset_of!(VmRange, private_data),
    att_at_lock_offset: offset_of!(XpmemAttachment, at_lock),
    att_vaddr_offset: offset_of!(XpmemAttachment, vaddr),
    att_at_vaddr_offset: offset_of!(XpmemAttachment, at_vaddr),
    att_at_size_offset: offset_of!(XpmemAttachment, at_size),
    att_flags_offset: offset_of!(XpmemAttachment, flags),
    att_vm_offset: offset_of!(XpmemAttachment, vm),
    att_att_list_offset: offset_of!(XpmemAttachment, att_list),
    ap_lock_offset: offset_of!(XpmemAccessPermit, lock),
    ap_seg_offset: offset_of!(XpmemAccessPermit, seg),
};

static XPMEM_CLEAR_PTES_OFFSETS: XpmemClearPtesOffsets = XpmemClearPtesOffsets {
    seg_lock_offset: offset_of!(XpmemSegment, lock),
    seg_vaddr_offset: offset_of!(XpmemSegment, vaddr),
    seg_size_offset: offset_of!(XpmemSegment, size),
    seg_ap_list_offset: offset_of!(XpmemSegment, ap_list),
    ap_lock_offset: offset_of!(XpmemAccessPermit, lock),
    ap_seg_offset: offset_of!(XpmemAccessPermit, seg),
    ap_att_list_offset: offset_of!(XpmemAccessPermit, att_list),
    ap_ap_list_offset: offset_of!(XpmemAccessPermit, ap_list),
    att_at_lock_offset: offset_of!(XpmemAttachment, at_lock),
    att_vaddr_offset: offset_of!(XpmemAttachment, vaddr),
    att_at_vaddr_offset: offset_of!(XpmemAttachment, at_vaddr),
    att_at_size_offset: offset_of!(XpmemAttachment, at_size),
    att_flags_offset: offset_of!(XpmemAttachment, flags),
    att_ap_offset: offset_of!(XpmemAttachment, ap),
    att_vm_offset: offset_of!(XpmemAttachment, vm),
    att_att_list_offset: offset_of!(XpmemAttachment, att_list),
    vm_memory_range_lock_offset: offset_of!(ProcessVm, memory_range_lock),
};

static XPMEM_REMOVE_PROCESS_MEMORY_RANGE_OFFSETS: XpmemRemoveProcessMemoryRangeOffsets =
    XpmemRemoveProcessMemoryRangeOffsets {
        range_start_offset: offset_of!(VmRange, start),
        range_end_offset: offset_of!(VmRange, end),
        range_private_data_offset: offset_of!(VmRange, private_data),
        att_at_lock_offset: offset_of!(XpmemAttachment, at_lock),
        att_at_vaddr_offset: offset_of!(XpmemAttachment, at_vaddr),
        att_at_size_offset: offset_of!(XpmemAttachment, at_size),
        att_flags_offset: offset_of!(XpmemAttachment, flags),
        att_ap_offset: offset_of!(XpmemAttachment, ap),
        att_att_list_offset: offset_of!(XpmemAttachment, att_list),
        ap_lock_offset: offset_of!(XpmemAccessPermit, lock),
    };

static XPMEM_REMOVE_PROCESS_RANGE_OFFSETS: XpmemRemoveProcessRangeOffsets =
    XpmemRemoveProcessRangeOffsets {
        range_start_offset: offset_of!(VmRange, start),
        range_end_offset: offset_of!(VmRange, end),
        range_flag_offset: offset_of!(VmRange, flag),
        range_private_data_offset: offset_of!(VmRange, private_data),
    };

static XPMEM_FREE_PROCESS_RANGE_OFFSETS: XpmemFreeProcessRangeOffsets =
    XpmemFreeProcessRangeOffsets {
        vm_address_space_offset: offset_of!(ProcessVm, address_space),
        vm_page_table_lock_offset: offset_of!(ProcessVm, page_table_lock),
        vm_range_tree_offset: offset_of!(ProcessVm, vm_range_tree),
        vm_range_cache_offset: offset_of!(ProcessVm, range_cache),
        vm_range_cache_count: VM_RANGE_CACHE_SIZE,
        address_space_page_table_offset: offset_of!(AddressSpace, page_table),
        range_start_offset: offset_of!(VmRange, start),
        range_end_offset: offset_of!(VmRange, end),
        range_memobj_offset: offset_of!(VmRange, memobj),
        range_rb_node_offset: offset_of!(VmRange, vm_rb_node),
    };

static XPMEM_UPDATE_PAGE_TABLE_OFFSETS: XpmemUpdatePageTableOffsets = XpmemUpdatePageTableOffsets {
    vm_address_space_offset: offset_of!(ProcessVm, address_space),
    address_space_page_table_offset: offset_of!(AddressSpace, page_table),
    range_start_offset: offset_of!(VmRange, start),
    range_end_offset: offset_of!(VmRange, end),
    range_pgshift_offset: offset_of!(VmRange, pgshift),
    range_private_data_offset: offset_of!(VmRange, private_data),
    att_at_vaddr_offset: offset_of!(XpmemAttachment, at_vaddr),
    att_at_vmr_offset: offset_of!(XpmemAttachment, at_vmr),
    att_flags_offset: offset_of!(XpmemAttachment, flags),
    att_ap_offset: offset_of!(XpmemAttachment, ap),
    ap_flags_offset: offset_of!(XpmemAccessPermit, flags),
    ap_mode_offset: offset_of!(XpmemAccessPermit, mode),
    ap_tg_offset: offset_of!(XpmemAccessPermit, tg),
    ap_seg_offset: offset_of!(XpmemAccessPermit, seg),
    tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
    tg_flags_offset: offset_of!(XpmemThreadGroupPrefix, flags),
    seg_flags_offset: offset_of!(XpmemSegment, flags),
    seg_tg_offset: offset_of!(XpmemSegment, tg),
};

static XPMEM_FAULT_PROCESS_RANGE_OFFSETS: XpmemFaultProcessRangeOffsets =
    XpmemFaultProcessRangeOffsets {
        vm_address_space_offset: offset_of!(ProcessVm, address_space),
        vm_proc_offset: offset_of!(ProcessVm, proc),
        vm_memory_range_lock_offset: offset_of!(ProcessVm, memory_range_lock),
        address_space_page_table_offset: offset_of!(AddressSpace, page_table),
        proc_straight_va_offset: offset_of!(Process, straight_va),
        proc_straight_len_offset: offset_of!(Process, straight_len),
        proc_straight_pa_offset: offset_of!(Process, straight_pa),
        range_start_offset: offset_of!(VmRange, start),
        range_end_offset: offset_of!(VmRange, end),
        range_flag_offset: offset_of!(VmRange, flag),
        range_pgshift_offset: offset_of!(VmRange, pgshift),
        range_private_data_offset: offset_of!(VmRange, private_data),
        att_at_vaddr_offset: offset_of!(XpmemAttachment, at_vaddr),
        att_at_size_offset: offset_of!(XpmemAttachment, at_size),
        att_vaddr_offset: offset_of!(XpmemAttachment, vaddr),
        att_flags_offset: offset_of!(XpmemAttachment, flags),
        att_ap_offset: offset_of!(XpmemAttachment, ap),
        ap_flags_offset: offset_of!(XpmemAccessPermit, flags),
        ap_mode_offset: offset_of!(XpmemAccessPermit, mode),
        ap_tg_offset: offset_of!(XpmemAccessPermit, tg),
        ap_seg_offset: offset_of!(XpmemAccessPermit, seg),
        tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
        tg_flags_offset: offset_of!(XpmemThreadGroupPrefix, flags),
        tg_vm_offset: offset_of!(XpmemThreadGroupPrefix, vm),
        tg_n_pinned_offset: offset_of!(XpmemThreadGroupPrefix, n_pinned),
        seg_flags_offset: offset_of!(XpmemSegment, flags),
    seg_tg_offset: offset_of!(XpmemSegment, tg),
};

static XPMEM_ATTACH_OFFSETS: XpmemAttachOffsets = XpmemAttachOffsets {
    mckfd_fd_offset: offset_of!(Mckfd, fd),
    vm_memory_range_lock_offset: offset_of!(ProcessVm, memory_range_lock),
    range_start_offset: offset_of!(VmRange, start),
    range_end_offset: offset_of!(VmRange, end),
    range_private_data_offset: offset_of!(VmRange, private_data),
    tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
    tg_flags_offset: offset_of!(XpmemThreadGroupPrefix, flags),
    ap_lock_offset: offset_of!(XpmemAccessPermit, lock),
    ap_flags_offset: offset_of!(XpmemAccessPermit, flags),
    ap_seg_offset: offset_of!(XpmemAccessPermit, seg),
    ap_att_list_offset: offset_of!(XpmemAccessPermit, att_list),
    seg_flags_offset: offset_of!(XpmemSegment, flags),
    seg_tg_offset: offset_of!(XpmemSegment, tg),
    att_size: size_of::<XpmemAttachment>(),
    att_at_lock_offset: offset_of!(XpmemAttachment, at_lock),
    att_vaddr_offset: offset_of!(XpmemAttachment, vaddr),
    att_at_size_offset: offset_of!(XpmemAttachment, at_size),
    att_flags_offset: offset_of!(XpmemAttachment, flags),
    att_ap_offset: offset_of!(XpmemAttachment, ap),
    att_vm_offset: offset_of!(XpmemAttachment, vm),
    att_att_list_offset: offset_of!(XpmemAttachment, att_list),
};

static XPMEM_IOCTL_OFFSETS: XpmemIoctlOffsets = XpmemIoctlOffsets {
    cmd_version: XPMEM_CMD_VERSION,
    cmd_make: XPMEM_CMD_MAKE,
    cmd_remove: XPMEM_CMD_REMOVE,
    cmd_get: XPMEM_CMD_GET,
    cmd_release: XPMEM_CMD_RELEASE,
    cmd_attach: XPMEM_CMD_ATTACH,
    cmd_detach: XPMEM_CMD_DETACH,
    current_version: XPMEM_CURRENT_VERSION,
    make_size: size_of::<XpmemCmdMake>(),
    make_vaddr_offset: offset_of!(XpmemCmdMake, vaddr),
    make_size_offset: offset_of!(XpmemCmdMake, size),
    make_permit_type_offset: offset_of!(XpmemCmdMake, permit_type),
    make_permit_value_offset: offset_of!(XpmemCmdMake, permit_value),
    make_segid_offset: offset_of!(XpmemCmdMake, segid),
    remove_size: size_of::<XpmemCmdRemove>(),
    remove_segid_offset: offset_of!(XpmemCmdRemove, segid),
    get_size: size_of::<XpmemCmdGet>(),
    get_segid_offset: offset_of!(XpmemCmdGet, segid),
    get_flags_offset: offset_of!(XpmemCmdGet, flags),
    get_permit_type_offset: offset_of!(XpmemCmdGet, permit_type),
    get_permit_value_offset: offset_of!(XpmemCmdGet, permit_value),
    get_apid_offset: offset_of!(XpmemCmdGet, apid),
    release_size: size_of::<XpmemCmdRelease>(),
    release_apid_offset: offset_of!(XpmemCmdRelease, apid),
    attach_size: size_of::<XpmemCmdAttach>(),
    attach_apid_offset: offset_of!(XpmemCmdAttach, apid),
    attach_offset_offset: offset_of!(XpmemCmdAttach, offset),
    attach_size_offset: offset_of!(XpmemCmdAttach, size),
    attach_vaddr_offset: offset_of!(XpmemCmdAttach, vaddr),
    attach_fd_offset: offset_of!(XpmemCmdAttach, fd),
    attach_flags_offset: offset_of!(XpmemCmdAttach, flags),
    detach_size: size_of::<XpmemCmdDetach>(),
    detach_vaddr_offset: offset_of!(XpmemCmdDetach, vaddr),
};

static XPMEM_PIN_PAGE_OFFSETS: XpmemPinPageOffsets = XpmemPinPageOffsets {
    tg_n_pinned_offset: offset_of!(XpmemThreadGroupPrefix, n_pinned),
    vm_memory_range_lock_offset: offset_of!(ProcessVm, memory_range_lock),
    vm_stack_start_offset: offset_of!(ProcessVm, region) + offset_of!(VmRegions, stack_start),
    vm_stack_end_offset: offset_of!(ProcessVm, region) + offset_of!(VmRegions, stack_end),
    range_start_offset: offset_of!(VmRange, start),
    range_private_data_offset: offset_of!(VmRange, private_data),
};

static XPMEM_ENSURE_VALID_PAGE_OFFSETS: XpmemEnsureValidPageOffsets = XpmemEnsureValidPageOffsets {
    seg_flags_offset: offset_of!(XpmemSegment, flags),
    seg_tg_offset: offset_of!(XpmemSegment, tg),
    tg_group_leader_offset: offset_of!(XpmemThreadGroupPrefix, group_leader),
    tg_vm_offset: offset_of!(XpmemThreadGroupPrefix, vm),
};

static XPMEM_VADDR_TO_PTE_OFFSETS: XpmemVaddrToPteOffsets = XpmemVaddrToPteOffsets {
    vm_address_space_offset: offset_of!(ProcessVm, address_space),
    address_space_page_table_offset: offset_of!(AddressSpace, page_table),
    range_pgshift_offset: offset_of!(VmRange, pgshift),
};

static XPMEM_UNPIN_PAGES_OFFSETS: XpmemUnpinPagesOffsets = XpmemUnpinPagesOffsets {
    seg_tg_offset: offset_of!(XpmemSegment, tg),
    tg_n_pinned_offset: offset_of!(XpmemThreadGroupPrefix, n_pinned),
};

static XPMEM_FAULT_PROCESS_RANGE_OPS: XpmemFaultProcessRangeOps = XpmemFaultProcessRangeOps {
    att_ref_fn: Some(xpmem_att_ref),
    att_deref_fn: Some(xpmem_att_deref_bridge),
    ap_ref_fn: Some(xpmem_ap_ref),
    ap_deref_fn: Some(xpmem_ap_deref_bridge),
    tg_ref_fn: Some(xpmem_tg_ref_bridge),
    tg_deref_fn: Some(xpmem_tg_deref_bridge),
    seg_ref_fn: Some(xpmem_seg_ref),
    seg_deref_fn: Some(xpmem_seg_deref_bridge),
    bug_on_fn: Some(xpmem_bug_on_bridge),
    ensure_valid_fn: Some(xpmem_ensure_valid_page_bridge),
    read_lock_noirq_fn: Some(xpmem_rwspin_read_lock_noirq_bridge),
    read_unlock_noirq_fn: Some(xpmem_rwspin_read_unlock_noirq_bridge),
    vaddr_to_pte_fn: Some(xpmem_vaddr_to_pte_bridge),
    pte_present_fn: Some(xpmem_pte_present_bridge),
    pte_phys_fn: Some(xpmem_pte_phys_bridge),
    pt_lookup_pte_fn: Some(xpmem_pt_lookup_pte_bridge),
    smaller_page_fn: Some(xpmem_get_smaller_page_size_bridge),
    adjust_page_fn: Some(xpmem_adjust_page_size_bridge),
    vrflag_to_ptattr_fn: Some(xpmem_vrflag_to_ptattr_bridge),
    pgsize_contiguous_fn: Some(xpmem_pgsize_contiguous_bridge),
    pt_set_pte_fn: Some(xpmem_pt_set_pte_bridge),
    pt_set_range_fn: Some(xpmem_pt_set_range_bridge),
    atomic_dec_fn: Some(xpmem_atomic_dec_bridge),
    flush_tlb_single_fn: Some(xpmem_flush_tlb_single_bridge),
    log_fn: Some(xpmem_fault_log_bridge),
};

#[no_mangle]
pub extern "C" fn xpmem_id_wrapper_bug_on(_condition: CInt) {}

#[no_mangle]
pub extern "C" fn xpmem_tg_hashtable_index_log(_tgid: CInt, _index: CInt) {}

#[no_mangle]
pub extern "C" fn xpmem_ap_hashtable_index_log(_apid: CLong, _index: CInt) {}

#[no_mangle]
pub extern "C" fn xpmem_destroyable_log(_event: CInt) {}

#[no_mangle]
pub unsafe extern "C" fn xpmem_refcnt_ptr_bridge(object: *mut c_void, kind: CInt) -> *mut c_void {
    if object.is_null() {
        return core::ptr::null_mut();
    }

    match kind {
        XPMEM_REF_KIND_TG => {
            &raw mut (*(object.cast::<XpmemThreadGroupPrefix>())).refcnt as *mut RustIhkAtomic
                as *mut c_void
        }
        XPMEM_REF_KIND_SEG => {
            &raw mut (*(object.cast::<XpmemSegment>())).refcnt as *mut RustIhkAtomic as *mut c_void
        }
        XPMEM_REF_KIND_AP => {
            &raw mut (*(object.cast::<XpmemAccessPermit>())).refcnt as *mut RustIhkAtomic
                as *mut c_void
        }
        XPMEM_REF_KIND_ATT => {
            &raw mut (*(object.cast::<XpmemAttachment>())).refcnt as *mut RustIhkAtomic
                as *mut c_void
        }
        _ => core::ptr::null_mut(),
    }
}

#[no_mangle]
pub extern "C" fn xpmem_refcnt_log(_kind: CInt, _refcnt: CInt) {}

#[no_mangle]
pub unsafe extern "C" fn xpmem_atomic_set_bridge(counter: *mut c_void, value: CInt) {
    ihk_atomic_set(counter.cast::<RustIhkAtomic>(), value);
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_atomic_read_bridge(counter: *mut c_void) -> CInt {
    ihk_atomic_read(counter.cast::<RustIhkAtomic>())
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_atomic_inc_bridge(counter: *mut c_void) -> CInt {
    ihk_atomic_inc_return(counter.cast::<RustIhkAtomic>())
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_atomic_dec_bridge(counter: *mut c_void) -> CInt {
    ihk_atomic_dec_return(counter.cast::<RustIhkAtomic>())
}

#[no_mangle]
pub extern "C" fn xpmem_bug_on_bridge(_condition: CInt) {}

#[no_mangle]
pub unsafe extern "C" fn xpmem_kfree_bridge(ptr: *mut c_void) {
    __kfree(ptr);
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_rwspin_write_lock_bridge(lock: *mut c_void) -> CULong {
    crate::lock_helpers::ihk_rwspinlock_write_lock(lock.cast::<IhkRwSpinlock>())
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_rwspin_write_unlock_bridge(lock: *mut c_void, irqstate: CULong) {
    crate::lock_helpers::ihk_rwspinlock_write_unlock(lock.cast::<IhkRwSpinlock>(), irqstate);
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_spin_lock_noirq_bridge(lock: *mut c_void) {
    crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(
        lock.cast::<crate::spinlock_helpers::IhkSpinlock>(),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_spin_unlock_noirq_bridge(lock: *mut c_void) {
    crate::spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(
        lock.cast::<crate::spinlock_helpers::IhkSpinlock>(),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_list_del_init_bridge(entry: *mut c_void) {
    crate::list_helpers::list_del_init(entry.cast::<crate::list_helpers::ListHead>());
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_lookup_range_bridge(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
) -> *mut c_void {
    lookup_process_memory_range(vm.cast::<ProcessVm>(), start, end).cast::<c_void>()
}

unsafe fn xpmem_current_thread() -> *mut Thread {
    let local = get_cpu_local_var(ihk_mc_get_processor_id());
    if local.is_null() {
        core::ptr::null_mut()
    } else {
        (*local).current
    }
}

unsafe fn xpmem_current_process() -> *mut Process {
    let thread = xpmem_current_thread();
    if thread.is_null() {
        core::ptr::null_mut()
    } else {
        (*thread).proc
    }
}

unsafe fn xpmem_current_vm() -> *mut ProcessVm {
    let proc = xpmem_current_process();
    if proc.is_null() {
        core::ptr::null_mut()
    } else {
        (*proc).vm
    }
}

unsafe extern "C" fn xpmem_alloc_nowait(size: SizeT) -> *mut c_void {
    __kmalloc(size as CInt, IHK_MC_AP_NOWAIT)
}

unsafe extern "C" fn xpmem_forward(syscall_num: CInt, ctx: *mut c_void) -> CLong {
    syscall_generic_forwarding(syscall_num, ctx)
}

unsafe extern "C" fn xpmem_mckfd_lock(lock: *mut c_void) -> CLong {
    crate::spinlock_helpers::__ihk_mc_spinlock_lock(
        lock.cast::<crate::spinlock_helpers::IhkSpinlock>(),
    ) as CLong
}

unsafe extern "C" fn xpmem_mckfd_unlock(lock: *mut c_void, irqstate: CLong) {
    crate::spinlock_helpers::__ihk_mc_spinlock_unlock(
        lock.cast::<crate::spinlock_helpers::IhkSpinlock>(),
        irqstate as CULong,
    );
}

unsafe extern "C" fn xpmem_rwlock_writer_lock_bridge(lock: *mut c_void, node: *mut c_void) {
    crate::lock_helpers::__mcs_rwlock_writer_lock(
        lock.cast::<McsRwlockLock>(),
        node.cast::<McsRwlockNodeIrqsave>(),
    );
}

unsafe extern "C" fn xpmem_rwlock_writer_unlock_bridge(lock: *mut c_void, node: *mut c_void) {
    crate::lock_helpers::__mcs_rwlock_writer_unlock(
        lock.cast::<McsRwlockLock>(),
        node.cast::<McsRwlockNodeIrqsave>(),
    );
}

unsafe extern "C" fn xpmem_rwlock_init_bridge(lock: *mut c_void) {
    crate::lock_helpers::mcs_rwlock_init(lock.cast::<McsRwlockLock>());
}

unsafe extern "C" fn xpmem_list_init_bridge(entry: *mut c_void) {
    crate::list_helpers::INIT_LIST_HEAD(entry.cast::<crate::list_helpers::ListHead>());
}

unsafe extern "C" fn xpmem_list_add_tail_bridge(entry: *mut c_void, head: *mut c_void) {
    crate::list_helpers::list_add_tail(
        entry.cast::<crate::list_helpers::ListHead>(),
        head.cast::<crate::list_helpers::ListHead>(),
    );
}

unsafe extern "C" fn xpmem_spinlock_init_bridge(lock: *mut c_void) {
    crate::spinlock_helpers::ihk_mc_spinlock_init(
        lock.cast::<crate::spinlock_helpers::IhkSpinlock>(),
    );
}

unsafe extern "C" fn xpmem_rwspinlock_init_bridge(lock: *mut c_void) {
    crate::lock_helpers::ihk_rwspinlock_init(lock.cast::<IhkRwSpinlock>());
}

unsafe extern "C" fn xpmem_atomic_sub_bridge(value: CInt, counter: *mut c_void) {
    ihk_atomic_sub(value, counter.cast::<RustIhkAtomic>());
}

unsafe extern "C" fn xpmem_copy_from_user_bridge(
    dst: *mut c_void,
    src: CULong,
    size: SizeT,
) -> CInt {
    copy_from_user(dst, src as *const c_void, size)
}

unsafe extern "C" fn xpmem_copy_to_user_bridge(
    dst: CULong,
    src: *const c_void,
    size: SizeT,
) -> CInt {
    copy_to_user(dst as *mut c_void, src, size)
}

unsafe extern "C" fn xpmem_do_mmap_bridge(
    addr: CULong,
    len: SizeT,
    prot: CULong,
    flags: CULong,
    fd: CInt,
    offset: OffT,
    vm_flags: CULong,
    private_data: *mut c_void,
) -> CULong {
    do_mmap(
        addr,
        len,
        prot as CInt,
        flags as CInt,
        fd,
        offset,
        vm_flags as CInt,
        private_data,
    ) as CULong
}

unsafe extern "C" fn xpmem_next_range_bridge(vm: *mut c_void, range: *mut c_void) -> *mut c_void {
    next_process_memory_range(vm.cast::<ProcessVm>(), range.cast::<VmRange>()).cast::<c_void>()
}

unsafe extern "C" fn xpmem_split_range_bridge(
    vm: *mut c_void,
    range: *mut c_void,
    addr: CULong,
    new_range: *mut *mut c_void,
) -> CInt {
    split_process_memory_range(
        vm.cast::<ProcessVm>(),
        range.cast::<VmRange>(),
        addr,
        new_range.cast::<*mut VmRange>(),
    )
}

unsafe extern "C" fn xpmem_pt_clear_range_bridge(
    page_table: *mut c_void,
    vm: *mut c_void,
    start: CULong,
    end: CULong,
) -> CInt {
    ihk_mc_pt_clear_range(
        page_table,
        vm.cast::<ProcessVm>(),
        start as *mut c_void,
        end as *mut c_void,
    )
}

unsafe extern "C" fn xpmem_range_erase_bridge(root: *mut c_void, node: *mut c_void) {
    rb_erase(node, root);
}

unsafe extern "C" fn xpmem_memobj_unref_bridge(ptr: *mut c_void) {
    let _ = memobj_unref(ptr);
}

extern "C" fn xpmem_open_log_bridge(
    _event: CInt,
    _syscall_num: CInt,
    _pathname: *const u8,
    _flags: CInt,
    _value: CLong,
    _ptr: *mut c_void,
) {
}

extern "C" fn xpmem_close_log_bridge(_event: CInt, _mckfd: *mut c_void, _value: CInt) {}

extern "C" fn xpmem_flush_log_bridge(_event: CInt, _tg: *mut c_void, _value: CLong) {}

extern "C" fn xpmem_remove_seg_log_bridge(
    _event: CInt,
    _tg: *mut c_void,
    _seg: *mut c_void,
    _value: CLong,
) {
}

extern "C" fn xpmem_remove_segs_log_bridge(
    _event: CInt,
    _tg: *mut c_void,
    _seg: *mut c_void,
    _value: CLong,
) {
}

extern "C" fn xpmem_release_ap_log_bridge(
    _event: CInt,
    _tg: *mut c_void,
    _ap: *mut c_void,
    _value: CLong,
) {
}

extern "C" fn xpmem_release_aps_log_bridge(
    _event: CInt,
    _tg: *mut c_void,
    _ap: *mut c_void,
    _value: CLong,
) {
}

extern "C" fn xpmem_remove_process_range_log_bridge(
    _vm: *mut c_void,
    _start: CULong,
    _end: CULong,
    _error: CInt,
    _free_error: CInt,
) {
}

extern "C" fn xpmem_free_process_range_log_bridge(
    _event: CInt,
    _vm: *mut c_void,
    _range: *mut c_void,
    _start: CULong,
    _end: CULong,
    _error: CInt,
) {
}

unsafe extern "C" fn xpmem_partition_init() -> CInt {
    xpmem_partition_init_body_result(
        &raw mut xpmem_my_part,
        &xpmem_partition_offsets,
        Some(xpmem_alloc_nowait),
        Some(xpmem_rwlock_init_bridge),
        Some(xpmem_list_init_bridge),
        Some(xpmem_atomic_set_bridge),
    )
}

unsafe extern "C" fn xpmem_partition_exit() {
    let _ = xpmem_partition_exit_body_result(&raw mut xpmem_my_part, Some(xpmem_kfree_bridge));
}

unsafe extern "C" fn xpmem_open_tg() -> CInt {
    let thread = xpmem_current_thread();
    if thread.is_null() || (*thread).proc.is_null() {
        return -EINVAL;
    }

    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    xpmem_open_tg_body_result(
        &raw mut xpmem_my_part,
        thread.cast::<c_void>(),
        (*thread).proc.cast::<c_void>(),
        (*thread).vm.cast::<c_void>(),
        &XPMEM_OPEN_TG_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_tg_ref_by_tgid),
        Some(xpmem_tg_deref_bridge),
        Some(xpmem_alloc_nowait),
        Some(xpmem_spinlock_init_bridge),
        Some(xpmem_rwlock_init_bridge),
        Some(xpmem_list_init_bridge),
        Some(xpmem_atomic_set_bridge),
        Some(xpmem_tg_not_destroyable),
        Some(xpmem_rwlock_writer_lock_bridge),
        Some(xpmem_rwlock_writer_unlock_bridge),
        Some(xpmem_list_add_tail_bridge),
    )
}

unsafe extern "C" fn xpmem_destroy_tg_bridge(tg: *mut c_void) {
    let _ = xpmem_destroy_tg_body_result(
        tg,
        Some(xpmem_tg_destroyable),
        Some(xpmem_tg_deref_bridge),
    );
}

unsafe extern "C" fn xpmem_make_segid_bridge(tg: *mut c_void) -> CLong {
    xpmem_make_object_id_body_result(
        tg,
        &XPMEM_MAKE_SEGID_OFFSETS,
        Some(xpmem_atomic_inc_bridge),
        Some(xpmem_atomic_dec_bridge),
        Some(xpmem_bug_on_bridge),
    )
}

unsafe extern "C" fn xpmem_make_apid_bridge(tg: *mut c_void) -> CLong {
    xpmem_make_object_id_body_result(
        tg,
        &XPMEM_MAKE_APID_OFFSETS,
        Some(xpmem_atomic_inc_bridge),
        Some(xpmem_atomic_dec_bridge),
        Some(xpmem_bug_on_bridge),
    )
}

unsafe extern "C" fn xpmem_check_permit_mode_bridge(flags: CInt, seg: *mut c_void) -> CInt {
    let proc = xpmem_current_process();
    xpmem_check_permit_mode_body_result(
        flags,
        seg,
        proc.cast::<c_void>(),
        &XPMEM_PERM_OFFSETS,
        Some(xpmem_bug_on_bridge),
    )
}

unsafe extern "C" fn xpmem_validate_access_bridge(
    ap: *mut c_void,
    offset: OffT,
    size: SizeT,
    mode: CInt,
    vaddrp: *mut CULong,
) -> CInt {
    xpmem_validate_access_body_result(
        ap,
        xpmem_current_process().cast::<c_void>(),
        offset,
        size,
        mode,
        vaddrp,
        &XPMEM_VALIDATE_ACCESS_OFFSETS,
    )
}

unsafe extern "C" fn xpmem_tg_ref_by_segid_bridge(segid: CLong) -> *mut c_void {
    xpmem_tg_ref_by_tgid(xpmem_segid_to_tgid(segid))
}

unsafe extern "C" fn xpmem_tg_ref_by_apid_bridge(apid: CLong) -> *mut c_void {
    xpmem_tg_ref_by_tgid(xpmem_apid_to_tgid(apid))
}

unsafe extern "C" fn xpmem_seg_ref_by_segid_bridge(
    tg: *mut c_void,
    segid: CLong,
) -> *mut c_void {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    xpmem_seg_ref_by_segid_body_result(
        tg,
        segid,
        &XPMEM_SEG_LOOKUP_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_rwlock_reader_lock_bridge),
        Some(xpmem_rwlock_reader_unlock_bridge),
        Some(xpmem_seg_ref),
    )
}

unsafe extern "C" fn xpmem_ap_ref_by_apid_bridge(tg: *mut c_void, apid: CLong) -> *mut c_void {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    xpmem_ap_ref_by_apid_body_result(
        tg,
        apid,
        &XPMEM_AP_LOOKUP_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_rwlock_reader_lock_bridge),
        Some(xpmem_rwlock_reader_unlock_bridge),
        Some(xpmem_ap_ref),
    )
}

unsafe extern "C" fn xpmem_make_bridge(
    vaddr: CULong,
    size: SizeT,
    permit_type: CInt,
    permit_value: *mut c_void,
    segidp: *mut CLong,
) -> CInt {
    let proc = xpmem_current_process();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    xpmem_make_segment_body_result(
        vaddr,
        size,
        permit_type,
        permit_value,
        segidp,
        proc.cast::<c_void>(),
        &XPMEM_MAKE_SEGMENT_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_tg_ref_by_tgid),
        Some(xpmem_tg_deref_bridge),
        Some(xpmem_make_segid_bridge),
        Some(xpmem_alloc_nowait),
        Some(xpmem_spinlock_init_bridge),
        Some(xpmem_list_init_bridge),
        Some(xpmem_seg_not_destroyable),
        Some(xpmem_rwlock_writer_lock_bridge),
        Some(xpmem_rwlock_writer_unlock_bridge),
        Some(xpmem_list_add_tail_bridge),
        Some(xpmem_bug_on_bridge),
    )
}

unsafe extern "C" fn xpmem_remove_seg_bridge(tg: *mut c_void, seg: *mut c_void) {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let _ = xpmem_remove_seg_body_result(
        tg,
        seg,
        &XPMEM_REMOVE_SEG_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_clear_ptes_bridge),
        Some(xpmem_rwlock_writer_lock_bridge),
        Some(xpmem_rwlock_writer_unlock_bridge),
        Some(xpmem_list_del_init_bridge),
        Some(xpmem_seg_destroyable),
        Some(xpmem_remove_seg_log_bridge),
    );
}

unsafe extern "C" fn xpmem_remove_bridge(segid: CLong) -> CInt {
    let proc = xpmem_current_process();
    if proc.is_null() {
        return -EINVAL;
    }

    xpmem_remove_body_result(
        segid,
        (*proc).pid,
        &XPMEM_TG_ID_OFFSETS,
        Some(xpmem_tg_ref_by_segid_bridge),
        Some(xpmem_seg_ref_by_segid_bridge),
        Some(xpmem_remove_seg_bridge),
        Some(xpmem_seg_deref_bridge),
        Some(xpmem_tg_deref_bridge),
    )
}

unsafe extern "C" fn xpmem_remove_segs_of_tg_bridge(tg: *mut c_void) {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let _ = xpmem_remove_segs_of_tg_body_result(
        tg,
        &XPMEM_REMOVE_SEGS_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_rwlock_writer_lock_bridge),
        Some(xpmem_rwlock_writer_unlock_bridge),
        Some(xpmem_seg_ref),
        Some(xpmem_remove_seg_bridge),
        Some(xpmem_seg_deref_bridge),
        Some(xpmem_remove_segs_log_bridge),
    );
}

unsafe extern "C" fn xpmem_get_bridge(
    segid: CLong,
    flags: CInt,
    permit_type: CInt,
    permit_value: *mut c_void,
    apidp: *mut CLong,
) -> CInt {
    let proc = xpmem_current_process();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    xpmem_get_body_result(
        segid,
        flags,
        permit_type,
        permit_value,
        apidp,
        proc.cast::<c_void>(),
        &XPMEM_GET_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_tg_ref_by_segid_bridge),
        Some(xpmem_seg_ref_by_segid_bridge),
        Some(xpmem_check_permit_mode_bridge),
        Some(xpmem_tg_ref_by_tgid),
        Some(xpmem_make_apid_bridge),
        Some(xpmem_alloc_nowait),
        Some(xpmem_spinlock_init_bridge),
        Some(xpmem_list_init_bridge),
        Some(xpmem_ap_not_destroyable),
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_rwlock_writer_lock_bridge),
        Some(xpmem_rwlock_writer_unlock_bridge),
        Some(xpmem_list_add_tail_bridge),
        Some(xpmem_seg_deref_bridge),
        Some(xpmem_tg_deref_bridge),
        Some(xpmem_bug_on_bridge),
    )
}

unsafe extern "C" fn xpmem_release_ap_bridge(tg: *mut c_void, ap: *mut c_void) {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let _ = xpmem_release_ap_body_result(
        tg,
        ap,
        &XPMEM_RELEASE_AP_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_rwlock_writer_lock_bridge),
        Some(xpmem_rwlock_writer_unlock_bridge),
        Some(xpmem_list_del_init_bridge),
        Some(xpmem_att_ref),
        Some(xpmem_detach_att_bridge),
        Some(xpmem_att_deref_bridge),
        Some(xpmem_seg_deref_bridge),
        Some(xpmem_tg_deref_bridge),
        Some(xpmem_ap_destroyable),
        Some(xpmem_release_ap_log_bridge),
    );
}

unsafe extern "C" fn xpmem_release_bridge(apid: CLong) -> CInt {
    let proc = xpmem_current_process();
    if proc.is_null() {
        return -EINVAL;
    }

    xpmem_release_body_result(
        apid,
        (*proc).pid,
        &XPMEM_TG_ID_OFFSETS,
        Some(xpmem_tg_ref_by_apid_bridge),
        Some(xpmem_ap_ref_by_apid_bridge),
        Some(xpmem_release_ap_bridge),
        Some(xpmem_ap_deref_bridge),
        Some(xpmem_tg_deref_bridge),
    )
}

unsafe extern "C" fn xpmem_release_aps_of_tg_bridge(tg: *mut c_void) {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let _ = xpmem_release_aps_of_tg_body_result(
        tg,
        &XPMEM_RELEASE_APS_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_rwlock_writer_lock_bridge),
        Some(xpmem_rwlock_writer_unlock_bridge),
        Some(xpmem_ap_ref),
        Some(xpmem_release_ap_bridge),
        Some(xpmem_ap_deref_bridge),
        Some(xpmem_release_aps_log_bridge),
    );
}

unsafe extern "C" fn xpmem_flush(mckfd: *mut c_void) {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let _ = xpmem_flush_body_result(
        mckfd,
        &raw mut xpmem_my_part,
        &XPMEM_FLUSH_OFFSETS,
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_tg_ref_by_tgid_all_nolock),
        Some(xpmem_rwlock_writer_lock_bridge),
        Some(xpmem_rwlock_writer_unlock_bridge),
        Some(xpmem_list_del_init_bridge),
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_release_aps_of_tg_bridge),
        Some(xpmem_remove_segs_of_tg_bridge),
        Some(xpmem_destroy_tg_bridge),
        Some(xpmem_flush_log_bridge),
    );
}

unsafe extern "C" fn xpmem_attach_bridge(
    mckfd: *mut c_void,
    apid: CLong,
    offset: OffT,
    size: SizeT,
    vaddr: CULong,
    _fd: CInt,
    _flags: CInt,
    at_vaddrp: *mut CULong,
) -> CInt {
    let proc = xpmem_current_process();
    let vm = xpmem_current_vm();
    if proc.is_null() || vm.is_null() {
        return -EINVAL;
    }

    xpmem_attach_body_result(
        mckfd,
        apid,
        offset,
        size,
        vaddr,
        at_vaddrp,
        (*proc).pid,
        vm.cast::<c_void>(),
        0,
        PROT_READ | PROT_WRITE,
        MAP_SHARED,
        MAP_FIXED,
        MAP_ANONYMOUS,
        VR_XPMEM,
        &XPMEM_ATTACH_OFFSETS,
        Some(xpmem_tg_ref_by_apid_bridge),
        Some(xpmem_ap_ref_by_apid_bridge),
        Some(xpmem_seg_ref),
        Some(xpmem_seg_deref_bridge),
        Some(xpmem_tg_ref_bridge),
        Some(xpmem_tg_deref_bridge),
        Some(xpmem_ap_deref_bridge),
        Some(xpmem_validate_access_bridge),
        Some(xpmem_alloc_nowait),
        Some(xpmem_rwspinlock_init_bridge),
        Some(xpmem_list_init_bridge),
        Some(xpmem_att_not_destroyable),
        Some(xpmem_att_ref),
        Some(xpmem_att_deref_bridge),
        Some(xpmem_rwspin_write_lock_bridge),
        Some(xpmem_rwspin_write_unlock_bridge),
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_list_add_tail_bridge),
        Some(xpmem_rwspin_read_lock_noirq_bridge),
        Some(xpmem_rwspin_read_unlock_noirq_bridge),
        Some(xpmem_lookup_range_bridge),
        Some(xpmem_next_range_bridge),
        Some(xpmem_do_mmap_bridge),
        Some(xpmem_list_del_init_bridge),
        Some(xpmem_att_destroyable),
    )
}

unsafe extern "C" fn xpmem_unpin_pages_bridge(
    seg: *mut c_void,
    vm: *mut c_void,
    vaddr: CULong,
    size: SizeT,
) {
    let _ = xpmem_unpin_pages_body_result(
        seg,
        vm,
        vaddr,
        size,
        &XPMEM_UNPIN_PAGES_OFFSETS,
        Some(xpmem_vaddr_to_pte_bridge),
        Some(xpmem_pte_present_bridge),
        Some(xpmem_atomic_sub_bridge),
    );
}

unsafe extern "C" fn xpmem_remove_process_range_bridge(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    ro_freedp: *mut CInt,
) -> CInt {
    xpmem_remove_process_range_body_result(
        vm,
        start,
        end,
        ro_freedp,
        &XPMEM_REMOVE_PROCESS_RANGE_OFFSETS,
        Some(xpmem_lookup_range_bridge),
        Some(xpmem_next_range_bridge),
        Some(xpmem_split_range_bridge),
        Some(xpmem_remove_process_memory_range),
        Some(xpmem_free_process_memory_range),
        Some(xpmem_remove_process_range_log_bridge),
    )
}

unsafe extern "C" fn xpmem_vm_munmap_bridge(vm: *mut c_void, addr: CULong, len: SizeT) -> CInt {
    begin_free_pages_pending();
    let ret = xpmem_remove_process_range_bridge(
        vm,
        addr,
        addr.wrapping_add(len as CULong),
        core::ptr::null_mut(),
    );
    finish_free_pages_pending();
    ret
}

unsafe extern "C" fn xpmem_detach_bridge(at_vaddr: CULong) -> CInt {
    let proc = xpmem_current_process();
    let vm = xpmem_current_vm();
    if proc.is_null() || vm.is_null() {
        return -EINVAL;
    }

    xpmem_detach_body_result(
        at_vaddr,
        (*proc).pid,
        vm.cast::<c_void>(),
        &XPMEM_DETACH_OFFSETS,
        Some(xpmem_rwspin_write_lock_noirq_bridge),
        Some(xpmem_rwspin_write_unlock_noirq_bridge),
        Some(xpmem_lookup_range_bridge),
        Some(xpmem_att_ref),
        Some(xpmem_att_deref_bridge),
        Some(xpmem_rwspin_write_lock_bridge),
        Some(xpmem_rwspin_write_unlock_bridge),
        Some(xpmem_ap_ref),
        Some(xpmem_ap_deref_bridge),
        Some(xpmem_unpin_pages_bridge),
        Some(xpmem_vm_munmap_bridge),
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_list_del_init_bridge),
        Some(xpmem_att_destroyable),
    )
}

unsafe extern "C" fn xpmem_detach_att_bridge(ap: *mut c_void, att: *mut c_void) {
    let _ = xpmem_detach_att_body_result(
        ap,
        att,
        &XPMEM_DETACH_ATT_OFFSETS,
        Some(xpmem_rwspin_read_lock_noirq_bridge),
        Some(xpmem_rwspin_read_unlock_noirq_bridge),
        Some(xpmem_rwspin_write_lock_bridge),
        Some(xpmem_rwspin_write_unlock_bridge),
        Some(xpmem_lookup_range_bridge),
        Some(xpmem_unpin_pages_bridge),
        Some(xpmem_vm_munmap_bridge),
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_list_del_init_bridge),
        Some(xpmem_att_destroyable),
    );
}

unsafe extern "C" fn xpmem_clear_ptes_of_att_bridge(
    att: *mut c_void,
    start: CULong,
    end: CULong,
) {
    let _ = xpmem_clear_ptes_of_att_body_result(
        att,
        start,
        end,
        &XPMEM_CLEAR_PTES_OFFSETS,
        Some(xpmem_rwspin_read_lock_noirq_bridge),
        Some(xpmem_rwspin_read_unlock_noirq_bridge),
        Some(xpmem_rwspin_write_lock_bridge),
        Some(xpmem_rwspin_write_unlock_bridge),
        Some(xpmem_lookup_range_bridge),
        Some(xpmem_unpin_pages_bridge),
        Some(xpmem_vm_munmap_bridge),
    );
}

unsafe extern "C" fn xpmem_clear_ptes_of_ap_bridge(ap: *mut c_void, start: CULong, end: CULong) {
    let _ = xpmem_clear_ptes_of_ap_body_result(
        ap,
        start,
        end,
        &XPMEM_CLEAR_PTES_OFFSETS,
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_att_ref),
        Some(xpmem_clear_ptes_of_att_bridge),
        Some(xpmem_att_deref_bridge),
    );
}

unsafe extern "C" fn xpmem_clear_ptes_range_bridge(
    seg: *mut c_void,
    start: CULong,
    end: CULong,
) {
    let _ = xpmem_clear_ptes_range_body_result(
        seg,
        start,
        end,
        &XPMEM_CLEAR_PTES_OFFSETS,
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_ap_ref),
        Some(xpmem_clear_ptes_of_ap_bridge),
        Some(xpmem_ap_deref_bridge),
    );
}

unsafe extern "C" fn xpmem_clear_ptes_bridge(seg: *mut c_void) {
    let _ = xpmem_clear_ptes_body_result(
        seg,
        &XPMEM_CLEAR_PTES_OFFSETS,
        Some(xpmem_clear_ptes_range_bridge),
    );
}

unsafe extern "C" fn xpmem_free_process_memory_range(
    vm: *mut c_void,
    range: *mut c_void,
) -> CInt {
    xpmem_free_process_range_body_result(
        vm,
        range,
        &XPMEM_FREE_PROCESS_RANGE_OFFSETS,
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_pt_clear_range_bridge),
        Some(xpmem_memobj_unref_bridge),
        Some(xpmem_range_erase_bridge),
        Some(xpmem_kfree_bridge),
        Some(xpmem_free_process_range_log_bridge),
    )
}

unsafe extern "C" fn xpmem_ioctl(mckfd: *mut c_void, ctx: *mut c_void) -> CInt {
    let cmd = ihk_mc_syscall_arg1(ctx);
    let arg = ihk_mc_syscall_arg2(ctx);

    xpmem_ioctl_body_result(
        mckfd,
        cmd,
        arg,
        &XPMEM_IOCTL_OFFSETS,
        Some(xpmem_copy_from_user_bridge),
        Some(xpmem_copy_to_user_bridge),
        Some(xpmem_make_bridge),
        Some(xpmem_remove_bridge),
        Some(xpmem_get_bridge),
        Some(xpmem_release_bridge),
        Some(xpmem_attach_bridge),
        Some(xpmem_detach_bridge),
    )
}

unsafe extern "C" fn xpmem_close(mckfd: *mut c_void, _ctx: *mut c_void) -> CInt {
    xpmem_close_body_result(
        mckfd,
        &raw mut xpmem_my_part,
        &XPMEM_CLOSE_OFFSETS,
        Some(xpmem_atomic_dec_bridge),
        Some(xpmem_flush),
        Some(xpmem_partition_exit),
        Some(xpmem_close_log_bridge),
    )
}

unsafe extern "C" fn xpmem_dup(mckfd: *mut c_void, _ctx: *mut c_void) -> CInt {
    xpmem_dup_body_result(
        mckfd,
        &raw mut xpmem_my_part,
        &XPMEM_CLOSE_OFFSETS,
        Some(xpmem_atomic_inc_bridge),
    )
}

unsafe fn do_xpmem_open(
    syscall_num: CInt,
    pathname: *const u8,
    flags: CInt,
    ctx: *mut c_void,
) -> CInt {
    let proc = xpmem_current_process();
    if proc.is_null() {
        return -EINVAL;
    }

    xpmem_open_body_result(
        syscall_num,
        pathname,
        flags,
        ctx,
        &raw mut xpmem_my_part,
        proc.cast::<c_void>(),
        &XPMEM_OPEN_OFFSETS,
        xpmem_ioctl as usize as CULong,
        xpmem_close as usize as CULong,
        xpmem_dup as usize as CULong,
        Some(xpmem_partition_init),
        Some(xpmem_forward),
        Some(xpmem_open_tg),
        Some(xpmem_alloc_nowait),
        Some(xpmem_mckfd_lock),
        Some(xpmem_mckfd_unlock),
        Some(xpmem_atomic_inc_bridge),
        Some(xpmem_open_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_open(
    pathname: *const u8,
    flags: CInt,
    ctx: *mut c_void,
) -> CInt {
    do_xpmem_open(__NR_OPEN, pathname, flags, ctx)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_openat(
    pathname: *const u8,
    flags: CInt,
    ctx: *mut c_void,
) -> CInt {
    do_xpmem_open(__NR_OPENAT, pathname, flags, ctx)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_rwspin_read_lock_noirq_bridge(lock: *mut c_void) {
    crate::lock_helpers::ihk_rwspinlock_read_lock_noirq(lock.cast::<IhkRwSpinlock>());
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_rwspin_read_unlock_noirq_bridge(lock: *mut c_void) {
    crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(lock.cast::<IhkRwSpinlock>());
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_rwspin_write_lock_noirq_bridge(lock: *mut c_void) {
    crate::lock_helpers::ihk_rwspinlock_write_lock_noirq(lock.cast::<IhkRwSpinlock>());
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_rwspin_write_unlock_noirq_bridge(lock: *mut c_void) {
    crate::lock_helpers::ihk_rwspinlock_write_unlock_noirq(lock.cast::<IhkRwSpinlock>());
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_page_fault_vm_bridge(
    vm: *mut c_void,
    vaddr: CULong,
    reason: CULong,
) -> CInt {
    page_fault_process_vm(vm.cast::<ProcessVm>(), vaddr as *mut c_void, reason)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_page_fault_range_bridge(
    vm: *mut c_void,
    range: *mut c_void,
    vaddr: CULong,
    reason: CULong,
) -> CInt {
    page_fault_process_memory_range(
        vm.cast::<ProcessVm>(),
        range.cast::<VmRange>(),
        vaddr as *mut c_void,
        reason,
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_pt_lookup_pte_bridge(
    page_table: *mut c_void,
    vaddr: CULong,
    pgshift: CInt,
    base: *mut *mut c_void,
    pgsize: *mut SizeT,
    p2align: *mut CInt,
) -> *mut c_void {
    ihk_mc_pt_lookup_pte(
        page_table,
        vaddr as *mut c_void,
        pgshift,
        base,
        pgsize,
        p2align,
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_pte_present_bridge(pte: *mut c_void) -> CInt {
    (!pte.is_null() && crate::pte_helpers::pte_is_null(pte.cast::<CULong>()) == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_pte_phys_bridge(pte: *mut c_void) -> CULong {
    crate::pte_helpers::pte_get_phys(pte.cast::<CULong>())
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_get_smaller_page_size_bridge(
    pgsize: SizeT,
    new_pgsize: *mut SizeT,
    p2align: *mut CInt,
) -> CInt {
    arch_get_smaller_page_size(core::ptr::null_mut(), pgsize, new_pgsize, p2align)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_adjust_page_size_bridge(
    page_table: *mut c_void,
    fault_addr: CULong,
    pte: *mut c_void,
    pgaddr: *mut *mut c_void,
    pgsize: *mut SizeT,
) {
    arch_adjust_allocate_page_size(page_table, fault_addr, pte, pgaddr, pgsize);
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_vrflag_to_ptattr_bridge(flag: CULong, reason: CULong) -> CULong {
    arch_vrflag_to_ptattr(flag, reason, core::ptr::null_mut()) as CULong
}

#[no_mangle]
pub extern "C" fn xpmem_pgsize_contiguous_bridge(pgsize: SizeT) -> CInt {
    crate::pte_helpers::pgsize_is_contiguous(pgsize)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_pt_set_pte_bridge(
    page_table: *mut c_void,
    pte: *mut c_void,
    pgsize: SizeT,
    phys: CULong,
    attr: CULong,
) -> CInt {
    ihk_mc_pt_set_pte(page_table, pte, pgsize, phys, attr as CInt)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_pt_set_range_bridge(
    page_table: *mut c_void,
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CULong,
    pgshift: CInt,
    vmr: *mut c_void,
    replace: CInt,
) -> CInt {
    ihk_mc_pt_set_range(
        page_table,
        vm.cast::<ProcessVm>(),
        start as *mut c_void,
        end as *mut c_void,
        phys,
        attr as CInt,
        pgshift,
        vmr.cast::<VmRange>(),
        replace,
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_flush_tlb_single_bridge(vaddr: CULong) {
    flush_tlb_single(vaddr);
}

#[no_mangle]
pub extern "C" fn xpmem_fault_log_bridge(
    _event: CInt,
    _a: CULong,
    _b: CULong,
    _c: CULong,
    _size: SizeT,
    _error: CInt,
) {
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_pin_page_bridge(
    tg: *mut c_void,
    thread: *mut c_void,
    vm: *mut c_void,
    vaddr: CULong,
    page_in: CInt,
) -> CInt {
    let current_vm = xpmem_current_vm();
    if current_vm.is_null() {
        return -EINVAL;
    }

    xpmem_pin_page_body_result(
        tg,
        thread,
        vm,
        current_vm.cast::<c_void>(),
        vaddr,
        page_in,
        &XPMEM_PIN_PAGE_OFFSETS,
        Some(xpmem_rwspin_read_lock_noirq_bridge),
        Some(xpmem_rwspin_read_unlock_noirq_bridge),
        Some(xpmem_lookup_range_bridge),
        Some(xpmem_page_fault_vm_bridge),
        Some(xpmem_page_fault_range_bridge),
        Some(xpmem_atomic_inc_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_ensure_valid_page_bridge(
    seg: *mut c_void,
    vaddr: CULong,
    page_in: CInt,
) -> CInt {
    xpmem_ensure_valid_page_body_result(
        seg,
        vaddr,
        page_in,
        &XPMEM_ENSURE_VALID_PAGE_OFFSETS,
        Some(xpmem_pin_page_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_vaddr_to_pte_bridge(
    vm: *mut c_void,
    vaddr: CULong,
    pgsize: *mut SizeT,
) -> *mut c_void {
    xpmem_vaddr_to_pte_body_result(
        vm,
        vaddr,
        pgsize,
        &XPMEM_VADDR_TO_PTE_OFFSETS,
        Some(xpmem_lookup_range_bridge),
        Some(xpmem_pt_lookup_pte_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_fault_range_page_in_bridge(
    vm: *mut c_void,
    vmr: *mut c_void,
    vaddr: CULong,
    reason: CULong,
    page_in_remote: CInt,
) -> CInt {
    xpmem_fault_process_memory_range_inner(vm, vmr, vaddr, reason, page_in_remote)
}

unsafe fn xpmem_fault_process_memory_range_inner(
    vm: *mut c_void,
    vmr: *mut c_void,
    vaddr: CULong,
    reason: CULong,
    page_in_remote: CInt,
) -> CInt {
    let proc = xpmem_current_process();
    if proc.is_null() {
        return -EINVAL;
    }

    xpmem_fault_process_memory_range_body_result(
        vm,
        vmr,
        vaddr,
        reason,
        page_in_remote,
        (*proc).pid,
        (*proc).vm.cast::<c_void>(),
        &XPMEM_FAULT_PROCESS_RANGE_OFFSETS,
        &XPMEM_FAULT_PROCESS_RANGE_OPS,
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_fault_process_memory_range(
    vm: *mut c_void,
    vmr: *mut c_void,
    vaddr: CULong,
    reason: CULong,
) -> CInt {
    if vmr.is_null() {
        return -EFAULT;
    }

    let att = (*vmr.cast::<VmRange>()).private_data;
    if att.is_null() {
        return -EFAULT;
    }

    let at_lock = &raw mut (*att.cast::<XpmemAttachment>()).at_lock;
    let irqstate = crate::lock_helpers::ihk_rwspinlock_read_lock(at_lock.cast::<IhkRwSpinlock>());
    let ret = xpmem_fault_process_memory_range_inner(vm, vmr, vaddr, reason, 1);
    crate::lock_helpers::ihk_rwspinlock_read_unlock(at_lock.cast::<IhkRwSpinlock>(), irqstate);
    ret
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_update_process_page_table(
    vm: *mut c_void,
    vmr: *mut c_void,
) -> CInt {
    let proc = xpmem_current_process();
    if proc.is_null() {
        return -EINVAL;
    }

    xpmem_update_process_page_table_body_result(
        vm,
        vmr,
        (*proc).pid,
        xpmem_page_in_remote_on_attach,
        &XPMEM_UPDATE_PAGE_TABLE_OFFSETS,
        Some(xpmem_att_ref),
        Some(xpmem_att_deref_bridge),
        Some(xpmem_ap_ref),
        Some(xpmem_ap_deref_bridge),
        Some(xpmem_tg_ref_bridge),
        Some(xpmem_tg_deref_bridge),
        Some(xpmem_seg_ref),
        Some(xpmem_seg_deref_bridge),
        Some(xpmem_bug_on_bridge),
        Some(xpmem_fault_range_page_in_bridge),
        Some(xpmem_pt_lookup_pte_bridge),
        Some(xpmem_pte_present_bridge),
        Some(xpmem_update_page_table_log_bridge),
    )
}

#[no_mangle]
pub extern "C" fn xpmem_update_page_table_log_bridge(
    _event: CInt,
    _vm: *mut c_void,
    _range: *mut c_void,
    _vaddr: CULong,
    _error: CInt,
) {
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_rwlock_reader_lock_bridge(lock: *mut c_void, node: *mut c_void) {
    crate::lock_helpers::__mcs_rwlock_reader_lock(
        lock.cast::<McsRwlockLock>(),
        node.cast::<McsRwlockNodeIrqsave>(),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_rwlock_reader_unlock_bridge(lock: *mut c_void, node: *mut c_void) {
    crate::lock_helpers::__mcs_rwlock_reader_unlock(
        lock.cast::<McsRwlockLock>(),
        node.cast::<McsRwlockNodeIrqsave>(),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_ref_bridge(tg: *mut c_void) {
    xpmem_tg_ref(tg);
}

#[no_mangle]
pub extern "C" fn xpmem_tg_deref_log_bridge(_tg: *mut c_void) {}

#[no_mangle]
pub extern "C" fn xpmem_seg_deref_log_bridge(_seg: *mut c_void) {}

#[no_mangle]
pub extern "C" fn xpmem_ap_deref_log_bridge(_ap: *mut c_void) {}

#[no_mangle]
pub extern "C" fn xpmem_att_deref_log_bridge(_att: *mut c_void) {}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_deref_bridge(tg: *mut c_void) {
    xpmem_deref_body_result(
        tg,
        &XPMEM_TG_DEREF_OFFSETS,
        0,
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_atomic_dec_bridge),
        Some(xpmem_bug_on_bridge),
        Some(xpmem_tg_deref_log_bridge),
        Some(xpmem_kfree_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_seg_deref_bridge(seg: *mut c_void) {
    xpmem_deref_body_result(
        seg,
        &XPMEM_SEG_DEREF_OFFSETS,
        1,
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_atomic_dec_bridge),
        Some(xpmem_bug_on_bridge),
        Some(xpmem_seg_deref_log_bridge),
        Some(xpmem_kfree_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_ap_deref_bridge(ap: *mut c_void) {
    xpmem_deref_body_result(
        ap,
        &XPMEM_AP_DEREF_OFFSETS,
        1,
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_atomic_dec_bridge),
        Some(xpmem_bug_on_bridge),
        Some(xpmem_ap_deref_log_bridge),
        Some(xpmem_kfree_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_att_deref_bridge(att: *mut c_void) {
    xpmem_deref_body_result(
        att,
        &XPMEM_ATT_DEREF_OFFSETS,
        1,
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_atomic_dec_bridge),
        Some(xpmem_bug_on_bridge),
        Some(xpmem_att_deref_log_bridge),
        Some(xpmem_kfree_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_process_memory_range(
    vm: *mut c_void,
    vmr: *mut c_void,
) -> CInt {
    xpmem_remove_process_memory_range_body_result(
        vm,
        vmr,
        &XPMEM_REMOVE_PROCESS_MEMORY_RANGE_OFFSETS,
        Some(xpmem_att_ref),
        Some(xpmem_att_deref_bridge),
        Some(xpmem_rwspin_write_lock_bridge),
        Some(xpmem_rwspin_write_unlock_bridge),
        Some(xpmem_lookup_range_bridge),
        Some(xpmem_ap_ref),
        Some(xpmem_ap_deref_bridge),
        Some(xpmem_spin_lock_noirq_bridge),
        Some(xpmem_spin_unlock_noirq_bridge),
        Some(xpmem_list_del_init_bridge),
        Some(xpmem_att_destroyable),
    )
}

#[no_mangle]
pub extern "C" fn xpmem_tg_ref_lookup_log(
    _event: CInt,
    _tgid: CInt,
    _return_destroying: CInt,
    _part: *mut c_void,
    _result: *mut c_void,
) {
}

#[repr(C)]
pub struct XpmemOpenOffsets {
    pub proc_mckfd_lock_offset: SizeT,
    pub proc_mckfd_offset: SizeT,
    pub part_n_opened_offset: SizeT,
    pub mckfd_size: SizeT,
    pub mckfd_next_offset: SizeT,
    pub mckfd_fd_offset: SizeT,
    pub mckfd_sig_no_offset: SizeT,
    pub mckfd_data_offset: SizeT,
    pub mckfd_ioctl_cb_offset: SizeT,
    pub mckfd_close_cb_offset: SizeT,
    pub mckfd_dup_cb_offset: SizeT,
}

#[repr(C)]
pub struct XpmemCloseOffsets {
    pub part_n_opened_offset: SizeT,
    pub mckfd_fd_offset: SizeT,
    pub mckfd_data_offset: SizeT,
}

#[repr(C)]
pub struct XpmemIoctlOffsets {
    pub cmd_version: CULong,
    pub cmd_make: CULong,
    pub cmd_remove: CULong,
    pub cmd_get: CULong,
    pub cmd_release: CULong,
    pub cmd_attach: CULong,
    pub cmd_detach: CULong,
    pub current_version: CInt,
    pub make_size: SizeT,
    pub make_vaddr_offset: SizeT,
    pub make_size_offset: SizeT,
    pub make_permit_type_offset: SizeT,
    pub make_permit_value_offset: SizeT,
    pub make_segid_offset: SizeT,
    pub remove_size: SizeT,
    pub remove_segid_offset: SizeT,
    pub get_size: SizeT,
    pub get_segid_offset: SizeT,
    pub get_flags_offset: SizeT,
    pub get_permit_type_offset: SizeT,
    pub get_permit_value_offset: SizeT,
    pub get_apid_offset: SizeT,
    pub release_size: SizeT,
    pub release_apid_offset: SizeT,
    pub attach_size: SizeT,
    pub attach_apid_offset: SizeT,
    pub attach_offset_offset: SizeT,
    pub attach_size_offset: SizeT,
    pub attach_vaddr_offset: SizeT,
    pub attach_fd_offset: SizeT,
    pub attach_flags_offset: SizeT,
    pub detach_size: SizeT,
    pub detach_vaddr_offset: SizeT,
}

#[repr(C)]
pub struct XpmemPartitionOffsets {
    pub part_size: SizeT,
    pub part_n_opened_offset: SizeT,
    pub part_tg_hashtable_offset: SizeT,
    pub hashlist_stride: SizeT,
    pub hashlist_lock_offset: SizeT,
    pub hashlist_list_offset: SizeT,
}

#[repr(C)]
pub struct XpmemOpenTgOffsets {
    pub proc_pid_offset: SizeT,
    pub proc_ruid_offset: SizeT,
    pub proc_rgid_offset: SizeT,
    pub tg_size: SizeT,
    pub tg_lock_offset: SizeT,
    pub tg_tgid_offset: SizeT,
    pub tg_uid_offset: SizeT,
    pub tg_gid_offset: SizeT,
    pub tg_uniq_segid_offset: SizeT,
    pub tg_uniq_apid_offset: SizeT,
    pub tg_seg_list_lock_offset: SizeT,
    pub tg_seg_list_offset: SizeT,
    pub tg_n_pinned_offset: SizeT,
    pub tg_tg_hashlist_offset: SizeT,
    pub tg_group_leader_offset: SizeT,
    pub tg_vm_offset: SizeT,
    pub tg_ap_hashtable_offset: SizeT,
    pub part_tg_hashtable_offset: SizeT,
    pub hashlist_stride: SizeT,
    pub hashlist_lock_offset: SizeT,
    pub hashlist_list_offset: SizeT,
}

#[repr(C)]
pub struct XpmemFlushOffsets {
    pub part_tg_hashtable_offset: SizeT,
    pub hashlist_stride: SizeT,
    pub hashlist_lock_offset: SizeT,
    pub hashlist_list_offset: SizeT,
    pub mckfd_data_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub tg_lock_offset: SizeT,
    pub tg_flags_offset: SizeT,
    pub tg_hashlist_offset: SizeT,
    pub tg_vm_offset: SizeT,
}

#[repr(C)]
pub struct XpmemRemoveSegOffsets {
    pub tg_seg_list_lock_offset: SizeT,
    pub seg_lock_offset: SizeT,
    pub seg_flags_offset: SizeT,
    pub seg_list_offset: SizeT,
}

#[repr(C)]
pub struct XpmemRemoveSegsOffsets {
    pub tg_seg_list_lock_offset: SizeT,
    pub tg_seg_list_offset: SizeT,
    pub seg_list_offset: SizeT,
}

#[repr(C)]
pub struct XpmemReleaseApOffsets {
    pub tg_ap_hashtable_offset: SizeT,
    pub hashlist_stride: SizeT,
    pub hashlist_lock_offset: SizeT,
    pub ap_lock_offset: SizeT,
    pub ap_apid_offset: SizeT,
    pub ap_flags_offset: SizeT,
    pub ap_seg_offset: SizeT,
    pub ap_att_list_offset: SizeT,
    pub ap_ap_list_offset: SizeT,
    pub ap_hashlist_offset: SizeT,
    pub att_att_list_offset: SizeT,
    pub seg_lock_offset: SizeT,
    pub seg_tg_offset: SizeT,
}

#[repr(C)]
pub struct XpmemReleaseApsOffsets {
    pub tg_ap_hashtable_offset: SizeT,
    pub hashlist_stride: SizeT,
    pub hashlist_lock_offset: SizeT,
    pub hashlist_list_offset: SizeT,
    pub ap_hashlist_offset: SizeT,
}

#[repr(C)]
pub struct XpmemTgLookupOffsets {
    pub part_tg_hashtable_offset: SizeT,
    pub hashlist_stride: SizeT,
    pub hashlist_list_offset: SizeT,
    pub tg_tgid_offset: SizeT,
    pub tg_flags_offset: SizeT,
    pub tg_hashlist_offset: SizeT,
}

#[repr(C)]
pub struct XpmemSegLookupOffsets {
    pub tg_seg_list_lock_offset: SizeT,
    pub tg_seg_list_offset: SizeT,
    pub seg_segid_offset: SizeT,
    pub seg_flags_offset: SizeT,
    pub seg_list_offset: SizeT,
}

#[repr(C)]
pub struct XpmemApLookupOffsets {
    pub tg_ap_hashtable_offset: SizeT,
    pub hashlist_stride: SizeT,
    pub hashlist_lock_offset: SizeT,
    pub hashlist_list_offset: SizeT,
    pub ap_apid_offset: SizeT,
    pub ap_flags_offset: SizeT,
    pub ap_hashlist_offset: SizeT,
}

#[repr(C)]
pub struct XpmemDerefOffsets {
    pub refcnt_offset: SizeT,
    pub flags_offset: SizeT,
}

#[repr(C)]
pub struct XpmemMakeIdOffsets {
    pub tg_tgid_offset: SizeT,
    pub tg_uniq_offset: SizeT,
}

#[repr(C)]
pub struct XpmemValidateAccessOffsets {
    pub proc_pid_offset: SizeT,
    pub proc_vm_offset: SizeT,
    pub ap_mode_offset: SizeT,
    pub ap_tg_offset: SizeT,
    pub ap_seg_offset: SizeT,
    pub tg_tgid_offset: SizeT,
    pub seg_vaddr_offset: SizeT,
    pub seg_size_offset: SizeT,
}

#[repr(C)]
pub struct XpmemPermOffsets {
    pub proc_ruid_offset: SizeT,
    pub proc_rgid_offset: SizeT,
    pub perm_uid_offset: SizeT,
    pub perm_gid_offset: SizeT,
    pub perm_mode_offset: SizeT,
    pub seg_permit_type_offset: SizeT,
    pub seg_permit_value_offset: SizeT,
    pub seg_tg_offset: SizeT,
    pub tg_uid_offset: SizeT,
    pub tg_gid_offset: SizeT,
}

#[repr(C)]
pub struct XpmemMakeSegmentOffsets {
    pub proc_pid_offset: SizeT,
    pub seg_size: SizeT,
    pub seg_lock_offset: SizeT,
    pub seg_segid_offset: SizeT,
    pub seg_vaddr_offset: SizeT,
    pub seg_size_offset: SizeT,
    pub seg_permit_type_offset: SizeT,
    pub seg_permit_value_offset: SizeT,
    pub seg_tg_offset: SizeT,
    pub seg_ap_list_offset: SizeT,
    pub seg_seg_list_offset: SizeT,
    pub tg_seg_list_lock_offset: SizeT,
    pub tg_seg_list_offset: SizeT,
}

#[repr(C)]
pub struct XpmemGetOffsets {
    pub proc_pid_offset: SizeT,
    pub ap_size: SizeT,
    pub ap_lock_offset: SizeT,
    pub ap_apid_offset: SizeT,
    pub ap_mode_offset: SizeT,
    pub ap_seg_offset: SizeT,
    pub ap_tg_offset: SizeT,
    pub ap_att_list_offset: SizeT,
    pub ap_ap_list_offset: SizeT,
    pub ap_hashlist_offset: SizeT,
    pub seg_lock_offset: SizeT,
    pub seg_ap_list_offset: SizeT,
    pub tg_ap_hashtable_offset: SizeT,
    pub hashlist_stride: SizeT,
    pub hashlist_lock_offset: SizeT,
    pub hashlist_list_offset: SizeT,
}

#[repr(C)]
pub struct XpmemTgIdOffsets {
    pub tg_tgid_offset: SizeT,
}

#[repr(C)]
pub struct XpmemDetachOffsets {
    pub vm_memory_range_lock_offset: SizeT,
    pub range_start_offset: SizeT,
    pub range_private_data_offset: SizeT,
    pub att_at_lock_offset: SizeT,
    pub att_at_vaddr_offset: SizeT,
    pub att_at_size_offset: SizeT,
    pub att_flags_offset: SizeT,
    pub att_ap_offset: SizeT,
    pub att_vm_offset: SizeT,
    pub att_att_list_offset: SizeT,
    pub ap_lock_offset: SizeT,
    pub ap_tg_offset: SizeT,
    pub ap_seg_offset: SizeT,
    pub tg_tgid_offset: SizeT,
}

#[repr(C)]
pub struct XpmemDetachAttOffsets {
    pub vm_memory_range_lock_offset: SizeT,
    pub range_start_offset: SizeT,
    pub range_end_offset: SizeT,
    pub range_private_data_offset: SizeT,
    pub att_at_lock_offset: SizeT,
    pub att_vaddr_offset: SizeT,
    pub att_at_vaddr_offset: SizeT,
    pub att_at_size_offset: SizeT,
    pub att_flags_offset: SizeT,
    pub att_vm_offset: SizeT,
    pub att_att_list_offset: SizeT,
    pub ap_lock_offset: SizeT,
    pub ap_seg_offset: SizeT,
}

#[repr(C)]
pub struct XpmemClearPtesOffsets {
    pub seg_lock_offset: SizeT,
    pub seg_vaddr_offset: SizeT,
    pub seg_size_offset: SizeT,
    pub seg_ap_list_offset: SizeT,
    pub ap_lock_offset: SizeT,
    pub ap_seg_offset: SizeT,
    pub ap_att_list_offset: SizeT,
    pub ap_ap_list_offset: SizeT,
    pub att_at_lock_offset: SizeT,
    pub att_vaddr_offset: SizeT,
    pub att_at_vaddr_offset: SizeT,
    pub att_at_size_offset: SizeT,
    pub att_flags_offset: SizeT,
    pub att_ap_offset: SizeT,
    pub att_vm_offset: SizeT,
    pub att_att_list_offset: SizeT,
    pub vm_memory_range_lock_offset: SizeT,
}

#[repr(C)]
pub struct XpmemRemoveProcessMemoryRangeOffsets {
    pub range_start_offset: SizeT,
    pub range_end_offset: SizeT,
    pub range_private_data_offset: SizeT,
    pub att_at_lock_offset: SizeT,
    pub att_at_vaddr_offset: SizeT,
    pub att_at_size_offset: SizeT,
    pub att_flags_offset: SizeT,
    pub att_ap_offset: SizeT,
    pub att_att_list_offset: SizeT,
    pub ap_lock_offset: SizeT,
}

#[repr(C)]
pub struct XpmemRemoveProcessRangeOffsets {
    pub range_start_offset: SizeT,
    pub range_end_offset: SizeT,
    pub range_flag_offset: SizeT,
    pub range_private_data_offset: SizeT,
}

#[repr(C)]
pub struct XpmemFreeProcessRangeOffsets {
    pub vm_address_space_offset: SizeT,
    pub vm_page_table_lock_offset: SizeT,
    pub vm_range_tree_offset: SizeT,
    pub vm_range_cache_offset: SizeT,
    pub vm_range_cache_count: SizeT,
    pub address_space_page_table_offset: SizeT,
    pub range_start_offset: SizeT,
    pub range_end_offset: SizeT,
    pub range_memobj_offset: SizeT,
    pub range_rb_node_offset: SizeT,
}

#[repr(C)]
pub struct XpmemUpdatePageTableOffsets {
    pub vm_address_space_offset: SizeT,
    pub address_space_page_table_offset: SizeT,
    pub range_start_offset: SizeT,
    pub range_end_offset: SizeT,
    pub range_pgshift_offset: SizeT,
    pub range_private_data_offset: SizeT,
    pub att_at_vaddr_offset: SizeT,
    pub att_at_vmr_offset: SizeT,
    pub att_flags_offset: SizeT,
    pub att_ap_offset: SizeT,
    pub ap_flags_offset: SizeT,
    pub ap_mode_offset: SizeT,
    pub ap_tg_offset: SizeT,
    pub ap_seg_offset: SizeT,
    pub tg_tgid_offset: SizeT,
    pub tg_flags_offset: SizeT,
    pub seg_flags_offset: SizeT,
    pub seg_tg_offset: SizeT,
}

#[repr(C)]
pub struct XpmemFaultProcessRangeOffsets {
    pub vm_address_space_offset: SizeT,
    pub vm_proc_offset: SizeT,
    pub vm_memory_range_lock_offset: SizeT,
    pub address_space_page_table_offset: SizeT,
    pub proc_straight_va_offset: SizeT,
    pub proc_straight_len_offset: SizeT,
    pub proc_straight_pa_offset: SizeT,
    pub range_start_offset: SizeT,
    pub range_end_offset: SizeT,
    pub range_flag_offset: SizeT,
    pub range_pgshift_offset: SizeT,
    pub range_private_data_offset: SizeT,
    pub att_at_vaddr_offset: SizeT,
    pub att_at_size_offset: SizeT,
    pub att_vaddr_offset: SizeT,
    pub att_flags_offset: SizeT,
    pub att_ap_offset: SizeT,
    pub ap_flags_offset: SizeT,
    pub ap_mode_offset: SizeT,
    pub ap_tg_offset: SizeT,
    pub ap_seg_offset: SizeT,
    pub tg_tgid_offset: SizeT,
    pub tg_flags_offset: SizeT,
    pub tg_vm_offset: SizeT,
    pub tg_n_pinned_offset: SizeT,
    pub seg_flags_offset: SizeT,
    pub seg_tg_offset: SizeT,
}

#[repr(C)]
pub struct XpmemFaultProcessRangeOps {
    pub att_ref_fn: Option<XpmemObjectVoidFn>,
    pub att_deref_fn: Option<XpmemObjectVoidFn>,
    pub ap_ref_fn: Option<XpmemObjectVoidFn>,
    pub ap_deref_fn: Option<XpmemObjectVoidFn>,
    pub tg_ref_fn: Option<XpmemObjectVoidFn>,
    pub tg_deref_fn: Option<XpmemObjectVoidFn>,
    pub seg_ref_fn: Option<XpmemObjectVoidFn>,
    pub seg_deref_fn: Option<XpmemObjectVoidFn>,
    pub bug_on_fn: Option<XpmemBugOnFn>,
    pub ensure_valid_fn: Option<XpmemEnsureValidPageFn>,
    pub read_lock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    pub read_unlock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    pub vaddr_to_pte_fn: Option<XpmemVaddrToPteFn>,
    pub pte_present_fn: Option<XpmemPtePresentFn>,
    pub pte_phys_fn: Option<XpmemPtePhysFn>,
    pub pt_lookup_pte_fn: Option<XpmemPtLookupPteFn>,
    pub smaller_page_fn: Option<XpmemGetSmallerPageSizeFn>,
    pub adjust_page_fn: Option<XpmemAdjustPageSizeFn>,
    pub vrflag_to_ptattr_fn: Option<XpmemVrflagToPtattrFn>,
    pub pgsize_contiguous_fn: Option<XpmemPgsizeContiguousFn>,
    pub pt_set_pte_fn: Option<XpmemPtSetPteFn>,
    pub pt_set_range_fn: Option<XpmemPtSetRangeFn>,
    pub atomic_dec_fn: Option<XpmemAtomicDecFn>,
    pub flush_tlb_single_fn: Option<XpmemFlushTlbSingleFn>,
    pub log_fn: Option<XpmemFaultLogFn>,
}

#[repr(C)]
pub struct XpmemAttachOffsets {
    pub mckfd_fd_offset: SizeT,
    pub vm_memory_range_lock_offset: SizeT,
    pub range_start_offset: SizeT,
    pub range_end_offset: SizeT,
    pub range_private_data_offset: SizeT,
    pub tg_tgid_offset: SizeT,
    pub tg_flags_offset: SizeT,
    pub ap_lock_offset: SizeT,
    pub ap_flags_offset: SizeT,
    pub ap_seg_offset: SizeT,
    pub ap_att_list_offset: SizeT,
    pub seg_flags_offset: SizeT,
    pub seg_tg_offset: SizeT,
    pub att_size: SizeT,
    pub att_at_lock_offset: SizeT,
    pub att_vaddr_offset: SizeT,
    pub att_at_size_offset: SizeT,
    pub att_flags_offset: SizeT,
    pub att_ap_offset: SizeT,
    pub att_vm_offset: SizeT,
    pub att_att_list_offset: SizeT,
}

#[repr(C)]
pub struct XpmemPinPageOffsets {
    pub tg_n_pinned_offset: SizeT,
    pub vm_memory_range_lock_offset: SizeT,
    pub vm_stack_start_offset: SizeT,
    pub vm_stack_end_offset: SizeT,
    pub range_start_offset: SizeT,
    pub range_private_data_offset: SizeT,
}

#[repr(C)]
pub struct XpmemEnsureValidPageOffsets {
    pub seg_flags_offset: SizeT,
    pub seg_tg_offset: SizeT,
    pub tg_group_leader_offset: SizeT,
    pub tg_vm_offset: SizeT,
}

#[repr(C)]
pub struct XpmemVaddrToPteOffsets {
    pub vm_address_space_offset: SizeT,
    pub address_space_page_table_offset: SizeT,
    pub range_pgshift_offset: SizeT,
}

#[repr(C)]
pub struct XpmemUnpinPagesOffsets {
    pub seg_tg_offset: SizeT,
    pub tg_n_pinned_offset: SizeT,
}

#[inline(always)]
fn offset_in_page(value: CULong) -> CULong {
    value & !PAGE_MASK
}

#[inline(always)]
fn low_u32(value: CLong) -> u32 {
    value as u64 as u32
}

#[inline(always)]
fn high_u32(value: CLong) -> u32 {
    (value as u64 >> 32) as u32
}

#[inline(always)]
unsafe fn field_ptr<T>(base: *mut c_void, offset: SizeT) -> *mut T {
    (base as *mut u8).add(offset).cast::<T>()
}

#[inline(always)]
unsafe fn list_next(entry: *mut c_void) -> *mut c_void {
    *(entry as *mut *mut c_void)
}

#[inline(always)]
unsafe fn list_is_empty(entry: *mut c_void) -> bool {
    list_next(entry) == entry
}

#[inline(always)]
unsafe fn list_entry(entry: *mut c_void, offset: SizeT) -> *mut c_void {
    (entry as *mut u8).sub(offset).cast::<c_void>()
}

#[inline(always)]
fn ptr_is_err(ptr: *mut c_void) -> bool {
    let value = ptr as isize;
    value < 0 && value >= -4095
}

#[inline(always)]
fn err_ptr(error: CInt) -> *mut c_void {
    (error as isize) as *mut c_void
}

#[inline(always)]
fn ptr_err(ptr: *mut c_void) -> CInt {
    ptr as isize as CInt
}

#[inline(always)]
fn xpmem_perms_inner(
    perm_uid: CInt,
    perm_gid: CInt,
    perm_mode: CULong,
    flag: CInt,
    current_ruid: CInt,
    current_rgid: CInt,
) -> CInt {
    let requested_mode = (flag >> 6) | (flag >> 3) | flag;
    let mut granted_mode = perm_mode;

    if perm_uid == current_ruid {
        granted_mode >>= 6;
    } else if perm_gid == current_rgid {
        granted_mode >>= 3;
    }

    if (requested_mode as CULong & !granted_mode & 0o7) != 0 {
        -1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_id_to_tgid_result(id: CLong) -> CInt {
    low_u32(id) as CInt
}

#[no_mangle]
pub extern "C" fn xpmem_segid_to_tgid(segid: CLong) -> CInt {
    xpmem_id_wrapper_bug_on((segid <= 0) as CInt);
    xpmem_id_to_tgid_result(segid)
}

#[no_mangle]
pub extern "C" fn xpmem_apid_to_tgid(apid: CLong) -> CInt {
    xpmem_id_wrapper_bug_on((apid <= 0) as CInt);
    xpmem_id_to_tgid_result(apid)
}

#[no_mangle]
pub extern "C" fn xpmem_tg_hashtable_index_result(tgid: CInt) -> CInt {
    (tgid as u32 % XPMEM_TG_HASHTABLE_SIZE as u32) as CInt
}

#[no_mangle]
pub extern "C" fn xpmem_tg_hashtable_index(tgid: CInt) -> CInt {
    let index = xpmem_tg_hashtable_index_result(tgid);
    xpmem_tg_hashtable_index_log(tgid, index);
    index
}

#[no_mangle]
pub extern "C" fn xpmem_ap_hashtable_index_result(apid: CLong) -> CInt {
    (high_u32(apid) % XPMEM_AP_HASHTABLE_SIZE as u32) as CInt
}

#[no_mangle]
pub extern "C" fn xpmem_ap_hashtable_index(apid: CLong) -> CInt {
    xpmem_id_wrapper_bug_on((apid <= 0) as CInt);
    let index = xpmem_ap_hashtable_index_result(apid);
    xpmem_ap_hashtable_index_log(apid, index);
    index
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_make_id_result(tgid: CInt, uniq: CInt, idp: *mut CLong) -> CInt {
    if uniq > XPMEM_MAX_UNIQ_ID {
        return -EBUSY;
    }

    let id = ((uniq as u32 as u64) << 32) | (tgid as u32 as u64);
    write(idp, id as CLong);
    0
}

#[no_mangle]
pub extern "C" fn xpmem_positive_id_result(id: CLong) -> CInt {
    if id <= 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_owner_policy_result(current_pid: CInt, owner_tgid: CInt) -> CInt {
    if current_pid != owner_tgid {
        -EACCES
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_make_initial_policy_result(
    permit_type: CInt,
    permit_value: CULong,
    size: SizeT,
) -> CInt {
    if permit_type != XPMEM_PERMIT_MODE || (permit_value & !0o777) != 0 || size == 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_make_alignment_result(vaddr: CULong, size: SizeT) -> CInt {
    if offset_in_page(vaddr) != 0 || (offset_in_page(size as CULong) != 0 && size != SizeT::MAX) {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_get_policy_result(
    segid: CLong,
    flags: CInt,
    permit_type: CInt,
    has_permit_value: CInt,
) -> CInt {
    if segid <= 0 {
        return -EINVAL;
    }

    if (flags & !(XPMEM_RDONLY | XPMEM_RDWR)) != 0
        || (flags & (XPMEM_RDONLY | XPMEM_RDWR)) == (XPMEM_RDONLY | XPMEM_RDWR)
    {
        return -EINVAL;
    }

    if permit_type != XPMEM_PERMIT_MODE || has_permit_value != 0 {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn xpmem_perms_result(
    perm_uid: CInt,
    perm_gid: CInt,
    perm_mode: CULong,
    flag: CInt,
    current_ruid: CInt,
    current_rgid: CInt,
) -> CInt {
    xpmem_perms_inner(
        perm_uid,
        perm_gid,
        perm_mode,
        flag,
        current_ruid,
        current_rgid,
    )
}

#[no_mangle]
pub extern "C" fn xpmem_check_permit_mode_result(
    flags: CInt,
    seg_uid: CInt,
    seg_gid: CInt,
    seg_mode: CULong,
    current_ruid: CInt,
    current_rgid: CInt,
) -> CInt {
    let ret = xpmem_perms_inner(
        seg_uid,
        seg_gid,
        seg_mode,
        XPMEM_PERM_IRUSR,
        current_ruid,
        current_rgid,
    );
    if ret == 0 && (flags & XPMEM_RDWR) != 0 {
        xpmem_perms_inner(
            seg_uid,
            seg_gid,
            seg_mode,
            XPMEM_PERM_IWUSR,
            current_ruid,
            current_rgid,
        )
    } else {
        ret
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_attach_initial_policy_result(
    apid: CLong,
    offset: OffT,
    vaddr: CULong,
    size: SizeT,
    fjmpi_workaround: CInt,
    adjusted_sizep: *mut SizeT,
) -> CInt {
    if apid <= 0 {
        return -EINVAL;
    }

    if offset_in_page(vaddr) != 0 || offset_in_page(offset as CULong) != 0 {
        return -EINVAL;
    }

    let adjusted = if fjmpi_workaround != 0 {
        size & !(PAGE_SIZE as SizeT - 1)
    } else {
        let offset = offset_in_page(size as CULong) as SizeT;
        if offset != 0 {
            size.wrapping_add(PAGE_SIZE as SizeT - offset)
        } else {
            size
        }
    };

    write(adjusted_sizep, adjusted);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_validate_access_result(
    current_pid: CInt,
    ap_tgid: CInt,
    ap_mode: CInt,
    seg_vaddr: CULong,
    seg_size: SizeT,
    offset: CLong,
    size: SizeT,
    mode: CInt,
    vaddrp: *mut CULong,
) -> CInt {
    if current_pid != ap_tgid || (mode == XPMEM_RDWR && ap_mode == XPMEM_RDONLY) {
        return -EACCES;
    }

    if offset < 0
        || size == 0
        || (offset as CULong).wrapping_add(size as CULong) > seg_size as CULong
    {
        return -EINVAL;
    }

    write(vaddrp, seg_vaddr.wrapping_add(offset as CULong));
    0
}

#[no_mangle]
pub extern "C" fn xpmem_destroying_state_result(flags: CInt, return_destroying: CInt) -> CInt {
    if (flags & XPMEM_FLAG_DESTROYING) != 0 && return_destroying == 0 {
        0
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn xpmem_is_destroying_result(flags: CInt) -> CInt {
    if (flags & XPMEM_FLAG_DESTROYING) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_destroying_error_result(flags: CInt, error: CInt) -> CInt {
    if (flags & XPMEM_FLAG_DESTROYING) != 0 {
        error
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_two_destroying_error_result(
    first_flags: CInt,
    second_flags: CInt,
    error: CInt,
) -> CInt {
    if ((first_flags | second_flags) & XPMEM_FLAG_DESTROYING) != 0 {
        error
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_three_destroying_error_result(
    first_flags: CInt,
    second_flags: CInt,
    third_flags: CInt,
    error: CInt,
) -> CInt {
    if ((first_flags | second_flags | third_flags) & XPMEM_FLAG_DESTROYING) != 0 {
        error
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_pin_page_body_result(
    tg: *mut c_void,
    _src_thread: *mut c_void,
    src_vm: *mut c_void,
    current_vm: *mut c_void,
    vaddr: CULong,
    page_in: CInt,
    offsets: *const XpmemPinPageOffsets,
    read_lock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    read_unlock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    lookup_range_fn: Option<XpmemLookupRangeFn>,
    page_fault_vm_fn: Option<XpmemPageFaultVmFn>,
    page_fault_range_fn: Option<XpmemPageFaultRangeFn>,
    atomic_inc_fn: Option<XpmemAtomicIncFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(read_lock_noirq_fn) = read_lock_noirq_fn else {
        return -EINVAL;
    };
    let Some(read_unlock_noirq_fn) = read_unlock_noirq_fn else {
        return -EINVAL;
    };
    let Some(lookup_range_fn) = lookup_range_fn else {
        return -EINVAL;
    };
    let Some(page_fault_vm_fn) = page_fault_vm_fn else {
        return -EINVAL;
    };
    let Some(page_fault_range_fn) = page_fault_range_fn else {
        return -EINVAL;
    };
    let Some(atomic_inc_fn) = atomic_inc_fn else {
        return -EINVAL;
    };
    if tg.is_null() || src_vm.is_null() {
        return -EINVAL;
    }

    let reason = PF_POPULATE | PF_WRITE | PF_USER;
    loop {
        let remote = current_vm != src_vm;
        let range_lock = field_ptr::<c_void>(src_vm, offsets.vm_memory_range_lock_offset);
        if remote {
            read_lock_noirq_fn(range_lock);
        }

        let range = lookup_range_fn(src_vm, vaddr, vaddr.wrapping_add(1));
        let missing_range = if range.is_null() {
            true
        } else {
            *field_ptr::<CULong>(range, offsets.range_start_offset) > vaddr
        };
        if missing_range {
            if remote {
                read_unlock_noirq_fn(range_lock);
            }

            let stack_start = *field_ptr::<CULong>(src_vm, offsets.vm_stack_start_offset);
            let stack_end = *field_ptr::<CULong>(src_vm, offsets.vm_stack_end_offset);
            if stack_start <= vaddr && stack_end > vaddr {
                if page_fault_vm_fn(src_vm, vaddr, reason) < 0 {
                    return -ENOENT;
                }
                continue;
            }

            return -ENOENT;
        }

        if !(*field_ptr::<*mut c_void>(range, offsets.range_private_data_offset)).is_null() {
            if remote {
                read_unlock_noirq_fn(range_lock);
            }
            return -ENOENT;
        }

        let mut ret = 0;
        if page_in != 0 {
            ret = page_fault_range_fn(src_vm, range, vaddr, reason);
            if ret == 0 {
                atomic_inc_fn(field_ptr::<c_void>(tg, offsets.tg_n_pinned_offset));
            }
        }

        if remote {
            read_unlock_noirq_fn(range_lock);
        }
        return ret;
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_ensure_valid_page_body_result(
    seg: *mut c_void,
    vaddr: CULong,
    page_in: CInt,
    offsets: *const XpmemEnsureValidPageOffsets,
    pin_page_fn: Option<XpmemPinPageFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(pin_page_fn) = pin_page_fn else {
        return -EINVAL;
    };
    if seg.is_null() {
        return -EINVAL;
    }

    let flags = *field_ptr::<CInt>(seg, offsets.seg_flags_offset);
    let ret = xpmem_destroying_error_result(flags, -ENOENT);
    if ret != 0 {
        return ret;
    }

    let tg = *field_ptr::<*mut c_void>(seg, offsets.seg_tg_offset);
    if tg.is_null() {
        return -EINVAL;
    }
    let src_thread = *field_ptr::<*mut c_void>(tg, offsets.tg_group_leader_offset);
    let src_vm = *field_ptr::<*mut c_void>(tg, offsets.tg_vm_offset);
    pin_page_fn(tg, src_thread, src_vm, vaddr, page_in)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_vaddr_to_pte_body_result(
    vm: *mut c_void,
    vaddr: CULong,
    pgsizep: *mut SizeT,
    offsets: *const XpmemVaddrToPteOffsets,
    lookup_range_fn: Option<XpmemLookupRangeFn>,
    pt_lookup_pte_fn: Option<XpmemPtLookupPteFn>,
) -> *mut c_void {
    let Some(offsets) = offsets.as_ref() else {
        return core::ptr::null_mut();
    };
    let Some(lookup_range_fn) = lookup_range_fn else {
        return core::ptr::null_mut();
    };
    let Some(pt_lookup_pte_fn) = pt_lookup_pte_fn else {
        return core::ptr::null_mut();
    };
    if vm.is_null() || pgsizep.is_null() {
        return core::ptr::null_mut();
    }

    let range = lookup_range_fn(vm, vaddr, vaddr.wrapping_add(1));
    if range.is_null() {
        return core::ptr::null_mut();
    }

    let address_space = *field_ptr::<*mut c_void>(vm, offsets.vm_address_space_offset);
    if address_space.is_null() {
        return core::ptr::null_mut();
    }
    let page_table =
        *field_ptr::<*mut c_void>(address_space, offsets.address_space_page_table_offset);
    let pgshift = *field_ptr::<CInt>(range, offsets.range_pgshift_offset);
    let mut base: *mut c_void = core::ptr::null_mut();
    let mut size: SizeT = 0;
    let mut p2align: CInt = 0;
    let pte = pt_lookup_pte_fn(
        page_table,
        vaddr,
        pgshift,
        &mut base,
        &mut size,
        &mut p2align,
    );
    if pte.is_null() {
        write(pgsizep, PAGE_SIZE as SizeT);
    } else {
        write(pgsizep, size);
    }
    pte
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_unpin_pages_body_result(
    seg: *mut c_void,
    vm: *mut c_void,
    vaddr: CULong,
    size: SizeT,
    offsets: *const XpmemUnpinPagesOffsets,
    vaddr_to_pte_fn: Option<XpmemVaddrToPteFn>,
    pte_present_fn: Option<XpmemPtePresentFn>,
    atomic_sub_fn: Option<XpmemAtomicSubFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(vaddr_to_pte_fn) = vaddr_to_pte_fn else {
        return -EINVAL;
    };
    let Some(pte_present_fn) = pte_present_fn else {
        return -EINVAL;
    };
    let Some(atomic_sub_fn) = atomic_sub_fn else {
        return -EINVAL;
    };
    if seg.is_null() || vm.is_null() {
        return -EINVAL;
    }

    let mut n_pgs_unpinned: CInt = 0;
    let end = vaddr.wrapping_add(size as CULong);
    let mut cur = vaddr & PAGE_MASK;
    let mut vsize: SizeT = 0;
    while cur < end {
        let pte = vaddr_to_pte_fn(vm, cur, &mut vsize);
        let has_present_pte = if !pte.is_null() && pte_present_fn(pte) != 0 {
            1
        } else {
            0
        };
        let mut next_vaddr = 0;
        let mut unpinned = 0;
        xpmem_unpin_step_result(cur, vsize, has_present_pte, &mut next_vaddr, &mut unpinned);
        if unpinned != 0 {
            n_pgs_unpinned += 1;
        }
        cur = next_vaddr;
    }

    let tg = *field_ptr::<*mut c_void>(seg, offsets.seg_tg_offset);
    if tg.is_null() {
        return -EINVAL;
    }
    atomic_sub_fn(
        n_pgs_unpinned,
        field_ptr::<c_void>(tg, offsets.tg_n_pinned_offset),
    );
    n_pgs_unpinned
}

#[no_mangle]
pub extern "C" fn xpmem_attach_destroying_result(seg_flags: CInt, seg_tg_flags: CInt) -> CInt {
    if ((seg_flags | seg_tg_flags) & XPMEM_FLAG_DESTROYING) != 0 {
        -ENOENT
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_close_decision_result(
    n_opened: CInt,
    has_data: CInt,
    flush_objectsp: *mut CInt,
    exit_partitionp: *mut CInt,
) -> CInt {
    write(flush_objectsp, if has_data != 0 { 1 } else { 0 });
    write(exit_partitionp, if n_opened == 0 { 1 } else { 0 });
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_open_body_result(
    syscall_num: CInt,
    pathname: *const u8,
    flags: CInt,
    ctx: *mut c_void,
    partp: *mut *mut c_void,
    proc: *mut c_void,
    offsets: *const XpmemOpenOffsets,
    ioctl_cb_addr: CULong,
    close_cb_addr: CULong,
    dup_cb_addr: CULong,
    init_fn: Option<XpmemInitFn>,
    forward_fn: Option<XpmemForwardFn>,
    open_fn: Option<XpmemOpenFn>,
    alloc_fn: Option<XpmemAllocFn>,
    lock_fn: Option<XpmemLockFn>,
    unlock_fn: Option<XpmemUnlockFn>,
    atomic_inc_fn: Option<XpmemAtomicIncFn>,
    log_fn: Option<XpmemOpenLogFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(init_fn) = init_fn else {
        return -EINVAL;
    };
    let Some(forward_fn) = forward_fn else {
        return -EINVAL;
    };
    let Some(open_fn) = open_fn else {
        return -EINVAL;
    };
    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(atomic_inc_fn) = atomic_inc_fn else {
        return -EINVAL;
    };
    if partp.is_null() || proc.is_null() {
        return -EINVAL;
    }

    if let Some(log_fn) = log_fn {
        log_fn(
            XPMEM_OPEN_LOG_CALL,
            syscall_num,
            pathname,
            flags,
            0,
            core::ptr::null_mut(),
        );
    }

    if (*partp).is_null() {
        let ret = init_fn();
        if ret != 0 {
            return ret;
        }
    }

    let fd_long = forward_fn(syscall_num, ctx);
    if fd_long < 0 {
        if let Some(log_fn) = log_fn {
            log_fn(
                XPMEM_OPEN_LOG_SYSCALL_ERROR,
                syscall_num,
                pathname,
                flags,
                fd_long,
                core::ptr::null_mut(),
            );
        }
        return fd_long as CInt;
    }
    let fd = fd_long as CInt;

    let ret = open_fn();
    if ret != 0 {
        if let Some(log_fn) = log_fn {
            log_fn(
                XPMEM_OPEN_LOG_OPEN_ERROR,
                syscall_num,
                pathname,
                flags,
                ret as CLong,
                core::ptr::null_mut(),
            );
        }
        return ret;
    }

    let mckfd = alloc_fn(offsets.mckfd_size);
    if mckfd.is_null() {
        return -ENOMEM;
    }
    write_bytes(mckfd.cast::<u8>(), 0, offsets.mckfd_size);
    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_OPEN_LOG_ALLOC, syscall_num, pathname, flags, 0, mckfd);
    }

    write(field_ptr::<CInt>(mckfd, offsets.mckfd_fd_offset), fd);
    write(field_ptr::<CInt>(mckfd, offsets.mckfd_sig_no_offset), -1);
    write(
        field_ptr::<CLong>(mckfd, offsets.mckfd_data_offset),
        proc as CLong,
    );
    write(
        field_ptr::<CULong>(mckfd, offsets.mckfd_ioctl_cb_offset),
        ioctl_cb_addr,
    );
    write(
        field_ptr::<CULong>(mckfd, offsets.mckfd_close_cb_offset),
        close_cb_addr,
    );
    write(
        field_ptr::<CULong>(mckfd, offsets.mckfd_dup_cb_offset),
        dup_cb_addr,
    );

    let lock = field_ptr::<c_void>(proc, offsets.proc_mckfd_lock_offset);
    let headp = field_ptr::<*mut c_void>(proc, offsets.proc_mckfd_offset);
    let irqstate = lock_fn(lock);
    let old_head = *headp;
    write(
        field_ptr::<*mut c_void>(mckfd, offsets.mckfd_next_offset),
        old_head,
    );
    write(headp, mckfd);
    unlock_fn(lock, irqstate);

    let part = *partp;
    if part.is_null() {
        return -EINVAL;
    }
    let n_opened = atomic_inc_fn(field_ptr::<c_void>(part, offsets.part_n_opened_offset));
    if let Some(log_fn) = log_fn {
        log_fn(
            XPMEM_OPEN_LOG_N_OPENED,
            syscall_num,
            pathname,
            flags,
            n_opened as CLong,
            core::ptr::null_mut(),
        );
        log_fn(
            XPMEM_OPEN_LOG_RETURN,
            syscall_num,
            pathname,
            flags,
            fd as CLong,
            core::ptr::null_mut(),
        );
    }

    fd
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_ioctl_body_result(
    mckfd: *mut c_void,
    cmd: CULong,
    arg: CULong,
    offsets: *const XpmemIoctlOffsets,
    copy_from_user_fn: Option<XpmemCopyFromUserFn>,
    copy_to_user_fn: Option<XpmemCopyToUserFn>,
    make_fn: Option<XpmemMakeFn>,
    remove_fn: Option<XpmemRemoveFn>,
    get_fn: Option<XpmemGetFn>,
    release_fn: Option<XpmemReleaseFn>,
    attach_fn: Option<XpmemAttachFn>,
    detach_fn: Option<XpmemDetachFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(copy_from_user_fn),
        Some(copy_to_user_fn),
        Some(make_fn),
        Some(remove_fn),
        Some(get_fn),
        Some(release_fn),
        Some(attach_fn),
        Some(detach_fn),
    ) = (
        copy_from_user_fn,
        copy_to_user_fn,
        make_fn,
        remove_fn,
        get_fn,
        release_fn,
        attach_fn,
        detach_fn,
    )
    else {
        return -EINVAL;
    };
    if mckfd.is_null() {
        return -EINVAL;
    }

    let mut storage = core::mem::MaybeUninit::<[usize; 16]>::uninit();
    let buf = storage.as_mut_ptr().cast::<c_void>();
    let cap = core::mem::size_of::<[usize; 16]>();

    if cmd == offsets.cmd_version {
        return offsets.current_version;
    }

    if cmd == offsets.cmd_make {
        if offsets.make_size > cap {
            return -EINVAL;
        }
        if copy_from_user_fn(buf, arg, offsets.make_size) != 0 {
            return -EFAULT;
        }
        let mut segid: CLong = 0;
        let ret = make_fn(
            *field_ptr::<CULong>(buf, offsets.make_vaddr_offset),
            *field_ptr::<SizeT>(buf, offsets.make_size_offset),
            *field_ptr::<CInt>(buf, offsets.make_permit_type_offset),
            (*field_ptr::<CULong>(buf, offsets.make_permit_value_offset) as usize) as *mut c_void,
            &mut segid,
        );
        if ret != 0 {
            return ret;
        }
        if copy_to_user_fn(
            arg.wrapping_add(offsets.make_segid_offset as CULong),
            (&segid as *const CLong).cast::<c_void>(),
            core::mem::size_of::<CLong>(),
        ) != 0
        {
            let _ = remove_fn(segid);
            return -EFAULT;
        }
        return ret;
    }

    if cmd == offsets.cmd_remove {
        if offsets.remove_size > cap {
            return -EINVAL;
        }
        if copy_from_user_fn(buf, arg, offsets.remove_size) != 0 {
            return -EFAULT;
        }
        return remove_fn(*field_ptr::<CLong>(buf, offsets.remove_segid_offset));
    }

    if cmd == offsets.cmd_get {
        if offsets.get_size > cap {
            return -EINVAL;
        }
        if copy_from_user_fn(buf, arg, offsets.get_size) != 0 {
            return -EFAULT;
        }
        let mut apid: CLong = 0;
        let ret = get_fn(
            *field_ptr::<CLong>(buf, offsets.get_segid_offset),
            *field_ptr::<CInt>(buf, offsets.get_flags_offset),
            *field_ptr::<CInt>(buf, offsets.get_permit_type_offset),
            (*field_ptr::<CULong>(buf, offsets.get_permit_value_offset) as usize) as *mut c_void,
            &mut apid,
        );
        if ret != 0 {
            return ret;
        }
        if copy_to_user_fn(
            arg.wrapping_add(offsets.get_apid_offset as CULong),
            (&apid as *const CLong).cast::<c_void>(),
            core::mem::size_of::<CLong>(),
        ) != 0
        {
            let _ = release_fn(apid);
            return -EFAULT;
        }
        return ret;
    }

    if cmd == offsets.cmd_release {
        if offsets.release_size > cap {
            return -EINVAL;
        }
        if copy_from_user_fn(buf, arg, offsets.release_size) != 0 {
            return -EFAULT;
        }
        return release_fn(*field_ptr::<CLong>(buf, offsets.release_apid_offset));
    }

    if cmd == offsets.cmd_attach {
        if offsets.attach_size > cap {
            return -EINVAL;
        }
        if copy_from_user_fn(buf, arg, offsets.attach_size) != 0 {
            return -EFAULT;
        }
        let mut at_vaddr: CULong = 0;
        let ret = attach_fn(
            mckfd,
            *field_ptr::<CLong>(buf, offsets.attach_apid_offset),
            *field_ptr::<OffT>(buf, offsets.attach_offset_offset),
            *field_ptr::<SizeT>(buf, offsets.attach_size_offset),
            *field_ptr::<CULong>(buf, offsets.attach_vaddr_offset),
            *field_ptr::<CInt>(buf, offsets.attach_fd_offset),
            *field_ptr::<CInt>(buf, offsets.attach_flags_offset),
            &mut at_vaddr,
        );
        if ret != 0 {
            return ret;
        }
        if copy_to_user_fn(
            arg.wrapping_add(offsets.attach_vaddr_offset as CULong),
            (&at_vaddr as *const CULong).cast::<c_void>(),
            core::mem::size_of::<CULong>(),
        ) != 0
        {
            let _ = detach_fn(at_vaddr);
            return -EFAULT;
        }
        return ret;
    }

    if cmd == offsets.cmd_detach {
        if offsets.detach_size > cap {
            return -EINVAL;
        }
        if copy_from_user_fn(buf, arg, offsets.detach_size) != 0 {
            return -EFAULT;
        }
        return detach_fn(*field_ptr::<CULong>(buf, offsets.detach_vaddr_offset));
    }

    -EINVAL
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_dup_body_result(
    mckfd: *mut c_void,
    partp: *mut *mut c_void,
    offsets: *const XpmemCloseOffsets,
    atomic_inc_fn: Option<XpmemAtomicIncFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(atomic_inc_fn) = atomic_inc_fn else {
        return -EINVAL;
    };
    if mckfd.is_null() || partp.is_null() {
        return -EINVAL;
    }
    let part = *partp;
    if part.is_null() {
        return -EINVAL;
    }

    write(field_ptr::<CLong>(mckfd, offsets.mckfd_data_offset), 0);
    atomic_inc_fn(field_ptr::<c_void>(part, offsets.part_n_opened_offset));
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_close_body_result(
    mckfd: *mut c_void,
    partp: *mut *mut c_void,
    offsets: *const XpmemCloseOffsets,
    atomic_dec_fn: Option<XpmemAtomicDecFn>,
    flush_fn: Option<XpmemMckfdVoidFn>,
    exit_fn: Option<XpmemVoidFn>,
    log_fn: Option<XpmemCloseLogFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(atomic_dec_fn) = atomic_dec_fn else {
        return -EINVAL;
    };
    if mckfd.is_null() || partp.is_null() {
        return -EINVAL;
    }
    let part = *partp;
    if part.is_null() {
        return -EINVAL;
    }

    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_CLOSE_LOG_CALL, mckfd, 0);
    }

    let n_opened = atomic_dec_fn(field_ptr::<c_void>(part, offsets.part_n_opened_offset));
    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_CLOSE_LOG_N_OPENED, mckfd, n_opened);
    }

    let has_data = *field_ptr::<CLong>(mckfd, offsets.mckfd_data_offset) != 0;
    if has_data {
        if let Some(flush_fn) = flush_fn {
            flush_fn(mckfd);
        } else {
            return -EINVAL;
        }
    }

    if n_opened == 0 {
        if let Some(exit_fn) = exit_fn {
            exit_fn();
        } else {
            return -EINVAL;
        }
    }

    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_CLOSE_LOG_RETURN, mckfd, 0);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_partition_init_body_result(
    partp: *mut *mut c_void,
    offsets: *const XpmemPartitionOffsets,
    alloc_fn: Option<XpmemAllocFn>,
    rwlock_init_fn: Option<XpmemObjectVoidFn>,
    list_init_fn: Option<XpmemObjectVoidFn>,
    atomic_set_fn: Option<XpmemAtomicSetFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };
    let Some(rwlock_init_fn) = rwlock_init_fn else {
        return -EINVAL;
    };
    let Some(list_init_fn) = list_init_fn else {
        return -EINVAL;
    };
    let Some(atomic_set_fn) = atomic_set_fn else {
        return -EINVAL;
    };
    if partp.is_null() {
        return -EINVAL;
    }

    let part = alloc_fn(offsets.part_size);
    if part.is_null() {
        return -ENOMEM;
    }
    write_bytes(part, 0, offsets.part_size);

    for index in 0..XPMEM_TG_HASHTABLE_SIZE as SizeT {
        let hashlist = (part as *mut u8)
            .add(offsets.part_tg_hashtable_offset)
            .add(index * offsets.hashlist_stride)
            .cast::<c_void>();
        rwlock_init_fn(field_ptr::<c_void>(hashlist, offsets.hashlist_lock_offset));
        list_init_fn(field_ptr::<c_void>(hashlist, offsets.hashlist_list_offset));
    }

    atomic_set_fn(field_ptr::<c_void>(part, offsets.part_n_opened_offset), 0);
    write(partp, part);

    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_partition_exit_body_result(
    partp: *mut *mut c_void,
    free_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    if partp.is_null() {
        return -EINVAL;
    }

    let part = *partp;
    if !part.is_null() {
        free_fn(part);
        write(partp, core::ptr::null_mut());
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_open_tg_body_result(
    partp: *mut *mut c_void,
    current_thread: *mut c_void,
    current_proc: *mut c_void,
    current_vm: *mut c_void,
    offsets: *const XpmemOpenTgOffsets,
    rwlock_node: *mut c_void,
    tg_ref_fn: Option<XpmemTgRefFn>,
    tg_deref_fn: Option<XpmemObjectVoidFn>,
    alloc_fn: Option<XpmemAllocFn>,
    spinlock_init_fn: Option<XpmemObjectVoidFn>,
    rwlock_init_fn: Option<XpmemObjectVoidFn>,
    list_init_fn: Option<XpmemObjectVoidFn>,
    atomic_set_fn: Option<XpmemAtomicSetFn>,
    tg_not_destroyable_fn: Option<XpmemObjectVoidFn>,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    list_add_tail_fn: Option<XpmemListAddTailFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(tg_ref_fn) = tg_ref_fn else {
        return -EINVAL;
    };
    let Some(tg_deref_fn) = tg_deref_fn else {
        return -EINVAL;
    };
    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };
    let Some(spinlock_init_fn) = spinlock_init_fn else {
        return -EINVAL;
    };
    let Some(rwlock_init_fn) = rwlock_init_fn else {
        return -EINVAL;
    };
    let Some(list_init_fn) = list_init_fn else {
        return -EINVAL;
    };
    let Some(atomic_set_fn) = atomic_set_fn else {
        return -EINVAL;
    };
    let Some(tg_not_destroyable_fn) = tg_not_destroyable_fn else {
        return -EINVAL;
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return -EINVAL;
    };
    let Some(list_add_tail_fn) = list_add_tail_fn else {
        return -EINVAL;
    };
    if partp.is_null() || current_proc.is_null() || rwlock_node.is_null() {
        return -EINVAL;
    }
    let part = *partp;
    if part.is_null() {
        return -EINVAL;
    }

    let pid = *field_ptr::<CInt>(current_proc, offsets.proc_pid_offset);
    let existing = tg_ref_fn(pid);
    if !ptr_is_err(existing) && !existing.is_null() {
        tg_deref_fn(existing);
        return 0;
    }

    let tg = alloc_fn(offsets.tg_size);
    if tg.is_null() {
        return -ENOMEM;
    }
    write_bytes(tg, 0, offsets.tg_size);

    spinlock_init_fn(field_ptr::<c_void>(tg, offsets.tg_lock_offset));
    *field_ptr::<CInt>(tg, offsets.tg_tgid_offset) = pid;
    *field_ptr::<CInt>(tg, offsets.tg_uid_offset) =
        *field_ptr::<CInt>(current_proc, offsets.proc_ruid_offset);
    *field_ptr::<CInt>(tg, offsets.tg_gid_offset) =
        *field_ptr::<CInt>(current_proc, offsets.proc_rgid_offset);
    atomic_set_fn(field_ptr::<c_void>(tg, offsets.tg_uniq_segid_offset), 0);
    atomic_set_fn(field_ptr::<c_void>(tg, offsets.tg_uniq_apid_offset), 0);
    rwlock_init_fn(field_ptr::<c_void>(tg, offsets.tg_seg_list_lock_offset));
    list_init_fn(field_ptr::<c_void>(tg, offsets.tg_seg_list_offset));
    atomic_set_fn(field_ptr::<c_void>(tg, offsets.tg_n_pinned_offset), 0);
    list_init_fn(field_ptr::<c_void>(tg, offsets.tg_tg_hashlist_offset));
    *field_ptr::<*mut c_void>(tg, offsets.tg_vm_offset) = current_vm;

    for index in 0..XPMEM_AP_HASHTABLE_SIZE as SizeT {
        let hashlist = (tg as *mut u8)
            .add(offsets.tg_ap_hashtable_offset)
            .add(index * offsets.hashlist_stride)
            .cast::<c_void>();
        rwlock_init_fn(field_ptr::<c_void>(hashlist, offsets.hashlist_lock_offset));
        list_init_fn(field_ptr::<c_void>(hashlist, offsets.hashlist_list_offset));
    }

    tg_not_destroyable_fn(tg);

    let index = xpmem_tg_hashtable_index_result(pid) as SizeT;
    let hashlist = (part as *mut u8)
        .add(offsets.part_tg_hashtable_offset)
        .add(index * offsets.hashlist_stride)
        .cast::<c_void>();
    let hash_lock = field_ptr::<c_void>(hashlist, offsets.hashlist_lock_offset);
    rwlock_lock_fn(hash_lock, rwlock_node);
    list_add_tail_fn(
        field_ptr::<c_void>(tg, offsets.tg_tg_hashlist_offset),
        field_ptr::<c_void>(hashlist, offsets.hashlist_list_offset),
    );
    rwlock_unlock_fn(hash_lock, rwlock_node);

    *field_ptr::<*mut c_void>(tg, offsets.tg_group_leader_offset) = current_thread;

    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_flush_body_result(
    mckfd: *mut c_void,
    partp: *mut *mut c_void,
    offsets: *const XpmemFlushOffsets,
    rwlock_node: *mut c_void,
    tg_ref_fn: Option<XpmemTgRefFn>,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    list_del_init_fn: Option<XpmemListFn>,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    release_aps_fn: Option<XpmemTgVoidFn>,
    remove_segs_fn: Option<XpmemTgVoidFn>,
    destroy_tg_fn: Option<XpmemTgVoidFn>,
    log_fn: Option<XpmemFlushLogFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(tg_ref_fn) = tg_ref_fn else {
        return -EINVAL;
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return -EINVAL;
    };
    let Some(list_del_init_fn) = list_del_init_fn else {
        return -EINVAL;
    };
    let Some(spin_lock_fn) = spin_lock_fn else {
        return -EINVAL;
    };
    let Some(spin_unlock_fn) = spin_unlock_fn else {
        return -EINVAL;
    };
    let Some(release_aps_fn) = release_aps_fn else {
        return -EINVAL;
    };
    let Some(remove_segs_fn) = remove_segs_fn else {
        return -EINVAL;
    };
    let Some(destroy_tg_fn) = destroy_tg_fn else {
        return -EINVAL;
    };
    if mckfd.is_null() || partp.is_null() || rwlock_node.is_null() {
        return -EINVAL;
    }
    let part = *partp;
    if part.is_null() {
        return -EINVAL;
    }
    let proc = *field_ptr::<*mut c_void>(mckfd, offsets.mckfd_data_offset);
    if proc.is_null() {
        return -EINVAL;
    }

    let pid = *field_ptr::<CInt>(proc, offsets.proc_pid_offset);
    let index = xpmem_tg_hashtable_index_result(pid) as SizeT;
    let hashlist = (part as *mut u8)
        .add(offsets.part_tg_hashtable_offset)
        .add(index * offsets.hashlist_stride)
        .cast::<c_void>();
    let hash_lock = field_ptr::<c_void>(hashlist, offsets.hashlist_lock_offset);
    rwlock_lock_fn(hash_lock, rwlock_node);

    let tg = tg_ref_fn(pid);
    if tg.is_null() || ptr_is_err(tg) {
        rwlock_unlock_fn(hash_lock, rwlock_node);
        return 0;
    }

    list_del_init_fn(field_ptr::<c_void>(tg, offsets.tg_hashlist_offset));
    rwlock_unlock_fn(hash_lock, rwlock_node);

    if let Some(log_fn) = log_fn {
        let vm = *field_ptr::<*mut c_void>(tg, offsets.tg_vm_offset);
        log_fn(XPMEM_FLUSH_LOG_TG_VM, tg, vm as CLong);
    }

    let tg_lock = field_ptr::<c_void>(tg, offsets.tg_lock_offset);
    let flags_ptr = field_ptr::<CInt>(tg, offsets.tg_flags_offset);
    let mut new_flags = 0;
    spin_lock_fn(tg_lock);
    let _ = xpmem_begin_destroy_result(*flags_ptr, &mut new_flags);
    write(flags_ptr, new_flags);
    spin_unlock_fn(tg_lock);

    release_aps_fn(tg);
    remove_segs_fn(tg);

    spin_lock_fn(tg_lock);
    write(flags_ptr, xpmem_finish_destroy_result(*flags_ptr));
    spin_unlock_fn(tg_lock);

    destroy_tg_fn(tg);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_seg_body_result(
    seg_tg: *mut c_void,
    seg: *mut c_void,
    offsets: *const XpmemRemoveSegOffsets,
    rwlock_node: *mut c_void,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    clear_ptes_fn: Option<XpmemObjectVoidFn>,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    list_del_init_fn: Option<XpmemListFn>,
    seg_destroyable_fn: Option<XpmemObjectVoidFn>,
    log_fn: Option<XpmemRemoveSegLogFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(spin_lock_fn) = spin_lock_fn else {
        return -EINVAL;
    };
    let Some(spin_unlock_fn) = spin_unlock_fn else {
        return -EINVAL;
    };
    let Some(clear_ptes_fn) = clear_ptes_fn else {
        return -EINVAL;
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return -EINVAL;
    };
    let Some(list_del_init_fn) = list_del_init_fn else {
        return -EINVAL;
    };
    let Some(seg_destroyable_fn) = seg_destroyable_fn else {
        return -EINVAL;
    };
    if seg_tg.is_null() || seg.is_null() || rwlock_node.is_null() {
        return -EINVAL;
    }

    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_REMOVE_SEG_LOG_CALL, seg_tg, seg, 0);
    }

    let seg_lock = field_ptr::<c_void>(seg, offsets.seg_lock_offset);
    let flags_ptr = field_ptr::<CInt>(seg, offsets.seg_flags_offset);
    let mut new_flags = 0;
    spin_lock_fn(seg_lock);
    let should_destroy = xpmem_begin_destroy_result(*flags_ptr, &mut new_flags);
    if should_destroy == 0 {
        spin_unlock_fn(seg_lock);
        return 0;
    }
    write(flags_ptr, new_flags);
    spin_unlock_fn(seg_lock);

    clear_ptes_fn(seg);

    spin_lock_fn(seg_lock);
    write(flags_ptr, xpmem_finish_destroy_result(*flags_ptr));
    spin_unlock_fn(seg_lock);

    let seg_list_lock = field_ptr::<c_void>(seg_tg, offsets.tg_seg_list_lock_offset);
    rwlock_lock_fn(seg_list_lock, rwlock_node);
    list_del_init_fn(field_ptr::<c_void>(seg, offsets.seg_list_offset));
    rwlock_unlock_fn(seg_list_lock, rwlock_node);

    seg_destroyable_fn(seg);

    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_REMOVE_SEG_LOG_RETURN, seg_tg, seg, 0);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_segs_of_tg_body_result(
    seg_tg: *mut c_void,
    offsets: *const XpmemRemoveSegsOffsets,
    rwlock_node: *mut c_void,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    seg_ref_fn: Option<XpmemObjectVoidFn>,
    remove_seg_fn: Option<XpmemRemoveSegFn>,
    seg_deref_fn: Option<XpmemObjectVoidFn>,
    log_fn: Option<XpmemRemoveSegsLogFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return -EINVAL;
    };
    let Some(seg_ref_fn) = seg_ref_fn else {
        return -EINVAL;
    };
    let Some(remove_seg_fn) = remove_seg_fn else {
        return -EINVAL;
    };
    let Some(seg_deref_fn) = seg_deref_fn else {
        return -EINVAL;
    };
    if seg_tg.is_null() || rwlock_node.is_null() {
        return -EINVAL;
    }

    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_REMOVE_SEGS_LOG_CALL, seg_tg, core::ptr::null_mut(), 0);
    }

    let seg_list_lock = field_ptr::<c_void>(seg_tg, offsets.tg_seg_list_lock_offset);
    let seg_list_head = field_ptr::<c_void>(seg_tg, offsets.tg_seg_list_offset);

    rwlock_lock_fn(seg_list_lock, rwlock_node);
    loop {
        let next = *(seg_list_head as *mut *mut c_void);
        if next == seg_list_head {
            break;
        }

        let seg = (next as *mut u8)
            .sub(offsets.seg_list_offset)
            .cast::<c_void>();
        seg_ref_fn(seg);
        rwlock_unlock_fn(seg_list_lock, rwlock_node);

        remove_seg_fn(seg_tg, seg);
        seg_deref_fn(seg);

        rwlock_lock_fn(seg_list_lock, rwlock_node);
    }
    rwlock_unlock_fn(seg_list_lock, rwlock_node);

    if let Some(log_fn) = log_fn {
        log_fn(
            XPMEM_REMOVE_SEGS_LOG_RETURN,
            seg_tg,
            core::ptr::null_mut(),
            0,
        );
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_release_ap_body_result(
    ap_tg: *mut c_void,
    ap: *mut c_void,
    offsets: *const XpmemReleaseApOffsets,
    rwlock_node: *mut c_void,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    list_del_init_fn: Option<XpmemListFn>,
    att_ref_fn: Option<XpmemObjectVoidFn>,
    detach_att_fn: Option<XpmemDetachAttFn>,
    att_deref_fn: Option<XpmemObjectVoidFn>,
    seg_deref_fn: Option<XpmemObjectVoidFn>,
    tg_deref_fn: Option<XpmemObjectVoidFn>,
    ap_destroyable_fn: Option<XpmemObjectVoidFn>,
    log_fn: Option<XpmemReleaseApLogFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(spin_lock_fn) = spin_lock_fn else {
        return -EINVAL;
    };
    let Some(spin_unlock_fn) = spin_unlock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return -EINVAL;
    };
    let Some(list_del_init_fn) = list_del_init_fn else {
        return -EINVAL;
    };
    let Some(att_ref_fn) = att_ref_fn else {
        return -EINVAL;
    };
    let Some(detach_att_fn) = detach_att_fn else {
        return -EINVAL;
    };
    let Some(att_deref_fn) = att_deref_fn else {
        return -EINVAL;
    };
    let Some(seg_deref_fn) = seg_deref_fn else {
        return -EINVAL;
    };
    let Some(tg_deref_fn) = tg_deref_fn else {
        return -EINVAL;
    };
    let Some(ap_destroyable_fn) = ap_destroyable_fn else {
        return -EINVAL;
    };
    if ap_tg.is_null() || ap.is_null() || rwlock_node.is_null() {
        return -EINVAL;
    }

    let apid = *field_ptr::<CLong>(ap, offsets.ap_apid_offset);
    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_RELEASE_AP_LOG_CALL, ap_tg, ap, apid);
    }

    let ap_lock = field_ptr::<c_void>(ap, offsets.ap_lock_offset);
    let flags_ptr = field_ptr::<CInt>(ap, offsets.ap_flags_offset);
    let mut new_flags = 0;
    spin_lock_fn(ap_lock);
    let should_destroy = xpmem_begin_destroy_result(*flags_ptr, &mut new_flags);
    if should_destroy == 0 {
        spin_unlock_fn(ap_lock);
        return 0;
    }
    write(flags_ptr, new_flags);

    let att_list_head = field_ptr::<c_void>(ap, offsets.ap_att_list_offset);
    loop {
        let next = *(att_list_head as *mut *mut c_void);
        if next == att_list_head {
            break;
        }

        let att = (next as *mut u8)
            .sub(offsets.att_att_list_offset)
            .cast::<c_void>();
        att_ref_fn(att);
        spin_unlock_fn(ap_lock);

        detach_att_fn(ap, att);
        att_deref_fn(att);

        spin_lock_fn(ap_lock);
    }

    write(flags_ptr, xpmem_finish_destroy_result(*flags_ptr));
    spin_unlock_fn(ap_lock);

    let index = xpmem_ap_hashtable_index_result(apid) as SizeT;
    let hashlist = (ap_tg as *mut u8)
        .add(offsets.tg_ap_hashtable_offset)
        .add(index * offsets.hashlist_stride)
        .cast::<c_void>();
    let hash_lock = field_ptr::<c_void>(hashlist, offsets.hashlist_lock_offset);
    rwlock_lock_fn(hash_lock, rwlock_node);
    list_del_init_fn(field_ptr::<c_void>(ap, offsets.ap_hashlist_offset));
    rwlock_unlock_fn(hash_lock, rwlock_node);

    let seg = *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset);
    if seg.is_null() {
        return -EINVAL;
    }
    let seg_tg = *field_ptr::<*mut c_void>(seg, offsets.seg_tg_offset);
    if seg_tg.is_null() {
        return -EINVAL;
    }

    let seg_lock = field_ptr::<c_void>(seg, offsets.seg_lock_offset);
    spin_lock_fn(seg_lock);
    list_del_init_fn(field_ptr::<c_void>(ap, offsets.ap_ap_list_offset));
    spin_unlock_fn(seg_lock);

    seg_deref_fn(seg);
    tg_deref_fn(seg_tg);
    ap_destroyable_fn(ap);

    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_RELEASE_AP_LOG_RETURN, ap_tg, ap, 0);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_release_aps_of_tg_body_result(
    ap_tg: *mut c_void,
    offsets: *const XpmemReleaseApsOffsets,
    rwlock_node: *mut c_void,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    ap_ref_fn: Option<XpmemObjectVoidFn>,
    release_ap_fn: Option<XpmemRemoveSegFn>,
    ap_deref_fn: Option<XpmemObjectVoidFn>,
    log_fn: Option<XpmemRemoveSegsLogFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return -EINVAL;
    };
    let Some(ap_ref_fn) = ap_ref_fn else {
        return -EINVAL;
    };
    let Some(release_ap_fn) = release_ap_fn else {
        return -EINVAL;
    };
    let Some(ap_deref_fn) = ap_deref_fn else {
        return -EINVAL;
    };
    if ap_tg.is_null() || rwlock_node.is_null() {
        return -EINVAL;
    }

    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_RELEASE_AP_LOG_CALL, ap_tg, core::ptr::null_mut(), 0);
    }

    for index in 0..XPMEM_AP_HASHTABLE_SIZE as SizeT {
        let hashlist = (ap_tg as *mut u8)
            .add(offsets.tg_ap_hashtable_offset)
            .add(index * offsets.hashlist_stride)
            .cast::<c_void>();
        let hash_lock = field_ptr::<c_void>(hashlist, offsets.hashlist_lock_offset);
        let hash_head = field_ptr::<c_void>(hashlist, offsets.hashlist_list_offset);

        rwlock_lock_fn(hash_lock, rwlock_node);
        loop {
            let next = *(hash_head as *mut *mut c_void);
            if next == hash_head {
                break;
            }

            let ap = (next as *mut u8)
                .sub(offsets.ap_hashlist_offset)
                .cast::<c_void>();
            ap_ref_fn(ap);
            rwlock_unlock_fn(hash_lock, rwlock_node);

            release_ap_fn(ap_tg, ap);
            ap_deref_fn(ap);

            rwlock_lock_fn(hash_lock, rwlock_node);
        }
        rwlock_unlock_fn(hash_lock, rwlock_node);
    }

    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_RELEASE_AP_LOG_RETURN, ap_tg, core::ptr::null_mut(), 0);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_destroy_tg_body_result(
    tg: *mut c_void,
    tg_destroyable_fn: Option<XpmemObjectVoidFn>,
    tg_deref_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(tg_destroyable_fn) = tg_destroyable_fn else {
        return -EINVAL;
    };
    let Some(tg_deref_fn) = tg_deref_fn else {
        return -EINVAL;
    };
    if tg.is_null() {
        return -EINVAL;
    }

    tg_destroyable_fn(tg);
    tg_deref_fn(tg);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_body_result(
    segid: CLong,
    current_pid: CInt,
    offsets: *const XpmemTgIdOffsets,
    tg_ref_by_segid_fn: Option<XpmemIdRefFn>,
    seg_ref_by_segid_fn: Option<XpmemRefByIdFn>,
    remove_seg_fn: Option<XpmemRemoveSegFn>,
    seg_deref_fn: Option<XpmemObjectVoidFn>,
    tg_deref_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(tg_ref_by_segid_fn) = tg_ref_by_segid_fn else {
        return -EINVAL;
    };
    let Some(seg_ref_by_segid_fn) = seg_ref_by_segid_fn else {
        return -EINVAL;
    };
    let Some(remove_seg_fn) = remove_seg_fn else {
        return -EINVAL;
    };
    let Some(seg_deref_fn) = seg_deref_fn else {
        return -EINVAL;
    };
    let Some(tg_deref_fn) = tg_deref_fn else {
        return -EINVAL;
    };

    let ret = xpmem_positive_id_result(segid);
    if ret != 0 {
        return ret;
    }

    let seg_tg = tg_ref_by_segid_fn(segid);
    if seg_tg.is_null() || ptr_is_err(seg_tg) {
        return ptr_err(seg_tg);
    }

    let owner_tgid = *field_ptr::<CInt>(seg_tg, offsets.tg_tgid_offset);
    let ret = xpmem_owner_policy_result(current_pid, owner_tgid);
    if ret != 0 {
        tg_deref_fn(seg_tg);
        return ret;
    }

    let seg = seg_ref_by_segid_fn(seg_tg, segid);
    if seg.is_null() || ptr_is_err(seg) {
        tg_deref_fn(seg_tg);
        return ptr_err(seg);
    }

    remove_seg_fn(seg_tg, seg);
    seg_deref_fn(seg);
    tg_deref_fn(seg_tg);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_release_body_result(
    apid: CLong,
    current_pid: CInt,
    offsets: *const XpmemTgIdOffsets,
    tg_ref_by_apid_fn: Option<XpmemIdRefFn>,
    ap_ref_by_apid_fn: Option<XpmemRefByIdFn>,
    release_ap_fn: Option<XpmemRemoveSegFn>,
    ap_deref_fn: Option<XpmemObjectVoidFn>,
    tg_deref_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(tg_ref_by_apid_fn) = tg_ref_by_apid_fn else {
        return -EINVAL;
    };
    let Some(ap_ref_by_apid_fn) = ap_ref_by_apid_fn else {
        return -EINVAL;
    };
    let Some(release_ap_fn) = release_ap_fn else {
        return -EINVAL;
    };
    let Some(ap_deref_fn) = ap_deref_fn else {
        return -EINVAL;
    };
    let Some(tg_deref_fn) = tg_deref_fn else {
        return -EINVAL;
    };

    let ret = xpmem_positive_id_result(apid);
    if ret != 0 {
        return ret;
    }

    let ap_tg = tg_ref_by_apid_fn(apid);
    if ap_tg.is_null() || ptr_is_err(ap_tg) {
        return ptr_err(ap_tg);
    }

    let owner_tgid = *field_ptr::<CInt>(ap_tg, offsets.tg_tgid_offset);
    let ret = xpmem_owner_policy_result(current_pid, owner_tgid);
    if ret != 0 {
        tg_deref_fn(ap_tg);
        return ret;
    }

    let ap = ap_ref_by_apid_fn(ap_tg, apid);
    if ap.is_null() || ptr_is_err(ap) {
        tg_deref_fn(ap_tg);
        return ptr_err(ap);
    }

    release_ap_fn(ap_tg, ap);
    ap_deref_fn(ap);
    tg_deref_fn(ap_tg);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_vm_munmap_body_result(
    vm: *mut c_void,
    addr: CULong,
    len: SizeT,
    begin_fn: Option<XpmemVoidFn>,
    remove_range_fn: Option<XpmemRemoveRangeFn>,
    finish_fn: Option<XpmemVoidFn>,
) -> CInt {
    let Some(begin_fn) = begin_fn else {
        return -EINVAL;
    };
    let Some(remove_range_fn) = remove_range_fn else {
        return -EINVAL;
    };
    let Some(finish_fn) = finish_fn else {
        return -EINVAL;
    };
    if vm.is_null() {
        return -EINVAL;
    }

    let mut ro_freed = 0;
    begin_fn();
    let ret = remove_range_fn(vm, addr, addr.wrapping_add(len as CULong), &mut ro_freed);
    finish_fn();
    ret
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_detach_body_result(
    at_vaddr: CULong,
    current_pid: CInt,
    vm: *mut c_void,
    offsets: *const XpmemDetachOffsets,
    write_lock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    write_unlock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    lookup_range_fn: Option<XpmemLookupRangeFn>,
    att_ref_fn: Option<XpmemObjectVoidFn>,
    att_deref_fn: Option<XpmemObjectVoidFn>,
    att_write_lock_fn: Option<XpmemRwspinLockFn>,
    att_write_unlock_fn: Option<XpmemRwspinUnlockFn>,
    ap_ref_fn: Option<XpmemObjectVoidFn>,
    ap_deref_fn: Option<XpmemObjectVoidFn>,
    unpin_pages_fn: Option<XpmemUnpinPagesFn>,
    munmap_fn: Option<XpmemMunmapFn>,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    list_del_init_fn: Option<XpmemListFn>,
    att_destroyable_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(write_lock_noirq_fn) = write_lock_noirq_fn else {
        return -EINVAL;
    };
    let Some(write_unlock_noirq_fn) = write_unlock_noirq_fn else {
        return -EINVAL;
    };
    let Some(lookup_range_fn) = lookup_range_fn else {
        return -EINVAL;
    };
    let Some(att_ref_fn) = att_ref_fn else {
        return -EINVAL;
    };
    let Some(att_deref_fn) = att_deref_fn else {
        return -EINVAL;
    };
    let Some(att_write_lock_fn) = att_write_lock_fn else {
        return -EINVAL;
    };
    let Some(att_write_unlock_fn) = att_write_unlock_fn else {
        return -EINVAL;
    };
    let Some(ap_ref_fn) = ap_ref_fn else {
        return -EINVAL;
    };
    let Some(ap_deref_fn) = ap_deref_fn else {
        return -EINVAL;
    };
    let Some(unpin_pages_fn) = unpin_pages_fn else {
        return -EINVAL;
    };
    let Some(munmap_fn) = munmap_fn else {
        return -EINVAL;
    };
    let Some(spin_lock_fn) = spin_lock_fn else {
        return -EINVAL;
    };
    let Some(spin_unlock_fn) = spin_unlock_fn else {
        return -EINVAL;
    };
    let Some(list_del_init_fn) = list_del_init_fn else {
        return -EINVAL;
    };
    let Some(att_destroyable_fn) = att_destroyable_fn else {
        return -EINVAL;
    };
    if vm.is_null() {
        return -EINVAL;
    }

    let vm_lock = field_ptr::<c_void>(vm, offsets.vm_memory_range_lock_offset);
    write_lock_noirq_fn(vm_lock);
    let range = lookup_range_fn(vm, at_vaddr, at_vaddr.wrapping_add(1));
    let has_range = !range.is_null();
    let range_start = if has_range {
        *field_ptr::<CULong>(range, offsets.range_start_offset)
    } else {
        0
    };
    let private_data = if has_range {
        *field_ptr::<*mut c_void>(range, offsets.range_private_data_offset)
    } else {
        core::ptr::null_mut()
    };
    let ret = xpmem_detach_lookup_result(
        has_range as CInt,
        range_start,
        at_vaddr,
        (!private_data.is_null()) as CInt,
    );
    if ret <= 0 {
        write_unlock_noirq_fn(vm_lock);
        return ret;
    }

    let att = private_data;
    att_ref_fn(att);
    let att_lock = field_ptr::<c_void>(att, offsets.att_at_lock_offset);
    let at_lock = att_write_lock_fn(att_lock);

    let flags_ptr = field_ptr::<CInt>(att, offsets.att_flags_offset);
    let mut new_flags = 0;
    if xpmem_begin_destroy_result(*flags_ptr, &mut new_flags) == 0 {
        att_write_unlock_fn(att_lock, at_lock);
        write_unlock_noirq_fn(vm_lock);
        att_deref_fn(att);
        return 0;
    }
    write(flags_ptr, new_flags);

    let ap = *field_ptr::<*mut c_void>(att, offsets.att_ap_offset);
    ap_ref_fn(ap);
    let tg = *field_ptr::<*mut c_void>(ap, offsets.ap_tg_offset);
    let owner_tgid = *field_ptr::<CInt>(tg, offsets.tg_tgid_offset);
    let ret = xpmem_owner_policy_result(current_pid, owner_tgid);
    if ret != 0 {
        write(flags_ptr, *flags_ptr & !XPMEM_FLAG_DESTROYING);
        ap_deref_fn(ap);
        att_write_unlock_fn(att_lock, at_lock);
        write_unlock_noirq_fn(vm_lock);
        att_deref_fn(att);
        return ret;
    }

    let seg = *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset);
    let att_at_vaddr = *field_ptr::<CULong>(att, offsets.att_at_vaddr_offset);
    let att_at_size = *field_ptr::<SizeT>(att, offsets.att_at_size_offset);
    unpin_pages_fn(seg, vm, att_at_vaddr, att_at_size);

    write(
        field_ptr::<*mut c_void>(range, offsets.range_private_data_offset),
        core::ptr::null_mut(),
    );

    att_write_unlock_fn(att_lock, at_lock);
    let ret = munmap_fn(vm, range_start, att_at_size);
    write_unlock_noirq_fn(vm_lock);

    write(flags_ptr, *flags_ptr & !XPMEM_FLAG_VALIDPTES);

    let ap_lock = field_ptr::<c_void>(ap, offsets.ap_lock_offset);
    spin_lock_fn(ap_lock);
    list_del_init_fn(field_ptr::<c_void>(att, offsets.att_att_list_offset));
    spin_unlock_fn(ap_lock);

    att_destroyable_fn(att);
    ap_deref_fn(ap);
    att_deref_fn(att);

    let _ = ret;
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_detach_att_body_result(
    ap: *mut c_void,
    att: *mut c_void,
    offsets: *const XpmemDetachAttOffsets,
    read_lock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    read_unlock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    att_write_lock_fn: Option<XpmemRwspinLockFn>,
    att_write_unlock_fn: Option<XpmemRwspinUnlockFn>,
    lookup_range_fn: Option<XpmemLookupRangeFn>,
    unpin_pages_fn: Option<XpmemUnpinPagesFn>,
    munmap_fn: Option<XpmemMunmapFn>,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    list_del_init_fn: Option<XpmemListFn>,
    att_destroyable_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(read_lock_noirq_fn) = read_lock_noirq_fn else {
        return -EINVAL;
    };
    let Some(read_unlock_noirq_fn) = read_unlock_noirq_fn else {
        return -EINVAL;
    };
    let Some(att_write_lock_fn) = att_write_lock_fn else {
        return -EINVAL;
    };
    let Some(att_write_unlock_fn) = att_write_unlock_fn else {
        return -EINVAL;
    };
    let Some(lookup_range_fn) = lookup_range_fn else {
        return -EINVAL;
    };
    let Some(unpin_pages_fn) = unpin_pages_fn else {
        return -EINVAL;
    };
    let Some(munmap_fn) = munmap_fn else {
        return -EINVAL;
    };
    let Some(spin_lock_fn) = spin_lock_fn else {
        return -EINVAL;
    };
    let Some(spin_unlock_fn) = spin_unlock_fn else {
        return -EINVAL;
    };
    let Some(list_del_init_fn) = list_del_init_fn else {
        return -EINVAL;
    };
    let Some(att_destroyable_fn) = att_destroyable_fn else {
        return -EINVAL;
    };
    if ap.is_null() || att.is_null() {
        return -EINVAL;
    }

    let att_lock = field_ptr::<c_void>(att, offsets.att_at_lock_offset);
    let at_lock = att_write_lock_fn(att_lock);
    let flags_ptr = field_ptr::<CInt>(att, offsets.att_flags_offset);
    let mut new_flags = 0;
    if xpmem_begin_destroy_result(*flags_ptr, &mut new_flags) == 0 {
        att_write_unlock_fn(att_lock, at_lock);
        return 0;
    }
    write(flags_ptr, new_flags);

    let vm = *field_ptr::<*mut c_void>(att, offsets.att_vm_offset);
    let vm_lock = field_ptr::<c_void>(vm, offsets.vm_memory_range_lock_offset);
    read_lock_noirq_fn(vm_lock);

    let att_at_vaddr = *field_ptr::<CULong>(att, offsets.att_at_vaddr_offset);
    let att_at_size = *field_ptr::<SizeT>(att, offsets.att_at_size_offset);
    let range = lookup_range_fn(vm, att_at_vaddr, att_at_vaddr.wrapping_add(1));
    let range_start = if !range.is_null() {
        *field_ptr::<CULong>(range, offsets.range_start_offset)
    } else {
        0
    };
    if range.is_null() || range_start > att_at_vaddr {
        let ap_lock = field_ptr::<c_void>(ap, offsets.ap_lock_offset);
        spin_lock_fn(ap_lock);
        list_del_init_fn(field_ptr::<c_void>(att, offsets.att_att_list_offset));
        spin_unlock_fn(ap_lock);
        att_write_unlock_fn(att_lock, at_lock);
        read_unlock_noirq_fn(vm_lock);
        att_destroyable_fn(att);
        return 0;
    }

    let seg = *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset);
    unpin_pages_fn(seg, vm, att_at_vaddr, att_at_size);
    write(
        field_ptr::<*mut c_void>(range, offsets.range_private_data_offset),
        core::ptr::null_mut(),
    );
    write(flags_ptr, *flags_ptr & !XPMEM_FLAG_VALIDPTES);

    let ap_lock = field_ptr::<c_void>(ap, offsets.ap_lock_offset);
    spin_lock_fn(ap_lock);
    list_del_init_fn(field_ptr::<c_void>(att, offsets.att_att_list_offset));
    spin_unlock_fn(ap_lock);

    att_write_unlock_fn(att_lock, at_lock);
    let ret = munmap_fn(vm, range_start, att_at_size);
    read_unlock_noirq_fn(vm_lock);

    att_destroyable_fn(att);
    let _ = ret;
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_clear_ptes_body_result(
    seg: *mut c_void,
    offsets: *const XpmemClearPtesOffsets,
    clear_range_fn: Option<XpmemClearRangeFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(clear_range_fn) = clear_range_fn else {
        return -EINVAL;
    };
    if seg.is_null() {
        return -EINVAL;
    }

    let start = *field_ptr::<CULong>(seg, offsets.seg_vaddr_offset);
    let size = *field_ptr::<SizeT>(seg, offsets.seg_size_offset);
    clear_range_fn(seg, start, start.wrapping_add(size as CULong));
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_clear_ptes_range_body_result(
    seg: *mut c_void,
    start: CULong,
    end: CULong,
    offsets: *const XpmemClearPtesOffsets,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    ap_ref_fn: Option<XpmemObjectVoidFn>,
    clear_ap_fn: Option<XpmemClearRangeFn>,
    ap_deref_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(spin_lock_fn),
        Some(spin_unlock_fn),
        Some(ap_ref_fn),
        Some(clear_ap_fn),
        Some(ap_deref_fn),
    ) = (
        spin_lock_fn,
        spin_unlock_fn,
        ap_ref_fn,
        clear_ap_fn,
        ap_deref_fn,
    )
    else {
        return -EINVAL;
    };
    if seg.is_null() {
        return -EINVAL;
    }

    let seg_lock = field_ptr::<c_void>(seg, offsets.seg_lock_offset);
    let ap_head = field_ptr::<c_void>(seg, offsets.seg_ap_list_offset);
    spin_lock_fn(seg_lock);

    let mut cursor = list_next(ap_head);
    while cursor != ap_head {
        let ap = (cursor as *mut u8)
            .sub(offsets.ap_ap_list_offset)
            .cast::<c_void>();
        ap_ref_fn(ap);
        spin_unlock_fn(seg_lock);

        clear_ap_fn(ap, start, end);

        spin_lock_fn(seg_lock);
        let ap_entry = field_ptr::<c_void>(ap, offsets.ap_ap_list_offset);
        let next = if list_is_empty(ap_entry) {
            list_next(ap_head)
        } else {
            list_next(ap_entry)
        };
        ap_deref_fn(ap);
        cursor = next;
    }

    spin_unlock_fn(seg_lock);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_clear_ptes_of_ap_body_result(
    ap: *mut c_void,
    start: CULong,
    end: CULong,
    offsets: *const XpmemClearPtesOffsets,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    att_ref_fn: Option<XpmemObjectVoidFn>,
    clear_att_fn: Option<XpmemClearRangeFn>,
    att_deref_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(spin_lock_fn),
        Some(spin_unlock_fn),
        Some(att_ref_fn),
        Some(clear_att_fn),
        Some(att_deref_fn),
    ) = (
        spin_lock_fn,
        spin_unlock_fn,
        att_ref_fn,
        clear_att_fn,
        att_deref_fn,
    )
    else {
        return -EINVAL;
    };
    if ap.is_null() {
        return -EINVAL;
    }

    let ap_lock = field_ptr::<c_void>(ap, offsets.ap_lock_offset);
    let att_head = field_ptr::<c_void>(ap, offsets.ap_att_list_offset);
    spin_lock_fn(ap_lock);

    let mut cursor = list_next(att_head);
    while cursor != att_head {
        let att = (cursor as *mut u8)
            .sub(offsets.att_att_list_offset)
            .cast::<c_void>();
        let att_flags = *field_ptr::<CInt>(att, offsets.att_flags_offset);
        if (att_flags & XPMEM_FLAG_VALIDPTES) == 0 {
            cursor = list_next(cursor);
            continue;
        }

        att_ref_fn(att);
        spin_unlock_fn(ap_lock);

        clear_att_fn(att, start, end);

        spin_lock_fn(ap_lock);
        let att_entry = field_ptr::<c_void>(att, offsets.att_att_list_offset);
        let next = if list_is_empty(att_entry) {
            list_next(att_head)
        } else {
            list_next(att_entry)
        };
        att_deref_fn(att);
        cursor = next;
    }

    spin_unlock_fn(ap_lock);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_clear_ptes_of_att_body_result(
    att: *mut c_void,
    start: CULong,
    end: CULong,
    offsets: *const XpmemClearPtesOffsets,
    read_lock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    read_unlock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    att_write_lock_fn: Option<XpmemRwspinLockFn>,
    att_write_unlock_fn: Option<XpmemRwspinUnlockFn>,
    lookup_range_fn: Option<XpmemLookupRangeFn>,
    unpin_pages_fn: Option<XpmemUnpinPagesFn>,
    munmap_fn: Option<XpmemMunmapFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(read_lock_noirq_fn),
        Some(read_unlock_noirq_fn),
        Some(att_write_lock_fn),
        Some(att_write_unlock_fn),
        Some(lookup_range_fn),
        Some(unpin_pages_fn),
        Some(munmap_fn),
    ) = (
        read_lock_noirq_fn,
        read_unlock_noirq_fn,
        att_write_lock_fn,
        att_write_unlock_fn,
        lookup_range_fn,
        unpin_pages_fn,
        munmap_fn,
    )
    else {
        return -EINVAL;
    };
    if att.is_null() {
        return -EINVAL;
    }

    let vm = *field_ptr::<*mut c_void>(att, offsets.att_vm_offset);
    if vm.is_null() {
        return -EINVAL;
    }

    let vm_lock = field_ptr::<c_void>(vm, offsets.vm_memory_range_lock_offset);
    let att_lock = field_ptr::<c_void>(att, offsets.att_at_lock_offset);
    read_lock_noirq_fn(vm_lock);
    let mut at_lock = att_write_lock_fn(att_lock);

    let flags_ptr = field_ptr::<CInt>(att, offsets.att_flags_offset);
    if (*flags_ptr & XPMEM_FLAG_VALIDPTES) != 0 {
        let att_vaddr = *field_ptr::<CULong>(att, offsets.att_vaddr_offset);
        let att_at_vaddr = *field_ptr::<CULong>(att, offsets.att_at_vaddr_offset);
        let att_at_size = *field_ptr::<SizeT>(att, offsets.att_at_size_offset);
        let mut unpin_at = 0;
        let mut invalidate_len = 0;
        let mut clear_valid = 0;

        if xpmem_clear_pte_range_result(
            *flags_ptr,
            att_vaddr,
            att_at_vaddr,
            att_at_size,
            start,
            end,
            &mut unpin_at,
            &mut invalidate_len,
            &mut clear_valid,
        ) != 0
        {
            let ap = *field_ptr::<*mut c_void>(att, offsets.att_ap_offset);
            let seg = if ap.is_null() {
                core::ptr::null_mut()
            } else {
                *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset)
            };
            if !seg.is_null() {
                unpin_pages_fn(seg, vm, unpin_at, invalidate_len as SizeT);
            }

            let range = lookup_range_fn(vm, att_at_vaddr, att_at_vaddr.wrapping_add(1));
            if !range.is_null() {
                att_write_unlock_fn(att_lock, at_lock);
                let _ = munmap_fn(vm, unpin_at, invalidate_len as SizeT);
                at_lock = att_write_lock_fn(att_lock);
                if clear_valid != 0 {
                    *flags_ptr &= !XPMEM_FLAG_VALIDPTES;
                }
            }
        }
    }

    att_write_unlock_fn(att_lock, at_lock);
    read_unlock_noirq_fn(vm_lock);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_process_memory_range_body_result(
    vm: *mut c_void,
    vmr: *mut c_void,
    offsets: *const XpmemRemoveProcessMemoryRangeOffsets,
    att_ref_fn: Option<XpmemObjectVoidFn>,
    att_deref_fn: Option<XpmemObjectVoidFn>,
    att_write_lock_fn: Option<XpmemRwspinLockFn>,
    att_write_unlock_fn: Option<XpmemRwspinUnlockFn>,
    lookup_range_fn: Option<XpmemLookupRangeFn>,
    ap_ref_fn: Option<XpmemObjectVoidFn>,
    ap_deref_fn: Option<XpmemObjectVoidFn>,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    list_del_init_fn: Option<XpmemListFn>,
    att_destroyable_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(att_ref_fn),
        Some(att_deref_fn),
        Some(att_write_lock_fn),
        Some(att_write_unlock_fn),
        Some(lookup_range_fn),
        Some(ap_ref_fn),
        Some(ap_deref_fn),
        Some(spin_lock_fn),
        Some(spin_unlock_fn),
        Some(list_del_init_fn),
        Some(att_destroyable_fn),
    ) = (
        att_ref_fn,
        att_deref_fn,
        att_write_lock_fn,
        att_write_unlock_fn,
        lookup_range_fn,
        ap_ref_fn,
        ap_deref_fn,
        spin_lock_fn,
        spin_unlock_fn,
        list_del_init_fn,
        att_destroyable_fn,
    )
    else {
        return -EINVAL;
    };
    if vm.is_null() || vmr.is_null() {
        return -EINVAL;
    }

    let vmr_private_ptr = field_ptr::<*mut c_void>(vmr, offsets.range_private_data_offset);
    let att = *vmr_private_ptr;
    if att.is_null() {
        return 0;
    }

    att_ref_fn(att);
    let att_lock = field_ptr::<c_void>(att, offsets.att_at_lock_offset);
    let at_lock = att_write_lock_fn(att_lock);
    let flags_ptr = field_ptr::<CInt>(att, offsets.att_flags_offset);

    if xpmem_is_destroying_result(*flags_ptr) != 0 {
        att_write_unlock_fn(att_lock, at_lock);
        att_deref_fn(att);
        return 0;
    }

    let vmr_start = *field_ptr::<CULong>(vmr, offsets.range_start_offset);
    let vmr_end = *field_ptr::<CULong>(vmr, offsets.range_end_offset);
    let att_at_vaddr = *field_ptr::<CULong>(att, offsets.att_at_vaddr_offset);
    let att_at_size = *field_ptr::<SizeT>(att, offsets.att_at_size_offset);
    let mut remaining_vaddr = 0;
    let mut middle_lookup_vaddr = 0;
    let mut full_detach = 0;
    let mut needs_middle_lookup = 0;

    let _ = xpmem_remove_memory_range_action_result(
        vmr_start,
        vmr_end,
        att_at_vaddr,
        att_at_size,
        &mut remaining_vaddr,
        &mut middle_lookup_vaddr,
        &mut full_detach,
        &mut needs_middle_lookup,
    );

    if full_detach != 0 {
        let mut new_flags = 0;
        let _ = xpmem_begin_destroy_result(*flags_ptr, &mut new_flags);
        *flags_ptr = new_flags;

        let ap = *field_ptr::<*mut c_void>(att, offsets.att_ap_offset);
        ap_ref_fn(ap);
        let ap_lock = field_ptr::<c_void>(ap, offsets.ap_lock_offset);
        spin_lock_fn(ap_lock);
        list_del_init_fn(field_ptr::<c_void>(att, offsets.att_att_list_offset));
        spin_unlock_fn(ap_lock);
        ap_deref_fn(ap);
        att_destroyable_fn(att);

        att_write_unlock_fn(att_lock, at_lock);
        att_deref_fn(att);
        return 0;
    }

    if needs_middle_lookup != 0 {
        let remaining_vmr =
            lookup_range_fn(vm, middle_lookup_vaddr.wrapping_sub(1), middle_lookup_vaddr);
        let has_range = if remaining_vmr.is_null() { 0 } else { 1 };
        let range_start = if remaining_vmr.is_null() {
            0
        } else {
            *field_ptr::<CULong>(remaining_vmr, offsets.range_start_offset)
        };
        let private_matches = if remaining_vmr.is_null() {
            0
        } else if *field_ptr::<*mut c_void>(remaining_vmr, offsets.range_private_data_offset)
            == *vmr_private_ptr
        {
            1
        } else {
            0
        };
        if xpmem_range_private_invalid_result(
            has_range,
            range_start,
            middle_lookup_vaddr,
            private_matches,
        ) != 0
        {
            att_write_unlock_fn(att_lock, at_lock);
            att_deref_fn(att);
            return 0;
        }
        *field_ptr::<*mut c_void>(remaining_vmr, offsets.range_private_data_offset) =
            core::ptr::null_mut();
    }

    let remaining_vmr = lookup_range_fn(vm, remaining_vaddr, remaining_vaddr.wrapping_add(1));
    let has_range = if remaining_vmr.is_null() { 0 } else { 1 };
    let range_start = if remaining_vmr.is_null() {
        0
    } else {
        *field_ptr::<CULong>(remaining_vmr, offsets.range_start_offset)
    };
    let private_matches = if remaining_vmr.is_null() {
        0
    } else if *field_ptr::<*mut c_void>(remaining_vmr, offsets.range_private_data_offset)
        == *vmr_private_ptr
    {
        1
    } else {
        0
    };
    if xpmem_range_private_invalid_result(has_range, range_start, remaining_vaddr, private_matches)
        == 0
    {
        let remaining_start = *field_ptr::<CULong>(remaining_vmr, offsets.range_start_offset);
        let remaining_end = *field_ptr::<CULong>(remaining_vmr, offsets.range_end_offset);
        *field_ptr::<CULong>(att, offsets.att_at_vaddr_offset) = remaining_start;
        *field_ptr::<SizeT>(att, offsets.att_at_size_offset) =
            remaining_end.wrapping_sub(remaining_start) as SizeT;
        *vmr_private_ptr = core::ptr::null_mut();
    }

    att_write_unlock_fn(att_lock, at_lock);
    att_deref_fn(att);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_process_range_body_result(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    ro_freedp: *mut CInt,
    offsets: *const XpmemRemoveProcessRangeOffsets,
    lookup_range_fn: Option<XpmemLookupRangeFn>,
    next_range_fn: Option<XpmemNextRangeFn>,
    split_range_fn: Option<XpmemSplitRangeFn>,
    remove_private_fn: Option<XpmemRangeActionFn>,
    free_range_fn: Option<XpmemRangeActionFn>,
    log_fn: Option<XpmemRemoveProcessRangeLogFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(lookup_range_fn),
        Some(next_range_fn),
        Some(split_range_fn),
        Some(remove_private_fn),
        Some(free_range_fn),
        Some(log_fn),
    ) = (
        lookup_range_fn,
        next_range_fn,
        split_range_fn,
        remove_private_fn,
        free_range_fn,
        log_fn,
    )
    else {
        return -EINVAL;
    };
    if vm.is_null() {
        return -EINVAL;
    }

    let mut ro_freed = 0;
    let mut next = lookup_range_fn(vm, start, end);
    while !next.is_null() {
        let mut range = next;
        if *field_ptr::<CULong>(range, offsets.range_start_offset) >= end {
            break;
        }

        next = next_range_fn(vm, range);

        let mut split_start = 0;
        let mut split_end = 0;
        let mut range_ro_freed = 0;
        let mut remove_private = 0;
        let ret = xpmem_remove_range_step_result(
            *field_ptr::<CULong>(range, offsets.range_start_offset),
            *field_ptr::<CULong>(range, offsets.range_end_offset),
            start,
            end,
            *field_ptr::<CULong>(range, offsets.range_flag_offset),
            (!(*field_ptr::<*mut c_void>(range, offsets.range_private_data_offset)).is_null())
                as CInt,
            &mut split_start,
            &mut split_end,
            &mut range_ro_freed,
            &mut remove_private,
        );
        if ret != 0 {
            return ret;
        }

        if split_start != 0 {
            let mut new_range = core::ptr::null_mut();
            let ret = split_range_fn(vm, range, start, &mut new_range);
            if ret != 0 {
                log_fn(vm, start, end, ret, 0);
                return ret;
            }
            if new_range.is_null() {
                return -EINVAL;
            }
            range = new_range;
        }

        if split_end != 0 {
            let ret = split_range_fn(vm, range, end, core::ptr::null_mut());
            if ret != 0 {
                log_fn(vm, start, end, ret, 0);
                return ret;
            }
        }

        if range_ro_freed != 0 {
            ro_freed = 1;
        }

        if remove_private != 0 {
            let _ = remove_private_fn(vm, range);
        }

        let ret = free_range_fn(vm, range);
        if ret != 0 {
            log_fn(vm, start, end, ret, 1);
            return ret;
        }
    }

    if !ro_freedp.is_null() {
        write(ro_freedp, ro_freed);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_free_process_range_body_result(
    vm: *mut c_void,
    range: *mut c_void,
    offsets: *const XpmemFreeProcessRangeOffsets,
    lock_fn: Option<XpmemSpinFn>,
    unlock_fn: Option<XpmemSpinFn>,
    pt_clear_fn: Option<XpmemPtClearRangeFn>,
    memobj_unref_fn: Option<XpmemObjectVoidFn>,
    erase_fn: Option<XpmemRangeEraseFn>,
    free_fn: Option<XpmemObjectVoidFn>,
    log_fn: Option<XpmemFreeProcessRangeLogFn>,
) -> CInt {
    const LOG_PT_CLEAR_ERROR: CInt = 1;

    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(lock_fn),
        Some(unlock_fn),
        Some(pt_clear_fn),
        Some(memobj_unref_fn),
        Some(erase_fn),
        Some(free_fn),
        Some(log_fn),
    ) = (
        lock_fn,
        unlock_fn,
        pt_clear_fn,
        memobj_unref_fn,
        erase_fn,
        free_fn,
        log_fn,
    )
    else {
        return -EINVAL;
    };
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }

    let start = *field_ptr::<CULong>(range, offsets.range_start_offset);
    let end = *field_ptr::<CULong>(range, offsets.range_end_offset);
    let asp = *field_ptr::<*mut c_void>(vm, offsets.vm_address_space_offset);
    if asp.is_null() {
        return -EINVAL;
    }
    let page_table = *field_ptr::<*mut c_void>(asp, offsets.address_space_page_table_offset);
    let page_table_lock = (vm as *mut u8)
        .add(offsets.vm_page_table_lock_offset)
        .cast::<c_void>();

    lock_fn(page_table_lock);
    let error = pt_clear_fn(page_table, vm, start, end);
    unlock_fn(page_table_lock);
    if error != 0 && error != -ENOENT {
        log_fn(LOG_PT_CLEAR_ERROR, vm, range, start, end, error);
    }

    let memobj = *field_ptr::<*mut c_void>(range, offsets.range_memobj_offset);
    if !memobj.is_null() {
        memobj_unref_fn(memobj);
    }

    erase_fn(
        (vm as *mut u8)
            .add(offsets.vm_range_tree_offset)
            .cast::<c_void>(),
        (range as *mut u8)
            .add(offsets.range_rb_node_offset)
            .cast::<c_void>(),
    );

    let cache_base = (vm as *mut u8)
        .wrapping_add(offsets.vm_range_cache_offset)
        .cast::<*mut c_void>();
    let mut i = 0;
    while i < offsets.vm_range_cache_count {
        let slot = cache_base.add(i);
        if *slot == range {
            *slot = core::ptr::null_mut();
        }
        i += 1;
    }

    free_fn(range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_update_process_page_table_body_result(
    vm: *mut c_void,
    vmr: *mut c_void,
    current_pid: CInt,
    page_in_remote_on_attach: CInt,
    offsets: *const XpmemUpdatePageTableOffsets,
    att_ref_fn: Option<XpmemObjectVoidFn>,
    att_deref_fn: Option<XpmemObjectVoidFn>,
    ap_ref_fn: Option<XpmemObjectVoidFn>,
    ap_deref_fn: Option<XpmemObjectVoidFn>,
    tg_ref_fn: Option<XpmemObjectVoidFn>,
    tg_deref_fn: Option<XpmemObjectVoidFn>,
    seg_ref_fn: Option<XpmemObjectVoidFn>,
    seg_deref_fn: Option<XpmemObjectVoidFn>,
    bug_on_fn: Option<XpmemBugOnFn>,
    fault_fn: Option<XpmemFaultRangeWithPageInFn>,
    pt_lookup_pte_fn: Option<XpmemPtLookupPteFn>,
    pte_present_fn: Option<XpmemPtePresentFn>,
    log_fn: Option<XpmemUpdatePageTableLogFn>,
) -> CInt {
    const LOG_FAULT_ERROR: CInt = 1;

    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(att_ref_fn),
        Some(att_deref_fn),
        Some(ap_ref_fn),
        Some(ap_deref_fn),
        Some(tg_ref_fn),
        Some(tg_deref_fn),
        Some(seg_ref_fn),
        Some(seg_deref_fn),
        Some(bug_on_fn),
        Some(fault_fn),
        Some(pt_lookup_pte_fn),
        Some(pte_present_fn),
        Some(log_fn),
    ) = (
        att_ref_fn,
        att_deref_fn,
        ap_ref_fn,
        ap_deref_fn,
        tg_ref_fn,
        tg_deref_fn,
        seg_ref_fn,
        seg_deref_fn,
        bug_on_fn,
        fault_fn,
        pt_lookup_pte_fn,
        pte_present_fn,
        log_fn,
    )
    else {
        return -EINVAL;
    };
    if vm.is_null() || vmr.is_null() {
        return -EINVAL;
    }

    let att = *field_ptr::<*mut c_void>(vmr, offsets.range_private_data_offset);
    if att.is_null() {
        return -EFAULT;
    }

    let mut ret: CInt;

    att_ref_fn(att);
    let ap = *field_ptr::<*mut c_void>(att, offsets.att_ap_offset);
    if ap.is_null() {
        att_deref_fn(att);
        return -EINVAL;
    }
    ap_ref_fn(ap);
    let ap_tg = *field_ptr::<*mut c_void>(ap, offsets.ap_tg_offset);
    if ap_tg.is_null() {
        att_deref_fn(att);
        ap_deref_fn(ap);
        return -EINVAL;
    }
    tg_ref_fn(ap_tg);

    ret = xpmem_two_destroying_error_result(
        *field_ptr::<CInt>(ap, offsets.ap_flags_offset),
        *field_ptr::<CInt>(ap_tg, offsets.tg_flags_offset),
        -EFAULT,
    );
    if ret != 0 {
        att_deref_fn(att);
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        return ret;
    }

    bug_on_fn((*field_ptr::<CInt>(ap_tg, offsets.tg_tgid_offset) != current_pid) as CInt);
    bug_on_fn((*field_ptr::<CInt>(ap, offsets.ap_mode_offset) != XPMEM_RDWR) as CInt);

    let seg = *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset);
    if seg.is_null() {
        att_deref_fn(att);
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        return -EINVAL;
    }
    seg_ref_fn(seg);
    let seg_tg = *field_ptr::<*mut c_void>(seg, offsets.seg_tg_offset);
    if seg_tg.is_null() {
        seg_deref_fn(seg);
        att_deref_fn(att);
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        return -EINVAL;
    }
    tg_ref_fn(seg_tg);

    ret = xpmem_two_destroying_error_result(
        *field_ptr::<CInt>(seg, offsets.seg_flags_offset),
        *field_ptr::<CInt>(seg_tg, offsets.tg_flags_offset),
        -ENOENT,
    );
    if ret == 0 {
        let start = *field_ptr::<CULong>(vmr, offsets.range_start_offset);
        let end = *field_ptr::<CULong>(vmr, offsets.range_end_offset);
        *field_ptr::<CULong>(att, offsets.att_at_vaddr_offset) = start;
        *field_ptr::<*mut c_void>(att, offsets.att_at_vmr_offset) = vmr;

        if xpmem_three_destroying_error_result(
            *field_ptr::<CInt>(att, offsets.att_flags_offset),
            *field_ptr::<CInt>(ap_tg, offsets.tg_flags_offset),
            *field_ptr::<CInt>(seg_tg, offsets.tg_flags_offset),
            1,
        ) != 0
        {
            ret = 0;
        } else {
            let address_space = *field_ptr::<*mut c_void>(vm, offsets.vm_address_space_offset);
            if address_space.is_null() {
                ret = -EINVAL;
            } else {
                let page_table = *field_ptr::<*mut c_void>(
                    address_space,
                    offsets.address_space_page_table_offset,
                );
                let pgshift = *field_ptr::<CInt>(vmr, offsets.range_pgshift_offset);
                let mut vaddr = start;
                while vaddr < end {
                    ret = fault_fn(vm, vmr, vaddr, 0, page_in_remote_on_attach);
                    if ret != 0 {
                        log_fn(LOG_FAULT_ERROR, vm, vmr, vaddr, ret);
                    }

                    let mut pgsize: SizeT = 0;
                    let pte = pt_lookup_pte_fn(
                        page_table,
                        vaddr,
                        pgshift,
                        core::ptr::null_mut(),
                        &mut pgsize,
                        core::ptr::null_mut(),
                    );
                    if pte.is_null() || pte_present_fn(pte) == 0 {
                        pgsize = PAGE_SIZE as SizeT;
                    }
                    vaddr = vaddr.wrapping_add(pgsize as CULong);
                }
            }
        }
    }

    tg_deref_fn(seg_tg);
    seg_deref_fn(seg);
    att_deref_fn(att);
    ap_deref_fn(ap);
    tg_deref_fn(ap_tg);

    ret
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_fault_process_memory_range_body_result(
    vm: *mut c_void,
    vmr: *mut c_void,
    vaddr: CULong,
    reason: CULong,
    page_in_remote: CInt,
    current_pid: CInt,
    current_vm: *mut c_void,
    offsets: *const XpmemFaultProcessRangeOffsets,
    ops: *const XpmemFaultProcessRangeOps,
) -> CInt {
    const LOG_DESTROYING: CInt = 1;
    const LOG_BAD_VADDR: CInt = 2;

    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(ops) = ops.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(att_ref_fn),
        Some(att_deref_fn),
        Some(ap_ref_fn),
        Some(ap_deref_fn),
        Some(tg_ref_fn),
        Some(tg_deref_fn),
        Some(seg_ref_fn),
        Some(seg_deref_fn),
        Some(bug_on_fn),
        Some(ensure_valid_fn),
        Some(read_lock_noirq_fn),
        Some(read_unlock_noirq_fn),
        Some(vaddr_to_pte_fn),
        Some(pte_present_fn),
        Some(pte_phys_fn),
        Some(pt_lookup_pte_fn),
        Some(smaller_page_fn),
        Some(adjust_page_fn),
        Some(vrflag_to_ptattr_fn),
        Some(pgsize_contiguous_fn),
        Some(pt_set_pte_fn),
        Some(pt_set_range_fn),
        Some(atomic_dec_fn),
        Some(flush_tlb_single_fn),
        Some(log_fn),
    ) = (
        ops.att_ref_fn,
        ops.att_deref_fn,
        ops.ap_ref_fn,
        ops.ap_deref_fn,
        ops.tg_ref_fn,
        ops.tg_deref_fn,
        ops.seg_ref_fn,
        ops.seg_deref_fn,
        ops.bug_on_fn,
        ops.ensure_valid_fn,
        ops.read_lock_noirq_fn,
        ops.read_unlock_noirq_fn,
        ops.vaddr_to_pte_fn,
        ops.pte_present_fn,
        ops.pte_phys_fn,
        ops.pt_lookup_pte_fn,
        ops.smaller_page_fn,
        ops.adjust_page_fn,
        ops.vrflag_to_ptattr_fn,
        ops.pgsize_contiguous_fn,
        ops.pt_set_pte_fn,
        ops.pt_set_range_fn,
        ops.atomic_dec_fn,
        ops.flush_tlb_single_fn,
        ops.log_fn,
    )
    else {
        return -EINVAL;
    };
    if vm.is_null() || vmr.is_null() {
        return -EINVAL;
    }

    let att = *field_ptr::<*mut c_void>(vmr, offsets.range_private_data_offset);
    if att.is_null() {
        return -EFAULT;
    }

    att_ref_fn(att);
    let ap = *field_ptr::<*mut c_void>(att, offsets.att_ap_offset);
    if ap.is_null() {
        att_deref_fn(att);
        return -EINVAL;
    }
    ap_ref_fn(ap);
    let ap_tg = *field_ptr::<*mut c_void>(ap, offsets.ap_tg_offset);
    if ap_tg.is_null() {
        att_deref_fn(att);
        ap_deref_fn(ap);
        return -EINVAL;
    }
    tg_ref_fn(ap_tg);

    let mut ret = xpmem_two_destroying_error_result(
        *field_ptr::<CInt>(ap, offsets.ap_flags_offset),
        *field_ptr::<CInt>(ap_tg, offsets.tg_flags_offset),
        -EFAULT,
    );
    if ret != 0 {
        att_deref_fn(att);
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        return ret;
    }

    bug_on_fn((*field_ptr::<CInt>(ap_tg, offsets.tg_tgid_offset) != current_pid) as CInt);
    bug_on_fn((*field_ptr::<CInt>(ap, offsets.ap_mode_offset) != XPMEM_RDWR) as CInt);

    let seg = *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset);
    if seg.is_null() {
        att_deref_fn(att);
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        return -EINVAL;
    }
    seg_ref_fn(seg);
    let seg_tg = *field_ptr::<*mut c_void>(seg, offsets.seg_tg_offset);
    if seg_tg.is_null() {
        seg_deref_fn(seg);
        att_deref_fn(att);
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        return -EINVAL;
    }
    tg_ref_fn(seg_tg);

    ret = xpmem_two_destroying_error_result(
        *field_ptr::<CInt>(seg, offsets.seg_flags_offset),
        *field_ptr::<CInt>(seg_tg, offsets.tg_flags_offset),
        -EFAULT,
    );
    if ret != 0 {
        goto_fault_out(
            ret,
            ap,
            ap_tg,
            seg_tg,
            seg,
            att,
            ap_deref_fn,
            tg_deref_fn,
            seg_deref_fn,
            att_deref_fn,
        )
    } else {
        ret = xpmem_three_destroying_error_result(
            *field_ptr::<CInt>(att, offsets.att_flags_offset),
            *field_ptr::<CInt>(ap_tg, offsets.tg_flags_offset),
            *field_ptr::<CInt>(seg_tg, offsets.tg_flags_offset),
            -EFAULT,
        );
        if ret != 0 {
            log_fn(LOG_DESTROYING, vaddr, 0, 0, 0, ret);
        } else {
            let mut seg_vaddr: CULong = 0;
            ret = xpmem_fault_vaddr_result(
                vaddr,
                *field_ptr::<CULong>(att, offsets.att_at_vaddr_offset),
                *field_ptr::<SizeT>(att, offsets.att_at_size_offset),
                *field_ptr::<CULong>(att, offsets.att_vaddr_offset),
                &mut seg_vaddr,
            );
            if ret != 0 {
                log_fn(
                    LOG_BAD_VADDR,
                    vaddr,
                    *field_ptr::<CULong>(att, offsets.att_at_vaddr_offset),
                    0,
                    *field_ptr::<SizeT>(att, offsets.att_at_size_offset),
                    ret,
                );
            } else {
                ret = ensure_valid_fn(seg, seg_vaddr, page_in_remote);
                if ret == 0 {
                    ret = xpmem_fault_map_present_page(
                        vm,
                        vmr,
                        vaddr,
                        reason,
                        page_in_remote,
                        current_vm,
                        offsets,
                        att,
                        seg_tg,
                        seg_vaddr,
                        read_lock_noirq_fn,
                        read_unlock_noirq_fn,
                        vaddr_to_pte_fn,
                        pte_present_fn,
                        pte_phys_fn,
                        pt_lookup_pte_fn,
                        smaller_page_fn,
                        adjust_page_fn,
                        vrflag_to_ptattr_fn,
                        pgsize_contiguous_fn,
                        pt_set_pte_fn,
                        pt_set_range_fn,
                        atomic_dec_fn,
                        flush_tlb_single_fn,
                        log_fn,
                    );
                }
            }
        }

        goto_fault_out(
            ret,
            ap,
            ap_tg,
            seg_tg,
            seg,
            att,
            ap_deref_fn,
            tg_deref_fn,
            seg_deref_fn,
            att_deref_fn,
        )
    }
}

#[inline]
unsafe fn goto_fault_out(
    ret: CInt,
    ap: *mut c_void,
    ap_tg: *mut c_void,
    seg_tg: *mut c_void,
    seg: *mut c_void,
    att: *mut c_void,
    ap_deref_fn: XpmemObjectVoidFn,
    tg_deref_fn: XpmemObjectVoidFn,
    seg_deref_fn: XpmemObjectVoidFn,
    att_deref_fn: XpmemObjectVoidFn,
) -> CInt {
    ap_deref_fn(ap);
    tg_deref_fn(ap_tg);
    tg_deref_fn(seg_tg);
    seg_deref_fn(seg);
    att_deref_fn(att);
    ret
}

#[allow(clippy::too_many_arguments)]
unsafe fn xpmem_fault_map_present_page(
    vm: *mut c_void,
    vmr: *mut c_void,
    vaddr: CULong,
    reason: CULong,
    page_in_remote: CInt,
    current_vm: *mut c_void,
    offsets: &XpmemFaultProcessRangeOffsets,
    att: *mut c_void,
    seg_tg: *mut c_void,
    seg_vaddr: CULong,
    read_lock_noirq_fn: XpmemRwspinNoirqFn,
    read_unlock_noirq_fn: XpmemRwspinNoirqFn,
    vaddr_to_pte_fn: XpmemVaddrToPteFn,
    pte_present_fn: XpmemPtePresentFn,
    pte_phys_fn: XpmemPtePhysFn,
    pt_lookup_pte_fn: XpmemPtLookupPteFn,
    smaller_page_fn: XpmemGetSmallerPageSizeFn,
    adjust_page_fn: XpmemAdjustPageSizeFn,
    vrflag_to_ptattr_fn: XpmemVrflagToPtattrFn,
    pgsize_contiguous_fn: XpmemPgsizeContiguousFn,
    pt_set_pte_fn: XpmemPtSetPteFn,
    pt_set_range_fn: XpmemPtSetRangeFn,
    atomic_dec_fn: XpmemAtomicDecFn,
    flush_tlb_single_fn: XpmemFlushTlbSingleFn,
    log_fn: XpmemFaultLogFn,
) -> CInt {
    const LOG_SMALLER_PAGE_ERROR: CInt = 3;
    const LOG_PTE_MISMATCH: CInt = 4;
    const LOG_SET_PTE_ERROR: CInt = 5;
    const LOG_SET_RANGE_ERROR: CInt = 6;

    let seg_vm = *field_ptr::<*mut c_void>(seg_tg, offsets.tg_vm_offset);
    if seg_vm.is_null() {
        return -EINVAL;
    }
    let seg_proc = *field_ptr::<*mut c_void>(seg_vm, offsets.vm_proc_offset);
    if seg_proc.is_null() {
        return -EINVAL;
    }

    let remote = seg_vm != current_vm;
    if remote {
        read_lock_noirq_fn(
            (seg_vm as *mut u8)
                .add(offsets.vm_memory_range_lock_offset)
                .cast::<c_void>(),
        );
    }

    let mut seg_phys: CULong = 0;
    let mut seg_pgsize: SizeT = 0;
    if xpmem_straight_phys_result(
        seg_vaddr,
        *field_ptr::<*mut c_void>(seg_proc, offsets.proc_straight_va_offset) as CULong,
        *field_ptr::<SizeT>(seg_proc, offsets.proc_straight_len_offset),
        *field_ptr::<CULong>(seg_proc, offsets.proc_straight_pa_offset),
        &mut seg_phys,
        &mut seg_pgsize,
    ) == 0
    {
        let seg_pte = vaddr_to_pte_fn(seg_vm, seg_vaddr, &mut seg_pgsize);
        let ret = xpmem_remote_pte_missing_result(
            (!seg_pte.is_null()) as CInt,
            (!seg_pte.is_null() && pte_present_fn(seg_pte) == 0) as CInt,
            page_in_remote,
        );
        if ret != 1 {
            if remote {
                read_unlock_noirq_fn(
                    (seg_vm as *mut u8)
                        .add(offsets.vm_memory_range_lock_offset)
                        .cast::<c_void>(),
                );
            }
            return ret;
        }
        seg_phys = pte_phys_fn(seg_pte);
    }

    let seg_phys_plus_off = xpmem_seg_phys_plus_off_result(seg_phys, seg_pgsize, seg_vaddr);
    if remote {
        read_unlock_noirq_fn(
            (seg_vm as *mut u8)
                .add(offsets.vm_memory_range_lock_offset)
                .cast::<c_void>(),
        );
    }

    let address_space = *field_ptr::<*mut c_void>(vm, offsets.vm_address_space_offset);
    if address_space.is_null() {
        return -EINVAL;
    }
    let page_table =
        *field_ptr::<*mut c_void>(address_space, offsets.address_space_page_table_offset);
    let pgshift = *field_ptr::<CInt>(vmr, offsets.range_pgshift_offset);
    let mut att_pgaddr: *mut c_void = core::ptr::null_mut();
    let mut att_pgsize: SizeT = 0;
    let mut att_p2align: CInt = 0;
    let mut att_pte = pt_lookup_pte_fn(
        page_table,
        vaddr,
        pgshift,
        &mut att_pgaddr,
        &mut att_pgsize,
        &mut att_p2align,
    );

    while xpmem_att_page_fits_result(
        att_pgaddr as CULong,
        att_pgsize,
        *field_ptr::<CULong>(vmr, offsets.range_start_offset),
        *field_ptr::<CULong>(vmr, offsets.range_end_offset),
        seg_pgsize,
    ) == 0
    {
        att_pte = core::ptr::null_mut();
        let ret = smaller_page_fn(att_pgsize, &mut att_pgsize, &mut att_p2align);
        if ret != 0 {
            log_fn(
                LOG_SMALLER_PAGE_ERROR,
                *field_ptr::<CULong>(vmr, offsets.range_start_offset),
                *field_ptr::<CULong>(vmr, offsets.range_end_offset),
                0,
                att_pgsize,
                ret,
            );
            return ret;
        }
        att_pgaddr = (vaddr & !((att_pgsize as CULong).wrapping_sub(1))) as *mut c_void;
    }

    adjust_page_fn(page_table, vaddr, att_pte, &mut att_pgaddr, &mut att_pgsize);

    let seg_phys_aligned = seg_phys_plus_off & !((att_pgsize as CULong).wrapping_sub(1));
    let att_attr =
        vrflag_to_ptattr_fn(*field_ptr::<CULong>(vmr, offsets.range_flag_offset), reason);

    if !att_pte.is_null() && pte_present_fn(att_pte) != 0 {
        let att_phys = pte_phys_fn(att_pte);
        let ret = xpmem_pte_mismatch_result(att_phys, seg_phys_aligned);
        if ret != 0 {
            log_fn(LOG_PTE_MISMATCH, vaddr, att_phys, seg_phys_aligned, 0, ret);
        }
        if page_in_remote != 0 {
            let n_pinned = (seg_tg as *mut u8)
                .add(offsets.tg_n_pinned_offset)
                .cast::<c_void>();
            let _ = atomic_dec_fn(n_pinned);
        }
        return ret;
    }

    let ret = if !att_pte.is_null() && pgsize_contiguous_fn(att_pgsize) == 0 {
        let rc = pt_set_pte_fn(page_table, att_pte, att_pgsize, seg_phys_aligned, att_attr);
        if rc != 0 {
            log_fn(
                LOG_SET_PTE_ERROR,
                vaddr,
                seg_phys_aligned,
                0,
                att_pgsize,
                rc,
            );
            -EFAULT
        } else {
            0
        }
    } else {
        let start = att_pgaddr as CULong;
        let rc = pt_set_range_fn(
            page_table,
            vm,
            start,
            start.wrapping_add(att_pgsize as CULong),
            seg_phys_aligned,
            att_attr,
            pgshift,
            vmr,
            1,
        );
        if rc != 0 {
            log_fn(
                LOG_SET_RANGE_ERROR,
                vaddr,
                seg_phys_aligned,
                0,
                att_pgsize,
                rc,
            );
            -EFAULT
        } else {
            0
        }
    };
    if ret != 0 {
        return ret;
    }

    *field_ptr::<CInt>(att, offsets.att_flags_offset) |= XPMEM_FLAG_VALIDPTES;
    flush_tlb_single_fn(vaddr);
    0
}

#[no_mangle]
pub extern "C" fn xpmem_ref_drop_should_free_result(refcnt_after_dec: CInt) -> CInt {
    if refcnt_after_dec == 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_begin_destroy_result(flags: CInt, new_flagsp: *mut CInt) -> CInt {
    if (flags & XPMEM_FLAG_DESTROYING) != 0 {
        write(new_flagsp, flags);
        0
    } else {
        write(new_flagsp, flags | XPMEM_FLAG_DESTROYING);
        1
    }
}

#[no_mangle]
pub extern "C" fn xpmem_finish_destroy_result(flags: CInt) -> CInt {
    flags | XPMEM_FLAG_DESTROYED
}

#[no_mangle]
pub extern "C" fn xpmem_object_lookup_decision_result(
    candidate_id: CLong,
    requested_id: CLong,
    flags: CInt,
    return_destroying: CInt,
    stop_on_destroying: CInt,
) -> CInt {
    if candidate_id != requested_id {
        return XPMEM_LOOKUP_SKIP;
    }

    if (flags & XPMEM_FLAG_DESTROYING) != 0 && return_destroying == 0 {
        if stop_on_destroying != 0 {
            XPMEM_LOOKUP_STOP
        } else {
            XPMEM_LOOKUP_SKIP
        }
    } else {
        XPMEM_LOOKUP_TAKE
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_ref_by_tgid_nolock_body_result(
    part: *mut c_void,
    tgid: CInt,
    index: CInt,
    return_destroying: CInt,
    offsets: *const XpmemTgLookupOffsets,
    tg_ref_fn: Option<XpmemObjectVoidFn>,
) -> *mut c_void {
    let Some(offsets) = offsets.as_ref() else {
        return err_ptr(-EINVAL);
    };
    let Some(tg_ref_fn) = tg_ref_fn else {
        return err_ptr(-EINVAL);
    };
    if part.is_null() || index < 0 {
        return err_ptr(-EINVAL);
    }

    let hashlist = (part as *mut u8)
        .add(offsets.part_tg_hashtable_offset)
        .add(index as usize * offsets.hashlist_stride)
        .cast::<c_void>();
    let head = field_ptr::<c_void>(hashlist, offsets.hashlist_list_offset);
    let mut entry = list_next(head);
    while entry != head {
        let tg = list_entry(entry, offsets.tg_hashlist_offset);
        let candidate = *field_ptr::<CInt>(tg, offsets.tg_tgid_offset) as CLong;
        let flags = *field_ptr::<CInt>(tg, offsets.tg_flags_offset);
        if xpmem_object_lookup_decision_result(
            candidate,
            tgid as CLong,
            flags,
            return_destroying,
            0,
        ) == XPMEM_LOOKUP_TAKE
        {
            tg_ref_fn(tg);
            return tg;
        }
        entry = list_next(entry);
    }

    err_ptr(-ENOENT)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_ref_by_tgid_wrapper_result(
    part: *mut c_void,
    tgid: CInt,
    return_destroying: CInt,
    locked: CInt,
    lookup_offsets: *const XpmemTgLookupOffsets,
    partition_offsets: *const XpmemPartitionOffsets,
    rwlock_node: *mut c_void,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    tg_ref_fn: Option<XpmemObjectVoidFn>,
    log_fn: Option<XpmemTgLookupLogFn>,
) -> *mut c_void {
    let Some(_) = lookup_offsets.as_ref() else {
        return err_ptr(-EINVAL);
    };
    let Some(tg_ref_fn) = tg_ref_fn else {
        return err_ptr(-EINVAL);
    };
    if locked != 0
        && (partition_offsets.is_null()
            || rwlock_node.is_null()
            || rwlock_lock_fn.is_none()
            || rwlock_unlock_fn.is_none())
    {
        return err_ptr(-EINVAL);
    }

    if let Some(log_fn) = log_fn {
        log_fn(
            XPMEM_TG_LOOKUP_LOG_CALL,
            tgid,
            return_destroying,
            part,
            core::ptr::null_mut(),
        );
    }

    let index = xpmem_tg_hashtable_index(tgid);
    if index < 0 {
        return err_ptr(-EINVAL);
    }

    let tg = if locked != 0 {
        let Some(partition_offsets) = partition_offsets.as_ref() else {
            return err_ptr(-EINVAL);
        };
        let Some(rwlock_lock_fn) = rwlock_lock_fn else {
            return err_ptr(-EINVAL);
        };
        let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
            return err_ptr(-EINVAL);
        };
        if part.is_null() {
            return err_ptr(-EINVAL);
        }
        if let Some(log_fn) = log_fn {
            log_fn(
                XPMEM_TG_LOOKUP_LOG_PART,
                tgid,
                return_destroying,
                part,
                core::ptr::null_mut(),
            );
        }

        let hashlist = (part as *mut u8)
            .add(partition_offsets.part_tg_hashtable_offset)
            .add(index as usize * partition_offsets.hashlist_stride)
            .cast::<c_void>();
        let lock = field_ptr::<c_void>(hashlist, partition_offsets.hashlist_lock_offset);
        rwlock_lock_fn(lock, rwlock_node);
        let tg = xpmem_tg_ref_by_tgid_nolock_body_result(
            part,
            tgid,
            index,
            return_destroying,
            lookup_offsets,
            Some(tg_ref_fn),
        );
        rwlock_unlock_fn(lock, rwlock_node);
        tg
    } else {
        xpmem_tg_ref_by_tgid_nolock_body_result(
            part,
            tgid,
            index,
            return_destroying,
            lookup_offsets,
            Some(tg_ref_fn),
        )
    };

    if let Some(log_fn) = log_fn {
        log_fn(
            XPMEM_TG_LOOKUP_LOG_RETURN,
            tgid,
            return_destroying,
            part,
            tg,
        );
    }

    tg
}

unsafe fn xpmem_tg_ref_by_tgid_common(
    tgid: CInt,
    return_destroying: CInt,
    locked: CInt,
) -> *mut c_void {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();

    xpmem_tg_ref_by_tgid_wrapper_result(
        xpmem_my_part,
        tgid,
        return_destroying,
        locked,
        core::ptr::addr_of!(xpmem_tg_lookup_offsets),
        core::ptr::addr_of!(xpmem_partition_offsets),
        lock.as_mut_ptr().cast::<c_void>(),
        Some(xpmem_rwlock_reader_lock_bridge),
        Some(xpmem_rwlock_reader_unlock_bridge),
        Some(xpmem_tg_ref_bridge),
        Some(xpmem_tg_ref_lookup_log),
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_ref_by_tgid(tgid: CInt) -> *mut c_void {
    xpmem_tg_ref_by_tgid_common(tgid, 0, 1)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_ref_by_tgid_all(tgid: CInt) -> *mut c_void {
    xpmem_tg_ref_by_tgid_common(tgid, 1, 1)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_ref_by_tgid_nolock(tgid: CInt) -> *mut c_void {
    xpmem_tg_ref_by_tgid_common(tgid, 0, 0)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_ref_by_tgid_all_nolock(tgid: CInt) -> *mut c_void {
    xpmem_tg_ref_by_tgid_common(tgid, 1, 0)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_is_private_data_result(
    vmr: *mut c_void,
    private_data_offset: SizeT,
) -> CInt {
    if vmr.is_null() {
        return 0;
    }

    (!(*field_ptr::<*mut c_void>(vmr, private_data_offset)).is_null()) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_is_private_data(vmr: *mut c_void) -> CInt {
    xpmem_is_private_data_result(vmr, xpmem_vm_range_private_data_offset)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_seg_ref_by_segid_body_result(
    seg_tg: *mut c_void,
    segid: CLong,
    offsets: *const XpmemSegLookupOffsets,
    rwlock_node: *mut c_void,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    seg_ref_fn: Option<XpmemObjectVoidFn>,
) -> *mut c_void {
    let Some(offsets) = offsets.as_ref() else {
        return err_ptr(-EINVAL);
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return err_ptr(-EINVAL);
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return err_ptr(-EINVAL);
    };
    let Some(seg_ref_fn) = seg_ref_fn else {
        return err_ptr(-EINVAL);
    };
    if seg_tg.is_null() || rwlock_node.is_null() {
        return err_ptr(-EINVAL);
    }

    let lock = field_ptr::<c_void>(seg_tg, offsets.tg_seg_list_lock_offset);
    let head = field_ptr::<c_void>(seg_tg, offsets.tg_seg_list_offset);
    rwlock_lock_fn(lock, rwlock_node);
    let mut entry = list_next(head);
    while entry != head {
        let seg = list_entry(entry, offsets.seg_list_offset);
        let candidate = *field_ptr::<CLong>(seg, offsets.seg_segid_offset);
        let flags = *field_ptr::<CInt>(seg, offsets.seg_flags_offset);
        if xpmem_object_lookup_decision_result(candidate, segid, flags, 0, 0) == XPMEM_LOOKUP_TAKE {
            seg_ref_fn(seg);
            rwlock_unlock_fn(lock, rwlock_node);
            return seg;
        }
        entry = list_next(entry);
    }

    rwlock_unlock_fn(lock, rwlock_node);
    err_ptr(-ENOENT)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_ap_ref_by_apid_body_result(
    ap_tg: *mut c_void,
    apid: CLong,
    offsets: *const XpmemApLookupOffsets,
    rwlock_node: *mut c_void,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    ap_ref_fn: Option<XpmemObjectVoidFn>,
) -> *mut c_void {
    let Some(offsets) = offsets.as_ref() else {
        return err_ptr(-EINVAL);
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return err_ptr(-EINVAL);
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return err_ptr(-EINVAL);
    };
    let Some(ap_ref_fn) = ap_ref_fn else {
        return err_ptr(-EINVAL);
    };
    if ap_tg.is_null() || rwlock_node.is_null() {
        return err_ptr(-EINVAL);
    }

    let index = xpmem_ap_hashtable_index_result(apid);
    if index < 0 {
        return err_ptr(-EINVAL);
    }
    let hashlist = (ap_tg as *mut u8)
        .add(offsets.tg_ap_hashtable_offset)
        .add(index as usize * offsets.hashlist_stride)
        .cast::<c_void>();
    let lock = field_ptr::<c_void>(hashlist, offsets.hashlist_lock_offset);
    let head = field_ptr::<c_void>(hashlist, offsets.hashlist_list_offset);

    rwlock_lock_fn(lock, rwlock_node);
    let mut entry = list_next(head);
    while entry != head {
        let ap = list_entry(entry, offsets.ap_hashlist_offset);
        let candidate = *field_ptr::<CLong>(ap, offsets.ap_apid_offset);
        let flags = *field_ptr::<CInt>(ap, offsets.ap_flags_offset);
        match xpmem_object_lookup_decision_result(candidate, apid, flags, 0, 1) {
            XPMEM_LOOKUP_TAKE => {
                ap_ref_fn(ap);
                rwlock_unlock_fn(lock, rwlock_node);
                return ap;
            }
            XPMEM_LOOKUP_STOP => break,
            _ => {}
        }
        entry = list_next(entry);
    }

    rwlock_unlock_fn(lock, rwlock_node);
    err_ptr(-ENOENT)
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_deref_body_result(
    object: *mut c_void,
    offsets: *const XpmemDerefOffsets,
    require_destroying: CInt,
    atomic_read_fn: Option<XpmemAtomicReadFn>,
    atomic_dec_fn: Option<XpmemAtomicDecFn>,
    bug_on_fn: Option<XpmemBugOnFn>,
    free_log_fn: Option<XpmemObjectVoidFn>,
    free_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(atomic_read_fn) = atomic_read_fn else {
        return -EINVAL;
    };
    let Some(atomic_dec_fn) = atomic_dec_fn else {
        return -EINVAL;
    };
    let Some(bug_on_fn) = bug_on_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    if object.is_null() {
        return -EINVAL;
    }

    let refcnt = field_ptr::<c_void>(object, offsets.refcnt_offset);
    bug_on_fn((atomic_read_fn(refcnt) <= 0) as CInt);
    if xpmem_ref_drop_should_free_result(atomic_dec_fn(refcnt)) == 0 {
        return 0;
    }

    if require_destroying != 0 {
        let flags = *field_ptr::<CInt>(object, offsets.flags_offset);
        bug_on_fn(((flags & XPMEM_FLAG_DESTROYING) == 0) as CInt);
    }

    if let Some(free_log_fn) = free_log_fn {
        free_log_fn(object);
    }
    free_fn(object);
    1
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_destroyable_wrapper_result(
    object: *mut c_void,
    log_fn: Option<XpmemDestroyableLogFn>,
    deref_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(deref_fn) = deref_fn else {
        return -EINVAL;
    };

    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_DESTROYABLE_LOG_CALL);
    }
    deref_fn(object);
    if let Some(log_fn) = log_fn {
        log_fn(XPMEM_DESTROYABLE_LOG_RETURN);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_destroyable(tg: *mut c_void) {
    xpmem_destroyable_wrapper_result(tg, Some(xpmem_destroyable_log), Some(xpmem_tg_deref_bridge));
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_seg_destroyable(seg: *mut c_void) {
    xpmem_destroyable_wrapper_result(
        seg,
        Some(xpmem_destroyable_log),
        Some(xpmem_seg_deref_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_ap_destroyable(ap: *mut c_void) {
    xpmem_destroyable_wrapper_result(ap, Some(xpmem_destroyable_log), Some(xpmem_ap_deref_bridge));
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_att_destroyable(att: *mut c_void) {
    xpmem_destroyable_wrapper_result(
        att,
        Some(xpmem_destroyable_log),
        Some(xpmem_att_deref_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_not_destroyable_wrapper_result(
    object: *mut c_void,
    kind: CInt,
    refcnt_ptr_fn: Option<XpmemRefcntPtrFn>,
    atomic_set_fn: Option<XpmemAtomicSetFn>,
    atomic_read_fn: Option<XpmemAtomicReadFn>,
    log_fn: Option<XpmemRefcntLogFn>,
) -> CInt {
    let Some(refcnt_ptr_fn) = refcnt_ptr_fn else {
        return -EINVAL;
    };
    let Some(atomic_set_fn) = atomic_set_fn else {
        return -EINVAL;
    };
    let Some(atomic_read_fn) = atomic_read_fn else {
        return -EINVAL;
    };

    let refcnt = refcnt_ptr_fn(object, kind);
    if refcnt.is_null() {
        return -EINVAL;
    }

    atomic_set_fn(refcnt, 1);
    if let Some(log_fn) = log_fn {
        log_fn(kind, atomic_read_fn(refcnt));
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_ref_wrapper_result(
    object: *mut c_void,
    kind: CInt,
    refcnt_ptr_fn: Option<XpmemRefcntPtrFn>,
    atomic_read_fn: Option<XpmemAtomicReadFn>,
    atomic_inc_fn: Option<XpmemAtomicIncFn>,
    bug_on_fn: Option<XpmemBugOnFn>,
) -> CInt {
    let Some(refcnt_ptr_fn) = refcnt_ptr_fn else {
        return -EINVAL;
    };
    let Some(atomic_read_fn) = atomic_read_fn else {
        return -EINVAL;
    };
    let Some(atomic_inc_fn) = atomic_inc_fn else {
        return -EINVAL;
    };
    let Some(bug_on_fn) = bug_on_fn else {
        return -EINVAL;
    };

    let refcnt = refcnt_ptr_fn(object, kind);
    if refcnt.is_null() {
        return -EINVAL;
    }

    bug_on_fn((atomic_read_fn(refcnt) <= 0) as CInt);
    atomic_inc_fn(refcnt);

    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_not_destroyable(tg: *mut c_void) {
    xpmem_not_destroyable_wrapper_result(
        tg,
        XPMEM_REF_KIND_TG,
        Some(xpmem_refcnt_ptr_bridge),
        Some(xpmem_atomic_set_bridge),
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_refcnt_log),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_seg_not_destroyable(seg: *mut c_void) {
    xpmem_not_destroyable_wrapper_result(
        seg,
        XPMEM_REF_KIND_SEG,
        Some(xpmem_refcnt_ptr_bridge),
        Some(xpmem_atomic_set_bridge),
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_refcnt_log),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_ap_not_destroyable(ap: *mut c_void) {
    xpmem_not_destroyable_wrapper_result(
        ap,
        XPMEM_REF_KIND_AP,
        Some(xpmem_refcnt_ptr_bridge),
        Some(xpmem_atomic_set_bridge),
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_refcnt_log),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_att_not_destroyable(att: *mut c_void) {
    xpmem_not_destroyable_wrapper_result(
        att,
        XPMEM_REF_KIND_ATT,
        Some(xpmem_refcnt_ptr_bridge),
        Some(xpmem_atomic_set_bridge),
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_refcnt_log),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_tg_ref(tg: *mut c_void) {
    xpmem_ref_wrapper_result(
        tg,
        XPMEM_REF_KIND_TG,
        Some(xpmem_refcnt_ptr_bridge),
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_atomic_inc_bridge),
        Some(xpmem_bug_on_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_seg_ref(seg: *mut c_void) {
    xpmem_ref_wrapper_result(
        seg,
        XPMEM_REF_KIND_SEG,
        Some(xpmem_refcnt_ptr_bridge),
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_atomic_inc_bridge),
        Some(xpmem_bug_on_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_ap_ref(ap: *mut c_void) {
    xpmem_ref_wrapper_result(
        ap,
        XPMEM_REF_KIND_AP,
        Some(xpmem_refcnt_ptr_bridge),
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_atomic_inc_bridge),
        Some(xpmem_bug_on_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_att_ref(att: *mut c_void) {
    xpmem_ref_wrapper_result(
        att,
        XPMEM_REF_KIND_ATT,
        Some(xpmem_refcnt_ptr_bridge),
        Some(xpmem_atomic_read_bridge),
        Some(xpmem_atomic_inc_bridge),
        Some(xpmem_bug_on_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_make_object_id_body_result(
    tg: *mut c_void,
    offsets: *const XpmemMakeIdOffsets,
    atomic_inc_fn: Option<XpmemAtomicIncFn>,
    atomic_dec_fn: Option<XpmemAtomicDecFn>,
    bug_on_fn: Option<XpmemBugOnFn>,
) -> CLong {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL as CLong;
    };
    let Some(atomic_inc_fn) = atomic_inc_fn else {
        return -EINVAL as CLong;
    };
    let Some(atomic_dec_fn) = atomic_dec_fn else {
        return -EINVAL as CLong;
    };
    let Some(bug_on_fn) = bug_on_fn else {
        return -EINVAL as CLong;
    };
    if tg.is_null() {
        return -EINVAL as CLong;
    }

    let uniq_counter = field_ptr::<c_void>(tg, offsets.tg_uniq_offset);
    let uniq = atomic_inc_fn(uniq_counter);
    let tgid = *field_ptr::<CInt>(tg, offsets.tg_tgid_offset);
    let mut id: CLong = 0;
    let ret = xpmem_make_id_result(tgid, uniq, &mut id);
    if ret != 0 {
        atomic_dec_fn(uniq_counter);
        return ret as CLong;
    }

    bug_on_fn((id <= 0) as CInt);
    id
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_validate_access_body_result(
    ap: *mut c_void,
    current_proc: *mut c_void,
    offset: OffT,
    size: SizeT,
    mode: CInt,
    vaddrp: *mut CULong,
    offsets: *const XpmemValidateAccessOffsets,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    if ap.is_null() || current_proc.is_null() || vaddrp.is_null() {
        return -EINVAL;
    }

    let tg = *field_ptr::<*mut c_void>(ap, offsets.ap_tg_offset);
    let seg = *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset);
    if tg.is_null() || seg.is_null() {
        return -EINVAL;
    }

    xpmem_validate_access_result(
        *field_ptr::<CInt>(current_proc, offsets.proc_pid_offset),
        *field_ptr::<CInt>(tg, offsets.tg_tgid_offset),
        *field_ptr::<CInt>(ap, offsets.ap_mode_offset),
        *field_ptr::<CULong>(seg, offsets.seg_vaddr_offset),
        *field_ptr::<SizeT>(seg, offsets.seg_size_offset),
        offset,
        size,
        mode,
        vaddrp,
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_is_remote_vm_body_result(
    current_proc: *mut c_void,
    vm: *mut c_void,
    offsets: *const XpmemValidateAccessOffsets,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return 1;
    };
    if current_proc.is_null() {
        return 1;
    }

    let current_vm = *field_ptr::<*mut c_void>(current_proc, offsets.proc_vm_offset);
    (current_vm != vm) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_perms_body_result(
    perm: *mut c_void,
    flag: CInt,
    current_proc: *mut c_void,
    offsets: *const XpmemPermOffsets,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    if perm.is_null() || current_proc.is_null() {
        return -EINVAL;
    }

    xpmem_perms_result(
        *field_ptr::<CInt>(perm, offsets.perm_uid_offset),
        *field_ptr::<CInt>(perm, offsets.perm_gid_offset),
        *field_ptr::<CULong>(perm, offsets.perm_mode_offset),
        flag as i16 as CInt,
        *field_ptr::<CInt>(current_proc, offsets.proc_ruid_offset),
        *field_ptr::<CInt>(current_proc, offsets.proc_rgid_offset),
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_check_permit_mode_body_result(
    flags: CInt,
    seg: *mut c_void,
    current_proc: *mut c_void,
    offsets: *const XpmemPermOffsets,
    bug_on_fn: Option<XpmemBugOnFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(bug_on_fn) = bug_on_fn else {
        return -EINVAL;
    };
    if seg.is_null() || current_proc.is_null() {
        return -EINVAL;
    }

    bug_on_fn(
        (*field_ptr::<CInt>(seg, offsets.seg_permit_type_offset) != XPMEM_PERMIT_MODE) as CInt,
    );
    let tg = *field_ptr::<*mut c_void>(seg, offsets.seg_tg_offset);
    if tg.is_null() {
        return -EINVAL;
    }
    xpmem_check_permit_mode_result(
        flags,
        *field_ptr::<CInt>(tg, offsets.tg_uid_offset),
        *field_ptr::<CInt>(tg, offsets.tg_gid_offset),
        *field_ptr::<CULong>(seg, offsets.seg_permit_value_offset),
        *field_ptr::<CInt>(current_proc, offsets.proc_ruid_offset),
        *field_ptr::<CInt>(current_proc, offsets.proc_rgid_offset),
    )
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_make_segment_body_result(
    vaddr: CULong,
    size: SizeT,
    permit_type: CInt,
    permit_value: *mut c_void,
    segidp: *mut CLong,
    current_proc: *mut c_void,
    offsets: *const XpmemMakeSegmentOffsets,
    rwlock_node: *mut c_void,
    tg_ref_fn: Option<XpmemTgRefFn>,
    tg_deref_fn: Option<XpmemObjectVoidFn>,
    make_segid_fn: Option<XpmemObjectIdFn>,
    alloc_fn: Option<XpmemAllocFn>,
    spinlock_init_fn: Option<XpmemObjectVoidFn>,
    list_init_fn: Option<XpmemObjectVoidFn>,
    seg_not_destroyable_fn: Option<XpmemObjectVoidFn>,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    list_add_tail_fn: Option<XpmemListAddTailFn>,
    bug_on_fn: Option<XpmemBugOnFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(tg_ref_fn) = tg_ref_fn else {
        return -EINVAL;
    };
    let Some(tg_deref_fn) = tg_deref_fn else {
        return -EINVAL;
    };
    let Some(make_segid_fn) = make_segid_fn else {
        return -EINVAL;
    };
    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };
    let Some(spinlock_init_fn) = spinlock_init_fn else {
        return -EINVAL;
    };
    let Some(list_init_fn) = list_init_fn else {
        return -EINVAL;
    };
    let Some(seg_not_destroyable_fn) = seg_not_destroyable_fn else {
        return -EINVAL;
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return -EINVAL;
    };
    let Some(list_add_tail_fn) = list_add_tail_fn else {
        return -EINVAL;
    };
    let Some(bug_on_fn) = bug_on_fn else {
        return -EINVAL;
    };
    if segidp.is_null() || current_proc.is_null() || rwlock_node.is_null() {
        return -EINVAL;
    }

    let ret = xpmem_make_initial_policy_result(permit_type, permit_value as CULong, size);
    if ret != 0 {
        return ret;
    }

    let pid = *field_ptr::<CInt>(current_proc, offsets.proc_pid_offset);
    let seg_tg = tg_ref_fn(pid);
    if ptr_is_err(seg_tg) {
        bug_on_fn((ptr_err(seg_tg) != -ENOENT) as CInt);
        return -XPMEM_ERRNO_NOPROC;
    }

    let ret = xpmem_make_alignment_result(vaddr, size);
    if ret != 0 {
        tg_deref_fn(seg_tg);
        return ret;
    }

    let segid = make_segid_fn(seg_tg);
    if segid < 0 {
        tg_deref_fn(seg_tg);
        return segid as CInt;
    }

    let seg = alloc_fn(offsets.seg_size);
    if seg.is_null() {
        tg_deref_fn(seg_tg);
        return -ENOMEM;
    }
    write_bytes(seg, 0, offsets.seg_size);

    spinlock_init_fn(field_ptr::<c_void>(seg, offsets.seg_lock_offset));
    *field_ptr::<CLong>(seg, offsets.seg_segid_offset) = segid;
    *field_ptr::<CULong>(seg, offsets.seg_vaddr_offset) = vaddr;
    *field_ptr::<SizeT>(seg, offsets.seg_size_offset) = size;
    *field_ptr::<CInt>(seg, offsets.seg_permit_type_offset) = permit_type;
    *field_ptr::<*mut c_void>(seg, offsets.seg_permit_value_offset) = permit_value;
    *field_ptr::<*mut c_void>(seg, offsets.seg_tg_offset) = seg_tg;
    list_init_fn(field_ptr::<c_void>(seg, offsets.seg_ap_list_offset));
    list_init_fn(field_ptr::<c_void>(seg, offsets.seg_seg_list_offset));
    seg_not_destroyable_fn(seg);

    let lock = field_ptr::<c_void>(seg_tg, offsets.tg_seg_list_lock_offset);
    rwlock_lock_fn(lock, rwlock_node);
    list_add_tail_fn(
        field_ptr::<c_void>(seg, offsets.seg_seg_list_offset),
        field_ptr::<c_void>(seg_tg, offsets.tg_seg_list_offset),
    );
    rwlock_unlock_fn(lock, rwlock_node);

    tg_deref_fn(seg_tg);
    write(segidp, segid);

    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_get_body_result(
    segid: CLong,
    flags: CInt,
    permit_type: CInt,
    permit_value: *mut c_void,
    apidp: *mut CLong,
    current_proc: *mut c_void,
    offsets: *const XpmemGetOffsets,
    rwlock_node: *mut c_void,
    tg_ref_by_segid_fn: Option<XpmemIdRefFn>,
    seg_ref_by_segid_fn: Option<XpmemRefByIdFn>,
    check_permit_fn: Option<XpmemCheckPermitFn>,
    tg_ref_by_tgid_fn: Option<XpmemTgRefFn>,
    make_apid_fn: Option<XpmemObjectIdFn>,
    alloc_fn: Option<XpmemAllocFn>,
    spinlock_init_fn: Option<XpmemObjectVoidFn>,
    list_init_fn: Option<XpmemObjectVoidFn>,
    ap_not_destroyable_fn: Option<XpmemObjectVoidFn>,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    rwlock_lock_fn: Option<XpmemRwlockFn>,
    rwlock_unlock_fn: Option<XpmemRwlockFn>,
    list_add_tail_fn: Option<XpmemListAddTailFn>,
    seg_deref_fn: Option<XpmemObjectVoidFn>,
    tg_deref_fn: Option<XpmemObjectVoidFn>,
    bug_on_fn: Option<XpmemBugOnFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let Some(tg_ref_by_segid_fn) = tg_ref_by_segid_fn else {
        return -EINVAL;
    };
    let Some(seg_ref_by_segid_fn) = seg_ref_by_segid_fn else {
        return -EINVAL;
    };
    let Some(check_permit_fn) = check_permit_fn else {
        return -EINVAL;
    };
    let Some(tg_ref_by_tgid_fn) = tg_ref_by_tgid_fn else {
        return -EINVAL;
    };
    let Some(make_apid_fn) = make_apid_fn else {
        return -EINVAL;
    };
    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };
    let Some(spinlock_init_fn) = spinlock_init_fn else {
        return -EINVAL;
    };
    let Some(list_init_fn) = list_init_fn else {
        return -EINVAL;
    };
    let Some(ap_not_destroyable_fn) = ap_not_destroyable_fn else {
        return -EINVAL;
    };
    let Some(spin_lock_fn) = spin_lock_fn else {
        return -EINVAL;
    };
    let Some(spin_unlock_fn) = spin_unlock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_lock_fn) = rwlock_lock_fn else {
        return -EINVAL;
    };
    let Some(rwlock_unlock_fn) = rwlock_unlock_fn else {
        return -EINVAL;
    };
    let Some(list_add_tail_fn) = list_add_tail_fn else {
        return -EINVAL;
    };
    let Some(seg_deref_fn) = seg_deref_fn else {
        return -EINVAL;
    };
    let Some(tg_deref_fn) = tg_deref_fn else {
        return -EINVAL;
    };
    let Some(bug_on_fn) = bug_on_fn else {
        return -EINVAL;
    };
    if apidp.is_null() || current_proc.is_null() || rwlock_node.is_null() {
        return -EINVAL;
    }

    let ret = xpmem_get_policy_result(segid, flags, permit_type, (!permit_value.is_null()) as CInt);
    if ret != 0 {
        return ret;
    }

    let seg_tg = tg_ref_by_segid_fn(segid);
    if seg_tg.is_null() || ptr_is_err(seg_tg) {
        return ptr_err(seg_tg);
    }

    let seg = seg_ref_by_segid_fn(seg_tg, segid);
    if seg.is_null() || ptr_is_err(seg) {
        tg_deref_fn(seg_tg);
        return ptr_err(seg);
    }

    if check_permit_fn(flags, seg) != 0 {
        seg_deref_fn(seg);
        tg_deref_fn(seg_tg);
        return -EACCES;
    }

    let pid = *field_ptr::<CInt>(current_proc, offsets.proc_pid_offset);
    let ap_tg = tg_ref_by_tgid_fn(pid);
    if ptr_is_err(ap_tg) {
        bug_on_fn((ptr_err(ap_tg) != -ENOENT) as CInt);
        seg_deref_fn(seg);
        tg_deref_fn(seg_tg);
        return -XPMEM_ERRNO_NOPROC;
    }
    if ap_tg.is_null() {
        seg_deref_fn(seg);
        tg_deref_fn(seg_tg);
        return -XPMEM_ERRNO_NOPROC;
    }

    let apid = make_apid_fn(ap_tg);
    if apid < 0 {
        tg_deref_fn(ap_tg);
        seg_deref_fn(seg);
        tg_deref_fn(seg_tg);
        return apid as CInt;
    }

    let ap = alloc_fn(offsets.ap_size);
    if ap.is_null() {
        tg_deref_fn(ap_tg);
        seg_deref_fn(seg);
        tg_deref_fn(seg_tg);
        return -ENOMEM;
    }
    write_bytes(ap, 0, offsets.ap_size);

    spinlock_init_fn(field_ptr::<c_void>(ap, offsets.ap_lock_offset));
    *field_ptr::<CLong>(ap, offsets.ap_apid_offset) = apid;
    *field_ptr::<CInt>(ap, offsets.ap_mode_offset) = flags;
    *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset) = seg;
    *field_ptr::<*mut c_void>(ap, offsets.ap_tg_offset) = ap_tg;
    list_init_fn(field_ptr::<c_void>(ap, offsets.ap_att_list_offset));
    list_init_fn(field_ptr::<c_void>(ap, offsets.ap_ap_list_offset));
    list_init_fn(field_ptr::<c_void>(ap, offsets.ap_hashlist_offset));
    ap_not_destroyable_fn(ap);

    let seg_lock = field_ptr::<c_void>(seg, offsets.seg_lock_offset);
    spin_lock_fn(seg_lock);
    list_add_tail_fn(
        field_ptr::<c_void>(ap, offsets.ap_ap_list_offset),
        field_ptr::<c_void>(seg, offsets.seg_ap_list_offset),
    );
    spin_unlock_fn(seg_lock);

    let index = xpmem_ap_hashtable_index_result(apid) as SizeT;
    let hashlist = (ap_tg as *mut u8)
        .add(offsets.tg_ap_hashtable_offset)
        .add(index * offsets.hashlist_stride)
        .cast::<c_void>();
    let hash_lock = field_ptr::<c_void>(hashlist, offsets.hashlist_lock_offset);
    rwlock_lock_fn(hash_lock, rwlock_node);
    list_add_tail_fn(
        field_ptr::<c_void>(ap, offsets.ap_hashlist_offset),
        field_ptr::<c_void>(hashlist, offsets.hashlist_list_offset),
    );
    rwlock_unlock_fn(hash_lock, rwlock_node);

    tg_deref_fn(ap_tg);
    write(apidp, apid);

    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_attach_body_result(
    mckfd: *mut c_void,
    apid: CLong,
    offset: OffT,
    size: SizeT,
    vaddr: CULong,
    at_vaddr_p: *mut CULong,
    current_pid: CInt,
    current_vm: *mut c_void,
    fjmpi_workaround: CInt,
    prot_flags: CULong,
    map_shared: CULong,
    map_fixed: CULong,
    map_anonymous: CULong,
    vr_xpmem: CULong,
    offsets: *const XpmemAttachOffsets,
    tg_ref_by_apid_fn: Option<XpmemIdRefFn>,
    ap_ref_by_apid_fn: Option<XpmemRefByIdFn>,
    seg_ref_fn: Option<XpmemObjectVoidFn>,
    seg_deref_fn: Option<XpmemObjectVoidFn>,
    tg_ref_fn: Option<XpmemObjectVoidFn>,
    tg_deref_fn: Option<XpmemObjectVoidFn>,
    ap_deref_fn: Option<XpmemObjectVoidFn>,
    validate_access_fn: Option<XpmemValidateAccessCallbackFn>,
    alloc_fn: Option<XpmemAllocFn>,
    rwspin_init_fn: Option<XpmemObjectVoidFn>,
    list_init_fn: Option<XpmemObjectVoidFn>,
    att_not_destroyable_fn: Option<XpmemObjectVoidFn>,
    att_ref_fn: Option<XpmemObjectVoidFn>,
    att_deref_fn: Option<XpmemObjectVoidFn>,
    att_write_lock_fn: Option<XpmemRwspinLockFn>,
    att_write_unlock_fn: Option<XpmemRwspinUnlockFn>,
    spin_lock_fn: Option<XpmemSpinFn>,
    spin_unlock_fn: Option<XpmemSpinFn>,
    list_add_tail_fn: Option<XpmemListAddTailFn>,
    read_lock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    read_unlock_noirq_fn: Option<XpmemRwspinNoirqFn>,
    lookup_range_fn: Option<XpmemLookupRangeFn>,
    next_range_fn: Option<XpmemNextRangeFn>,
    mmap_fn: Option<XpmemMmapFn>,
    list_del_init_fn: Option<XpmemListFn>,
    att_destroyable_fn: Option<XpmemObjectVoidFn>,
) -> CInt {
    let Some(offsets) = offsets.as_ref() else {
        return -EINVAL;
    };
    let (
        Some(tg_ref_by_apid_fn),
        Some(ap_ref_by_apid_fn),
        Some(seg_ref_fn),
        Some(seg_deref_fn),
        Some(tg_ref_fn),
        Some(tg_deref_fn),
        Some(ap_deref_fn),
        Some(validate_access_fn),
        Some(alloc_fn),
        Some(rwspin_init_fn),
        Some(list_init_fn),
        Some(att_not_destroyable_fn),
        Some(att_ref_fn),
        Some(att_deref_fn),
        Some(att_write_lock_fn),
        Some(att_write_unlock_fn),
        Some(spin_lock_fn),
        Some(spin_unlock_fn),
        Some(list_add_tail_fn),
        Some(read_lock_noirq_fn),
        Some(read_unlock_noirq_fn),
        Some(lookup_range_fn),
        Some(next_range_fn),
        Some(mmap_fn),
        Some(list_del_init_fn),
        Some(att_destroyable_fn),
    ) = (
        tg_ref_by_apid_fn,
        ap_ref_by_apid_fn,
        seg_ref_fn,
        seg_deref_fn,
        tg_ref_fn,
        tg_deref_fn,
        ap_deref_fn,
        validate_access_fn,
        alloc_fn,
        rwspin_init_fn,
        list_init_fn,
        att_not_destroyable_fn,
        att_ref_fn,
        att_deref_fn,
        att_write_lock_fn,
        att_write_unlock_fn,
        spin_lock_fn,
        spin_unlock_fn,
        list_add_tail_fn,
        read_lock_noirq_fn,
        read_unlock_noirq_fn,
        lookup_range_fn,
        next_range_fn,
        mmap_fn,
        list_del_init_fn,
        att_destroyable_fn,
    )
    else {
        return -EINVAL;
    };
    if mckfd.is_null() || at_vaddr_p.is_null() || current_vm.is_null() {
        return -EINVAL;
    }

    let mut adjusted_size = size;
    let mut ret = xpmem_attach_initial_policy_result(
        apid,
        offset,
        vaddr,
        size,
        fjmpi_workaround,
        &mut adjusted_size,
    );
    if ret != 0 {
        return ret;
    }

    let ap_tg = tg_ref_by_apid_fn(apid);
    if ptr_is_err(ap_tg) || ap_tg.is_null() {
        return ptr_err(ap_tg);
    }

    let ap = ap_ref_by_apid_fn(ap_tg, apid);
    if ptr_is_err(ap) || ap.is_null() {
        tg_deref_fn(ap_tg);
        return ptr_err(ap);
    }

    let mut seg = *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset);
    if seg.is_null() {
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        return -EINVAL;
    }
    seg_ref_fn(seg);
    let seg_tg = *field_ptr::<*mut c_void>(seg, offsets.seg_tg_offset);
    if seg_tg.is_null() {
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        seg_deref_fn(seg);
        return -EINVAL;
    }
    tg_ref_fn(seg_tg);

    ret = xpmem_attach_destroying_result(
        *field_ptr::<CInt>(seg, offsets.seg_flags_offset),
        *field_ptr::<CInt>(seg_tg, offsets.tg_flags_offset),
    );
    if ret != 0 {
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        seg_deref_fn(seg);
        tg_deref_fn(seg_tg);
        return ret;
    }

    let mut seg_vaddr: CULong = 0;
    ret = validate_access_fn(ap, offset, adjusted_size, XPMEM_RDWR, &mut seg_vaddr);
    if ret != 0 {
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        seg_deref_fn(seg);
        tg_deref_fn(seg_tg);
        return ret;
    }

    adjusted_size = adjusted_size.wrapping_add(offset_in_page(seg_vaddr) as SizeT);
    seg = *field_ptr::<*mut c_void>(ap, offsets.ap_seg_offset);
    ret = xpmem_attach_overlap_result(
        current_pid,
        *field_ptr::<CInt>(seg_tg, offsets.tg_tgid_offset),
        vaddr,
        adjusted_size,
        seg_vaddr,
    );
    if ret != 0 {
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        seg_deref_fn(seg);
        tg_deref_fn(seg_tg);
        return ret;
    }

    let att = alloc_fn(offsets.att_size);
    if att.is_null() {
        ap_deref_fn(ap);
        tg_deref_fn(ap_tg);
        seg_deref_fn(seg);
        tg_deref_fn(seg_tg);
        return -ENOMEM;
    }
    write_bytes(att, 0, offsets.att_size);

    rwspin_init_fn(field_ptr::<c_void>(att, offsets.att_at_lock_offset));
    *field_ptr::<CULong>(att, offsets.att_vaddr_offset) = seg_vaddr;
    *field_ptr::<SizeT>(att, offsets.att_at_size_offset) = adjusted_size;
    *field_ptr::<*mut c_void>(att, offsets.att_ap_offset) = ap;
    list_init_fn(field_ptr::<c_void>(att, offsets.att_att_list_offset));
    *field_ptr::<*mut c_void>(att, offsets.att_vm_offset) = current_vm;
    att_not_destroyable_fn(att);
    att_ref_fn(att);

    let att_lock = field_ptr::<c_void>(att, offsets.att_at_lock_offset);
    let at_lock = att_write_lock_fn(att_lock);

    let ap_lock = field_ptr::<c_void>(ap, offsets.ap_lock_offset);
    spin_lock_fn(ap_lock);
    list_add_tail_fn(
        field_ptr::<c_void>(att, offsets.att_att_list_offset),
        field_ptr::<c_void>(ap, offsets.ap_att_list_offset),
    );
    ret = xpmem_destroying_error_result(*field_ptr::<CInt>(ap, offsets.ap_flags_offset), -ENOENT);
    if ret != 0 {
        spin_unlock_fn(ap_lock);
    } else {
        spin_unlock_fn(ap_lock);

        let mut map_flags = map_shared;
        if vaddr != 0 {
            map_flags |= map_fixed;
        }

        if (map_flags & map_fixed) != 0 {
            let range_lock = field_ptr::<c_void>(current_vm, offsets.vm_memory_range_lock_offset);
            let end = vaddr.wrapping_add(adjusted_size as CULong);
            read_lock_noirq_fn(range_lock);
            let mut range = lookup_range_fn(current_vm, vaddr, end);
            while !range.is_null() && *field_ptr::<CULong>(range, offsets.range_start_offset) < end
            {
                if !(*field_ptr::<*mut c_void>(range, offsets.range_private_data_offset)).is_null()
                {
                    ret = -EINVAL;
                    break;
                }
                range = next_range_fn(current_vm, range);
            }
            read_unlock_noirq_fn(range_lock);
        }

        if ret == 0 {
            map_flags |= map_anonymous;
            let mmap_vaddr = mmap_fn(
                vaddr,
                adjusted_size,
                prot_flags,
                map_flags,
                *field_ptr::<CInt>(mckfd, offsets.mckfd_fd_offset),
                offset,
                vr_xpmem,
                att,
            );
            if ptr_is_err(mmap_vaddr as usize as *mut c_void) {
                ret = mmap_vaddr as CInt;
            } else {
                write(
                    at_vaddr_p,
                    mmap_vaddr.wrapping_add(offset_in_page(*field_ptr::<CULong>(
                        att,
                        offsets.att_vaddr_offset,
                    ))),
                );
            }
        }
    }

    if ret != 0 {
        let mut new_flags = 0;
        let flags_ptr = field_ptr::<CInt>(att, offsets.att_flags_offset);
        let _ = xpmem_begin_destroy_result(*flags_ptr, &mut new_flags);
        *flags_ptr = new_flags;
        spin_lock_fn(ap_lock);
        list_del_init_fn(field_ptr::<c_void>(att, offsets.att_att_list_offset));
        spin_unlock_fn(ap_lock);
        att_destroyable_fn(att);
    }
    att_write_unlock_fn(att_lock, at_lock);
    att_deref_fn(att);
    ap_deref_fn(ap);
    tg_deref_fn(ap_tg);
    seg_deref_fn(seg);
    tg_deref_fn(seg_tg);

    ret
}

#[no_mangle]
pub extern "C" fn xpmem_detach_lookup_result(
    has_range: CInt,
    range_start: CULong,
    at_vaddr: CULong,
    has_private_data: CInt,
) -> CInt {
    if has_range == 0 || range_start > at_vaddr {
        return 0;
    }

    if has_private_data == 0 {
        return -EINVAL;
    }

    XPMEM_DETACH_LOOKUP_CONTINUE
}

#[no_mangle]
pub extern "C" fn xpmem_attach_overlap_result(
    current_pid: CInt,
    seg_tgid: CInt,
    requested_vaddr: CULong,
    size: SizeT,
    seg_vaddr: CULong,
) -> CInt {
    if current_pid == seg_tgid
        && requested_vaddr != 0
        && requested_vaddr.wrapping_add(size as CULong) > seg_vaddr
        && requested_vaddr < seg_vaddr.wrapping_add(size as CULong)
    {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_range_step_result(
    range_start: CULong,
    range_end: CULong,
    start: CULong,
    end: CULong,
    range_flags: CULong,
    has_private_data: CInt,
    split_startp: *mut CInt,
    split_endp: *mut CInt,
    ro_freedp: *mut CInt,
    remove_privatep: *mut CInt,
) -> CInt {
    write(split_startp, if range_start < start { 1 } else { 0 });
    write(split_endp, if end < range_end { 1 } else { 0 });
    write(
        ro_freedp,
        if (range_flags & VR_PROT_WRITE) == 0 {
            1
        } else {
            0
        },
    );
    write(remove_privatep, if has_private_data != 0 { 1 } else { 0 });
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_memory_range_action_result(
    vmr_start: CULong,
    vmr_end: CULong,
    att_at_vaddr: CULong,
    att_at_size: SizeT,
    remaining_vaddrp: *mut CULong,
    middle_lookup_vaddrp: *mut CULong,
    full_detachp: *mut CInt,
    needs_middle_lookupp: *mut CInt,
) -> CInt {
    let att_end = att_at_vaddr.wrapping_add(att_at_size as CULong);

    if vmr_start == att_at_vaddr && vmr_end.wrapping_sub(vmr_start) == att_at_size as CULong {
        write(full_detachp, 1);
        write(needs_middle_lookupp, 0);
        write(remaining_vaddrp, 0);
        write(middle_lookup_vaddrp, 0);
        return 0;
    }

    write(full_detachp, 0);
    if vmr_start == att_at_vaddr {
        write(remaining_vaddrp, vmr_end);
        write(middle_lookup_vaddrp, 0);
        write(needs_middle_lookupp, 0);
    } else if vmr_end == att_end {
        write(remaining_vaddrp, att_at_vaddr);
        write(middle_lookup_vaddrp, 0);
        write(needs_middle_lookupp, 0);
    } else {
        write(remaining_vaddrp, att_at_vaddr);
        write(middle_lookup_vaddrp, vmr_end);
        write(needs_middle_lookupp, 1);
    }

    0
}

#[no_mangle]
pub extern "C" fn xpmem_range_private_invalid_result(
    has_range: CInt,
    range_start: CULong,
    vaddr: CULong,
    private_matches: CInt,
) -> CInt {
    if has_range == 0 || range_start > vaddr || private_matches == 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_clear_pte_range_result(
    att_flags: CInt,
    att_vaddr: CULong,
    att_at_vaddr: CULong,
    att_at_size: SizeT,
    start: CULong,
    end: CULong,
    unpin_atp: *mut CULong,
    invalidate_lenp: *mut CULong,
    clear_validp: *mut CInt,
) -> CInt {
    write(unpin_atp, 0);
    write(invalidate_lenp, 0);
    write(clear_validp, 0);

    if (att_flags & XPMEM_FLAG_VALIDPTES) == 0 {
        return 0;
    }

    let att_vaddr_end = att_vaddr.wrapping_add(att_at_size as CULong);
    let invalidate_start = if start > att_vaddr { start } else { att_vaddr };
    let invalidate_end = if end < att_vaddr_end {
        end
    } else {
        att_vaddr_end
    };

    if invalidate_start >= att_vaddr_end || invalidate_end <= att_vaddr {
        return 0;
    }

    let offset_start = invalidate_start.wrapping_sub(att_vaddr);
    let offset_end = invalidate_end.wrapping_sub(att_vaddr);
    let invalidate_len = offset_end.wrapping_sub(offset_start);

    write(unpin_atp, att_at_vaddr.wrapping_add(offset_start));
    write(invalidate_lenp, invalidate_len);
    write(
        clear_validp,
        if offset_start == 0 && att_at_size as CULong == invalidate_len {
            1
        } else {
            0
        },
    );
    1
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_fault_vaddr_result(
    vaddr: CULong,
    att_at_vaddr: CULong,
    att_at_size: SizeT,
    att_vaddr: CULong,
    seg_vaddrp: *mut CULong,
) -> CInt {
    if vaddr < att_at_vaddr
        || vaddr.wrapping_add(1) > att_at_vaddr.wrapping_add(att_at_size as CULong)
    {
        return -EFAULT;
    }

    write(
        seg_vaddrp,
        att_vaddr.wrapping_add(vaddr.wrapping_sub(att_at_vaddr)),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_straight_phys_result(
    seg_vaddr: CULong,
    straight_va: CULong,
    straight_len: SizeT,
    straight_pa: CULong,
    seg_physp: *mut CULong,
    seg_pgsizep: *mut SizeT,
) -> CInt {
    if straight_va != 0
        && seg_vaddr >= straight_va
        && seg_vaddr < straight_va.wrapping_add(straight_len as CULong)
    {
        write(
            seg_physp,
            ((seg_vaddr & PAGE_MASK).wrapping_sub(straight_va)).wrapping_add(straight_pa),
        );
        write(seg_pgsizep, 1usize << 29);
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_remote_pte_missing_result(
    has_pte: CInt,
    pte_is_empty: CInt,
    page_in_remote: CInt,
) -> CInt {
    if has_pte == 0 || pte_is_empty != 0 {
        if page_in_remote != 0 {
            -EFAULT
        } else {
            0
        }
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn xpmem_seg_phys_plus_off_result(
    seg_phys: CULong,
    seg_pgsize: SizeT,
    seg_vaddr: CULong,
) -> CULong {
    (seg_phys & !(seg_pgsize as CULong - 1)) | (seg_vaddr & (seg_pgsize as CULong - 1))
}

#[no_mangle]
pub extern "C" fn xpmem_att_page_fits_result(
    att_pgaddr: CULong,
    att_pgsize: SizeT,
    vmr_start: CULong,
    vmr_end: CULong,
    seg_pgsize: SizeT,
) -> CInt {
    if att_pgaddr < vmr_start
        || vmr_end < att_pgaddr.wrapping_add(att_pgsize as CULong)
        || att_pgsize > seg_pgsize
    {
        0
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn xpmem_pte_mismatch_result(att_phys: CULong, seg_phys_aligned: CULong) -> CInt {
    if att_phys != seg_phys_aligned {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_unpin_step_result(
    vaddr: CULong,
    vsize: SizeT,
    has_present_pte: CInt,
    next_vaddrp: *mut CULong,
    unpinnedp: *mut CInt,
) -> CInt {
    if has_present_pte != 0 {
        write(next_vaddrp, vaddr.wrapping_add(vsize as CULong));
        write(unpinnedp, 1);
    } else {
        write(
            next_vaddrp,
            (vaddr.wrapping_add(vsize as CULong)) & !(vsize as CULong - 1),
        );
        write(unpinnedp, 0);
    }
    0
}
