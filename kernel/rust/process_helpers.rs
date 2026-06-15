use core::ffi::c_void;
use core::mem::{MaybeUninit, size_of};
use core::ptr::{copy_nonoverlapping, null_mut, write_volatile};
use core::sync::atomic::{AtomicI32, Ordering};

use crate::abi::{
    AUXV_LEN, AbiListHead, CInt, CLong, CPU_SET_MAX_CPUS, CULong, CpuLocalVar, CpuSet, IhkAtomic,
    IhkSpinlock, Memobj, OffT, PROCESS_HASH_SIZE, PROCESS_NUMA_MASK_BITS, Process, ProcessHash,
    ProcessVm, ProgramLoadDesc, ResourceSet, SizeT, Thread, ThreadHash, VM_RANGE_CACHE_SIZE,
    VmRange,
};
use crate::rbtree::{
    RbNode, RbRoot, rb_erase, rb_first, rb_insert_color, rb_link_node, rb_next, rb_prev,
};

unsafe extern "C" {
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
    fn memobj_ref(obj: *mut Memobj) -> CInt;
    fn memobj_unref(obj: *mut Memobj) -> CInt;
}

const EINVAL: CInt = 22;
const EACCES: CInt = 13;
const EFAULT: CInt = 14;
const ENOMEM: CInt = 12;
const E2BIG: CInt = 7;
const EPERM: CInt = 1;
const ENOENT: CInt = 2;
const ECANCELED: CInt = 125;
const ERESTART: CInt = 85;

const PAGE_SIZE: CULong = 4096;
const PAGE_SHIFT: CULong = 12;
const PF_WRITE: CULong = 1 << 1;
const PF_INSTR: CULong = 1 << 4;
const PF_PATCH: CULong = 1 << 29;
const PF_POPULATE: CULong = 1 << 30;

const VERIFY_READ: CInt = 0;
const VERIFY_WRITE: CInt = 1;

const PS_EXITED: CInt = 0x10;
const PT_TRACED: CInt = 0x80;
const PT_TRACE_EXEC: CInt = 0x100;
const PT_TRACE_SYSCALL: CInt = 0x200;
const PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG: CInt = 1;
const PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG: CInt = 2;
const UTI_STATE_EPILOGUE: CInt = 3;
const PROCESS_TID_ACTION_NONE: CInt = 0;
const PROCESS_TID_ACTION_RELEASE: CInt = 1;
const PROCESS_TID_ACTION_REPLACE: CInt = 2;
const PROCESS_CREATE_CPU_LOG_INVALID: CInt = 1;
const PROCESS_CREATE_CPU_LOG_REQUESTED: CInt = 2;
const PROCESS_PTRACE_TRACEME_LOG_ENTER: CInt = 1;
const PROCESS_PTRACE_TRACEME_LOG_PARENT: CInt = 2;
const PROCESS_PTRACE_TRACEME_LOG_RETURN: CInt = 3;
const CLONE_VM: CInt = 0x0000_0100;
const CLONE_SIGHAND: CInt = 0x0000_0800;
const WNOWAIT: CInt = 0x0100_0000;
const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;
const MPOL_DEFAULT: CInt = 0;

const VR_RESERVED: CULong = 0x2;
const VR_STACK: CULong = 0x1;
const VR_AP_USER: CULong = 0x4;
const VR_IO_NOCACHE: CULong = 0x100;
const VR_REMOTE: CULong = 0x200;
const VR_WRITE_COMBINED: CULong = 0x400;
const VR_DONTFORK: CULong = 0x800;
const VR_DEMAND_PAGING: CULong = 0x1000;
const VR_PRIVATE: CULong = 0x2000;
const VR_XPMEM: CULong = 0x4000_0000;
const VR_PROT_NONE: CULong = 0x0000_0000;
const VR_PROT_READ: CULong = 0x0001_0000;
const VR_PROT_WRITE: CULong = 0x0002_0000;
const VR_PROT_EXEC: CULong = 0x0004_0000;
const VR_PROT_MASK: CULong = 0x0007_0000;
const VR_MAXPROT_READ: CULong = 0x0010_0000;
const VR_MAXPROT_WRITE: CULong = 0x0020_0000;
const VR_MAXPROT_EXEC: CULong = 0x0040_0000;
const VR_MAXPROT_MASK: CULong = 0x0070_0000;
const NOPHYS: CULong = !0;
const HASH_SIZE: CInt = PROCESS_HASH_SIZE as CInt;

const MF_SHM: u32 = 0x40000;
const MF_HUGETLBFS: u32 = 0x100000;
const MF_ZEROFILL: u32 = 0x0010;
const VPTEF_SKIP_NULL: CInt = 0x0001;
const MCK_RLIMIT_STACK: usize = 15;
const IHK_UCR_STACK_POINTER: CInt = 1;
const AT_NULL: CULong = 0;
const AT_IGNORE: CULong = 1;
const AT_PHDR: CULong = 3;
const AT_PHENT: CULong = 4;
const AT_PHNUM: CULong = 5;
const AT_PAGESZ: CULong = 6;
const AT_BASE: CULong = 7;
const AT_FLAGS: CULong = 8;
const AT_ENTRY: CULong = 9;
const AT_UID: CULong = 11;
const AT_EUID: CULong = 12;
const AT_GID: CULong = 13;
const AT_EGID: CULong = 14;
const AT_HWCAP: CULong = 16;
const AT_CLKTCK: CULong = 17;
const AT_SECURE: CULong = 23;
const AT_RANDOM: CULong = 25;
const AT_HWCAP2: CULong = 26;
const AT_EXECFN: CULong = 31;
const AT_SYSINFO_EHDR: CULong = 33;

const PROCESS_ADD_RANGE_MAP_SKIP: CInt = 0;
const PROCESS_ADD_RANGE_MAP_UPDATE: CInt = 1;
const PROCESS_ADD_RANGE_MAP_MARK_XPMEM: CInt = 2;
const PROCESS_ADD_RANGE_MAP_DEMAND: CInt = 3;
const PROCESS_ADD_RANGE_LOG_ALLOC_FAILED: CInt = 1;
const PROCESS_ADD_RANGE_LOG_INSERT_FAILED: CInt = 2;
const PROCESS_ADD_RANGE_LOG_PREP_FAILED: CInt = 3;
const PROCESS_ADD_RANGE_LOG_DEMAND: CInt = 4;
const PROCESS_ADD_RANGE_LOG_BOUNDS_FAILED: CInt = 5;
const PROCESS_VM_RANGE_INSERT_LOG_OVERLAP: CInt = 1;
const PROCESS_VM_RANGE_INSERT_LOG_SUCCESS: CInt = 2;
const PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER: CInt = 1;
const PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT: CInt = 2;
const PROCESS_RANGE_PUBLIC_LOG_NEXT_ENTER: CInt = 3;
const PROCESS_RANGE_PUBLIC_LOG_NEXT_EXIT: CInt = 4;
const PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_ENTER: CInt = 5;
const PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_EXIT: CInt = 6;
const PROCESS_RANGE_PUBLIC_LOG_EXTEND_ENTER: CInt = 7;
const PROCESS_RANGE_PUBLIC_LOG_EXTEND_EXIT: CInt = 8;
const PROCESS_CHANGE_PROT_PUBLIC_LOG_ENTER: CInt = 1;
const PROCESS_CHANGE_PROT_PUBLIC_LOG_ERROR: CInt = 2;
const PROCESS_CHANGE_PROT_PUBLIC_LOG_EXIT: CInt = 3;
const PROCESS_FREE_RANGE_PT_SKIP: CInt = 0;
const PROCESS_FREE_RANGE_PT_FREE: CInt = 1;
const PROCESS_FREE_RANGE_PT_CLEAR: CInt = 2;
const PROCESS_REMOVE_STRAIGHT_NO_CONVERT: CInt = 0;
const PROCESS_REMOVE_STRAIGHT_NEED_RANGE: CInt = 1;
const PROCESS_REMOVE_STRAIGHT_CONVERTED: CInt = 2;
const PROCESS_REMOVE_RANGE_LOG_NO_STRAIGHT: CInt = 1;
const PROCESS_REMOVE_RANGE_LOG_CONVERTED: CInt = 2;
const PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED: CInt = 3;
const PROCESS_REMOVE_RANGE_LOG_FREE_FAILED: CInt = 4;
const PROCESS_REMOVE_RANGE_LOG_DONE: CInt = 5;
const PROCESS_FREE_BODY_LOG_PLAN_FAILED: CInt = 1;
const PROCESS_FREE_BODY_LOG_PT_FREE_FAILED: CInt = 2;
const PROCESS_FREE_BODY_LOG_PT_CLEAR_FAILED: CInt = 3;
const PROCESS_FREE_BODY_LOG_TOFU_REMOVED: CInt = 4;
const PROCESS_FREE_BODY_LOG_FINALIZE_FAILED: CInt = 5;
const PROCESS_FREE_BODY_LOG_DONE: CInt = 6;
const PROCESS_REMAP_RANGE_LOG_PGSHIFT: CInt = 1;
const PROCESS_REMAP_RANGE_LOG_VISIT_FAILED: CInt = 2;
const PROCESS_INIT_STACK_LOG_SIZE: CInt = 1;
const PROCESS_INIT_STACK_LOG_AP_USER: CInt = 2;
const PROCESS_INIT_STACK_LOG_ALLOC_FAILED: CInt = 3;
const PROCESS_INIT_STACK_LOG_ADD_FAILED: CInt = 4;
const PROCESS_INIT_STACK_LOG_PT_FAILED: CInt = 5;
const PROCESS_INIT_STACK_LOG_AUXV: CInt = 6;
const PROCESS_INIT_STACK_LOG_SIZE_MISMATCH: CInt = 7;
const PROCESS_INIT_STACK_LOG_ALIGN_MISMATCH: CInt = 8;
const PROCESS_INIT_STACK_LOG_INITIAL: CInt = 9;
const PROCESS_SPLIT_SHM_LOG_LOOKUP_FAILED: CInt = 1;
const PROCESS_SPLIT_SHM_LOG_UPDATE_FAILED: CInt = 2;

const PTATTR_ACTIVE: CULong = 0x01;
const PTATTR_WRITABLE: CULong = 0x02;
const PTATTR_USER: CULong = 0x04;
const PTATTR_NO_EXECUTE: CULong = 0x8000_0000_0000_0000;
const PTATTR_UNCACHABLE: CULong = 0x10000;
const PTATTR_FOR_USER: CULong = 0x20000;
const PTATTR_WRITE_COMBINED: CULong = 0x40000;
const IHK_PTA_REMOTE: CULong = 0;

#[repr(C)]
pub struct ProcessInitStateOffsets {
    pub pid_offset: CULong,
    pub status_offset: CULong,
    pub parent_offset: CULong,
    pub ppid_parent_offset: CULong,
    pub pgid_offset: CULong,
    pub ruid_offset: CULong,
    pub euid_offset: CULong,
    pub suid_offset: CULong,
    pub fsuid_offset: CULong,
    pub rgid_offset: CULong,
    pub egid_offset: CULong,
    pub sgid_offset: CULong,
    pub fsgid_offset: CULong,
    pub mpol_flags_offset: CULong,
    pub mpol_threshold_offset: CULong,
    pub thp_disable_offset: CULong,
    pub rlimit_offset: CULong,
    pub rlimit_size: CULong,
    pub cpu_set_offset: CULong,
    pub cpu_set_size: CULong,
    pub enable_uti_offset: CULong,
}

#[repr(C)]
pub struct ProcessPtraceTracemeOffsets {
    pub thread_proc_offset: CULong,
    pub thread_report_proc_offset: CULong,
    pub thread_report_siblings_list_offset: CULong,
    pub thread_ptrace_offset: CULong,
    pub thread_ptrace_debugreg_offset: CULong,
    pub proc_pid_offset: CULong,
    pub proc_parent_offset: CULong,
    pub proc_main_thread_offset: CULong,
    pub proc_children_lock_offset: CULong,
    pub proc_threads_lock_offset: CULong,
    pub proc_ptraced_siblings_list_offset: CULong,
    pub proc_ptraced_children_list_offset: CULong,
    pub proc_report_threads_list_offset: CULong,
}

#[repr(C)]
pub struct ProcessPtraceAttachOffsets {
    pub thread_proc_offset: CULong,
    pub thread_report_proc_offset: CULong,
    pub thread_report_siblings_list_offset: CULong,
    pub thread_ptrace_debugreg_offset: CULong,
    pub proc_pid_offset: CULong,
    pub proc_parent_offset: CULong,
    pub proc_main_thread_offset: CULong,
    pub proc_children_lock_offset: CULong,
    pub proc_threads_lock_offset: CULong,
    pub proc_children_list_offset: CULong,
    pub proc_siblings_list_offset: CULong,
    pub proc_ptraced_siblings_list_offset: CULong,
    pub proc_ptraced_children_list_offset: CULong,
    pub proc_report_threads_list_offset: CULong,
}

#[repr(C)]
pub struct ProcessFindThreadOffsets {
    pub thread_hash_list_offset: CULong,
    pub thread_tid_offset: CULong,
    pub thread_proc_offset: CULong,
    pub proc_pid_offset: CULong,
}

#[repr(C)]
pub struct ProcessFindProcessOffsets {
    pub process_hash_list_offset: CULong,
    pub process_pid_offset: CULong,
}

type ProcessAddRangeAllocFn = unsafe extern "C" fn(CULong) -> *mut VmRange;
type ProcessAddRangeFreeFn = unsafe extern "C" fn(*mut VmRange);
type ProcessAddRangeInsertFn = unsafe extern "C" fn(*mut c_void, *mut VmRange) -> CInt;
type ProcessAddRangeUpdateFn =
    unsafe extern "C" fn(*mut c_void, *mut VmRange, CULong, CULong) -> CInt;
type ProcessAddRangeRemoveFn = unsafe extern "C" fn(*mut c_void, CULong, CULong);
type ProcessAddRangeMarkXpmemFn = unsafe extern "C" fn(*mut VmRange);
type ProcessAddRangeMemclearFn = unsafe extern "C" fn(CULong, CULong);
type ProcessAddRangeLogFn = unsafe extern "C" fn(CInt, CInt, CULong, CULong);
type ProcessVmRangeInsertLogFn =
    unsafe extern "C" fn(CInt, *mut c_void, *mut VmRange, *mut VmRange);
type ProcessVmRangeInsertDumpFn = unsafe extern "C" fn(*mut c_void);
type ProcessRangePublicLogFn =
    unsafe extern "C" fn(CInt, *mut c_void, *mut VmRange, CULong, CULong, CInt);
type ProcessChangeProtPublicLogFn =
    unsafe extern "C" fn(CInt, *mut c_void, *mut VmRange, CULong, CInt);
type ProcessAccessOkLogFn = unsafe extern "C" fn(*mut ProcessVm, CInt, CULong, SizeT, CInt);
type ProcessRangeMemobjRefFn = unsafe extern "C" fn(*mut c_void);
type ProcessSplitRangeInsertFn = unsafe extern "C" fn(*mut c_void, *mut VmRange) -> CInt;
type ProcessSplitRangeAllocFn = unsafe extern "C" fn(CULong, CULong) -> *mut VmRange;
type ProcessSplitRangeAllocLogFn =
    unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, *mut c_void);
type ProcessSplitRangePublishLogFn = unsafe extern "C" fn(CInt);
type ProcessSplitRangePtSplitFn =
    unsafe extern "C" fn(*mut c_void, *mut ProcessVm, *mut VmRange, *mut c_void) -> CInt;
type ProcessSplitRangePtLogFn = unsafe extern "C" fn(CInt);
type ProcessSplitShmLookupPageFn =
    unsafe extern "C" fn(*mut c_void, OffT, CInt, *mut CULong, *mut CULong) -> CInt;
type ProcessSplitShmPhysToPageFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessSplitShmUpdatePageFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, *mut c_void) -> CInt;
type ProcessSplitShmLogFn = unsafe extern "C" fn(CInt, CInt);
type ProcessJoinRangeFreeFn = unsafe extern "C" fn(*mut VmRange);
type ProcessJoinRangeTofuFn = unsafe extern "C" fn(*mut c_void, *mut VmRange, *mut VmRange) -> CInt;
type ProcessFreeRangePageSizeFn = unsafe extern "C" fn(SizeT, *mut SizeT) -> CInt;
type ProcessFreeRangePhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessFreeRangePagesFn = unsafe extern "C" fn(*mut c_void, CULong);
type ProcessFreeRangeClearMainFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CInt;
type ProcessFreeRangeFreeFn = unsafe extern "C" fn(*mut VmRange);
type ProcessFreeRangePtFreeFn =
    unsafe extern "C" fn(*mut c_void, *mut ProcessVm, CULong, CULong, *mut c_void) -> CInt;
type ProcessFreeRangePtClearFn =
    unsafe extern "C" fn(*mut c_void, *mut ProcessVm, CULong, CULong) -> CInt;
type ProcessFreeRangeTofuRemoveFn = unsafe extern "C" fn(*mut ProcessVm, *mut VmRange) -> CInt;
type ProcessFreeRangeLogFn =
    unsafe extern "C" fn(CInt, *mut ProcessVm, *mut VmRange, CULong, CULong, CInt);
type ProcessVisitPteRangeFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong, CInt, CInt, *mut c_void, *mut c_void) -> CInt;
type ProcessCopyRangeLookupFn =
    unsafe extern "C" fn(*mut ProcessVm, CULong, CULong) -> *mut VmRange;
type ProcessCopyRangeNextFn = unsafe extern "C" fn(*mut ProcessVm, *mut VmRange) -> *mut VmRange;
type ProcessCopyUserRangesLogFn = unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CLong);
type ProcessLookupPteFn =
    unsafe extern "C" fn(*mut c_void, CULong, CInt, *mut SizeT) -> *mut c_void;
type ProcessPteTestFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessPtePgsizeTestFn = unsafe extern "C" fn(*mut c_void, SizeT) -> CInt;
type ProcessSplitContiguousPagesFn = unsafe extern "C" fn(*mut c_void, SizeT, u32) -> CInt;
type ProcessPteGetPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type ProcessPhysToPageFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessPageOffsetFn = unsafe extern "C" fn(*mut c_void) -> OffT;
type ProcessPteMakeFileoffFn = unsafe extern "C" fn(OffT, SizeT, *mut c_void);
type ProcessPteXchgFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessFlushTlbSingleFn = unsafe extern "C" fn(CULong);
type ProcessPgsizeToTbllvFn = unsafe extern "C" fn(SizeT) -> CInt;
type ProcessTbllvToContpgsizeFn = unsafe extern "C" fn(CInt) -> SizeT;
type ProcessPageUnmapFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessPanicFn = unsafe extern "C" fn(*const i8);
type ProcessMemobjInvalidatePageFn = unsafe extern "C" fn(*mut Memobj, CULong, SizeT) -> CInt;
type ProcessInvalidateOnePageLogFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, CULong, *mut c_void, CInt, CInt);
type ProcessSyncRangeLogFn =
    unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, CULong, CInt);
type ProcessRemapRangeLogFn =
    unsafe extern "C" fn(CInt, *mut ProcessVm, *mut VmRange, CULong, CULong, OffT, CInt, CInt);
type ProcessMemoryRangeFreeFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type ProcessMemoryRangeLogFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CInt);
type ProcessMckfdCloseFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type ProcessMckfdDupFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type ProcessMckfdFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessPolicyFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessDetachAddressSpaceFn = unsafe extern "C" fn(*mut c_void, CInt);
type ProcessReleaseProcessFn = unsafe extern "C" fn(*mut c_void);
type ProcessOptionalFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessReleaseFpRegsFn = unsafe extern "C" fn(*mut c_void);
type ProcessRefIncFn = unsafe extern "C" fn(*mut c_void, CULong);
type ProcessRefDecAndTestFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;
type ProcessDefaultNcpusFn = unsafe extern "C" fn() -> CInt;
type ProcessCreateCpuLogFn = unsafe extern "C" fn(CInt, CInt, CInt);
type ProcessHoldThreadWarnFn = unsafe extern "C" fn(*mut c_void);
type ProcessCurrentResourceSetFn = unsafe extern "C" fn() -> *mut c_void;
type ProcessResourceProcessActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessProcessActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessResourceSetActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessTidLogFn = unsafe extern "C" fn(CInt, *mut c_void, CInt);
type ProcessThreadProfileFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessThreadActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessThreadProcActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessThreadTidActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CInt);
type ProcessVmActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessMcsRwlockFn = unsafe extern "C" fn(CULong, *mut c_void);
type ProcessAllocDebugregFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessPtraceTracemeLogFn = unsafe extern "C" fn(CInt, CInt, CULong, CInt);
type ProcessSpinLockFn = unsafe extern "C" fn(CULong) -> CULong;
type ProcessSpinUnlockFn = unsafe extern "C" fn(CULong, CULong);
type ProcessFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessVmFreeCallback = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessAddressSpaceFreeCallback = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessAddressSpaceActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessPtDestroyFn = unsafe extern "C" fn(*mut c_void);
type ProcessAllocFn = unsafe extern "C" fn(CULong, CULong) -> *mut c_void;
type ProcessPtCreateFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessRefSetFn = unsafe extern "C" fn(*mut c_void, CULong, CInt);
type ProcessSpinInitFn = unsafe extern "C" fn(CULong);
type ProcessRwlockInitFn = unsafe extern "C" fn(CULong);
type ProcessVmInitNumaLogFn = unsafe extern "C" fn(CInt);
type ProcessWaitqInitFn = unsafe extern "C" fn(CULong);
type ProcessMcsLockInitFn = unsafe extern "C" fn(CULong);
type ProcessAllocPagesFn = unsafe extern "C" fn(CInt, CULong) -> *mut c_void;
type ProcessCreateAddressSpaceFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type ProcessReleaseAddressSpaceFn = unsafe extern "C" fn(*mut c_void);
type ProcessInitProcessFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type ProcessInitProcessVmFn = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void) -> CInt;
type ProcessInitUserProcessFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong);
type ProcessSchedInitContextFn = unsafe extern "C" fn(*mut c_void);
type ProcessSchedSaveFpFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessSchedTimerInitFn = unsafe extern "C" fn(CInt);
type ProcessVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type ProcessPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessMemsetFn = unsafe extern "C" fn(*mut c_void, CInt, SizeT);
type ProcessMemsetSmpLogFn = unsafe extern "C" fn(CInt, CInt, CInt, CULong, SizeT, CULong, CULong);
type ProcessSmpCallFn = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void) -> CInt;
type ProcessAttrFromVrflagFn = unsafe extern "C" fn(CULong, CULong, *mut c_void) -> CULong;
type ProcessNoirqLockFn = unsafe extern "C" fn(CULong);
type ProcessNoirqUnlockFn = unsafe extern "C" fn(CULong);
type ProcessPtChangeAttrFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong, CULong) -> CInt;
type ProcessPtSetRangeFn = unsafe extern "C" fn(
    *mut c_void,
    *mut ProcessVm,
    CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    *mut VmRange,
    CInt,
) -> CInt;
type ProcessUpdatePageTableLogFn = unsafe extern "C" fn(CInt);
type ProcessFaultRangeFn =
    unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, CULong) -> CInt;
type ProcessZeroobjMatchFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessPageFaultVmFn = unsafe extern "C" fn(*mut ProcessVm, CULong, CULong) -> CInt;
type ProcessPreemptFn = unsafe extern "C" fn();
type ProcessPgioDispatchFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessPopulateWarnFn =
    unsafe extern "C" fn(*mut ProcessVm, CULong, CULong, CULong, SizeT, CInt);
type ProcessRemoveRangeSplitFn =
    unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, *mut *mut VmRange) -> CInt;
type ProcessRemoveRangeXpmemFn = unsafe extern "C" fn(*mut ProcessVm, *mut VmRange);
type ProcessRemoveRangeLogFn =
    unsafe extern "C" fn(CInt, *mut ProcessVm, CULong, CULong, *mut VmRange, CInt);
type ProcessRemoveRegionClearFn =
    unsafe extern "C" fn(*mut c_void, *mut ProcessVm, CULong, CULong) -> CInt;
type ProcessRemoveRegionLogFn = unsafe extern "C" fn(*mut ProcessVm, CULong, CULong);
type ProcessInitStackAllocAlignedFn =
    unsafe extern "C" fn(CInt, CInt, CULong, CULong) -> *mut c_void;
type ProcessInitStackFreePagesFn = unsafe extern "C" fn(*mut c_void, CInt);
type ProcessInitStackAddRangeFn = unsafe extern "C" fn(
    *mut ProcessVm,
    CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    *mut *mut VmRange,
) -> CInt;
type ProcessInitStackVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type ProcessInitStackPtSetRangeFn = unsafe extern "C" fn(
    *mut c_void,
    *mut ProcessVm,
    CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    *mut VmRange,
    CInt,
) -> CInt;
type ProcessInitStackHwcapFn = unsafe extern "C" fn() -> CULong;
type ProcessInitStackModifyContextFn = unsafe extern "C" fn(*mut c_void, CInt, CULong);
type ProcessInitStackLogFn = unsafe extern "C" fn(CInt, *const CULong);

#[no_mangle]
pub extern "C" fn PROT_TO_VR_FLAG(prot: CULong) -> CULong {
    (prot << 16) & VR_PROT_MASK
}

#[no_mangle]
pub extern "C" fn VRFLAG_PROT_TO_MAXPROT(vrflag: CULong) -> CULong {
    (vrflag & VR_PROT_MASK) << 4
}

#[no_mangle]
pub extern "C" fn VRFLAG_MAXPROT_TO_PROT(vrflag: CULong) -> CULong {
    (vrflag & VR_MAXPROT_MASK) >> 4
}

#[no_mangle]
pub extern "C" fn __WEXITSTATUS(status: CInt) -> CInt {
    (status & 0xff00) >> 8
}

#[no_mangle]
pub extern "C" fn __WTERMSIG(status: CInt) -> CInt {
    status & 0x7f
}

#[no_mangle]
pub extern "C" fn __WSTOPSIG(status: CInt) -> CInt {
    __WEXITSTATUS(status)
}

#[no_mangle]
pub extern "C" fn __WIFEXITED(status: CInt) -> CInt {
    (__WTERMSIG(status) == 0) as CInt
}

#[no_mangle]
pub extern "C" fn __WIFSIGNALED(status: CInt) -> CInt {
    ((((status & 0x7f) + 1) as i8) >> 1 > 0) as CInt
}

#[no_mangle]
pub extern "C" fn __WIFSTOPPED(status: CInt) -> CInt {
    ((status & 0xff) == 0x7f) as CInt
}

#[no_mangle]
pub extern "C" fn process_hash(pid: CInt) -> CInt {
    pid % HASH_SIZE
}

#[no_mangle]
pub extern "C" fn thread_hash(tid: CInt) -> CInt {
    tid % HASH_SIZE
}

#[no_mangle]
pub unsafe extern "C" fn has_cap_ipc_lock(th: *mut Thread) -> CInt {
    ((*(*th).proc).euid == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn has_cap_sys_admin(th: *mut Thread) -> CInt {
    ((*(*th).proc).euid == 0) as CInt
}

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

#[inline(always)]
#[cfg(enable_tofu)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_init_result(
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    flag: CULong,
    memobj: *mut c_void,
    offset: OffT,
    pgshift: CInt,
    private_data: *mut c_void,
) -> CInt {
    if range.is_null() {
        return 0;
    }

    (*range).vm_rb_node.__rb_parent_color = core::ptr::addr_of_mut!((*range).vm_rb_node) as CULong;
    (*range).start = start;
    (*range).end = end;
    (*range).flag = flag;
    (*range).memobj = memobj;
    (*range).objoff = offset;
    (*range).pgshift = pgshift;
    (*range).private_data = private_data;
    (*range).straight_start = 0;
    #[cfg(enable_tofu)]
    init_list_head(&raw mut (*range).tofu_stag_list);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_mapping_result(
    phys: CULong,
    flag: CULong,
    range_flag: CULong,
    attrp: *mut CULong,
    memclearp: *mut CInt,
) -> CInt {
    let mut attr = 0;
    let action = if phys == NOPHYS {
        PROCESS_ADD_RANGE_MAP_SKIP
    } else if (flag & VR_REMOTE) != 0 {
        attr = IHK_PTA_REMOTE;
        PROCESS_ADD_RANGE_MAP_UPDATE
    } else if (flag & VR_IO_NOCACHE) != 0 {
        attr = PTATTR_UNCACHABLE;
        PROCESS_ADD_RANGE_MAP_UPDATE
    } else if (flag & VR_XPMEM) != 0 {
        PROCESS_ADD_RANGE_MAP_MARK_XPMEM
    } else if (flag & VR_DEMAND_PAGING) != 0 {
        PROCESS_ADD_RANGE_MAP_DEMAND
    } else if (range_flag & VR_PROT_MASK) == VR_PROT_NONE {
        PROCESS_ADD_RANGE_MAP_SKIP
    } else {
        PROCESS_ADD_RANGE_MAP_UPDATE
    };

    let memclear = phys != NOPHYS
        && (flag & (VR_REMOTE | VR_DEMAND_PAGING | VR_XPMEM)) == 0
        && (flag & VR_PROT_MASK) != VR_PROT_NONE;

    if !attrp.is_null() {
        *attrp = attr;
    }
    if !memclearp.is_null() {
        *memclearp = memclear as CInt;
    }

    action
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_alloc_result(
    range_size: CULong,
    alloc_fn: Option<ProcessAddRangeAllocFn>,
) -> *mut VmRange {
    let Some(alloc) = alloc_fn else {
        return null_mut();
    };

    alloc(range_size)
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_free_result(
    range: *mut VmRange,
    free_fn: Option<ProcessAddRangeFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_insert_result(
    vm: *mut c_void,
    range: *mut VmRange,
    insert_fn: Option<ProcessAddRangeInsertFn>,
) -> CInt {
    let Some(insert) = insert_fn else {
        return -EINVAL;
    };

    insert(vm, range)
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_update_result(
    vm: *mut c_void,
    range: *mut VmRange,
    phys: CULong,
    attr: CULong,
    update_fn: Option<ProcessAddRangeUpdateFn>,
) -> CInt {
    let Some(update) = update_fn else {
        return -EINVAL;
    };

    update(vm, range, phys, attr)
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_remove_result(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    remove_fn: Option<ProcessAddRangeRemoveFn>,
) -> CInt {
    let Some(remove) = remove_fn else {
        return -EINVAL;
    };

    remove(vm, start, end);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_mark_xpmem_result(
    range: *mut VmRange,
    mark_xpmem_fn: Option<ProcessAddRangeMarkXpmemFn>,
) -> CInt {
    let Some(mark_xpmem) = mark_xpmem_fn else {
        return -EINVAL;
    };

    mark_xpmem(range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_memclear_result(
    phys: CULong,
    bytes: CULong,
    memclear_fn: Option<ProcessAddRangeMemclearFn>,
) -> CInt {
    let Some(memclear) = memclear_fn else {
        return -EINVAL;
    };

    memclear(phys, bytes);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_log_result(
    event: CInt,
    rc: CInt,
    start: CULong,
    end: CULong,
    log_fn: Option<ProcessAddRangeLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, rc, start, end);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_orchestrate_result(
    vm: *mut c_void,
    range_size: CULong,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    memobj: *mut c_void,
    offset: OffT,
    pgshift: CInt,
    private_data: *mut c_void,
    rp: *mut *mut VmRange,
    alloc_fn: Option<ProcessAddRangeAllocFn>,
    free_fn: Option<ProcessAddRangeFreeFn>,
    insert_fn: Option<ProcessAddRangeInsertFn>,
    update_fn: Option<ProcessAddRangeUpdateFn>,
    remove_fn: Option<ProcessAddRangeRemoveFn>,
    mark_xpmem_fn: Option<ProcessAddRangeMarkXpmemFn>,
    memclear_fn: Option<ProcessAddRangeMemclearFn>,
    log_fn: Option<ProcessAddRangeLogFn>,
) -> CInt {
    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    let Some(insert_fn) = insert_fn else {
        return -EINVAL;
    };
    let Some(update_fn) = update_fn else {
        return -EINVAL;
    };
    let Some(remove_fn) = remove_fn else {
        return -EINVAL;
    };
    let Some(mark_xpmem_fn) = mark_xpmem_fn else {
        return -EINVAL;
    };
    let Some(memclear_fn) = memclear_fn else {
        return -EINVAL;
    };

    let range = process_add_range_alloc_result(range_size, Some(alloc_fn));
    if range.is_null() {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_ALLOC_FAILED,
            -ENOMEM,
            start,
            end,
            log_fn,
        );
        return -ENOMEM;
    }

    process_add_range_init_result(
        range,
        start,
        end,
        flag,
        memobj,
        offset,
        pgshift,
        private_data,
    );

    let mut rc = process_add_range_insert_result(vm, range, Some(insert_fn));
    if rc != 0 {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_INSERT_FAILED,
            rc,
            start,
            end,
            log_fn,
        );
        let _ = process_add_range_free_result(range, Some(free_fn));
        return rc;
    }

    let mut map_attr = 0;
    let mut should_memclear = 0;
    let map_action = process_add_range_mapping_result(
        phys,
        flag,
        (*range).flag,
        &mut map_attr,
        &mut should_memclear,
    );
    if map_action == PROCESS_ADD_RANGE_MAP_UPDATE {
        rc = process_add_range_update_result(vm, range, phys, map_attr, Some(update_fn));
    } else if map_action == PROCESS_ADD_RANGE_MAP_MARK_XPMEM {
        let _ = process_add_range_mark_xpmem_result(range, Some(mark_xpmem_fn));
    } else if map_action == PROCESS_ADD_RANGE_MAP_DEMAND {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_DEMAND,
            0,
            (*range).start,
            (*range).end,
            log_fn,
        );
    }

    if rc != 0 {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_PREP_FAILED,
            rc,
            (*range).start,
            (*range).end,
            log_fn,
        );
        let _ = process_add_range_remove_result(vm, (*range).start, (*range).end, Some(remove_fn));
        let _ = process_add_range_free_result(range, Some(free_fn));
        return rc;
    }

    if should_memclear != 0 {
        let _ = process_add_range_memclear_result(phys, end - start, Some(memclear_fn));
    }

    if !rp.is_null() {
        *rp = range;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_public_body_result(
    vm: *mut c_void,
    range_size: CULong,
    user_start: CULong,
    user_end: CULong,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    memobj: *mut c_void,
    offset: OffT,
    pgshift: CInt,
    private_data: *mut c_void,
    rp: *mut *mut VmRange,
    alloc_fn: Option<ProcessAddRangeAllocFn>,
    free_fn: Option<ProcessAddRangeFreeFn>,
    insert_fn: Option<ProcessAddRangeInsertFn>,
    update_fn: Option<ProcessAddRangeUpdateFn>,
    remove_fn: Option<ProcessAddRangeRemoveFn>,
    mark_xpmem_fn: Option<ProcessAddRangeMarkXpmemFn>,
    memclear_fn: Option<ProcessAddRangeMemclearFn>,
    log_fn: Option<ProcessAddRangeLogFn>,
) -> CInt {
    let rc = process_add_range_bounds_result(user_start, user_end, start, end);
    if rc != 0 {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_BOUNDS_FAILED,
            rc,
            start,
            end,
            log_fn,
        );
        return rc;
    }

    process_add_range_orchestrate_result(
        vm,
        range_size,
        start,
        end,
        phys,
        flag,
        memobj,
        offset,
        pgshift,
        private_data,
        rp,
        alloc_fn,
        free_fn,
        insert_fn,
        update_fn,
        remove_fn,
        mark_xpmem_fn,
        memclear_fn,
        log_fn,
    )
}

#[inline(always)]
unsafe fn vm_range_rb_node(range: *mut VmRange) -> *mut RbNode {
    (&raw mut (*range).vm_rb_node).cast::<RbNode>()
}

#[inline(always)]
unsafe fn vm_range_from_rb_node(node: *mut RbNode) -> *mut VmRange {
    node.cast::<VmRange>()
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_range_insert_log_result(
    event: CInt,
    vm: *mut c_void,
    newrange: *mut VmRange,
    range: *mut VmRange,
    log_fn: Option<ProcessVmRangeInsertLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, vm, newrange, range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_range_insert_dump_result(
    vm: *mut c_void,
    dump_fn: Option<ProcessVmRangeInsertDumpFn>,
) -> CInt {
    let Some(dump) = dump_fn else {
        return 0;
    };

    dump(vm);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_range_insert_result(
    root: *mut RbRoot,
    newrange: *mut VmRange,
    vm: *mut c_void,
    log_fn: Option<ProcessVmRangeInsertLogFn>,
    dump_fn: Option<ProcessVmRangeInsertDumpFn>,
) -> CInt {
    if root.is_null() || newrange.is_null() {
        return -EINVAL;
    }

    let mut link: *mut *mut RbNode = &raw mut (*root).rb_node;
    let mut parent: *mut RbNode = null_mut();

    while !(*link).is_null() {
        let current = *link;
        let range = vm_range_from_rb_node(current);

        parent = current;
        if (*newrange).end <= (*range).start {
            link = &raw mut (*current).rb_left;
        } else if (*newrange).start >= (*range).end {
            link = &raw mut (*current).rb_right;
        } else {
            let _ = process_vm_range_insert_log_result(
                PROCESS_VM_RANGE_INSERT_LOG_OVERLAP,
                vm,
                newrange,
                range,
                log_fn,
            );
            return -EFAULT;
        }
    }

    let _ = process_vm_range_insert_log_result(
        PROCESS_VM_RANGE_INSERT_LOG_SUCCESS,
        vm,
        newrange,
        null_mut(),
        log_fn,
    );
    let _ = process_vm_range_insert_dump_result(vm, dump_fn);

    let node = vm_range_rb_node(newrange);
    rb_link_node(node, parent, link);
    rb_insert_color(node, root);

    0
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
pub unsafe extern "C" fn process_noirq_lock_result(
    lock_addr: CULong,
    lock_fn: Option<ProcessNoirqLockFn>,
) -> CInt {
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };

    lock(lock_addr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_noirq_unlock_result(
    lock_addr: CULong,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
) -> CInt {
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };

    unlock(lock_addr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_pt_change_attr_result(
    page_table: *mut c_void,
    start: CULong,
    end: CULong,
    clrattr: CULong,
    setattr: CULong,
    change_attr_fn: Option<ProcessPtChangeAttrFn>,
) -> CInt {
    let Some(change_attr) = change_attr_fn else {
        return -EINVAL;
    };

    change_attr(page_table, start, end, clrattr, setattr)
}

#[no_mangle]
pub unsafe extern "C" fn process_pt_set_range_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CULong,
    pgshift: CInt,
    range: *mut VmRange,
    flags: CInt,
    pt_set_range_fn: Option<ProcessPtSetRangeFn>,
) -> CInt {
    let Some(pt_set_range) = pt_set_range_fn else {
        return -EINVAL;
    };

    pt_set_range(
        page_table, vm, start, end, phys, attr, pgshift, range, flags,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_update_page_table_log_result(
    error: CInt,
    log_fn: Option<ProcessUpdatePageTableLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_zeroobj_match_result(
    memobj: *mut c_void,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
) -> CInt {
    let Some(zeroobj_match) = zeroobj_match_fn else {
        return -EINVAL;
    };

    zeroobj_match(memobj)
}

#[no_mangle]
pub unsafe extern "C" fn process_fault_range_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    fault_fn: Option<ProcessFaultRangeFn>,
) -> CInt {
    let Some(fault) = fault_fn else {
        return -EINVAL;
    };

    fault(vm, range, fault_addr, reason)
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

#[no_mangle]
pub extern "C" fn process_range_cache_hit_result(
    cache_start: CULong,
    cache_end: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    (cache_start <= start && cache_end >= end) as CInt
}

#[no_mangle]
pub extern "C" fn process_lookup_range_relation_result(
    start: CULong,
    end: CULong,
    range_start: CULong,
    range_end: CULong,
) -> CInt {
    if end <= range_start {
        -1
    } else if start >= range_end {
        1
    } else if start < range_start {
        -2
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_range_cache_replace_result(
    cache: *mut *mut c_void,
    count: CInt,
    from: *mut c_void,
    to: *mut c_void,
) -> CInt {
    if cache.is_null() || count <= 0 || from.is_null() {
        return 0;
    }

    let mut replaced = 0;
    let mut i = 0;
    while i < count {
        let slot = unsafe { cache.add(i as usize) };
        if unsafe { *slot == from } {
            unsafe {
                *slot = to;
            }
            replaced += 1;
        }
        i += 1;
    }

    replaced
}

#[no_mangle]
pub unsafe extern "C" fn process_range_cache_store_result(
    cache: *mut *mut c_void,
    count: CInt,
    indexp: *mut CInt,
    match_range: *mut c_void,
) -> CInt {
    if cache.is_null() || count <= 0 || indexp.is_null() || match_range.is_null() {
        return -EINVAL;
    }

    let new_index = unsafe { (*indexp - 1 + count) % count };
    unsafe {
        *indexp = new_index;
        *cache.add(new_index as usize) = match_range;
    }
    new_index
}

#[no_mangle]
pub unsafe extern "C" fn process_lookup_memory_range_body_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
) -> *mut VmRange {
    if vm.is_null() || end <= start {
        return null_mut();
    }

    let mut i = 0;
    let cache_base = (&raw mut (*vm).range_cache).cast::<*mut VmRange>();
    while i < crate::abi::VM_RANGE_CACHE_SIZE as CInt {
        let c_i = (i + (*vm).range_cache_ind) % crate::abi::VM_RANGE_CACHE_SIZE as CInt;
        let cached = *cache_base.add(c_i as usize);
        if !cached.is_null()
            && process_range_cache_hit_result((*cached).start, (*cached).end, start, end) != 0
        {
            return cached;
        }
        i += 1;
    }

    let mut node = (*vm).vm_range_tree.rb_node.cast::<RbNode>();
    let mut matched: *mut VmRange = null_mut();
    while !node.is_null() {
        let range = vm_range_from_rb_node(node);
        let relation =
            process_lookup_range_relation_result(start, end, (*range).start, (*range).end);
        if relation < -1 {
            matched = range;
            node = (*node).rb_left;
        } else if relation < 0 {
            node = (*node).rb_left;
        } else if relation > 0 {
            node = (*node).rb_right;
        } else {
            matched = range;
            break;
        }
    }

    if !matched.is_null() && end > (*matched).start {
        let cache = (&raw mut (*vm).range_cache).cast::<*mut c_void>();
        process_range_cache_store_result(
            cache,
            crate::abi::VM_RANGE_CACHE_SIZE as CInt,
            &raw mut (*vm).range_cache_ind,
            matched.cast(),
        );
    }

    matched
}

#[no_mangle]
pub unsafe extern "C" fn process_next_memory_range_body_result(
    range: *mut VmRange,
) -> *mut VmRange {
    if range.is_null() {
        return null_mut();
    }
    let node = rb_next(vm_range_rb_node(range));
    if node.is_null() {
        null_mut()
    } else {
        vm_range_from_rb_node(node)
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_previous_memory_range_body_result(
    range: *mut VmRange,
) -> *mut VmRange {
    if range.is_null() {
        return null_mut();
    }
    let node = rb_prev(vm_range_rb_node(range));
    if node.is_null() {
        null_mut()
    } else {
        vm_range_from_rb_node(node)
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_extend_up_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    newend: CULong,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }
    let next = process_next_memory_range_body_result(range);
    let error = process_extend_up_result(
        (*range).end,
        (*vm).region.user_end,
        (!next.is_null()) as CInt,
        if next.is_null() { 0 } else { (*next).start },
        newend,
    );
    if error != 0 {
        return error;
    }
    process_range_end_commit_result(range, newend);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_public_log_result(
    event: CInt,
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    error: CInt,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> CInt {
    if let Some(log_fn) = log_fn {
        log_fn(event, vm.cast(), range, start, end, error);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_lookup_memory_range_public_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> *mut VmRange {
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER,
        vm,
        null_mut(),
        start,
        end,
        0,
        log_fn,
    );
    let matched = process_lookup_memory_range_body_result(vm, start, end);
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT,
        vm,
        matched,
        start,
        end,
        0,
        log_fn,
    );
    matched
}

#[no_mangle]
pub unsafe extern "C" fn process_next_memory_range_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> *mut VmRange {
    let start = if range.is_null() { 0 } else { (*range).start };
    let end = if range.is_null() { 0 } else { (*range).end };
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_NEXT_ENTER,
        vm,
        range,
        start,
        end,
        0,
        log_fn,
    );
    let next = process_next_memory_range_body_result(range);
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_NEXT_EXIT,
        vm,
        next,
        start,
        end,
        0,
        log_fn,
    );
    next
}

#[no_mangle]
pub unsafe extern "C" fn process_previous_memory_range_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> *mut VmRange {
    let start = if range.is_null() { 0 } else { (*range).start };
    let end = if range.is_null() { 0 } else { (*range).end };
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_ENTER,
        vm,
        range,
        start,
        end,
        0,
        log_fn,
    );
    let prev = process_previous_memory_range_body_result(range);
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_EXIT,
        vm,
        prev,
        start,
        end,
        0,
        log_fn,
    );
    prev
}

#[no_mangle]
pub unsafe extern "C" fn process_extend_up_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    newend: CULong,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> CInt {
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_EXTEND_ENTER,
        vm,
        range,
        if range.is_null() { 0 } else { (*range).start },
        newend,
        0,
        log_fn,
    );
    let error = process_extend_up_body_result(vm, range, newend);
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_EXTEND_EXIT,
        vm,
        range,
        if range.is_null() { 0 } else { (*range).start },
        newend,
        error,
        log_fn,
    );
    error
}

#[no_mangle]
pub unsafe extern "C" fn process_change_prot_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    protflag: CULong,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    change_attr_fn: Option<ProcessPtChangeAttrFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }

    let newflag = process_change_prot_newflag_result((*range).flag, protflag);
    if (*range).flag == newflag {
        return 0;
    }

    if attr_fn.is_none() {
        return -EINVAL;
    }
    let mut clrattr = 0;
    let mut setattr = 0;
    process_attr_delta_result(
        process_attr_from_vrflag_result((*range).flag, PF_POPULATE, null_mut(), attr_fn),
        process_attr_from_vrflag_result(newflag, PF_POPULATE, null_mut(), attr_fn),
        &raw mut clrattr,
        &raw mut setattr,
    );

    if !(*range).memobj.is_null() && ((*range).flag & VR_PRIVATE) != 0 {
        let memobj = (*range).memobj.cast::<Memobj>();
        setattr = process_private_file_setattr_result(1, (*range).flag, (*memobj).flags, setattr);
        if clrattr == 0 && setattr == 0 {
            process_range_flag_commit_result(range, newflag);
            return 0;
        }
    }

    if lock_fn.is_none() || unlock_fn.is_none() || change_attr_fn.is_none() {
        return -EINVAL;
    }
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;
    let error = process_noirq_lock_result(lock_addr, lock_fn);
    if error != 0 {
        return error;
    }
    let error = process_pt_change_attr_result(
        (*address_space).page_table,
        (*range).start,
        (*range).end,
        clrattr,
        setattr,
        change_attr_fn,
    );
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);

    if error != 0 && error != -ENOENT {
        return error;
    }

    process_range_flag_commit_result(range, newflag);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_change_prot_public_log_result(
    event: CInt,
    vm: *mut ProcessVm,
    range: *mut VmRange,
    protflag: CULong,
    error: CInt,
    log_fn: Option<ProcessChangeProtPublicLogFn>,
) -> CInt {
    if let Some(log_fn) = log_fn {
        log_fn(event, vm.cast(), range, protflag, error);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_change_prot_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    protflag: CULong,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    change_attr_fn: Option<ProcessPtChangeAttrFn>,
    log_fn: Option<ProcessChangeProtPublicLogFn>,
) -> CInt {
    let _ = process_change_prot_public_log_result(
        PROCESS_CHANGE_PROT_PUBLIC_LOG_ENTER,
        vm,
        range,
        protflag,
        0,
        log_fn,
    );
    let error = process_change_prot_body_result(
        vm,
        range,
        protflag,
        attr_fn,
        lock_fn,
        unlock_fn,
        change_attr_fn,
    );
    if error != 0 && error != -ENOENT {
        let _ = process_change_prot_public_log_result(
            PROCESS_CHANGE_PROT_PUBLIC_LOG_ERROR,
            vm,
            range,
            protflag,
            error,
            log_fn,
        );
    }
    let _ = process_change_prot_public_log_result(
        PROCESS_CHANGE_PROT_PUBLIC_LOG_EXIT,
        vm,
        range,
        protflag,
        error,
        log_fn,
    );
    error
}

#[no_mangle]
pub unsafe extern "C" fn process_update_page_table_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    phys: CULong,
    populate_fault: CULong,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    pt_set_range_fn: Option<ProcessPtSetRangeFn>,
    log_fn: Option<ProcessUpdatePageTableLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }
    if attr_fn.is_none() || lock_fn.is_none() || unlock_fn.is_none() || pt_set_range_fn.is_none() {
        return -EINVAL;
    }

    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let attr = process_attr_from_vrflag_result((*range).flag, populate_fault, null_mut(), attr_fn);
    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;
    let irqstate = process_spin_lock_result(lock_addr, lock_fn);
    let error = process_pt_set_range_result(
        (*address_space).page_table,
        vm,
        (*range).start,
        (*range).end,
        phys,
        attr,
        (*range).pgshift,
        range,
        0,
        pt_set_range_fn,
    );
    let _ = process_spin_unlock_result(lock_addr, irqstate, unlock_fn);
    if error != 0 {
        let _ = process_update_page_table_log_result(error, log_fn);
        return error;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn process_update_page_table_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    phys: CULong,
    flag: CULong,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    pt_set_range_fn: Option<ProcessPtSetRangeFn>,
    log_fn: Option<ProcessUpdatePageTableLogFn>,
) -> CInt {
    let _ = flag;
    process_update_page_table_body_result(
        vm,
        range,
        phys,
        PF_POPULATE,
        attr_fn,
        lock_fn,
        unlock_fn,
        pt_set_range_fn,
        log_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_access_ok_body_result(
    vm: *mut ProcessVm,
    verify_type: CInt,
    addr: CULong,
    len: SizeT,
) -> CInt {
    if vm.is_null() {
        return -EFAULT;
    }

    let end = addr.wrapping_add(len as CULong);
    let mut range = process_lookup_memory_range_body_result(vm, addr, end);
    let mut rc = process_access_initial_result(
        (!range.is_null()) as CInt,
        if range.is_null() { 0 } else { (*range).start },
        addr,
    );
    if rc != 0 {
        return rc;
    }

    loop {
        rc = process_access_permission_result(verify_type, (*range).flag);
        if rc != 0 {
            return rc;
        }

        if end <= (*range).end {
            return 0;
        }

        let next = process_next_memory_range_body_result(range);
        rc = process_access_adjacent_result(
            (*range).end,
            (!next.is_null()) as CInt,
            if next.is_null() { 0 } else { (*next).start },
        );
        if rc != 0 {
            return rc;
        }
        range = next;
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_access_ok_log_result(
    vm: *mut ProcessVm,
    verify_type: CInt,
    addr: CULong,
    len: SizeT,
    error: CInt,
    log_fn: Option<ProcessAccessOkLogFn>,
) -> CInt {
    if let Some(log_fn) = log_fn {
        log_fn(vm, verify_type, addr, len, error);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_access_ok_public_result(
    vm: *mut ProcessVm,
    verify_type: CInt,
    addr: CULong,
    len: SizeT,
    log_fn: Option<ProcessAccessOkLogFn>,
) -> CInt {
    let error = process_access_ok_body_result(vm, verify_type, addr, len);
    if error != 0 {
        let _ = process_access_ok_log_result(vm, verify_type, addr, len, error, log_fn);
    }
    error
}

#[inline(always)]
unsafe fn process_do_page_fault_vm_body_impl(
    vm: *mut ProcessVm,
    current_vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    current_cpu: CInt,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    write_lock_fn: Option<ProcessNoirqLockFn>,
    write_unlock_fn: Option<ProcessNoirqUnlockFn>,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
    normal_fault_fn: Option<ProcessFaultRangeFn>,
    xpmem_fault_fn: Option<ProcessFaultRangeFn>,
) -> CInt {
    if vm.is_null() || current_vm.is_null() {
        return -EFAULT;
    }

    if read_lock_fn.is_none()
        || read_unlock_fn.is_none()
        || write_lock_fn.is_none()
        || write_unlock_fn.is_none()
        || normal_fault_fn.is_none()
        || xpmem_fault_fn.is_none()
    {
        return -EINVAL;
    }

    let mut range: *mut VmRange = null_mut();

    if fault_addr >= (*current_vm).region.stack_start && fault_addr < (*current_vm).region.stack_end
    {
        range = process_lookup_memory_range_body_result(
            vm,
            (*current_vm).region.stack_end.wrapping_sub(1),
            (*current_vm).region.stack_end,
        );
        if range.is_null() {
            return -EFAULT;
        }

        if (*range).memobj.is_null() && fault_addr < (*range).start {
            let mut write_locked = 0;
            if (*current_vm).is_memory_range_lock_taken == -1
                || (*current_vm).is_memory_range_lock_taken != current_cpu
            {
                let lock_addr = (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong;
                let error = process_noirq_lock_result(lock_addr, write_lock_fn);
                if error != 0 {
                    return error;
                }
                write_locked = 1;
            }

            process_range_stack_start_commit_result(range, fault_addr, (*range).pgshift);

            if write_locked != 0 {
                let _ = process_noirq_unlock_result(
                    (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong,
                    write_unlock_fn,
                );
            }
        }
    }

    let mut read_locked = 0;
    if (*current_vm).is_memory_range_lock_taken == -1
        || (*current_vm).is_memory_range_lock_taken != current_cpu
    {
        let error = process_noirq_lock_result(
            (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong,
            read_lock_fn,
        );
        if error != 0 {
            return error;
        }
        read_locked = 1;
    }

    let error;
    if (*vm).exiting != 0 {
        error = -ECANCELED;
        goto_unlock(read_locked, vm, read_unlock_fn);
        return error;
    }

    if range.is_null() {
        range = process_lookup_memory_range_body_result(vm, fault_addr, fault_addr.wrapping_add(1));
        if range.is_null() {
            error = -EFAULT;
            goto_unlock(read_locked, vm, read_unlock_fn);
            return error;
        }
    }

    if ((*range).flag & VR_PROT_MASK) == VR_PROT_NONE
        || (((reason & PF_WRITE) != 0 && (reason & PF_PATCH) == 0)
            && ((*range).flag & VR_PROT_WRITE) == 0)
        || ((reason & PF_INSTR) != 0 && ((*range).flag & VR_PROT_EXEC) == 0)
    {
        error = -EFAULT;
        goto_unlock(read_locked, vm, read_unlock_fn);
        return error;
    }

    let mut fault_reason = reason;
    if ((*range).flag & VR_PRIVATE) != 0 && !(*range).memobj.is_null() {
        if zeroobj_match_fn.is_none() {
            goto_unlock(read_locked, vm, read_unlock_fn);
            return -EINVAL;
        }
        if process_zeroobj_match_result((*range).memobj, zeroobj_match_fn) != 0 {
            fault_reason |= PF_POPULATE;
        }
    }

    error = if (*range).private_data.is_null() {
        process_fault_range_result(vm, range, fault_addr, fault_reason, normal_fault_fn)
    } else {
        process_fault_range_result(vm, range, fault_addr, fault_reason, xpmem_fault_fn)
    };

    goto_unlock(read_locked, vm, read_unlock_fn);
    error
}

#[no_mangle]
pub unsafe extern "C" fn process_do_page_fault_vm_body_result(
    vm: *mut ProcessVm,
    current_vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    current_cpu: CInt,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    write_lock_fn: Option<ProcessNoirqLockFn>,
    write_unlock_fn: Option<ProcessNoirqUnlockFn>,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
    normal_fault_fn: Option<ProcessFaultRangeFn>,
    xpmem_fault_fn: Option<ProcessFaultRangeFn>,
) -> CInt {
    unsafe {
        process_do_page_fault_vm_body_impl(
            vm,
            current_vm,
            fault_addr,
            reason,
            current_cpu,
            read_lock_fn,
            read_unlock_fn,
            write_lock_fn,
            write_unlock_fn,
            zeroobj_match_fn,
            normal_fault_fn,
            xpmem_fault_fn,
        )
    }
}

unsafe fn goto_unlock(locked: CInt, vm: *mut ProcessVm, unlock_fn: Option<ProcessNoirqUnlockFn>) {
    if locked != 0 {
        let _ = process_noirq_unlock_result(
            (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong,
            unlock_fn,
        );
    }
}

unsafe fn process_dispatch_pending_pgio(
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    dispatch: ProcessPgioDispatchFn,
) {
    if thread.is_null() {
        return;
    }

    let fp_slot = thread
        .cast::<u8>()
        .add(pgio_fp_offset as usize)
        .cast::<*mut c_void>();
    let arg_slot = thread
        .cast::<u8>()
        .add(pgio_arg_offset as usize)
        .cast::<*mut c_void>();
    let fp = *fp_slot;
    if !fp.is_null() {
        dispatch(fp, *arg_slot);
        *fp_slot = null_mut();
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_vm_dispatch_result(
    vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    fault_fn: Option<ProcessPageFaultVmFn>,
) -> CInt {
    let Some(fault) = fault_fn else {
        return -EINVAL;
    };

    fault(vm, fault_addr, reason)
}

#[no_mangle]
pub unsafe extern "C" fn process_preempt_result(preempt_fn: Option<ProcessPreemptFn>) -> CInt {
    let Some(preempt) = preempt_fn else {
        return -EINVAL;
    };

    preempt();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_pgio_dispatch_pending_result(
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    dispatch_fn: Option<ProcessPgioDispatchFn>,
) -> CInt {
    let Some(dispatch) = dispatch_fn else {
        return -EINVAL;
    };

    process_dispatch_pending_pgio(thread, pgio_fp_offset, pgio_arg_offset, dispatch);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_populate_warn_result(
    vm: *mut ProcessVm,
    addr: CULong,
    reason: CULong,
    off: CULong,
    len: SizeT,
    error: CInt,
    warn_fn: Option<ProcessPopulateWarnFn>,
) -> CInt {
    let Some(warn) = warn_fn else {
        return 0;
    };

    warn(vm, addr, reason, off, len, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_vm_public_result(
    vm: *mut ProcessVm,
    current_vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    current_cpu: CInt,
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    write_lock_fn: Option<ProcessNoirqLockFn>,
    write_unlock_fn: Option<ProcessNoirqUnlockFn>,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
    normal_fault_fn: Option<ProcessFaultRangeFn>,
    xpmem_fault_fn: Option<ProcessFaultRangeFn>,
    preempt_enable_fn: Option<ProcessPreemptFn>,
    preempt_disable_fn: Option<ProcessPreemptFn>,
    pgio_dispatch_fn: Option<ProcessPgioDispatchFn>,
) -> CInt {
    if preempt_enable_fn.is_none() || preempt_disable_fn.is_none() || pgio_dispatch_fn.is_none() {
        return -EINVAL;
    }

    loop {
        let error = unsafe {
            process_do_page_fault_vm_body_impl(
                vm,
                current_vm,
                fault_addr,
                reason,
                current_cpu,
                read_lock_fn,
                read_unlock_fn,
                write_lock_fn,
                write_unlock_fn,
                zeroobj_match_fn,
                normal_fault_fn,
                xpmem_fault_fn,
            )
        };
        if error != -ERESTART {
            return error;
        }

        unsafe {
            let _ = process_preempt_result(preempt_enable_fn);
            let _ = process_pgio_dispatch_pending_result(
                thread,
                pgio_fp_offset,
                pgio_arg_offset,
                pgio_dispatch_fn,
            );
            let _ = process_preempt_result(preempt_disable_fn);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_vm_retry_body_result(
    vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    do_fault_fn: Option<ProcessPageFaultVmFn>,
    preempt_enable_fn: Option<ProcessPreemptFn>,
    preempt_disable_fn: Option<ProcessPreemptFn>,
    pgio_dispatch_fn: Option<ProcessPgioDispatchFn>,
) -> CInt {
    if do_fault_fn.is_none()
        || preempt_enable_fn.is_none()
        || preempt_disable_fn.is_none()
        || pgio_dispatch_fn.is_none()
    {
        return -EINVAL;
    }

    loop {
        let error = process_page_fault_vm_dispatch_result(vm, fault_addr, reason, do_fault_fn);
        if error != -ERESTART {
            return error;
        }

        let _ = process_preempt_result(preempt_enable_fn);
        let _ = process_pgio_dispatch_pending_result(
            thread,
            pgio_fp_offset,
            pgio_arg_offset,
            pgio_dispatch_fn,
        );
        let _ = process_preempt_result(preempt_disable_fn);
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_populate_memory_body_result(
    vm: *mut ProcessVm,
    start: CULong,
    len: SizeT,
    page_size: CULong,
    reason: CULong,
    page_fault_fn: Option<ProcessPageFaultVmFn>,
    preempt_disable_fn: Option<ProcessPreemptFn>,
    preempt_enable_fn: Option<ProcessPreemptFn>,
    warn_fn: Option<ProcessPopulateWarnFn>,
) -> CInt {
    if page_fault_fn.is_none()
        || preempt_disable_fn.is_none()
        || preempt_enable_fn.is_none()
        || page_size == 0
    {
        return -EINVAL;
    }

    let end = start.wrapping_add(len as CULong);
    let _ = process_preempt_result(preempt_disable_fn);
    let mut addr = start;
    while addr < end {
        let error = process_page_fault_vm_dispatch_result(vm, addr, reason, page_fault_fn);
        if error != 0 {
            let _ = process_populate_warn_result(
                vm,
                addr,
                reason,
                addr.wrapping_sub(start),
                len,
                error,
                warn_fn,
            );
            let _ = process_preempt_result(preempt_enable_fn);
            return error;
        }
        addr = addr.wrapping_add(page_size);
    }

    let _ = process_preempt_result(preempt_enable_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_populate_memory_public_result(
    vm: *mut ProcessVm,
    current_vm: *mut ProcessVm,
    start: CULong,
    len: SizeT,
    page_size: CULong,
    reason: CULong,
    current_cpu: CInt,
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    write_lock_fn: Option<ProcessNoirqLockFn>,
    write_unlock_fn: Option<ProcessNoirqUnlockFn>,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
    normal_fault_fn: Option<ProcessFaultRangeFn>,
    xpmem_fault_fn: Option<ProcessFaultRangeFn>,
    preempt_disable_fn: Option<ProcessPreemptFn>,
    preempt_enable_fn: Option<ProcessPreemptFn>,
    pgio_dispatch_fn: Option<ProcessPgioDispatchFn>,
    warn_fn: Option<ProcessPopulateWarnFn>,
) -> CInt {
    if preempt_disable_fn.is_none()
        || preempt_enable_fn.is_none()
        || pgio_dispatch_fn.is_none()
        || page_size == 0
    {
        return -EINVAL;
    }

    let end = start.wrapping_add(len as CULong);
    let _ = process_preempt_result(preempt_disable_fn);

    let mut addr = start;
    while addr < end {
        let error = process_page_fault_vm_public_result(
            vm,
            current_vm,
            addr,
            reason,
            current_cpu,
            thread,
            pgio_fp_offset,
            pgio_arg_offset,
            read_lock_fn,
            read_unlock_fn,
            write_lock_fn,
            write_unlock_fn,
            zeroobj_match_fn,
            normal_fault_fn,
            xpmem_fault_fn,
            preempt_enable_fn,
            preempt_disable_fn,
            pgio_dispatch_fn,
        );
        if error != 0 {
            let _ = process_populate_warn_result(
                vm,
                addr,
                reason,
                addr.wrapping_sub(start),
                len,
                error,
                warn_fn,
            );
            let _ = process_preempt_result(preempt_enable_fn);
            return error;
        }
        addr = addr.wrapping_add(page_size);
    }

    let _ = process_preempt_result(preempt_enable_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_end_commit_result(
    range: *mut VmRange,
    newend: CULong,
) -> CInt {
    if range.is_null() {
        return 0;
    }

    unsafe {
        (*range).end = newend;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_range_flag_commit_result(
    range: *mut VmRange,
    newflag: CULong,
) -> CInt {
    if range.is_null() {
        return 0;
    }

    unsafe {
        (*range).flag = newflag;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_range_stack_start_commit_result(
    range: *mut VmRange,
    fault_addr: CULong,
    pgshift: CInt,
) -> CInt {
    if range.is_null() {
        return 0;
    }

    let new_start = if pgshift > 0 && (pgshift as usize) < CULong::BITS as usize {
        fault_addr & !((1u64 << pgshift) - 1)
    } else if pgshift == 0 {
        fault_addr & !(PAGE_SIZE - 1)
    } else {
        return 0;
    };

    unsafe {
        (*range).start = new_start;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_step_result(
    range_start: CULong,
    range_end: CULong,
    remove_start: CULong,
    remove_end: CULong,
    range_flags: CULong,
    private_data: CULong,
    split_startp: *mut CInt,
    split_endp: *mut CInt,
    ro_freedp: *mut CInt,
    xpmem_removep: *mut CInt,
) {
    if !split_startp.is_null() {
        unsafe {
            *split_startp = (range_start < remove_start) as CInt;
        }
    }
    if !split_endp.is_null() {
        unsafe {
            *split_endp = (remove_end < range_end) as CInt;
        }
    }
    if !ro_freedp.is_null() {
        unsafe {
            *ro_freedp = ((range_flags & VR_PROT_WRITE) == 0) as CInt;
        }
    }
    if !xpmem_removep.is_null() {
        unsafe {
            *xpmem_removep = (private_data != 0) as CInt;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_init_result(
    low: *const VmRange,
    high: *mut VmRange,
    addr: CULong,
) -> CInt {
    if low.is_null() || high.is_null() {
        return 0;
    }

    (*high).start = addr;
    (*high).straight_start = if (*low).straight_start != 0 {
        (*low)
            .straight_start
            .wrapping_add(addr.wrapping_sub((*low).start))
    } else {
        0
    };
    (*high).end = (*low).end;
    (*high).flag = (*low).flag;
    (*high).pgshift = (*low).pgshift;
    (*high).private_data = (*low).private_data;

    if !(*low).memobj.is_null() {
        (*high).memobj = (*low).memobj;
        (*high).objoff = (*low)
            .objoff
            .wrapping_add(addr.wrapping_sub((*low).start) as i64);
    } else {
        core::ptr::write_volatile(
            core::ptr::addr_of_mut!((*high).memobj),
            core::ptr::null_mut(),
        );
        core::ptr::write_volatile(core::ptr::addr_of_mut!((*high).objoff), 0);
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_commit_result(low: *mut VmRange, addr: CULong) {
    if !low.is_null() {
        (*low).end = addr;
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_memobj_ref_direct_result(memobj: *mut Memobj) -> CInt {
    if memobj.is_null() {
        return -EINVAL;
    }

    memobj_ref(memobj)
}

#[no_mangle]
pub unsafe extern "C" fn process_memobj_unref_direct_result(memobj: *mut Memobj) -> CInt {
    if memobj.is_null() {
        return -EINVAL;
    }

    memobj_unref(memobj)
}

#[no_mangle]
pub unsafe extern "C" fn process_range_memobj_ref_result(
    memobj: *mut c_void,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }
    let Some(memobj_ref) = memobj_ref_fn else {
        return -EINVAL;
    };

    memobj_ref(memobj);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_optional_memobj_ref_result(
    memobj: *mut c_void,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }
    let Some(memobj_ref) = memobj_ref_fn else {
        return 0;
    };

    memobj_ref(memobj);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_memobj_ref_or_direct_result(
    memobj: *mut c_void,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }
    if let Some(memobj_ref) = memobj_ref_fn {
        memobj_ref(memobj);
        return 0;
    }

    let _ = process_memobj_ref_direct_result(memobj.cast::<Memobj>());
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_memobj_unref_or_direct_result(
    memobj: *mut c_void,
    memobj_unref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }
    if let Some(memobj_unref) = memobj_unref_fn {
        memobj_unref(memobj);
        return 0;
    }

    let _ = process_memobj_unref_direct_result(memobj.cast::<Memobj>());
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_optional_memobj_ref_or_direct_result(
    memobj: *mut c_void,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }

    process_range_memobj_ref_or_direct_result(memobj, memobj_ref_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_range_optional_memobj_unref_or_direct_result(
    memobj: *mut c_void,
    memobj_unref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }

    process_range_memobj_unref_or_direct_result(memobj, memobj_unref_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_insert_result(
    vm: *mut c_void,
    range: *mut VmRange,
    insert_fn: Option<ProcessSplitRangeInsertFn>,
) -> CInt {
    let Some(insert) = insert_fn else {
        return -EINVAL;
    };

    insert(vm, range)
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_publish_result(
    vm: *mut c_void,
    low: *mut VmRange,
    high: *mut VmRange,
    addr: CULong,
    splitp: *mut *mut VmRange,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
    insert_fn: Option<ProcessSplitRangeInsertFn>,
) -> CInt {
    if low.is_null() || high.is_null() {
        return -EINVAL;
    }
    if insert_fn.is_none() {
        return -EINVAL;
    }
    if !(*low).memobj.is_null() {
        let rc = process_range_memobj_ref_or_direct_result((*low).memobj, memobj_ref_fn);
        if rc != 0 {
            return rc;
        }
    }

    process_split_range_commit_result(low, addr);

    let rc = process_split_range_insert_result(vm, high, insert_fn);
    if rc != 0 {
        return rc;
    }

    if !splitp.is_null() {
        *splitp = high;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_alloc_init_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    addr: CULong,
    splitp: *mut c_void,
    range_size: CULong,
    alloc_flags: CULong,
    errorp: *mut CInt,
    alloc_fn: Option<ProcessSplitRangeAllocFn>,
    log_fn: Option<ProcessSplitRangeAllocLogFn>,
) -> *mut VmRange {
    if errorp.is_null() {
        return null_mut();
    }
    *errorp = 0;

    let Some(alloc) = alloc_fn else {
        *errorp = -EINVAL;
        return null_mut();
    };
    if range.is_null() {
        *errorp = -EINVAL;
        return null_mut();
    }

    let newrange = alloc(range_size, alloc_flags);
    if newrange.is_null() {
        *errorp = -ENOMEM;
        if let Some(log) = log_fn {
            log(vm, range, addr, splitp);
        }
        return null_mut();
    }

    if process_split_range_init_result(range, newrange, addr) == 0 {
        *errorp = -EINVAL;
        return newrange;
    }

    newrange
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_publish_body_result(
    vm: *mut c_void,
    low: *mut VmRange,
    high: *mut VmRange,
    addr: CULong,
    splitp: *mut *mut VmRange,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
    insert_fn: Option<ProcessSplitRangeInsertFn>,
    log_fn: Option<ProcessSplitRangePublishLogFn>,
) -> CInt {
    let rc =
        process_split_range_publish_result(vm, low, high, addr, splitp, memobj_ref_fn, insert_fn);
    if rc != 0 {
        if let Some(log) = log_fn {
            log(rc);
        }
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_pt_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    addr: CULong,
    split_fn: Option<ProcessSplitRangePtSplitFn>,
    log_fn: Option<ProcessSplitRangePtLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }

    (*range).pgshift = process_split_pgshift_result((*range).pgshift, addr);

    let Some(split) = split_fn else {
        return -EINVAL;
    };
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let rc = split((*address_space).page_table, vm, range, addr as *mut c_void);
    if rc != 0 {
        if let Some(log) = log_fn {
            log(rc);
        }
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn process_split_shm_log_result(
    event: CInt,
    error: CInt,
    log_fn: Option<ProcessSplitShmLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_split_shm_update_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    addr: CULong,
    page_pgshift_offset: CULong,
    lookup_page_fn: Option<ProcessSplitShmLookupPageFn>,
    phys_to_page_fn: Option<ProcessSplitShmPhysToPageFn>,
    update_page_fn: Option<ProcessSplitShmUpdatePageFn>,
    log_fn: Option<ProcessSplitShmLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }

    let memobj = (*range).memobj;
    if memobj.is_null() {
        return 0;
    }
    if ((*memobj.cast::<Memobj>()).flags & MF_SHM) == 0 {
        return 0;
    }

    let (Some(lookup_page), Some(phys_to_page), Some(update_page)) =
        (lookup_page_fn, phys_to_page_fn, update_page_fn)
    else {
        return -EINVAL;
    };
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let mut phys = 0;
    let off = (*range)
        .objoff
        .wrapping_add(addr.wrapping_sub((*range).start) as OffT);
    let error = lookup_page(memobj, off, 0, &raw mut phys, null_mut());
    if error != 0 && error != -ENOENT {
        let _ = process_split_shm_log_result(PROCESS_SPLIT_SHM_LOG_LOOKUP_FAILED, error, log_fn);
        return error;
    }

    let page = phys_to_page(phys);
    if page.is_null() {
        return 0;
    }

    let pgshift = *(page
        .cast::<u8>()
        .wrapping_add(page_pgshift_offset as usize)
        .cast::<CInt>());
    let page_mask = !((1 as CULong).wrapping_shl(pgshift as u32).wrapping_sub(1));
    let error = update_page(
        memobj,
        (*address_space).page_table,
        page,
        (addr & page_mask) as *mut c_void,
    );
    if error != 0 {
        let _ = process_split_shm_log_result(PROCESS_SPLIT_SHM_LOG_UPDATE_FAILED, error, log_fn);
        return error;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn process_join_range_prepare_result(
    surviving: *mut VmRange,
    merging: *const VmRange,
) -> CInt {
    if surviving.is_null() || merging.is_null() {
        return -EINVAL;
    }

    if (*surviving).end != (*merging).start
        || (*surviving).flag != (*merging).flag
        || (*surviving).memobj != (*merging).memobj
    {
        return -EINVAL;
    }

    if !(*surviving).memobj.is_null() {
        let len = (*surviving).end.wrapping_sub((*surviving).start);
        let endoff = (*surviving).objoff.wrapping_add(len as i64);
        if endoff != (*merging).objoff {
            return -EINVAL;
        }
    }

    (*surviving).end = (*merging).end;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_join_range_free_result(
    range: *mut VmRange,
    free_fn: Option<ProcessJoinRangeFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_join_range_tofu_result(
    vm: *mut c_void,
    surviving: *mut VmRange,
    merging: *mut VmRange,
    tofu_fn: Option<ProcessJoinRangeTofuFn>,
) -> CInt {
    let Some(tofu) = tofu_fn else {
        return 0;
    };

    tofu(vm, surviving, merging)
}

#[no_mangle]
pub unsafe extern "C" fn process_join_range_body_result(
    vm: *mut c_void,
    root: *mut RbRoot,
    cache: *mut *mut c_void,
    cache_count: CInt,
    surviving: *mut VmRange,
    merging: *mut VmRange,
    memobj_unref_fn: Option<ProcessRangeMemobjRefFn>,
    free_fn: Option<ProcessJoinRangeFreeFn>,
    tofu_fn: Option<ProcessJoinRangeTofuFn>,
) -> CInt {
    if root.is_null() || cache.is_null() {
        return -EINVAL;
    }
    if free_fn.is_none() {
        return -EINVAL;
    }

    let rc = process_join_range_prepare_result(surviving, merging);
    if rc != 0 {
        return rc;
    }

    if !(*merging).memobj.is_null() {
        let rc = process_range_memobj_unref_or_direct_result((*merging).memobj, memobj_unref_fn);
        if rc != 0 {
            return rc;
        }
    }

    rb_erase(vm_range_rb_node(merging), root);
    process_range_cache_replace_result(cache, cache_count, merging.cast(), surviving.cast());

    let tofu_rc = process_join_range_tofu_result(vm, surviving, merging, tofu_fn);
    if tofu_rc != 0 {
        return tofu_rc;
    }

    process_join_range_free_result(merging, free_fn)
}

fn align_down(value: CULong, size: SizeT) -> CULong {
    value & !((size as CULong).wrapping_sub(1))
}

fn align_up(value: CULong, size: SizeT) -> CULong {
    value.wrapping_add(size as CULong).wrapping_sub(1) & !((size as CULong).wrapping_sub(1))
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_page_size_result(
    current: SizeT,
    nextp: *mut SizeT,
    page_size_fn: Option<ProcessFreeRangePageSizeFn>,
) -> CInt {
    let Some(page_size) = page_size_fn else {
        return -EINVAL;
    };

    page_size(current, nextp)
}

unsafe fn plan_lower_free_bound(
    mut start: CULong,
    has_prev: CInt,
    prev_end: CULong,
    page_size_fn: ProcessFreeRangePageSizeFn,
    first_error: &mut CInt,
) -> CULong {
    let mut pgsize = SizeT::MAX;
    loop {
        let mut next = 0usize;
        let rc = process_free_range_page_size_result(pgsize, &mut next, Some(page_size_fn));
        if rc != 0 {
            if *first_error == 0 {
                *first_error = rc;
            }
            break;
        }
        pgsize = next;
        let candidate = align_down(start, pgsize);
        if has_prev == 0 || prev_end <= candidate {
            start = candidate;
            break;
        }
    }
    start
}

unsafe fn plan_upper_free_bound(
    mut end: CULong,
    has_next: CInt,
    next_start: CULong,
    page_size_fn: ProcessFreeRangePageSizeFn,
    first_error: &mut CInt,
) -> CULong {
    let mut pgsize = SizeT::MAX;
    loop {
        let mut next = 0usize;
        let rc = process_free_range_page_size_result(pgsize, &mut next, Some(page_size_fn));
        if rc != 0 {
            if *first_error == 0 {
                *first_error = rc;
            }
            break;
        }
        pgsize = next;
        let candidate = align_up(end, pgsize);
        if has_next == 0 || candidate <= next_start {
            end = candidate;
            break;
        }
    }
    end
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_pt_plan_result(
    range: *const VmRange,
    straight_va: CULong,
    has_prev: CInt,
    prev_end: CULong,
    has_next: CInt,
    next_start: CULong,
    has_memobj: CInt,
    memobj_flags: u32,
    startp: *mut CULong,
    endp: *mut CULong,
    actionp: *mut CInt,
    page_size_fn: Option<ProcessFreeRangePageSizeFn>,
) -> CInt {
    if range.is_null() || startp.is_null() || endp.is_null() || actionp.is_null() {
        return -EINVAL;
    }

    let mut start = (*range).start;
    let mut end = (*range).end;
    let mut action = PROCESS_FREE_RANGE_PT_SKIP;
    let mut first_error = 0;

    if (*range).straight_start == 0 && (*range).start != straight_va {
        if ((*range).flag & (VR_REMOTE | VR_IO_NOCACHE | VR_RESERVED)) != 0 {
            action = PROCESS_FREE_RANGE_PT_CLEAR;
        } else {
            let Some(page_size_fn) = page_size_fn else {
                return -EINVAL;
            };
            start =
                plan_lower_free_bound(start, has_prev, prev_end, page_size_fn, &mut first_error);
            end = plan_upper_free_bound(end, has_next, next_start, page_size_fn, &mut first_error);
            action = if has_memobj != 0 && (memobj_flags & MF_HUGETLBFS) != 0 {
                PROCESS_FREE_RANGE_PT_CLEAR
            } else {
                PROCESS_FREE_RANGE_PT_FREE
            };
        }
    }

    *startp = start;
    *endp = end;
    *actionp = action;
    first_error
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_finalize_result(
    vm: *mut c_void,
    root: *mut RbRoot,
    cache: *mut *mut c_void,
    cache_count: CInt,
    range: *mut VmRange,
    straight_va: CULong,
    straight_lenp: *mut SizeT,
    straight_pa: CULong,
    phys_to_virt_fn: Option<ProcessFreeRangePhysToVirtFn>,
    free_pages_fn: Option<ProcessFreeRangePagesFn>,
    clear_main_fn: Option<ProcessFreeRangeClearMainFn>,
    free_fn: Option<ProcessFreeRangeFreeFn>,
) -> CInt {
    if root.is_null() || cache.is_null() || range.is_null() || straight_lenp.is_null() {
        return -EINVAL;
    }
    if free_fn.is_none() {
        return -EINVAL;
    }

    let needs_straight_free = (*range).straight_start != 0;
    let straight_len = *straight_lenp;
    let is_main_straight = !needs_straight_free
        && (*range).start == straight_va
        && (*range).end == straight_va.wrapping_add(straight_len as CULong);

    if needs_straight_free && (phys_to_virt_fn.is_none() || free_pages_fn.is_none()) {
        return -EINVAL;
    }
    if is_main_straight && clear_main_fn.is_none() {
        return -EINVAL;
    }

    rb_erase(vm_range_rb_node(range), root);
    process_range_cache_replace_result(cache, cache_count, range.cast(), null_mut());

    if needs_straight_free {
        let phys = straight_pa.wrapping_add((*range).straight_start.wrapping_sub(straight_va));
        let addr = process_free_range_phys_to_virt_result(phys, phys_to_virt_fn);
        let pages = (*range).end.wrapping_sub((*range).start) >> PAGE_SHIFT;
        let rc = process_free_range_free_pages_result(addr, pages, free_pages_fn);
        if rc != 0 {
            return rc;
        }
    } else if is_main_straight {
        let _ =
            process_free_range_clear_main_result(vm, (*range).start, (*range).end, clear_main_fn);
        *straight_lenp = 0;
    }

    process_free_range_free_result(range, free_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_phys_to_virt_result(
    phys: CULong,
    phys_to_virt_fn: Option<ProcessFreeRangePhysToVirtFn>,
) -> *mut c_void {
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return null_mut();
    };

    phys_to_virt(phys)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_free_pages_result(
    addr: *mut c_void,
    pages: CULong,
    free_pages_fn: Option<ProcessFreeRangePagesFn>,
) -> CInt {
    let Some(free_pages) = free_pages_fn else {
        return -EINVAL;
    };

    free_pages(addr, pages);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_clear_main_result(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    clear_main_fn: Option<ProcessFreeRangeClearMainFn>,
) -> CInt {
    let Some(clear_main) = clear_main_fn else {
        return -EINVAL;
    };

    clear_main(vm, start, end)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_free_result(
    range: *mut VmRange,
    free_fn: Option<ProcessFreeRangeFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_pt_free_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    memobj: *mut c_void,
    pt_free_fn: Option<ProcessFreeRangePtFreeFn>,
) -> CInt {
    let Some(pt_free) = pt_free_fn else {
        return -EINVAL;
    };

    pt_free(page_table, vm, start, end, memobj)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_pt_clear_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    pt_clear_fn: Option<ProcessFreeRangePtClearFn>,
) -> CInt {
    let Some(pt_clear) = pt_clear_fn else {
        return -EINVAL;
    };

    pt_clear(page_table, vm, start, end)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_tofu_remove_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    tofu_remove_fn: Option<ProcessFreeRangeTofuRemoveFn>,
) -> CInt {
    let Some(tofu_remove) = tofu_remove_fn else {
        return 0;
    };

    tofu_remove(vm, range)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_log_result(
    event: CInt,
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    error: CInt,
    log_fn: Option<ProcessFreeRangeLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, vm, range, start, end, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_free_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    straight_va: CULong,
    straight_lenp: *mut SizeT,
    straight_pa: CULong,
    tofu_enabled: CInt,
    page_size_fn: Option<ProcessFreeRangePageSizeFn>,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
    memobj_unref_fn: Option<ProcessRangeMemobjRefFn>,
    pt_free_fn: Option<ProcessFreeRangePtFreeFn>,
    pt_clear_fn: Option<ProcessFreeRangePtClearFn>,
    tofu_remove_fn: Option<ProcessFreeRangeTofuRemoveFn>,
    phys_to_virt_fn: Option<ProcessFreeRangePhysToVirtFn>,
    free_pages_fn: Option<ProcessFreeRangePagesFn>,
    clear_main_fn: Option<ProcessFreeRangeClearMainFn>,
    free_fn: Option<ProcessFreeRangeFreeFn>,
    log_fn: Option<ProcessFreeRangeLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() || straight_lenp.is_null() {
        return -EINVAL;
    }
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let start0 = (*range).start;
    let end0 = (*range).end;
    let mut start = start0;
    let mut end = end0;
    let prev = process_previous_memory_range_body_result(range);
    let next = process_next_memory_range_body_result(range);
    let has_memobj = !(*range).memobj.is_null();
    let memobj_flags = if has_memobj {
        (*(*range).memobj.cast::<Memobj>()).flags
    } else {
        0
    };
    let mut pt_action = PROCESS_FREE_RANGE_PT_SKIP;
    let mut error = process_free_range_pt_plan_result(
        range,
        straight_va,
        (!prev.is_null()) as CInt,
        if prev.is_null() { 0 } else { (*prev).end },
        (!next.is_null()) as CInt,
        if next.is_null() { 0 } else { (*next).start },
        has_memobj as CInt,
        memobj_flags,
        &raw mut start,
        &raw mut end,
        &raw mut pt_action,
        page_size_fn,
    );
    if error != 0 {
        let _ = process_free_range_log_result(
            PROCESS_FREE_BODY_LOG_PLAN_FAILED,
            vm,
            range,
            start,
            end,
            error,
            log_fn,
        );
    }

    if pt_action != PROCESS_FREE_RANGE_PT_SKIP {
        if lock_fn.is_none() || unlock_fn.is_none() {
            return -EINVAL;
        }
        let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;

        if pt_action == PROCESS_FREE_RANGE_PT_FREE {
            if pt_free_fn.is_none() {
                return -EINVAL;
            }
            let _ = process_noirq_lock_result(lock_addr, lock_fn);
            let _ =
                process_range_optional_memobj_ref_or_direct_result((*range).memobj, memobj_ref_fn);
            error = process_free_range_pt_free_result(
                (*address_space).page_table,
                vm,
                start,
                end,
                (*range).memobj,
                pt_free_fn,
            );
            let _ = process_range_optional_memobj_unref_or_direct_result(
                (*range).memobj,
                memobj_unref_fn,
            );
            let _ = process_noirq_unlock_result(lock_addr, unlock_fn);
            if error != 0 && error != -ENOENT {
                let _ = process_free_range_log_result(
                    PROCESS_FREE_BODY_LOG_PT_FREE_FAILED,
                    vm,
                    range,
                    start,
                    end,
                    error,
                    log_fn,
                );
            }
        } else if pt_action == PROCESS_FREE_RANGE_PT_CLEAR {
            if pt_clear_fn.is_none() {
                return -EINVAL;
            }
            let _ = process_noirq_lock_result(lock_addr, lock_fn);
            error = process_free_range_pt_clear_result(
                (*address_space).page_table,
                vm,
                start,
                end,
                pt_clear_fn,
            );
            let _ = process_noirq_unlock_result(lock_addr, unlock_fn);
            if error != 0 && error != -ENOENT {
                let _ = process_free_range_log_result(
                    PROCESS_FREE_BODY_LOG_PT_CLEAR_FAILED,
                    vm,
                    range,
                    start,
                    end,
                    error,
                    log_fn,
                );
            }
        }

        let _ =
            process_range_optional_memobj_unref_or_direct_result((*range).memobj, memobj_unref_fn);
    }

    if tofu_enabled != 0 {
        let entries = process_free_range_tofu_remove_result(vm, range, tofu_remove_fn);
        if entries > 0 {
            let _ = process_free_range_log_result(
                PROCESS_FREE_BODY_LOG_TOFU_REMOVED,
                vm,
                range,
                start0,
                end0,
                entries,
                log_fn,
            );
        }
    }

    let root = (&raw mut (*vm).vm_range_tree).cast::<RbRoot>();
    let cache = (&raw mut (*vm).range_cache).cast::<*mut c_void>();
    error = process_free_range_finalize_result(
        vm.cast(),
        root,
        cache,
        crate::abi::VM_RANGE_CACHE_SIZE as CInt,
        range,
        straight_va,
        straight_lenp,
        straight_pa,
        phys_to_virt_fn,
        free_pages_fn,
        clear_main_fn,
        free_fn,
    );
    if error != 0 {
        let _ = process_free_range_log_result(
            PROCESS_FREE_BODY_LOG_FINALIZE_FAILED,
            vm,
            range,
            start0,
            end0,
            error,
            log_fn,
        );
        return error;
    }

    let _ = process_free_range_log_result(
        PROCESS_FREE_BODY_LOG_DONE,
        vm,
        range,
        start0,
        end0,
        0,
        log_fn,
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn process_sync_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    arg: *mut c_void,
    visit_step_fn: *mut c_void,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    log_fn: Option<ProcessSyncRangeLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() || (*vm).address_space.is_null() || (*range).memobj.is_null()
    {
        return -EINVAL;
    }
    if lock_fn.is_none() || unlock_fn.is_none() {
        return -EINVAL;
    }
    let Some(visit) = visit_fn else {
        return -EINVAL;
    };

    let memobj = (*range).memobj.cast::<Memobj>();
    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;
    let zero_fill = ((*memobj).flags & MF_ZEROFILL) != 0;

    let _ = process_noirq_lock_result(lock_addr, lock_fn);
    if !zero_fill {
        let _ = process_memobj_ref_direct_result(memobj);
    }

    let error = visit(
        (*(*vm).address_space).page_table,
        start,
        end,
        (*range).pgshift,
        VPTEF_SKIP_NULL,
        visit_step_fn,
        arg,
    );

    if !zero_fill {
        let _ = process_memobj_unref_direct_result(memobj);
    }
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);

    if error != 0 {
        if let Some(log) = log_fn {
            log(vm, range, start, end, error);
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn process_remap_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    off: OffT,
    arg: *mut c_void,
    visit_step_fn: *mut c_void,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    log_fn: Option<ProcessRemapRangeLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() || (*vm).address_space.is_null() || (*range).memobj.is_null()
    {
        return -EINVAL;
    }
    if lock_fn.is_none() || unlock_fn.is_none() {
        return -EINVAL;
    }
    let Some(visit) = visit_fn else {
        return -EINVAL;
    };

    let memobj = (*range).memobj.cast::<Memobj>();
    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;

    let _ = process_noirq_lock_result(lock_addr, lock_fn);
    let _ = process_memobj_ref_direct_result(memobj);

    let pgshift = AtomicI32::from_ptr(&raw mut (*range).pgshift);
    let old_pgshift =
        match pgshift.compare_exchange(0, PAGE_SHIFT as CInt, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(old) | Err(old) => old,
        };

    let error = if old_pgshift != 0 && old_pgshift != PAGE_SHIFT as CInt {
        let error = -E2BIG;
        if let Some(log) = log_fn {
            log(
                PROCESS_REMAP_RANGE_LOG_PGSHIFT,
                vm,
                range,
                start,
                end,
                off,
                old_pgshift,
                error,
            );
        }
        error
    } else {
        let error = visit(
            (*(*vm).address_space).page_table,
            start,
            end,
            (*range).pgshift,
            0,
            visit_step_fn,
            arg,
        );
        if error != 0 {
            if let Some(log) = log_fn {
                log(
                    PROCESS_REMAP_RANGE_LOG_VISIT_FAILED,
                    vm,
                    range,
                    start,
                    end,
                    off,
                    old_pgshift,
                    error,
                );
            }
        }
        error
    };

    let _ = process_memobj_unref_direct_result(memobj);
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);
    error
}

#[no_mangle]
pub unsafe extern "C" fn process_invalidate_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    arg: *mut c_void,
    visit_step_fn: *mut c_void,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    lookup_pte_fn: Option<ProcessLookupPteFn>,
    pte_contiguous_fn: Option<ProcessPteTestFn>,
    pte_head_fn: Option<ProcessPtePgsizeTestFn>,
    pte_tail_fn: Option<ProcessPtePgsizeTestFn>,
    split_fn: Option<ProcessSplitContiguousPagesFn>,
    pt_free_fn: Option<ProcessFreeRangePtFreeFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    log_fn: Option<ProcessSyncRangeLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() || (*vm).address_space.is_null() || (*range).memobj.is_null()
    {
        return -EINVAL;
    }
    if lock_fn.is_none() || unlock_fn.is_none() {
        return -EINVAL;
    }
    let Some(lookup_pte) = lookup_pte_fn else {
        return -EINVAL;
    };
    let Some(pte_contiguous) = pte_contiguous_fn else {
        return -EINVAL;
    };
    let Some(pte_head) = pte_head_fn else {
        return -EINVAL;
    };
    let Some(pte_tail) = pte_tail_fn else {
        return -EINVAL;
    };
    let Some(split) = split_fn else {
        return -EINVAL;
    };
    let Some(pt_free) = pt_free_fn else {
        return -EINVAL;
    };
    let Some(visit) = visit_fn else {
        return -EINVAL;
    };

    let memobj = (*range).memobj.cast::<Memobj>();
    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;
    let page_table = (*(*vm).address_space).page_table;
    let mut error = 0;
    let mut should_log = false;
    let mut pgsize: SizeT = 0;

    let _ = process_noirq_lock_result(lock_addr, lock_fn);
    let _ = process_memobj_ref_direct_result(memobj);

    let ptep = lookup_pte(page_table, start, 0, &raw mut pgsize);
    if !ptep.is_null() && pte_contiguous(ptep) != 0 && pte_head(ptep, pgsize) == 0 {
        error = split(ptep, pgsize, (*memobj).flags);
    }

    if error == 0 {
        pgsize = 0;
        let ptep = lookup_pte(page_table, end - 1, 0, &raw mut pgsize);
        if !ptep.is_null() && pte_contiguous(ptep) != 0 && pte_tail(ptep, pgsize) == 0 {
            error = split(ptep, pgsize, (*memobj).flags);
        }
    }

    if error == 0 {
        should_log = true;
        if ((*memobj).flags & MF_SHM) != 0 {
            error = pt_free(page_table, vm, start, end, memobj.cast::<c_void>());
        } else {
            error = visit(
                page_table,
                start,
                end,
                (*range).pgshift,
                VPTEF_SKIP_NULL,
                visit_step_fn,
                arg,
            );
        }
    }

    let _ = process_memobj_unref_direct_result(memobj);
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);

    if should_log && error != 0 {
        if let Some(log) = log_fn {
            log(vm, range, start, end, error);
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn process_invalidate_one_page_body_result(
    arg: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
    pte_null_fn: Option<ProcessPteTestFn>,
    pte_fileoff_fn: Option<ProcessPtePgsizeTestFn>,
    pte_get_phys_fn: Option<ProcessPteGetPhysFn>,
    phys_to_page_fn: Option<ProcessPhysToPageFn>,
    page_offset_fn: Option<ProcessPageOffsetFn>,
    pte_make_fileoff_fn: Option<ProcessPteMakeFileoffFn>,
    pte_xchg_fn: Option<ProcessPteXchgFn>,
    flush_tlb_single_fn: Option<ProcessFlushTlbSingleFn>,
    pte_contiguous_fn: Option<ProcessPteTestFn>,
    pte_head_fn: Option<ProcessPtePgsizeTestFn>,
    pgsize_to_tbllv_fn: Option<ProcessPgsizeToTbllvFn>,
    tbllv_to_contpgsize_fn: Option<ProcessTbllvToContpgsizeFn>,
    page_unmap_fn: Option<ProcessPageUnmapFn>,
    panic_fn: Option<ProcessPanicFn>,
    memobj_invalidate_page_fn: Option<ProcessMemobjInvalidatePageFn>,
    log_fn: Option<ProcessInvalidateOnePageLogFn>,
) -> CInt {
    if arg.is_null() || ptep.is_null() || pgshift < 0 || pgshift as usize >= SizeT::BITS as usize {
        return -EINVAL;
    }
    let Some(pte_null) = pte_null_fn else {
        return -EINVAL;
    };
    let Some(pte_fileoff) = pte_fileoff_fn else {
        return -EINVAL;
    };
    let Some(pte_get_phys) = pte_get_phys_fn else {
        return -EINVAL;
    };
    let Some(phys_to_page) = phys_to_page_fn else {
        return -EINVAL;
    };
    let Some(page_offset) = page_offset_fn else {
        return -EINVAL;
    };
    let Some(pte_make_fileoff) = pte_make_fileoff_fn else {
        return -EINVAL;
    };
    let Some(pte_xchg) = pte_xchg_fn else {
        return -EINVAL;
    };
    let Some(flush_tlb_single) = flush_tlb_single_fn else {
        return -EINVAL;
    };
    let Some(pte_contiguous) = pte_contiguous_fn else {
        return -EINVAL;
    };
    let Some(pte_head) = pte_head_fn else {
        return -EINVAL;
    };
    let Some(pgsize_to_tbllv) = pgsize_to_tbllv_fn else {
        return -EINVAL;
    };
    let Some(tbllv_to_contpgsize) = tbllv_to_contpgsize_fn else {
        return -EINVAL;
    };
    let Some(page_unmap) = page_unmap_fn else {
        return -EINVAL;
    };
    let Some(panic_call) = panic_fn else {
        return -EINVAL;
    };
    let Some(memobj_invalidate_page) = memobj_invalidate_page_fn else {
        return -EINVAL;
    };

    let range = *(arg.cast::<*mut VmRange>());
    if range.is_null() || (*range).memobj.is_null() {
        return -EINVAL;
    }

    let pgsize = 1usize << (pgshift as usize);
    if pte_null(ptep) != 0 || pte_fileoff(ptep, pgsize) != 0 {
        return 0;
    }

    let phys = pte_get_phys(ptep);
    let page = phys_to_page(phys);
    let linear_off = (*range)
        .objoff
        .wrapping_add((pgaddr as CULong).wrapping_sub((*range).start) as OffT);
    let mut apte: CULong = 0;

    if !page.is_null() {
        let page_off = page_offset(page);

        if page_off != linear_off {
            pte_make_fileoff(page_off, pgsize, (&raw mut apte).cast::<c_void>());
        }
    }

    pte_xchg(ptep, (&raw mut apte).cast::<c_void>());
    flush_tlb_single(pgaddr as CULong);

    let memobj_pgsize = if pte_contiguous((&raw mut apte).cast::<c_void>()) != 0 {
        if pte_head(ptep, pgsize) != 0 {
            tbllv_to_contpgsize(pgsize_to_tbllv(pgsize))
        } else {
            return 0;
        }
    } else {
        pgsize
    };

    if !page.is_null() && page_unmap(page) != 0 {
        panic_call(b"invalidate_one_page\0".as_ptr().cast::<i8>());
    }

    let error = memobj_invalidate_page((*range).memobj.cast::<Memobj>(), phys, memobj_pgsize);
    if error != 0 {
        if let Some(log) = log_fn {
            log(
                arg,
                page_table,
                ptep,
                *(ptep.cast::<CULong>()),
                pgaddr,
                pgshift,
                error,
            );
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_straight_convert_result(
    straight_va: CULong,
    straight_len: SizeT,
    range: *const VmRange,
    start: CULong,
    end: CULong,
    new_startp: *mut CULong,
    new_endp: *mut CULong,
    lenp: *mut CULong,
) -> CInt {
    if new_startp.is_null() || new_endp.is_null() || lenp.is_null() {
        return -EINVAL;
    }

    let len = end.wrapping_sub(start);
    *new_startp = start;
    *new_endp = end;
    *lenp = len;

    let straight_end = straight_va.wrapping_add(straight_len as CULong);
    let needs_conversion = straight_va != 0
        && start >= straight_va
        && end <= straight_end
        && !(start == straight_va && end == straight_end);
    if !needs_conversion {
        return PROCESS_REMOVE_STRAIGHT_NO_CONVERT;
    }
    if range.is_null() {
        return PROCESS_REMOVE_STRAIGHT_NEED_RANGE;
    }

    let range_len = (*range).end.wrapping_sub((*range).start);
    let range_straight_end = (*range).straight_start.wrapping_add(range_len);
    if (*range).straight_start != 0
        && start >= (*range).straight_start
        && start < range_straight_end
    {
        let new_start = (*range)
            .start
            .wrapping_add(start.wrapping_sub((*range).straight_start));
        *new_startp = new_start;
        *new_endp = new_start.wrapping_add(len);
        return PROCESS_REMOVE_STRAIGHT_CONVERTED;
    }

    PROCESS_REMOVE_STRAIGHT_NEED_RANGE
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_split_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    addr: CULong,
    splitp: *mut *mut VmRange,
    split_fn: Option<ProcessRemoveRangeSplitFn>,
) -> CInt {
    let Some(split) = split_fn else {
        return -EINVAL;
    };

    split(vm, range, addr, splitp)
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_xpmem_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    xpmem_remove_fn: Option<ProcessRemoveRangeXpmemFn>,
) -> CInt {
    let Some(xpmem_remove) = xpmem_remove_fn else {
        return -EINVAL;
    };

    xpmem_remove(vm, range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_free_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(vm.cast(), range.cast())
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_log_result(
    event: CInt,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    range: *mut VmRange,
    error: CInt,
    log_fn: Option<ProcessRemoveRangeLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, vm, start, end, range, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_memory_range_body_result(
    vm: *mut ProcessVm,
    mut start: CULong,
    mut end: CULong,
    ro_freedp: *mut CInt,
    straight_va: CULong,
    straight_len: SizeT,
    split_fn: Option<ProcessRemoveRangeSplitFn>,
    xpmem_remove_fn: Option<ProcessRemoveRangeXpmemFn>,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessRemoveRangeLogFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let Some(split_fn) = split_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };

    let mut converted_start = start;
    let mut converted_end = end;
    let mut len = end.wrapping_sub(start);
    let mut action = process_remove_straight_convert_result(
        straight_va,
        straight_len,
        core::ptr::null(),
        start,
        end,
        &mut converted_start,
        &mut converted_end,
        &mut len,
    );

    if action == PROCESS_REMOVE_STRAIGHT_NEED_RANGE {
        let mut range_iter = process_lookup_memory_range_body_result(vm, 0, CULong::MAX);
        let mut converted_range: *mut VmRange = null_mut();

        while !range_iter.is_null() {
            action = process_remove_straight_convert_result(
                straight_va,
                straight_len,
                range_iter,
                start,
                end,
                &mut converted_start,
                &mut converted_end,
                &mut len,
            );
            if action == PROCESS_REMOVE_STRAIGHT_CONVERTED {
                converted_range = range_iter;
                break;
            }
            range_iter = process_next_memory_range_body_result(range_iter);
        }

        if converted_range.is_null() {
            let _ = process_remove_range_log_result(
                PROCESS_REMOVE_RANGE_LOG_NO_STRAIGHT,
                vm,
                start,
                end,
                null_mut(),
                0,
                log_fn,
            );
            return 0;
        }

        let _ = process_remove_range_log_result(
            PROCESS_REMOVE_RANGE_LOG_CONVERTED,
            vm,
            converted_start,
            converted_end,
            converted_range,
            0,
            log_fn,
        );
        start = converted_start;
        end = converted_end;
    }

    let mut ro_freed = 0;
    let mut next = process_lookup_memory_range_body_result(vm, start, end);
    while !next.is_null() && (*next).start < end {
        let mut range = next;
        next = process_next_memory_range_body_result(range);

        let mut split_start = 0;
        let mut split_end = 0;
        let mut mark_ro_freed = 0;
        let mut remove_xpmem = 0;
        process_remove_range_step_result(
            (*range).start,
            (*range).end,
            start,
            end,
            (*range).flag,
            (*range).private_data as CULong,
            &mut split_start,
            &mut split_end,
            &mut mark_ro_freed,
            &mut remove_xpmem,
        );

        if split_start != 0 {
            let rc =
                process_remove_range_split_result(vm, range, start, &mut range, Some(split_fn));
            if rc != 0 {
                let _ = process_remove_range_log_result(
                    PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED,
                    vm,
                    start,
                    end,
                    range,
                    rc,
                    log_fn,
                );
                return rc;
            }
        }

        if split_end != 0 {
            let rc = process_remove_range_split_result(vm, range, end, null_mut(), Some(split_fn));
            if rc != 0 {
                let _ = process_remove_range_log_result(
                    PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED,
                    vm,
                    start,
                    end,
                    range,
                    rc,
                    log_fn,
                );
                return rc;
            }
        }

        if mark_ro_freed != 0 {
            ro_freed = 1;
        }

        if remove_xpmem != 0 {
            let rc = process_remove_range_xpmem_result(vm, range, xpmem_remove_fn);
            if rc != 0 {
                return rc;
            }
        }

        let rc = process_remove_range_free_result(vm, range, Some(free_fn));
        if rc != 0 {
            let _ = process_remove_range_log_result(
                PROCESS_REMOVE_RANGE_LOG_FREE_FAILED,
                vm,
                start,
                end,
                range,
                rc,
                log_fn,
            );
            return rc;
        }
    }

    if !ro_freedp.is_null() {
        *ro_freedp = ro_freed;
    }
    let _ = process_remove_range_log_result(
        PROCESS_REMOVE_RANGE_LOG_DONE,
        vm,
        start,
        end,
        null_mut(),
        ro_freed,
        log_fn,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_region_body_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    clear_fn: Option<ProcessRemoveRegionClearFn>,
    log_fn: Option<ProcessRemoveRegionLogFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }

    let rc = process_remove_region_alignment_result(start, end);
    if rc != 0 {
        return rc;
    }

    if lock_fn.is_none() || unlock_fn.is_none() || clear_fn.is_none() {
        return -EINVAL;
    }
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<c_void>() as CULong;
    let rc = process_noirq_lock_result(lock_addr, lock_fn);
    if rc != 0 {
        return rc;
    }
    let _ =
        process_remove_region_clear_result((*address_space).page_table, vm, start, end, clear_fn);
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);

    process_remove_region_log_result(vm, start, end, log_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_region_clear_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    clear_fn: Option<ProcessRemoveRegionClearFn>,
) -> CInt {
    let Some(clear) = clear_fn else {
        return -EINVAL;
    };

    clear(page_table, vm, start, end)
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_region_log_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    log_fn: Option<ProcessRemoveRegionLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(vm, start, end);
    0
}

#[inline(always)]
unsafe fn process_init_stack_zero(mut ptr: *mut u8, mut len: CULong) {
    while len != 0 {
        write_volatile(ptr, 0);
        ptr = ptr.add(1);
        len -= 1;
    }
}

#[inline(always)]
unsafe fn process_init_stack_push(base: *mut CULong, s_ind: &mut isize, value: CULong) {
    write_volatile(base.offset(*s_ind), value);
    *s_ind -= 1;
}

#[inline(always)]
fn process_init_stack_sp(end: CULong, s_ind: isize) -> CULong {
    end.wrapping_add((s_ind as i64 as CULong).wrapping_mul(size_of::<CULong>() as CULong))
}

#[inline(always)]
unsafe fn process_init_stack_log_args(args: &mut MaybeUninit<[CULong; 12]>) -> *mut CULong {
    let ptr = args.as_mut_ptr().cast::<CULong>();
    let mut index = 0usize;
    while index < 12 {
        write_volatile(ptr.add(index), 0);
        index += 1;
    }
    ptr
}

macro_rules! process_init_stack_log {
    ($log_fn:expr, $event:expr $(, $index:literal => $value:expr)* $(,)?) => {{
        if $log_fn.is_some() {
            let mut args = MaybeUninit::<[CULong; 12]>::uninit();
            let args_ptr = process_init_stack_log_args(&mut args);
            $(
                write_volatile(args_ptr.add($index), $value as CULong);
            )*
            let _ = process_init_stack_log_result($event, args_ptr as *const CULong, $log_fn);
        }
    }};
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_alloc_aligned_result(
    npages: CInt,
    p2align: CInt,
    flags: CULong,
    virt_addr: CULong,
    alloc_aligned_fn: Option<ProcessInitStackAllocAlignedFn>,
) -> *mut c_void {
    let Some(alloc_aligned) = alloc_aligned_fn else {
        return null_mut();
    };

    alloc_aligned(npages, p2align, flags, virt_addr)
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_free_pages_result(
    addr: *mut c_void,
    npages: CInt,
    free_pages_fn: Option<ProcessInitStackFreePagesFn>,
) -> CInt {
    let Some(free_pages) = free_pages_fn else {
        return -EINVAL;
    };

    free_pages(addr, npages);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_add_range_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    pgshift: CInt,
    rangep: *mut *mut VmRange,
    add_range_fn: Option<ProcessInitStackAddRangeFn>,
) -> CInt {
    let Some(add_range) = add_range_fn else {
        return -EINVAL;
    };

    add_range(vm, start, end, phys, flag, pgshift, rangep)
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_virt_to_phys_result(
    addr: *mut c_void,
    virt_to_phys_fn: Option<ProcessInitStackVirtToPhysFn>,
) -> CULong {
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return 0;
    };

    virt_to_phys(addr)
}

#[no_mangle]
pub unsafe extern "C" fn process_attr_from_vrflag_result(
    flag: CULong,
    fault: CULong,
    ptep: *mut c_void,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
) -> CULong {
    let Some(attr) = attr_fn else {
        return 0;
    };

    attr(flag, fault, ptep)
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_pt_set_range_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CULong,
    pgshift: CInt,
    range: *mut VmRange,
    flags: CInt,
    pt_set_range_fn: Option<ProcessInitStackPtSetRangeFn>,
) -> CInt {
    let Some(pt_set_range) = pt_set_range_fn else {
        return -EINVAL;
    };

    pt_set_range(
        page_table, vm, start, end, phys, attr, pgshift, range, flags,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_hwcap_result(
    hwcap_fn: Option<ProcessInitStackHwcapFn>,
) -> CULong {
    let Some(hwcap) = hwcap_fn else {
        return 0;
    };

    hwcap()
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_modify_context_result(
    uctx: *mut c_void,
    reg: CInt,
    value: CULong,
    modify_context_fn: Option<ProcessInitStackModifyContextFn>,
) -> CInt {
    let Some(modify_context) = modify_context_fn else {
        return -EINVAL;
    };

    modify_context(uctx, reg, value);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_log_result(
    event: CInt,
    args: *const CULong,
    log_fn: Option<ProcessInitStackLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return -EINVAL;
    };
    if args.is_null() {
        return -EINVAL;
    }

    log(event, args);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_body_result(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    at_base: CULong,
    argc: CInt,
    argv: *mut *mut i8,
    envc: CInt,
    env: *mut *mut i8,
    page_size: CULong,
    page_shift: CInt,
    user_stack_page_mask: CULong,
    user_stack_page_shift: CInt,
    user_stack_prepage_size: CULong,
    stack_alloc_size_override: CULong,
    user_stack_page_p2align: CInt,
    alloc_nowait: CULong,
    alloc_user: CULong,
    mpol_no_stack: CULong,
    user_context_sp_reg: CInt,
    pf_populate: CULong,
    alloc_aligned_fn: Option<ProcessInitStackAllocAlignedFn>,
    free_pages_fn: Option<ProcessInitStackFreePagesFn>,
    add_range_fn: Option<ProcessInitStackAddRangeFn>,
    virt_to_phys_fn: Option<ProcessInitStackVirtToPhysFn>,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    pt_set_range_fn: Option<ProcessInitStackPtSetRangeFn>,
    hwcap_fn: Option<ProcessInitStackHwcapFn>,
    modify_context_fn: Option<ProcessInitStackModifyContextFn>,
    log_fn: Option<ProcessInitStackLogFn>,
) -> CInt {
    if thread.is_null()
        || pn.is_null()
        || page_size == 0
        || page_shift < 0
        || user_stack_page_shift < 0
    {
        return -EINVAL;
    }
    if alloc_aligned_fn.is_none()
        || free_pages_fn.is_none()
        || add_range_fn.is_none()
        || virt_to_phys_fn.is_none()
        || attr_fn.is_none()
        || pt_set_range_fn.is_none()
        || hwcap_fn.is_none()
        || modify_context_fn.is_none()
    {
        return -EINVAL;
    }

    let proc = (*thread).proc;
    let vm = (*thread).vm;
    if proc.is_null() || vm.is_null() || (*vm).address_space.is_null() {
        return -EINVAL;
    }

    let end = (*vm).region.user_end & user_stack_page_mask;
    let mut minsz = ((*pn).stack_premap as CULong).wrapping_add(user_stack_prepage_size - 1)
        & user_stack_page_mask;
    let maxsz = end.wrapping_sub((*vm).region.map_start) / 2;
    let mut size = (*proc).rlimit[MCK_RLIMIT_STACK].rlim_cur;
    if size > maxsz {
        size = maxsz;
    } else if size < minsz {
        size = minsz;
    }
    size = size.wrapping_add(user_stack_prepage_size - 1) & user_stack_page_mask;
    process_init_stack_log!(
        log_fn,
        PROCESS_INIT_STACK_LOG_SIZE,
        0 => (*pn).stack_premap as CULong,
        1 => (*proc).rlimit[MCK_RLIMIT_STACK].rlim_cur,
        2 => minsz,
        3 => size,
        4 => maxsz,
    );
    let start = end.wrapping_sub(minsz) & user_stack_page_mask;

    let ap_flag =
        if minsz >= (*proc).mpol_threshold as CULong && ((*proc).mpol_flags & mpol_no_stack) == 0 {
            alloc_user
        } else {
            0
        };
    process_init_stack_log!(
        log_fn,
        PROCESS_INIT_STACK_LOG_AP_USER,
        0 => size,
        1 => minsz,
        2 => ap_flag,
    );
    if stack_alloc_size_override != 0 {
        minsz = stack_alloc_size_override;
    }

    let stack_npages = (minsz >> (page_shift as u32)) as CInt;
    let stack = process_init_stack_alloc_aligned_result(
        stack_npages,
        user_stack_page_p2align,
        alloc_nowait | ap_flag,
        start,
        alloc_aligned_fn,
    );
    if stack.is_null() {
        process_init_stack_log!(log_fn, PROCESS_INIT_STACK_LOG_ALLOC_FAILED);
        return -ENOMEM;
    }
    process_init_stack_zero(stack.cast::<u8>(), minsz);

    let mut vrflag = VR_STACK | VR_DEMAND_PAGING | VR_PRIVATE;
    if (ap_flag & alloc_user) != 0 {
        vrflag |= VR_AP_USER;
    }
    vrflag |= ((*pn).stack_prot as CULong) << 16 & VR_PROT_MASK;
    vrflag |= VR_MAXPROT_READ | VR_MAXPROT_WRITE | VR_MAXPROT_EXEC;

    let mut range: *mut VmRange = null_mut();
    let mut error = process_init_stack_add_range_result(
        vm,
        start,
        end,
        NOPHYS,
        vrflag,
        user_stack_page_shift,
        &mut range,
        add_range_fn,
    );
    if error != 0 {
        let _ = process_init_stack_free_pages_result(stack, stack_npages, free_pages_fn);
        process_init_stack_log!(
            log_fn,
            PROCESS_INIT_STACK_LOG_ADD_FAILED,
            0 => error as CULong,
        );
        return error;
    }
    if range.is_null() {
        let _ = process_init_stack_free_pages_result(stack, stack_npages, free_pages_fn);
        return -EINVAL;
    }

    let stack_phys = process_init_stack_virt_to_phys_result(stack, virt_to_phys_fn);
    let stack_attr = process_attr_from_vrflag_result(vrflag, pf_populate, null_mut(), attr_fn);
    error = process_init_stack_pt_set_range_result(
        (*(*vm).address_space).page_table,
        vm,
        end.wrapping_sub(minsz),
        end,
        stack_phys,
        stack_attr,
        user_stack_page_shift,
        range,
        0,
        pt_set_range_fn,
    );
    if error != 0 {
        process_init_stack_log!(
            log_fn,
            PROCESS_INIT_STACK_LOG_PT_FAILED,
            0 => end.wrapping_sub(minsz),
            1 => end,
            2 => stack as CULong,
            3 => error as CULong,
        );
        let _ = process_init_stack_free_pages_result(stack, stack_npages, free_pages_fn);
        return error;
    }

    let stack_populated_size = (16usize
        + AUXV_LEN * size_of::<CULong>()
        + (argc.wrapping_add(2) as usize).wrapping_mul(size_of::<CULong>())
        + (envc.wrapping_add(1) as usize).wrapping_mul(size_of::<CULong>()))
        as CULong;
    let p = stack.cast::<u8>().add(minsz as usize).cast::<CULong>();
    let mut s_ind: isize = -1;
    let mut stack_align_padding = 0u64;
    while ((stack as CULong)
        .wrapping_add(minsz)
        .wrapping_sub(stack_populated_size)
        .wrapping_sub(stack_align_padding)
        & (0x40 - 1))
        != 0
    {
        s_ind -= 1;
        stack_align_padding = stack_align_padding.wrapping_add(size_of::<CULong>() as CULong);
    }

    process_init_stack_push(p, &mut s_ind, 0x010101011);
    process_init_stack_push(p, &mut s_ind, 0x010101011);
    let at_rand = end
        .wrapping_add(((s_ind + 1) as i64 as CULong).wrapping_mul(size_of::<CULong>() as CULong));

    process_init_stack_push(p, &mut s_ind, 0);
    process_init_stack_push(p, &mut s_ind, AT_NULL);
    process_init_stack_push(p, &mut s_ind, if argc > 0 { *argv as CULong } else { 0 });
    process_init_stack_push(p, &mut s_ind, if argc > 0 { AT_EXECFN } else { AT_IGNORE });
    process_init_stack_push(p, &mut s_ind, 0);
    process_init_stack_push(p, &mut s_ind, AT_HWCAP2);
    let ap_hwcap = process_init_stack_hwcap_result(hwcap_fn);
    process_init_stack_push(p, &mut s_ind, ap_hwcap);
    process_init_stack_push(
        p,
        &mut s_ind,
        if ap_hwcap != 0 { AT_HWCAP } else { AT_IGNORE },
    );
    process_init_stack_push(p, &mut s_ind, 0);
    process_init_stack_push(p, &mut s_ind, AT_SECURE);
    process_init_stack_push(p, &mut s_ind, (*proc).egid as CULong);
    process_init_stack_push(p, &mut s_ind, AT_EGID);
    process_init_stack_push(p, &mut s_ind, (*proc).rgid as CULong);
    process_init_stack_push(p, &mut s_ind, AT_GID);
    process_init_stack_push(p, &mut s_ind, (*proc).euid as CULong);
    process_init_stack_push(p, &mut s_ind, AT_EUID);
    process_init_stack_push(p, &mut s_ind, (*proc).ruid as CULong);
    process_init_stack_push(p, &mut s_ind, AT_UID);
    process_init_stack_push(p, &mut s_ind, (*pn).at_entry);
    process_init_stack_push(p, &mut s_ind, AT_ENTRY);
    process_init_stack_push(p, &mut s_ind, 0);
    process_init_stack_push(p, &mut s_ind, AT_FLAGS);
    process_init_stack_push(p, &mut s_ind, at_base);
    process_init_stack_push(p, &mut s_ind, AT_BASE);
    process_init_stack_push(p, &mut s_ind, (*pn).at_phnum);
    process_init_stack_push(p, &mut s_ind, AT_PHNUM);
    process_init_stack_push(p, &mut s_ind, (*pn).at_phent);
    process_init_stack_push(p, &mut s_ind, AT_PHENT);
    process_init_stack_push(p, &mut s_ind, (*pn).at_phdr);
    process_init_stack_push(p, &mut s_ind, AT_PHDR);
    process_init_stack_push(p, &mut s_ind, page_size);
    process_init_stack_push(p, &mut s_ind, AT_PAGESZ);
    process_init_stack_push(p, &mut s_ind, (*pn).at_clktck);
    process_init_stack_push(p, &mut s_ind, AT_CLKTCK);
    process_init_stack_push(p, &mut s_ind, at_rand);
    process_init_stack_push(p, &mut s_ind, AT_RANDOM);
    process_init_stack_push(p, &mut s_ind, (*vm).vdso_addr as CULong);
    process_init_stack_push(
        p,
        &mut s_ind,
        if !(*vm).vdso_addr.is_null() {
            AT_SYSINFO_EHDR
        } else {
            AT_IGNORE
        },
    );
    process_init_stack_log!(
        log_fn,
        PROCESS_INIT_STACK_LOG_AUXV,
        0 => (*proc).pid as CULong,
        1 => (*thread).tid as CULong,
        2 => (*pn).at_entry,
        3 => at_base,
        4 => (*pn).at_phdr,
        5 => (*vm).vdso_addr as CULong,
        6 => page_size,
        7 => at_rand,
        8 => end,
        9 => argc as CULong,
        10 => envc as CULong,
    );

    let aux_start = p.offset(s_ind + 1);
    let mut aux_index = 0usize;
    while aux_index < AUXV_LEN {
        write_volatile(
            &raw mut (*proc).saved_auxv[aux_index],
            *aux_start.add(aux_index),
        );
        aux_index += 1;
    }

    process_init_stack_push(p, &mut s_ind, 0);
    let mut arg_ind = envc - 1;
    while arg_ind > -1 {
        process_init_stack_push(p, &mut s_ind, *env.add(arg_ind as usize) as CULong);
        arg_ind -= 1;
    }
    process_init_stack_push(p, &mut s_ind, 0);
    arg_ind = argc - 1;
    while arg_ind > -1 {
        process_init_stack_push(p, &mut s_ind, *argv.add(arg_ind as usize) as CULong);
        arg_ind -= 1;
    }
    write_volatile(p.offset(s_ind), argc as CULong);

    let actual_stack = p.offset(s_ind) as *mut c_void;
    let expected_stack = (stack as CULong)
        .wrapping_add(minsz)
        .wrapping_sub(stack_populated_size)
        .wrapping_sub(stack_align_padding);
    if actual_stack as CULong != expected_stack {
        process_init_stack_log!(
            log_fn,
            PROCESS_INIT_STACK_LOG_SIZE_MISMATCH,
            0 => actual_stack as CULong,
            1 => expected_stack,
        );
    }
    if (actual_stack as CULong & (0x40 - 1)) != 0 {
        process_init_stack_log!(log_fn, PROCESS_INIT_STACK_LOG_ALIGN_MISMATCH);
    }

    let user_sp = process_init_stack_sp(end, s_ind);
    let argv_null_i = s_ind + argc as isize + 1;
    let env0_i = argv_null_i + 1;
    let env_null_i = env0_i + envc as isize;
    let aux0_i = env_null_i + 1;
    process_init_stack_log!(
        log_fn,
        PROCESS_INIT_STACK_LOG_INITIAL,
        0 => (*proc).pid as CULong,
        1 => (*thread).tid as CULong,
        2 => user_sp,
        3 => *p.offset(s_ind),
        4 => if argc > 0 { *p.offset(s_ind + 1) } else { 0 },
        5 => *p.offset(argv_null_i),
        6 => if envc > 0 { *p.offset(env0_i) } else { 0 },
        7 => *p.offset(env_null_i),
        8 => *p.offset(aux0_i),
        9 => *p.offset(aux0_i + 1),
    );
    let _ = process_init_stack_modify_context_result(
        (*thread).uctx.cast::<c_void>(),
        if user_context_sp_reg == 0 {
            IHK_UCR_STACK_POINTER
        } else {
            user_context_sp_reg
        },
        user_sp,
        modify_context_fn,
    );
    (*vm).region.stack_end = end;
    (*vm).region.stack_start = end.wrapping_sub(size) & user_stack_page_mask;
    0
}

#[no_mangle]
pub extern "C" fn process_ref_release_should_destroy_result(dec_and_test: CInt) -> CInt {
    (dec_and_test != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_release_address_space_should_destroy_result(dec_and_test: CInt) -> CInt {
    (dec_and_test != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_release_address_space_should_run_free_cb_result(
    free_cb_addr: CULong,
) -> CInt {
    (free_cb_addr != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_dec_and_test_result(
    object: *mut c_void,
    ref_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
) -> CInt {
    if let Some(dec) = dec_fn {
        return dec(object, ref_offset);
    }

    process_ref_dec_and_test_direct_result(object, ref_offset)
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_set_result(
    object: *mut c_void,
    ref_offset: CULong,
    value: CInt,
    ref_set_fn: Option<ProcessRefSetFn>,
) -> CInt {
    if let Some(ref_set) = ref_set_fn {
        ref_set(object, ref_offset, value);
        return 0;
    }

    process_ref_set_direct_result(object, ref_offset, value)
}

unsafe fn process_ref_atomic_at(
    object: *mut c_void,
    ref_offset: CULong,
) -> Option<&'static AtomicI32> {
    if object.is_null() {
        return None;
    }

    let atomic = object
        .cast::<u8>()
        .wrapping_add(ref_offset as usize)
        .cast::<IhkAtomic>();
    Some(AtomicI32::from_ptr(&raw mut (*atomic).counter))
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_inc_direct_result(
    object: *mut c_void,
    ref_offset: CULong,
) -> CInt {
    let Some(atomic) = process_ref_atomic_at(object, ref_offset) else {
        return -EINVAL;
    };

    let _ = atomic.fetch_add(1, Ordering::SeqCst);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_dec_and_test_direct_result(
    object: *mut c_void,
    ref_offset: CULong,
) -> CInt {
    let Some(atomic) = process_ref_atomic_at(object, ref_offset) else {
        return -EINVAL;
    };

    (atomic.fetch_sub(1, Ordering::SeqCst) - 1 == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_set_direct_result(
    object: *mut c_void,
    ref_offset: CULong,
    value: CInt,
) -> CInt {
    let Some(atomic) = process_ref_atomic_at(object, ref_offset) else {
        return -EINVAL;
    };

    atomic.store(value, Ordering::SeqCst);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_alloc_result(
    size: CULong,
    flags: CULong,
    alloc_fn: Option<ProcessAllocFn>,
) -> *mut c_void {
    let Some(alloc) = alloc_fn else {
        return null_mut();
    };

    alloc(size, flags)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_callback_result(
    ptr: *mut c_void,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(ptr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_pt_create_result(
    flags: CULong,
    pt_create_fn: Option<ProcessPtCreateFn>,
) -> *mut c_void {
    let Some(pt_create) = pt_create_fn else {
        return null_mut();
    };

    pt_create(flags)
}

#[no_mangle]
pub unsafe extern "C" fn process_pt_destroy_result(
    page_table: *mut c_void,
    pt_destroy_fn: Option<ProcessPtDestroyFn>,
) -> CInt {
    let Some(pt_destroy) = pt_destroy_fn else {
        return -EINVAL;
    };

    pt_destroy(page_table);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_init_result(
    lock_addr: CULong,
    spin_init_fn: Option<ProcessSpinInitFn>,
) -> CInt {
    let Some(spin_init) = spin_init_fn else {
        return -EINVAL;
    };

    spin_init(lock_addr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_address_space_free_cb_result(
    asp: *mut c_void,
    opt: *mut c_void,
    free_cb: Option<ProcessAddressSpaceFreeCallback>,
) -> CInt {
    let Some(free_cb) = free_cb else {
        return 0;
    };

    free_cb(asp, opt);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_address_space_action_result(
    asp: *mut c_void,
    action_fn: Option<ProcessAddressSpaceActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(asp);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_release_address_space_body_result(
    asp: *mut c_void,
    refcount_offset: CULong,
    free_cb_offset: CULong,
    opt_offset: CULong,
    page_table_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    pt_destroy_fn: Option<ProcessPtDestroyFn>,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    if asp.is_null() {
        return -EINVAL;
    }
    let Some(pt_destroy_fn) = pt_destroy_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };

    if process_release_address_space_should_destroy_result(process_ref_dec_and_test_result(
        asp,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let base = asp.cast::<u8>();
    let free_cb = *(base
        .wrapping_add(free_cb_offset as usize)
        .cast::<Option<ProcessAddressSpaceFreeCallback>>());
    if process_release_address_space_should_run_free_cb_result(
        free_cb.map_or(0, |f| f as usize as CULong),
    ) != 0
    {
        let opt = *(base.wrapping_add(opt_offset as usize).cast::<*mut c_void>());
        if let Some(free_cb) = free_cb {
            let _ = process_address_space_free_cb_result(asp, opt, Some(free_cb));
        }
    }

    let page_table = *(base
        .wrapping_add(page_table_offset as usize)
        .cast::<*mut c_void>());
    let _ = process_pt_destroy_result(page_table, Some(pt_destroy_fn));
    let _ = process_free_callback_result(asp, Some(free_fn));
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_hold_address_space_public_result(
    asp: *mut c_void,
    refcount_offset: CULong,
    inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    process_ref_hold_body_result(asp, refcount_offset, inc_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_release_address_space_public_result(
    asp: *mut c_void,
    refcount_offset: CULong,
    free_cb_offset: CULong,
    opt_offset: CULong,
    page_table_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    pt_destroy_fn: Option<ProcessPtDestroyFn>,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    process_release_address_space_body_result(
        asp,
        refcount_offset,
        free_cb_offset,
        opt_offset,
        page_table_offset,
        dec_fn,
        pt_destroy_fn,
        free_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_detach_address_space_body_result(
    asp: *mut c_void,
    pid: CInt,
    pids_offset: CULong,
    nslots_offset: CULong,
    release_fn: Option<ProcessAddressSpaceActionFn>,
) -> CInt {
    if asp.is_null() {
        return -EINVAL;
    }
    let Some(release_fn) = release_fn else {
        return -EINVAL;
    };

    let base = asp.cast::<u8>();
    let pids = base.wrapping_add(pids_offset as usize).cast::<CInt>();
    let nslots = *(base.wrapping_add(nslots_offset as usize).cast::<CInt>());
    let detached = process_address_space_pid_detach_result(pids, nslots, pid);
    let _ = process_address_space_action_result(asp, Some(release_fn));
    detached
}

#[no_mangle]
pub unsafe extern "C" fn process_detach_address_space_public_result(
    asp: *mut c_void,
    pid: CInt,
    pids_offset: CULong,
    nslots_offset: CULong,
    release_fn: Option<ProcessAddressSpaceActionFn>,
) -> CInt {
    process_detach_address_space_body_result(asp, pid, pids_offset, nslots_offset, release_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_create_address_space_body_result(
    nslots: CInt,
    address_space_size: CULong,
    pid_slot_size: CULong,
    nowait_flag: CULong,
    page_table_offset: CULong,
    refcount_offset: CULong,
    cpu_set_offset: CULong,
    cpu_set_size: CULong,
    cpu_set_lock_offset: CULong,
    nslots_offset: CULong,
    alloc_fn: Option<ProcessAllocFn>,
    free_fn: Option<ProcessFreeFn>,
    pt_create_fn: Option<ProcessPtCreateFn>,
    ref_set_fn: Option<ProcessRefSetFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
) -> *mut c_void {
    if nslots < 0 {
        return null_mut();
    }
    let Some(alloc_fn) = alloc_fn else {
        return null_mut();
    };
    let Some(free_fn) = free_fn else {
        return null_mut();
    };
    let Some(pt_create_fn) = pt_create_fn else {
        return null_mut();
    };
    let Some(spin_init_fn) = spin_init_fn else {
        return null_mut();
    };

    let total_size = address_space_size.wrapping_add(pid_slot_size.wrapping_mul(nslots as CULong));
    let asp = process_alloc_result(total_size, nowait_flag, Some(alloc_fn));
    if asp.is_null() {
        return null_mut();
    }

    let pt = process_pt_create_result(nowait_flag, Some(pt_create_fn));
    if pt.is_null() {
        let _ = process_free_callback_result(asp, Some(free_fn));
        return null_mut();
    }

    let mut offset = 0;
    while offset < total_size {
        write_volatile(asp.cast::<u8>().add(offset as usize), 0);
        offset = offset.wrapping_add(1);
    }

    let base = asp.cast::<u8>();
    *(base.wrapping_add(nslots_offset as usize).cast::<CInt>()) = nslots;
    *(base
        .wrapping_add(page_table_offset as usize)
        .cast::<*mut c_void>()) = pt;
    let _ = process_ref_set_result(asp, refcount_offset, 1, ref_set_fn);

    let mut cpu_offset = 0;
    while cpu_offset < cpu_set_size {
        write_volatile(
            base.wrapping_add(cpu_set_offset as usize)
                .add(cpu_offset as usize),
            0,
        );
        cpu_offset = cpu_offset.wrapping_add(1);
    }
    let _ = process_spin_init_result(
        base.wrapping_add(cpu_set_lock_offset as usize) as CULong,
        Some(spin_init_fn),
    );
    asp
}

#[no_mangle]
pub extern "C" fn process_create_cpu_allowed_result(cpu: CInt, num_processors: CInt) -> CInt {
    (cpu >= 0 && cpu < num_processors) as CInt
}

#[no_mangle]
pub extern "C" fn process_create_use_default_cpu_set_result(cpu_set_empty: CInt) -> CInt {
    (cpu_set_empty != 0) as CInt
}

unsafe fn process_cpu_input_bit_is_set(cpu_set_addr: CULong, cpu: CULong) -> bool {
    if cpu_set_addr == 0 {
        return false;
    }

    let word_bits = (core::mem::size_of::<CULong>() * 8) as CULong;
    let word = (cpu_set_addr as *const CULong).add((cpu / word_bits) as usize);
    let mask = 1u64.wrapping_shl((cpu % word_bits) as u32);
    (*word & mask) != 0
}

unsafe fn process_cpu_set_direct(cpu_set_addr: CULong, cpu: CInt, cpu_set_bits: CInt) -> CInt {
    if let Some((word, mask)) = process_cpu_set_word(cpu_set_addr, cpu, cpu_set_bits) {
        *word |= mask;
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_create_cpu_sets_body_result(
    requested_cpu_set_addr: CULong,
    requested_bits: CULong,
    thread_cpu_set_addr: CULong,
    proc_cpu_set_addr: CULong,
    output_cpu_set_bits: CInt,
    num_processors: CInt,
    pid: CInt,
    default_ncpus_fn: Option<ProcessDefaultNcpusFn>,
    log_fn: Option<ProcessCreateCpuLogFn>,
) -> CInt {
    if thread_cpu_set_addr == 0 || proc_cpu_set_addr == 0 || output_cpu_set_bits <= 0 {
        return -EINVAL;
    }
    if requested_bits != 0 && requested_cpu_set_addr == 0 {
        return -EINVAL;
    }

    let mut selected = 0;
    let mut cpu = 0;
    while cpu < requested_bits {
        if process_cpu_input_bit_is_set(requested_cpu_set_addr, cpu) {
            let cpu_i = cpu as CInt;
            if process_create_cpu_allowed_result(cpu_i, num_processors) == 0 {
                if let Some(log) = log_fn {
                    log(PROCESS_CREATE_CPU_LOG_INVALID, pid, cpu_i);
                }
                return -EINVAL;
            }
            if let Some(log) = log_fn {
                log(PROCESS_CREATE_CPU_LOG_REQUESTED, pid, cpu_i);
            }
            selected += process_cpu_set_direct(thread_cpu_set_addr, cpu_i, output_cpu_set_bits);
            selected += process_cpu_set_direct(proc_cpu_set_addr, cpu_i, output_cpu_set_bits);
        }
        cpu = cpu.wrapping_add(1);
    }

    if process_create_use_default_cpu_set_result((selected == 0) as CInt) != 0 {
        let Some(default_ncpus) = default_ncpus_fn else {
            return -EINVAL;
        };
        let ncpus = default_ncpus();
        if ncpus < 0 {
            return -EINVAL;
        }

        let mut default_cpu = 0;
        while default_cpu < ncpus {
            selected +=
                process_cpu_set_direct(thread_cpu_set_addr, default_cpu, output_cpu_set_bits);
            selected += process_cpu_set_direct(proc_cpu_set_addr, default_cpu, output_cpu_set_bits);
            default_cpu += 1;
        }
    }

    selected / 2
}

unsafe fn process_list_head_init(head: *mut AbiListHead) {
    if head.is_null() {
        return;
    }

    (*head).next = head;
    (*head).prev = head;
}

#[no_mangle]
pub unsafe extern "C" fn process_allocated_object_zero_body_result(
    object: *mut c_void,
    object_size: CULong,
) -> CInt {
    if object.is_null() {
        return -EINVAL;
    }

    let mut offset = 0;
    while offset < object_size {
        write_volatile(object.cast::<u8>().add(offset as usize), 0);
        offset = offset.wrapping_add(1);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_init_body_result(
    vm: *mut ProcessVm,
    owner: *mut c_void,
    asp: *mut c_void,
    nr_numa_nodes: CInt,
    memory_lock_init_fn: Option<ProcessRwlockInitFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
    numa_log_fn: Option<ProcessVmInitNumaLogFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let Some(memory_lock_init_fn) = memory_lock_init_fn else {
        return -EINVAL;
    };
    let Some(spin_init_fn) = spin_init_fn else {
        return -EINVAL;
    };

    memory_lock_init_fn((&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong);
    let _ = process_spin_init_result(
        (&raw mut (*vm).page_table_lock).cast::<c_void>() as CULong,
        Some(spin_init_fn),
    );

    (*vm).refcount.counter = 1;
    (*vm).vm_range_tree.rb_node = null_mut();
    (*vm).vm_range_numa_policy_tree.rb_node = null_mut();
    (*vm).address_space = asp.cast();
    (*vm).proc = owner;
    (*vm).exiting = 0;

    let mask_base = (&raw mut (*vm).numa_mask).cast::<CULong>();
    let mut word = 0usize;
    while word < (*vm).numa_mask.len() {
        write_volatile(mask_base.add(word), 0);
        word += 1;
    }

    let bits_per_word = size_of::<CULong>() * 8;
    let mut node = 0;
    while node < nr_numa_nodes {
        if node as usize >= PROCESS_NUMA_MASK_BITS {
            if let Some(log_fn) = numa_log_fn {
                log_fn(node);
            }
            break;
        }
        let bit = node as usize;
        let wordp = mask_base.add(bit / bits_per_word);
        let current = core::ptr::read_volatile(wordp);
        write_volatile(wordp, current | (1u64 << (bit % bits_per_word)));
        node += 1;
    }
    (*vm).numa_mem_policy = MPOL_DEFAULT;

    let cache_base = (&raw mut (*vm).range_cache).cast::<*mut VmRange>();
    let mut cache_index = 0usize;
    while cache_index < VM_RANGE_CACHE_SIZE {
        write_volatile(cache_base.add(cache_index), null_mut());
        cache_index += 1;
    }
    (*vm).range_cache_ind = 0;

    #[cfg(enable_tofu)]
    {
        let _ = process_spin_init_result(
            (&raw mut (*vm).tofu_stag_lock).cast::<c_void>() as CULong,
            Some(spin_init_fn),
        );
        let mut tofu_index = 0usize;
        while tofu_index < crate::abi::TOFU_STAG_HASH_SIZE {
            process_list_head_init(&raw mut (*vm).tofu_stag_hash[tofu_index]);
            tofu_index += 1;
        }
    }

    0
}

unsafe fn process_new_resource_cleanup(
    res: *mut ResourceSet,
    phash: *mut ProcessHash,
    thash: *mut ThreadHash,
    pid1: *mut Process,
    free_fn: ProcessFreeFn,
) -> *mut c_void {
    if !res.is_null() {
        free_fn(res.cast());
    }
    if !phash.is_null() {
        free_fn(phash.cast());
    }
    if !thash.is_null() {
        free_fn(thash.cast());
    }
    if !pid1.is_null() {
        free_fn(pid1.cast());
    }
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn process_new_resource_set_body_result(
    resource_set_size: CULong,
    process_hash_size: CULong,
    thread_hash_size: CULong,
    process_size: CULong,
    nowait_flag: CULong,
    hash_size: CInt,
    init_pid: CInt,
    alloc_fn: Option<ProcessAllocFn>,
    free_fn: Option<ProcessFreeFn>,
    init_process_fn: Option<ProcessInitProcessFn>,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
) -> *mut c_void {
    let (Some(alloc_fn), Some(free_fn), Some(init_process_fn), Some(rwlock_init_fn)) =
        (alloc_fn, free_fn, init_process_fn, rwlock_init_fn)
    else {
        return null_mut();
    };
    if hash_size <= 0 || hash_size as usize > PROCESS_HASH_SIZE {
        return null_mut();
    }

    let res = alloc_fn(resource_set_size, nowait_flag).cast::<ResourceSet>();
    let phash = alloc_fn(process_hash_size, nowait_flag).cast::<ProcessHash>();
    let thash = alloc_fn(thread_hash_size, nowait_flag).cast::<ThreadHash>();
    let pid1 = alloc_fn(process_size, nowait_flag).cast::<Process>();
    if res.is_null() || phash.is_null() || thash.is_null() || pid1.is_null() {
        return process_new_resource_cleanup(res, phash, thash, pid1, free_fn);
    }

    if process_allocated_object_zero_body_result(res.cast(), resource_set_size) < 0
        || process_allocated_object_zero_body_result(phash.cast(), process_hash_size) < 0
        || process_allocated_object_zero_body_result(thash.cast(), thread_hash_size) < 0
        || process_allocated_object_zero_body_result(pid1.cast(), process_size) < 0
    {
        return process_new_resource_cleanup(res, phash, thash, pid1, free_fn);
    }

    process_list_head_init(&raw mut (*res).phys_mem_list);
    rwlock_init_fn((&raw mut (*res).phys_mem_lock).cast::<c_void>() as CULong);
    rwlock_init_fn((&raw mut (*res).cpu_set_lock).cast::<c_void>() as CULong);

    let mut i = 0usize;
    while i < hash_size as usize {
        process_list_head_init(&raw mut (*phash).list[i]);
        rwlock_init_fn((&raw mut (*phash).lock[i]).cast::<c_void>() as CULong);
        i += 1;
    }
    (*res).process_hash = phash;

    i = 0;
    while i < hash_size as usize {
        process_list_head_init(&raw mut (*thash).list[i]);
        rwlock_init_fn((&raw mut (*thash).lock[i]).cast::<c_void>() as CULong);
        i += 1;
    }
    (*res).thread_hash = thash;

    if init_process_fn(pid1.cast(), pid1.cast()) != 0 {
        return process_new_resource_cleanup(res, phash, thash, pid1, free_fn);
    }
    (*pid1).pid = init_pid;
    let hash = (init_pid as usize) % (hash_size as usize);
    process_list_add_tail_result(&raw mut (*pid1).hash_list, &raw mut (*phash).list[hash]);
    (*res).pid1 = pid1;

    res.cast()
}

#[no_mangle]
pub unsafe extern "C" fn process_memset_smp_handler_body_result(
    cpu_index: CInt,
    nr_cpus: CInt,
    phys: CULong,
    len: SizeT,
    value: CInt,
    phys_to_virt_fn: Option<ProcessPhysToVirtFn>,
    memset_fn: Option<ProcessMemsetFn>,
    log_fn: Option<ProcessMemsetSmpLogFn>,
) -> CInt {
    let (Some(phys_to_virt), Some(memset_cb)) = (phys_to_virt_fn, memset_fn) else {
        return -EINVAL;
    };
    if cpu_index < 0 || nr_cpus <= 0 {
        return -EINVAL;
    }

    let chunk = len / nr_cpus as SizeT;
    if chunk == 0 {
        if cpu_index == 0 {
            memset_cb(phys_to_virt(phys), value, len);
        }
        return 0;
    }

    let chunk_phys = chunk as CULong;
    let start = phys.wrapping_add((cpu_index as CULong).wrapping_mul(chunk_phys));
    let mut end = start.wrapping_add(chunk_phys);
    if cpu_index == nr_cpus - 1 {
        end = phys.wrapping_add(len as CULong);
    }

    memset_cb(phys_to_virt(start), value, end.wrapping_sub(start) as SizeT);
    if let Some(log) = log_fn {
        log(1, cpu_index, nr_cpus, phys, len, start, end);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_memset_smp_body_result(
    cpu_set: *mut c_void,
    addr: *mut c_void,
    value: CInt,
    len: SizeT,
    phys_slot: *mut CULong,
    len_slot: *mut SizeT,
    value_slot: *mut CInt,
    handler: *mut c_void,
    request: *mut c_void,
    virt_to_phys_fn: Option<ProcessVirtToPhysFn>,
    smp_call_fn: Option<ProcessSmpCallFn>,
) -> CInt {
    let (Some(virt_to_phys), Some(smp_call)) = (virt_to_phys_fn, smp_call_fn) else {
        return -EINVAL;
    };
    if phys_slot.is_null()
        || len_slot.is_null()
        || value_slot.is_null()
        || handler.is_null()
        || request.is_null()
    {
        return -EINVAL;
    }

    write_volatile(phys_slot, virt_to_phys(addr));
    write_volatile(len_slot, len);
    write_volatile(value_slot, value);
    smp_call(cpu_set, handler, request)
}

#[no_mangle]
pub unsafe extern "C" fn process_proc_init_body_result(
    resource_set: *mut c_void,
    resource_set_list: *mut AbiListHead,
    resource_set_lock_addr: CULong,
    num_processors: CInt,
    cpu_set_bits: CInt,
    path_size: CULong,
    nowait_flag: CULong,
    alloc_fn: Option<ProcessAllocFn>,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
) -> CInt {
    let (Some(alloc_fn), Some(rwlock_init_fn)) = (alloc_fn, rwlock_init_fn) else {
        return -EINVAL;
    };
    if resource_set.is_null() || resource_set_list.is_null() || path_size == 0 {
        return -EINVAL;
    }

    let res = resource_set.cast::<ResourceSet>();
    process_list_head_init(resource_set_list);
    rwlock_init_fn(resource_set_lock_addr);

    let cpu_set_addr = (&raw mut (*res).cpu_set).cast::<c_void>() as CULong;
    let mut cpu = 0;
    while cpu < num_processors {
        let _ = process_cpu_set_direct(cpu_set_addr, cpu, cpu_set_bits);
        cpu += 1;
    }

    let path = alloc_fn(path_size, nowait_flag).cast::<u8>();
    if path.is_null() {
        return -ENOMEM;
    }
    write_volatile(path, b'/');
    write_volatile(path, 0);
    (*res).path = path.cast::<i8>();
    process_list_add_tail_result(&raw mut (*res).list, resource_set_list);

    0
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_init_body_result(
    cpu_local_addr: CULong,
    resource_set_list: *mut AbiListHead,
    current_cpu: CInt,
    init_process_fn: Option<ProcessInitProcessFn>,
    memory_lock_init_fn: Option<ProcessRwlockInitFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
    init_context_fn: Option<ProcessSchedInitContextFn>,
    save_fp_fn: Option<ProcessSchedSaveFpFn>,
    timer_init_fn: Option<ProcessSchedTimerInitFn>,
) -> CInt {
    let (
        Some(init_process_fn),
        Some(memory_lock_init_fn),
        Some(spin_init_fn),
        Some(init_context_fn),
        Some(save_fp_fn),
        Some(timer_init_fn),
    ) = (
        init_process_fn,
        memory_lock_init_fn,
        spin_init_fn,
        init_context_fn,
        save_fp_fn,
        timer_init_fn,
    )
    else {
        return -EINVAL;
    };
    if cpu_local_addr == 0 || resource_set_list.is_null() {
        return -EINVAL;
    }

    let cpu_local = cpu_local_addr as *mut CpuLocalVar;
    let first = (*resource_set_list).next;
    if first.is_null() || first == resource_set_list {
        return -ENOMEM;
    }
    let res = first.cast::<ResourceSet>();
    (*cpu_local).resource_set = res;

    let idle_thread = &raw mut (*cpu_local).idle;
    let idle_proc = &raw mut (*cpu_local).idle_proc;
    let idle_vm = &raw mut (*cpu_local).idle_vm;
    let idle_asp = &raw mut (*cpu_local).idle_asp;

    if process_allocated_object_zero_body_result(idle_thread.cast(), size_of::<Thread>() as CULong)
        < 0
        || process_allocated_object_zero_body_result(
            idle_vm.cast(),
            size_of::<ProcessVm>() as CULong,
        ) < 0
        || process_allocated_object_zero_body_result(
            idle_proc.cast(),
            size_of::<Process>() as CULong,
        ) < 0
    {
        return -EINVAL;
    }

    (*idle_thread).vm = idle_vm;
    (*idle_vm).address_space = idle_asp;
    (*idle_thread).proc = idle_proc;
    if init_process_fn(idle_proc.cast(), null_mut()) != 0 {
        return -EINVAL;
    }
    (*idle_proc).nohost = 1;
    (*idle_proc).vm = idle_vm;
    process_list_add_tail_result(
        &raw mut (*idle_thread).siblings_list,
        &raw mut (*idle_proc).children_list,
    );

    init_context_fn(idle_thread.cast());
    memory_lock_init_fn((&raw mut (*idle_vm).memory_range_lock).cast::<c_void>() as CULong);
    (*idle_vm).vm_range_tree.rb_node = null_mut();
    (*idle_vm).vm_range_numa_policy_tree.rb_node = null_mut();
    (*idle_proc).pid = 0;
    (*idle_thread).tid = current_cpu;

    process_list_head_init(&raw mut (*cpu_local).runq);
    (*cpu_local).runq_len = 0;
    process_spin_init_result(
        (&raw mut (*cpu_local).runq_lock).cast::<c_void>() as CULong,
        Some(spin_init_fn),
    );

    process_list_head_init(&raw mut (*cpu_local).migq);
    process_spin_init_result(
        (&raw mut (*cpu_local).migq_lock).cast::<c_void>() as CULong,
        Some(spin_init_fn),
    );

    let _ = save_fp_fn(idle_thread.cast());
    timer_init_fn(current_cpu);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_state_body_result(
    process: *mut c_void,
    parent: *const c_void,
    offsets: *const ProcessInitStateOffsets,
    initial_pid: CInt,
    running_status: CInt,
) -> CInt {
    if process.is_null() || offsets.is_null() {
        return -EINVAL;
    }

    let proc = process.cast::<u8>();
    let offsets = &*offsets;
    *proc.add(offsets.pid_offset as usize).cast::<CInt>() = initial_pid;
    *proc.add(offsets.status_offset as usize).cast::<CInt>() = running_status;

    if parent.is_null() {
        return 0;
    }

    let pproc = parent.cast::<u8>();
    *proc
        .add(offsets.parent_offset as usize)
        .cast::<*const c_void>() = parent;
    *proc
        .add(offsets.ppid_parent_offset as usize)
        .cast::<*const c_void>() = parent;
    *proc.add(offsets.pgid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.pgid_offset as usize).cast::<CInt>();
    *proc.add(offsets.ruid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.ruid_offset as usize).cast::<CInt>();
    *proc.add(offsets.euid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.euid_offset as usize).cast::<CInt>();
    *proc.add(offsets.suid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.suid_offset as usize).cast::<CInt>();
    *proc.add(offsets.fsuid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.fsuid_offset as usize).cast::<CInt>();
    *proc.add(offsets.rgid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.rgid_offset as usize).cast::<CInt>();
    *proc.add(offsets.egid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.egid_offset as usize).cast::<CInt>();
    *proc.add(offsets.sgid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.sgid_offset as usize).cast::<CInt>();
    *proc.add(offsets.fsgid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.fsgid_offset as usize).cast::<CInt>();
    *proc
        .add(offsets.mpol_flags_offset as usize)
        .cast::<CULong>() = *pproc
        .add(offsets.mpol_flags_offset as usize)
        .cast::<CULong>();
    *proc
        .add(offsets.mpol_threshold_offset as usize)
        .cast::<CULong>() = *pproc
        .add(offsets.mpol_threshold_offset as usize)
        .cast::<CULong>();
    *proc.add(offsets.thp_disable_offset as usize).cast::<CInt>() = *pproc
        .add(offsets.thp_disable_offset as usize)
        .cast::<CInt>();
    copy_nonoverlapping(
        pproc.add(offsets.rlimit_offset as usize),
        proc.add(offsets.rlimit_offset as usize),
        offsets.rlimit_size as usize,
    );
    copy_nonoverlapping(
        pproc.add(offsets.cpu_set_offset as usize),
        proc.add(offsets.cpu_set_offset as usize),
        offsets.cpu_set_size as usize,
    );
    *proc.add(offsets.enable_uti_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.enable_uti_offset as usize).cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_links_body_result(
    process: *mut c_void,
    hash_list_offset: CULong,
    siblings_list_offset: CULong,
    ptraced_siblings_list_offset: CULong,
    update_lock_offset: CULong,
    report_threads_list_offset: CULong,
    threads_list_offset: CULong,
    children_list_offset: CULong,
    ptraced_children_list_offset: CULong,
    threads_lock_offset: CULong,
    children_lock_offset: CULong,
    coredump_lock_offset: CULong,
    mckfd_lock_offset: CULong,
    waitpid_q_offset: CULong,
    refcount_offset: CULong,
    monitoring_event_offset: CULong,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
    waitq_init_fn: Option<ProcessWaitqInitFn>,
    ref_set_fn: Option<ProcessRefSetFn>,
) -> CInt {
    if process.is_null() {
        return -EINVAL;
    }
    let Some(rwlock_init_fn) = rwlock_init_fn else {
        return -EINVAL;
    };
    let Some(spin_init_fn) = spin_init_fn else {
        return -EINVAL;
    };
    let Some(waitq_init_fn) = waitq_init_fn else {
        return -EINVAL;
    };
    let proc = process.cast::<u8>();
    process_list_head_init(proc.add(hash_list_offset as usize).cast::<AbiListHead>());
    process_list_head_init(
        proc.add(siblings_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    process_list_head_init(
        proc.add(ptraced_siblings_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    rwlock_init_fn(proc.add(update_lock_offset as usize) as CULong);
    process_list_head_init(
        proc.add(report_threads_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    process_list_head_init(proc.add(threads_list_offset as usize).cast::<AbiListHead>());
    process_list_head_init(
        proc.add(children_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    process_list_head_init(
        proc.add(ptraced_children_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    rwlock_init_fn(proc.add(threads_lock_offset as usize) as CULong);
    rwlock_init_fn(proc.add(children_lock_offset as usize) as CULong);
    rwlock_init_fn(proc.add(coredump_lock_offset as usize) as CULong);
    let _ = process_spin_init_result(
        proc.add(mckfd_lock_offset as usize) as CULong,
        Some(spin_init_fn),
    );
    waitq_init_fn(proc.add(waitpid_q_offset as usize) as CULong);
    if process_ref_set_result(process, refcount_offset, 2, ref_set_fn) != 0 {
        return -EINVAL;
    }
    write_volatile(
        proc.add(monitoring_event_offset as usize)
            .cast::<*mut c_void>(),
        null_mut(),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_profile_body_result(
    process: *mut c_void,
    profile_lock_offset: CULong,
    profile_events_offset: CULong,
    lock_init_fn: Option<ProcessMcsLockInitFn>,
) -> CInt {
    if process.is_null() {
        return -EINVAL;
    }
    let Some(lock_init_fn) = lock_init_fn else {
        return -EINVAL;
    };

    let proc = process.cast::<u8>();
    lock_init_fn(proc.add(profile_lock_offset as usize) as CULong);
    write_volatile(
        proc.add(profile_events_offset as usize)
            .cast::<*mut c_void>(),
        null_mut(),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_thread_base_state_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    cpu_set_offset: CULong,
    cpu_set_size: CULong,
    in_kernel_offset: CULong,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }

    let dst = thread.cast::<u8>();
    let src = origin.cast::<u8>();
    copy_nonoverlapping(
        src.add(cpu_set_offset as usize),
        dst.add(cpu_set_offset as usize),
        cpu_set_size as usize,
    );
    *dst.add(in_kernel_offset as usize).cast::<CInt>() =
        *src.add(in_kernel_offset as usize).cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_thread_sched_state_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    sched_policy_offset: CULong,
    sched_priority_offset: CULong,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }

    let dst = thread.cast::<u8>();
    let src = origin.cast::<u8>();
    *dst.add(sched_policy_offset as usize).cast::<CInt>() =
        *src.add(sched_policy_offset as usize).cast::<CInt>();
    *dst.add(sched_priority_offset as usize).cast::<CInt>() =
        *src.add(sched_priority_offset as usize).cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_sched_default_body_result(
    thread: *mut c_void,
    sched_policy_offset: CULong,
    default_policy: CInt,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }

    *thread
        .cast::<u8>()
        .add(sched_policy_offset as usize)
        .cast::<CInt>() = default_policy;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_create_thread_link_state_body_result(
    thread: *mut c_void,
    process: *mut c_void,
    vm: *mut c_void,
    thread_vm_offset: CULong,
    thread_proc_offset: CULong,
    process_vm_offset: CULong,
    process_main_thread_offset: CULong,
) -> CInt {
    if thread.is_null() || process.is_null() || vm.is_null() {
        return -EINVAL;
    }

    let thread_base = thread.cast::<u8>();
    let process_base = process.cast::<u8>();
    *thread_base
        .add(thread_vm_offset as usize)
        .cast::<*mut c_void>() = vm;
    *thread_base
        .add(thread_proc_offset as usize)
        .cast::<*mut c_void>() = process;
    *process_base
        .add(process_vm_offset as usize)
        .cast::<*mut c_void>() = vm;
    *process_base
        .add(process_main_thread_offset as usize)
        .cast::<*mut c_void>() = thread;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_exit_status_init_body_result(
    thread: *mut c_void,
    exit_status_offset: CULong,
    exit_status: CInt,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }

    *thread
        .cast::<u8>()
        .add(exit_status_offset as usize)
        .cast::<CInt>() = exit_status;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_spin_sleep_init_body_result(
    thread: *mut c_void,
    spin_sleep_lock_offset: CULong,
    spin_sleep_offset: CULong,
    spin_init_fn: Option<ProcessSpinInitFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let Some(spin_init_fn) = spin_init_fn else {
        return -EINVAL;
    };

    let thread_base = thread.cast::<u8>();
    let _ = process_spin_init_result(
        thread_base.add(spin_sleep_lock_offset as usize) as CULong,
        Some(spin_init_fn),
    );
    *thread_base.add(spin_sleep_offset as usize).cast::<CInt>() = 0;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_sigmask_copy_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    sigmask_offset: CULong,
    sigmask_size: CULong,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }

    copy_nonoverlapping(
        origin.cast::<u8>().add(sigmask_offset as usize),
        thread.cast::<u8>().add(sigmask_offset as usize),
        sigmask_size as usize,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_profile_state_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    process: *const c_void,
    thread_profile_offset: CULong,
    process_profile_offset: CULong,
) -> CInt {
    if thread.is_null() || origin.is_null() || process.is_null() {
        return -EINVAL;
    }

    *thread
        .cast::<u8>()
        .add(thread_profile_offset as usize)
        .cast::<CInt>() = *origin
        .cast::<u8>()
        .add(thread_profile_offset as usize)
        .cast::<CInt>()
        | *process
            .cast::<u8>()
            .add(process_profile_offset as usize)
            .cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_fork_process_termsig_body_result(
    process: *mut c_void,
    termsig_offset: CULong,
    termsig: CInt,
) -> CInt {
    if process.is_null() {
        return -EINVAL;
    }

    *process
        .cast::<u8>()
        .add(termsig_offset as usize)
        .cast::<CInt>() = termsig;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_fork_saved_cmdline_body_result(
    process: *mut c_void,
    origin_process: *const c_void,
    saved_cmdline_len_offset: CULong,
    saved_cmdline_offset: CULong,
    nowait_flag: CULong,
    alloc_fn: Option<ProcessAllocFn>,
) -> CInt {
    if process.is_null() || origin_process.is_null() {
        return -EINVAL;
    }
    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };

    let dst = process.cast::<u8>();
    let src = origin_process.cast::<u8>();
    let len = *src.add(saved_cmdline_len_offset as usize).cast::<CLong>();
    *dst.add(saved_cmdline_len_offset as usize).cast::<CLong>() = len;
    let cmdline = alloc_fn(len as CULong, nowait_flag);
    if cmdline.is_null() {
        return -ENOMEM;
    }
    if len != 0 {
        let src_cmdline = *src.add(saved_cmdline_offset as usize).cast::<*const u8>();
        copy_nonoverlapping(src_cmdline, cmdline.cast::<u8>(), len as usize);
    }
    *dst.add(saved_cmdline_offset as usize).cast::<*mut c_void>() = cmdline;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_fork_vm_policy_body_result(
    dst_vm: *mut c_void,
    src_vm: *const c_void,
    numa_mask_offset: CULong,
    numa_mask_size: CULong,
    numa_mem_policy_offset: CULong,
    region_offset: CULong,
    region_size: CULong,
) -> CInt {
    if dst_vm.is_null() || src_vm.is_null() {
        return -EINVAL;
    }

    let dst = dst_vm.cast::<u8>();
    let src = src_vm.cast::<u8>();
    copy_nonoverlapping(
        src.add(numa_mask_offset as usize),
        dst.add(numa_mask_offset as usize),
        numa_mask_size as usize,
    );
    *dst.add(numa_mem_policy_offset as usize).cast::<CInt>() =
        *src.add(numa_mem_policy_offset as usize).cast::<CInt>();
    copy_nonoverlapping(
        src.add(region_offset as usize),
        dst.add(region_offset as usize),
        region_size as usize,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_thread_shared_vm_state_body_result(
    thread: *mut c_void,
    process: *mut c_void,
    vm: *mut c_void,
    thread_vm_offset: CULong,
    thread_proc_offset: CULong,
) -> CInt {
    if thread.is_null() || process.is_null() || vm.is_null() {
        return -EINVAL;
    }

    let thread_base = thread.cast::<u8>();
    *thread_base
        .add(thread_vm_offset as usize)
        .cast::<*mut c_void>() = vm;
    *thread_base
        .add(thread_proc_offset as usize)
        .cast::<*mut c_void>() = process;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_sigcommon_share_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    sigcommon_offset: CULong,
    sigcommon_use_offset: CULong,
    ref_inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }
    let sigcommon = *origin
        .cast::<u8>()
        .add(sigcommon_offset as usize)
        .cast::<*mut c_void>();
    if sigcommon.is_null() {
        return -EINVAL;
    }
    *thread
        .cast::<u8>()
        .add(sigcommon_offset as usize)
        .cast::<*mut c_void>() = sigcommon;
    process_ref_inc_result(sigcommon, sigcommon_use_offset, ref_inc_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_sigcommon_action_copy_body_result(
    dst_sigcommon: *mut c_void,
    src_sigcommon: *const c_void,
    action_offset: CULong,
    action_size: CULong,
) -> CInt {
    if dst_sigcommon.is_null() || src_sigcommon.is_null() {
        return -EINVAL;
    }

    copy_nonoverlapping(
        src_sigcommon.cast::<u8>().add(action_offset as usize),
        dst_sigcommon.cast::<u8>().add(action_offset as usize),
        action_size as usize,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_user_context_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    uctx_offset: CULong,
    uctx_size: CULong,
    stack_pointer_reg: CInt,
    sp: CULong,
    program_counter_reg: CInt,
    pc: CULong,
    modify_context_fn: Option<ProcessInitStackModifyContextFn>,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }
    let Some(modify_context_fn) = modify_context_fn else {
        return -EINVAL;
    };

    let dst_uctx = *thread
        .cast::<u8>()
        .add(uctx_offset as usize)
        .cast::<*mut u8>();
    let src_uctx = *origin
        .cast::<u8>()
        .add(uctx_offset as usize)
        .cast::<*const u8>();
    if dst_uctx.is_null() || src_uctx.is_null() {
        return -EINVAL;
    }

    copy_nonoverlapping(src_uctx, dst_uctx, uctx_size as usize);
    modify_context_fn(dst_uctx.cast::<c_void>(), stack_pointer_reg, sp);
    modify_context_fn(dst_uctx.cast::<c_void>(), program_counter_reg, pc);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_fork_profile_body_result(
    process: *mut c_void,
    origin_process: *const c_void,
    profile_offset: CULong,
) -> CInt {
    if process.is_null() || origin_process.is_null() {
        return -EINVAL;
    }

    *process
        .cast::<u8>()
        .add(profile_offset as usize)
        .cast::<CInt>() = *origin_process
        .cast::<u8>()
        .add(profile_offset as usize)
        .cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_on_fork_vm_body_result(
    cpu_local: *mut c_void,
    on_fork_vm_offset: CULong,
    vm: *mut c_void,
) -> CInt {
    if cpu_local.is_null() {
        return -EINVAL;
    }

    *cpu_local
        .cast::<u8>()
        .add(on_fork_vm_offset as usize)
        .cast::<*mut c_void>() = vm;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_copy_body_result(
    dst: *mut c_void,
    src: *const c_void,
    mckfd_size: CULong,
) -> CInt {
    if dst.is_null() || src.is_null() {
        return -EINVAL;
    }

    copy_nonoverlapping(src.cast::<u8>(), dst.cast::<u8>(), mckfd_size as usize);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_copy_user_range_metadata_body_result(
    dst: *mut VmRange,
    src: *const VmRange,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if dst.is_null() || src.is_null() {
        return -EINVAL;
    }

    (*dst).vm_rb_node.__rb_parent_color = core::ptr::addr_of_mut!((*dst).vm_rb_node) as CULong;
    (*dst).start = (*src).start;
    (*dst).end = (*src).end;
    (*dst).flag = (*src).flag;
    (*dst).memobj = (*src).memobj;
    (*dst).objoff = (*src).objoff;
    (*dst).pgshift = (*src).pgshift;
    (*dst).private_data = (*src).private_data;
    (*dst).straight_start = (*src).straight_start;

    process_range_memobj_ref_or_direct_result((*dst).memobj, memobj_ref_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_copy_user_pte_args_init_body_result(
    args: *mut c_void,
    new_vm_offset: CULong,
    new_vrflag_offset: CULong,
    range_offset: CULong,
    fault_addr_offset: CULong,
    vm: *mut c_void,
    vrflag: CULong,
    range: *mut c_void,
    fault_addr: CLong,
) -> CInt {
    if args.is_null() || vm.is_null() || range.is_null() {
        return -EINVAL;
    }

    let base = args.cast::<u8>();
    *base.add(new_vm_offset as usize).cast::<*mut c_void>() = vm;
    *base.add(new_vrflag_offset as usize).cast::<CULong>() = vrflag;
    *base.add(range_offset as usize).cast::<*mut c_void>() = range;
    *base.add(fault_addr_offset as usize).cast::<CLong>() = fault_addr;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_copy_user_pte_buffer_body_result(
    dst: *mut c_void,
    src: *const c_void,
    len: SizeT,
    wipe: CInt,
) -> CInt {
    if dst.is_null() || (wipe == 0 && src.is_null()) {
        return -EINVAL;
    }

    if wipe != 0 {
        core::ptr::write_bytes(dst.cast::<u8>(), 0, len);
    } else {
        copy_nonoverlapping(src.cast::<u8>(), dst.cast::<u8>(), len);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_copy_user_ranges_body_result(
    vm: *mut ProcessVm,
    orgvm: *mut ProcessVm,
    range_size: CULong,
    _alloc_flags: CULong,
    copy_args: *mut c_void,
    new_vm_offset: CULong,
    new_vrflag_offset: CULong,
    range_offset: CULong,
    fault_addr_offset: CULong,
    copy_pte_fn: *mut c_void,
    visit_flags: CInt,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    lookup_fn: Option<ProcessCopyRangeLookupFn>,
    next_fn: Option<ProcessCopyRangeNextFn>,
    alloc_fn: Option<ProcessAddRangeAllocFn>,
    free_fn: Option<ProcessAddRangeFreeFn>,
    insert_fn: Option<ProcessAddRangeInsertFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    free_range_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessCopyUserRangesLogFn>,
) -> CInt {
    if vm.is_null()
        || orgvm.is_null()
        || copy_args.is_null()
        || copy_pte_fn.is_null()
        || (*orgvm).address_space.is_null()
    {
        return -EINVAL;
    }

    let Some(read_lock) = read_lock_fn else {
        return -EINVAL;
    };
    let Some(read_unlock) = read_unlock_fn else {
        return -EINVAL;
    };
    let Some(lookup) = lookup_fn else {
        return -EINVAL;
    };
    let Some(next) = next_fn else {
        return -EINVAL;
    };
    let Some(alloc) = alloc_fn else {
        return -EINVAL;
    };
    let Some(free) = free_fn else {
        return -EINVAL;
    };
    let Some(insert) = insert_fn else {
        return -EINVAL;
    };
    let Some(visit) = visit_fn else {
        return -EINVAL;
    };
    let Some(free_range) = free_range_fn else {
        return -EINVAL;
    };

    let lock_addr = (&raw mut (*orgvm).memory_range_lock).cast::<c_void>() as CULong;
    let lock_rc = process_noirq_lock_result(lock_addr, Some(read_lock));
    if lock_rc != 0 {
        return lock_rc;
    }

    let mut error: CInt = 0;
    let mut src_range: *mut VmRange = null_mut();
    let mut last_insert: *mut VmRange = null_mut();

    loop {
        src_range = if src_range.is_null() {
            lookup(orgvm, 0, NOPHYS)
        } else {
            next(orgvm, src_range)
        };
        if src_range.is_null() {
            break;
        }

        if ((*src_range).flag & VR_DONTFORK) != 0 {
            continue;
        }

        let range = alloc(range_size);
        if range.is_null() {
            error = -1;
            break;
        }

        if process_copy_user_range_metadata_body_result(range, src_range, None) < 0 {
            free(range);
            error = -1;
            break;
        }

        let _ = insert(vm.cast::<c_void>(), range);
        last_insert = src_range;

        if process_copy_user_pte_args_init_body_result(
            copy_args,
            new_vm_offset,
            new_vrflag_offset,
            range_offset,
            fault_addr_offset,
            vm.cast::<c_void>(),
            (*range).flag,
            range.cast::<c_void>(),
            -1,
        ) < 0
        {
            error = -1;
            break;
        }

        error = visit(
            (*(*orgvm).address_space).page_table,
            (*range).start,
            (*range).end,
            (*range).pgshift,
            visit_flags,
            copy_pte_fn,
            copy_args,
        );
        if error != 0 {
            let fault_addr = *copy_args
                .cast::<u8>()
                .add(fault_addr_offset as usize)
                .cast::<CLong>();
            if fault_addr != -1 {
                if let Some(log) = log_fn {
                    log(orgvm, range, fault_addr);
                }
            }
            error = -1;
            break;
        }
    }

    if error != 0 && !last_insert.is_null() {
        src_range = lookup(orgvm, 0, NOPHYS);
        while !src_range.is_null() {
            if ((*src_range).flag & VR_DONTFORK) == 0 {
                let dest_range = lookup(vm, (*src_range).start, (*src_range).end);
                if !dest_range.is_null() {
                    let _ = process_memory_range_free_result(
                        vm.cast::<c_void>(),
                        dest_range.cast::<c_void>(),
                        Some(free_range),
                    );
                }
                if src_range == last_insert {
                    break;
                }
            }
            src_range = next(orgvm, src_range);
        }
    }

    let _ = process_noirq_unlock_result(lock_addr, Some(read_unlock));
    if error == 0 { 0 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn process_sigcommon_alloc_init_body_result(
    sigcommon_size: CULong,
    flags: CULong,
    use_offset: CULong,
    lock_offset: CULong,
    sigpending_offset: CULong,
    alloc_fn: Option<ProcessAllocFn>,
    free_fn: Option<ProcessFreeFn>,
    ref_set_fn: Option<ProcessRefSetFn>,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
) -> *mut c_void {
    let Some(alloc) = alloc_fn else {
        return null_mut();
    };
    let Some(free_fn) = free_fn else {
        return null_mut();
    };
    let Some(rwlock_init_fn) = rwlock_init_fn else {
        return null_mut();
    };

    let sigcommon = process_alloc_result(sigcommon_size, flags, Some(alloc));
    if sigcommon.is_null() {
        return null_mut();
    }

    let mut offset = 0;
    while offset < sigcommon_size {
        write_volatile(sigcommon.cast::<u8>().add(offset as usize), 0);
        offset = offset.wrapping_add(1);
    }

    if process_ref_set_result(sigcommon, use_offset, 1, ref_set_fn) != 0 {
        let _ = process_free_callback_result(sigcommon, Some(free_fn));
        return null_mut();
    }
    rwlock_init_fn(sigcommon.cast::<u8>().add(lock_offset as usize) as CULong);
    process_list_head_init(
        sigcommon
            .cast::<u8>()
            .add(sigpending_offset as usize)
            .cast::<AbiListHead>(),
    );
    sigcommon
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_sigpending_init_body_result(
    thread: *mut c_void,
    lock_offset: CULong,
    sigpending_offset: CULong,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let Some(rwlock_init_fn) = rwlock_init_fn else {
        return -EINVAL;
    };

    rwlock_init_fn(thread.cast::<u8>().add(lock_offset as usize) as CULong);
    process_list_head_init(
        thread
            .cast::<u8>()
            .add(sigpending_offset as usize)
            .cast::<AbiListHead>(),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_alloc_init_body_result(
    thread: *mut c_void,
    thread_size: CULong,
    refcount_offset: CULong,
    hash_list_offset: CULong,
    siblings_list_offset: CULong,
    ref_set_fn: Option<ProcessRefSetFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let mut offset = 0;
    while offset < thread_size {
        write_volatile(thread.cast::<u8>().add(offset as usize), 0);
        offset = offset.wrapping_add(1);
    }
    if process_ref_set_result(thread, refcount_offset, 2, ref_set_fn) != 0 {
        return -EINVAL;
    }
    process_list_head_init(
        thread
            .cast::<u8>()
            .add(hash_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    process_list_head_init(
        thread
            .cast::<u8>()
            .add(siblings_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_sigstack_disable_body_result(
    thread: *mut c_void,
    sigstack_offset: CULong,
    sp_offset: CULong,
    flags_offset: CULong,
    size_offset: CULong,
    disable_flag: CInt,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }

    let sigstack = thread.cast::<u8>().add(sigstack_offset as usize);
    write_volatile(
        sigstack.add(sp_offset as usize).cast::<*mut c_void>(),
        null_mut(),
    );
    write_volatile(
        sigstack.add(flags_offset as usize).cast::<CInt>(),
        disable_flag,
    );
    write_volatile(sigstack.add(size_offset as usize).cast::<SizeT>(), 0);
    0
}

unsafe fn process_create_thread_cleanup(
    thread: *mut c_void,
    proc: *mut c_void,
    vm: *mut c_void,
    asp: *mut c_void,
    thread_sigcommon_offset: CULong,
    free_fn: ProcessFreeFn,
    release_address_space_fn: ProcessReleaseAddressSpaceFn,
    free_thread_fn: ProcessThreadActionFn,
) -> *mut c_void {
    if !proc.is_null() {
        let _ = process_free_callback_result(proc, Some(free_fn));
    }
    if !vm.is_null() {
        let _ = process_free_callback_result(vm, Some(free_fn));
    }
    if !asp.is_null() {
        release_address_space_fn(asp);
    }
    if !thread.is_null() {
        let sigcommon = *(thread
            .cast::<u8>()
            .add(thread_sigcommon_offset as usize)
            .cast::<*mut c_void>());
        if !sigcommon.is_null() {
            let _ = process_free_callback_result(sigcommon, Some(free_fn));
        }
        let _ = process_thread_action_result(thread, Some(free_thread_fn));
    }
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn process_create_thread_body_result(
    user_pc: CULong,
    requested_cpu_set_addr: CULong,
    requested_bits: CULong,
    thread_pages: CULong,
    thread_size: CULong,
    process_size: CULong,
    vm_size: CULong,
    nowait_flag: CULong,
    kernel_stack_bytes: CULong,
    cpu_set_bits: CInt,
    num_processors: CInt,
    sched_normal: CInt,
    ss_disable: CInt,
    current_cpu: CInt,
    parent_process: *mut c_void,
    process_pid_offset: CULong,
    thread_refcount_offset: CULong,
    thread_hash_list_offset: CULong,
    thread_siblings_list_offset: CULong,
    thread_cpu_set_offset: CULong,
    thread_sched_policy_offset: CULong,
    thread_sigcommon_offset: CULong,
    thread_sigpendinglock_offset: CULong,
    thread_sigpending_offset: CULong,
    thread_sigstack_offset: CULong,
    sigstack_sp_offset: CULong,
    sigstack_flags_offset: CULong,
    sigstack_size_offset: CULong,
    thread_vm_offset: CULong,
    thread_proc_offset: CULong,
    process_cpu_set_offset: CULong,
    process_vm_offset: CULong,
    process_main_thread_offset: CULong,
    vm_address_space_offset: CULong,
    address_space_cpu_set_offset: CULong,
    address_space_cpu_set_lock_offset: CULong,
    thread_exit_status_offset: CULong,
    thread_spin_sleep_lock_offset: CULong,
    thread_spin_sleep_offset: CULong,
    sigcommon_size: CULong,
    sigcommon_use_offset: CULong,
    sigcommon_lock_offset: CULong,
    sigcommon_sigpending_offset: CULong,
    alloc_pages_fn: Option<ProcessAllocPagesFn>,
    alloc_fn: Option<ProcessAllocFn>,
    free_fn: Option<ProcessFreeFn>,
    create_address_space_fn: Option<ProcessCreateAddressSpaceFn>,
    release_address_space_fn: Option<ProcessReleaseAddressSpaceFn>,
    init_process_fn: Option<ProcessInitProcessFn>,
    init_process_vm_fn: Option<ProcessInitProcessVmFn>,
    init_user_process_fn: Option<ProcessInitUserProcessFn>,
    default_ncpus_fn: Option<ProcessDefaultNcpusFn>,
    cpu_log_fn: Option<ProcessCreateCpuLogFn>,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
    spin_lock_fn: Option<ProcessSpinLockFn>,
    spin_unlock_fn: Option<ProcessSpinUnlockFn>,
    free_thread_fn: Option<ProcessThreadActionFn>,
) -> *mut c_void {
    let (
        Some(alloc_pages_fn),
        Some(alloc_fn),
        Some(free_fn),
        Some(create_address_space_fn),
        Some(release_address_space_fn),
        Some(init_process_fn),
        Some(init_process_vm_fn),
        Some(init_user_process_fn),
        Some(rwlock_init_fn),
        Some(spin_init_fn),
        Some(spin_lock_fn),
        Some(spin_unlock_fn),
        Some(free_thread_fn),
    ) = (
        alloc_pages_fn,
        alloc_fn,
        free_fn,
        create_address_space_fn,
        release_address_space_fn,
        init_process_fn,
        init_process_vm_fn,
        init_user_process_fn,
        rwlock_init_fn,
        spin_init_fn,
        spin_lock_fn,
        spin_unlock_fn,
        free_thread_fn,
    )
    else {
        return null_mut();
    };

    let thread = alloc_pages_fn(thread_pages as CInt, nowait_flag);
    if thread.is_null() {
        return null_mut();
    }
    if process_thread_alloc_init_body_result(
        thread,
        thread_size,
        thread_refcount_offset,
        thread_hash_list_offset,
        thread_siblings_list_offset,
        None,
    ) < 0
    {
        let _ = process_thread_action_result(thread, Some(free_thread_fn));
        return null_mut();
    }

    let proc = process_alloc_result(process_size, nowait_flag, Some(alloc_fn));
    let vm = process_alloc_result(vm_size, nowait_flag, Some(alloc_fn));
    let asp = create_address_space_fn(1);
    if proc.is_null() || vm.is_null() || asp.is_null() {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    if process_allocated_object_zero_body_result(proc, process_size) < 0
        || process_allocated_object_zero_body_result(vm, vm_size) < 0
        || init_process_fn(proc, parent_process) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    let thread_base = thread.cast::<u8>();
    let proc_base = proc.cast::<u8>();
    let pid = *proc_base.add(process_pid_offset as usize).cast::<CInt>();
    if process_create_cpu_sets_body_result(
        requested_cpu_set_addr,
        requested_bits,
        thread_base.add(thread_cpu_set_offset as usize) as CULong,
        proc_base.add(process_cpu_set_offset as usize) as CULong,
        cpu_set_bits,
        num_processors,
        pid,
        default_ncpus_fn,
        cpu_log_fn,
    ) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    if process_thread_sched_default_body_result(thread, thread_sched_policy_offset, sched_normal)
        < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    let sigcommon = process_sigcommon_alloc_init_body_result(
        sigcommon_size,
        nowait_flag,
        sigcommon_use_offset,
        sigcommon_lock_offset,
        sigcommon_sigpending_offset,
        Some(alloc_fn),
        Some(free_fn),
        None,
        Some(rwlock_init_fn),
    );
    *thread_base
        .add(thread_sigcommon_offset as usize)
        .cast::<*mut c_void>() = sigcommon;
    if sigcommon.is_null() {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    if process_thread_sigpending_init_body_result(
        thread,
        thread_sigpendinglock_offset,
        thread_sigpending_offset,
        Some(rwlock_init_fn),
    ) < 0
        || process_thread_sigstack_disable_body_result(
            thread,
            thread_sigstack_offset,
            sigstack_sp_offset,
            sigstack_flags_offset,
            sigstack_size_offset,
            ss_disable,
        ) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    init_user_process_fn(
        thread,
        (thread as CULong).wrapping_add(kernel_stack_bytes),
        user_pc,
        0,
    );

    if process_create_thread_link_state_body_result(
        thread,
        proc,
        vm,
        thread_vm_offset,
        thread_proc_offset,
        process_vm_offset,
        process_main_thread_offset,
    ) < 0
        || init_process_vm_fn(proc, asp, vm) != 0
        || process_thread_exit_status_init_body_result(thread, thread_exit_status_offset, -1) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    let asp_base = asp.cast::<u8>();
    let _ = process_cpu_set_update_body_result(
        asp_base.add(address_space_cpu_set_offset as usize) as CULong,
        asp_base.add(address_space_cpu_set_lock_offset as usize) as CULong,
        -1,
        current_cpu,
        num_processors,
        Some(spin_lock_fn),
        Some(spin_unlock_fn),
    );

    if process_thread_spin_sleep_init_body_result(
        thread,
        thread_spin_sleep_lock_offset,
        thread_spin_sleep_offset,
        Some(spin_init_fn),
    ) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    let _ = vm_address_space_offset;
    thread
}

#[no_mangle]
pub unsafe extern "C" fn process_address_space_pid_detach_result(
    pids: *mut CInt,
    nslots: CInt,
    pid: CInt,
) -> CInt {
    if pids.is_null() || nslots <= 0 {
        return -1;
    }

    let mut i = 0;
    while i < nslots {
        let slot = pids.add(i as usize);
        if *slot == pid {
            *slot = 0;
            return i;
        }
        i += 1;
    }

    -1
}

#[no_mangle]
pub extern "C" fn process_clone_shares_vm_result(clone_flags: CInt) -> CInt {
    ((clone_flags & CLONE_VM) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_clone_shares_sighand_result(clone_flags: CInt) -> CInt {
    ((clone_flags & CLONE_SIGHAND) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_mckfd_should_dup_result(dup_cb_addr: CULong) -> CInt {
    (dup_cb_addr != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_dup_result(
    fdp: *mut c_void,
    dup_fn: Option<ProcessMckfdDupFn>,
) -> CInt {
    let Some(dup) = dup_fn else {
        return 0;
    };

    dup(fdp, null_mut())
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_copy_vm_thread_state_result(
    dst_vm: *mut c_void,
    src_vm: *const c_void,
    vdso_offset: CULong,
    vvar_offset: CULong,
    dst_thread: *mut c_void,
    src_thread: *const c_void,
    sigstack_offset: CULong,
    sigstack_size: usize,
) -> CInt {
    if dst_vm.is_null() || src_vm.is_null() || dst_thread.is_null() || src_thread.is_null() {
        return 0;
    }

    let dvm = dst_vm.cast::<u8>();
    let svm = src_vm.cast::<u8>();
    let dthread = dst_thread.cast::<u8>();
    let sthread = src_thread.cast::<u8>();

    *(dvm.add(vdso_offset as usize).cast::<*mut c_void>()) =
        *(svm.add(vdso_offset as usize).cast::<*mut c_void>());
    *(dvm.add(vvar_offset as usize).cast::<*mut c_void>()) =
        *(svm.add(vvar_offset as usize).cast::<*mut c_void>());
    copy_nonoverlapping(
        sthread.add(sigstack_offset as usize),
        dthread.add(sigstack_offset as usize),
        sigstack_size,
    );

    1
}

#[no_mangle]
pub unsafe extern "C" fn process_tid_index_for_thread_result(
    tids: *const c_void,
    nr_tids: CInt,
    entry_stride: CULong,
    thread_offset: CULong,
    thread_addr: CULong,
) -> CInt {
    if tids.is_null() || nr_tids <= 0 || entry_stride == 0 || thread_addr == 0 {
        return -1;
    }

    let base = tids.cast::<u8>();
    let stride = entry_stride as usize;
    let offset = thread_offset as usize;

    for index in 0..(nr_tids as usize) {
        let entry = base.add(index.saturating_mul(stride).saturating_add(offset));
        let stored = *(entry.cast::<CULong>());
        if stored == thread_addr {
            return index as CInt;
        }
    }

    -1
}

#[no_mangle]
pub extern "C" fn process_tid_index_found_result(index: CInt) -> CInt {
    (index >= 0) as CInt
}

fn checked_entry_addr(
    base: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    member_offset: CULong,
) -> Option<*mut u8> {
    if base.is_null() || index < 0 || entry_stride == 0 {
        return None;
    }

    let offset = (index as usize)
        .checked_mul(entry_stride as usize)?
        .checked_add(member_offset as usize)?;
    Some(base.cast::<u8>().wrapping_add(offset))
}

#[no_mangle]
pub unsafe extern "C" fn process_tid_release_slot_result(
    tids: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    thread_offset: CULong,
) -> CInt {
    let Some(thread_slot) = checked_entry_addr(tids, index, entry_stride, thread_offset) else {
        return 0;
    };

    *(thread_slot.cast::<CULong>()) = 0;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_tid_replace_slot_result(
    tids: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    tid_offset: CULong,
    thread_offset: CULong,
    new_tid: CInt,
) -> CInt {
    let Some(tid_slot) = checked_entry_addr(tids, index, entry_stride, tid_offset) else {
        return 0;
    };
    let Some(thread_slot) = checked_entry_addr(tids, index, entry_stride, thread_offset) else {
        return 0;
    };

    *(thread_slot.cast::<CULong>()) = 0;
    *(tid_slot.cast::<CInt>()) = new_tid;
    1
}

#[no_mangle]
pub extern "C" fn process_sigpending_cleanup_needed_result(list_empty: CInt) -> CInt {
    (list_empty == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_sigpending_pop_front_result(
    head: *mut AbiListHead,
    list_offset: CULong,
) -> *mut c_void {
    if head.is_null() {
        return core::ptr::null_mut();
    }

    let first = (*head).next;
    if first.is_null() || first == head {
        return core::ptr::null_mut();
    }

    let next = (*first).next;
    (*head).next = next;
    if !next.is_null() {
        (*next).prev = head;
    }
    (*first).next = LIST_POISON1 as *mut AbiListHead;
    (*first).prev = LIST_POISON2 as *mut AbiListHead;

    first.cast::<u8>().wrapping_sub(list_offset as usize).cast()
}

#[no_mangle]
pub unsafe extern "C" fn process_sigpending_drain_free_result(
    head: *mut AbiListHead,
    list_offset: CULong,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    if head.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut freed = 0;
    loop {
        let pending = process_sigpending_pop_front_result(head, list_offset);
        if pending.is_null() {
            break;
        }
        let _ = process_free_callback_result(pending, Some(free_fn));
        freed += 1;
    }

    freed
}

#[no_mangle]
pub unsafe extern "C" fn process_list_is_linked_result(entry: *const AbiListHead) -> CInt {
    if entry.is_null() {
        return 0;
    }

    let next = (*entry).next;
    (!next.is_null() && next != entry.cast_mut()) as CInt
}

unsafe fn list_detach(entry: *mut AbiListHead) -> bool {
    if entry.is_null() {
        return false;
    }

    let prev = (*entry).prev;
    let next = (*entry).next;
    if prev.is_null() || next.is_null() || next == entry {
        return false;
    }

    (*next).prev = prev;
    (*prev).next = next;
    (*entry).next = LIST_POISON1 as *mut AbiListHead;
    (*entry).prev = LIST_POISON2 as *mut AbiListHead;
    true
}

#[no_mangle]
pub unsafe extern "C" fn process_list_detach_result(entry: *mut AbiListHead) {
    let _ = list_detach(entry);
}

#[no_mangle]
pub unsafe extern "C" fn process_list_detach_counted_result(
    entry: *mut AbiListHead,
    lenp: *mut CULong,
) -> CInt {
    if lenp.is_null() || !list_detach(entry) {
        return 0;
    }

    *lenp = (*lenp).wrapping_sub(1);
    1
}

unsafe fn list_add_tail(entry: *mut AbiListHead, head: *mut AbiListHead) -> bool {
    if entry.is_null() || head.is_null() {
        return false;
    }

    let prev = (*head).prev;
    if prev.is_null() {
        return false;
    }

    (*entry).next = head;
    (*entry).prev = prev;
    (*prev).next = entry;
    (*head).prev = entry;
    true
}

#[no_mangle]
pub unsafe extern "C" fn process_list_add_tail_result(
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
) {
    let _ = list_add_tail(entry, head);
}

#[no_mangle]
pub unsafe extern "C" fn process_list_add_tail_counted_result(
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
    lenp: *mut CULong,
) -> CInt {
    if lenp.is_null() || !list_add_tail(entry, head) {
        return 0;
    }

    *lenp = (*lenp).wrapping_add(1);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_list_move_tail_result(
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
) -> CInt {
    if entry.is_null() || head.is_null() {
        return 0;
    }
    if !list_detach(entry) {
        return 0;
    }
    list_add_tail(entry, head) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_list_del_init_result(entry: *mut AbiListHead) -> CInt {
    if entry.is_null() {
        return 0;
    }

    let prev = (*entry).prev;
    let next = (*entry).next;
    if prev.is_null() || next.is_null() {
        return 0;
    }

    if next != entry {
        (*next).prev = prev;
        (*prev).next = next;
    }
    (*entry).next = entry;
    (*entry).prev = entry;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_child_reparent_result(
    child: *mut c_void,
    ppid_parent_offset: CULong,
    parent_offset: CULong,
    new_parent: *mut c_void,
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
    update_parent: CInt,
) -> CInt {
    if child.is_null() || new_parent.is_null() || entry.is_null() || head.is_null() {
        return 0;
    }

    let base = child.cast::<u8>();
    *(base
        .wrapping_add(ppid_parent_offset as usize)
        .cast::<*mut c_void>()) = new_parent;
    if update_parent != 0 {
        *(base
            .wrapping_add(parent_offset as usize)
            .cast::<*mut c_void>()) = new_parent;
    }

    process_list_move_tail_result(entry, head)
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_report_attach_result(
    thread: *mut c_void,
    termsig_offset: CULong,
    update_termsig: CInt,
    termsig: CInt,
    report_proc_offset: CULong,
    report_proc: *mut c_void,
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
) -> CInt {
    if thread.is_null() || report_proc.is_null() || entry.is_null() || head.is_null() {
        return 0;
    }

    let base = thread.cast::<u8>();
    if update_termsig != 0 {
        *(base.wrapping_add(termsig_offset as usize).cast::<CInt>()) = termsig;
    }
    *(base
        .wrapping_add(report_proc_offset as usize)
        .cast::<*mut c_void>()) = report_proc;

    list_add_tail(entry, head) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_report_detach_result(
    thread: *mut c_void,
    report_proc_offset: CULong,
    report_proc: *mut c_void,
    entry: *mut AbiListHead,
) -> CInt {
    if thread.is_null() || entry.is_null() {
        return 0;
    }

    *(thread
        .cast::<u8>()
        .wrapping_add(report_proc_offset as usize)
        .cast::<*mut c_void>()) = report_proc;
    list_detach(entry) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_ptrace_main_detach_reparent_result(
    process: *mut c_void,
    parent_offset: CULong,
    parent: *mut c_void,
    ptraced_entry: *mut AbiListHead,
    sibling_entry: *mut AbiListHead,
    children_head: *mut AbiListHead,
) -> CInt {
    if process.is_null()
        || parent.is_null()
        || ptraced_entry.is_null()
        || sibling_entry.is_null()
        || children_head.is_null()
    {
        return 0;
    }
    let _ = list_detach(ptraced_entry);
    if !list_add_tail(sibling_entry, children_head) {
        return 0;
    }

    *(process
        .cast::<u8>()
        .wrapping_add(parent_offset as usize)
        .cast::<*mut c_void>()) = parent;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_ptrace_main_attach_reparent_result(
    process: *mut c_void,
    parent_offset: CULong,
    parent: *mut c_void,
    sibling_entry: *mut AbiListHead,
    children_head: *mut AbiListHead,
) -> CInt {
    if process.is_null() || parent.is_null() || sibling_entry.is_null() || children_head.is_null() {
        return 0;
    }
    if !list_add_tail(sibling_entry, children_head) {
        return 0;
    }

    *(process
        .cast::<u8>()
        .wrapping_add(parent_offset as usize)
        .cast::<*mut c_void>()) = parent;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_termsig_clear_result(
    thread: *mut c_void,
    termsig_offset: CULong,
    clear_termsig: CInt,
) -> CInt {
    if thread.is_null() || clear_termsig == 0 {
        return 0;
    }

    *(thread
        .cast::<u8>()
        .wrapping_add(termsig_offset as usize)
        .cast::<CInt>()) = 0;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_cleanup_result(
    thread: *mut c_void,
    ptrace_offset: CULong,
    saved_valid_offset: CULong,
    debugreg_offset: CULong,
) -> *mut c_void {
    if thread.is_null() {
        return core::ptr::null_mut();
    }

    let base = thread.cast::<u8>();
    let debugreg_slot = base
        .wrapping_add(debugreg_offset as usize)
        .cast::<*mut c_void>();
    let debugreg = *debugreg_slot;
    *(base.wrapping_add(ptrace_offset as usize).cast::<CInt>()) = 0;
    *(base
        .wrapping_add(saved_valid_offset as usize)
        .cast::<CInt>()) = 0;
    *debugreg_slot = core::ptr::null_mut();
    debugreg
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_saved_context_clear_result(
    thread: *mut c_void,
    saved_valid_offset: CULong,
) -> CInt {
    if thread.is_null() {
        return 0;
    }

    *(thread
        .cast::<u8>()
        .wrapping_add(saved_valid_offset as usize)
        .cast::<CInt>()) = 0;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_trace_syscall_update_result(
    thread: *mut c_void,
    ptrace_offset: CULong,
    trace_syscall: CInt,
) -> CInt {
    if thread.is_null() {
        return 0;
    }

    let ptrace = thread
        .cast::<u8>()
        .wrapping_add(ptrace_offset as usize)
        .cast::<CInt>();
    *ptrace &= !PT_TRACE_SYSCALL;
    if trace_syscall != 0 {
        *ptrace |= PT_TRACE_SYSCALL;
    }
    *ptrace
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_pending_signal_take_result(
    thread: *mut c_void,
    sendsig_offset: CULong,
    recvsig_offset: CULong,
    source: CInt,
) -> *mut c_void {
    if thread.is_null() {
        return core::ptr::null_mut();
    }

    let base = thread.cast::<u8>();
    let slot = if source == PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG {
        base.wrapping_add(sendsig_offset as usize)
            .cast::<*mut c_void>()
    } else if source == PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG {
        base.wrapping_add(recvsig_offset as usize)
            .cast::<*mut c_void>()
    } else {
        return core::ptr::null_mut();
    };

    let pending = *slot;
    *slot = core::ptr::null_mut();
    pending
}

#[no_mangle]
pub unsafe extern "C" fn process_ptrace_traceme_body_result(
    thread: *mut c_void,
    proc: *mut c_void,
    parent: *mut c_void,
    pid1: *mut c_void,
    offsets: *const ProcessPtraceTracemeOffsets,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    alloc_debugreg_fn: Option<ProcessAllocDebugregFn>,
    clear_single_step_fn: Option<ProcessThreadActionFn>,
    hold_thread_fn: Option<ProcessThreadActionFn>,
    log_fn: Option<ProcessPtraceTracemeLogFn>,
) -> CInt {
    if thread.is_null() || proc.is_null() || parent.is_null() || pid1.is_null() || offsets.is_null()
    {
        return -EFAULT;
    }

    let offsets = unsafe { &*offsets };
    let thread_base = thread.cast::<u8>();
    let proc_base = proc.cast::<u8>();
    let parent_base = parent.cast::<u8>();
    let pid = unsafe {
        *(proc_base
            .wrapping_add(offsets.proc_pid_offset as usize)
            .cast::<CInt>())
    };
    if let Some(log) = log_fn {
        unsafe { log(PROCESS_PTRACE_TRACEME_LOG_ENTER, pid, parent as CULong, 0) };
    }

    let ptrace_slot = thread_base
        .wrapping_add(offsets.thread_ptrace_offset as usize)
        .cast::<CInt>();
    if (unsafe { *ptrace_slot } & PT_TRACED) != 0 {
        return -EPERM;
    }
    if parent == pid1 {
        return -EPERM;
    }

    let parent_pid = unsafe {
        *(parent_base
            .wrapping_add(offsets.proc_pid_offset as usize)
            .cast::<CInt>())
    };
    if let Some(log) = log_fn {
        unsafe { log(PROCESS_PTRACE_TRACEME_LOG_PARENT, parent_pid, 0, 0) };
    }

    let Some(lock) = lock_fn else {
        return -EFAULT;
    };
    let Some(unlock) = unlock_fn else {
        return -EFAULT;
    };
    if lock_node.is_null() {
        return -EFAULT;
    }

    let main_thread = unsafe {
        *(proc_base
            .wrapping_add(offsets.proc_main_thread_offset as usize)
            .cast::<*mut c_void>())
    };
    if thread == main_thread {
        let children_lock =
            (parent as CULong).wrapping_add(offsets.proc_children_lock_offset as CULong);
        let ptraced_sibling = proc_base
            .wrapping_add(offsets.proc_ptraced_siblings_list_offset as usize)
            .cast::<AbiListHead>();
        let ptraced_children = parent_base
            .wrapping_add(offsets.proc_ptraced_children_list_offset as usize)
            .cast::<AbiListHead>();
        unsafe { lock(children_lock, lock_node) };
        unsafe { process_list_add_tail_result(ptraced_sibling, ptraced_children) };
        unsafe { unlock(children_lock, lock_node) };
    }

    let report_proc = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_report_proc_offset as usize)
            .cast::<*mut c_void>())
    };
    if report_proc.is_null() {
        let threads_lock = (parent as CULong).wrapping_add(offsets.proc_threads_lock_offset);
        let report_sibling = thread_base
            .wrapping_add(offsets.thread_report_siblings_list_offset as usize)
            .cast::<AbiListHead>();
        let report_threads = parent_base
            .wrapping_add(offsets.proc_report_threads_list_offset as usize)
            .cast::<AbiListHead>();
        unsafe { lock(threads_lock, lock_node) };
        unsafe {
            process_thread_report_attach_result(
                thread,
                0,
                0,
                0,
                offsets.thread_report_proc_offset,
                parent,
                report_sibling,
                report_threads,
            );
        }
        unsafe { unlock(threads_lock, lock_node) };
    }

    unsafe { *ptrace_slot = PT_TRACED | PT_TRACE_EXEC };

    let debugreg = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_ptrace_debugreg_offset as usize)
            .cast::<*mut c_void>())
    };
    let mut error = 0;
    if debugreg.is_null() {
        let Some(alloc_debugreg) = alloc_debugreg_fn else {
            return -EFAULT;
        };
        error = unsafe { alloc_debugreg(thread) };
    }

    let Some(clear_single_step) = clear_single_step_fn else {
        return -EFAULT;
    };
    let Some(hold_thread) = hold_thread_fn else {
        return -EFAULT;
    };
    unsafe { clear_single_step(thread) };
    unsafe { hold_thread(thread) };

    if let Some(log) = log_fn {
        unsafe { log(PROCESS_PTRACE_TRACEME_LOG_RETURN, pid, 0, error) };
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn process_ptrace_attach_thread_body_result(
    thread: *mut c_void,
    proc: *mut c_void,
    offsets: *const ProcessPtraceAttachOffsets,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    alloc_debugreg_fn: Option<ProcessAllocDebugregFn>,
    clear_single_step_fn: Option<ProcessThreadActionFn>,
    hold_thread_fn: Option<ProcessThreadActionFn>,
    log_fn: Option<ProcessPtraceTracemeLogFn>,
) -> CInt {
    if thread.is_null() || proc.is_null() || offsets.is_null() || lock_node.is_null() {
        return -EFAULT;
    }
    let Some(lock) = lock_fn else {
        return -EFAULT;
    };
    let Some(unlock) = unlock_fn else {
        return -EFAULT;
    };
    let offsets = unsafe { &*offsets };
    let thread_base = thread.cast::<u8>();
    let proc_base = proc.cast::<u8>();

    let old_report_proc = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_report_proc_offset as usize)
            .cast::<*mut c_void>())
    };
    let report_sibling = thread_base
        .wrapping_add(offsets.thread_report_siblings_list_offset as usize)
        .cast::<AbiListHead>();
    if !old_report_proc.is_null() {
        let old_threads_lock =
            (old_report_proc as CULong).wrapping_add(offsets.proc_threads_lock_offset);
        unsafe { lock(old_threads_lock, lock_node) };
        unsafe { process_list_detach_result(report_sibling) };
        unsafe { unlock(old_threads_lock, lock_node) };
    }

    let proc_threads_lock = (proc as CULong).wrapping_add(offsets.proc_threads_lock_offset);
    let proc_report_threads = proc_base
        .wrapping_add(offsets.proc_report_threads_list_offset as usize)
        .cast::<AbiListHead>();
    unsafe { lock(proc_threads_lock, lock_node) };
    unsafe {
        process_thread_report_attach_result(
            thread,
            0,
            0,
            0,
            offsets.thread_report_proc_offset,
            proc,
            report_sibling,
            proc_report_threads,
        );
    }
    unsafe { unlock(proc_threads_lock, lock_node) };

    let child = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_proc_offset as usize)
            .cast::<*mut c_void>())
    };
    if child.is_null() {
        return -EFAULT;
    }
    let child_base = child.cast::<u8>();
    let main_thread = unsafe {
        *(child_base
            .wrapping_add(offsets.proc_main_thread_offset as usize)
            .cast::<*mut c_void>())
    };
    if thread == main_thread {
        let parent = unsafe {
            *(child_base
                .wrapping_add(offsets.proc_parent_offset as usize)
                .cast::<*mut c_void>())
        };
        if parent.is_null() {
            return -EFAULT;
        }
        let parent_base = parent.cast::<u8>();
        let parent_pid = unsafe {
            *(parent_base
                .wrapping_add(offsets.proc_pid_offset as usize)
                .cast::<CInt>())
        };
        if let Some(log) = log_fn {
            unsafe { log(PROCESS_PTRACE_TRACEME_LOG_PARENT, parent_pid, 0, 0) };
        }
        let parent_children_lock =
            (parent as CULong).wrapping_add(offsets.proc_children_lock_offset);
        let child_sibling = child_base
            .wrapping_add(offsets.proc_siblings_list_offset as usize)
            .cast::<AbiListHead>();
        let child_ptraced_sibling = child_base
            .wrapping_add(offsets.proc_ptraced_siblings_list_offset as usize)
            .cast::<AbiListHead>();
        let parent_ptraced_children = parent_base
            .wrapping_add(offsets.proc_ptraced_children_list_offset as usize)
            .cast::<AbiListHead>();
        unsafe { lock(parent_children_lock, lock_node) };
        unsafe { process_list_detach_result(child_sibling) };
        unsafe { process_list_add_tail_result(child_ptraced_sibling, parent_ptraced_children) };
        unsafe { unlock(parent_children_lock, lock_node) };

        let proc_children_lock = (proc as CULong).wrapping_add(offsets.proc_children_lock_offset);
        let proc_children = proc_base
            .wrapping_add(offsets.proc_children_list_offset as usize)
            .cast::<AbiListHead>();
        unsafe { lock(proc_children_lock, lock_node) };
        unsafe {
            process_ptrace_main_attach_reparent_result(
                child,
                offsets.proc_parent_offset,
                proc,
                child_sibling,
                proc_children,
            );
        }
        unsafe { unlock(proc_children_lock, lock_node) };
    }

    let debugreg = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_ptrace_debugreg_offset as usize)
            .cast::<*mut c_void>())
    };
    let mut error = 0;
    if debugreg.is_null() {
        let Some(alloc_debugreg) = alloc_debugreg_fn else {
            return -EFAULT;
        };
        error = unsafe { alloc_debugreg(thread) };
        if error < 0 {
            return error;
        }
    }

    let Some(hold_thread) = hold_thread_fn else {
        return -EFAULT;
    };
    let Some(clear_single_step) = clear_single_step_fn else {
        return -EFAULT;
    };
    unsafe { hold_thread(thread) };
    unsafe { clear_single_step(thread) };
    error
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_signal_flags_reap_result(
    thread: *mut c_void,
    signal_flags_offset: CULong,
    options: CInt,
    clear_mask: CInt,
) -> CInt {
    if thread.is_null() {
        return 0;
    }

    let signal_flags = thread
        .cast::<u8>()
        .wrapping_add(signal_flags_offset as usize)
        .cast::<CInt>();
    if (options & WNOWAIT) == 0 {
        *signal_flags &= !clear_mask;
    }
    *signal_flags
}

#[no_mangle]
pub unsafe extern "C" fn process_wait_exit_status_reap_result(
    object: *mut c_void,
    exit_status_offset: CULong,
    options: CInt,
) -> CInt {
    if object.is_null() {
        return 0;
    }

    let exit_status = object
        .cast::<u8>()
        .wrapping_add(exit_status_offset as usize)
        .cast::<CInt>();
    if (options & WNOWAIT) == 0 {
        *exit_status = 0;
    }
    *exit_status
}

#[no_mangle]
pub extern "C" fn process_optional_ptr_should_free_result(ptr_addr: CULong) -> CInt {
    (ptr_addr != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_hold_thread_warn_exited_result(status: CInt) -> CInt {
    (status == PS_EXITED) as CInt
}

#[no_mangle]
pub extern "C" fn process_sigcommon_release_should_destroy_result(dec_and_test: CInt) -> CInt {
    (dec_and_test != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_destroy_thread_tid_action_result(
    has_tids: CInt,
    is_main_thread: CInt,
    uti_state: CInt,
) -> CInt {
    if has_tids == 0 {
        PROCESS_TID_ACTION_NONE
    } else if uti_state == UTI_STATE_EPILOGUE {
        PROCESS_TID_ACTION_REPLACE
    } else if is_main_thread == 0 {
        PROCESS_TID_ACTION_RELEASE
    } else {
        PROCESS_TID_ACTION_NONE
    }
}

#[no_mangle]
pub extern "C" fn process_thread_should_free_pages_result(is_main_thread: CInt) -> CInt {
    (is_main_thread == 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_release_vm_should_run_free_cb_result(free_cb_addr: CULong) -> CInt {
    (free_cb_addr != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_release_mckfd_should_close_result(close_cb_addr: CULong) -> CInt {
    (close_cb_addr != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_push_head_result(
    headp: *mut *mut c_void,
    entry: *mut c_void,
) -> CInt {
    if headp.is_null() || entry.is_null() {
        return 0;
    }

    let next_slot = entry.cast::<*mut c_void>();
    *next_slot = *headp;
    *headp = entry;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_pop_head_result(headp: *mut *mut c_void) -> *mut c_void {
    if headp.is_null() {
        return core::ptr::null_mut();
    }

    let current = *headp;
    if current.is_null() {
        return core::ptr::null_mut();
    }

    let next_slot = current.cast::<*mut c_void>();
    *headp = *next_slot;
    *next_slot = core::ptr::null_mut();
    current
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_close_all_result(
    head: *mut c_void,
    next_offset: CULong,
    close_offset: CULong,
) -> CInt {
    let mut current = head;
    let mut closed = 0;

    while !current.is_null() {
        let base = current.cast::<u8>();
        let close_slot = base.wrapping_add(close_offset as usize);
        let close_cb = *(close_slot.cast::<Option<ProcessMckfdCloseFn>>());
        if let Some(close_cb) = close_cb {
            let _ = close_cb(current, core::ptr::null_mut());
            closed += 1;
        }

        current = *(base
            .wrapping_add(next_offset as usize)
            .cast::<*mut c_void>());
    }

    closed
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_drain_free_result(
    headp: *mut *mut c_void,
    next_offset: CULong,
    free_fn: Option<ProcessMckfdFreeFn>,
) -> CInt {
    if headp.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut freed = 0;
    let mut current = *headp;
    while !current.is_null() {
        let next_slot = current
            .cast::<u8>()
            .wrapping_add(next_offset as usize)
            .cast::<*mut c_void>();
        let next = *next_slot;
        *headp = next;
        *next_slot = core::ptr::null_mut();
        freed += process_mckfd_free_result(current, Some(free_fn));
        current = next;
    }

    freed
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_free_result(
    fdp: *mut c_void,
    free_fn: Option<ProcessMckfdFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return 0;
    };

    free(fdp);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_memory_range_free_result(
    vm: *mut c_void,
    range: *mut c_void,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(vm, range)
}

#[no_mangle]
pub unsafe extern "C" fn process_memory_range_log_result(
    vm: *mut c_void,
    range: *mut c_void,
    error: CInt,
    log_fn: Option<ProcessMemoryRangeLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(vm, range, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_memory_range_free_all_result(
    vm: *mut c_void,
    root: *mut RbRoot,
    node_offset: CULong,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessMemoryRangeLogFn>,
) -> CInt {
    if vm.is_null() || root.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut visited = 0;
    let mut node = rb_first(root);
    while !node.is_null() {
        let next = rb_next(node);
        let range = node
            .cast::<u8>()
            .wrapping_sub(node_offset as usize)
            .cast::<c_void>();
        let error = process_memory_range_free_result(vm, range, Some(free_fn));
        if error != 0 {
            let _ = process_memory_range_log_result(vm, range, error, log_fn);
        }
        visited += 1;
        node = next;
    }

    visited
}

#[no_mangle]
pub unsafe extern "C" fn process_flush_memory_body_result(
    vm: *mut ProcessVm,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessMemoryRangeLogFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };

    let lock_addr = (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong;
    let rc = process_noirq_lock_result(lock_addr, Some(lock_fn));
    if rc != 0 {
        return rc;
    }
    (*vm).exiting = 1;

    let root = (&raw mut (*vm).vm_range_tree).cast::<RbRoot>();
    let mut attempted = 0;
    let mut node = rb_first(root);
    while !node.is_null() {
        let next = rb_next(node);
        let range = node.cast::<VmRange>();
        if !(*range).memobj.is_null() {
            let error = process_memory_range_free_result(
                vm.cast::<c_void>(),
                range.cast::<c_void>(),
                Some(free_fn),
            );
            attempted += 1;
            if error != 0 {
                let _ = process_memory_range_log_result(
                    vm.cast::<c_void>(),
                    range.cast::<c_void>(),
                    error,
                    log_fn,
                );
            }
        }
        node = next;
    }

    let _ = process_noirq_unlock_result(lock_addr, Some(unlock_fn));
    attempted
}

#[no_mangle]
pub unsafe extern "C" fn process_free_all_memory_ranges_body_result(
    vm: *mut ProcessVm,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessMemoryRangeLogFn>,
) -> CInt {
    if vm.is_null() {
        return 0;
    }
    let Some(lock_fn) = lock_fn else {
        return 0;
    };
    let Some(unlock_fn) = unlock_fn else {
        return 0;
    };
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let lock_addr = (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong;
    let rc = process_noirq_lock_result(lock_addr, Some(lock_fn));
    if rc != 0 {
        return rc;
    }
    let visited = process_memory_range_free_all_result(
        vm.cast::<c_void>(),
        (&raw mut (*vm).vm_range_tree).cast::<RbRoot>(),
        0,
        Some(free_fn),
        log_fn,
    );
    let _ = process_noirq_unlock_result(lock_addr, Some(unlock_fn));
    visited
}

#[inline(always)]
unsafe fn process_cpu_set_word(
    cpu_set_addr: CULong,
    cpu: CInt,
    cpu_set_bits: CInt,
) -> Option<(*mut CULong, CULong)> {
    if cpu_set_addr == 0 || cpu < 0 || cpu_set_bits <= 0 || cpu >= cpu_set_bits {
        return None;
    }

    let word_bits = (core::mem::size_of::<CULong>() * 8) as CInt;
    let word = (cpu / word_bits) as usize;
    let bit = (cpu % word_bits) as CULong;
    Some((
        (cpu_set_addr as *mut CULong).add(word),
        1u64.wrapping_shl(bit as u32),
    ))
}

#[no_mangle]
pub unsafe extern "C" fn process_cpu_set_update_body_result(
    cpu_set_addr: CULong,
    lock_addr: CULong,
    clear_cpu: CInt,
    set_cpu: CInt,
    cpu_set_bits: CInt,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    if cpu_set_addr == 0 || lock_addr == 0 {
        return -EINVAL;
    }
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };

    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mut changed = 0;
    if let Some((word, mask)) = process_cpu_set_word(cpu_set_addr, clear_cpu, cpu_set_bits) {
        *word &= !mask;
        changed += 1;
    }
    if let Some((word, mask)) = process_cpu_set_word(cpu_set_addr, set_cpu, cpu_set_bits) {
        *word |= mask;
        changed += 1;
    }
    let _ = process_spin_unlock_result(lock_addr, irqstate, Some(unlock_fn));
    changed
}

#[no_mangle]
pub unsafe extern "C" fn process_cpu_set_public_result(
    cpu: CInt,
    cpu_set_addr: CULong,
    lock_addr: CULong,
    cpu_set_bits: CInt,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    process_cpu_set_update_body_result(
        cpu_set_addr,
        lock_addr,
        -1,
        cpu,
        cpu_set_bits,
        lock_fn,
        unlock_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_cpu_clear_public_result(
    cpu: CInt,
    cpu_set_addr: CULong,
    lock_addr: CULong,
    cpu_set_bits: CInt,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    process_cpu_set_update_body_result(
        cpu_set_addr,
        lock_addr,
        cpu,
        -1,
        cpu_set_bits,
        lock_fn,
        unlock_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_cpu_clear_and_set_public_result(
    clear_cpu: CInt,
    set_cpu: CInt,
    cpu_set_addr: CULong,
    lock_addr: CULong,
    cpu_set_bits: CInt,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    process_cpu_set_update_body_result(
        cpu_set_addr,
        lock_addr,
        clear_cpu,
        set_cpu,
        cpu_set_bits,
        lock_fn,
        unlock_fn,
    )
}

unsafe extern "C" fn process_cpu_set_spin_lock_direct(lock_addr: CULong) -> CULong {
    __ihk_mc_spinlock_lock(lock_addr as *mut IhkSpinlock)
}

unsafe extern "C" fn process_cpu_set_spin_unlock_direct(lock_addr: CULong, flags: CULong) {
    __ihk_mc_spinlock_unlock(lock_addr as *mut IhkSpinlock, flags);
}

#[no_mangle]
pub unsafe extern "C" fn cpu_set(cpu: CInt, cpu_set: *mut CpuSet, lock: *mut IhkSpinlock) {
    let _ = process_cpu_set_public_result(
        cpu,
        cpu_set as CULong,
        lock as CULong,
        CPU_SET_MAX_CPUS as CInt,
        Some(process_cpu_set_spin_lock_direct),
        Some(process_cpu_set_spin_unlock_direct),
    );
}

#[no_mangle]
pub unsafe extern "C" fn cpu_clear(cpu: CInt, cpu_set: *mut CpuSet, lock: *mut IhkSpinlock) {
    let _ = process_cpu_clear_public_result(
        cpu,
        cpu_set as CULong,
        lock as CULong,
        CPU_SET_MAX_CPUS as CInt,
        Some(process_cpu_set_spin_lock_direct),
        Some(process_cpu_set_spin_unlock_direct),
    );
}

#[no_mangle]
pub unsafe extern "C" fn cpu_clear_and_set(
    clear_cpu: CInt,
    set_cpu: CInt,
    cpu_set: *mut CpuSet,
    lock: *mut IhkSpinlock,
) {
    let _ = process_cpu_clear_and_set_public_result(
        clear_cpu,
        set_cpu,
        cpu_set as CULong,
        lock as CULong,
        CPU_SET_MAX_CPUS as CInt,
        Some(process_cpu_set_spin_lock_direct),
        Some(process_cpu_set_spin_unlock_direct),
    );
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_inc_result(
    object: *mut c_void,
    ref_offset: CULong,
    inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    if let Some(inc) = inc_fn {
        inc(object, ref_offset);
        return 0;
    }

    process_ref_inc_direct_result(object, ref_offset)
}

#[no_mangle]
pub unsafe extern "C" fn process_hold_thread_warn_result(
    thread: *mut c_void,
    warn_fn: Option<ProcessHoldThreadWarnFn>,
) -> CInt {
    let Some(warn) = warn_fn else {
        return 0;
    };

    warn(thread);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_hold_body_result(
    object: *mut c_void,
    ref_offset: CULong,
    inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    if object.is_null() {
        return -EINVAL;
    }
    let rc = process_ref_inc_result(object, ref_offset, inc_fn);
    if rc != 0 {
        return rc;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_hold_thread_body_result(
    thread: *mut c_void,
    status_offset: CULong,
    refcount_offset: CULong,
    inc_fn: Option<ProcessRefIncFn>,
    warn_fn: Option<ProcessHoldThreadWarnFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }

    let status = *(thread
        .cast::<u8>()
        .wrapping_add(status_offset as usize)
        .cast::<CInt>());
    if process_hold_thread_warn_exited_result(status) != 0 {
        let _ = process_hold_thread_warn_result(thread, warn_fn);
    }

    process_ref_hold_body_result(thread, refcount_offset, inc_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_current_resource_set_result(
    current_resource_set_fn: Option<ProcessCurrentResourceSetFn>,
) -> *mut c_void {
    let Some(current_resource_set) = current_resource_set_fn else {
        return null_mut();
    };

    current_resource_set()
}

#[no_mangle]
pub unsafe extern "C" fn process_resource_process_action_result(
    resource_set: *mut c_void,
    process: *mut c_void,
    action_fn: Option<ProcessResourceProcessActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(resource_set, process);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_process_action_result(
    process: *mut c_void,
    action_fn: Option<ProcessProcessActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(process);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_resource_set_action_result(
    resource_set: *mut c_void,
    action_fn: Option<ProcessResourceSetActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(resource_set);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_action_result(
    thread: *mut c_void,
    action_fn: Option<ProcessThreadActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(thread);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_profile_result(
    thread: *mut c_void,
    process: *mut c_void,
    profile_fn: Option<ProcessThreadProfileFn>,
) -> CInt {
    let Some(profile) = profile_fn else {
        return 0;
    };

    profile(thread, process);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_action_result(
    vm: *mut c_void,
    action_fn: Option<ProcessVmActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(vm);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_policy_free_result(
    policy: *mut c_void,
    policy_free_fn: Option<ProcessPolicyFreeFn>,
) -> CInt {
    let Some(policy_free) = policy_free_fn else {
        return -EINVAL;
    };

    policy_free(policy);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_free_cb_result(
    vm: *mut c_void,
    opt: *mut c_void,
    free_cb: Option<ProcessVmFreeCallback>,
) -> CInt {
    let Some(free_cb) = free_cb else {
        return 0;
    };

    free_cb(vm, opt);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_lock_result(
    lock_addr: CULong,
    lock_fn: Option<ProcessSpinLockFn>,
) -> CULong {
    let Some(lock) = lock_fn else {
        return 0;
    };

    lock(lock_addr)
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_unlock_result(
    lock_addr: CULong,
    irqstate: CULong,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };

    unlock(lock_addr, irqstate);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_release_process_body_result(
    proc: *mut c_void,
    refcount_offset: CULong,
    tids_offset: CULong,
    main_thread_offset: CULong,
    mckfd_offset: CULong,
    mckfd_lock_offset: CULong,
    mckfd_next_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    current_resource_set_fn: Option<ProcessCurrentResourceSetFn>,
    hash_detach_fn: Option<ProcessResourceProcessActionFn>,
    sibling_detach_fn: Option<ProcessProcessActionFn>,
    profile_fn: Option<ProcessProcessActionFn>,
    free_thread_pages_fn: Option<ProcessThreadActionFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    mckfd_free_fn: Option<ProcessMckfdFreeFn>,
    free_fn: Option<ProcessFreeFn>,
    final_cleanup_fn: Option<ProcessResourceSetActionFn>,
) -> CInt {
    if proc.is_null() {
        return -EINVAL;
    }
    let Some(current_resource_set_fn) = current_resource_set_fn else {
        return -EINVAL;
    };
    let Some(hash_detach_fn) = hash_detach_fn else {
        return -EINVAL;
    };
    let Some(sibling_detach_fn) = sibling_detach_fn else {
        return -EINVAL;
    };
    let Some(free_thread_pages_fn) = free_thread_pages_fn else {
        return -EINVAL;
    };
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(mckfd_free_fn) = mckfd_free_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    let Some(final_cleanup_fn) = final_cleanup_fn else {
        return -EINVAL;
    };

    if process_ref_release_should_destroy_result(process_ref_dec_and_test_result(
        proc,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let resource_set = process_current_resource_set_result(Some(current_resource_set_fn));
    let _ = process_resource_process_action_result(resource_set, proc, Some(hash_detach_fn));
    let _ = process_process_action_result(proc, Some(sibling_detach_fn));

    let tids = field_ptr(proc, tids_offset);
    if !tids.is_null() {
        let _ = process_free_callback_result(tids, Some(free_fn));
    }

    if let Some(profile_fn) = profile_fn {
        let _ = process_process_action_result(proc, Some(profile_fn));
    }

    let main_thread = field_ptr(proc, main_thread_offset);
    if !main_thread.is_null() {
        let _ = process_thread_action_result(main_thread, Some(free_thread_pages_fn));
    }

    let lock_addr = (proc as CULong).wrapping_add(mckfd_lock_offset);
    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mckfd_headp = proc
        .cast::<u8>()
        .wrapping_add(mckfd_offset as usize)
        .cast::<*mut c_void>();
    process_mckfd_drain_free_result(mckfd_headp, mckfd_next_offset, Some(mckfd_free_fn));
    let _ = process_spin_unlock_result(lock_addr, irqstate, Some(unlock_fn));

    let _ = process_free_callback_result(proc, Some(free_fn));
    let _ = process_resource_set_action_result(resource_set, Some(final_cleanup_fn));
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_policy_drain_free_result(
    root: *mut RbRoot,
    node_offset: CULong,
    free_fn: Option<ProcessPolicyFreeFn>,
) -> CInt {
    if root.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut freed = 0;
    loop {
        let node = rb_first(root);
        if node.is_null() {
            break;
        }
        let policy = node
            .cast::<u8>()
            .wrapping_sub(node_offset as usize)
            .cast::<c_void>();
        rb_erase(node, root);
        let _ = process_policy_free_result(policy, Some(free_fn));
        freed += 1;
    }

    freed
}

#[no_mangle]
pub unsafe extern "C" fn process_detach_address_space_pid_result(
    address_space: *mut c_void,
    pid: CInt,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
) -> CInt {
    let Some(detach) = detach_fn else {
        return -EINVAL;
    };

    detach(address_space, pid);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_release_process_action_result(
    process: *mut c_void,
    release_fn: Option<ProcessReleaseProcessFn>,
) -> CInt {
    let Some(release) = release_fn else {
        return -EINVAL;
    };

    release(process);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_release_vm_detach_process_result(
    vm: *mut c_void,
    address_space_offset: CULong,
    proc_offset: CULong,
    pid_offset: CULong,
    proc_vm_offset: CULong,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
    release_fn: Option<ProcessReleaseProcessFn>,
) -> CInt {
    if vm.is_null() {
        return 0;
    }
    let (Some(detach_fn), Some(release_fn)) = (detach_fn, release_fn) else {
        return 0;
    };

    let vm_base = vm.cast::<u8>();
    let address_space = *(vm_base
        .wrapping_add(address_space_offset as usize)
        .cast::<*mut c_void>());
    let proc = *(vm_base
        .wrapping_add(proc_offset as usize)
        .cast::<*mut c_void>());
    if proc.is_null() {
        return 0;
    }

    let proc_base = proc.cast::<u8>();
    let pid = *(proc_base.wrapping_add(pid_offset as usize).cast::<CInt>());
    let _ = process_detach_address_space_pid_result(address_space, pid, Some(detach_fn));
    *(proc_base
        .wrapping_add(proc_vm_offset as usize)
        .cast::<*mut c_void>()) = core::ptr::null_mut();
    let _ = process_release_process_action_result(proc, Some(release_fn));
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_release_fp_regs_result(
    thread: *mut c_void,
    release_fp_fn: Option<ProcessReleaseFpRegsFn>,
) -> CInt {
    let Some(release_fp) = release_fp_fn else {
        return 0;
    };

    release_fp(thread);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_optional_cleanup_result(
    thread: *mut c_void,
    debugreg_offset: CULong,
    recvsig_offset: CULong,
    sendsig_offset: CULong,
    fp_regs_offset: CULong,
    coredump_regs_offset: CULong,
    free_fn: Option<ProcessOptionalFreeFn>,
    release_fp_fn: Option<ProcessReleaseFpRegsFn>,
) -> CInt {
    if thread.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let base = thread.cast::<u8>();
    let mut actions = 0;
    for offset in [debugreg_offset, recvsig_offset, sendsig_offset] {
        let ptr = *(base.wrapping_add(offset as usize).cast::<*mut c_void>());
        if !ptr.is_null() {
            let _ = process_free_callback_result(ptr, Some(free_fn));
            actions += 1;
        }
    }

    let fp_regs = *(base
        .wrapping_add(fp_regs_offset as usize)
        .cast::<*mut c_void>());
    if !fp_regs.is_null() {
        actions += process_release_fp_regs_result(thread, release_fp_fn);
    }

    let coredump_regs = *(base
        .wrapping_add(coredump_regs_offset as usize)
        .cast::<*mut c_void>());
    let _ = process_free_callback_result(coredump_regs, Some(free_fn));
    actions + 1
}

#[inline]
unsafe fn field_ptr(base: *mut c_void, offset: CULong) -> *mut c_void {
    *(base
        .cast::<u8>()
        .wrapping_add(offset as usize)
        .cast::<*mut c_void>())
}

#[no_mangle]
pub unsafe extern "C" fn process_release_sigcommon_body_result(
    sigcommon: *mut c_void,
    dec_and_test: CInt,
    sigpending_empty: CInt,
    sigpending_offset: CULong,
    pending_list_offset: CULong,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    if sigcommon.is_null() {
        return -EINVAL;
    }
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    if process_sigcommon_release_should_destroy_result(dec_and_test) == 0 {
        return 0;
    }

    if process_sigpending_cleanup_needed_result(sigpending_empty) != 0 {
        let head = sigcommon
            .cast::<u8>()
            .wrapping_add(sigpending_offset as usize)
            .cast::<AbiListHead>();
        loop {
            let pending = process_sigpending_pop_front_result(head, pending_list_offset);
            if pending.is_null() {
                break;
            }
            let _ = process_free_callback_result(pending, Some(free_fn));
        }
    }

    let _ = process_free_callback_result(sigcommon, Some(free_fn));
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_release_sigcommon_public_body_result(
    sigcommon: *mut c_void,
    use_offset: CULong,
    sigpending_offset: CULong,
    pending_list_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    if sigcommon.is_null() {
        return -EINVAL;
    }
    let head = sigcommon
        .cast::<u8>()
        .wrapping_add(sigpending_offset as usize)
        .cast::<AbiListHead>();
    let sigpending_empty = ((*head).next == head) as CInt;
    process_release_sigcommon_body_result(
        sigcommon,
        process_ref_dec_and_test_result(sigcommon, use_offset, dec_fn),
        sigpending_empty,
        sigpending_offset,
        pending_list_offset,
        free_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_release_tid_body_result(
    tids: *mut c_void,
    nr_tids: CInt,
    tid_stride: CULong,
    tid_thread_offset: CULong,
    thread: *mut c_void,
    thread_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    if tids.is_null() || thread.is_null() {
        return 0;
    }

    let index = process_tid_index_for_thread_result(
        tids,
        nr_tids,
        tid_stride,
        tid_thread_offset,
        thread as CULong,
    );
    if process_tid_index_found_result(index) == 0 {
        return 0;
    }
    if process_tid_release_slot_result(tids, index, tid_stride, tid_thread_offset) == 0 {
        return 0;
    }

    let _ = process_tid_log_result(thread_tid, thread, 0, log_fn);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_tid_log_result(
    old_tid: CInt,
    thread: *mut c_void,
    new_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(old_tid, thread, new_tid);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_replace_tid_body_result(
    tids: *mut c_void,
    nr_tids: CInt,
    tid_stride: CULong,
    tid_offset: CULong,
    tid_thread_offset: CULong,
    thread: *mut c_void,
    old_tid: CInt,
    new_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    if tids.is_null() || thread.is_null() {
        return 0;
    }

    let index = process_tid_index_for_thread_result(
        tids,
        nr_tids,
        tid_stride,
        tid_thread_offset,
        thread as CULong,
    );
    if process_tid_index_found_result(index) == 0 {
        return 0;
    }
    if process_tid_replace_slot_result(
        tids,
        index,
        tid_stride,
        tid_offset,
        tid_thread_offset,
        new_tid,
    ) == 0
    {
        return 0;
    }

    let _ = process_tid_log_result(old_tid, thread, new_tid, log_fn);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_chain_process_body_result(
    siblings_entry: *mut AbiListHead,
    children_head: *mut AbiListHead,
    children_lock_addr: CULong,
    hash_entry: *mut AbiListHead,
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
) -> CInt {
    if siblings_entry.is_null()
        || children_head.is_null()
        || hash_entry.is_null()
        || hash_head.is_null()
        || lock_node.is_null()
    {
        return -EINVAL;
    }
    let (Some(lock_fn), Some(unlock_fn)) = (lock_fn, unlock_fn) else {
        return -EINVAL;
    };

    lock_fn(children_lock_addr, lock_node);
    process_list_add_tail_result(siblings_entry, children_head);
    unlock_fn(children_lock_addr, lock_node);

    lock_fn(hash_lock_addr, lock_node);
    process_list_add_tail_result(hash_entry, hash_head);
    unlock_fn(hash_lock_addr, lock_node);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_chain_thread_body_result(
    siblings_entry: *mut AbiListHead,
    threads_head: *mut AbiListHead,
    threads_lock_addr: CULong,
    hash_entry: *mut AbiListHead,
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    vm: *mut c_void,
    vm_refcount_offset: CULong,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    ref_inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    let rc = process_chain_process_body_result(
        siblings_entry,
        threads_head,
        threads_lock_addr,
        hash_entry,
        hash_head,
        hash_lock_addr,
        lock_node,
        lock_fn,
        unlock_fn,
    );
    if rc < 0 {
        return rc;
    }
    process_ref_inc_result(vm, vm_refcount_offset, ref_inc_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_body_result(
    thread: *mut c_void,
    thread_proc_offset: CULong,
    thread_vm_offset: CULong,
    thread_cpu_id_offset: CULong,
    thread_siblings_list_offset: CULong,
    thread_uti_state_offset: CULong,
    thread_uti_refill_tid_offset: CULong,
    thread_sigpending_offset: CULong,
    thread_sigcommon_offset: CULong,
    proc_threads_lock_offset: CULong,
    proc_tids_offset: CULong,
    proc_main_thread_offset: CULong,
    vm_address_space_offset: CULong,
    address_space_cpu_set_offset: CULong,
    address_space_cpu_set_lock_offset: CULong,
    pending_list_offset: CULong,
    debugreg_offset: CULong,
    recvsig_offset: CULong,
    sendsig_offset: CULong,
    fp_regs_offset: CULong,
    coredump_regs_offset: CULong,
    cpu_set_bits: CInt,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    hash_detach_fn: Option<ProcessThreadActionFn>,
    time_account_fn: Option<ProcessThreadActionFn>,
    release_tid_fn: Option<ProcessThreadProcActionFn>,
    replace_tid_fn: Option<ProcessThreadTidActionFn>,
    cpu_lock_fn: Option<ProcessSpinLockFn>,
    cpu_unlock_fn: Option<ProcessSpinUnlockFn>,
    free_fn: Option<ProcessOptionalFreeFn>,
    release_fp_fn: Option<ProcessReleaseFpRegsFn>,
    release_sigcommon_fn: Option<ProcessThreadActionFn>,
    free_thread_pages_fn: Option<ProcessThreadActionFn>,
) -> CInt {
    if thread.is_null() || lock_node.is_null() {
        return -EINVAL;
    }
    let (
        Some(lock_fn),
        Some(unlock_fn),
        Some(hash_detach_fn),
        Some(time_account_fn),
        Some(release_tid_fn),
        Some(replace_tid_fn),
        Some(cpu_lock_fn),
        Some(cpu_unlock_fn),
        Some(free_fn),
        Some(release_sigcommon_fn),
        Some(free_thread_pages_fn),
    ) = (
        lock_fn,
        unlock_fn,
        hash_detach_fn,
        time_account_fn,
        release_tid_fn,
        replace_tid_fn,
        cpu_lock_fn,
        cpu_unlock_fn,
        free_fn,
        release_sigcommon_fn,
        free_thread_pages_fn,
    )
    else {
        return -EINVAL;
    };

    hash_detach_fn(thread);
    time_account_fn(thread);

    let proc = field_ptr(thread, thread_proc_offset);
    if proc.is_null() {
        return -EINVAL;
    }
    let thread_base = thread.cast::<u8>();
    let threads_lock_addr = (proc as CULong).wrapping_add(proc_threads_lock_offset);

    lock_fn(threads_lock_addr, lock_node);
    let siblings = thread_base
        .wrapping_add(thread_siblings_list_offset as usize)
        .cast::<AbiListHead>();
    process_list_detach_result(siblings);

    let tids = field_ptr(proc, proc_tids_offset);
    let main_thread = field_ptr(proc, proc_main_thread_offset);
    let uti_state = *(thread_base
        .wrapping_add(thread_uti_state_offset as usize)
        .cast::<CInt>());
    match process_destroy_thread_tid_action_result(
        (!tids.is_null()) as CInt,
        (thread == main_thread) as CInt,
        uti_state,
    ) {
        PROCESS_TID_ACTION_REPLACE => {
            let new_tid = *(thread_base
                .wrapping_add(thread_uti_refill_tid_offset as usize)
                .cast::<CInt>());
            replace_tid_fn(proc, thread, new_tid);
        }
        PROCESS_TID_ACTION_RELEASE => release_tid_fn(proc, thread),
        _ => {}
    }

    let vm = field_ptr(thread, thread_vm_offset);
    if !vm.is_null() {
        let address_space = field_ptr(vm, vm_address_space_offset);
        if !address_space.is_null() {
            let cpu_id = *(thread_base
                .wrapping_add(thread_cpu_id_offset as usize)
                .cast::<CInt>());
            let cpu_set_addr = (address_space as CULong).wrapping_add(address_space_cpu_set_offset);
            let cpu_set_lock_addr =
                (address_space as CULong).wrapping_add(address_space_cpu_set_lock_offset);
            let _ = process_cpu_set_update_body_result(
                cpu_set_addr,
                cpu_set_lock_addr,
                cpu_id,
                -1,
                cpu_set_bits,
                Some(cpu_lock_fn),
                Some(cpu_unlock_fn),
            );
        }
    }

    let sigpending = thread_base
        .wrapping_add(thread_sigpending_offset as usize)
        .cast::<AbiListHead>();
    let sigpending_empty =
        ((!(*sigpending).next.is_null()) && (*sigpending).next == sigpending) as CInt;
    if process_sigpending_cleanup_needed_result(sigpending_empty) != 0 {
        let _ =
            process_sigpending_drain_free_result(sigpending, pending_list_offset, Some(free_fn));
    }

    let _ = process_destroy_thread_optional_cleanup_result(
        thread,
        debugreg_offset,
        recvsig_offset,
        sendsig_offset,
        fp_regs_offset,
        coredump_regs_offset,
        Some(free_fn),
        release_fp_fn,
    );

    let sigcommon = field_ptr(thread, thread_sigcommon_offset);
    release_sigcommon_fn(sigcommon);

    if process_thread_should_free_pages_result((thread == main_thread) as CInt) != 0 {
        free_thread_pages_fn(thread);
    }
    unlock_fn(threads_lock_addr, lock_node);
    1
}

#[inline]
unsafe fn process_list_container(entry: *mut AbiListHead, list_offset: CULong) -> *mut c_void {
    entry
        .cast::<u8>()
        .wrapping_sub(list_offset as usize)
        .cast::<c_void>()
}

#[no_mangle]
pub unsafe extern "C" fn process_find_thread_body_result(
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    pid: CInt,
    tid: CInt,
    offsets: *const ProcessFindThreadOffsets,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    hold_fn: Option<ProcessThreadActionFn>,
) -> *mut c_void {
    if tid <= 0 {
        return null_mut();
    }
    if hash_head.is_null() || lock_node.is_null() || offsets.is_null() {
        return null_mut();
    }
    let (Some(lock_fn), Some(unlock_fn), Some(hold_fn)) = (lock_fn, unlock_fn, hold_fn) else {
        return null_mut();
    };
    let offsets = &*offsets;

    lock_fn(hash_lock_addr, lock_node);
    let mut match_pid = pid;
    loop {
        let mut entry = (*hash_head).next;
        while !entry.is_null() && entry != hash_head {
            let thread = process_list_container(entry, offsets.thread_hash_list_offset);
            let thread_base = thread.cast::<u8>();
            let thread_tid = *(thread_base
                .wrapping_add(offsets.thread_tid_offset as usize)
                .cast::<CInt>());
            if thread_tid == tid {
                let proc = field_ptr(thread, offsets.thread_proc_offset);
                let proc_pid = if proc.is_null() {
                    0
                } else {
                    *(proc
                        .cast::<u8>()
                        .wrapping_add(offsets.proc_pid_offset as usize)
                        .cast::<CInt>())
                };
                if match_pid <= 0 || proc_pid == match_pid {
                    hold_fn(thread);
                    unlock_fn(hash_lock_addr, lock_node);
                    return thread;
                }
            }
            entry = (*entry).next;
        }
        if match_pid > 0 && match_pid == tid {
            match_pid = 0;
            continue;
        }
        break;
    }

    unlock_fn(hash_lock_addr, lock_node);
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn process_find_process_body_result(
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    pid: CInt,
    offsets: *const ProcessFindProcessOffsets,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
) -> *mut c_void {
    if pid <= 0 {
        return null_mut();
    }
    if hash_head.is_null() || lock_node.is_null() || offsets.is_null() {
        return null_mut();
    }
    let (Some(lock_fn), Some(unlock_fn)) = (lock_fn, unlock_fn) else {
        return null_mut();
    };
    let offsets = &*offsets;

    lock_fn(hash_lock_addr, lock_node);
    let mut entry = (*hash_head).next;
    while !entry.is_null() && entry != hash_head {
        let process = process_list_container(entry, offsets.process_hash_list_offset);
        let proc_pid = *(process
            .cast::<u8>()
            .wrapping_add(offsets.process_pid_offset as usize)
            .cast::<CInt>());
        if proc_pid == pid {
            return process;
        }
        entry = (*entry).next;
    }

    unlock_fn(hash_lock_addr, lock_node);
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn process_unlock_found_process_result(
    process: *mut c_void,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    unlock_fn: Option<ProcessMcsRwlockFn>,
) -> CInt {
    if process.is_null() {
        return 0;
    }
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    unlock_fn(hash_lock_addr, lock_node);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_release_thread_body_result(
    thread: *mut c_void,
    refcount_offset: CULong,
    vm_offset: CULong,
    proc_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    profile_fn: Option<ProcessThreadProfileFn>,
    procfs_delete_fn: Option<ProcessThreadActionFn>,
    destroy_thread_fn: Option<ProcessThreadActionFn>,
    release_vm_fn: Option<ProcessVmActionFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let Some(procfs_delete_fn) = procfs_delete_fn else {
        return -EINVAL;
    };
    let Some(destroy_thread_fn) = destroy_thread_fn else {
        return -EINVAL;
    };
    let Some(release_vm_fn) = release_vm_fn else {
        return -EINVAL;
    };

    if process_ref_release_should_destroy_result(process_ref_dec_and_test_result(
        thread,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let vm = field_ptr(thread, vm_offset);
    let proc = field_ptr(thread, proc_offset);
    let _ = process_thread_profile_result(thread, proc, profile_fn);
    let _ = process_thread_action_result(thread, Some(procfs_delete_fn));
    let _ = process_thread_action_result(thread, Some(destroy_thread_fn));
    let _ = process_vm_action_result(vm, Some(release_vm_fn));
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_release_vm_body_result(
    vm: *mut c_void,
    refcount_offset: CULong,
    proc_offset: CULong,
    proc_mckfd_offset: CULong,
    proc_mckfd_lock_offset: CULong,
    mckfd_next_offset: CULong,
    mckfd_close_offset: CULong,
    vm_free_cb_offset: CULong,
    vm_opt_offset: CULong,
    vm_address_space_offset: CULong,
    proc_pid_offset: CULong,
    proc_vm_offset: CULong,
    vm_policy_tree_offset: CULong,
    policy_node_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    flush_fn: Option<ProcessVmActionFn>,
    free_ranges_fn: Option<ProcessVmActionFn>,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
    release_process_fn: Option<ProcessReleaseProcessFn>,
    policy_free_fn: Option<ProcessPolicyFreeFn>,
    free_vm_fn: Option<ProcessFreeFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(flush_fn) = flush_fn else {
        return -EINVAL;
    };
    let Some(free_ranges_fn) = free_ranges_fn else {
        return -EINVAL;
    };
    let Some(free_vm_fn) = free_vm_fn else {
        return -EINVAL;
    };

    if process_ref_release_should_destroy_result(process_ref_dec_and_test_result(
        vm,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let proc = field_ptr(vm, proc_offset);
    if proc.is_null() {
        return -EINVAL;
    }

    let lock_addr = (proc as CULong).wrapping_add(proc_mckfd_lock_offset);
    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mckfd_head = field_ptr(proc, proc_mckfd_offset);
    process_mckfd_close_all_result(mckfd_head, mckfd_next_offset, mckfd_close_offset);
    let _ = process_spin_unlock_result(lock_addr, irqstate, Some(unlock_fn));

    let free_cb_slot = vm
        .cast::<u8>()
        .wrapping_add(vm_free_cb_offset as usize)
        .cast::<Option<ProcessVmFreeCallback>>();
    let free_cb = *free_cb_slot;
    if process_release_vm_should_run_free_cb_result(free_cb.map_or(0, |f| f as usize as CULong))
        != 0
    {
        let opt = field_ptr(vm, vm_opt_offset);
        let _ = process_vm_free_cb_result(vm, opt, free_cb);
    }

    let _ = process_vm_action_result(vm, Some(flush_fn));
    let _ = process_vm_action_result(vm, Some(free_ranges_fn));

    process_release_vm_detach_process_result(
        vm,
        vm_address_space_offset,
        proc_offset,
        proc_pid_offset,
        proc_vm_offset,
        detach_fn,
        release_process_fn,
    );

    let policy_root = vm
        .cast::<u8>()
        .wrapping_add(vm_policy_tree_offset as usize)
        .cast::<RbRoot>();
    process_vm_policy_drain_free_result(policy_root, policy_node_offset, policy_free_fn);
    let _ = process_free_callback_result(vm, Some(free_vm_fn));
    1
}
