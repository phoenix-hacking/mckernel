use core::ffi::c_void;
use core::mem::{ManuallyDrop, MaybeUninit, size_of};
use core::ptr::{
    addr_of, addr_of_mut, copy_nonoverlapping, null_mut, read_volatile, write, write_volatile,
};

use crate::abi::{
    AbiListHead, CInt, CLong, CULong, ITimerVal, IkcScdPacket, IkcScdPacketTraditional, Iovec,
    KSigAction, MovePagesSmpReq, PROCESS_NUMA_MASK_WORDS, ProcessVm, RUsage, SigAction, SigInfo,
    SigInfoChild, SigInfoKill, SigStack, SizeT, SysInfo, SyscallRequest, SyscallResponse, TimeSpec,
    TimeVal, TodData, VmRange, VmRangeNumaPolicy, X86UserContext,
};

const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const EACCES: CInt = 13;
const EPERM: CInt = 1;
const ENOENT: CInt = 2;
const EFAULT: CInt = 14;
const EINTR: CInt = 4;
const EBUSY: CInt = 16;
const ESRCH: CInt = 3;
const EIO: CInt = 5;
const EBADF: CInt = 9;
const ECHILD: CInt = 10;
const ENODEV: CInt = 19;
const ENOSYS: CInt = 38;
const EOPNOTSUPP: CInt = 95;
const ENOTSUPP: CInt = 524;
const ERESTARTSYS: CLong = 512;

const ROBUST_LIST_HEAD_SIZE: SizeT = 24;
const SIGKILL: CInt = 9;
const SIGSTOP: CInt = 19;
const SIGTSTP: CInt = 20;
const SIGTTIN: CInt = 21;
const SIGTTOU: CInt = 22;
const NSIG: CInt = 64;
const SIG_BLOCK: CInt = 0;
const SIG_UNBLOCK: CInt = 1;
const SIG_SETMASK: CInt = 2;
const SIGKILL_MASK: CULong = 1 << 8;
const SIGSTOP_MASK: CULong = 1 << 18;
const PAGE_SIZE: CULong = 1 << 12;
const PAGE_SHIFT: CULong = 12;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);
const PF_WRITE: CULong = 1 << 1;
const PF_USER: CULong = 1 << 2;
const PF_POPULATE: CULong = 1 << 30;
const PGOFF_LIMIT: SizeT = 1usize << (63 - PAGE_SHIFT as usize);
const VR_RESERVED: CULong = 0x2;
const VR_IO_NOCACHE: CULong = 0x100;
const VR_REMOTE: CULong = 0x200;
const VR_DEMAND_PAGING: CULong = 0x1000;
const VR_PRIVATE: CULong = 0x2000;
const VR_LOCKED: CULong = 0x4000;
const VR_FILEOFF: CULong = 0x8000;
const VR_PROT_READ: CULong = 0x00010000;
const VR_PROT_WRITE: CULong = 0x00020000;
const VR_PROT_EXEC: CULong = 0x00040000;
const VR_PROT_MASK: CULong = 0x00070000;
const VR_MAXPROT_MASK: CULong = 0x00700000;
const VR_XPMEM: CULong = 0x40000000;
const PTATTR_ACTIVE: CULong = 0x01;
const PTATTR_USER: CULong = 0x04;
const PTATTR_NO_EXECUTE: CULong = 0x8000_0000_0000_0000;
const PTATTR_UNCACHABLE: CULong = 0x10000;

const MCL_CURRENT: CInt = 0x01;
const MCL_FUTURE: CInt = 0x02;

#[no_mangle]
pub extern "C" fn valid_signal(sig: CULong) -> CInt {
    (sig <= NSIG as CULong) as CInt
}

#[no_mangle]
pub extern "C" fn __sigmask(sig: CULong) -> CULong {
    1u64.wrapping_shl((sig.wrapping_sub(1) & 63) as u32) as CULong
}

#[no_mangle]
pub unsafe extern "C" fn iov_length(iov: *const Iovec, nr_segs: CULong) -> SizeT {
    let mut seg = 0;
    let mut ret: SizeT = 0;
    while seg < nr_segs {
        ret = ret.wrapping_add(read_volatile(addr_of!((*iov.add(seg as usize)).iov_len)));
        seg += 1;
    }
    ret
}

const PROT_READ: CInt = 0x01;
const PROT_WRITE: CInt = 0x02;
const PROT_EXEC: CInt = 0x04;

const SHM_RDONLY: CInt = 0o10000;
const SHM_RND: CInt = 0o20000;
const SHM_DEST: u16 = 0o1000;
const SHM_LOCKED: u16 = 0o2000;
const IPC_RMID: CInt = 0;
const IPC_SET: CInt = 1;
const IPC_STAT: CInt = 2;
const IPC_INFO: CInt = 3;
const SHM_LOCK: CInt = 11;
const SHM_UNLOCK: CInt = 12;
const SHM_STAT: CInt = 13;
const SHM_INFO: CInt = 14;
const SHMCTL_LOG_ENTER: CInt = 1;
const SHMCTL_LOG_LOOKUP: CInt = 2;
const SHMCTL_LOG_EPERM: CInt = 3;
const SHMCTL_LOG_COPY: CInt = 4;
const SHMCTL_LOG_EXIT: CInt = 5;
const SHMCTL_LOG_EACCES: CInt = 6;
const SHMCTL_LOG_PERM_SHM: CInt = 7;
const SHMCTL_LOG_PERM_PROC: CInt = 8;
const SHMCTL_LOG_USER_LOOKUP: CInt = 9;
const SHMCTL_LOG_TOO_LARGE: CInt = 10;
const SHMCTL_LOG_EINVAL: CInt = 11;

const MAP_SHARED: CInt = 0x01;
const MAP_PRIVATE: CInt = 0x02;
const MAP_FIXED: CInt = 0x10;
const MAP_ANONYMOUS: CInt = 0x20;
const MAP_LOCKED: CInt = 0x2000;
const MAP_POPULATE: CInt = 0x8000;
const MAP_HUGETLB: CInt = 0x00040000;

const SFD_CLOEXEC: CInt = 0o2000000;
const SFD_NONBLOCK: CInt = 0o4000;
const MINSIGSTKSZ: SizeT = 2048;
const SS_DISABLE: CInt = 2;

const IOV_MAX: CULong = 1024;
const PROCESS_VM_READ: CInt = 0;
const PROCESS_VM_WRITE: CInt = 1;
const PR_SET_THP_DISABLE: CInt = 41;
const PR_GET_THP_DISABLE: CInt = 42;
const ARCH_SET_GS: CULong = 0x1001;
const ARCH_SET_FS: CULong = 0x1002;
const ARCH_GET_FS: CULong = 0x1003;
const ARCH_GET_GS: CULong = 0x1004;
const IHK_ASR_X86_FS: CInt = 0;
const IHK_ASR_X86_GS: CInt = 1;
const SHM_HUGETLB: CInt = 0o4000;
const SHM_HUGE_SHIFT: CInt = 26;
const MAP_HUGE_SHIFT: CInt = 26;
const SHM_HUGE_2MB: CInt = 21 << SHM_HUGE_SHIFT;
const SHM_HUGE_1GB: CInt = 30 << SHM_HUGE_SHIFT;
const MAP_HUGE_2MB: CInt = 21 << MAP_HUGE_SHIFT;
const MAP_HUGE_1GB: CInt = 30 << MAP_HUGE_SHIFT;
const MAP_HUGE_MASK: CInt = 0xfc000000u32 as CInt;
const PTL3_SIZE: CULong = 1 << 30;
const ARCH_SHMGET_LOG_ENTER: CInt = 1;
const ARCH_SHMGET_LOG_EXIT: CInt = 2;
const ARCH_MMAP_LOG_ENTER: CInt = 1;
const ARCH_MMAP_LOG_UNSUPPORTED_PGSIZE: CInt = 2;
const ARCH_MMAP_LOG_INVALID: CInt = 3;
const ARCH_MMAP_LOG_NOMEM: CInt = 4;
const ARCH_MMAP_LOG_UNKNOWN_FLAGS: CInt = 5;

unsafe extern "C" {
    static mut tod_data: TodData;
}

#[no_mangle]
pub unsafe extern "C" fn tsc_to_ts(tsc: CULong, ts: *mut TimeSpec) {
    let clocks_per_sec = tod_data.clocks_per_sec;
    let sec_delta = core::intrinsics::unchecked_div(tsc, clocks_per_sec);
    let tsc_rem = core::intrinsics::unchecked_rem(tsc, clocks_per_sec);
    let ns_delta = core::intrinsics::unchecked_div(
        (NS_PER_SEC as CULong).wrapping_mul(tsc_rem),
        clocks_per_sec,
    );

    (*ts).tv_sec = sec_delta as CLong;
    (*ts).tv_nsec = ns_delta as CLong;
    if (*ts).tv_nsec >= NS_PER_SEC {
        (*ts).tv_nsec -= NS_PER_SEC;
        (*ts).tv_sec += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn timeval_to_jiffy(ats: *const TimeVal) -> CULong {
    ((*ats).tv_sec as CULong)
        .wrapping_mul(100)
        .wrapping_add((*ats).tv_usec as CULong / 10000)
}

#[no_mangle]
pub unsafe extern "C" fn timespec_to_jiffy(ats: *const TimeSpec) -> CULong {
    ((*ats).tv_sec as CULong)
        .wrapping_mul(100)
        .wrapping_add((*ats).tv_nsec as CULong / 10000000)
}
const ARCH_MMAP_LOG_EXIT: CInt = 6;

const SIGTRAP: CInt = 5;
const TRAP_TRACE: CInt = 2;
const RFLAGS_TF: CULong = 1 << 8;
const PTRACE_CONT: CLong = 7;
const PTRACE_KILL: CLong = 8;
const PTRACE_SINGLESTEP: CLong = 9;
const PTRACE_TRACEME: CLong = 0;
const PTRACE_PEEKTEXT: CLong = 1;
const PTRACE_PEEKDATA: CLong = 2;
const PTRACE_PEEKUSER: CLong = 3;
const PTRACE_POKETEXT: CLong = 4;
const PTRACE_POKEDATA: CLong = 5;
const PTRACE_POKEUSER: CLong = 6;
const PTRACE_GETREGS: CLong = 12;
const PTRACE_SETREGS: CLong = 13;
const PTRACE_GETFPREGS: CLong = 14;
const PTRACE_SETFPREGS: CLong = 15;
const PTRACE_ATTACH: CLong = 16;
const PTRACE_DETACH: CLong = 17;
const PTRACE_SYSCALL: CLong = 24;
const PTRACE_SETOPTIONS: CLong = 0x4200;
const PTRACE_GETEVENTMSG: CLong = 0x4201;
const PTRACE_GETSIGINFO: CLong = 0x4202;
const PTRACE_SETSIGINFO: CLong = 0x4203;
const PTRACE_GETREGSET: CLong = 0x4204;
const PTRACE_SETREGSET: CLong = 0x4205;
const PTRACE_WAKEUP_ACTION_NONE: CInt = 0;
const PTRACE_WAKEUP_ACTION_KILL: CInt = 1;
const PTRACE_WAKEUP_ACTION_RESUME: CInt = 2;
const PTRACE_RESUME_SIGNAL_SOURCE_USER: CInt = 0;
const PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG: CInt = 1;
const PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG: CInt = 2;
const PTRACE_SIGINFO_STORE_SENDSIG: CInt = 0x1;
const PTRACE_SIGINFO_STORE_RECVSIG: CInt = 0x2;
const PTRACE_SIGINFO_ALLOC_SENDSIG: CInt = 0x4;
const PTRACE_DISPATCH_ARCH: CInt = 0;
const PTRACE_DISPATCH_TRACEME: CInt = 1;
const PTRACE_DISPATCH_WAKEUP: CInt = 2;
const PTRACE_DISPATCH_GETREGS: CInt = 3;
const PTRACE_DISPATCH_SETREGS: CInt = 4;
const PTRACE_DISPATCH_GETFPREGS: CInt = 5;
const PTRACE_DISPATCH_SETFPREGS: CInt = 6;
const PTRACE_DISPATCH_PEEKUSER: CInt = 7;
const PTRACE_DISPATCH_POKEUSER: CInt = 8;
const PTRACE_DISPATCH_PEEKTEXT: CInt = 9;
const PTRACE_DISPATCH_POKETEXT: CInt = 10;
const PTRACE_DISPATCH_SETOPTIONS: CInt = 11;
const PTRACE_DISPATCH_ATTACH: CInt = 12;
const PTRACE_DISPATCH_DETACH: CInt = 13;
const PTRACE_DISPATCH_GETSIGINFO: CInt = 14;
const PTRACE_DISPATCH_SETSIGINFO: CInt = 15;
const PTRACE_DISPATCH_GETREGSET: CInt = 16;
const PTRACE_DISPATCH_SETREGSET: CInt = 17;
const PTRACE_DISPATCH_GETEVENTMSG: CInt = 18;
const PTRACE_O_MASK: CInt = 0x7f;
const NT_PRSTATUS: CLong = 1;
const NT_X86_XSTATE: CLong = 0x202;
const ARCH_PTRACE_REGSET_LOG_READ_UNSUPPORTED: CInt = 1;
const ARCH_PTRACE_REGSET_LOG_WRITE_UNSUPPORTED: CInt = 2;
const ARCH_PTRACE_USER_LOG_READ_MISSING_DEBUGREG: CInt = 3;
const ARCH_PTRACE_USER_LOG_READ_OTHER: CInt = 4;
const ARCH_PTRACE_USER_LOG_WRITE_MISSING_DEBUGREG: CInt = 5;
const ARCH_PTRACE_USER_LOG_WRITE_OTHER: CInt = 6;
const ARCH_PTRACE_USER_LOG_ALLOC_FAILED: CInt = 7;
const PTRACE_TEXT_LOG_PEEK_BAD_AREA: CInt = 1;
const PTRACE_TEXT_LOG_POKE_BAD_ADDRESS: CInt = 2;
const PTRACE_CONTROL_LOG_SETOPTIONS_UNSUPPORTED: CInt = 1;
const PTRACE_CONTROL_LOG_SETOPTIONS_APPLIED: CInt = 2;
const PTRACE_CONTROL_LOG_ATTACH_RETURN: CInt = 3;
const PTRACE_CONTROL_LOG_WAKEUP_ENTER: CInt = 4;
const PTRACE_REPORT_CLONE_LOG_ENTER: CInt = 5;
const PTRACE_REPORT_CLONE_LOG_KILL_SIGCHLD: CInt = 6;
const PTRACE_REPORT_CLONE_LOG_DO_KILL_FAILED: CInt = 7;
const PTRACE_REPORT_SIGNAL_LOG_ENTER: CInt = 8;
const PTRACE_REPORT_SIGNAL_LOG_SLEEPING: CInt = 9;
const PTRACE_REPORT_SIGNAL_LOG_WAKE: CInt = 10;
const PTRACE_O_TRACESYSGOOD: CInt = 0x01;
const PTRACE_O_TRACEFORK: CInt = 0x02;
const PTRACE_O_TRACEVFORK: CInt = 0x04;
const PTRACE_O_TRACECLONE: CInt = 0x08;
const PTRACE_O_TRACEEXEC: CInt = 0x10;
const PTRACE_O_TRACEVFORKDONE: CInt = 0x20;
const PTRACE_O_TRACEEXIT: CInt = 0x40;
const PTRACE_ALLOWED_OPTIONS: CInt = PTRACE_O_TRACESYSGOOD
    | PTRACE_O_TRACEFORK
    | PTRACE_O_TRACEVFORK
    | PTRACE_O_TRACECLONE
    | PTRACE_O_TRACEEXEC
    | PTRACE_O_TRACEVFORKDONE
    | PTRACE_O_TRACEEXIT;
const PS_RUNNING: CInt = 0x1;
const PS_STOPPED: CInt = 0x20;
const PS_TRACED: CInt = 0x40;
const PT_TRACED: CInt = 0x80;
const PT_TRACE_EXEC: CInt = 0x100;
const PT_TRACE_SYSCALL: CInt = 0x200;
const RFLAGS_MASK: CULong = (1 << 0)
    | (1 << 2)
    | (1 << 4)
    | (1 << 6)
    | (1 << 7)
    | (1 << 8)
    | (1 << 10)
    | (1 << 11)
    | (1 << 14)
    | (1 << 16)
    | (1 << 18);
const DB6_RESERVED_MASK: CULong = 0xffffffffffff1ff0;
const DB6_RESERVED_SET: CULong = 0xffff0ff0;
const DB7_RESERVED_MASK: CULong = 0xffffffff0000dc00;
const DB7_RESERVED_SET: CULong = 0x400;
const PERF_STOP_EVENT_CAPACITY: usize = 65;

type PtraceReadUserWordFn = unsafe extern "C" fn(CULong, CLong, *mut CULong) -> CLong;
type PtraceWriteUserWordFn = unsafe extern "C" fn(CULong, CLong, CULong) -> CLong;
type PtraceReadVmWordFn = unsafe extern "C" fn(CULong, CULong, *mut CULong) -> CLong;
type PtraceWriteVmWordFn = unsafe extern "C" fn(CULong, CULong, CULong) -> CLong;
type PtraceFpregsIoFn = unsafe extern "C" fn(CULong, CULong) -> CLong;
type PtraceUserCopyFromFn = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;
type PtraceUserCopyToFn = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;
type PtraceRegsetIoFn = unsafe extern "C" fn(CULong, CLong, *mut u8) -> CLong;
type PtraceFindThreadFn = unsafe extern "C" fn(CInt, CInt) -> CULong;
type PtraceThreadUnlockFn = unsafe extern "C" fn(CULong);
type PtraceTextLogFn = unsafe extern "C" fn(CInt, CULong);
type PtraceControlLogFn = unsafe extern "C" fn(CInt, CInt, CInt);
type PtraceAttachThreadFn = unsafe extern "C" fn(CULong, CULong) -> CInt;
type PtraceDetachCallFn = unsafe extern "C" fn(CULong, CInt);
type PtraceSetSingleStepFn = unsafe extern "C" fn(CULong);
type PtraceRwlockFn = unsafe extern "C" fn(CULong, *mut c_void);
type PtraceReportSignalFn = unsafe extern "C" fn(*mut c_void, CInt);
type PtraceVoidFn = unsafe extern "C" fn();
type PtraceArchSyscallEventFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CLong) -> CLong;
type PtraceSignalLockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type PtraceSaveDebugregFn = unsafe extern "C" fn(*mut c_void);
type PtraceSavedContextClearFn = unsafe extern "C" fn(CULong, CULong) -> CInt;
type PtraceTraceSyscallUpdateFn = unsafe extern "C" fn(CULong, CULong, CInt) -> CInt;
type PtracePendingSignalTakeFn = unsafe extern "C" fn(CULong, CULong, CULong, CInt) -> CULong;
type ArchPtraceGpregsReadFn = unsafe extern "C" fn(CULong, *mut u8) -> CLong;
type ArchPtraceGpregsWriteFn = unsafe extern "C" fn(CULong, *const u8) -> CLong;
type ArchPtraceXstateIoFn = unsafe extern "C" fn(CULong, CULong, SizeT) -> CLong;
type ArchPtraceRegsetLogFn = unsafe extern "C" fn(CInt, CLong);
type ArchPtraceLookupUserContextFn = unsafe extern "C" fn(*mut c_void) -> *mut c_void;
type ArchPtraceAllocFn = unsafe extern "C" fn(SizeT, CULong) -> *mut c_void;
type PtraceTracemeFn = unsafe extern "C" fn() -> CInt;
type PtraceWakeupSigFn = unsafe extern "C" fn(CInt, CLong, CLong) -> CInt;
type PtracePidDataFn = unsafe extern "C" fn(CInt, CLong) -> CLong;
type PtracePidAddrDataFn = unsafe extern "C" fn(CInt, CLong, CLong) -> CLong;
type PtraceSetoptionsFn = unsafe extern "C" fn(CInt, CInt) -> CInt;
type PtraceAttachFn = unsafe extern "C" fn(CInt) -> CInt;
type PtraceDetachFn = unsafe extern "C" fn(CInt, CInt) -> CInt;
type PtraceSiginfoFn = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;
type PtraceArchFn = unsafe extern "C" fn(CLong, CInt, CLong, CLong) -> CLong;
type SyscallCopyIntToUserFn = unsafe extern "C" fn(CULong, *const CInt) -> CLong;
type SyscallCopyFromUserFn = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;
type SyscallCopyToUserFn = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;
type SyscallForwardSigmaskFn = unsafe extern "C" fn(CULong) -> CLong;
type SyscallSigactionFn = unsafe extern "C" fn(CInt, *mut KSigAction, *mut KSigAction) -> CInt;
type SyscallSigcommonLockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type SyscallSigactionForwardFn = unsafe extern "C" fn(CInt, *const c_void) -> CLong;
type SyscallDoKillFn = unsafe extern "C" fn(CInt, CInt, *const SigInfo) -> CLong;
type SyscallDoKillThreadFn =
    unsafe extern "C" fn(*mut c_void, CInt, CInt, CInt, *const SigInfo, CInt) -> CLong;
type SyscallRefreshCredFn = unsafe extern "C" fn();
type SyscallGettimeFn = unsafe extern "C" fn(*mut TimeSpec);
type SyscallDoSyscall2Fn = unsafe extern "C" fn(CInt, CULong, CULong) -> CLong;
type SyscallDoSyscall3Fn = unsafe extern "C" fn(CInt, CULong, CULong, CULong) -> CLong;
type SyscallRequestCallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;
type SyscallVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type SyscallGetcredFn = unsafe extern "C" fn(*mut CInt) -> *mut CInt;
type SyscallForwardContextFn = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;
type SyscallTscToTsFn = unsafe extern "C" fn(CULong, *mut TimeSpec);
type SyscallTimespecToJiffyFn = unsafe extern "C" fn(*const TimeSpec) -> CULong;
type SyscallTsAddFn = unsafe extern "C" fn(*mut TimeSpec, *const TimeSpec);
type SyscallFindProcessFn = unsafe extern "C" fn(CInt, *mut c_void) -> *mut c_void;
type SyscallProcessUnlockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessCleanupFdFn = unsafe extern "C" fn(*mut c_void, CInt) -> CLong;
type ProcessCleanupMissingLogFn = unsafe extern "C" fn(CInt);
type SyscallSigsuspendFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CLong;
type SyscallDoPrlimit64Fn = unsafe extern "C" fn(CInt, CInt, CULong, CULong) -> CLong;
type SyscallGetCpuFn = unsafe extern "C" fn() -> CInt;
type SyscallLogIntFn = unsafe extern "C" fn(CInt, CInt);
type SyscallMbindLogFn = unsafe extern "C" fn(CInt, CULong, CULong, CInt);
type SyscallSetMempolicyLogFn = unsafe extern "C" fn(CInt, CInt, CInt);
type SyscallGetMempolicyLogFn = unsafe extern "C" fn(CInt, CULong, CInt);
type SyscallRwlockFn = unsafe extern "C" fn(*mut c_void);
type SyscallLookupNodeFn = unsafe extern "C" fn(*mut ProcessVm, *mut c_void) -> CInt;
type SyscallLookupRangeFn = unsafe extern "C" fn(*mut ProcessVm, CULong, CULong) -> *mut VmRange;
type SyscallPolicySearchFn = unsafe extern "C" fn(*mut ProcessVm, CULong) -> *mut VmRangeNumaPolicy;
type SyscallPolicyClearRangeFn = unsafe extern "C" fn(*mut ProcessVm, CULong, CULong) -> CInt;
type SyscallPolicyInsertFn = unsafe extern "C" fn(*mut ProcessVm, *mut VmRangeNumaPolicy) -> CInt;
type SyscallPolicyRbClearFn = unsafe extern "C" fn(*mut VmRangeNumaPolicy);
type SyscallPolicyAllocFn = unsafe extern "C" fn(SizeT, CULong) -> *mut c_void;
type MovePagesVerifyFn = unsafe extern "C" fn(*mut ProcessVm, CULong, SizeT) -> CInt;
type MovePagesGetNrNodesFn = unsafe extern "C" fn() -> CInt;
type MovePagesSmpHandlerFn = unsafe extern "C" fn(CInt, CInt, *mut c_void) -> CInt;
type MovePagesSmpCallFn =
    unsafe extern "C" fn(*mut c_void, Option<MovePagesSmpHandlerFn>, *mut c_void) -> CInt;
type MovePagesLogFn = unsafe extern "C" fn(CInt, CULong, CInt);
type ArchPrctlSetRegisterFn = unsafe extern "C" fn(CInt, CULong) -> CInt;
type ArchPrctlGetRegisterFn = unsafe extern "C" fn(CInt, *mut CULong) -> CInt;
type ArchPrctlLogFn = unsafe extern "C" fn(CInt, CInt, CULong);
type ArchCloneLockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ArchDoForkFn =
    unsafe extern "C" fn(CInt, CULong, CULong, CULong, CULong, CULong, CULong) -> CULong;
type ArchRtSigreturnSetSignalFn = unsafe extern "C" fn(CInt, *mut c_void, *const SigInfo);
type ArchRtSigreturnCheckSignalFn = unsafe extern "C" fn(CInt, *mut c_void, CInt);
type ArchRtSigreturnFreeFn = unsafe extern "C" fn(*mut c_void);
type ArchRtSigreturnXrstorFn = unsafe extern "C" fn(*mut c_void);
type ArchShmgetDefaultHugeShiftFn = unsafe extern "C" fn() -> CInt;
type ArchDoShmgetFn = unsafe extern "C" fn(CLong, SizeT, CInt) -> CInt;
type ArchShmgetLogFn = unsafe extern "C" fn(CInt, CLong, SizeT, CInt, CInt, CInt);
type ArchMmapDefaultHugeShiftFn = unsafe extern "C" fn() -> CInt;
type ArchMmapOvermapFn = unsafe extern "C" fn(SizeT, CInt) -> CInt;
type ArchDoMmapFn =
    unsafe extern "C" fn(CULong, SizeT, CInt, CInt, CInt, CLong, CInt, *mut c_void) -> CLong;
type ArchMmapLogFn =
    unsafe extern "C" fn(CInt, CULong, SizeT, CInt, CInt, CInt, CLong, CInt, CULong, CInt);
type SyscallMckfdLockFn = unsafe extern "C" fn(*mut c_void) -> CLong;
type SyscallMckfdUnlockFn = unsafe extern "C" fn(*mut c_void, CLong);
type SyscallMckfdLongFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CLong;
type SyscallMckfdIntFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type SyscallMckfdFreeFn = unsafe extern "C" fn(*mut c_void);
type SyscallTofuIoctlFn =
    unsafe extern "C" fn(*mut c_void, CInt, CULong, CULong, *mut CInt) -> CLong;
type SyscallTofuCloseFn = unsafe extern "C" fn(*mut c_void, CInt);
type SyscallRdtscFn = unsafe extern "C" fn() -> CULong;
type SyscallNsPerTscFn = unsafe extern "C" fn() -> CULong;
type SyscallHasSigpendingFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type SyscallCpuPauseFn = unsafe extern "C" fn();
type SyscallSetTimerFn = unsafe extern "C" fn(CInt);
type SyscallPendingMaskFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type SyscallSignalfdCreateFn = unsafe extern "C" fn(CInt, CInt) -> CLong;
type SyscallSignalfdPublishFn =
    unsafe extern "C" fn(*mut c_void, CInt, *const CULong, CInt) -> CLong;
type SyscallAtomic64ReadFn = unsafe extern "C" fn(*mut c_void) -> CLong;
type SyscallAtomic64IncFn = unsafe extern "C" fn(*mut c_void);
type SyscallWmbFn = unsafe extern "C" fn();
type SyscallPanicFn = unsafe extern "C" fn();
type SyncChildPerfReadFn = unsafe extern "C" fn(CInt) -> CULong;
type SyncChildAtomic64SetFn = unsafe extern "C" fn(*mut c_void, CLong);
type PerfEventUpdateFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type PerfReadAttrFlagsFn =
    unsafe extern "C" fn(*const c_void, *mut CInt, *mut CInt, *mut CInt) -> CInt;
type PerfReadValueFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type PerfReadDispatchFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CLong;
type PerfEventVoidFn = unsafe extern "C" fn(*mut c_void);
type PerfEventIntFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type PerfCounterExtraSetFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type PerfCounterInitRawFn = unsafe extern "C" fn(CInt, CULong, CInt) -> CInt;
type PerfCounterAttrFlagsFn = unsafe extern "C" fn(*const c_void, *mut CInt, *mut CInt) -> CInt;
type PerfCounterMaskCheckFn = unsafe extern "C" fn(CULong) -> CInt;
type PerfCounterStartFn = unsafe extern "C" fn(CULong) -> CInt;
type PerfCounterStopFn = unsafe extern "C" fn(CULong, CInt) -> CInt;
type PerfCounterAllocFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type PerfOpenSyscallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;
type PerfOpenAllocEventFn = unsafe extern "C" fn(*mut *mut c_void, *mut c_void) -> CInt;
type PerfAttrFreqFn = unsafe extern "C" fn(*const c_void) -> CInt;
type PerfDoMmapFn =
    unsafe extern "C" fn(CULong, SizeT, CInt, CInt, CInt, CLong, CInt, *mut c_void) -> CLong;
type PerfEventMapFn = unsafe extern "C" fn(CULong) -> CULong;
type PerfEventValidateFn = unsafe extern "C" fn(CULong) -> CInt;
type PerfExtraRegIdFn = unsafe extern "C" fn(CULong, CULong) -> CInt;
type PerfExtraRegMsrFn = unsafe extern "C" fn(CInt) -> u32;
type PerfExtraRegIdxFn = unsafe extern "C" fn(CInt) -> CInt;
type PerfHwEventInitFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type SettimeofdayLogFn = unsafe extern "C" fn(CInt, CULong, CULong, CLong, CLong, CLong);
type FutexSyscallTimeFn = unsafe extern "C" fn(CInt, CInt, *mut TimeSpec) -> CInt;
type FutexLocalTimeFn = unsafe extern "C" fn(*mut TimeSpec);
type FutexLinuxTimeFn = unsafe extern "C" fn(CInt, *mut TimeSpec) -> CInt;
type FutexNsPerTscFn = unsafe extern "C" fn() -> CULong;
type FutexDispatchFn = unsafe extern "C" fn(CULong, CInt, u32, u64, CULong, u32, u32, CInt) -> CInt;
type FutexLogFn = unsafe extern "C" fn(*const FutexLogRecord);
type BrkFlushFn = unsafe extern "C" fn();
type BrkExtendFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong) -> CULong;
type BrkLogFn = unsafe extern "C" fn(CInt, CInt, CULong, CULong, CULong);
type MunmapDoFn = unsafe extern "C" fn(*mut c_void, SizeT, CInt) -> CInt;
type MunmapLogFn = unsafe extern "C" fn(CInt, CInt, CULong, SizeT, CInt);
type DoMunmapVoidFn = unsafe extern "C" fn();
type DoMunmapRemoveRangeFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, *mut CInt) -> CInt;
type DoMunmapClearHostFn = unsafe extern "C" fn(CULong, SizeT, CInt);
type DoMunmapLogFn = unsafe extern "C" fn(CULong, SizeT, CInt);
type DoMmapSmallerPageFn = unsafe extern "C" fn(SizeT, *mut CInt) -> CInt;
type ClearHostPteLogFn = unsafe extern "C" fn(CLong);
type MunmapAllFreeRangesFn = unsafe extern "C" fn(*mut c_void);
type MunmapAllLogFn = unsafe extern "C" fn(CULong, SizeT, CInt);
type ShmdtLogFn = unsafe extern "C" fn(CInt, CULong, CInt);
type ShmatVoidFn = unsafe extern "C" fn();
type ShmatLookupObjFn = unsafe extern "C" fn(CInt, *mut *mut c_void) -> CInt;
type ShmatMemobjFn = unsafe extern "C" fn(*mut c_void);
type ShmatSearchFn = unsafe extern "C" fn(SizeT, CInt, *mut CULong) -> CInt;
type ShmatAddRangeFn = unsafe extern "C" fn(
    *mut c_void,
    CULong,
    CULong,
    CULong,
    CULong,
    *mut c_void,
    CLong,
    CInt,
) -> CInt;
type ShmatLogFn = unsafe extern "C" fn(CInt, CInt, CULong, CInt, CLong);
type ShmctlGetMaxIndexFn = unsafe extern "C" fn() -> CInt;
type ShmctlShmlockUserGetFn = unsafe extern "C" fn(u32, *mut *mut c_void) -> CInt;
type ShmctlMemobjRefcntReadFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ShmctlLogFn = unsafe extern "C" fn(CInt, CInt, CInt, CULong, CLong);
type SearchFreeSpaceLogFn = unsafe extern "C" fn(CInt, SizeT, CInt, CULong, CInt);

#[repr(C)]
pub(crate) struct ShmctlOffsets {
    obj_memobj_offset: SizeT,
    obj_pgshift_offset: SizeT,
    obj_real_segsz_offset: SizeT,
    obj_user_offset: SizeT,
    obj_ds_offset: SizeT,
    obj_uid_offset: SizeT,
    obj_cuid_offset: SizeT,
    obj_gid_offset: SizeT,
    obj_cgid_offset: SizeT,
    obj_mode_offset: SizeT,
    obj_ctime_offset: SizeT,
    obj_nattch_offset: SizeT,
    shmlock_user_locked_offset: SizeT,
    shmid_ds_size: SizeT,
    shminfo_size: SizeT,
    shm_info_size: SizeT,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct IpcPerm {
    key: CInt,
    uid: u32,
    gid: u32,
    cuid: u32,
    cgid: u32,
    mode: u16,
    padding: [u8; 2],
    seq: u16,
    padding2: [u8; 22],
}

#[repr(C)]
#[derive(Clone, Copy)]
struct ShmidDs {
    shm_perm: IpcPerm,
    shm_segsz: SizeT,
    shm_atime: CLong,
    shm_dtime: CLong,
    shm_ctime: CLong,
    shm_cpid: CInt,
    shm_lpid: CInt,
    shm_nattch: u64,
    padding: [u8; 12],
    init_pgshift: CInt,
}
type MsyncLookupRangeFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> *mut c_void;
type MsyncNextRangeFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> *mut c_void;
type MsyncHasPagerFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type MsyncRangeOpFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong) -> CInt;
type MsyncLogFn = unsafe extern "C" fn(CInt, CULong, SizeT, CInt, CInt);
type MemlockSplitFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, *mut *mut c_void) -> CInt;
type MemlockJoinFn = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void) -> CInt;
type MemlockPopulateFn = unsafe extern "C" fn(*mut c_void, CULong, SizeT) -> CInt;
type MemlockLogFn = unsafe extern "C" fn(*const MemlockLogRecord);
type MprotectFlushFn = unsafe extern "C" fn();
type MprotectChangeFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong) -> CInt;
type MprotectSetHostVmaFn = unsafe extern "C" fn(CULong, SizeT, CInt, CInt) -> CInt;
type MprotectLogFn = unsafe extern "C" fn(*const MprotectLogRecord);
type RemapFilePagesCallableFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type RemapFilePagesRemapFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong, CLong) -> CInt;
type RemapFilePagesClearHostFn = unsafe extern "C" fn(CULong, SizeT, CInt);
type RemapFilePagesLogFn = unsafe extern "C" fn(*const RemapFilePagesLogRecord);
type MremapExtendFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong) -> CInt;
type MremapSearchFn = unsafe extern "C" fn(SizeT, CULong, *mut CULong) -> CInt;
type MremapMemobjRefFn = unsafe extern "C" fn(*mut c_void);
type MremapAddRangeFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong, CLong, CULong, *mut c_void, CULong) -> CInt;
type MremapMovePteFn = unsafe extern "C" fn(
    *mut c_void,
    *mut c_void,
    *mut c_void,
    *mut c_void,
    SizeT,
    *mut c_void,
) -> CInt;
type MremapLogFn = unsafe extern "C" fn(*const MremapLogRecord);
type MincorePteLookupFn = unsafe extern "C" fn(*mut c_void, CULong) -> *mut c_void;
type MincorePtePresentFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type MincoreMemobjLookupFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;
type MincoreCopyByteFn = unsafe extern "C" fn(CULong, u8) -> CLong;
type MincoreLogFn = unsafe extern "C" fn(CInt, CULong, SizeT, CULong, CInt);
type ProcessVmRwFn =
    unsafe extern "C" fn(CInt, *const c_void, CULong, *const c_void, CULong, CULong, CInt) -> CInt;
type ArchProcessVmRwLockFn = unsafe extern "C" fn(*mut c_void);
type ArchProcessVmRwLookupRangeFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong) -> *mut c_void;
type ArchProcessVmRwFindProcessFn = unsafe extern "C" fn(CInt, *mut c_void) -> *mut c_void;
type ArchProcessVmRwProcessUnlockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ArchProcessVmRwProcessLockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ArchProcessVmRwVmVoidFn = unsafe extern "C" fn(*mut c_void);
type ArchProcessVmRwVtopFn =
    unsafe extern "C" fn(*mut c_void, CULong, *mut CULong, *mut CULong) -> CInt;
type ArchProcessVmRwFaultFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CInt;
type ArchProcessVmRwPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ArchProcessVmRwMemcpyFn = unsafe extern "C" fn(*mut c_void, *const c_void, SizeT);
type ArchProcessVmRwLogFn = unsafe extern "C" fn(*const ArchProcessVmRwLogRecord);
type UtilThreadFn = unsafe extern "C" fn(*mut c_void) -> CLong;
type ExecveatFn = unsafe extern "C" fn(
    *mut c_void,
    CInt,
    *const c_void,
    *mut *mut c_void,
    *mut *mut c_void,
    CInt,
) -> CInt;
type SwapoutPageoutFn = unsafe extern "C" fn(*const c_void, *mut c_void, SizeT, CInt) -> CInt;
type SwapoutPageinFn = unsafe extern "C" fn(CInt) -> CInt;
type SyscallStrlenUserFn = unsafe extern "C" fn(*const c_void) -> CLong;
type SyscallOpenSpecialFn = unsafe extern "C" fn(*const c_void, CInt, *mut c_void) -> CLong;
type SyscallIkcSendFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CInt) -> CInt;

#[repr(C)]
pub struct ArchProcessVmRwOffsets {
    thread_proc_offset: SizeT,
    thread_vm_offset: SizeT,
    proc_vm_offset: SizeT,
    proc_status_offset: SizeT,
    proc_ruid_offset: SizeT,
    proc_euid_offset: SizeT,
    proc_suid_offset: SizeT,
    proc_rgid_offset: SizeT,
    proc_egid_offset: SizeT,
    proc_sgid_offset: SizeT,
    process_vm_address_space_offset: SizeT,
    address_space_page_table_offset: SizeT,
    vm_range_flag_offset: SizeT,
}

#[repr(C)]
pub struct ArchProcessVmRwLogRecord {
    event: CInt,
    x: CInt,
    y: CInt,
    z: CInt,
    a: CULong,
    b: CULong,
    c: CULong,
    d: CULong,
    e: CULong,
}

#[repr(C)]
pub struct MemlockLogRecord {
    event: CInt,
    op: CInt,
    cpu: CInt,
    start: CULong,
    len: SizeT,
    addr: CULong,
    range_start: CULong,
    range_end: CULong,
    error: CInt,
}

#[repr(C)]
pub struct MprotectLogRecord {
    event: CInt,
    cpu: CInt,
    start: CULong,
    len: SizeT,
    prot: CInt,
    addr: CULong,
    range_start: CULong,
    range_end: CULong,
    range_flags: CULong,
    protflags: CULong,
    denied: CULong,
    error: CInt,
}

#[repr(C)]
pub struct RemapFilePagesLogRecord {
    event: CInt,
    cpu: CInt,
    start0: CULong,
    size: SizeT,
    prot: CInt,
    pgoff: SizeT,
    flags: CInt,
    start: CULong,
    end: CULong,
    range_start: CULong,
    range_end: CULong,
    range_flags: CULong,
    memobj: *mut c_void,
    off: CLong,
    error: CInt,
}

#[repr(C)]
pub struct MremapLogRecord {
    event: CInt,
    oldaddr: CULong,
    oldsize0: SizeT,
    newsize0: SizeT,
    flags: CInt,
    newaddr: CULong,
    oldstart: CULong,
    oldend: CULong,
    newstart: CULong,
    newend: CULong,
    range_start: CULong,
    range_end: CULong,
    range_flags: CULong,
    lckstart: CULong,
    lckend: CULong,
    error: CInt,
}

#[repr(C)]
pub struct FutexLogRecord {
    event: CInt,
    flags: CInt,
    op: CInt,
    uaddr: CULong,
    val: u32,
    utime: CULong,
    uaddr2: CULong,
    val3: u32,
    fshared: CInt,
    ret: CInt,
    sec: CLong,
    nsec: CLong,
}
type Wait4DoWaitFn = unsafe extern "C" fn(CInt, *mut CInt, CInt, *mut RUsage) -> CInt;
type WaitScanFn = unsafe extern "C" fn(CInt, *mut CInt, CInt, *mut c_void, *mut CInt) -> CInt;
type WaitEntryInitFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type WaitPrepareFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CInt);
type WaitFinishFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type WaitHasSignalFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type WaitScheduleFn = unsafe extern "C" fn();
type WaitLogFn = unsafe extern "C" fn(CInt, CInt, CInt);
type WaitStatusFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, *mut CInt, CInt) -> CInt;
type WaitLockUnlockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type WaitThreadReportDetachFn = unsafe extern "C" fn(*mut c_void);
type WaitThreadSideEffectFn = unsafe extern "C" fn(*mut c_void);
type WaitSignalFlagsReapFn = unsafe extern "C" fn(*mut c_void, CULong, CInt, CInt) -> CInt;
type WaitExitStatusReapFn = unsafe extern "C" fn(*mut c_void, CULong, CInt) -> CInt;
type WaitHostWait4Fn = unsafe extern "C" fn(CInt, CInt) -> CInt;
type WaitListDetachFn = unsafe extern "C" fn(*mut c_void);
type WaitListAddTailFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type WaitZombieLogFn = unsafe extern "C" fn(CInt, CInt, CInt, CInt);
type PtraceListDetachFn = unsafe extern "C" fn(*mut c_void);
type PtraceMainReparentFn = unsafe extern "C" fn(
    *mut c_void,
    CULong,
    *mut c_void,
    *mut c_void,
    *mut c_void,
    *mut c_void,
) -> CInt;
type PtraceReportDetachFn =
    unsafe extern "C" fn(*mut c_void, CULong, *mut c_void, *mut c_void) -> CInt;
type PtraceCleanupFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong) -> *mut c_void;
type PtraceFreeFn = unsafe extern "C" fn(*mut c_void);
type PtraceClearSingleStepFn = unsafe extern "C" fn(*mut c_void);
type PtraceReportAttachFn = unsafe extern "C" fn(
    *mut c_void,
    CULong,
    CInt,
    CInt,
    CULong,
    *mut c_void,
    *mut c_void,
    *mut c_void,
) -> CInt;
type PtraceThreadExitSignalFn = unsafe extern "C" fn(*mut c_void);
type PtraceDoKillThreadFn =
    unsafe extern "C" fn(*mut c_void, CInt, CInt, CInt, *const SigInfo, CInt) -> CLong;
type PtraceWakeupThreadFn = unsafe extern "C" fn(*mut c_void, CInt);
type PtraceFinalizeProcessFn = unsafe extern "C" fn(*mut c_void);

#[repr(C)]
pub struct PtraceSyscallOps {
    traceme_fn: Option<PtraceTracemeFn>,
    wakeup_fn: Option<PtraceWakeupSigFn>,
    getregs_fn: Option<PtracePidDataFn>,
    setregs_fn: Option<PtracePidDataFn>,
    getfpregs_fn: Option<PtracePidDataFn>,
    setfpregs_fn: Option<PtracePidDataFn>,
    peekuser_fn: Option<PtracePidAddrDataFn>,
    pokeuser_fn: Option<PtracePidAddrDataFn>,
    peektext_fn: Option<PtracePidAddrDataFn>,
    poketext_fn: Option<PtracePidAddrDataFn>,
    setoptions_fn: Option<PtraceSetoptionsFn>,
    attach_fn: Option<PtraceAttachFn>,
    detach_fn: Option<PtraceDetachFn>,
    getsiginfo_fn: Option<PtraceSiginfoFn>,
    setsiginfo_fn: Option<PtraceSiginfoFn>,
    getregset_fn: Option<PtracePidAddrDataFn>,
    setregset_fn: Option<PtracePidAddrDataFn>,
    geteventmsg_fn: Option<PtracePidDataFn>,
    arch_fn: Option<PtraceArchFn>,
}

#[repr(C)]
pub struct PtraceIoOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_status_offset: SizeT,
    pub thread_vm_offset: SizeT,
    pub thread_ptrace_offset: SizeT,
    pub thread_ptrace_eventmsg_offset: SizeT,
    pub thread_ptrace_recvsig_offset: SizeT,
    pub thread_ptrace_sendsig_offset: SizeT,
    pub thread_report_proc_offset: SizeT,
    pub thread_ptrace_saved_uctx_valid_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_update_lock_offset: SizeT,
}

#[repr(C)]
pub struct PtraceReportCloneOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_tid_offset: SizeT,
    pub thread_status_offset: SizeT,
    pub thread_exit_status_offset: SizeT,
    pub thread_ptrace_offset: SizeT,
    pub thread_ptrace_eventmsg_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_parent_offset: SizeT,
    pub proc_status_offset: SizeT,
    pub proc_update_lock_offset: SizeT,
    pub proc_waitpid_q_offset: SizeT,
}

#[repr(C)]
pub struct PtraceReportExecOffsets {
    pub thread_ptrace_offset: SizeT,
    pub thread_ctx_offset: SizeT,
    pub thread_uctx_offset: SizeT,
    pub thread_ptrace_saved_uctx_offset: SizeT,
    pub thread_ptrace_saved_uctx_valid_offset: SizeT,
}

#[repr(C)]
pub struct PtraceReportSignalOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_tid_offset: SizeT,
    pub thread_status_offset: SizeT,
    pub thread_exit_status_offset: SizeT,
    pub thread_signal_flags_offset: SizeT,
    pub thread_ptrace_offset: SizeT,
    pub thread_ptrace_debugreg_offset: SizeT,
    pub thread_report_proc_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_parent_offset: SizeT,
    pub proc_main_thread_offset: SizeT,
    pub proc_status_offset: SizeT,
    pub proc_update_lock_offset: SizeT,
    pub proc_waitpid_q_offset: SizeT,
}

#[repr(C)]
pub struct ArchPtraceUserOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_ptrace_saved_uctx_valid_offset: SizeT,
    pub thread_ptrace_saved_uctx_offset: SizeT,
    pub thread_ptrace_debugreg_offset: SizeT,
    pub proc_status_offset: SizeT,
    pub uctx_sr_offset: SizeT,
    pub uctx_gpr_offset: SizeT,
}

type SyscallThreadsLockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type SyscallThreadsUnlockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type SyscallInterruptCpuFn = unsafe extern "C" fn(CInt);
type SyscallExitFn = unsafe extern "C" fn(CInt);
type SyscallTerminateFn = unsafe extern "C" fn(CInt, CInt);
type SyscallExitGroupLogFn = unsafe extern "C" fn(CInt);
type SyscallScheduleFn = unsafe extern "C" fn();
type ThreadExitWakeFn = unsafe extern "C" fn(*mut c_void);
type ThreadExitLogFn = unsafe extern "C" fn(CInt, CLong);
type FinalizeWakeupLogFn = unsafe extern "C" fn();
type TerminateMcexecCmpxchgFn = unsafe extern "C" fn(*mut CULong, CULong, CULong) -> CULong;
type TerminateMcexecSyscallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;
type TerminateHostRefSetFn = unsafe extern "C" fn(*mut c_void, CInt);

#[repr(C)]
pub struct SyscallCputimeOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_status_offset: SizeT,
    pub thread_in_kernel_offset: SizeT,
    pub thread_cpu_id_offset: SizeT,
    pub thread_times_update_offset: SizeT,
    pub thread_user_tsc_offset: SizeT,
    pub thread_system_tsc_offset: SizeT,
    pub thread_siblings_list_offset: SizeT,
    pub proc_threads_list_offset: SizeT,
    pub proc_utime_offset: SizeT,
    pub proc_stime_offset: SizeT,
    pub proc_utime_children_offset: SizeT,
    pub proc_stime_children_offset: SizeT,
    pub proc_maxrss_offset: SizeT,
    pub proc_maxrss_children_offset: SizeT,
}

#[repr(C)]
pub struct SyscallItimerOffsets {
    pub thread_itimer_enabled_offset: SizeT,
    pub thread_itimer_virtual_offset: SizeT,
    pub thread_itimer_prof_offset: SizeT,
    pub thread_itimer_virtual_value_offset: SizeT,
    pub thread_itimer_prof_value_offset: SizeT,
}

#[repr(C)]
pub struct SyscallTimesOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_user_tsc_offset: SizeT,
    pub thread_system_tsc_offset: SizeT,
    pub proc_utime_offset: SizeT,
    pub proc_stime_offset: SizeT,
    pub proc_utime_children_offset: SizeT,
    pub proc_stime_children_offset: SizeT,
}

#[repr(C)]
pub struct SyscallTimesTms {
    pub tms_utime: CULong,
    pub tms_stime: CULong,
    pub tms_cutime: CULong,
    pub tms_cstime: CULong,
}

#[repr(C)]
pub struct SyscallSetpgidOffsets {
    pub thread_proc_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_pgid_offset: SizeT,
    pub proc_execed_offset: SizeT,
}

#[repr(C)]
pub struct SyscallMlockallOffsets {
    pub thread_proc_offset: SizeT,
    pub proc_euid_offset: SizeT,
    pub proc_rlimit_offset: SizeT,
    pub rlimit_entry_size: SizeT,
    pub memlock_resource: CInt,
}

#[repr(C)]
pub struct SyscallMckfdOffsets {
    pub thread_proc_offset: SizeT,
    pub proc_mckfd_lock_offset: SizeT,
    pub proc_mckfd_offset: SizeT,
    pub mckfd_next_offset: SizeT,
    pub mckfd_fd_offset: SizeT,
    pub mckfd_read_cb_offset: SizeT,
    pub mckfd_ioctl_cb_offset: SizeT,
    pub mckfd_close_cb_offset: SizeT,
    pub mckfd_fcntl_cb_offset: SizeT,
}

#[repr(C)]
pub struct WaitZombieOffsets {
    pub thread_ptrace_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_ppid_parent_offset: SizeT,
    pub proc_parent_offset: SizeT,
    pub proc_status_offset: SizeT,
    pub proc_group_exit_status_offset: SizeT,
    pub proc_nowait_offset: SizeT,
    pub proc_update_lock_offset: SizeT,
    pub proc_children_lock_offset: SizeT,
    pub proc_threads_lock_offset: SizeT,
    pub proc_siblings_list_offset: SizeT,
    pub proc_children_list_offset: SizeT,
    pub proc_main_thread_offset: SizeT,
    pub proc_stime_offset: SizeT,
    pub proc_utime_offset: SizeT,
    pub proc_stime_children_offset: SizeT,
    pub proc_utime_children_offset: SizeT,
    pub proc_maxrss_offset: SizeT,
    pub proc_maxrss_children_offset: SizeT,
}

#[repr(C)]
pub struct WaitScanOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_tid_offset: SizeT,
    pub thread_status_offset: SizeT,
    pub thread_ptrace_offset: SizeT,
    pub thread_signal_flags_offset: SizeT,
    pub thread_termsig_offset: SizeT,
    pub thread_report_siblings_list_offset: SizeT,
    pub thread_siblings_list_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_pgid_offset: SizeT,
    pub proc_status_offset: SizeT,
    pub proc_children_lock_offset: SizeT,
    pub proc_threads_lock_offset: SizeT,
    pub proc_children_list_offset: SizeT,
    pub proc_ptraced_children_list_offset: SizeT,
    pub proc_siblings_list_offset: SizeT,
    pub proc_ptraced_siblings_list_offset: SizeT,
    pub proc_report_threads_list_offset: SizeT,
    pub proc_threads_list_offset: SizeT,
    pub proc_main_thread_offset: SizeT,
}

#[repr(C)]
pub struct PtraceDetachOffsets {
    pub thread_proc_offset: SizeT,
    pub thread_termsig_offset: SizeT,
    pub thread_status_offset: SizeT,
    pub thread_tid_offset: SizeT,
    pub thread_report_proc_offset: SizeT,
    pub thread_report_siblings_list_offset: SizeT,
    pub thread_ptrace_offset: SizeT,
    pub thread_ptrace_saved_uctx_valid_offset: SizeT,
    pub thread_ptrace_debugreg_offset: SizeT,
    pub proc_pid_offset: SizeT,
    pub proc_status_offset: SizeT,
    pub proc_parent_offset: SizeT,
    pub proc_ppid_parent_offset: SizeT,
    pub proc_main_thread_offset: SizeT,
    pub proc_children_lock_offset: SizeT,
    pub proc_threads_lock_offset: SizeT,
    pub proc_children_list_offset: SizeT,
    pub proc_siblings_list_offset: SizeT,
    pub proc_ptraced_siblings_list_offset: SizeT,
    pub proc_report_threads_list_offset: SizeT,
}

const PTRACE_EVENT_FORK: CInt = 1;
const PTRACE_EVENT_VFORK: CInt = 2;
const PTRACE_EVENT_CLONE: CInt = 3;
const PTRACE_EVENT_EXEC: CInt = 4;
const PTRACE_EVENT_VFORK_DONE: CInt = 5;
const CLD_TRAPPED: CInt = 4;
const SI_USER: CInt = 0;
const SIGCHLD: CInt = 17;
const SIGCONT: CInt = 18;
const SIGURG: CInt = 23;
const SIG_IGN_HANDLER: CULong = 1;

const SIGNAL_STOP_STOPPED: CInt = 0x1;
const SIGNAL_STOP_CONTINUED: CInt = 0x2;
const PS_ZOMBIE: CInt = 0x8;
const PS_EXITED: CInt = 0x10;
const PS_DELAY_STOPPED: CInt = 0x200;
const PS_DELAY_TRACED: CInt = 0x400;
const WNOHANG: CInt = 0x00000001;
const WUNTRACED: CInt = 0x00000002;
const WSTOPPED: CInt = WUNTRACED;
const WEXITED: CInt = 0x00000004;
const WCONTINUED: CInt = 0x00000008;
const WNOWAIT: CInt = 0x01000000;
const __WALL: CInt = 0x40000000;
const __WCLONE: CInt = 0x80000000u32 as CInt;
const P_ALL: CInt = 0;
const P_PID: CInt = 1;
const P_PGID: CInt = 2;
const CLD_EXITED: CInt = 1;
const CLD_KILLED: CInt = 2;
const CLD_DUMPED: CInt = 3;
const CLD_STOPPED: CInt = 5;
const CLD_CONTINUED: CInt = 6;
const EXIT_GROUP_STATUS_CONFIRMED: CULong = 0x0000000100000000;
const WAIT_STOP_SOURCE_NONE: CInt = 0;
const WAIT_STOP_SOURCE_THREAD: CInt = 1;
const WAIT_STOP_SOURCE_PROCESS: CInt = 2;
const WAIT_STOP_SOURCE_MAIN_THREAD: CInt = 3;
const WAIT_THREAD_REAP_ACTION_NONE: CInt = 0;
const WAIT_THREAD_REAP_ACTION_RELEASE: CInt = 1;
const WAIT_THREAD_REAP_ACTION_PTRACE_DETACH: CInt = 2;
const WAIT_LOG_ENTER: CInt = 1;
const WAIT_LOG_SLEEPING: CInt = 2;
const WAIT_LOG_WOKEN: CInt = 3;
const WAIT_LOG_FOUND: CInt = 4;
const WAIT_LOG_NOTFOUND: CInt = 5;
const WAIT_ZOMBIE_LOG_FOUND: CInt = 1;
const WAIT_ZOMBIE_LOG_WARNING: CInt = 2;
const WAIT_ZOMBIE_LOG_STATUS: CInt = 3;

const CSIGNAL: CInt = 0x000000ff;
const CLONE_VM: CInt = 0x00000100;
const CLONE_FS: CInt = 0x00000200;
const CLONE_SIGHAND: CInt = 0x00000800;
const CLONE_VFORK: CInt = 0x00004000;
const CLONE_PARENT: CInt = 0x00008000;
const CLONE_THREAD: CInt = 0x00010000;
const CLONE_NEWNS: CInt = 0x00020000;
const CLONE_SYSVSEM: CInt = 0x00040000;
const CLONE_SETTLS: CInt = 0x00080000;
const CLONE_PARENT_SETTID: CInt = 0x00100000;
const CLONE_CHILD_CLEARTID: CInt = 0x00200000;
const CLONE_CHILD_SETTID: CInt = 0x01000000;
const CLONE_NEWIPC: CInt = 0x08000000;
const CLONE_NEWPID: CInt = 0x20000000;
const SPAWN_TO_LOCAL: CInt = 0;
const SPAWN_TO_REMOTE: CInt = 1;
const CLONE_TLS_SOURCE_INHERIT: CInt = 0;
const CLONE_TLS_SOURCE_ARGUMENT: CInt = 1;

const AT_FDCWD: CInt = -100;
const AT_SYMLINK_NOFOLLOW: CInt = 0x100;
const AT_EMPTY_PATH: CInt = 0x1000;

const FUTEX_WAIT: CInt = 0;
const FUTEX_CMP_REQUEUE: CInt = 4;
const FUTEX_WAKE_OP: CInt = 5;
const FUTEX_WAIT_BITSET: CInt = 9;
const FUTEX_PRIVATE_FLAG: CInt = 128;
const FUTEX_CLOCK_REALTIME: CInt = 256;
const FUTEX_CMD_MASK: CInt = !(FUTEX_PRIVATE_FLAG | FUTEX_CLOCK_REALTIME);
const DO_FUTEX_LOG_ENTER: CInt = 1;
const DO_FUTEX_LOG_TIMEOUT: CInt = 2;
const DO_FUTEX_LOG_ABSOLUTE_TIME: CInt = 3;
const DO_FUTEX_LOG_EXIT: CInt = 4;
const BRK_LOG_ENTER: CInt = 1;
const BRK_LOG_SET_END: CInt = 2;
const MUNMAP_LOG_ENTER: CInt = 1;
const MUNMAP_LOG_EXIT: CInt = 2;
const MUNMAP_LOG_ERROR: CInt = 3;
const SHMDT_LOG_ENTER: CInt = 1;
const SHMDT_LOG_INVALID: CInt = 2;
const SHMDT_LOG_EXIT: CInt = 3;
const SHMAT_LOG_ENTER: CInt = 1;
const SHMAT_LOG_LOOKUP_FAILED: CInt = 2;
const SHMAT_LOG_INVALID_ADDR: CInt = 3;
const SHMAT_LOG_ACCESS_FAILED: CInt = 4;
const SHMAT_LOG_RANGE_BUSY: CInt = 5;
const SHMAT_LOG_SEARCH_FAILED: CInt = 6;
const SHMAT_LOG_SET_HOST_FAILED: CInt = 7;
const SHMAT_LOG_ADD_FAILED: CInt = 8;
const SHMAT_LOG_EXIT: CInt = 9;
const SEARCH_FREE_SPACE_LOG_ENTER: CInt = 1;
const SEARCH_FREE_SPACE_LOG_OUTSIDE: CInt = 2;
const SEARCH_FREE_SPACE_LOG_EXIT: CInt = 3;
const MSYNC_LOG_ENTER: CInt = 1;
const MSYNC_LOG_INVALID_ARGS: CInt = 2;
const MSYNC_LOG_INVALID_VMR: CInt = 3;
const MSYNC_LOG_LOCKED_VMR: CInt = 4;
const MSYNC_LOG_UNSYNCABLE_VMR: CInt = 5;
const MSYNC_LOG_SYNC_FAILED: CInt = 6;
const MSYNC_LOG_INVALIDATE_FAILED: CInt = 7;
const MSYNC_LOG_EXIT: CInt = 8;
const MEMLOCK_OP_LOCK: CInt = 1;
const MEMLOCK_OP_UNLOCK: CInt = 2;
const MEMLOCK_LOG_ENTER: CInt = 1;
const MEMLOCK_LOG_NOT_CONTIG: CInt = 2;
const MEMLOCK_LOG_CANNOT_CHANGE: CInt = 3;
const MEMLOCK_LOG_SPLIT_FAILED: CInt = 4;
const MEMLOCK_LOG_JOIN_FAILED: CInt = 5;
const MEMLOCK_LOG_POPULATE_FAILED: CInt = 6;
const MEMLOCK_LOG_EXIT: CInt = 7;
const MPROTECT_LOG_ENTER: CInt = 1;
const MPROTECT_LOG_INVALID_RANGE: CInt = 2;
const MPROTECT_LOG_STRAIGHT_IGNORED: CInt = 3;
const MPROTECT_LOG_NOT_CONTIG: CInt = 4;
const MPROTECT_LOG_DENIED: CInt = 5;
const MPROTECT_LOG_CANNOT_CHANGE: CInt = 6;
const MPROTECT_LOG_SPLIT_FAILED: CInt = 7;
const MPROTECT_LOG_CHANGE_FAILED: CInt = 8;
const MPROTECT_LOG_JOIN_FAILED: CInt = 9;
const MPROTECT_LOG_SET_HOST_FAILED: CInt = 10;
const MPROTECT_LOG_EXIT: CInt = 11;
const REMAP_FILE_PAGES_LOG_ENTER: CInt = 1;
const REMAP_FILE_PAGES_LOG_INVALID_ARGS: CInt = 2;
const REMAP_FILE_PAGES_LOG_INVALID_VMR: CInt = 3;
const REMAP_FILE_PAGES_LOG_REMAP_FAILED: CInt = 4;
const REMAP_FILE_PAGES_LOG_POPULATE_FAILED: CInt = 5;
const REMAP_FILE_PAGES_LOG_EXIT: CInt = 6;
const MREMAP_LOG_ENTER: CInt = 1;
const MREMAP_LOG_STRAIGHT_REJECT: CInt = 2;
const MREMAP_LOG_INVALID: CInt = 3;
const MREMAP_LOG_ALLOCATE_FAILED: CInt = 4;
const MREMAP_LOG_LOOKUP_FAILED: CInt = 5;
const MREMAP_LOG_FIXED_MIN_ADDR: CInt = 6;
const MREMAP_LOG_FIXED_OVERLAP: CInt = 7;
const MREMAP_LOG_CANNOT_RELOCATE: CInt = 8;
const MREMAP_LOG_SEARCH_FAILED: CInt = 9;
const MREMAP_LOG_FIXED_MUNMAP_FAILED: CInt = 10;
const MREMAP_LOG_ADD_FAILED: CInt = 11;
const MREMAP_LOG_SPLIT_FAILED: CInt = 12;
const MREMAP_LOG_MOVE_FAILED: CInt = 13;
const MREMAP_LOG_RELOCATE_MUNMAP_FAILED: CInt = 14;
const MREMAP_LOG_SHRINK_MUNMAP_FAILED: CInt = 15;
const MREMAP_LOG_POPULATE_FAILED: CInt = 16;
const MREMAP_LOG_EXIT: CInt = 17;
const MINCORE_LOG_INVALID: CInt = 1;
const MINCORE_LOG_LOOKUP_FAILED: CInt = 2;
const MINCORE_LOG_COPY_FAILED: CInt = 3;
const MINCORE_LOG_EXIT: CInt = 4;

const MREMAP_MAYMOVE: CInt = 0x01;
const MREMAP_FIXED: CInt = 0x02;

const MS_ASYNC: CInt = 0x01;
const MS_INVALIDATE: CInt = 0x02;
const MS_SYNC: CInt = 0x04;

const PROCESS_NUMA_MASK_BITS: CULong = 256;
const MPOL_DEFAULT: CInt = 0;
const MPOL_PREFERRED: CInt = 1;
const MPOL_BIND: CInt = 2;
const MPOL_INTERLEAVE: CInt = 3;
const MPOL_F_STATIC_NODES: CInt = 1 << 15;
const MPOL_F_RELATIVE_NODES: CInt = 1 << 14;
const MPOL_MODE_FLAGS: CInt = MPOL_F_STATIC_NODES | MPOL_F_RELATIVE_NODES;
const MPOL_F_NODE: CInt = 1 << 0;
const MPOL_F_ADDR: CInt = 1 << 1;
const MPOL_F_MEMS_ALLOWED: CInt = 1 << 2;
const MPOL_MF_STRICT: CInt = 1 << 0;
const MPOL_MF_MOVE: CInt = 1 << 1;
const MPOL_MF_MOVE_ALL: CInt = 1 << 2;
const MOVE_PAGES_LOG_UNSUPPORTED_PID: CInt = 1;
const MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL: CInt = 2;
const MOVE_PAGES_LOG_INIT_MALLOC: CInt = 3;
const MOVE_PAGES_LOG_INIT_VERIFY: CInt = 4;
const MOVE_PAGES_LOG_PARALLEL: CInt = 5;

const RUSAGE_SELF: CInt = 0;
const RUSAGE_CHILDREN: CInt = -1;
const RUSAGE_THREAD: CInt = 1;
const GETRUSAGE_DISPATCH_SELF: CInt = 1;
const GETRUSAGE_DISPATCH_CHILDREN: CInt = 2;
const GETRUSAGE_DISPATCH_THREAD: CInt = 3;
const GETRUSAGE_THREAD_UPDATE_READY: CInt = 0;
const GETRUSAGE_THREAD_UPDATE_INTERRUPT: CInt = 1;
const TERMINATE_CHILD_ACTION_NONE: CInt = 0;
const TERMINATE_CHILD_ACTION_FREE_ZOMBIE: CInt = 1;
const TERMINATE_CHILD_ACTION_REPARENT_CHILD: CInt = 2;
const TERMINATE_CHILD_ACTION_REPARENT_PTRACED: CInt = 3;
const SYNC_CHILD_EVENT_ACTION_NONE: CInt = 0;
const SYNC_CHILD_EVENT_ACTION_CHILD_TOTAL: CInt = 1;
const SYNC_CHILD_EVENT_ACTION_SET_COUNT: CInt = 2;

const ITIMER_REAL: CInt = 0;
const ITIMER_VIRTUAL: CInt = 1;
const ITIMER_PROF: CInt = 2;

const CLOCK_REALTIME: CInt = 0;
const CLOCK_MONOTONIC: CInt = 1;
const CLOCK_PROCESS_CPUTIME_ID: CInt = 2;
const CLOCK_THREAD_CPUTIME_ID: CInt = 3;
const NS_PER_SEC: CLong = 1_000_000_000;
const TIME_DISPATCH_NOOP: CInt = 0;
const TIME_DISPATCH_LOCAL_REALTIME: CInt = 1;
const TIME_DISPATCH_PROCESS_CPUTIME: CInt = 2;
const TIME_DISPATCH_THREAD_CPUTIME: CInt = 3;
const TIME_DISPATCH_FORWARD: CInt = 4;
const SETTIMEOFDAY_LOG_ENTER: CInt = 1;
const SETTIMEOFDAY_LOG_ORIGIN: CInt = 2;
const SETTIMEOFDAY_LOG_EXIT: CInt = 3;

#[no_mangle]
pub extern "C" fn robust_list_len_result(len: SizeT) -> CInt {
    if len == ROBUST_LIST_HEAD_SIZE {
        0
    } else {
        -EINVAL
    }
}

#[no_mangle]
pub extern "C" fn set_robust_list_body_result(len: SizeT) -> CLong {
    robust_list_len_result(len) as CLong
}

#[no_mangle]
pub extern "C" fn tkill_tid_result(tid: CInt) -> CInt {
    if tid <= 0 { -EINVAL } else { 0 }
}

#[no_mangle]
pub extern "C" fn tgkill_target_result(tgid: CInt, tid: CInt) -> CInt {
    if tgid <= 0 || tid <= 0 { -EINVAL } else { 0 }
}

#[no_mangle]
pub extern "C" fn sigaction_validate(sig: CInt, has_act: CInt) -> CInt {
    if sig < 1 || sig > NSIG {
        return -EINVAL;
    }

    if has_act != 0 && (sig == SIGKILL || sig == SIGSTOP) {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn rt_sigprocmask_validate(
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
    has_set: CInt,
    how: CInt,
) -> CInt {
    if sigsetsize != expected_sigset_size {
        return -EINVAL;
    }

    if has_set != 0 && how != SIG_BLOCK && how != SIG_UNBLOCK && how != SIG_SETMASK {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn rt_sigprocmask_apply(
    current_mask: CULong,
    set_mask: CULong,
    has_set: CInt,
    how: CInt,
) -> CULong {
    let mut mask = current_mask;

    if has_set != 0 {
        if how == SIG_BLOCK {
            mask |= set_mask;
        } else if how == SIG_UNBLOCK {
            mask &= !set_mask;
        } else if how == SIG_SETMASK {
            mask = set_mask;
        }
    }

    mask & !(SIGKILL_MASK | SIGSTOP_MASK)
}

#[no_mangle]
pub unsafe extern "C" fn rt_sigprocmask_body_result(
    how: CInt,
    set_addr: CULong,
    oldset_addr: CULong,
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
    thread: *mut u8,
    sigmask_offset: SizeT,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    forward_fn: Option<SyscallForwardSigmaskFn>,
) -> CLong {
    let has_set = if set_addr != 0 { 1 } else { 0 };
    let error = rt_sigprocmask_validate(sigsetsize, expected_sigset_size, has_set, how);
    if error != 0 {
        return error as CLong;
    }

    let sigmaskp = field_ptr::<CULong>(thread, sigmask_offset);
    let mut wsig = 0;
    if oldset_addr != 0 {
        let Some(copy_to) = copy_to_fn else {
            return -EFAULT as CLong;
        };
        wsig = *sigmaskp;
        if copy_to(
            oldset_addr,
            (&wsig as *const CULong).cast::<u8>(),
            size_of::<CULong>(),
        ) != 0
        {
            return -EFAULT as CLong;
        }
    }

    if set_addr != 0 {
        let Some(copy_from) = copy_from_fn else {
            return -EFAULT as CLong;
        };
        if copy_from(
            (&mut wsig as *mut CULong).cast::<u8>(),
            set_addr,
            size_of::<CULong>(),
        ) != 0
        {
            return -EFAULT as CLong;
        }
    }

    *sigmaskp = rt_sigprocmask_apply(*sigmaskp, wsig, has_set, how);
    if let Some(forward) = forward_fn {
        forward(*sigmaskp);
    }
    0
}

#[no_mangle]
pub extern "C" fn rt_sigpending_size_result(
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
) -> CInt {
    if sigsetsize > expected_sigset_size {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn signalfd4_sigsetsize_result(
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
) -> CInt {
    if sigsetsize != expected_sigset_size {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn signalfd4_flags_result(flags: CInt) -> CInt {
    if (flags & !(SFD_NONBLOCK | SFD_CLOEXEC)) != 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn signalfd_body_result() -> CLong {
    -(EOPNOTSUPP as CLong)
}

#[inline(always)]
unsafe fn thread_sigmask_ptr(thread: *mut c_void, sigmask_offset: SizeT) -> *mut CULong {
    thread.cast::<u8>().add(sigmask_offset).cast::<CULong>()
}

#[no_mangle]
pub unsafe extern "C" fn syscall_temp_sigmask_body_result(
    set_addr: CULong,
    thread: *mut c_void,
    sigmask_offset: SizeT,
    syscall_nr: CInt,
    ctx: *mut c_void,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    if thread.is_null() {
        return -(EINVAL as CLong);
    }
    let Some(forward) = forward_fn else {
        return -(EINVAL as CLong);
    };

    let sigmaskp = thread_sigmask_ptr(thread, sigmask_offset);
    let oldset = *sigmaskp;
    if set_addr != 0 {
        let Some(copy_from) = copy_from_fn else {
            return -(EFAULT as CLong);
        };
        let mut wset: CULong = 0;
        if copy_from(
            (&mut wset as *mut CULong).cast::<u8>(),
            set_addr,
            size_of::<CULong>(),
        ) != 0
        {
            return -(EFAULT as CLong);
        }
        *sigmaskp = wset;
    }

    let rc = forward(syscall_nr, ctx);
    *sigmaskp = oldset;
    rc
}

#[no_mangle]
pub unsafe extern "C" fn pselect6_sigmask_body_result(
    set_ptr_addr: CULong,
    thread: *mut c_void,
    sigmask_offset: SizeT,
    syscall_nr: CInt,
    ctx: *mut c_void,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    let mut set_addr: CULong = 0;
    if set_ptr_addr != 0 {
        let Some(copy_from) = copy_from_fn else {
            return -(EFAULT as CLong);
        };
        if copy_from(
            (&mut set_addr as *mut CULong).cast::<u8>(),
            set_ptr_addr,
            size_of::<CULong>(),
        ) != 0
        {
            return -(EFAULT as CLong);
        }
    }

    syscall_temp_sigmask_body_result(
        set_addr,
        thread,
        sigmask_offset,
        syscall_nr,
        ctx,
        copy_from_fn,
        forward_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn rt_sigpending_body_result(
    set_addr: CULong,
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
    thread: *mut c_void,
    pending_mask_fn: Option<SyscallPendingMaskFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    let error = rt_sigpending_size_result(sigsetsize, expected_sigset_size);
    if error != 0 {
        return error as CLong;
    }
    if set_addr == 0 || thread.is_null() {
        return -(EFAULT as CLong);
    }
    let (Some(pending_mask), Some(copy_to)) = (pending_mask_fn, copy_to_fn) else {
        return -(EFAULT as CLong);
    };

    let pending = pending_mask(thread);
    if copy_to(
        set_addr,
        (&pending as *const CULong).cast::<u8>(),
        size_of::<CULong>(),
    ) != 0
    {
        return -(EFAULT as CLong);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn signalfd4_body_result(
    fd: CInt,
    mask_addr: CULong,
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
    flags: CInt,
    thread: *mut c_void,
    syscall_nr: CInt,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    create_fn: Option<SyscallSignalfdCreateFn>,
    publish_fn: Option<SyscallSignalfdPublishFn>,
) -> CLong {
    let error = signalfd4_sigsetsize_result(sigsetsize, expected_sigset_size);
    if error != 0 {
        return error as CLong;
    }
    let Some(copy_from) = copy_from_fn else {
        return -(EFAULT as CLong);
    };
    let mut mask: CULong = 0;
    if mask_addr == 0
        || copy_from(
            (&mut mask as *mut CULong).cast::<u8>(),
            mask_addr,
            size_of::<CULong>(),
        ) != 0
    {
        return -(EFAULT as CLong);
    }
    let error = signalfd4_flags_result(flags);
    if error != 0 {
        return error as CLong;
    }
    if thread.is_null() {
        return -(EINVAL as CLong);
    }
    let Some(publish) = publish_fn else {
        return -(EINVAL as CLong);
    };

    let mut out_fd = fd;
    let mut create = 0;
    if fd == -1 {
        let Some(create_fd) = create_fn else {
            return -(EINVAL as CLong);
        };
        let created = create_fd(syscall_nr, flags);
        if created < 0 {
            return created;
        }
        out_fd = created as CInt;
        create = 1;
    }

    publish(thread, out_fd, &mask as *const CULong, create)
}

#[no_mangle]
pub extern "C" fn syscall_refresh_cred_needed_result(rc: CLong) -> CInt {
    (rc == 0) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_getpid_result(pid: CInt) -> CInt {
    pid
}

#[no_mangle]
pub extern "C" fn syscall_getppid_result(ppid: CInt) -> CInt {
    ppid
}

#[no_mangle]
pub extern "C" fn syscall_gettid_result(tid: CInt) -> CInt {
    tid
}

#[no_mangle]
pub extern "C" fn syscall_set_tid_address_return_result(pid: CInt) -> CInt {
    pid
}

#[inline(always)]
unsafe fn field_ptr<T>(base: *mut u8, offset: SizeT) -> *mut T {
    base.add(offset).cast::<T>()
}

#[inline(always)]
unsafe fn ptrace_copy_bytes(dst: *mut u8, src: *const u8, bytes: SizeT) {
    let mut offset = 0;
    while offset < bytes {
        dst.add(offset)
            .write_volatile(src.add(offset).read_volatile());
        offset += 1;
    }
}

#[inline(always)]
unsafe fn thread_process(thread: *mut u8, proc_offset: SizeT) -> *mut u8 {
    *field_ptr::<*mut u8>(thread, proc_offset)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_getpid_body_result(
    thread: *mut u8,
    proc_offset: SizeT,
    pid_offset: SizeT,
) -> CLong {
    let proc = thread_process(thread, proc_offset);
    *field_ptr::<CInt>(proc, pid_offset) as CLong
}

#[no_mangle]
pub unsafe extern "C" fn syscall_getppid_body_result(
    thread: *mut u8,
    proc_offset: SizeT,
    ppid_parent_offset: SizeT,
    pid_offset: SizeT,
) -> CLong {
    let proc = thread_process(thread, proc_offset);
    let parent = *field_ptr::<*mut u8>(proc, ppid_parent_offset);
    *field_ptr::<CInt>(parent, pid_offset) as CLong
}

#[no_mangle]
pub unsafe extern "C" fn syscall_gettid_body_result(thread: *mut u8, tid_offset: SizeT) -> CLong {
    *field_ptr::<CInt>(thread, tid_offset) as CLong
}

#[no_mangle]
pub unsafe extern "C" fn syscall_set_tid_address_body_result(
    thread: *mut u8,
    clear_child_tid_offset: SizeT,
    proc_offset: SizeT,
    pid_offset: SizeT,
    clear_child_tid: *mut CInt,
) -> CLong {
    *field_ptr::<*mut CInt>(thread, clear_child_tid_offset) = clear_child_tid;
    syscall_getpid_body_result(thread, proc_offset, pid_offset)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_get_process_id_field_result(
    thread: *mut u8,
    proc_offset: SizeT,
    field_offset: SizeT,
) -> CLong {
    let proc = thread_process(thread, proc_offset);
    *field_ptr::<CInt>(proc, field_offset) as CLong
}

#[no_mangle]
pub unsafe extern "C" fn syscall_getresid_body_result(
    thread: *mut u8,
    proc_offset: SizeT,
    first_offset: SizeT,
    second_offset: SizeT,
    third_offset: SizeT,
    first_user_addr: CULong,
    second_user_addr: CULong,
    third_user_addr: CULong,
    copy_int_fn: SyscallCopyIntToUserFn,
) -> CLong {
    let proc = thread_process(thread, proc_offset);

    if copy_int_fn(first_user_addr, field_ptr::<CInt>(proc, first_offset)) != 0 {
        return -(EFAULT as CLong);
    }
    if copy_int_fn(second_user_addr, field_ptr::<CInt>(proc, second_offset)) != 0 {
        return -(EFAULT as CLong);
    }
    if copy_int_fn(third_user_addr, field_ptr::<CInt>(proc, third_offset)) != 0 {
        return -(EFAULT as CLong);
    }

    0
}

#[inline(always)]
unsafe fn syscall_process_id(thread: *mut u8, proc_offset: SizeT, pid_offset: SizeT) -> CInt {
    let proc = thread_process(thread, proc_offset);
    *field_ptr::<CInt>(proc, pid_offset)
}

#[inline(always)]
fn syscall_make_kill_siginfo(sig: CInt, code: CInt, pid: CInt) -> SigInfo {
    SigInfo {
        si_signo: sig,
        si_errno: 0,
        si_code: code,
        padding: 0,
        sifields: crate::abi::SigInfoFields {
            kill: ManuallyDrop::new(SigInfoKill {
                si_pid: pid,
                si_uid: 0,
            }),
        },
    }
}

#[no_mangle]
pub unsafe extern "C" fn syscall_kill_body_result(
    thread: *mut u8,
    proc_offset: SizeT,
    pid_offset: SizeT,
    pid: CInt,
    sig: CInt,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
) -> CLong {
    let Some(do_kill) = do_kill_fn else {
        return -(EINVAL as CLong);
    };
    let current_pid = syscall_process_id(thread, proc_offset, pid_offset);
    let info = syscall_make_kill_siginfo(sig, 0, current_pid);

    do_kill(thread.cast::<c_void>(), pid, -1, sig, &info, 0)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_tgkill_body_result(
    thread: *mut u8,
    proc_offset: SizeT,
    pid_offset: SizeT,
    tgid: CInt,
    tid: CInt,
    sig: CInt,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
) -> CLong {
    let error = tgkill_target_result(tgid, tid);
    if error != 0 {
        return error as CLong;
    }
    let Some(do_kill) = do_kill_fn else {
        return -(EINVAL as CLong);
    };
    let current_pid = syscall_process_id(thread, proc_offset, pid_offset);
    let info = syscall_make_kill_siginfo(sig, -6, current_pid);

    do_kill(thread.cast::<c_void>(), tgid, tid, sig, &info, 0)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_tkill_body_result(
    thread: *mut u8,
    proc_offset: SizeT,
    pid_offset: SizeT,
    tid: CInt,
    sig: CInt,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
) -> CLong {
    let error = tkill_tid_result(tid);
    if error != 0 {
        return error as CLong;
    }
    let Some(do_kill) = do_kill_fn else {
        return -(EINVAL as CLong);
    };
    let current_pid = syscall_process_id(thread, proc_offset, pid_offset);
    let info = syscall_make_kill_siginfo(sig, -6, current_pid);

    do_kill(thread.cast::<c_void>(), -1, tid, sig, &info, 0)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_forward_refresh_cred_body_result(
    syscall_nr: CInt,
    ctx: *mut c_void,
    forward_fn: Option<SyscallForwardContextFn>,
    refresh_fn: Option<SyscallRefreshCredFn>,
) -> CLong {
    let Some(forward) = forward_fn else {
        return -(EINVAL as CLong);
    };
    let rc = forward(syscall_nr, ctx);
    if syscall_refresh_cred_needed_result(rc) != 0 {
        let Some(refresh) = refresh_fn else {
            return -(EINVAL as CLong);
        };
        refresh();
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn syscall_setfsid_body_result(
    id: CInt,
    syscall_nr: CInt,
    do_syscall_fn: Option<SyscallDoSyscall2Fn>,
    refresh_fn: Option<SyscallRefreshCredFn>,
) -> CULong {
    let Some(do_syscall) = do_syscall_fn else {
        return (-(EINVAL as CLong)) as CULong;
    };
    let new_id = do_syscall(syscall_nr, id as CULong, 0) as CULong;
    let Some(refresh) = refresh_fn else {
        return (-(EINVAL as CLong)) as CULong;
    };
    refresh();
    new_id
}

#[no_mangle]
pub unsafe extern "C" fn getcred_body_result(
    raw_buf: *mut CInt,
    page_mask: CULong,
    syscall_nr: CInt,
    virt_to_phys_fn: Option<SyscallVirtToPhysFn>,
    processor_id_fn: Option<SyscallGetCpuFn>,
    do_syscall_fn: Option<SyscallRequestCallFn>,
) -> *mut CInt {
    if raw_buf.is_null() {
        return null_mut();
    }
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return null_mut();
    };
    let Some(processor_id) = processor_id_fn else {
        return null_mut();
    };
    let Some(do_syscall) = do_syscall_fn else {
        return null_mut();
    };

    let alternate_buf = raw_buf.add(8);
    let selected_buf = if ((raw_buf as CULong) ^ (alternate_buf as CULong)) & page_mask != 0 {
        alternate_buf
    } else {
        raw_buf
    };

    let mut request = MaybeUninit::<SyscallRequest>::zeroed();
    let requestp = request.as_mut_ptr();
    (*requestp).number = syscall_nr as CULong;
    (*requestp).args[0] = virt_to_phys(selected_buf.cast::<c_void>());
    (*requestp).args[1] = 1;
    do_syscall(requestp, processor_id());

    selected_buf
}

#[no_mangle]
pub unsafe extern "C" fn syscall_refresh_cred_fields_body_result(
    thread: *mut c_void,
    scratch: *mut CInt,
    thread_proc_offset: SizeT,
    field0_offset: SizeT,
    field1_offset: SizeT,
    field2_offset: SizeT,
    field3_offset: SizeT,
    value0_index: SizeT,
    value1_index: SizeT,
    value2_index: SizeT,
    value3_index: SizeT,
    getcred_fn: Option<SyscallGetcredFn>,
) -> CInt {
    if thread.is_null() || scratch.is_null() {
        return -EFAULT;
    }
    let Some(getcred) = getcred_fn else {
        return -EINVAL;
    };
    let values = getcred(scratch);
    if values.is_null() {
        return -EFAULT;
    }

    let proc = *(thread
        .cast::<u8>()
        .add(thread_proc_offset)
        .cast::<*mut c_void>());
    if proc.is_null() {
        return -EFAULT;
    }
    let proc_bytes = proc.cast::<u8>();
    write(
        proc_bytes.add(field0_offset).cast::<CInt>(),
        *values.add(value0_index),
    );
    write(
        proc_bytes.add(field1_offset).cast::<CInt>(),
        *values.add(value1_index),
    );
    write(
        proc_bytes.add(field2_offset).cast::<CInt>(),
        *values.add(value2_index),
    );
    write(
        proc_bytes.add(field3_offset).cast::<CInt>(),
        *values.add(value3_index),
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn syscall_times_body_result(
    thread: *mut u8,
    buf_addr: CULong,
    gettime_local_support: CInt,
    offsets: *const SyscallTimesOffsets,
    tsc_to_ts_fn: Option<SyscallTscToTsFn>,
    timespec_to_jiffy_fn: Option<SyscallTimespecToJiffyFn>,
    ts_add_fn: Option<SyscallTsAddFn>,
    gettime_fn: Option<SyscallGettimeFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    let Some(offsets) = offsets.as_ref() else {
        return -(EINVAL as CLong);
    };
    let Some(tsc_to_ts) = tsc_to_ts_fn else {
        return -(EINVAL as CLong);
    };
    let Some(timespec_to_jiffy) = timespec_to_jiffy_fn else {
        return -(EINVAL as CLong);
    };
    let Some(ts_add) = ts_add_fn else {
        return -(EINVAL as CLong);
    };
    let Some(copy_to) = copy_to_fn else {
        return -(EINVAL as CLong);
    };

    let proc = thread_process(thread, offsets.thread_proc_offset);
    let mut ats = MaybeUninit::<TimeSpec>::uninit();
    let ats_ptr = ats.as_mut_ptr();
    let mut mytms = SyscallTimesTms {
        tms_utime: 0,
        tms_stime: 0,
        tms_cutime: 0,
        tms_cstime: 0,
    };

    tsc_to_ts(
        *field_ptr::<CULong>(thread, offsets.thread_user_tsc_offset),
        ats_ptr,
    );
    mytms.tms_utime = timespec_to_jiffy(ats.as_ptr());

    tsc_to_ts(
        *field_ptr::<CULong>(thread, offsets.thread_system_tsc_offset),
        ats_ptr,
    );
    mytms.tms_stime = timespec_to_jiffy(ats.as_ptr());

    let proc_utime = read_timespec(proc, offsets.proc_utime_offset);
    write_volatile(
        core::ptr::addr_of_mut!((*ats_ptr).tv_sec),
        proc_utime.tv_sec,
    );
    write_volatile(
        core::ptr::addr_of_mut!((*ats_ptr).tv_nsec),
        proc_utime.tv_nsec,
    );
    ts_add(
        ats_ptr,
        field_ptr::<TimeSpec>(proc, offsets.proc_utime_children_offset),
    );
    mytms.tms_cutime = timespec_to_jiffy(ats.as_ptr());

    let proc_stime = read_timespec(proc, offsets.proc_stime_offset);
    write_volatile(
        core::ptr::addr_of_mut!((*ats_ptr).tv_sec),
        proc_stime.tv_sec,
    );
    write_volatile(
        core::ptr::addr_of_mut!((*ats_ptr).tv_nsec),
        proc_stime.tv_nsec,
    );
    ts_add(
        ats_ptr,
        field_ptr::<TimeSpec>(proc, offsets.proc_stime_children_offset),
    );
    mytms.tms_cstime = timespec_to_jiffy(ats.as_ptr());

    if copy_to(
        buf_addr,
        (&mytms as *const SyscallTimesTms).cast::<u8>(),
        size_of::<SyscallTimesTms>(),
    ) != 0
    {
        return -(EFAULT as CLong);
    }

    if gettime_local_support != 0 {
        let Some(gettime) = gettime_fn else {
            return -(EINVAL as CLong);
        };
        gettime(ats_ptr);
    } else {
        write_volatile(core::ptr::addr_of_mut!((*ats_ptr).tv_sec), 0);
        write_volatile(core::ptr::addr_of_mut!((*ats_ptr).tv_nsec), 0);
    }

    timespec_to_jiffy(ats.as_ptr()) as CLong
}

#[no_mangle]
pub extern "C" fn syscall_use_requester_tid_result(
    syscall_nr: CInt,
    arg0: CULong,
    sched_setaffinity_nr: CInt,
) -> CInt {
    (syscall_nr == sched_setaffinity_nr && arg0 == 0) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_target_tid_result(use_requester_tid: CInt, current_tid: CInt) -> CInt {
    if use_requester_tid != 0 {
        current_tid
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn syscall_send_prepare_result(
    request: *mut SyscallRequest,
    response: *mut SyscallResponse,
) -> CInt {
    if request.is_null() || response.is_null() {
        return -EINVAL;
    }

    write(core::ptr::addr_of_mut!((*response).status), 0);
    write(core::ptr::addr_of_mut!((*request).valid), 0);

    0
}

#[no_mangle]
pub unsafe extern "C" fn syscall_request_copy_result(
    dst: *mut SyscallRequest,
    src: *const SyscallRequest,
) -> CInt {
    if dst.is_null() || src.is_null() {
        return -EINVAL;
    }

    write(core::ptr::addr_of_mut!((*dst).rtid), (*src).rtid);
    write(core::ptr::addr_of_mut!((*dst).ttid), (*src).ttid);
    write(core::ptr::addr_of_mut!((*dst).valid), (*src).valid);
    write(core::ptr::addr_of_mut!((*dst).number), (*src).number);
    write(core::ptr::addr_of_mut!((*dst).args[0]), (*src).args[0]);
    write(core::ptr::addr_of_mut!((*dst).args[1]), (*src).args[1]);
    write(core::ptr::addr_of_mut!((*dst).args[2]), (*src).args[2]);
    write(core::ptr::addr_of_mut!((*dst).args[3]), (*src).args[3]);
    write(core::ptr::addr_of_mut!((*dst).args[4]), (*src).args[4]);
    write(core::ptr::addr_of_mut!((*dst).args[5]), (*src).args[5]);

    0
}

#[no_mangle]
pub unsafe extern "C" fn syscall_generic_forwarding_body_result(
    request: *mut SyscallRequest,
    n: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
    arg3: CULong,
    arg4: CULong,
    arg5: CULong,
    cpu: CInt,
    do_syscall_fn: Option<SyscallRequestCallFn>,
) -> CLong {
    let Some(do_syscall_fn) = do_syscall_fn else {
        return -(EINVAL as CLong);
    };
    if request.is_null() {
        return -(EINVAL as CLong);
    }

    write(addr_of_mut!((*request).number), n as CULong);
    write(addr_of_mut!((*request).args[0]), arg0);
    write(addr_of_mut!((*request).args[1]), arg1);
    write(addr_of_mut!((*request).args[2]), arg2);
    write(addr_of_mut!((*request).args[3]), arg3);
    write(addr_of_mut!((*request).args[4]), arg4);
    write(addr_of_mut!((*request).args[5]), arg5);

    do_syscall_fn(request, cpu)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_packet_traditional_prepare_result(
    packet: *mut IkcScdPacket,
    msg: CInt,
    cpu_ref: CInt,
    pid: CInt,
    resp_pa: CULong,
) -> CInt {
    if packet.is_null() {
        return -EINVAL;
    }

    write(core::ptr::addr_of_mut!((*packet).msg), msg);
    let traditional = core::ptr::addr_of_mut!((*packet).body).cast::<IkcScdPacketTraditional>();
    write(core::ptr::addr_of_mut!((*traditional).ref_), cpu_ref);
    write(core::ptr::addr_of_mut!((*traditional).pid), pid);
    write(core::ptr::addr_of_mut!((*traditional).resp_pa), resp_pa);

    0
}

unsafe fn zero_syscall_ikc_scd_packet(packet: *mut IkcScdPacket) {
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
pub unsafe extern "C" fn syscall_eventfd_packet_prepare_result(
    packet: *mut IkcScdPacket,
    msg: CInt,
    eventfd_type: CInt,
) -> CInt {
    if packet.is_null() {
        return -EINVAL;
    }

    zero_syscall_ikc_scd_packet(packet);
    write(core::ptr::addr_of_mut!((*packet).msg), msg);
    write(
        core::ptr::addr_of_mut!((*packet).body.eventfd_type),
        eventfd_type,
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn syscall_eventfd_send_result(
    channel: *mut c_void,
    msg: CInt,
    eventfd_type: CInt,
    send_fn: Option<SyscallIkcSendFn>,
) -> CInt {
    let Some(send) = send_fn else {
        return -EINVAL;
    };

    let mut packet = MaybeUninit::<IkcScdPacket>::uninit();
    let prep_rc = syscall_eventfd_packet_prepare_result(packet.as_mut_ptr(), msg, eventfd_type);
    if prep_rc != 0 {
        return prep_rc;
    }

    send(channel, packet.as_mut_ptr().cast::<c_void>(), 0)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_log_budget_result(
    pid: CInt,
    last_pidp: *mut CInt,
    log_countp: *mut CInt,
    limit: CInt,
) -> CInt {
    if last_pidp.is_null() || log_countp.is_null() {
        return -EINVAL;
    }

    let mut log_count = *log_countp;
    if *last_pidp != pid {
        write(last_pidp, pid);
        write(log_countp, 0);
        log_count = 0;
    }

    if limit > 0 && log_count < limit {
        write(log_countp, log_count + 1);
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn syscall_reject_after_exit_result(
    process_status: CInt,
    syscall_nr: CInt,
    exit_nr: CInt,
    exit_group_nr: CInt,
) -> CInt {
    (process_status == PS_EXITED && syscall_nr != exit_nr && syscall_nr != exit_group_nr) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_offload_spin_without_schedule_result(
    no_preempt: CInt,
    tid: CInt,
) -> CInt {
    (no_preempt != 0 || tid == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn syscall_offload_prepare_result(
    request: *mut SyscallRequest,
    response: *mut SyscallResponse,
    current_tid: CInt,
    syscall_nr: CInt,
    arg0: CULong,
    sched_setaffinity_nr: CInt,
    spinning_status: CULong,
) -> CInt {
    if request.is_null() || response.is_null() {
        return -EINVAL;
    }

    let use_requester_tid =
        syscall_use_requester_tid_result(syscall_nr, arg0, sched_setaffinity_nr);
    let target_tid = syscall_target_tid_result(use_requester_tid, current_tid);

    write(core::ptr::addr_of_mut!((*request).rtid), current_tid);
    write(core::ptr::addr_of_mut!((*request).ttid), target_tid);
    write(
        core::ptr::addr_of_mut!((*response).req_thread_status),
        spinning_status,
    );
    write(
        core::ptr::addr_of_mut!((*response).pde_data),
        core::ptr::null_mut(),
    );

    use_requester_tid
}

#[no_mangle]
pub extern "C" fn syscall_preempt_disable_needed_result(rtid: CInt) -> CInt {
    (rtid == -1) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_proxy_dead_result(rc: CLong) -> CInt {
    (rc == -ERESTARTSYS) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_tofu_post_reply_candidate_result(
    syscall_nr: CInt,
    rc: CLong,
    ioctl_nr: CInt,
    openat_nr: CInt,
) -> CInt {
    ((syscall_nr == ioctl_nr && rc == 0) || (syscall_nr == openat_nr && rc > 0)) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_profile_event_needed_result(syscall_nr: CInt, profile_max: CInt) -> CInt {
    (syscall_nr < profile_max) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_offload_counted_result(syscall_nr: CInt, exit_group_nr: CInt) -> CInt {
    (syscall_nr != exit_group_nr) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_nested_dispatch_valid_result(
    syscall_nr: CInt,
    syscall_count: CInt,
    has_handler: CInt,
) -> CInt {
    (syscall_nr >= 0 && syscall_nr < syscall_count && has_handler != 0) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_nested_rt_sigaction_index_result(sig: CInt, nsig: CInt) -> CInt {
    let index = sig - 1;

    if index < 0 || index >= nsig {
        -EINVAL
    } else {
        index
    }
}

#[no_mangle]
pub unsafe extern "C" fn syscall_nested_response_prepare_result(
    request: *mut SyscallRequest,
    response: *mut SyscallResponse,
    response_nr: CULong,
    syscall_ret: CULong,
    current_tid: CInt,
    service_tid: CInt,
    spinning_status: CULong,
) -> CInt {
    if request.is_null() || response.is_null() {
        return -EINVAL;
    }

    write(core::ptr::addr_of_mut!((*request).number), response_nr);
    write(core::ptr::addr_of_mut!((*request).args[1]), syscall_ret);
    write(core::ptr::addr_of_mut!((*request).rtid), current_tid);
    write(core::ptr::addr_of_mut!((*request).ttid), service_tid);
    write(
        core::ptr::addr_of_mut!((*response).req_thread_status),
        spinning_status,
    );

    0
}

#[no_mangle]
pub extern "C" fn setpgid_normalize_pid(current_pid: CInt, pid: CInt) -> CInt {
    if pid == 0 { current_pid } else { pid }
}

#[no_mangle]
pub extern "C" fn setpgid_normalize_pgid(pid: CInt, pgid: CInt) -> CInt {
    if pgid == 0 { pid } else { pgid }
}

#[no_mangle]
pub extern "C" fn setpgid_execed_result(execed: CInt) -> CInt {
    if execed != 0 { -EACCES } else { 0 }
}

#[no_mangle]
pub unsafe extern "C" fn syscall_setpgid_body_result(
    thread: *mut u8,
    pid: CInt,
    pgid: CInt,
    syscall_nr: CInt,
    ctx: *mut c_void,
    offsets: *const SyscallSetpgidOffsets,
    lock_arg: *mut c_void,
    find_fn: Option<SyscallFindProcessFn>,
    unlock_fn: Option<SyscallProcessUnlockFn>,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    let Some(offsets) = offsets.as_ref() else {
        return -(EINVAL as CLong);
    };
    let proc = thread_process(thread, offsets.thread_proc_offset);
    let current_pid = *field_ptr::<CInt>(proc, offsets.proc_pid_offset);
    let pid = setpgid_normalize_pid(current_pid, pid);
    let pgid = setpgid_normalize_pgid(pid, pgid);

    let Some(find_process) = find_fn else {
        return -(EINVAL as CLong);
    };
    let Some(process_unlock) = unlock_fn else {
        return -(EINVAL as CLong);
    };

    if current_pid != pid {
        let target = find_process(pid, lock_arg);
        if target.is_null() {
            return -(ESRCH as CLong);
        }

        let rc = setpgid_execed_result(*field_ptr::<CInt>(
            target.cast::<u8>(),
            offsets.proc_execed_offset,
        ));
        if rc != 0 {
            process_unlock(target, lock_arg);
            return rc as CLong;
        }
        process_unlock(target, lock_arg);
    }

    let Some(forward) = forward_fn else {
        return -(EINVAL as CLong);
    };
    let rc = forward(syscall_nr, ctx);
    if rc == 0 {
        let target = find_process(pid, lock_arg);
        if !target.is_null() {
            *field_ptr::<CInt>(target.cast::<u8>(), offsets.proc_pgid_offset) = pgid;
            process_unlock(target, lock_arg);
        }
    }

    rc
}

#[no_mangle]
pub unsafe extern "C" fn syscall_setrlimit_body_result(
    resource: CInt,
    new_limit_addr: CULong,
    do_prlimit_fn: Option<SyscallDoPrlimit64Fn>,
) -> CLong {
    let Some(do_prlimit) = do_prlimit_fn else {
        return -(EINVAL as CLong);
    };

    do_prlimit(0, resource, new_limit_addr, 0)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_getrlimit_body_result(
    resource: CInt,
    old_limit_addr: CULong,
    do_prlimit_fn: Option<SyscallDoPrlimit64Fn>,
) -> CLong {
    let Some(do_prlimit) = do_prlimit_fn else {
        return -(EINVAL as CLong);
    };

    do_prlimit(0, resource, 0, old_limit_addr)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_prlimit64_body_result(
    pid: CInt,
    resource: CInt,
    new_limit_addr: CULong,
    old_limit_addr: CULong,
    do_prlimit_fn: Option<SyscallDoPrlimit64Fn>,
) -> CLong {
    let Some(do_prlimit) = do_prlimit_fn else {
        return -(EINVAL as CLong);
    };

    do_prlimit(pid, resource, new_limit_addr, old_limit_addr)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_sysinfo_body_result(
    sysinfo_addr: CULong,
    totalram: CULong,
    freeram: CULong,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    let Some(copy_to) = copy_to_fn else {
        return -(EINVAL as CLong);
    };
    let mut info = MaybeUninit::<SysInfo>::uninit();
    let info_ptr = info.as_mut_ptr();
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).uptime), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).loads[0]), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).loads[1]), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).loads[2]), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).totalram), totalram);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).freeram), freeram);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).sharedram), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).bufferram), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).totalswap), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).freeswap), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).procs), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).padding[0]), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).padding[1]), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).padding[2]), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).padding[3]), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).padding[4]), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).padding[5]), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).totalhigh), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).freehigh), 0);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).mem_unit), 1);
    write_volatile(core::ptr::addr_of_mut!((*info_ptr).tail_padding), 0);

    if copy_to(
        sysinfo_addr,
        info.as_ptr().cast::<u8>(),
        size_of::<SysInfo>(),
    ) != 0
    {
        return -(EFAULT as CLong);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn syscall_get_cpu_id_body_result(
    get_cpu_fn: Option<SyscallGetCpuFn>,
) -> CLong {
    let Some(get_cpu) = get_cpu_fn else {
        return -(EINVAL as CLong);
    };

    get_cpu() as CLong
}

#[no_mangle]
pub unsafe extern "C" fn syscall_mlockall_body_result(
    thread: *mut u8,
    flags: CInt,
    offsets: *const SyscallMlockallOffsets,
    log_fn: Option<SyscallLogIntFn>,
) -> CLong {
    let Some(offsets) = offsets.as_ref() else {
        return -(EINVAL as CLong);
    };
    if offsets.memlock_resource < 0 {
        return -(EINVAL as CLong);
    }

    let proc = thread_process(thread, offsets.thread_proc_offset);
    let is_privileged = (*field_ptr::<CInt>(proc, offsets.proc_euid_offset) == 0) as CInt;
    let memlock_cur = *field_ptr::<CULong>(
        proc,
        offsets.proc_rlimit_offset + offsets.memlock_resource as SizeT * offsets.rlimit_entry_size,
    );
    let rc = mlockall_policy_result(flags, is_privileged, memlock_cur);
    if let Some(log) = log_fn {
        log(flags, rc);
    }

    rc as CLong
}

#[no_mangle]
pub unsafe extern "C" fn syscall_munlockall_body_result(log_fn: Option<SyscallLogIntFn>) -> CLong {
    if let Some(log) = log_fn {
        log(0, 0);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn syscall_getcpu_body_result(
    cpup_addr: CULong,
    nodep_addr: CULong,
    cpu: CInt,
    node: CInt,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    let Some(copy_to) = copy_to_fn else {
        return -(EINVAL as CLong);
    };

    if cpup_addr != 0 {
        let rc = copy_to(
            cpup_addr,
            (&cpu as *const CInt).cast::<u8>(),
            size_of::<CInt>(),
        );
        if rc != 0 {
            return rc;
        }
    }

    if nodep_addr != 0 {
        let rc = copy_to(
            nodep_addr,
            (&node as *const CInt).cast::<u8>(),
            size_of::<CInt>(),
        );
        if rc != 0 {
            return rc;
        }
    }

    0
}

unsafe fn syscall_mckfd_proc(thread: *mut c_void, offsets: *const SyscallMckfdOffsets) -> *mut u8 {
    if thread.is_null() || offsets.is_null() {
        return core::ptr::null_mut();
    }

    *field_ptr::<*mut u8>(thread.cast::<u8>(), (*offsets).thread_proc_offset)
}

unsafe fn syscall_mckfd_lock_ptr(
    proc: *mut u8,
    offsets: *const SyscallMckfdOffsets,
) -> *mut c_void {
    field_ptr::<c_void>(proc, (*offsets).proc_mckfd_lock_offset)
}

unsafe fn syscall_mckfd_headp(proc: *mut u8, offsets: *const SyscallMckfdOffsets) -> *mut *mut u8 {
    field_ptr::<*mut u8>(proc, (*offsets).proc_mckfd_offset)
}

unsafe fn syscall_mckfd_next(entry: *mut u8, offsets: *const SyscallMckfdOffsets) -> *mut u8 {
    *field_ptr::<*mut u8>(entry, (*offsets).mckfd_next_offset)
}

unsafe fn syscall_mckfd_set_next(
    entry: *mut u8,
    offsets: *const SyscallMckfdOffsets,
    next: *mut u8,
) {
    *field_ptr::<*mut u8>(entry, (*offsets).mckfd_next_offset) = next;
}

unsafe fn syscall_mckfd_find(
    proc: *mut u8,
    fd: CInt,
    offsets: *const SyscallMckfdOffsets,
) -> *mut u8 {
    let mut cur = *syscall_mckfd_headp(proc, offsets);

    while !cur.is_null() {
        if *field_ptr::<CInt>(cur, (*offsets).mckfd_fd_offset) == fd {
            return cur;
        }
        cur = syscall_mckfd_next(cur, offsets);
    }

    core::ptr::null_mut()
}

unsafe fn syscall_mckfd_find_locked(
    thread: *mut c_void,
    fd: CInt,
    offsets: *const SyscallMckfdOffsets,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> *mut u8 {
    let proc = syscall_mckfd_proc(thread, offsets);
    let Some(lock_fn) = lock_fn else {
        return core::ptr::null_mut();
    };
    let Some(unlock_fn) = unlock_fn else {
        return core::ptr::null_mut();
    };
    if proc.is_null() {
        return core::ptr::null_mut();
    }

    let lock = syscall_mckfd_lock_ptr(proc, offsets);
    let irqstate = lock_fn(lock);
    let fdp = syscall_mckfd_find(proc, fd, offsets);
    unlock_fn(lock, irqstate);
    fdp
}

unsafe fn syscall_mckfd_long_callback(entry: *mut u8, offset: SizeT) -> Option<SyscallMckfdLongFn> {
    *field_ptr::<Option<SyscallMckfdLongFn>>(entry, offset)
}

unsafe fn syscall_mckfd_int_callback(entry: *mut u8, offset: SizeT) -> Option<SyscallMckfdIntFn> {
    *field_ptr::<Option<SyscallMckfdIntFn>>(entry, offset)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_read_body_result(
    thread: *mut c_void,
    fd: CInt,
    syscall_nr: CInt,
    ctx: *mut c_void,
    offsets: *const SyscallMckfdOffsets,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    let Some(forward_fn) = forward_fn else {
        return -(EINVAL as CLong);
    };
    if offsets.is_null() || lock_fn.is_none() || unlock_fn.is_none() {
        return -(EINVAL as CLong);
    }

    let fdp = syscall_mckfd_find_locked(thread, fd, offsets, lock_fn, unlock_fn);
    if !fdp.is_null() {
        if let Some(read_fn) = syscall_mckfd_long_callback(fdp, (*offsets).mckfd_read_cb_offset) {
            return read_fn(fdp.cast::<c_void>(), ctx);
        }
    }

    forward_fn(syscall_nr, ctx)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_ioctl_body_result(
    thread: *mut c_void,
    fd: CInt,
    cmd: CULong,
    arg: CULong,
    syscall_nr: CInt,
    ctx: *mut c_void,
    offsets: *const SyscallMckfdOffsets,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
    forward_fn: Option<SyscallForwardContextFn>,
    tofu_fn: Option<SyscallTofuIoctlFn>,
) -> CLong {
    let Some(forward_fn) = forward_fn else {
        return -(EINVAL as CLong);
    };
    if offsets.is_null() || lock_fn.is_none() || unlock_fn.is_none() {
        return -(EINVAL as CLong);
    }

    let fdp = syscall_mckfd_find_locked(thread, fd, offsets, lock_fn, unlock_fn);
    if let Some(tofu_fn) = tofu_fn {
        let mut handled = 0;
        let tofu_rc = tofu_fn(thread, fd, cmd, arg, &mut handled);
        if handled != 0 {
            return tofu_rc;
        }
    }

    if !fdp.is_null() {
        if let Some(ioctl_fn) = syscall_mckfd_int_callback(fdp, (*offsets).mckfd_ioctl_cb_offset) {
            return ioctl_fn(fdp.cast::<c_void>(), ctx) as CLong;
        }
    }

    forward_fn(syscall_nr, ctx)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_fcntl_body_result(
    thread: *mut c_void,
    fd: CInt,
    syscall_nr: CInt,
    ctx: *mut c_void,
    offsets: *const SyscallMckfdOffsets,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    let Some(forward_fn) = forward_fn else {
        return -(EINVAL as CLong);
    };
    if offsets.is_null() || lock_fn.is_none() || unlock_fn.is_none() {
        return -(EINVAL as CLong);
    }

    let fdp = syscall_mckfd_find_locked(thread, fd, offsets, lock_fn, unlock_fn);
    if !fdp.is_null() {
        if let Some(fcntl_fn) = syscall_mckfd_int_callback(fdp, (*offsets).mckfd_fcntl_cb_offset) {
            return fcntl_fn(fdp.cast::<c_void>(), ctx) as CLong;
        }
    }

    forward_fn(syscall_nr, ctx)
}

#[no_mangle]
pub unsafe extern "C" fn syscall_close_body_result(
    thread: *mut c_void,
    fd: CInt,
    syscall_nr: CInt,
    ctx: *mut c_void,
    offsets: *const SyscallMckfdOffsets,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
    forward_fn: Option<SyscallForwardContextFn>,
    close_path_fn: Option<SyscallTofuCloseFn>,
    free_fn: Option<SyscallMckfdFreeFn>,
) -> CLong {
    let Some(forward_fn) = forward_fn else {
        return -(EINVAL as CLong);
    };
    if offsets.is_null() || lock_fn.is_none() || unlock_fn.is_none() {
        return -(EINVAL as CLong);
    }

    let proc = syscall_mckfd_proc(thread, offsets);
    if proc.is_null() {
        return -(EINVAL as CLong);
    }

    let lock = syscall_mckfd_lock_ptr(proc, offsets);
    let irqstate = lock_fn.unwrap()(lock);
    if let Some(close_path_fn) = close_path_fn {
        close_path_fn(thread, fd);
    }

    let headp = syscall_mckfd_headp(proc, offsets);
    let mut prev = core::ptr::null_mut();
    let mut cur = *headp;
    while !cur.is_null() {
        if *field_ptr::<CInt>(cur, (*offsets).mckfd_fd_offset) == fd {
            break;
        }
        prev = cur;
        cur = syscall_mckfd_next(cur, offsets);
    }

    if cur.is_null() {
        unlock_fn.unwrap()(lock, irqstate);
        return forward_fn(syscall_nr, ctx);
    }

    let next = syscall_mckfd_next(cur, offsets);
    if prev.is_null() {
        *headp = next;
    } else {
        syscall_mckfd_set_next(prev, offsets, next);
    }
    syscall_mckfd_set_next(cur, offsets, core::ptr::null_mut());
    unlock_fn.unwrap()(lock, irqstate);

    if let Some(close_fn) = syscall_mckfd_int_callback(cur, (*offsets).mckfd_close_cb_offset) {
        close_fn(cur.cast::<c_void>(), ctx);
    }
    if let Some(free_fn) = free_fn {
        free_fn(cur.cast::<c_void>());
    }

    forward_fn(syscall_nr, ctx)
}

#[no_mangle]
pub unsafe extern "C" fn do_mmap_mckfd_dispatch_body_result(
    thread: *mut c_void,
    flags: CInt,
    fd: CInt,
    ctx: *mut c_void,
    handledp: *mut CInt,
    offsets: *const SyscallMckfdOffsets,
    mckfd_mmap_cb_offset: SizeT,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    if !handledp.is_null() {
        *handledp = 0;
    }
    if (flags & MAP_ANONYMOUS) != 0 {
        return 0;
    }
    if handledp.is_null() || offsets.is_null() || lock_fn.is_none() || unlock_fn.is_none() {
        if !handledp.is_null() {
            *handledp = 1;
        }
        return -(EINVAL as CLong);
    }

    let fdp = syscall_mckfd_find_locked(thread, fd, offsets, lock_fn, unlock_fn);
    if fdp.is_null() {
        return 0;
    }

    *handledp = 1;
    if let Some(mmap_fn) = syscall_mckfd_long_callback(fdp, mckfd_mmap_cb_offset) {
        return mmap_fn(fdp.cast::<c_void>(), ctx);
    }

    -(EBADF as CLong)
}

#[no_mangle]
pub unsafe extern "C" fn do_mmap_page_size_body_result(
    flags: CInt,
    vrf0: CULong,
    thp_disable: CInt,
    len: SizeT,
    pgshiftp: *mut CInt,
    p2alignp: *mut CInt,
    default_huge_shift_fn: Option<ArchMmapDefaultHugeShiftFn>,
    smaller_page_fn: Option<DoMmapSmallerPageFn>,
) -> CInt {
    if pgshiftp.is_null() || p2alignp.is_null() {
        return -EINVAL;
    }

    if (flags & MAP_HUGETLB) != 0 {
        let mut pgshift = (flags >> MAP_HUGE_SHIFT) & 0x3f;
        if pgshift == 0 {
            let Some(default_huge_shift) = default_huge_shift_fn else {
                return -EINVAL;
            };
            pgshift = default_huge_shift();
        }
        *pgshiftp = pgshift;
        *p2alignp = pgshift - PAGE_SHIFT as CInt;
        return 0;
    }

    if ((((flags & (MAP_PRIVATE | MAP_SHARED)) != 0) && (flags & MAP_ANONYMOUS) != 0)
        || (vrf0 & VR_XPMEM) != 0)
        && thp_disable == 0
    {
        *pgshiftp = 0;
        *p2alignp = 0;
        if len > PAGE_SIZE as SizeT {
            let Some(smaller_page) = smaller_page_fn else {
                return -EINVAL;
            };
            return smaller_page(len.wrapping_add(1), p2alignp);
        }
        return 0;
    }

    *pgshiftp = PAGE_SHIFT as CInt;
    *p2alignp = 0;
    0
}

#[no_mangle]
pub unsafe extern "C" fn memlock_prepare_range(
    start0: CULong,
    len0: SizeT,
    user_start: CULong,
    user_end: CULong,
    startp: *mut CULong,
    lenp: *mut SizeT,
    endp: *mut CULong,
) -> CInt {
    let start = start0 & PAGE_MASK;
    let len = ((start & (PAGE_SIZE - 1)).wrapping_add(len0 as CULong)).wrapping_add(PAGE_SIZE - 1)
        & PAGE_MASK;
    let end = start.wrapping_add(len);

    write(startp, start);
    write(lenp, len as SizeT);
    write(endp, end);

    if end < start {
        return -EINVAL;
    }

    if start < user_start
        || user_end <= start
        || len > user_end.wrapping_sub(user_start)
        || user_end.wrapping_sub(len) < start
    {
        return -ENOMEM;
    }

    0
}

#[no_mangle]
pub extern "C" fn memlock_range_flag_result(flag: CULong) -> CInt {
    if (flag & (VR_REMOTE | VR_RESERVED | VR_IO_NOCACHE)) != 0 {
        -EINVAL
    } else {
        0
    }
}

#[inline(always)]
unsafe fn memlock_range_ulong(range: *mut c_void, offset: SizeT) -> CULong {
    *field_ptr::<CULong>(range.cast::<u8>(), offset)
}

#[inline(always)]
unsafe fn memlock_range_ptr(range: *mut c_void, offset: SizeT) -> *mut c_void {
    *field_ptr::<*mut c_void>(range.cast::<u8>(), offset)
}

#[inline(always)]
unsafe fn memlock_range_set_ulong(range: *mut c_void, offset: SizeT, value: CULong) {
    *field_ptr::<CULong>(range.cast::<u8>(), offset) = value;
}

#[inline(always)]
unsafe fn memlock_log(
    log: Option<MemlockLogFn>,
    event: CInt,
    op: CInt,
    cpu: CInt,
    start: CULong,
    len: SizeT,
    addr: CULong,
    range_start: CULong,
    range_end: CULong,
    error: CInt,
) {
    let Some(log) = log else {
        return;
    };

    let mut record = MaybeUninit::<MemlockLogRecord>::uninit();
    let ptr = record.as_mut_ptr();
    write_volatile(&raw mut (*ptr).event, event);
    write_volatile(&raw mut (*ptr).op, op);
    write_volatile(&raw mut (*ptr).cpu, cpu);
    write_volatile(&raw mut (*ptr).start, start);
    write_volatile(&raw mut (*ptr).len, len);
    write_volatile(&raw mut (*ptr).addr, addr);
    write_volatile(&raw mut (*ptr).range_start, range_start);
    write_volatile(&raw mut (*ptr).range_end, range_end);
    write_volatile(&raw mut (*ptr).error, error);
    log(ptr as *const MemlockLogRecord);
}

#[no_mangle]
pub unsafe extern "C" fn memlock_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    start0: CULong,
    len0: SizeT,
    user_start: CULong,
    user_end: CULong,
    op: CInt,
    cpu: CInt,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_flag_offset: SizeT,
    range_memobj_offset: SizeT,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    next_fn: Option<MsyncNextRangeFn>,
    split_fn: Option<MemlockSplitFn>,
    join_fn: Option<MemlockJoinFn>,
    populate_fn: Option<MemlockPopulateFn>,
    log_fn: Option<MemlockLogFn>,
) -> CInt {
    let _ = range_memobj_offset;
    memlock_log(log_fn, MEMLOCK_LOG_ENTER, op, cpu, start0, len0, 0, 0, 0, 0);

    if op != MEMLOCK_OP_LOCK && op != MEMLOCK_OP_UNLOCK {
        let error = -EINVAL;
        memlock_log(
            log_fn,
            MEMLOCK_LOG_EXIT,
            op,
            cpu,
            start0,
            len0,
            0,
            0,
            0,
            error,
        );
        return error;
    }

    let mut start: CULong = 0;
    let mut len: SizeT = 0;
    let mut end: CULong = 0;
    let mut error = memlock_prepare_range(
        start0, len0, user_start, user_end, &mut start, &mut len, &mut end,
    );
    if error != 0 || start == end {
        if start == end {
            error = 0;
        }
        memlock_log(
            log_fn,
            MEMLOCK_LOG_EXIT,
            op,
            cpu,
            start0,
            len0,
            0,
            0,
            0,
            error,
        );
        return error;
    }

    if let Some(lock) = lock_fn {
        lock(range_lock);
    }

    let mut first = core::ptr::null_mut::<c_void>();
    let mut range = core::ptr::null_mut::<c_void>();
    let mut addr = start;
    while addr < end {
        if first.is_null() {
            range = if let Some(lookup) = lookup_fn {
                lookup(vm, start, start.wrapping_add(PAGE_SIZE))
            } else {
                core::ptr::null_mut()
            };
            first = range;
        } else {
            range = if let Some(next) = next_fn {
                next(vm, range)
            } else {
                core::ptr::null_mut()
            };
        }

        if range.is_null() || addr < memlock_range_ulong(range, range_start_offset) {
            error = -ENOMEM;
            let (range_start, range_end) = if range.is_null() {
                (0, 0)
            } else {
                (
                    memlock_range_ulong(range, range_start_offset),
                    memlock_range_ulong(range, range_end_offset),
                )
            };
            memlock_log(
                log_fn,
                MEMLOCK_LOG_NOT_CONTIG,
                op,
                cpu,
                start0,
                len0,
                addr,
                range_start,
                range_end,
                error,
            );
            break;
        }

        error = memlock_range_flag_result(memlock_range_ulong(range, range_flag_offset));
        if error != 0 {
            memlock_log(
                log_fn,
                MEMLOCK_LOG_CANNOT_CHANGE,
                op,
                cpu,
                start0,
                len0,
                addr,
                memlock_range_ulong(range, range_start_offset),
                memlock_range_ulong(range, range_end_offset),
                error,
            );
            break;
        }

        addr = memlock_range_ulong(range, range_end_offset);
    }

    if error == 0 {
        let mut changed = core::ptr::null_mut::<c_void>();
        addr = start;
        while addr < end {
            range = if changed.is_null() {
                first
            } else if let Some(next) = next_fn {
                next(vm, changed)
            } else {
                core::ptr::null_mut()
            };

            if range.is_null() || addr < memlock_range_ulong(range, range_start_offset) {
                error = -ENOMEM;
                let (range_start, range_end) = if range.is_null() {
                    (0, 0)
                } else {
                    (
                        memlock_range_ulong(range, range_start_offset),
                        memlock_range_ulong(range, range_end_offset),
                    )
                };
                memlock_log(
                    log_fn,
                    MEMLOCK_LOG_NOT_CONTIG,
                    op,
                    cpu,
                    start0,
                    len0,
                    addr,
                    range_start,
                    range_end,
                    error,
                );
                break;
            }

            if memlock_range_ulong(range, range_start_offset) < addr {
                error = if let Some(split) = split_fn {
                    split(vm, range, addr, &mut range)
                } else {
                    -EINVAL
                };
                if error != 0 {
                    memlock_log(
                        log_fn,
                        MEMLOCK_LOG_SPLIT_FAILED,
                        op,
                        cpu,
                        start0,
                        len0,
                        addr,
                        memlock_range_ulong(range, range_start_offset),
                        memlock_range_ulong(range, range_end_offset),
                        error,
                    );
                    break;
                }
            }
            if end < memlock_range_ulong(range, range_end_offset) {
                error = if let Some(split) = split_fn {
                    split(vm, range, end, core::ptr::null_mut())
                } else {
                    -EINVAL
                };
                if error != 0 {
                    memlock_log(
                        log_fn,
                        MEMLOCK_LOG_SPLIT_FAILED,
                        op,
                        cpu,
                        start0,
                        len0,
                        addr,
                        memlock_range_ulong(range, range_start_offset),
                        memlock_range_ulong(range, range_end_offset),
                        error,
                    );
                    break;
                }
            }

            let flag = memlock_range_ulong(range, range_flag_offset);
            if op == MEMLOCK_OP_LOCK {
                memlock_range_set_ulong(range, range_flag_offset, flag | VR_LOCKED);
            } else {
                memlock_range_set_ulong(range, range_flag_offset, flag & !VR_LOCKED);
            }

            if changed.is_null() {
                changed = range;
            } else {
                error = if let Some(join) = join_fn {
                    join(vm, changed, range)
                } else {
                    -EINVAL
                };
                if error != 0 {
                    memlock_log(
                        log_fn,
                        MEMLOCK_LOG_JOIN_FAILED,
                        op,
                        cpu,
                        start0,
                        len0,
                        addr,
                        memlock_range_ulong(changed, range_start_offset),
                        memlock_range_ulong(range, range_end_offset),
                        error,
                    );
                    changed = range;
                }
            }

            addr = memlock_range_ulong(changed, range_end_offset);
        }
    }

    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }

    if error == 0 && op == MEMLOCK_OP_LOCK {
        error = if let Some(populate) = populate_fn {
            populate(vm, start, len)
        } else {
            -EINVAL
        };
        if error != 0 {
            memlock_log(
                log_fn,
                MEMLOCK_LOG_POPULATE_FAILED,
                op,
                cpu,
                start0,
                len0,
                start,
                start,
                end,
                error,
            );
            error = 0;
        }
    }

    memlock_log(
        log_fn,
        MEMLOCK_LOG_EXIT,
        op,
        cpu,
        start0,
        len0,
        0,
        0,
        0,
        error,
    );
    error
}

#[no_mangle]
pub extern "C" fn range_has_disallowed_change_flags(flag: CULong) -> CInt {
    if (flag & (VR_REMOTE | VR_RESERVED | VR_IO_NOCACHE)) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn munmap_prepare_range(
    addr: CULong,
    len0: SizeT,
    user_start: CULong,
    user_end: CULong,
    lenp: *mut SizeT,
) -> CInt {
    let len = len0.wrapping_add((PAGE_SIZE - 1) as SizeT) & PAGE_MASK as SizeT;
    write(lenp, len);

    if (addr & (PAGE_SIZE - 1)) != 0
        || addr < user_start
        || user_end <= addr
        || len == 0
        || len > user_end.wrapping_sub(user_start) as SizeT
        || user_end.wrapping_sub(len as CULong) < addr
    {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn munmap_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    addr: CULong,
    len0: SizeT,
    user_start: CULong,
    user_end: CULong,
    cpu: CInt,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    do_munmap_fn: Option<MunmapDoFn>,
    log_fn: Option<MunmapLogFn>,
) -> CInt {
    let _ = vm;
    if let Some(log) = log_fn {
        log(MUNMAP_LOG_ENTER, cpu, addr, len0, 0);
    }

    let mut len: SizeT = 0;
    let mut error = munmap_prepare_range(addr, len0, user_start, user_end, &mut len);
    if error == 0 {
        if let Some(lock) = lock_fn {
            lock(range_lock);
        }
        error = if let Some(do_munmap) = do_munmap_fn {
            do_munmap(addr as *mut c_void, len, 1)
        } else {
            -EINVAL
        };
        if let Some(unlock) = unlock_fn {
            unlock(range_lock);
        }
    }

    if let Some(log) = log_fn {
        log(MUNMAP_LOG_EXIT, cpu, addr, len0, error);
        if cfg!(enable_fugaku_hacks) && error != 0 {
            log(MUNMAP_LOG_ERROR, cpu, addr, len0, error);
        }
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn do_munmap_body_result(
    vm: *mut c_void,
    proc: *mut c_void,
    addr: CULong,
    len: SizeT,
    holding_memory_range_lock: CInt,
    proc_straight_va_offset: SizeT,
    proc_straight_len_offset: SizeT,
    begin_fn: Option<DoMunmapVoidFn>,
    remove_range_fn: Option<DoMunmapRemoveRangeFn>,
    clear_host_pte_fn: Option<DoMunmapClearHostFn>,
    set_host_vma_fn: Option<MprotectSetHostVmaFn>,
    finish_fn: Option<DoMunmapVoidFn>,
    log_fn: Option<DoMunmapLogFn>,
) -> CInt {
    if let Some(begin) = begin_fn {
        begin();
    }

    let mut ro_freed = 0;
    let mut error = if let Some(remove_range) = remove_range_fn {
        remove_range(vm, addr, addr.wrapping_add(len as CULong), &mut ro_freed)
    } else {
        -EINVAL
    };

    let straight_va = *field_ptr::<CULong>(proc.cast::<u8>(), proc_straight_va_offset);
    let straight_len = *field_ptr::<SizeT>(proc.cast::<u8>(), proc_straight_len_offset);
    if straight_va == 0
        || addr < straight_va
        || addr.wrapping_add(len as CULong) > straight_va.wrapping_add(straight_len as CULong)
    {
        if error != 0 || ro_freed == 0 {
            if let Some(clear_host_pte) = clear_host_pte_fn {
                clear_host_pte(addr, len, holding_memory_range_lock);
            }
        } else {
            error = if let Some(set_host_vma) = set_host_vma_fn {
                set_host_vma(
                    addr,
                    len,
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                    holding_memory_range_lock,
                )
            } else {
                -EINVAL
            };
        }
    }

    if let Some(finish) = finish_fn {
        finish();
    }
    if let Some(log) = log_fn {
        log(addr, len, error);
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn clear_host_pte_body_result(
    vm: *mut c_void,
    addr: CULong,
    len: SizeT,
    holding_memory_range_lock: CInt,
    vm_lock_taken_offset: SizeT,
    cpu: CInt,
    syscall_nr: CInt,
    forward_fn: Option<SyscallDoSyscall3Fn>,
    log_fn: Option<ClearHostPteLogFn>,
) -> CLong {
    if holding_memory_range_lock != 0 {
        *field_ptr::<CInt>(vm.cast::<u8>(), vm_lock_taken_offset) = cpu;
    }

    let lerror = if let Some(forward) = forward_fn {
        forward(syscall_nr, addr, len as CULong, 0)
    } else {
        (-EINVAL) as CLong
    };

    if holding_memory_range_lock != 0 {
        *field_ptr::<CInt>(vm.cast::<u8>(), vm_lock_taken_offset) = -1;
    }
    if lerror != 0 {
        if let Some(log) = log_fn {
            log(lerror);
        }
    }
    lerror
}

#[no_mangle]
pub unsafe extern "C" fn munmap_all_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    region: *mut c_void,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    region_map_start_offset: SizeT,
    region_map_end_offset: SizeT,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    next_fn: Option<MsyncNextRangeFn>,
    do_munmap_fn: Option<MunmapDoFn>,
    free_ranges_fn: Option<MunmapAllFreeRangesFn>,
    log_fn: Option<MunmapAllLogFn>,
) {
    if let Some(lock) = lock_fn {
        lock(range_lock);
    }

    let mut next = if let Some(lookup) = lookup_fn {
        lookup(vm, 0, CULong::MAX)
    } else {
        core::ptr::null_mut()
    };

    while !next.is_null() {
        let range = next;
        next = if let Some(next_range) = next_fn {
            next_range(vm, range)
        } else {
            core::ptr::null_mut()
        };

        let start = *field_ptr::<CULong>(range.cast::<u8>(), range_start_offset);
        let end = *field_ptr::<CULong>(range.cast::<u8>(), range_end_offset);
        let size = end.wrapping_sub(start) as SizeT;
        let error = if let Some(do_munmap) = do_munmap_fn {
            do_munmap(start as *mut c_void, size, 1)
        } else {
            -EINVAL
        };
        if error != 0 {
            if let Some(log) = log_fn {
                log(start, size, error);
            }
        }
    }

    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }

    if let Some(free_ranges) = free_ranges_fn {
        free_ranges(vm);
    }

    let map_start = *field_ptr::<CULong>(region.cast::<u8>(), region_map_start_offset);
    *field_ptr::<CULong>(region.cast::<u8>(), region_map_end_offset) = map_start;
}

#[inline(always)]
unsafe fn shmdt_log(log_fn: Option<ShmdtLogFn>, event: CInt, addr: CULong, error: CInt) {
    if let Some(log) = log_fn {
        log(event, addr, error);
    }
}

#[no_mangle]
pub unsafe extern "C" fn shmdt_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    shmaddr: CULong,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_memobj_offset: SizeT,
    memobj_flags_offset: SizeT,
    shmdt_ok_flag: CULong,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    do_munmap_fn: Option<MunmapDoFn>,
    log_fn: Option<ShmdtLogFn>,
) -> CInt {
    shmdt_log(log_fn, SHMDT_LOG_ENTER, shmaddr, 0);

    if let Some(lock) = lock_fn {
        lock(range_lock);
    }

    let mut error = -EINVAL;
    let mut invalid = true;

    if let Some(lookup) = lookup_fn {
        let range = lookup(vm, shmaddr, shmaddr.wrapping_add(1));
        if !range.is_null() {
            let start = memlock_range_ulong(range, range_start_offset);
            let end = memlock_range_ulong(range, range_end_offset);
            let memobj = memlock_range_ptr(range, range_memobj_offset);
            if start == shmaddr && !memobj.is_null() {
                let flags = *field_ptr::<u32>(memobj.cast::<u8>(), memobj_flags_offset) as CULong;
                if (flags & shmdt_ok_flag) != 0 {
                    invalid = false;
                    error = if let Some(do_munmap) = do_munmap_fn {
                        do_munmap(start as *mut c_void, end.wrapping_sub(start) as SizeT, 1)
                    } else {
                        -EINVAL
                    };
                }
            }
        }
    }

    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }

    if invalid {
        shmdt_log(log_fn, SHMDT_LOG_INVALID, shmaddr, -EINVAL);
    } else {
        shmdt_log(log_fn, SHMDT_LOG_EXIT, shmaddr, error);
    }

    error
}

#[inline(always)]
unsafe fn shmat_log(
    log_fn: Option<ShmatLogFn>,
    event: CInt,
    shmid: CInt,
    shmaddr: CULong,
    shmflg: CInt,
    error: CLong,
) {
    if let Some(log) = log_fn {
        log(event, shmid, shmaddr, shmflg, error);
    }
}

#[inline(always)]
fn shmat_access(
    euid: u32,
    egid: u32,
    shmflg: CInt,
    uid: u32,
    cuid: u32,
    gid: u32,
    cgid: u32,
    mode: u16,
) -> CInt {
    let mut req = 0o4;
    if (shmflg & SHM_RDONLY) == 0 {
        req |= 0o2;
    }

    if euid == 0 {
        req = 0;
    } else if euid == uid || euid == cuid {
        req <<= 6;
    } else if egid == gid || egid == cgid {
        req <<= 3;
    }

    if (req & !(mode as CInt)) != 0 {
        -EACCES
    } else {
        0
    }
}

#[inline(always)]
unsafe fn shmat_memobj(obj: *mut c_void, obj_memobj_offset: SizeT) -> *mut c_void {
    obj.cast::<u8>().add(obj_memobj_offset).cast::<c_void>()
}

#[inline(always)]
unsafe fn shmat_unref_obj(
    obj: *mut c_void,
    obj_memobj_offset: SizeT,
    memobj_unref_fn: Option<ShmatMemobjFn>,
) {
    if let Some(unref) = memobj_unref_fn {
        unref(shmat_memobj(obj, obj_memobj_offset));
    }
}

#[no_mangle]
pub unsafe extern "C" fn shmat_body_result(
    shmid: CInt,
    shmaddr: CULong,
    shmflg: CInt,
    proc_euid: u32,
    proc_egid: u32,
    vm: *mut c_void,
    range_lock: *mut c_void,
    obj_pgshift_offset: SizeT,
    obj_real_segsz_offset: SizeT,
    obj_memobj_offset: SizeT,
    obj_uid_offset: SizeT,
    obj_cuid_offset: SizeT,
    obj_gid_offset: SizeT,
    obj_cgid_offset: SizeT,
    obj_mode_offset: SizeT,
    list_lock_fn: Option<ShmatVoidFn>,
    list_unlock_fn: Option<ShmatVoidFn>,
    lookup_obj_fn: Option<ShmatLookupObjFn>,
    memobj_unref_fn: Option<ShmatMemobjFn>,
    range_lock_fn: Option<SyscallRwlockFn>,
    range_unlock_fn: Option<SyscallRwlockFn>,
    lookup_range_fn: Option<MsyncLookupRangeFn>,
    search_free_fn: Option<ShmatSearchFn>,
    set_host_vma_fn: Option<MprotectSetHostVmaFn>,
    add_range_fn: Option<ShmatAddRangeFn>,
    log_fn: Option<ShmatLogFn>,
) -> CLong {
    shmat_log(log_fn, SHMAT_LOG_ENTER, shmid, shmaddr, shmflg, 0);

    if let Some(lock) = list_lock_fn {
        lock();
    }

    let mut obj: *mut c_void = core::ptr::null_mut();
    let error = if let Some(lookup_obj) = lookup_obj_fn {
        lookup_obj(shmid, &mut obj)
    } else {
        -EINVAL
    };
    if error != 0 || obj.is_null() {
        let rc = if error != 0 { error } else { -EINVAL };
        if let Some(unlock) = list_unlock_fn {
            unlock();
        }
        shmat_log(
            log_fn,
            SHMAT_LOG_LOOKUP_FAILED,
            shmid,
            shmaddr,
            shmflg,
            rc as CLong,
        );
        return rc as CLong;
    }

    let pgshift = *field_ptr::<CInt>(obj.cast::<u8>(), obj_pgshift_offset);
    if pgshift < 0 || pgshift >= (size_of::<SizeT>() * 8) as CInt {
        if let Some(unlock) = list_unlock_fn {
            unlock();
        }
        shmat_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
        shmat_log(
            log_fn,
            SHMAT_LOG_INVALID_ADDR,
            shmid,
            shmaddr,
            shmflg,
            (-EINVAL) as CLong,
        );
        return (-EINVAL) as CLong;
    }

    let pgsize = 1usize << (pgshift as usize);
    let pgmask = (pgsize as CULong).wrapping_sub(1);
    if shmaddr != 0 && (shmaddr & pgmask) != 0 && (shmflg & SHM_RND) == 0 {
        if let Some(unlock) = list_unlock_fn {
            unlock();
        }
        shmat_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
        shmat_log(
            log_fn,
            SHMAT_LOG_INVALID_ADDR,
            shmid,
            shmaddr,
            shmflg,
            (-EINVAL) as CLong,
        );
        return (-EINVAL) as CLong;
    }

    let mut addr = shmaddr & !pgmask;
    let len = *field_ptr::<SizeT>(obj.cast::<u8>(), obj_real_segsz_offset);
    let mut prot = PROT_READ;
    if (shmflg & SHM_RDONLY) == 0 {
        prot |= PROT_WRITE;
    }

    let access = shmat_access(
        proc_euid,
        proc_egid,
        shmflg,
        *field_ptr::<u32>(obj.cast::<u8>(), obj_uid_offset),
        *field_ptr::<u32>(obj.cast::<u8>(), obj_cuid_offset),
        *field_ptr::<u32>(obj.cast::<u8>(), obj_gid_offset),
        *field_ptr::<u32>(obj.cast::<u8>(), obj_cgid_offset),
        *field_ptr::<u16>(obj.cast::<u8>(), obj_mode_offset),
    );
    if access != 0 {
        if let Some(unlock) = list_unlock_fn {
            unlock();
        }
        shmat_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
        shmat_log(
            log_fn,
            SHMAT_LOG_ACCESS_FAILED,
            shmid,
            shmaddr,
            shmflg,
            access as CLong,
        );
        return access as CLong;
    }

    if let Some(lock) = range_lock_fn {
        lock(range_lock);
    }

    if addr != 0 {
        if let Some(lookup_range) = lookup_range_fn {
            if !lookup_range(vm, addr, addr.wrapping_add(len as CULong)).is_null() {
                if let Some(unlock) = range_unlock_fn {
                    unlock(range_lock);
                }
                if let Some(unlock) = list_unlock_fn {
                    unlock();
                }
                shmat_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
                shmat_log(
                    log_fn,
                    SHMAT_LOG_RANGE_BUSY,
                    shmid,
                    shmaddr,
                    shmflg,
                    (-ENOMEM) as CLong,
                );
                return (-ENOMEM) as CLong;
            }
        } else {
            if let Some(unlock) = range_unlock_fn {
                unlock(range_lock);
            }
            if let Some(unlock) = list_unlock_fn {
                unlock();
            }
            shmat_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
            shmat_log(
                log_fn,
                SHMAT_LOG_RANGE_BUSY,
                shmid,
                shmaddr,
                shmflg,
                (-EINVAL) as CLong,
            );
            return (-EINVAL) as CLong;
        }
    } else if let Some(search_free) = search_free_fn {
        let mut found_addr = 0;
        let search_error = search_free(len, pgshift, &mut found_addr);
        if search_error != 0 {
            if let Some(unlock) = range_unlock_fn {
                unlock(range_lock);
            }
            if let Some(unlock) = list_unlock_fn {
                unlock();
            }
            shmat_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
            shmat_log(
                log_fn,
                SHMAT_LOG_SEARCH_FAILED,
                shmid,
                shmaddr,
                shmflg,
                search_error as CLong,
            );
            return search_error as CLong;
        }
        addr = found_addr;
    } else {
        if let Some(unlock) = range_unlock_fn {
            unlock(range_lock);
        }
        if let Some(unlock) = list_unlock_fn {
            unlock();
        }
        shmat_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
        shmat_log(
            log_fn,
            SHMAT_LOG_SEARCH_FAILED,
            shmid,
            shmaddr,
            shmflg,
            (-EINVAL) as CLong,
        );
        return (-EINVAL) as CLong;
    }

    let mut vrflags = VR_DEMAND_PAGING | prot_to_vr_flag(prot);
    vrflags |= vrflag_prot_to_maxprot(vrflags);

    if (prot & PROT_WRITE) == 0 {
        let host_error = if let Some(set_host_vma) = set_host_vma_fn {
            set_host_vma(addr, len, PROT_READ | PROT_EXEC, 1)
        } else {
            -EINVAL
        };
        if host_error != 0 {
            if let Some(unlock) = range_unlock_fn {
                unlock(range_lock);
            }
            if let Some(unlock) = list_unlock_fn {
                unlock();
            }
            shmat_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
            shmat_log(
                log_fn,
                SHMAT_LOG_SET_HOST_FAILED,
                shmid,
                shmaddr,
                shmflg,
                host_error as CLong,
            );
            return host_error as CLong;
        }
    }

    let memobj = shmat_memobj(obj, obj_memobj_offset);
    let add_error = if let Some(add_range) = add_range_fn {
        add_range(
            vm,
            addr,
            addr.wrapping_add(len as CULong),
            CULong::MAX,
            vrflags,
            memobj,
            0,
            pgshift,
        )
    } else {
        -EINVAL
    };
    if add_error != 0 {
        if (prot & PROT_WRITE) == 0 {
            if let Some(set_host_vma) = set_host_vma_fn {
                set_host_vma(addr, len, PROT_READ | PROT_WRITE | PROT_EXEC, 1);
            }
        }
        shmat_unref_obj(obj, obj_memobj_offset, memobj_unref_fn);
        if let Some(unlock) = range_unlock_fn {
            unlock(range_lock);
        }
        if let Some(unlock) = list_unlock_fn {
            unlock();
        }
        shmat_log(
            log_fn,
            SHMAT_LOG_ADD_FAILED,
            shmid,
            shmaddr,
            shmflg,
            add_error as CLong,
        );
        return add_error as CLong;
    }

    if let Some(unlock) = range_unlock_fn {
        unlock(range_lock);
    }
    if let Some(unlock) = list_unlock_fn {
        unlock();
    }
    shmat_log(
        log_fn,
        SHMAT_LOG_EXIT,
        shmid,
        shmaddr,
        shmflg,
        addr as CLong,
    );
    addr as CLong
}

#[inline(always)]
unsafe fn shmctl_log(
    log_fn: Option<ShmctlLogFn>,
    event: CInt,
    shmid: CInt,
    cmd: CInt,
    buf_addr: CULong,
    error: CLong,
) {
    if let Some(log) = log_fn {
        log(event, shmid, cmd, buf_addr, error);
    }
}

#[inline(always)]
unsafe fn shmctl_obj_memobj(obj: *mut c_void, offsets: &ShmctlOffsets) -> *mut c_void {
    obj.cast::<u8>()
        .add(offsets.obj_memobj_offset)
        .cast::<c_void>()
}

#[inline(always)]
unsafe fn shmctl_unref_obj(
    obj: *mut c_void,
    offsets: &ShmctlOffsets,
    memobj_unref_fn: Option<ShmatMemobjFn>,
) {
    if let Some(unref) = memobj_unref_fn {
        unref(shmctl_obj_memobj(obj, offsets));
    }
}

#[inline(always)]
fn shmctl_owner(euid: u32, uid: u32, cuid: u32) -> CInt {
    if uid == euid || cuid == euid {
        0
    } else {
        -EPERM
    }
}

#[inline(always)]
fn shmctl_owner_or_cap(has_cap: CInt, euid: u32, uid: u32, cuid: u32) -> CInt {
    if has_cap != 0 || uid == euid || cuid == euid {
        0
    } else {
        -EPERM
    }
}

#[inline(always)]
fn shmctl_ipc_stat_access(
    euid: u32,
    egid: u32,
    uid: u32,
    cuid: u32,
    gid: u32,
    cgid: u32,
    mode: u16,
) -> CInt {
    let req = if euid == 0 {
        0
    } else if euid == uid || euid == cuid {
        0o400
    } else if egid == gid || egid == cgid {
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

#[inline(always)]
fn shmctl_shmlock_rlimit(
    has_cap: CInt,
    rlim_cur: CULong,
    user_locked: CULong,
    size: CULong,
) -> CInt {
    if rlim_cur == 0 && has_cap == 0 {
        return -EPERM;
    }
    if has_cap == 0
        && rlim_cur != CULong::MAX
        && (rlim_cur < user_locked || rlim_cur.wrapping_sub(user_locked) < size)
    {
        return -ENOMEM;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn shmctl_body_result(
    shmid: CInt,
    cmd: CInt,
    buf_addr: CULong,
    proc_euid: u32,
    proc_egid: u32,
    proc_ruid: u32,
    rlim_memlock_cur: CULong,
    now: CLong,
    has_cap_sys_admin: CInt,
    has_cap_ipc_lock: CInt,
    offsets: *const ShmctlOffsets,
    shminfo: *const c_void,
    shm_info: *const c_void,
    list_lock_fn: Option<ShmatVoidFn>,
    list_unlock_fn: Option<ShmatVoidFn>,
    lookup_obj_fn: Option<ShmatLookupObjFn>,
    lookup_by_index_fn: Option<ShmatLookupObjFn>,
    memobj_unref_fn: Option<ShmatMemobjFn>,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    get_max_index_fn: Option<ShmctlGetMaxIndexFn>,
    users_lock_fn: Option<ShmatVoidFn>,
    users_unlock_fn: Option<ShmatVoidFn>,
    shmlock_user_get_fn: Option<ShmctlShmlockUserGetFn>,
    shmlock_user_free_fn: Option<ShmatMemobjFn>,
    memobj_refcnt_read_fn: Option<ShmctlMemobjRefcntReadFn>,
    log_fn: Option<ShmctlLogFn>,
) -> CLong {
    shmctl_log(log_fn, SHMCTL_LOG_ENTER, shmid, cmd, buf_addr, 0);

    if offsets.is_null() {
        shmctl_log(
            log_fn,
            SHMCTL_LOG_EINVAL,
            shmid,
            cmd,
            buf_addr,
            (-EINVAL) as CLong,
        );
        return (-EINVAL) as CLong;
    }
    let offsets = &*offsets;
    if offsets.shmid_ds_size != size_of::<ShmidDs>() {
        shmctl_log(
            log_fn,
            SHMCTL_LOG_EINVAL,
            shmid,
            cmd,
            buf_addr,
            (-EINVAL) as CLong,
        );
        return (-EINVAL) as CLong;
    }

    let Some(list_lock) = list_lock_fn else {
        return (-EINVAL) as CLong;
    };
    let Some(list_unlock) = list_unlock_fn else {
        return (-EINVAL) as CLong;
    };
    let Some(lookup_obj) = lookup_obj_fn else {
        return (-EINVAL) as CLong;
    };
    let Some(copy_to_user) = copy_to_fn else {
        return (-EINVAL) as CLong;
    };
    let Some(get_max_index) = get_max_index_fn else {
        return (-EINVAL) as CLong;
    };

    match cmd {
        IPC_RMID => {
            list_lock();
            let mut obj: *mut c_void = null_mut();
            let error = lookup_obj(shmid, &mut obj);
            if error != 0 || obj.is_null() {
                let rc = if error != 0 { error } else { -EINVAL };
                list_unlock();
                shmctl_log(log_fn, SHMCTL_LOG_LOOKUP, shmid, cmd, buf_addr, rc as CLong);
                return rc as CLong;
            }

            let base = obj.cast::<u8>();
            let perm_error = shmctl_owner_or_cap(
                has_cap_sys_admin,
                proc_euid,
                *field_ptr::<u32>(base, offsets.obj_uid_offset),
                *field_ptr::<u32>(base, offsets.obj_cuid_offset),
            );
            if perm_error != 0 {
                list_unlock();
                shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                shmctl_log(
                    log_fn,
                    SHMCTL_LOG_EPERM,
                    shmid,
                    cmd,
                    buf_addr,
                    perm_error as CLong,
                );
                return perm_error as CLong;
            }

            let modep = field_ptr::<u16>(base, offsets.obj_mode_offset);
            let oldmode = *modep;
            *modep = oldmode | SHM_DEST;
            list_unlock();
            if (oldmode & SHM_DEST) == 0 {
                shmctl_unref_obj(obj, offsets, memobj_unref_fn);
            }
            shmctl_unref_obj(obj, offsets, memobj_unref_fn);
            shmctl_log(log_fn, SHMCTL_LOG_EXIT, shmid, cmd, buf_addr, 0);
            0
        }
        IPC_SET => {
            let Some(copy_from_user) = copy_from_fn else {
                return (-EINVAL) as CLong;
            };

            list_lock();
            let mut obj: *mut c_void = null_mut();
            let error = lookup_obj(shmid, &mut obj);
            if error != 0 || obj.is_null() {
                let rc = if error != 0 { error } else { -EINVAL };
                list_unlock();
                shmctl_log(log_fn, SHMCTL_LOG_LOOKUP, shmid, cmd, buf_addr, rc as CLong);
                return rc as CLong;
            }

            let base = obj.cast::<u8>();
            let perm_error = shmctl_owner(
                proc_euid,
                *field_ptr::<u32>(base, offsets.obj_uid_offset),
                *field_ptr::<u32>(base, offsets.obj_cuid_offset),
            );
            if perm_error != 0 {
                list_unlock();
                shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                shmctl_log(
                    log_fn,
                    SHMCTL_LOG_EPERM,
                    shmid,
                    cmd,
                    buf_addr,
                    perm_error as CLong,
                );
                return perm_error as CLong;
            }

            let mut ads = MaybeUninit::<ShmidDs>::zeroed();
            let copy_error = copy_from_user(
                ads.as_mut_ptr().cast::<u8>(),
                buf_addr,
                offsets.shmid_ds_size,
            );
            if copy_error != 0 {
                list_unlock();
                shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                shmctl_log(log_fn, SHMCTL_LOG_COPY, shmid, cmd, buf_addr, copy_error);
                return copy_error;
            }
            let ads = ads.assume_init();
            *field_ptr::<u32>(base, offsets.obj_uid_offset) = ads.shm_perm.uid;
            *field_ptr::<u32>(base, offsets.obj_gid_offset) = ads.shm_perm.gid;
            let modep = field_ptr::<u16>(base, offsets.obj_mode_offset);
            *modep = (*modep & !0o777u16) | (ads.shm_perm.mode & 0o777u16);
            *field_ptr::<CLong>(base, offsets.obj_ctime_offset) = now;

            list_unlock();
            shmctl_unref_obj(obj, offsets, memobj_unref_fn);
            shmctl_log(log_fn, SHMCTL_LOG_EXIT, shmid, cmd, buf_addr, 0);
            0
        }
        IPC_STAT | SHM_STAT => {
            list_lock();
            let mut obj: *mut c_void = null_mut();
            let error = if cmd == IPC_STAT {
                lookup_obj(shmid, &mut obj)
            } else if let Some(lookup_index) = lookup_by_index_fn {
                lookup_index(shmid, &mut obj)
            } else {
                -EINVAL
            };
            if error != 0 || obj.is_null() {
                let rc = if error != 0 { error } else { -EINVAL };
                list_unlock();
                shmctl_log(log_fn, SHMCTL_LOG_LOOKUP, shmid, cmd, buf_addr, rc as CLong);
                return rc as CLong;
            }

            let base = obj.cast::<u8>();
            if cmd == IPC_STAT {
                let access_error = shmctl_ipc_stat_access(
                    proc_euid,
                    proc_egid,
                    *field_ptr::<u32>(base, offsets.obj_uid_offset),
                    *field_ptr::<u32>(base, offsets.obj_cuid_offset),
                    *field_ptr::<u32>(base, offsets.obj_gid_offset),
                    *field_ptr::<u32>(base, offsets.obj_cgid_offset),
                    *field_ptr::<u16>(base, offsets.obj_mode_offset),
                );
                if access_error != 0 {
                    list_unlock();
                    shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                    shmctl_log(
                        log_fn,
                        SHMCTL_LOG_EACCES,
                        shmid,
                        cmd,
                        buf_addr,
                        access_error as CLong,
                    );
                    return access_error as CLong;
                }
            }

            let refcnt = if let Some(read_refcnt) = memobj_refcnt_read_fn {
                read_refcnt(shmctl_obj_memobj(obj, offsets))
            } else {
                0
            };
            let mut nattch = refcnt as i64 - 1;
            if (*field_ptr::<u16>(base, offsets.obj_mode_offset) & SHM_DEST) == 0 {
                nattch -= 1;
            }
            *field_ptr::<u64>(base, offsets.obj_nattch_offset) = nattch as u64;

            let copy_error = copy_to_user(
                buf_addr,
                base.add(offsets.obj_ds_offset).cast::<u8>(),
                offsets.shmid_ds_size,
            );
            if copy_error != 0 {
                list_unlock();
                shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                shmctl_log(log_fn, SHMCTL_LOG_COPY, shmid, cmd, buf_addr, copy_error);
                return copy_error;
            }
            list_unlock();
            shmctl_unref_obj(obj, offsets, memobj_unref_fn);
            shmctl_log(log_fn, SHMCTL_LOG_EXIT, shmid, cmd, buf_addr, 0);
            0
        }
        IPC_INFO => {
            list_lock();
            let mut obj: *mut c_void = null_mut();
            let error = lookup_obj(shmid, &mut obj);
            if error != 0 || obj.is_null() {
                let rc = if error != 0 { error } else { -EINVAL };
                list_unlock();
                shmctl_log(log_fn, SHMCTL_LOG_LOOKUP, shmid, cmd, buf_addr, rc as CLong);
                return rc as CLong;
            }

            let copy_error = copy_to_user(buf_addr, shminfo.cast::<u8>(), offsets.shminfo_size);
            if copy_error != 0 {
                list_unlock();
                shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                shmctl_log(log_fn, SHMCTL_LOG_COPY, shmid, cmd, buf_addr, copy_error);
                return copy_error;
            }
            let mut maxi = get_max_index();
            if maxi < 0 {
                maxi = 0;
            }
            list_unlock();
            shmctl_unref_obj(obj, offsets, memobj_unref_fn);
            shmctl_log(log_fn, SHMCTL_LOG_EXIT, shmid, cmd, buf_addr, maxi as CLong);
            maxi as CLong
        }
        SHM_LOCK => {
            list_lock();
            let mut obj: *mut c_void = null_mut();
            let error = lookup_obj(shmid, &mut obj);
            if error != 0 || obj.is_null() {
                let rc = if error != 0 { error } else { -EINVAL };
                list_unlock();
                shmctl_log(log_fn, SHMCTL_LOG_LOOKUP, shmid, cmd, buf_addr, rc as CLong);
                return rc as CLong;
            }

            let base = obj.cast::<u8>();
            let perm_error = shmctl_owner_or_cap(
                has_cap_ipc_lock,
                proc_euid,
                *field_ptr::<u32>(base, offsets.obj_uid_offset),
                *field_ptr::<u32>(base, offsets.obj_cuid_offset),
            );
            if perm_error != 0 {
                list_unlock();
                shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                shmctl_log(
                    log_fn,
                    SHMCTL_LOG_PERM_SHM,
                    shmid,
                    cmd,
                    buf_addr,
                    perm_error as CLong,
                );
                return perm_error as CLong;
            }

            let proc_perm_error = shmctl_shmlock_rlimit(has_cap_ipc_lock, rlim_memlock_cur, 0, 0);
            if proc_perm_error != 0 {
                list_unlock();
                shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                shmctl_log(
                    log_fn,
                    SHMCTL_LOG_PERM_PROC,
                    shmid,
                    cmd,
                    buf_addr,
                    proc_perm_error as CLong,
                );
                return proc_perm_error as CLong;
            }

            let modep = field_ptr::<u16>(base, offsets.obj_mode_offset);
            let pgshift = *field_ptr::<CInt>(base, offsets.obj_pgshift_offset);
            if (*modep & SHM_LOCKED) == 0 && (pgshift == 0 || pgshift == PAGE_SHIFT as CInt) {
                let Some(users_lock) = users_lock_fn else {
                    list_unlock();
                    shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                    return (-EINVAL) as CLong;
                };
                let Some(users_unlock) = users_unlock_fn else {
                    list_unlock();
                    shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                    return (-EINVAL) as CLong;
                };
                let Some(user_get) = shmlock_user_get_fn else {
                    list_unlock();
                    shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                    return (-EINVAL) as CLong;
                };

                users_lock();
                let mut user: *mut c_void = null_mut();
                let user_error = user_get(proc_ruid, &mut user);
                if user_error != 0 || user.is_null() {
                    users_unlock();
                    shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                    list_unlock();
                    shmctl_log(
                        log_fn,
                        SHMCTL_LOG_USER_LOOKUP,
                        shmid,
                        cmd,
                        buf_addr,
                        user_error as CLong,
                    );
                    return (-ENOMEM) as CLong;
                }

                let size = *field_ptr::<SizeT>(base, offsets.obj_real_segsz_offset) as CULong;
                let user_lockedp =
                    field_ptr::<SizeT>(user.cast::<u8>(), offsets.shmlock_user_locked_offset);
                let size_error = shmctl_shmlock_rlimit(
                    has_cap_ipc_lock,
                    rlim_memlock_cur,
                    *user_lockedp as CULong,
                    size,
                );
                if size_error != 0 {
                    users_unlock();
                    shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                    list_unlock();
                    shmctl_log(
                        log_fn,
                        SHMCTL_LOG_TOO_LARGE,
                        shmid,
                        cmd,
                        buf_addr,
                        size_error as CLong,
                    );
                    return size_error as CLong;
                }

                *modep |= SHM_LOCKED;
                *field_ptr::<*mut c_void>(base, offsets.obj_user_offset) = user;
                *user_lockedp = user_lockedp.read().wrapping_add(size as SizeT);
                users_unlock();
            }

            list_unlock();
            shmctl_unref_obj(obj, offsets, memobj_unref_fn);
            shmctl_log(log_fn, SHMCTL_LOG_EXIT, shmid, cmd, buf_addr, 0);
            0
        }
        SHM_UNLOCK => {
            list_lock();
            let mut obj: *mut c_void = null_mut();
            let error = lookup_obj(shmid, &mut obj);
            if error != 0 || obj.is_null() {
                let rc = if error != 0 { error } else { -EINVAL };
                list_unlock();
                shmctl_log(log_fn, SHMCTL_LOG_LOOKUP, shmid, cmd, buf_addr, rc as CLong);
                return rc as CLong;
            }

            let base = obj.cast::<u8>();
            let perm_error = shmctl_owner_or_cap(
                has_cap_ipc_lock,
                proc_euid,
                *field_ptr::<u32>(base, offsets.obj_uid_offset),
                *field_ptr::<u32>(base, offsets.obj_cuid_offset),
            );
            if perm_error != 0 {
                list_unlock();
                shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                shmctl_log(
                    log_fn,
                    SHMCTL_LOG_PERM_SHM,
                    shmid,
                    cmd,
                    buf_addr,
                    perm_error as CLong,
                );
                return perm_error as CLong;
            }

            let modep = field_ptr::<u16>(base, offsets.obj_mode_offset);
            let pgshift = *field_ptr::<CInt>(base, offsets.obj_pgshift_offset);
            if (*modep & SHM_LOCKED) != 0 && (pgshift == 0 || pgshift == PAGE_SHIFT as CInt) {
                let Some(users_lock) = users_lock_fn else {
                    list_unlock();
                    shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                    return (-EINVAL) as CLong;
                };
                let Some(users_unlock) = users_unlock_fn else {
                    list_unlock();
                    shmctl_unref_obj(obj, offsets, memobj_unref_fn);
                    return (-EINVAL) as CLong;
                };
                let size = *field_ptr::<SizeT>(base, offsets.obj_real_segsz_offset);
                users_lock();
                let user = *field_ptr::<*mut c_void>(base, offsets.obj_user_offset);
                *field_ptr::<*mut c_void>(base, offsets.obj_user_offset) = null_mut();
                if !user.is_null() {
                    let lockedp =
                        field_ptr::<SizeT>(user.cast::<u8>(), offsets.shmlock_user_locked_offset);
                    *lockedp = lockedp.read().wrapping_sub(size);
                    if *lockedp == 0 {
                        if let Some(user_free) = shmlock_user_free_fn {
                            user_free(user);
                        }
                    }
                }
                users_unlock();
                *modep &= !SHM_LOCKED;
            }

            list_unlock();
            shmctl_unref_obj(obj, offsets, memobj_unref_fn);
            shmctl_log(log_fn, SHMCTL_LOG_EXIT, shmid, cmd, buf_addr, 0);
            0
        }
        SHM_INFO => {
            list_lock();
            let copy_error = copy_to_user(buf_addr, shm_info.cast::<u8>(), offsets.shm_info_size);
            if copy_error != 0 {
                list_unlock();
                shmctl_log(log_fn, SHMCTL_LOG_COPY, shmid, cmd, buf_addr, copy_error);
                return copy_error;
            }
            let mut maxi = get_max_index();
            if maxi < 0 {
                maxi = 0;
            }
            list_unlock();
            shmctl_log(log_fn, SHMCTL_LOG_EXIT, shmid, cmd, buf_addr, maxi as CLong);
            maxi as CLong
        }
        _ => {
            shmctl_log(
                log_fn,
                SHMCTL_LOG_EINVAL,
                shmid,
                cmd,
                buf_addr,
                (-EINVAL) as CLong,
            );
            (-EINVAL) as CLong
        }
    }
}

#[inline(always)]
unsafe fn search_free_space_log(
    log_fn: Option<SearchFreeSpaceLogFn>,
    event: CInt,
    len: SizeT,
    pgshift: CInt,
    addr: CULong,
    error: CInt,
) {
    if let Some(log) = log_fn {
        log(event, len, pgshift, addr, error);
    }
}

#[no_mangle]
pub unsafe extern "C" fn search_free_space_body_result(
    vm: *mut c_void,
    region: *mut c_void,
    len: SizeT,
    pgshift: CInt,
    addrp: *mut CULong,
    region_user_end_offset: SizeT,
    region_map_end_offset: SizeT,
    range_end_offset: SizeT,
    lookup_range_fn: Option<MsyncLookupRangeFn>,
    log_fn: Option<SearchFreeSpaceLogFn>,
) -> CInt {
    let mut addr = if !addrp.is_null() { *addrp } else { 0 };
    search_free_space_log(log_fn, SEARCH_FREE_SPACE_LOG_ENTER, len, pgshift, addr, 0);

    if addrp.is_null() || pgshift < 0 || pgshift >= (size_of::<SizeT>() * 8) as CInt {
        search_free_space_log(
            log_fn,
            SEARCH_FREE_SPACE_LOG_EXIT,
            len,
            pgshift,
            addr,
            -EINVAL,
        );
        return -EINVAL;
    }

    let lookup_range = if let Some(lookup) = lookup_range_fn {
        lookup
    } else {
        search_free_space_log(
            log_fn,
            SEARCH_FREE_SPACE_LOG_EXIT,
            len,
            pgshift,
            addr,
            -EINVAL,
        );
        return -EINVAL;
    };

    let user_end = *field_ptr::<CULong>(region.cast::<u8>(), region_user_end_offset);
    let pgsize = 1usize << (pgshift as usize);
    let pgmask = (pgsize as CULong).wrapping_sub(1);

    if addr != 0 {
        if user_end <= addr || user_end.wrapping_sub(len as CULong) < addr {
            search_free_space_log(
                log_fn,
                SEARCH_FREE_SPACE_LOG_OUTSIDE,
                len,
                pgshift,
                addr,
                -ENOMEM,
            );
            search_free_space_log(
                log_fn,
                SEARCH_FREE_SPACE_LOG_EXIT,
                len,
                pgshift,
                addr,
                -ENOMEM,
            );
            return -ENOMEM;
        }

        let range = lookup_range(vm, addr, addr.wrapping_add(len as CULong));
        if range.is_null() {
            search_free_space_log(log_fn, SEARCH_FREE_SPACE_LOG_EXIT, len, pgshift, addr, 0);
            return 0;
        }
    }

    addr = *field_ptr::<CULong>(region.cast::<u8>(), region_map_end_offset);
    loop {
        addr = addr.wrapping_add(pgmask) & !pgmask;
        if user_end <= addr || user_end.wrapping_sub(len as CULong) < addr {
            search_free_space_log(
                log_fn,
                SEARCH_FREE_SPACE_LOG_OUTSIDE,
                len,
                pgshift,
                addr,
                -ENOMEM,
            );
            search_free_space_log(
                log_fn,
                SEARCH_FREE_SPACE_LOG_EXIT,
                len,
                pgshift,
                addr,
                -ENOMEM,
            );
            return -ENOMEM;
        }

        let range = lookup_range(vm, addr, addr.wrapping_add(len as CULong));
        if range.is_null() {
            break;
        }
        addr = *field_ptr::<CULong>(range.cast::<u8>(), range_end_offset);
    }

    *field_ptr::<CULong>(region.cast::<u8>(), region_map_end_offset) =
        addr.wrapping_add(len as CULong);
    *addrp = addr;
    search_free_space_log(log_fn, SEARCH_FREE_SPACE_LOG_EXIT, len, pgshift, addr, 0);
    0
}

#[no_mangle]
pub extern "C" fn set_host_vma_body_result(
    _addr: CULong,
    _len: SizeT,
    _prot: CInt,
    _holding_memory_range_lock: CInt,
) -> CInt {
    0
}

#[no_mangle]
pub unsafe extern "C" fn mprotect_prepare_range(
    start: CULong,
    len0: SizeT,
    user_start: CULong,
    user_end: CULong,
    lenp: *mut SizeT,
    endp: *mut CULong,
) -> CInt {
    let len = len0.wrapping_add((PAGE_SIZE - 1) as SizeT) & PAGE_MASK as SizeT;
    let end = start.wrapping_add(len as CULong);

    write(lenp, len);
    write(endp, end);

    if (start & (PAGE_SIZE - 1)) != 0 {
        return -EINVAL;
    }

    if start < user_start || user_end <= start || user_end.wrapping_sub(start) < len as CULong {
        return -ENOMEM;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mprotect_split_needed_result(
    range_start: CULong,
    range_end: CULong,
    addr: CULong,
    end: CULong,
    split_startp: *mut CInt,
    split_endp: *mut CInt,
) {
    if !split_startp.is_null() {
        unsafe {
            *split_startp = (range_start < addr) as CInt;
        }
    }
    if !split_endp.is_null() {
        unsafe {
            *split_endp = (end < range_end) as CInt;
        }
    }
}

#[no_mangle]
pub extern "C" fn mprotect_write_changed_result(range_flags: CULong, protflags: CULong) -> CInt {
    (((range_flags ^ protflags) & VR_PROT_WRITE) != 0) as CInt
}

#[inline(always)]
unsafe fn mprotect_log(
    log: Option<MprotectLogFn>,
    event: CInt,
    cpu: CInt,
    start: CULong,
    len: SizeT,
    prot: CInt,
    addr: CULong,
    range_start: CULong,
    range_end: CULong,
    range_flags: CULong,
    protflags: CULong,
    denied: CULong,
    error: CInt,
) {
    let Some(log) = log else {
        return;
    };

    let mut record = MaybeUninit::<MprotectLogRecord>::uninit();
    let ptr = record.as_mut_ptr();
    write_volatile(&raw mut (*ptr).event, event);
    write_volatile(&raw mut (*ptr).cpu, cpu);
    write_volatile(&raw mut (*ptr).start, start);
    write_volatile(&raw mut (*ptr).len, len);
    write_volatile(&raw mut (*ptr).prot, prot);
    write_volatile(&raw mut (*ptr).addr, addr);
    write_volatile(&raw mut (*ptr).range_start, range_start);
    write_volatile(&raw mut (*ptr).range_end, range_end);
    write_volatile(&raw mut (*ptr).range_flags, range_flags);
    write_volatile(&raw mut (*ptr).protflags, protflags);
    write_volatile(&raw mut (*ptr).denied, denied);
    write_volatile(&raw mut (*ptr).error, error);
    log(ptr as *const MprotectLogRecord);
}

#[no_mangle]
pub unsafe extern "C" fn mprotect_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    start: CULong,
    len0: SizeT,
    prot: CInt,
    user_start: CULong,
    user_end: CULong,
    straight_va: CULong,
    straight_len: SizeT,
    cpu: CInt,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_flag_offset: SizeT,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    next_fn: Option<MsyncNextRangeFn>,
    split_fn: Option<MemlockSplitFn>,
    join_fn: Option<MemlockJoinFn>,
    change_fn: Option<MprotectChangeFn>,
    set_host_vma_fn: Option<MprotectSetHostVmaFn>,
    flush_nfo_fn: Option<MprotectFlushFn>,
    flush_tlb_fn: Option<MprotectFlushFn>,
    log_fn: Option<MprotectLogFn>,
) -> CInt {
    let protflags = ((prot as CULong) << 16) & VR_PROT_MASK;
    mprotect_log(
        log_fn,
        MPROTECT_LOG_ENTER,
        cpu,
        start,
        len0,
        prot,
        0,
        0,
        0,
        0,
        protflags,
        0,
        0,
    );

    let mut len: SizeT = 0;
    let mut end: CULong = 0;
    let mut error = mprotect_prepare_range(start, len0, user_start, user_end, &mut len, &mut end);
    if error != 0 {
        mprotect_log(
            log_fn,
            MPROTECT_LOG_INVALID_RANGE,
            cpu,
            start,
            len0,
            prot,
            0,
            0,
            0,
            0,
            protflags,
            0,
            error,
        );
        return error;
    }

    if len == 0 {
        return 0;
    }

    if straight_va != 0
        && start >= straight_va
        && end <= straight_va.wrapping_add(straight_len as CULong)
    {
        mprotect_log(
            log_fn,
            MPROTECT_LOG_STRAIGHT_IGNORED,
            cpu,
            start,
            len0,
            prot,
            0,
            straight_va,
            straight_va.wrapping_add(straight_len as CULong),
            0,
            protflags,
            0,
            0,
        );
        mprotect_log(
            log_fn,
            MPROTECT_LOG_EXIT,
            cpu,
            start,
            len0,
            prot,
            0,
            0,
            0,
            0,
            protflags,
            0,
            0,
        );
        return 0;
    }

    if let Some(flush_nfo) = flush_nfo_fn {
        flush_nfo();
    }

    if let Some(lock) = lock_fn {
        lock(range_lock);
    }

    let first = if let Some(lookup) = lookup_fn {
        lookup(vm, start, start.wrapping_add(PAGE_SIZE))
    } else {
        core::ptr::null_mut()
    };
    let mut changed = core::ptr::null_mut::<c_void>();
    let mut ro_changed = 0;
    let mut addr = start;

    while addr < end {
        let mut range = if changed.is_null() {
            first
        } else if let Some(next) = next_fn {
            next(vm, changed)
        } else {
            core::ptr::null_mut()
        };

        if range.is_null() || addr < memlock_range_ulong(range, range_start_offset) {
            error = -ENOMEM;
            let (range_start, range_end, range_flags) = if range.is_null() {
                (0, 0, 0)
            } else {
                (
                    memlock_range_ulong(range, range_start_offset),
                    memlock_range_ulong(range, range_end_offset),
                    memlock_range_ulong(range, range_flag_offset),
                )
            };
            mprotect_log(
                log_fn,
                MPROTECT_LOG_NOT_CONTIG,
                cpu,
                start,
                len0,
                prot,
                addr,
                range_start,
                range_end,
                range_flags,
                protflags,
                0,
                error,
            );
            break;
        }

        let mut range_flags = memlock_range_ulong(range, range_flag_offset);
        let denied = protflags & !((range_flags & VR_MAXPROT_MASK) >> 4);
        if denied != 0 {
            error = -EACCES;
            mprotect_log(
                log_fn,
                MPROTECT_LOG_DENIED,
                cpu,
                start,
                len0,
                prot,
                addr,
                memlock_range_ulong(range, range_start_offset),
                memlock_range_ulong(range, range_end_offset),
                range_flags,
                protflags,
                denied,
                error,
            );
            break;
        }

        if range_has_disallowed_change_flags(range_flags) != 0 {
            error = -ENOMEM;
            mprotect_log(
                log_fn,
                MPROTECT_LOG_CANNOT_CHANGE,
                cpu,
                start,
                len0,
                prot,
                addr,
                memlock_range_ulong(range, range_start_offset),
                memlock_range_ulong(range, range_end_offset),
                range_flags,
                protflags,
                0,
                error,
            );
            break;
        }

        let mut split_start = 0;
        let mut split_end = 0;
        mprotect_split_needed_result(
            memlock_range_ulong(range, range_start_offset),
            memlock_range_ulong(range, range_end_offset),
            addr,
            end,
            &mut split_start,
            &mut split_end,
        );
        if split_start != 0 {
            error = if let Some(split) = split_fn {
                split(vm, range, addr, &mut range)
            } else {
                -EINVAL
            };
            if error != 0 {
                mprotect_log(
                    log_fn,
                    MPROTECT_LOG_SPLIT_FAILED,
                    cpu,
                    start,
                    len0,
                    prot,
                    addr,
                    memlock_range_ulong(range, range_start_offset),
                    memlock_range_ulong(range, range_end_offset),
                    memlock_range_ulong(range, range_flag_offset),
                    protflags,
                    0,
                    error,
                );
                break;
            }
        }
        if split_end != 0 {
            error = if let Some(split) = split_fn {
                split(vm, range, end, core::ptr::null_mut())
            } else {
                -EINVAL
            };
            if error != 0 {
                mprotect_log(
                    log_fn,
                    MPROTECT_LOG_SPLIT_FAILED,
                    cpu,
                    start,
                    len0,
                    prot,
                    end,
                    memlock_range_ulong(range, range_start_offset),
                    memlock_range_ulong(range, range_end_offset),
                    memlock_range_ulong(range, range_flag_offset),
                    protflags,
                    0,
                    error,
                );
                break;
            }
        }

        range_flags = memlock_range_ulong(range, range_flag_offset);
        if mprotect_write_changed_result(range_flags, protflags) != 0 {
            ro_changed = 1;
        }

        error = if let Some(change) = change_fn {
            change(vm, range, protflags)
        } else {
            -EINVAL
        };
        if error != 0 {
            mprotect_log(
                log_fn,
                MPROTECT_LOG_CHANGE_FAILED,
                cpu,
                start,
                len0,
                prot,
                addr,
                memlock_range_ulong(range, range_start_offset),
                memlock_range_ulong(range, range_end_offset),
                memlock_range_ulong(range, range_flag_offset),
                protflags,
                0,
                error,
            );
            break;
        }

        if changed.is_null() {
            changed = range;
        } else {
            let join_error = if let Some(join) = join_fn {
                join(vm, changed, range)
            } else {
                -EINVAL
            };
            if join_error != 0 {
                mprotect_log(
                    log_fn,
                    MPROTECT_LOG_JOIN_FAILED,
                    cpu,
                    start,
                    len0,
                    prot,
                    addr,
                    memlock_range_ulong(changed, range_start_offset),
                    memlock_range_ulong(range, range_end_offset),
                    memlock_range_ulong(range, range_flag_offset),
                    protflags,
                    0,
                    join_error,
                );
                changed = range;
            }
        }

        addr = memlock_range_ulong(changed, range_end_offset);
    }

    if let Some(flush_tlb) = flush_tlb_fn {
        flush_tlb();
    }
    if ro_changed != 0 && error == 0 {
        error = if let Some(set_host_vma) = set_host_vma_fn {
            set_host_vma(start, len, prot & (PROT_READ | PROT_WRITE | PROT_EXEC), 1)
        } else {
            -EINVAL
        };
        if error != 0 {
            mprotect_log(
                log_fn,
                MPROTECT_LOG_SET_HOST_FAILED,
                cpu,
                start,
                len0,
                prot,
                0,
                0,
                0,
                0,
                protflags,
                0,
                error,
            );
        }
    }
    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }

    mprotect_log(
        log_fn,
        MPROTECT_LOG_EXIT,
        cpu,
        start,
        len0,
        prot,
        0,
        0,
        0,
        0,
        protflags,
        0,
        error,
    );
    error
}

#[no_mangle]
pub extern "C" fn mlockall_policy_result(
    flags: CInt,
    is_privileged: CInt,
    memlock_cur: u64,
) -> CInt {
    if flags == 0 || (flags & !(MCL_CURRENT | MCL_FUTURE)) != 0 {
        return -EINVAL;
    }

    if is_privileged != 0 {
        return 0;
    }

    if memlock_cur != 0 {
        return -ENOMEM;
    }

    -EPERM
}

#[no_mangle]
pub unsafe extern "C" fn remap_file_pages_prepare(
    start0: CULong,
    size: SizeT,
    prot: CInt,
    pgoff: SizeT,
    startp: *mut CULong,
    endp: *mut CULong,
    offp: *mut CLong,
) -> CInt {
    let start = start0 & PAGE_MASK;
    let end = start.wrapping_add(size as CULong);

    write(startp, start);
    write(endp, end);
    write(offp, (pgoff as CLong) << PAGE_SHIFT);

    if size == 0
        || (size & (PAGE_SIZE as SizeT - 1)) != 0
        || prot != 0
        || PGOFF_LIMIT <= pgoff
        || PGOFF_LIMIT.wrapping_sub(pgoff) < (size / PAGE_SIZE as SizeT)
        || !(start < end || end == 0)
    {
        return -EINVAL;
    }

    0
}

#[inline(always)]
unsafe fn remap_file_pages_log(
    log: Option<RemapFilePagesLogFn>,
    event: CInt,
    cpu: CInt,
    start0: CULong,
    size: SizeT,
    prot: CInt,
    pgoff: SizeT,
    flags: CInt,
    start: CULong,
    end: CULong,
    range_start: CULong,
    range_end: CULong,
    range_flags: CULong,
    memobj: *mut c_void,
    off: CLong,
    error: CInt,
) {
    let Some(log) = log else {
        return;
    };

    let mut record = MaybeUninit::<RemapFilePagesLogRecord>::uninit();
    let ptr = record.as_mut_ptr();
    write_volatile(&raw mut (*ptr).event, event);
    write_volatile(&raw mut (*ptr).cpu, cpu);
    write_volatile(&raw mut (*ptr).start0, start0);
    write_volatile(&raw mut (*ptr).size, size);
    write_volatile(&raw mut (*ptr).prot, prot);
    write_volatile(&raw mut (*ptr).pgoff, pgoff);
    write_volatile(&raw mut (*ptr).flags, flags);
    write_volatile(&raw mut (*ptr).start, start);
    write_volatile(&raw mut (*ptr).end, end);
    write_volatile(&raw mut (*ptr).range_start, range_start);
    write_volatile(&raw mut (*ptr).range_end, range_end);
    write_volatile(&raw mut (*ptr).range_flags, range_flags);
    write_volatile(&raw mut (*ptr).memobj, memobj);
    write_volatile(&raw mut (*ptr).off, off);
    write_volatile(&raw mut (*ptr).error, error);
    log(ptr as *const RemapFilePagesLogRecord);
}

#[no_mangle]
pub unsafe extern "C" fn remap_file_pages_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    start0: CULong,
    size: SizeT,
    prot: CInt,
    pgoff: SizeT,
    flags: CInt,
    cpu: CInt,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_flag_offset: SizeT,
    range_memobj_offset: SizeT,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    callable_fn: Option<RemapFilePagesCallableFn>,
    remap_fn: Option<RemapFilePagesRemapFn>,
    clear_host_fn: Option<RemapFilePagesClearHostFn>,
    populate_fn: Option<MemlockPopulateFn>,
    flush_nfo_fn: Option<MprotectFlushFn>,
    log_fn: Option<RemapFilePagesLogFn>,
) -> CInt {
    let mut start: CULong = 0;
    let mut end: CULong = 0;
    let mut off: CLong = 0;
    let mut range = core::ptr::null_mut::<c_void>();
    let mut memobj = core::ptr::null_mut::<c_void>();
    let mut need_populate = 0;

    remap_file_pages_log(
        log_fn,
        REMAP_FILE_PAGES_LOG_ENTER,
        cpu,
        start0,
        size,
        prot,
        pgoff,
        flags,
        0,
        0,
        0,
        0,
        0,
        core::ptr::null_mut(),
        0,
        0,
    );

    if let Some(lock) = lock_fn {
        lock(range_lock);
    }

    let mut error =
        remap_file_pages_prepare(start0, size, prot, pgoff, &mut start, &mut end, &mut off);
    if error != 0 {
        remap_file_pages_log(
            log_fn,
            REMAP_FILE_PAGES_LOG_INVALID_ARGS,
            cpu,
            start0,
            size,
            prot,
            pgoff,
            flags,
            start,
            end,
            0,
            0,
            0,
            core::ptr::null_mut(),
            off,
            error,
        );
    } else {
        range = if let Some(lookup) = lookup_fn {
            lookup(vm, start, end)
        } else {
            core::ptr::null_mut()
        };
        if !range.is_null() {
            memobj = memlock_range_ptr(range, range_memobj_offset);
        }

        let mut invalid = range.is_null();
        let mut range_start = 0;
        let mut range_end = 0;
        let mut range_flags = 0;
        if !range.is_null() {
            range_start = memlock_range_ulong(range, range_start_offset);
            range_end = memlock_range_ulong(range, range_end_offset);
            range_flags = memlock_range_ulong(range, range_flag_offset);
            invalid = start < range_start
                || range_end < end
                || (range_flags & VR_PRIVATE) != 0
                || range_has_disallowed_change_flags(range_flags) != 0;
            if !invalid {
                invalid = if let Some(callable) = callable_fn {
                    callable(memobj) == 0
                } else {
                    true
                };
            }
        }

        if invalid {
            error = -EINVAL;
            remap_file_pages_log(
                log_fn,
                REMAP_FILE_PAGES_LOG_INVALID_VMR,
                cpu,
                start0,
                size,
                prot,
                pgoff,
                flags,
                start,
                end,
                range_start,
                range_end,
                range_flags,
                memobj,
                off,
                error,
            );
        } else {
            if let Some(flush_nfo) = flush_nfo_fn {
                flush_nfo();
            }

            range_flags |= VR_FILEOFF;
            memlock_range_set_ulong(range, range_flag_offset, range_flags);
            error = if let Some(remap) = remap_fn {
                remap(vm, range, start, end, off)
            } else {
                -EINVAL
            };
            if error != 0 {
                remap_file_pages_log(
                    log_fn,
                    REMAP_FILE_PAGES_LOG_REMAP_FAILED,
                    cpu,
                    start0,
                    size,
                    prot,
                    pgoff,
                    flags,
                    start,
                    end,
                    memlock_range_ulong(range, range_start_offset),
                    memlock_range_ulong(range, range_end_offset),
                    memlock_range_ulong(range, range_flag_offset),
                    memobj,
                    off,
                    error,
                );
            } else {
                if let Some(clear_host) = clear_host_fn {
                    clear_host(start, size, 1);
                }
                if (memlock_range_ulong(range, range_flag_offset) & VR_LOCKED) != 0 {
                    need_populate = 1;
                }
            }
        }
    }

    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }

    if need_populate != 0 {
        let populate_error = if let Some(populate) = populate_fn {
            populate(vm, start, size)
        } else {
            -EINVAL
        };
        if populate_error != 0 {
            remap_file_pages_log(
                log_fn,
                REMAP_FILE_PAGES_LOG_POPULATE_FAILED,
                cpu,
                start0,
                size,
                prot,
                pgoff,
                flags,
                start,
                end,
                if range.is_null() {
                    0
                } else {
                    memlock_range_ulong(range, range_start_offset)
                },
                if range.is_null() {
                    0
                } else {
                    memlock_range_ulong(range, range_end_offset)
                },
                if range.is_null() {
                    0
                } else {
                    memlock_range_ulong(range, range_flag_offset)
                },
                memobj,
                off,
                populate_error,
            );
        }
    }

    remap_file_pages_log(
        log_fn,
        REMAP_FILE_PAGES_LOG_EXIT,
        cpu,
        start0,
        size,
        prot,
        pgoff,
        flags,
        start,
        end,
        if range.is_null() {
            0
        } else {
            memlock_range_ulong(range, range_start_offset)
        },
        if range.is_null() {
            0
        } else {
            memlock_range_ulong(range, range_end_offset)
        },
        if range.is_null() {
            0
        } else {
            memlock_range_ulong(range, range_flag_offset)
        },
        memobj,
        off,
        error,
    );
    error
}

#[no_mangle]
pub unsafe extern "C" fn mremap_prepare_args(
    oldaddr: CULong,
    oldsize0: SizeT,
    newsize0: SizeT,
    flags: CInt,
    newaddr: CULong,
    user_start: CULong,
    user_end: CULong,
    oldsizep: *mut SizeT,
    newsizep: *mut SizeT,
    oldendp: *mut CULong,
    no_opp: *mut CInt,
) -> CInt {
    let oldsize = oldsize0.wrapping_add((PAGE_SIZE - 1) as SizeT) & PAGE_MASK as SizeT;
    let newsize = newsize0.wrapping_add((PAGE_SIZE - 1) as SizeT) & PAGE_MASK as SizeT;
    let oldend = oldaddr.wrapping_add(oldsize as CULong);

    write(oldsizep, oldsize);
    write(newsizep, newsize);
    write(oldendp, oldend);
    write(no_opp, 0);

    if (oldaddr & (PAGE_SIZE - 1)) != 0
        || newsize == 0
        || (flags & !(MREMAP_MAYMOVE | MREMAP_FIXED)) != 0
        || ((flags & MREMAP_FIXED) != 0 && (flags & MREMAP_MAYMOVE) == 0)
        || ((flags & MREMAP_FIXED) != 0 && (newaddr & (PAGE_SIZE - 1)) != 0)
    {
        return -EINVAL;
    }

    if (flags & MREMAP_FIXED) == 0 && oldsize == newsize {
        write(no_opp, 1);
        return 0;
    }

    if oldend < oldaddr {
        return -EINVAL;
    }

    if newsize as CULong > user_end.wrapping_sub(user_start) {
        return -ENOMEM;
    }

    0
}

#[no_mangle]
pub extern "C" fn mremap_fixed_range_result(
    newstart: CULong,
    user_start: CULong,
    oldstart: CULong,
    oldend: CULong,
    newend: CULong,
) -> CInt {
    if newstart < user_start {
        return -EPERM;
    }

    if newstart < oldend && oldstart < newend {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn mremap_maymove_result(flags: CInt) -> CInt {
    if (flags & MREMAP_MAYMOVE) == 0 {
        -ENOMEM
    } else {
        0
    }
}

#[inline(always)]
unsafe fn mremap_log(
    log: Option<MremapLogFn>,
    event: CInt,
    oldaddr: CULong,
    oldsize0: SizeT,
    newsize0: SizeT,
    flags: CInt,
    newaddr: CULong,
    oldstart: CULong,
    oldend: CULong,
    newstart: CULong,
    newend: CULong,
    range_start: CULong,
    range_end: CULong,
    range_flags: CULong,
    lckstart: CULong,
    lckend: CULong,
    error: CInt,
) {
    let Some(log) = log else {
        return;
    };

    let mut record = MaybeUninit::<MremapLogRecord>::uninit();
    let ptr = record.as_mut_ptr();
    write_volatile(&raw mut (*ptr).event, event);
    write_volatile(&raw mut (*ptr).oldaddr, oldaddr);
    write_volatile(&raw mut (*ptr).oldsize0, oldsize0);
    write_volatile(&raw mut (*ptr).newsize0, newsize0);
    write_volatile(&raw mut (*ptr).flags, flags);
    write_volatile(&raw mut (*ptr).newaddr, newaddr);
    write_volatile(&raw mut (*ptr).oldstart, oldstart);
    write_volatile(&raw mut (*ptr).oldend, oldend);
    write_volatile(&raw mut (*ptr).newstart, newstart);
    write_volatile(&raw mut (*ptr).newend, newend);
    write_volatile(&raw mut (*ptr).range_start, range_start);
    write_volatile(&raw mut (*ptr).range_end, range_end);
    write_volatile(&raw mut (*ptr).range_flags, range_flags);
    write_volatile(&raw mut (*ptr).lckstart, lckstart);
    write_volatile(&raw mut (*ptr).lckend, lckend);
    write_volatile(&raw mut (*ptr).error, error);
    log(ptr as *const MremapLogRecord);
}

#[inline(always)]
unsafe fn mremap_range_snapshot(
    range: *mut c_void,
    start_offset: SizeT,
    end_offset: SizeT,
    flag_offset: SizeT,
) -> (CULong, CULong, CULong) {
    if range.is_null() {
        (0, 0, 0)
    } else {
        (
            memlock_range_ulong(range, start_offset),
            memlock_range_ulong(range, end_offset),
            memlock_range_ulong(range, flag_offset),
        )
    }
}

#[inline(always)]
unsafe fn mremap_log_range(
    log_fn: Option<MremapLogFn>,
    event: CInt,
    oldaddr: CULong,
    oldsize0: SizeT,
    newsize0: SizeT,
    flags: CInt,
    newaddr: CULong,
    oldstart: CULong,
    oldend: CULong,
    newstart: CULong,
    newend: CULong,
    range: *mut c_void,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_flag_offset: SizeT,
    lckstart: CULong,
    lckend: CULong,
    error: CInt,
) {
    let (range_start, range_end, range_flags) = mremap_range_snapshot(
        range,
        range_start_offset,
        range_end_offset,
        range_flag_offset,
    );
    mremap_log(
        log_fn,
        event,
        oldaddr,
        oldsize0,
        newsize0,
        flags,
        newaddr,
        oldstart,
        oldend,
        newstart,
        newend,
        range_start,
        range_end,
        range_flags,
        lckstart,
        lckend,
        error,
    );
}

#[inline(always)]
unsafe fn mremap_relocate(
    vm: *mut c_void,
    pte_lock: *mut c_void,
    page_table: *mut c_void,
    oldaddr: CULong,
    oldsize0: SizeT,
    oldsize: SizeT,
    newsize0: SizeT,
    newsize: SizeT,
    flags: CInt,
    newaddr: CULong,
    oldstart: CULong,
    oldend: CULong,
    newstart: CULong,
    newend: CULong,
    range: *mut *mut c_void,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_flag_offset: SizeT,
    range_memobj_offset: SizeT,
    range_objoff_offset: SizeT,
    lckstart: *mut CULong,
    lckend: *mut CULong,
    munmap_fn: Option<MunmapDoFn>,
    memobj_ref_fn: Option<MremapMemobjRefFn>,
    memobj_unref_fn: Option<MremapMemobjRefFn>,
    add_range_fn: Option<MremapAddRangeFn>,
    flush_nfo_fn: Option<MprotectFlushFn>,
    pte_lock_fn: Option<SyscallRwlockFn>,
    pte_unlock_fn: Option<SyscallRwlockFn>,
    split_fn: Option<MemlockSplitFn>,
    move_pte_fn: Option<MremapMovePteFn>,
    log_fn: Option<MremapLogFn>,
) -> CInt {
    let mut error: CInt;

    if (flags & MREMAP_FIXED) != 0 {
        error = if let Some(munmap) = munmap_fn {
            munmap(newstart as *mut c_void, newsize, 1)
        } else {
            -EINVAL
        };
        if error != 0 {
            mremap_log(
                log_fn,
                MREMAP_LOG_FIXED_MUNMAP_FAILED,
                oldaddr,
                oldsize0,
                newsize0,
                flags,
                newaddr,
                oldstart,
                oldend,
                newstart,
                newend,
                0,
                0,
                0,
                *lckstart,
                *lckend,
                error,
            );
            return error;
        }
    }

    let memobj = memlock_range_ptr(*range, range_memobj_offset);
    if !memobj.is_null() {
        if let Some(memobj_ref) = memobj_ref_fn {
            memobj_ref(memobj);
        }
    }
    let objoff = memlock_range_ulong(*range, range_objoff_offset)
        .wrapping_add(oldstart - memlock_range_ulong(*range, range_start_offset));
    error = if let Some(add_range) = add_range_fn {
        add_range(
            vm,
            newstart,
            newend,
            -1,
            memlock_range_ulong(*range, range_flag_offset),
            memobj,
            objoff,
        )
    } else {
        -EINVAL
    };
    if error != 0 {
        mremap_log_range(
            log_fn,
            MREMAP_LOG_ADD_FAILED,
            oldaddr,
            oldsize0,
            newsize0,
            flags,
            newaddr,
            oldstart,
            oldend,
            newstart,
            newend,
            *range,
            range_start_offset,
            range_end_offset,
            range_flag_offset,
            *lckstart,
            *lckend,
            error,
        );
        if !memobj.is_null() {
            if let Some(memobj_unref) = memobj_unref_fn {
                memobj_unref(memobj);
            }
        }
        return error;
    }

    if let Some(flush) = flush_nfo_fn {
        flush();
    }
    if (memlock_range_ulong(*range, range_flag_offset) & VR_LOCKED) != 0 {
        *lckstart = newstart;
        *lckend = newend;
    }

    if oldsize > 0 {
        let move_size = if oldsize < newsize { oldsize } else { newsize };
        if let Some(lock) = pte_lock_fn {
            lock(pte_lock);
        }
        if memlock_range_ulong(*range, range_start_offset) != oldstart {
            error = if let Some(split) = split_fn {
                split(vm, *range, oldstart, range)
            } else {
                -EINVAL
            };
        }
        if error == 0
            && memlock_range_ulong(*range, range_end_offset)
                != oldstart.wrapping_add(move_size as CULong)
        {
            error = if let Some(split) = split_fn {
                split(
                    vm,
                    *range,
                    oldstart.wrapping_add(move_size as CULong),
                    core::ptr::null_mut(),
                )
            } else {
                -EINVAL
            };
        }
        if error == 0 {
            error = if let Some(move_pte) = move_pte_fn {
                move_pte(
                    page_table,
                    vm,
                    oldstart as *mut c_void,
                    newstart as *mut c_void,
                    move_size,
                    *range,
                )
            } else {
                -EINVAL
            };
        }
        if let Some(unlock) = pte_unlock_fn {
            unlock(pte_lock);
        }
        if error != 0 {
            mremap_log(
                log_fn,
                if error == -EINVAL {
                    MREMAP_LOG_SPLIT_FAILED
                } else {
                    MREMAP_LOG_MOVE_FAILED
                },
                oldaddr,
                oldsize0,
                newsize0,
                flags,
                newaddr,
                oldstart,
                oldend,
                newstart,
                newend,
                0,
                0,
                0,
                *lckstart,
                *lckend,
                error,
            );
            return error;
        }

        error = if let Some(munmap) = munmap_fn {
            munmap(oldstart as *mut c_void, oldsize, 1)
        } else {
            -EINVAL
        };
        if error != 0 {
            mremap_log(
                log_fn,
                MREMAP_LOG_RELOCATE_MUNMAP_FAILED,
                oldaddr,
                oldsize0,
                newsize0,
                flags,
                newaddr,
                oldstart,
                oldend,
                newstart,
                newend,
                0,
                0,
                0,
                *lckstart,
                *lckend,
                error,
            );
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn mremap_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    pte_lock: *mut c_void,
    page_table: *mut c_void,
    oldaddr: CULong,
    oldsize0: SizeT,
    newsize0: SizeT,
    flags: CInt,
    newaddr: CULong,
    user_start: CULong,
    user_end: CULong,
    straight_va: CULong,
    straight_len: SizeT,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_flag_offset: SizeT,
    range_pgshift_offset: SizeT,
    range_memobj_offset: SizeT,
    range_objoff_offset: SizeT,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    extend_fn: Option<MremapExtendFn>,
    flush_nfo_fn: Option<MprotectFlushFn>,
    search_fn: Option<MremapSearchFn>,
    munmap_fn: Option<MunmapDoFn>,
    memobj_ref_fn: Option<MremapMemobjRefFn>,
    memobj_unref_fn: Option<MremapMemobjRefFn>,
    add_range_fn: Option<MremapAddRangeFn>,
    pte_lock_fn: Option<SyscallRwlockFn>,
    pte_unlock_fn: Option<SyscallRwlockFn>,
    split_fn: Option<MemlockSplitFn>,
    move_pte_fn: Option<MremapMovePteFn>,
    populate_fn: Option<MemlockPopulateFn>,
    log_fn: Option<MremapLogFn>,
) -> CLong {
    let mut oldsize: SizeT = 0;
    let mut newsize: SizeT = 0;
    let oldstart = oldaddr;
    let mut oldend: CULong = 0;
    let mut no_op = 0;
    let mut range = core::ptr::null_mut::<c_void>();
    let mut need_relocate = 0;
    let mut newstart: CULong = 0;
    let mut newend: CULong = 0;
    let mut lckstart = CULong::MAX;
    let mut lckend = CULong::MAX;

    mremap_log(
        log_fn,
        MREMAP_LOG_ENTER,
        oldaddr,
        oldsize0,
        newsize0,
        flags,
        newaddr,
        oldstart,
        oldend,
        newstart,
        newend,
        0,
        0,
        0,
        lckstart,
        lckend,
        0,
    );

    if straight_va != 0
        && oldaddr >= straight_va
        && oldaddr < straight_va.wrapping_add(straight_len as CULong)
    {
        let error = -EINVAL;
        mremap_log(
            log_fn,
            MREMAP_LOG_STRAIGHT_REJECT,
            oldaddr,
            oldsize0,
            newsize0,
            flags,
            newaddr,
            oldstart,
            oldend,
            newstart,
            newend,
            straight_va,
            straight_va.wrapping_add(straight_len as CULong),
            0,
            lckstart,
            lckend,
            error,
        );
        return error as CLong;
    }

    if let Some(lock) = lock_fn {
        lock(range_lock);
    }

    let mut error = mremap_prepare_args(
        oldaddr,
        oldsize0,
        newsize0,
        flags,
        newaddr,
        user_start,
        user_end,
        &mut oldsize,
        &mut newsize,
        &mut oldend,
        &mut no_op,
    );

    if error != 0 {
        mremap_log(
            log_fn,
            if error == -ENOMEM {
                MREMAP_LOG_ALLOCATE_FAILED
            } else {
                MREMAP_LOG_INVALID
            },
            oldaddr,
            oldsize0,
            newsize0,
            flags,
            newaddr,
            oldstart,
            oldend,
            newstart,
            newend,
            0,
            0,
            0,
            lckstart,
            lckend,
            error,
        );
    } else if no_op != 0 {
        newstart = oldaddr;
    } else {
        range = if let Some(lookup) = lookup_fn {
            lookup(vm, oldstart, oldstart.wrapping_add(PAGE_SIZE))
        } else {
            core::ptr::null_mut()
        };

        let invalid = if range.is_null() {
            true
        } else {
            let range_start = memlock_range_ulong(range, range_start_offset);
            let range_end = memlock_range_ulong(range, range_end_offset);
            let range_flags = memlock_range_ulong(range, range_flag_offset);
            oldstart < range_start
                || range_end < oldend
                || (range_flags & VR_FILEOFF) != 0
                || range_has_disallowed_change_flags(range_flags) != 0
        };
        if invalid {
            error = -EFAULT;
            mremap_log_range(
                log_fn,
                MREMAP_LOG_LOOKUP_FAILED,
                oldaddr,
                oldsize0,
                newsize0,
                flags,
                newaddr,
                oldstart,
                oldend,
                newstart,
                newend,
                range,
                range_start_offset,
                range_end_offset,
                range_flag_offset,
                lckstart,
                lckend,
                error,
            );
        } else {
            if (flags & MREMAP_FIXED) != 0 {
                need_relocate = 1;
                newstart = newaddr;
                newend = newstart.wrapping_add(newsize as CULong);
                error = mremap_fixed_range_result(newstart, user_start, oldstart, oldend, newend);
                if error != 0 {
                    mremap_log(
                        log_fn,
                        if error == -EPERM {
                            MREMAP_LOG_FIXED_MIN_ADDR
                        } else {
                            MREMAP_LOG_FIXED_OVERLAP
                        },
                        oldaddr,
                        oldsize0,
                        newsize0,
                        flags,
                        newaddr,
                        oldstart,
                        oldend,
                        newstart,
                        newend,
                        if error == -EPERM { user_start } else { 0 },
                        0,
                        0,
                        lckstart,
                        lckend,
                        error,
                    );
                }
            } else if oldsize < newsize {
                if oldend == memlock_range_ulong(range, range_end_offset) {
                    newstart = oldstart;
                    newend = newstart.wrapping_add(newsize as CULong);
                    error = if let Some(extend) = extend_fn {
                        extend(vm, range, newend)
                    } else {
                        -EINVAL
                    };
                    if let Some(flush) = flush_nfo_fn {
                        flush();
                    }
                    if error == 0 {
                        if (memlock_range_ulong(range, range_flag_offset) & VR_LOCKED) != 0 {
                            lckstart = oldend;
                            lckend = newend;
                        }
                    }
                }
                if error != 0 {
                    error = mremap_maymove_result(flags);
                    if error != 0 {
                        mremap_log(
                            log_fn,
                            MREMAP_LOG_CANNOT_RELOCATE,
                            oldaddr,
                            oldsize0,
                            newsize0,
                            flags,
                            newaddr,
                            oldstart,
                            oldend,
                            newstart,
                            newend,
                            0,
                            0,
                            0,
                            lckstart,
                            lckend,
                            error,
                        );
                    } else {
                        need_relocate = 1;
                        error = if let Some(search) = search_fn {
                            search(
                                newsize,
                                memlock_range_ulong(range, range_pgshift_offset),
                                &mut newstart,
                            )
                        } else {
                            -EINVAL
                        };
                        if error != 0 {
                            mremap_log(
                                log_fn,
                                MREMAP_LOG_SEARCH_FAILED,
                                oldaddr,
                                oldsize0,
                                newsize0,
                                flags,
                                newaddr,
                                oldstart,
                                oldend,
                                newstart,
                                newend,
                                0,
                                0,
                                0,
                                lckstart,
                                lckend,
                                error,
                            );
                        } else {
                            newend = newstart.wrapping_add(newsize as CULong);
                        }
                    }
                }
            } else {
                newstart = oldstart;
                newend = newstart.wrapping_add(newsize as CULong);
            }

            if error == 0 && need_relocate != 0 {
                error = mremap_relocate(
                    vm,
                    pte_lock,
                    page_table,
                    oldaddr,
                    oldsize0,
                    oldsize,
                    newsize0,
                    newsize,
                    flags,
                    newaddr,
                    oldstart,
                    oldend,
                    newstart,
                    newend,
                    &mut range,
                    range_start_offset,
                    range_end_offset,
                    range_flag_offset,
                    range_memobj_offset,
                    range_objoff_offset,
                    &mut lckstart,
                    &mut lckend,
                    munmap_fn,
                    memobj_ref_fn,
                    memobj_unref_fn,
                    add_range_fn,
                    flush_nfo_fn,
                    pte_lock_fn,
                    pte_unlock_fn,
                    split_fn,
                    move_pte_fn,
                    log_fn,
                );
            } else if error == 0 && newsize < oldsize {
                error = if let Some(munmap) = munmap_fn {
                    munmap(newend as *mut c_void, (oldend - newend) as SizeT, 1)
                } else {
                    -EINVAL
                };
                if error != 0 {
                    mremap_log(
                        log_fn,
                        MREMAP_LOG_SHRINK_MUNMAP_FAILED,
                        oldaddr,
                        oldsize0,
                        newsize0,
                        flags,
                        newaddr,
                        oldstart,
                        oldend,
                        newstart,
                        newend,
                        0,
                        0,
                        0,
                        lckstart,
                        lckend,
                        error,
                    );
                }
            }
        }
    }

    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }

    if error == 0 && lckstart < lckend {
        let populate_error = if let Some(populate) = populate_fn {
            populate(vm, lckstart, (lckend - lckstart) as SizeT)
        } else {
            -EINVAL
        };
        if populate_error != 0 {
            mremap_log(
                log_fn,
                MREMAP_LOG_POPULATE_FAILED,
                oldaddr,
                oldsize0,
                newsize0,
                flags,
                newaddr,
                oldstart,
                oldend,
                newstart,
                newend,
                0,
                0,
                0,
                lckstart,
                lckend,
                populate_error,
            );
        }
    }

    let ret = if error != 0 {
        error as CLong
    } else {
        newstart as CLong
    };
    mremap_log_range(
        log_fn,
        MREMAP_LOG_EXIT,
        oldaddr,
        oldsize0,
        newsize0,
        flags,
        newaddr,
        oldstart,
        oldend,
        newstart,
        newend,
        range,
        range_start_offset,
        range_end_offset,
        range_flag_offset,
        lckstart,
        lckend,
        error,
    );
    ret
}

#[no_mangle]
pub unsafe extern "C" fn msync_prepare_range(
    start0: CULong,
    len0: SizeT,
    flags: CInt,
    lenp: *mut SizeT,
    endp: *mut CULong,
) -> CInt {
    let len = len0.wrapping_add((PAGE_SIZE - 1) as SizeT) & PAGE_MASK as SizeT;
    let end = start0.wrapping_add(len as CULong);

    write(lenp, len);
    write(endp, end);

    if (start0 & (PAGE_SIZE - 1)) != 0
        || (flags & !(MS_ASYNC | MS_INVALIDATE | MS_SYNC)) != 0
        || ((flags & MS_ASYNC) != 0 && (flags & MS_SYNC) != 0)
    {
        return -EINVAL;
    }

    if end < start0 {
        return -ENOMEM;
    }

    0
}

#[no_mangle]
pub extern "C" fn msync_locked_range_result(flags: CInt, range_flags: CULong) -> CInt {
    if (flags & MS_INVALIDATE) != 0 && (range_flags & VR_LOCKED) != 0 {
        -EBUSY
    } else {
        0
    }
}

#[inline(always)]
unsafe fn msync_range_ulong(range: *mut c_void, offset: SizeT) -> CULong {
    *field_ptr::<CULong>(range.cast::<u8>(), offset)
}

#[inline(always)]
unsafe fn msync_range_ptr(range: *mut c_void, offset: SizeT) -> *mut c_void {
    *field_ptr::<*mut c_void>(range.cast::<u8>(), offset)
}

#[no_mangle]
pub unsafe extern "C" fn msync_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    start0: CULong,
    len0: SizeT,
    flags: CInt,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_flag_offset: SizeT,
    range_memobj_offset: SizeT,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    next_fn: Option<MsyncNextRangeFn>,
    has_pager_fn: Option<MsyncHasPagerFn>,
    sync_fn: Option<MsyncRangeOpFn>,
    invalidate_fn: Option<MsyncRangeOpFn>,
    log_fn: Option<MsyncLogFn>,
) -> CInt {
    if let Some(log) = log_fn {
        log(MSYNC_LOG_ENTER, start0, len0, flags, 0);
    }
    if let Some(lock) = lock_fn {
        lock(range_lock);
    }

    let mut len: SizeT = 0;
    let mut end: CULong = 0;
    let mut error = msync_prepare_range(start0, len0, flags, &mut len, &mut end);
    if error != 0 {
        if let Some(log) = log_fn {
            log(MSYNC_LOG_INVALID_ARGS, start0, len0, flags, error);
        }
        if let Some(unlock) = unlock_fn {
            unlock(range_lock);
        }
        if let Some(log) = log_fn {
            log(MSYNC_LOG_EXIT, start0, len0, flags, error);
        }
        return error;
    }

    let mut range = core::ptr::null_mut::<c_void>();
    let mut addr = start0;
    while addr < end {
        range = if range.is_null() {
            if let Some(lookup) = lookup_fn {
                lookup(vm, addr, addr.wrapping_add(PAGE_SIZE))
            } else {
                core::ptr::null_mut()
            }
        } else if let Some(next) = next_fn {
            next(vm, range)
        } else {
            core::ptr::null_mut()
        };

        if range.is_null() || addr < msync_range_ulong(range, range_start_offset) {
            error = -ENOMEM;
            if let Some(log) = log_fn {
                log(MSYNC_LOG_INVALID_VMR, start0, len0, flags, error);
            }
            break;
        }

        error = msync_locked_range_result(flags, msync_range_ulong(range, range_flag_offset));
        if error != 0 {
            if let Some(log) = log_fn {
                log(MSYNC_LOG_LOCKED_VMR, start0, len0, flags, error);
            }
            break;
        }

        addr = msync_range_ulong(range, range_end_offset);
    }

    if error == 0 {
        range = core::ptr::null_mut();
        addr = start0;
        while addr < end {
            range = if range.is_null() {
                if let Some(lookup) = lookup_fn {
                    lookup(vm, addr, addr.wrapping_add(PAGE_SIZE))
                } else {
                    core::ptr::null_mut()
                }
            } else if let Some(next) = next_fn {
                next(vm, range)
            } else {
                core::ptr::null_mut()
            };
            if range.is_null() {
                error = -ENOMEM;
                if let Some(log) = log_fn {
                    log(MSYNC_LOG_INVALID_VMR, start0, len0, flags, error);
                }
                break;
            }

            let range_end = msync_range_ulong(range, range_end_offset);
            let range_flag = msync_range_ulong(range, range_flag_offset);
            let memobj = msync_range_ptr(range, range_memobj_offset);
            if (range_flag & VR_PRIVATE) != 0
                || memobj.is_null()
                || has_pager_fn.map_or(true, |has_pager| has_pager(memobj) == 0)
            {
                if let Some(log) = log_fn {
                    log(MSYNC_LOG_UNSYNCABLE_VMR, start0, len0, flags, 0);
                }
                addr = range_end;
                continue;
            }

            let sync_start = addr;
            let sync_end = if range_end < end { range_end } else { end };
            if (flags & (MS_ASYNC | MS_SYNC)) != 0 {
                error = if let Some(sync) = sync_fn {
                    sync(vm, range, sync_start, sync_end)
                } else {
                    -EINVAL
                };
                if error != 0 {
                    if let Some(log) = log_fn {
                        log(MSYNC_LOG_SYNC_FAILED, start0, len0, flags, error);
                    }
                    break;
                }
            }

            if (flags & MS_INVALIDATE) != 0 {
                error = if let Some(invalidate) = invalidate_fn {
                    invalidate(vm, range, sync_start, sync_end)
                } else {
                    -EINVAL
                };
                if error != 0 {
                    if let Some(log) = log_fn {
                        log(MSYNC_LOG_INVALIDATE_FAILED, start0, len0, flags, error);
                    }
                    break;
                }
            }

            addr = range_end;
        }
    }

    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }
    if let Some(log) = log_fn {
        log(MSYNC_LOG_EXIT, start0, len0, flags, error);
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn mbind_prepare_range(
    addr: CULong,
    len0: CULong,
    lenp: *mut CULong,
) -> CInt {
    let len = len0.wrapping_add(PAGE_SIZE - 1) & PAGE_MASK;
    write(lenp, len);

    if (addr & (PAGE_SIZE - 1)) != 0
        || addr.wrapping_add(len) < addr
        || addr == addr.wrapping_add(len)
    {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mempolicy_nodemask_bits_result(
    maxnode: CULong,
    nodemask_bitsp: *mut CULong,
) -> CInt {
    let mut nodemask_bits = if maxnode != 0 {
        maxnode.wrapping_add(7) & !7
    } else {
        0
    };

    if maxnode > (PAGE_SIZE << 3) {
        write(nodemask_bitsp, nodemask_bits);
        return -EINVAL;
    }

    if nodemask_bits > PROCESS_NUMA_MASK_BITS {
        nodemask_bits = PROCESS_NUMA_MASK_BITS;
    }

    write(nodemask_bitsp, nodemask_bits);
    0
}

#[no_mangle]
pub extern "C" fn mempolicy_nodemask_bits_is_clamped(maxnode: CULong) -> CInt {
    if maxnode != 0 && ((maxnode.wrapping_add(7) & !7) > PROCESS_NUMA_MASK_BITS) {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn mbind_mode_flags_result(
    mode: CInt,
    flags: CInt,
    mode_flagsp: *mut CInt,
    normalized_modep: *mut CInt,
) -> CInt {
    if (mode & MPOL_F_STATIC_NODES) != 0 && (mode & MPOL_F_RELATIVE_NODES) != 0 {
        return -EINVAL;
    }

    if (flags & MPOL_MF_STRICT) != 0 && (flags & MPOL_MF_MOVE) != 0 {
        return -EINVAL;
    }

    let mode_flags = mode & MPOL_MODE_FLAGS;
    let normalized_mode = mode & !MPOL_MODE_FLAGS;
    write(mode_flagsp, mode_flags);
    write(normalized_modep, normalized_mode);

    if (mode_flags & MPOL_F_RELATIVE_NODES) != 0 {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn mempolicy_mode_is_supported(mode: CInt) -> CInt {
    if mode == MPOL_DEFAULT
        || mode == MPOL_BIND
        || mode == MPOL_INTERLEAVE
        || mode == MPOL_PREFERRED
    {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_mempolicy_normalize_mode(
    mode: CInt,
    normalized_modep: *mut CInt,
) -> CInt {
    if (mode & MPOL_F_STATIC_NODES) != 0 && (mode & MPOL_F_RELATIVE_NODES) != 0 {
        return -EINVAL;
    }

    write(normalized_modep, mode & !MPOL_MODE_FLAGS);
    0
}

const SET_MEMPOLICY_LOG_NODEMASK_BITS_TOO_BIG: CInt = 1;
const SET_MEMPOLICY_LOG_CLAMPED: CInt = 2;
const SET_MEMPOLICY_LOG_DEFAULT_MASK_NOT_EMPTY: CInt = 3;
const SET_MEMPOLICY_LOG_NODEMASK_NOT_SPECIFIED: CInt = 4;
const SET_MEMPOLICY_LOG_NODE_TOO_LARGE: CInt = 5;
const SET_MEMPOLICY_LOG_INVALID_NODEMASK: CInt = 6;
const SET_MEMPOLICY_LOG_SET: CInt = 7;

unsafe fn policy_mask_zero(mask: *mut CULong) {
    let mut word = 0usize;
    while word < PROCESS_NUMA_MASK_WORDS {
        write_volatile(mask.add(word), 0);
        word += 1;
    }
}

unsafe fn policy_mask_set(mask: *mut CULong, bit: CInt) {
    if bit < 0 || bit as CULong >= PROCESS_NUMA_MASK_BITS {
        return;
    }
    let shift = (bit as usize) % (size_of::<CULong>() * 8);
    let word = (bit as usize) / (size_of::<CULong>() * 8);
    let value = read_volatile(mask.add(word)) | ((1 as CULong) << shift);
    write_volatile(mask.add(word), value);
}

unsafe fn policy_mask_clear(mask: *mut CULong, bit: CInt) {
    if bit < 0 || bit as CULong >= PROCESS_NUMA_MASK_BITS {
        return;
    }
    let shift = (bit as usize) % (size_of::<CULong>() * 8);
    let word = (bit as usize) / (size_of::<CULong>() * 8);
    let value = read_volatile(mask.add(word)) & !((1 as CULong) << shift);
    write_volatile(mask.add(word), value);
}

unsafe fn policy_mask_test(mask: *const CULong, bit: CInt) -> bool {
    if bit < 0 || bit as CULong >= PROCESS_NUMA_MASK_BITS {
        return false;
    }
    let shift = (bit as usize) % (size_of::<CULong>() * 8);
    let word = (bit as usize) / (size_of::<CULong>() * 8);
    (read_volatile(mask.add(word)) & ((1 as CULong) << shift)) != 0
}

unsafe fn policy_mask_empty(mask: *const CULong, bits: CULong) -> bool {
    let limit = if bits > PROCESS_NUMA_MASK_BITS {
        PROCESS_NUMA_MASK_BITS
    } else {
        bits
    };
    let mut bit = 0 as CULong;
    while bit < limit {
        if policy_mask_test(mask, bit as CInt) {
            return false;
        }
        bit += 1;
    }
    true
}

unsafe fn policy_mask_set_all_nodes(mask: *mut CULong, nr_numa_nodes: CInt) {
    policy_mask_zero(mask);
    let mut bit = 0;
    while bit < nr_numa_nodes && (bit as CULong) < PROCESS_NUMA_MASK_BITS {
        policy_mask_set(mask, bit);
        bit += 1;
    }
}

unsafe fn set_mempolicy_log(
    log_fn: Option<SyscallSetMempolicyLogFn>,
    event: CInt,
    value: CInt,
    pid: CInt,
) {
    if let Some(log) = log_fn {
        log(event, value, pid);
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_mempolicy_body_result(
    mode: CInt,
    nodemask_addr: CULong,
    maxnode: CULong,
    vm: *mut ProcessVm,
    nr_numa_nodes: CInt,
    pid: CInt,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    log_fn: Option<SyscallSetMempolicyLogFn>,
) -> CLong {
    if vm.is_null() {
        return -(EFAULT as CLong);
    }

    let mut nodemask_bits: CULong = 0;
    let mut numa_mask = [0 as CULong; PROCESS_NUMA_MASK_WORDS];
    policy_mask_zero(numa_mask.as_mut_ptr());

    let error = mempolicy_nodemask_bits_result(maxnode, &mut nodemask_bits);
    if error != 0 {
        set_mempolicy_log(log_fn, SET_MEMPOLICY_LOG_NODEMASK_BITS_TOO_BIG, 0, pid);
        return error as CLong;
    }
    if mempolicy_nodemask_bits_is_clamped(maxnode) != 0 {
        set_mempolicy_log(log_fn, SET_MEMPOLICY_LOG_CLAMPED, 0, pid);
    }

    let mut normalized_mode = mode;
    let error = set_mempolicy_normalize_mode(mode, &mut normalized_mode);
    if error != 0 {
        return error as CLong;
    }
    if mempolicy_mode_is_supported(normalized_mode) == 0 {
        return -(EINVAL as CLong);
    }

    match normalized_mode {
        MPOL_DEFAULT => {
            if nodemask_addr != 0 && nodemask_bits != 0 {
                let Some(copy_from) = copy_from_fn else {
                    return -(EINVAL as CLong);
                };
                if copy_from(
                    numa_mask.as_mut_ptr().cast::<u8>(),
                    nodemask_addr,
                    (nodemask_bits >> 3) as SizeT,
                ) != 0
                {
                    return -(EFAULT as CLong);
                }
                if !policy_mask_empty(numa_mask.as_ptr(), nodemask_bits) {
                    set_mempolicy_log(log_fn, SET_MEMPOLICY_LOG_DEFAULT_MASK_NOT_EMPTY, 0, pid);
                    return -(EINVAL as CLong);
                }
            }

            policy_mask_set_all_nodes((*vm).numa_mask.as_mut_ptr(), nr_numa_nodes);
            (*vm).numa_mem_policy = normalized_mode;
            set_mempolicy_log(log_fn, SET_MEMPOLICY_LOG_SET, normalized_mode, pid);
            0
        }
        MPOL_BIND | MPOL_INTERLEAVE | MPOL_PREFERRED => {
            if normalized_mode == MPOL_PREFERRED && nodemask_addr == 0 {
                policy_mask_set_all_nodes((*vm).numa_mask.as_mut_ptr(), nr_numa_nodes);
                (*vm).numa_mem_policy = normalized_mode;
                set_mempolicy_log(log_fn, SET_MEMPOLICY_LOG_SET, normalized_mode, pid);
                return 0;
            }

            if nodemask_addr == 0 {
                set_mempolicy_log(log_fn, SET_MEMPOLICY_LOG_NODEMASK_NOT_SPECIFIED, 0, pid);
                return -(EINVAL as CLong);
            }

            let Some(copy_from) = copy_from_fn else {
                return -(EINVAL as CLong);
            };
            if copy_from(
                numa_mask.as_mut_ptr().cast::<u8>(),
                nodemask_addr,
                (nodemask_bits >> 3) as SizeT,
            ) != 0
            {
                return -(EFAULT as CLong);
            }

            let scan_bits = if maxnode < PROCESS_NUMA_MASK_BITS {
                maxnode
            } else {
                PROCESS_NUMA_MASK_BITS
            };
            let mut valid_mask = false;
            let mut bit = 0 as CULong;
            while bit < scan_bits {
                if policy_mask_test(numa_mask.as_ptr(), bit as CInt) {
                    if bit as CInt >= nr_numa_nodes {
                        set_mempolicy_log(
                            log_fn,
                            SET_MEMPOLICY_LOG_NODE_TOO_LARGE,
                            bit as CInt,
                            pid,
                        );
                        return -(EINVAL as CLong);
                    }
                    if policy_mask_test((*vm).numa_mask.as_ptr(), bit as CInt) {
                        valid_mask = true;
                    }
                }
                bit += 1;
            }

            if !valid_mask {
                set_mempolicy_log(log_fn, SET_MEMPOLICY_LOG_INVALID_NODEMASK, 0, pid);
                return -(EINVAL as CLong);
            }

            bit = 0;
            while bit < scan_bits {
                if policy_mask_test((*vm).numa_mask.as_ptr(), bit as CInt)
                    && !policy_mask_test(numa_mask.as_ptr(), bit as CInt)
                {
                    policy_mask_clear((*vm).numa_mask.as_mut_ptr(), bit as CInt);
                }
                bit += 1;
            }

            (*vm).numa_mem_policy = normalized_mode;
            if normalized_mode == MPOL_INTERLEAVE {
                (*vm).il_prev = (PROCESS_NUMA_MASK_BITS - 1) as CInt;
            }
            set_mempolicy_log(log_fn, SET_MEMPOLICY_LOG_SET, normalized_mode, pid);
            0
        }
        _ => -(EINVAL as CLong),
    }
}

const MBIND_LOG_NODEMASK_BITS_TOO_BIG: CInt = 2;
const MBIND_LOG_CLAMPED: CInt = 3;
const MBIND_LOG_INVALID_MODE_FLAGS: CInt = 4;
const MBIND_LOG_COPY_FROM_NUMA_MASK: CInt = 5;
const MBIND_LOG_DEFAULT_MASK_NOT_EMPTY: CInt = 6;
const MBIND_LOG_NODEMASK_NOT_SPECIFIED: CInt = 7;
const MBIND_LOG_NODE_TOO_LARGE: CInt = 8;
const MBIND_LOG_INVALID_RANGE: CInt = 9;
const MBIND_LOG_CLEAR_POLICY_RANGE: CInt = 10;
const MBIND_LOG_ALLOC_POLICY: CInt = 11;
const MBIND_LOG_INSERT_POLICY: CInt = 12;

unsafe fn mbind_log(
    log_fn: Option<SyscallMbindLogFn>,
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CInt,
) {
    if let Some(log) = log_fn {
        log(event, arg0, arg1, arg2);
    }
}

unsafe fn policy_mask_copy_words(dst: *mut CULong, src: *const CULong) {
    let mut word = 0usize;
    while word < PROCESS_NUMA_MASK_WORDS {
        let value = read_volatile(src.add(word));
        write_volatile(dst.add(word), value);
        word += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mbind_body_result(
    addr: CULong,
    len0: CULong,
    mode: CInt,
    nodemask_addr: CULong,
    maxnode: CULong,
    flags: CInt,
    vm: *mut ProcessVm,
    straight_va: CInt,
    fugaku_hacks: CInt,
    nr_numa_nodes: CInt,
    policy_size: SizeT,
    alloc_flags: CULong,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    write_lock_fn: Option<SyscallRwlockFn>,
    write_unlock_fn: Option<SyscallRwlockFn>,
    lookup_range_fn: Option<SyscallLookupRangeFn>,
    policy_search_fn: Option<SyscallPolicySearchFn>,
    clear_range_fn: Option<SyscallPolicyClearRangeFn>,
    alloc_fn: Option<SyscallPolicyAllocFn>,
    rb_clear_fn: Option<SyscallPolicyRbClearFn>,
    insert_fn: Option<SyscallPolicyInsertFn>,
    log_fn: Option<SyscallMbindLogFn>,
) -> CLong {
    if straight_va != 0 {
        return 0;
    }
    if vm.is_null() {
        return -(EFAULT as CLong);
    }

    let mut len = len0;
    let error = mbind_prepare_range(addr, len0, &mut len);
    if error != 0 {
        return error as CLong;
    }

    if fugaku_hacks != 0 {
        return 0;
    }

    let mut numa_mask = [0 as CULong; PROCESS_NUMA_MASK_WORDS];
    policy_mask_zero(numa_mask.as_mut_ptr());

    let mut nodemask_bits: CULong = 0;
    let error = mempolicy_nodemask_bits_result(maxnode, &mut nodemask_bits);
    if error != 0 {
        mbind_log(
            log_fn,
            MBIND_LOG_NODEMASK_BITS_TOO_BIG,
            addr,
            maxnode,
            error,
        );
        return error as CLong;
    }
    if mempolicy_nodemask_bits_is_clamped(maxnode) != 0 {
        mbind_log(log_fn, MBIND_LOG_CLAMPED, addr, maxnode, 0);
    }

    let mut mode_flags = 0;
    let mut normalized_mode = mode;
    let error = mbind_mode_flags_result(mode, flags, &mut mode_flags, &mut normalized_mode);
    if error != 0 {
        mbind_log(
            log_fn,
            MBIND_LOG_INVALID_MODE_FLAGS,
            addr,
            flags as CULong,
            error,
        );
        return error as CLong;
    }
    if mempolicy_mode_is_supported(normalized_mode) == 0 {
        return -(EINVAL as CLong);
    }

    match normalized_mode {
        MPOL_DEFAULT => {
            if nodemask_addr != 0 && nodemask_bits != 0 {
                let Some(copy_from) = copy_from_fn else {
                    return -(EINVAL as CLong);
                };
                if copy_from(
                    numa_mask.as_mut_ptr().cast::<u8>(),
                    nodemask_addr,
                    (nodemask_bits >> 3) as SizeT,
                ) != 0
                {
                    mbind_log(
                        log_fn,
                        MBIND_LOG_COPY_FROM_NUMA_MASK,
                        addr,
                        nodemask_addr,
                        0,
                    );
                    return -(EFAULT as CLong);
                }
                if !policy_mask_empty(numa_mask.as_ptr(), nodemask_bits) {
                    mbind_log(
                        log_fn,
                        MBIND_LOG_DEFAULT_MASK_NOT_EMPTY,
                        addr,
                        nodemask_addr,
                        0,
                    );
                    return -(EINVAL as CLong);
                }
            }
        }
        MPOL_BIND | MPOL_INTERLEAVE | MPOL_PREFERRED => {
            if normalized_mode == MPOL_PREFERRED && nodemask_addr == 0 {
            } else {
                if (flags & MPOL_MF_STRICT) != 0 {
                    return -(EIO as CLong);
                }

                let Some(copy_from) = copy_from_fn else {
                    return -(EINVAL as CLong);
                };
                if copy_from(
                    numa_mask.as_mut_ptr().cast::<u8>(),
                    nodemask_addr,
                    (nodemask_bits >> 3) as SizeT,
                ) != 0
                {
                    return -(EFAULT as CLong);
                }

                if nodemask_addr == 0 || policy_mask_empty(numa_mask.as_ptr(), nodemask_bits) {
                    mbind_log(
                        log_fn,
                        MBIND_LOG_NODEMASK_NOT_SPECIFIED,
                        addr,
                        nodemask_addr,
                        0,
                    );
                    return -(EINVAL as CLong);
                }

                let scan_bits = if maxnode < PROCESS_NUMA_MASK_BITS {
                    maxnode
                } else {
                    PROCESS_NUMA_MASK_BITS
                };
                let mut bit = 0 as CULong;
                while bit < scan_bits {
                    if policy_mask_test(numa_mask.as_ptr(), bit as CInt)
                        && bit as CInt >= nr_numa_nodes
                    {
                        mbind_log(log_fn, MBIND_LOG_NODE_TOO_LARGE, addr, bit, 0);
                        return -(EINVAL as CLong);
                    }
                    bit += 1;
                }
            }
        }
        _ => return -(EINVAL as CLong),
    }

    let (
        Some(write_lock),
        Some(write_unlock),
        Some(lookup_range),
        Some(policy_search),
        Some(clear_range),
        Some(alloc),
        Some(rb_clear),
        Some(insert),
    ) = (
        write_lock_fn,
        write_unlock_fn,
        lookup_range_fn,
        policy_search_fn,
        clear_range_fn,
        alloc_fn,
        rb_clear_fn,
        insert_fn,
    )
    else {
        return -(EINVAL as CLong);
    };

    let lock = core::ptr::addr_of_mut!((*vm).memory_range_lock) as *mut c_void;
    write_lock(lock);

    let end = addr.wrapping_add(len);
    let range = lookup_range(vm, addr, end);
    if range.is_null() {
        mbind_log(log_fn, MBIND_LOG_INVALID_RANGE, addr, end, 0);
        write_unlock(lock);
        return -(EFAULT as CLong);
    }

    let mut range_policy = policy_search(vm, addr);
    if range_policy.is_null() || (*range_policy).start != addr || (*range_policy).end != end {
        let error = clear_range(vm, addr, end);
        if error != 0 {
            mbind_log(log_fn, MBIND_LOG_CLEAR_POLICY_RANGE, addr, end, error);
            write_unlock(lock);
            return error as CLong;
        }

        range_policy = alloc(policy_size, alloc_flags).cast::<VmRangeNumaPolicy>();
        if range_policy.is_null() {
            mbind_log(log_fn, MBIND_LOG_ALLOC_POLICY, addr, end, 0);
            write_unlock(lock);
            return -(ENOMEM as CLong);
        }

        rb_clear(range_policy);
        (*range_policy).start = addr;
        (*range_policy).end = end;

        let error = insert(vm, range_policy);
        if error != 0 {
            mbind_log(log_fn, MBIND_LOG_INSERT_POLICY, addr, end, error);
            write_unlock(lock);
            return error as CLong;
        }
    }

    if normalized_mode == MPOL_DEFAULT {
        policy_mask_set_all_nodes((*range_policy).numa_mask.as_mut_ptr(), nr_numa_nodes);
    } else {
        policy_mask_copy_words((*range_policy).numa_mask.as_mut_ptr(), numa_mask.as_ptr());
    }
    (*range_policy).numa_mem_policy = normalized_mode;
    if normalized_mode == MPOL_INTERLEAVE {
        (*range_policy).il_prev = (PROCESS_NUMA_MASK_BITS - 1) as CInt;
    }

    write_unlock(lock);
    0
}

#[no_mangle]
pub unsafe extern "C" fn get_mempolicy_validate(
    addr: CULong,
    flags: CInt,
    process_policy: CInt,
    maxnode: CULong,
    nr_numa_nodes: CInt,
    nodemask_bitsp: *mut CULong,
) -> CInt {
    write(nodemask_bitsp, 0);

    if ((flags & MPOL_F_ADDR) == 0 && addr != 0)
        || (flags & !(MPOL_F_ADDR | MPOL_F_NODE | MPOL_F_MEMS_ALLOWED)) != 0
        || ((flags & MPOL_F_NODE) != 0
            && (flags & MPOL_F_ADDR) == 0
            && process_policy == MPOL_INTERLEAVE)
    {
        return -EINVAL;
    }

    if (flags & MPOL_F_ADDR) != 0 && addr == 0 {
        return -EFAULT;
    }

    if maxnode != 0 {
        if maxnode < nr_numa_nodes as CULong {
            return -EINVAL;
        }

        let mut nodemask_bits = maxnode.wrapping_add(7) & !7;
        if nodemask_bits > PROCESS_NUMA_MASK_BITS {
            nodemask_bits = PROCESS_NUMA_MASK_BITS;
        }
        write(nodemask_bitsp, nodemask_bits);
    }

    0
}

const GET_MEMPOLICY_LOG_CLAMPED: CInt = 1;
const GET_MEMPOLICY_LOG_INVALID_RANGE: CInt = 2;

#[no_mangle]
pub unsafe extern "C" fn get_mempolicy_body_result(
    mode_addr: CULong,
    nodemask_addr: CULong,
    maxnode: CULong,
    addr: CULong,
    flags: CInt,
    vm: *mut ProcessVm,
    nr_numa_nodes: CInt,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    lookup_node_fn: Option<SyscallLookupNodeFn>,
    read_lock_fn: Option<SyscallRwlockFn>,
    read_unlock_fn: Option<SyscallRwlockFn>,
    lookup_range_fn: Option<SyscallLookupRangeFn>,
    policy_search_fn: Option<SyscallPolicySearchFn>,
    log_fn: Option<SyscallGetMempolicyLogFn>,
) -> CLong {
    if vm.is_null() {
        return -(EFAULT as CLong);
    }

    let mut nodemask_bits: CULong = 0;
    let process_policy = (*vm).numa_mem_policy;
    let error = get_mempolicy_validate(
        addr,
        flags,
        process_policy,
        maxnode,
        nr_numa_nodes,
        &mut nodemask_bits,
    );
    if error != 0 {
        return error as CLong;
    }

    if mempolicy_nodemask_bits_is_clamped(maxnode) != 0 {
        if let Some(log) = log_fn {
            log(GET_MEMPOLICY_LOG_CLAMPED, addr, nodemask_bits as CInt);
        }
    }

    let Some(copy_to) = copy_to_fn else {
        return -(EINVAL as CLong);
    };

    if (flags & MPOL_F_NODE) != 0 && (flags & MPOL_F_ADDR) != 0 {
        let Some(lookup_node) = lookup_node_fn else {
            return -(EINVAL as CLong);
        };
        let nid = lookup_node(vm, addr as *mut c_void);
        if copy_to(
            mode_addr,
            (&nid as *const CInt).cast::<u8>(),
            size_of::<CInt>(),
        ) != 0
        {
            return -(EFAULT as CLong);
        }
        return 0;
    }

    if flags == MPOL_F_MEMS_ALLOWED {
        if nodemask_addr != 0
            && copy_to(
                nodemask_addr,
                (*vm).numa_mask.as_ptr().cast::<u8>(),
                (nodemask_bits >> 3) as SizeT,
            ) != 0
        {
            return -(EFAULT as CLong);
        }
        return 0;
    }

    let mut range_policy: *mut VmRangeNumaPolicy = core::ptr::null_mut();
    if (flags & MPOL_F_ADDR) != 0 {
        let (Some(read_lock), Some(read_unlock), Some(lookup_range), Some(policy_search)) = (
            read_lock_fn,
            read_unlock_fn,
            lookup_range_fn,
            policy_search_fn,
        ) else {
            return -(EINVAL as CLong);
        };
        let lock = core::ptr::addr_of_mut!((*vm).memory_range_lock) as *mut c_void;
        read_lock(lock);
        let range = lookup_range(vm, addr, addr.wrapping_add(1));
        if range.is_null() {
            if let Some(log) = log_fn {
                log(GET_MEMPOLICY_LOG_INVALID_RANGE, addr, 0);
            }
            read_unlock(lock);
            return -(EFAULT as CLong);
        }

        range_policy = policy_search(vm, addr);
        read_unlock(lock);
    }

    let policy = if !range_policy.is_null() {
        (*range_policy).numa_mem_policy
    } else {
        (*vm).numa_mem_policy
    };

    if mode_addr != 0
        && copy_to(
            mode_addr,
            (&policy as *const CInt).cast::<u8>(),
            size_of::<CInt>(),
        ) != 0
    {
        return -(EFAULT as CLong);
    }

    if nodemask_addr != 0 && policy != MPOL_DEFAULT {
        let mask = if !range_policy.is_null() {
            (*range_policy).numa_mask.as_ptr()
        } else {
            (*vm).numa_mask.as_ptr()
        };
        if copy_to(
            nodemask_addr,
            mask.cast::<u8>(),
            (nodemask_bits >> 3) as SizeT,
        ) != 0
        {
            return -(EFAULT as CLong);
        }
    }

    0
}

#[no_mangle]
pub extern "C" fn move_pages_policy_result(pid: CInt, flags: CInt) -> CInt {
    if pid != 0 {
        return -EINVAL;
    }

    if (flags & !(MPOL_MF_MOVE | MPOL_MF_MOVE_ALL)) != 0 || (flags & MPOL_MF_MOVE_ALL) != 0 {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn move_pages_smp_req_prepare_result(
    req: *mut MovePagesSmpReq,
    count: CULong,
    user_virt_addr: *mut *const c_void,
    user_status: *mut CInt,
    user_nodes: *const CInt,
    virt_addr: *mut *mut c_void,
    status: *mut CInt,
    ptep: *mut *mut c_void,
    nodes: *mut CInt,
    nr_pages: *mut CInt,
    dst_phys: *mut CULong,
    proc: *mut c_void,
) -> CInt {
    if req.is_null() {
        return -EINVAL;
    }

    (*req).count = count;
    (*req).user_virt_addr = user_virt_addr;
    (*req).user_status = user_status;
    (*req).user_nodes = user_nodes;
    (*req).virt_addr = virt_addr;
    (*req).status = status;
    (*req).ptep = ptep;
    (*req).nodes = nodes;
    (*req).nodes_ready = 0;
    (*req).nr_pages = nr_pages;
    (*req).dst_phys = dst_phys;
    (*req).proc = proc;
    (*req).phase_done.counter = 0;
    (*req).phase_ret = 0;
    0
}

unsafe fn move_pages_log_delta(
    log_fn: Option<MovePagesLogFn>,
    rdtsc_fn: Option<SyscallRdtscFn>,
    event: CInt,
    start: CULong,
) -> CULong {
    let now = rdtsc_fn.map_or(start, |rdtsc| rdtsc());
    if let Some(log) = log_fn {
        log(event, now.wrapping_sub(start), 0);
    }
    now
}

unsafe fn move_pages_free_arrays(
    free_fn: Option<SyscallMckfdFreeFn>,
    virt_addr: *mut c_void,
    nr_pages: *mut c_void,
    nodes: *mut c_void,
    status: *mut c_void,
    ptep: *mut c_void,
    dst_phys: *mut c_void,
) {
    if let Some(free) = free_fn {
        free(virt_addr);
        free(nr_pages);
        free(nodes);
        free(status);
        free(ptep);
        free(dst_phys);
    }
}

#[no_mangle]
pub unsafe extern "C" fn move_pages_body_result(
    pid: CInt,
    count: CULong,
    user_virt_addr_addr: CULong,
    user_nodes_addr: CULong,
    user_status_addr: CULong,
    flags: CInt,
    vm: *mut ProcessVm,
    page_table_lock: *mut c_void,
    cpu_set: *mut c_void,
    proc: *mut c_void,
    alloc_flags: CULong,
    ptr_size: SizeT,
    int_size: SizeT,
    pte_size: SizeT,
    ulong_size: SizeT,
    verify_fn: Option<MovePagesVerifyFn>,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    alloc_fn: Option<SyscallPolicyAllocFn>,
    free_fn: Option<SyscallMckfdFreeFn>,
    get_nr_nodes_fn: Option<MovePagesGetNrNodesFn>,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    smp_call_fn: Option<MovePagesSmpCallFn>,
    handler_fn: Option<MovePagesSmpHandlerFn>,
    rdtsc_fn: Option<SyscallRdtscFn>,
    log_fn: Option<MovePagesLogFn>,
) -> CLong {
    let policy_error = move_pages_policy_result(pid, flags);
    if policy_error != 0 {
        if let Some(log) = log_fn {
            if pid != 0 {
                log(MOVE_PAGES_LOG_UNSUPPORTED_PID, 0, policy_error);
            } else if (flags & MPOL_MF_MOVE_ALL) != 0 {
                log(MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL, 0, policy_error);
            }
        }
        return policy_error as CLong;
    }

    let (
        Some(alloc),
        Some(verify),
        Some(copy_to),
        Some(get_nr_nodes),
        Some(lock),
        Some(unlock),
        Some(smp_call),
        Some(handler),
    ) = (
        alloc_fn,
        verify_fn,
        copy_to_fn,
        get_nr_nodes_fn,
        lock_fn,
        unlock_fn,
        smp_call_fn,
        handler_fn,
    )
    else {
        return -(EFAULT as CLong);
    };

    if vm.is_null() || page_table_lock.is_null() || cpu_set.is_null() || proc.is_null() {
        return -(EFAULT as CLong);
    }

    let count_size = count as SizeT;
    let ptr_bytes = ptr_size.wrapping_mul(count_size);
    let int_bytes = int_size.wrapping_mul(count_size);
    let pte_bytes = pte_size.wrapping_mul(count_size);
    let ulong_bytes = ulong_size.wrapping_mul(count_size);
    let mut start = rdtsc_fn.map_or(0, |rdtsc| rdtsc());

    let virt_addr = alloc(ptr_bytes, alloc_flags);
    if virt_addr.is_null() {
        return -(ENOMEM as CLong);
    }
    let nr_pages = alloc(int_bytes, alloc_flags);
    if nr_pages.is_null() {
        move_pages_free_arrays(
            free_fn,
            virt_addr,
            nr_pages,
            null_mut(),
            null_mut(),
            null_mut(),
            null_mut(),
        );
        return -(ENOMEM as CLong);
    }
    let nodes = alloc(int_bytes, alloc_flags);
    if nodes.is_null() {
        move_pages_free_arrays(
            free_fn,
            virt_addr,
            nr_pages,
            nodes,
            null_mut(),
            null_mut(),
            null_mut(),
        );
        return -(ENOMEM as CLong);
    }
    let status = alloc(int_bytes, alloc_flags);
    if status.is_null() {
        move_pages_free_arrays(
            free_fn,
            virt_addr,
            nr_pages,
            nodes,
            status,
            null_mut(),
            null_mut(),
        );
        return -(ENOMEM as CLong);
    }
    let ptep = alloc(pte_bytes, alloc_flags);
    if ptep.is_null() {
        move_pages_free_arrays(
            free_fn,
            virt_addr,
            nr_pages,
            nodes,
            status,
            ptep,
            null_mut(),
        );
        return -(ENOMEM as CLong);
    }
    let dst_phys = alloc(ulong_bytes, alloc_flags);
    if dst_phys.is_null() {
        move_pages_free_arrays(free_fn, virt_addr, nr_pages, nodes, status, ptep, dst_phys);
        return -(ENOMEM as CLong);
    }

    start = move_pages_log_delta(log_fn, rdtsc_fn, MOVE_PAGES_LOG_INIT_MALLOC, start);

    let mut ret = 0;
    if verify(vm, user_virt_addr_addr, ptr_bytes) != 0 {
        ret = -EFAULT;
    } else if user_nodes_addr != 0 && verify(vm, user_nodes_addr, int_bytes) != 0 {
        ret = -EFAULT;
    } else if verify(vm, user_status_addr, int_bytes) != 0 {
        ret = -EFAULT;
    }

    if ret == 0 && user_nodes_addr != 0 {
        if let Some(copy_from) = copy_from_fn {
            let _ = copy_from(nodes.cast::<u8>(), user_nodes_addr, int_bytes);
            let nr_nodes = get_nr_nodes();
            let nodes_i32 = nodes.cast::<CInt>();
            let mut i = 0usize;
            while i < count_size {
                let node = read_volatile(nodes_i32.add(i));
                if node < 0 || node >= nr_nodes {
                    ret = -ENODEV;
                    break;
                }
                i += 1;
            }
        } else {
            ret = -EFAULT;
        }
    }

    start = move_pages_log_delta(log_fn, rdtsc_fn, MOVE_PAGES_LOG_INIT_VERIFY, start);

    if ret == 0 {
        let mut request = MaybeUninit::<MovePagesSmpReq>::uninit();
        lock(page_table_lock);
        ret = move_pages_smp_req_prepare_result(
            request.as_mut_ptr(),
            count,
            user_virt_addr_addr as *mut *const c_void,
            user_status_addr as *mut CInt,
            user_nodes_addr as *const CInt,
            virt_addr.cast::<*mut c_void>(),
            status.cast::<CInt>(),
            ptep.cast::<*mut c_void>(),
            nodes.cast::<CInt>(),
            nr_pages.cast::<CInt>(),
            dst_phys.cast::<CULong>(),
            proc,
        );
        if ret == 0 {
            ret = smp_call(
                cpu_set,
                Some(handler),
                request.as_mut_ptr().cast::<c_void>(),
            );
        }
        unlock(page_table_lock);
    }

    if ret == 0 {
        let _ = move_pages_log_delta(log_fn, rdtsc_fn, MOVE_PAGES_LOG_PARALLEL, start);
        if copy_to(user_status_addr, status.cast::<u8>(), int_bytes) != 0 {
            ret = -EFAULT;
        }
    }

    move_pages_free_arrays(free_fn, virt_addr, nr_pages, nodes, status, ptep, dst_phys);
    ret as CLong
}

#[no_mangle]
pub extern "C" fn getrusage_who_result(who: CInt) -> CInt {
    if who != RUSAGE_SELF && who != RUSAGE_CHILDREN && who != RUSAGE_THREAD {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn getrusage_dispatch_result(who: CInt) -> CInt {
    if who == RUSAGE_SELF {
        GETRUSAGE_DISPATCH_SELF
    } else if who == RUSAGE_CHILDREN {
        GETRUSAGE_DISPATCH_CHILDREN
    } else if who == RUSAGE_THREAD {
        GETRUSAGE_DISPATCH_THREAD
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn getrusage_thread_update_action_result(
    is_current_thread: CInt,
    status: CInt,
    in_kernel: CInt,
) -> CInt {
    if is_current_thread == 0 && status == PS_RUNNING && in_kernel == 0 {
        GETRUSAGE_THREAD_UPDATE_INTERRUPT
    } else {
        GETRUSAGE_THREAD_UPDATE_READY
    }
}

#[no_mangle]
pub unsafe extern "C" fn getrusage_thread_times_update_prepare_result(
    thread_addr: CULong,
    times_update_offset: CULong,
    update_action: CInt,
) -> CInt {
    if thread_addr == 0 {
        return 0;
    }

    let times_update = thread_addr.wrapping_add(times_update_offset) as *mut CInt;
    if update_action == GETRUSAGE_THREAD_UPDATE_INTERRUPT {
        unsafe {
            write(times_update, 0);
        }
        return 1;
    }

    unsafe {
        write(times_update, 1);
    }
    0
}

#[no_mangle]
pub extern "C" fn getrusage_maxrss_kb_result(maxrss: CLong) -> CLong {
    maxrss / 1024
}

#[inline(always)]
fn getrusage_tsc_to_timespec(tsc: CULong, clocks_per_sec: CULong) -> (CLong, CLong) {
    if clocks_per_sec == 0 {
        return (0, 0);
    }

    let mut sec = (tsc / clocks_per_sec) as CLong;
    let mut nsec =
        ((NS_PER_SEC as CULong).wrapping_mul(tsc % clocks_per_sec) / clocks_per_sec) as CLong;

    if nsec >= NS_PER_SEC {
        nsec -= NS_PER_SEC;
        sec += 1;
    }

    (sec, nsec)
}

#[no_mangle]
pub unsafe extern "C" fn getrusage_timespec_add_tsc_result(
    secp: *mut CLong,
    nsecp: *mut CLong,
    tsc: CULong,
    clocks_per_sec: CULong,
) {
    let (add_sec, add_nsec) = getrusage_tsc_to_timespec(tsc, clocks_per_sec);
    let mut sec = *secp + add_sec;
    let mut nsec = *nsecp + add_nsec;

    while nsec >= NS_PER_SEC {
        sec += 1;
        nsec -= NS_PER_SEC;
    }

    write(secp, sec);
    write(nsecp, nsec);
}

#[no_mangle]
pub unsafe extern "C" fn getrusage_fill_timespec_result(
    usage: *mut RUsage,
    utime_sec: CLong,
    utime_nsec: CLong,
    stime_sec: CLong,
    stime_nsec: CLong,
    maxrss: CLong,
) {
    (*usage).ru_utime.tv_sec = utime_sec;
    (*usage).ru_utime.tv_usec = utime_nsec / 1000;
    (*usage).ru_stime.tv_sec = stime_sec;
    (*usage).ru_stime.tv_usec = stime_nsec / 1000;
    (*usage).ru_maxrss = getrusage_maxrss_kb_result(maxrss);
}

unsafe fn read_timespec(base: *mut u8, offset: SizeT) -> TimeSpec {
    let ts = field_ptr::<TimeSpec>(base, offset);
    TimeSpec {
        tv_sec: read_volatile(&(*ts).tv_sec),
        tv_nsec: read_volatile(&(*ts).tv_nsec),
    }
}

unsafe fn write_timespec(base: *mut u8, offset: SizeT, value: &TimeSpec) {
    let ts = field_ptr::<TimeSpec>(base, offset);
    write_volatile(&mut (*ts).tv_sec, value.tv_sec);
    write_volatile(&mut (*ts).tv_nsec, value.tv_nsec);
}

fn timespec_add(dst: &mut TimeSpec, src: &TimeSpec) {
    dst.tv_sec += src.tv_sec;
    dst.tv_nsec += src.tv_nsec;
    while dst.tv_nsec >= NS_PER_SEC {
        dst.tv_sec += 1;
        dst.tv_nsec -= NS_PER_SEC;
    }
}

fn timespec_add_tsc(dst: &mut TimeSpec, tsc: CULong, clocks_per_sec: CULong) {
    let (sec, nsec) = getrusage_tsc_to_timespec(tsc, clocks_per_sec);
    let add = TimeSpec {
        tv_sec: sec,
        tv_nsec: nsec,
    };
    timespec_add(dst, &add);
}

unsafe fn for_each_thread(
    proc: *mut u8,
    offsets: &SyscallCputimeOffsets,
    mut visit: impl FnMut(*mut u8),
) {
    let head = field_ptr::<AbiListHead>(proc, offsets.proc_threads_list_offset);
    let mut pos = (*head).next;
    while !pos.is_null() && pos != head {
        let next = (*pos).next;
        let thread = (pos as *mut u8).sub(offsets.thread_siblings_list_offset);
        visit(thread);
        pos = next;
    }
}

unsafe fn rusage_current_process(thread: *mut u8, offsets: &SyscallCputimeOffsets) -> *mut u8 {
    *field_ptr::<*mut u8>(thread, offsets.thread_proc_offset)
}

unsafe fn rusage_request_thread_update(
    current: *mut u8,
    child: *mut u8,
    offsets: &SyscallCputimeOffsets,
    interrupt_fn: SyscallInterruptCpuFn,
) {
    let update_action = getrusage_thread_update_action_result(
        (child == current) as CInt,
        *field_ptr::<CInt>(child, offsets.thread_status_offset),
        *field_ptr::<CInt>(child, offsets.thread_in_kernel_offset),
    );
    if getrusage_thread_times_update_prepare_result(
        child as CULong,
        offsets.thread_times_update_offset as CULong,
        update_action,
    ) != 0
    {
        interrupt_fn(*field_ptr::<CInt>(child, offsets.thread_cpu_id_offset));
    }
}

unsafe fn rusage_wait_thread_update(
    child: *mut u8,
    offsets: &SyscallCputimeOffsets,
    pause_fn: SyscallCpuPauseFn,
) {
    while *field_ptr::<CInt>(child, offsets.thread_times_update_offset) == 0 {
        pause_fn();
    }
}

unsafe fn rusage_add_thread_user_system(
    utime: &mut TimeSpec,
    stime: &mut TimeSpec,
    child: *mut u8,
    offsets: &SyscallCputimeOffsets,
    clocks_per_sec: CULong,
) {
    timespec_add_tsc(
        utime,
        *field_ptr::<CULong>(child, offsets.thread_user_tsc_offset),
        clocks_per_sec,
    );
    timespec_add_tsc(
        stime,
        *field_ptr::<CULong>(child, offsets.thread_system_tsc_offset),
        clocks_per_sec,
    );
}

unsafe fn rusage_process_cputime(
    thread: *mut u8,
    proc: *mut u8,
    offsets: &SyscallCputimeOffsets,
    clocks_per_sec: CULong,
    lock_fn: SyscallThreadsLockFn,
    unlock_fn: SyscallThreadsUnlockFn,
    lock_arg: *mut c_void,
    interrupt_fn: SyscallInterruptCpuFn,
    pause_fn: SyscallCpuPauseFn,
) -> TimeSpec {
    lock_fn(proc.cast::<c_void>(), lock_arg);

    for_each_thread(proc, offsets, |child| {
        if child != thread
            && unsafe { *field_ptr::<CInt>(child, offsets.thread_status_offset) } == PS_RUNNING
            && unsafe { *field_ptr::<CInt>(child, offsets.thread_in_kernel_offset) } == 0
        {
            unsafe {
                *field_ptr::<CInt>(child, offsets.thread_times_update_offset) = 0;
                interrupt_fn(*field_ptr::<CInt>(child, offsets.thread_cpu_id_offset));
            }
        }
    });

    let mut total = read_timespec(proc, offsets.proc_utime_offset);
    let stime = read_timespec(proc, offsets.proc_stime_offset);
    timespec_add(&mut total, &stime);

    for_each_thread(proc, offsets, |child| unsafe {
        rusage_wait_thread_update(child, offsets, pause_fn);
        let tsc = (*field_ptr::<CULong>(child, offsets.thread_user_tsc_offset)).wrapping_add(
            *field_ptr::<CULong>(child, offsets.thread_system_tsc_offset),
        );
        timespec_add_tsc(&mut total, tsc, clocks_per_sec);
    });

    unlock_fn(proc.cast::<c_void>(), lock_arg);
    total
}

#[no_mangle]
pub unsafe extern "C" fn getrusage_body_result(
    who: CInt,
    usage_addr: CULong,
    thread: *mut u8,
    clocks_per_sec: CULong,
    offsets: *const SyscallCputimeOffsets,
    lock_fn: Option<SyscallThreadsLockFn>,
    unlock_fn: Option<SyscallThreadsUnlockFn>,
    lock_arg: *mut c_void,
    interrupt_fn: Option<SyscallInterruptCpuFn>,
    pause_fn: Option<SyscallCpuPauseFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    let error = getrusage_who_result(who);
    if error != 0 {
        return error as CLong;
    }
    if thread.is_null() || offsets.is_null() {
        return -EFAULT as CLong;
    }
    let Some(copy_to) = copy_to_fn else {
        return -EFAULT as CLong;
    };
    let offsets = &*offsets;
    let proc = rusage_current_process(thread, offsets);
    if proc.is_null() {
        return -EFAULT as CLong;
    }

    let mut usage = MaybeUninit::<RUsage>::uninit();
    let usage_ptr = usage.as_mut_ptr();
    zero_rusage(usage_ptr);

    match getrusage_dispatch_result(who) {
        GETRUSAGE_DISPATCH_SELF => {
            let Some(lock) = lock_fn else {
                return -EFAULT as CLong;
            };
            let Some(unlock) = unlock_fn else {
                return -EFAULT as CLong;
            };
            let Some(interrupt) = interrupt_fn else {
                return -EFAULT as CLong;
            };
            let Some(pause) = pause_fn else {
                return -EFAULT as CLong;
            };

            lock(proc.cast::<c_void>(), lock_arg);
            for_each_thread(proc, offsets, |child| unsafe {
                rusage_request_thread_update(thread, child, offsets, interrupt);
            });

            let mut utime = read_timespec(proc, offsets.proc_utime_offset);
            let mut stime = read_timespec(proc, offsets.proc_stime_offset);
            for_each_thread(proc, offsets, |child| unsafe {
                rusage_wait_thread_update(child, offsets, pause);
                rusage_add_thread_user_system(
                    &mut utime,
                    &mut stime,
                    child,
                    offsets,
                    clocks_per_sec,
                );
            });
            unlock(proc.cast::<c_void>(), lock_arg);

            getrusage_fill_timespec_result(
                usage_ptr,
                utime.tv_sec,
                utime.tv_nsec,
                stime.tv_sec,
                stime.tv_nsec,
                *field_ptr::<CLong>(proc, offsets.proc_maxrss_offset),
            );
        }
        GETRUSAGE_DISPATCH_CHILDREN => {
            let utime = read_timespec(proc, offsets.proc_utime_children_offset);
            let stime = read_timespec(proc, offsets.proc_stime_children_offset);
            getrusage_fill_timespec_result(
                usage_ptr,
                utime.tv_sec,
                utime.tv_nsec,
                stime.tv_sec,
                stime.tv_nsec,
                *field_ptr::<CLong>(proc, offsets.proc_maxrss_children_offset),
            );
        }
        GETRUSAGE_DISPATCH_THREAD => {
            let mut utime = TimeSpec {
                tv_sec: 0,
                tv_nsec: 0,
            };
            let mut stime = TimeSpec {
                tv_sec: 0,
                tv_nsec: 0,
            };
            rusage_add_thread_user_system(&mut utime, &mut stime, thread, offsets, clocks_per_sec);
            getrusage_fill_timespec_result(
                usage_ptr,
                utime.tv_sec,
                utime.tv_nsec,
                stime.tv_sec,
                stime.tv_nsec,
                *field_ptr::<CLong>(proc, offsets.proc_maxrss_offset),
            );
        }
        _ => return -EINVAL as CLong,
    }

    if copy_to(usage_addr, usage_ptr.cast::<u8>(), size_of::<RUsage>()) != 0 {
        return -EFAULT as CLong;
    }
    0
}

#[no_mangle]
pub extern "C" fn itimer_which_result(which: CInt) -> CInt {
    if which != ITIMER_REAL && which != ITIMER_VIRTUAL && which != ITIMER_PROF {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn itimer_is_real(which: CInt) -> CInt {
    if which == ITIMER_REAL { 1 } else { 0 }
}

#[no_mangle]
pub extern "C" fn itimer_should_start(value_sec: CLong, value_usec: CLong) -> CInt {
    if value_sec == 0 && value_usec == 0 {
        0
    } else {
        1
    }
}

#[inline(always)]
fn itimer_timeval_is_active(value: &TimeVal) -> bool {
    value.tv_sec != 0 || value.tv_usec != 0
}

#[inline(always)]
fn itimer_timespec_to_timeval(ts: &TimeSpec) -> TimeVal {
    TimeVal {
        tv_sec: ts.tv_sec,
        tv_usec: ts.tv_nsec / 1000,
    }
}

#[inline(always)]
fn itimer_timeval_sub(dst: &mut TimeVal, src: &TimeVal) {
    dst.tv_sec -= src.tv_sec;
    dst.tv_usec -= src.tv_usec;
    while dst.tv_usec < 0 {
        dst.tv_sec -= 1;
        dst.tv_usec += 1_000_000;
    }
}

#[inline(always)]
unsafe fn itimer_slot(
    thread: *mut u8,
    offsets: *const SyscallItimerOffsets,
    which: CInt,
) -> (*mut ITimerVal, *mut TimeSpec) {
    let offsets = &*offsets;
    if which == ITIMER_VIRTUAL {
        (
            field_ptr::<ITimerVal>(thread, offsets.thread_itimer_virtual_offset),
            field_ptr::<TimeSpec>(thread, offsets.thread_itimer_virtual_value_offset),
        )
    } else {
        (
            field_ptr::<ITimerVal>(thread, offsets.thread_itimer_prof_offset),
            field_ptr::<TimeSpec>(thread, offsets.thread_itimer_prof_value_offset),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn itimer_snapshot_current_result(
    timer_addr: CULong,
    elapsed_addr: CULong,
    out_addr: CULong,
) {
    let timer = timer_addr as *const ITimerVal;
    let elapsed = elapsed_addr as *const TimeSpec;
    let out = out_addr as *mut ITimerVal;
    let src = &*timer;

    (*out).it_interval.tv_sec = src.it_interval.tv_sec;
    (*out).it_interval.tv_usec = src.it_interval.tv_usec;
    (*out).it_value.tv_sec = src.it_value.tv_sec;
    (*out).it_value.tv_usec = src.it_value.tv_usec;

    if itimer_timeval_is_active(&(*out).it_value) {
        let elapsed_tv = itimer_timespec_to_timeval(&*elapsed);
        itimer_timeval_sub(&mut (*out).it_value, &elapsed_tv);
    }
}

#[no_mangle]
pub unsafe extern "C" fn setitimer_body_result(
    which: CInt,
    new_addr: CULong,
    old_addr: CULong,
    thread: *mut c_void,
    offsets: *const SyscallItimerOffsets,
    syscall_nr: CInt,
    syscall3_fn: Option<SyscallDoSyscall3Fn>,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    set_timer_fn: Option<SyscallSetTimerFn>,
) -> CLong {
    let error = itimer_which_result(which);
    if error != 0 {
        return error as CLong;
    }

    if itimer_is_real(which) != 0 {
        let Some(syscall3) = syscall3_fn else {
            return -(EINVAL as CLong);
        };
        return syscall3(syscall_nr, which as CULong, new_addr, old_addr);
    }

    if thread.is_null() || offsets.is_null() {
        return -(EINVAL as CLong);
    }

    let (timer, elapsed) = itimer_slot(thread.cast::<u8>(), offsets, which);
    if old_addr != 0 {
        let Some(copy_to) = copy_to_fn else {
            return -(EFAULT as CLong);
        };
        let mut snapshot = MaybeUninit::<ITimerVal>::uninit();
        itimer_snapshot_current_result(
            timer as CULong,
            elapsed as CULong,
            snapshot.as_mut_ptr() as CULong,
        );
        if copy_to(
            old_addr,
            snapshot.as_ptr().cast::<u8>(),
            size_of::<ITimerVal>(),
        ) != 0
        {
            return -(EFAULT as CLong);
        }
    }

    if new_addr == 0 {
        return 0;
    }

    let Some(copy_from) = copy_from_fn else {
        return -(EFAULT as CLong);
    };
    if copy_from(timer.cast::<u8>(), new_addr, size_of::<ITimerVal>()) != 0 {
        return -(EFAULT as CLong);
    }

    write_volatile(&mut (*elapsed).tv_sec, 0);
    write_volatile(&mut (*elapsed).tv_nsec, 0);

    let start = itimer_should_start((*timer).it_value.tv_sec, (*timer).it_value.tv_usec);
    *field_ptr::<CInt>(thread.cast::<u8>(), (*offsets).thread_itimer_enabled_offset) = start;

    let Some(set_timer) = set_timer_fn else {
        return -(EINVAL as CLong);
    };
    set_timer(0);
    0
}

#[no_mangle]
pub unsafe extern "C" fn getitimer_body_result(
    which: CInt,
    old_addr: CULong,
    thread: *mut c_void,
    offsets: *const SyscallItimerOffsets,
    syscall_nr: CInt,
    syscall2_fn: Option<SyscallDoSyscall2Fn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    let error = itimer_which_result(which);
    if error != 0 {
        return error as CLong;
    }

    if itimer_is_real(which) != 0 {
        let Some(syscall2) = syscall2_fn else {
            return -(EINVAL as CLong);
        };
        return syscall2(syscall_nr, which as CULong, old_addr);
    }

    if thread.is_null() || offsets.is_null() {
        return -(EINVAL as CLong);
    }

    if old_addr == 0 {
        return 0;
    }

    let Some(copy_to) = copy_to_fn else {
        return -(EFAULT as CLong);
    };
    let (timer, elapsed) = itimer_slot(thread.cast::<u8>(), offsets, which);
    let mut snapshot = MaybeUninit::<ITimerVal>::uninit();
    itimer_snapshot_current_result(
        timer as CULong,
        elapsed as CULong,
        snapshot.as_mut_ptr() as CULong,
    );
    if copy_to(
        old_addr,
        snapshot.as_ptr().cast::<u8>(),
        size_of::<ITimerVal>(),
    ) != 0
    {
        return -(EFAULT as CLong);
    }
    0
}

#[no_mangle]
pub extern "C" fn clock_gettime_dispatch(
    clock_id: CInt,
    local_support: CInt,
    has_ts: CInt,
) -> CInt {
    if has_ts == 0 {
        return TIME_DISPATCH_NOOP;
    }

    if local_support != 0 && clock_id == CLOCK_REALTIME {
        return TIME_DISPATCH_LOCAL_REALTIME;
    }

    if clock_id == CLOCK_PROCESS_CPUTIME_ID {
        return TIME_DISPATCH_PROCESS_CPUTIME;
    }

    if clock_id == CLOCK_THREAD_CPUTIME_ID {
        return TIME_DISPATCH_THREAD_CPUTIME;
    }

    TIME_DISPATCH_FORWARD
}

#[no_mangle]
pub unsafe extern "C" fn clock_gettime_body_result(
    clock_id: CInt,
    ts_addr: CULong,
    local_support: CInt,
    syscall_nr: CInt,
    thread: *mut u8,
    clocks_per_sec: CULong,
    offsets: *const SyscallCputimeOffsets,
    gettime_fn: Option<SyscallGettimeFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    syscall2_fn: Option<SyscallDoSyscall2Fn>,
    lock_fn: Option<SyscallThreadsLockFn>,
    unlock_fn: Option<SyscallThreadsUnlockFn>,
    lock_arg: *mut c_void,
    interrupt_fn: Option<SyscallInterruptCpuFn>,
    pause_fn: Option<SyscallCpuPauseFn>,
) -> CLong {
    let dispatch = clock_gettime_dispatch(clock_id, local_support, (ts_addr != 0) as CInt);
    if dispatch == TIME_DISPATCH_NOOP {
        return 0;
    }

    let Some(copy_to) = copy_to_fn else {
        return -EFAULT as CLong;
    };

    if dispatch == TIME_DISPATCH_LOCAL_REALTIME {
        let Some(gettime) = gettime_fn else {
            return -EFAULT as CLong;
        };
        let mut ts = MaybeUninit::<TimeSpec>::uninit();
        gettime(ts.as_mut_ptr());
        return copy_to(ts_addr, ts.as_ptr().cast::<u8>(), size_of::<TimeSpec>());
    }

    if dispatch == TIME_DISPATCH_PROCESS_CPUTIME || dispatch == TIME_DISPATCH_THREAD_CPUTIME {
        if thread.is_null() || offsets.is_null() {
            return -EFAULT as CLong;
        }
        let offsets = &*offsets;
        let proc = rusage_current_process(thread, offsets);
        if proc.is_null() {
            return -EFAULT as CLong;
        }

        let ts = if dispatch == TIME_DISPATCH_PROCESS_CPUTIME {
            let Some(lock) = lock_fn else {
                return -EFAULT as CLong;
            };
            let Some(unlock) = unlock_fn else {
                return -EFAULT as CLong;
            };
            let Some(interrupt) = interrupt_fn else {
                return -EFAULT as CLong;
            };
            let Some(pause) = pause_fn else {
                return -EFAULT as CLong;
            };
            rusage_process_cputime(
                thread,
                proc,
                offsets,
                clocks_per_sec,
                lock,
                unlock,
                lock_arg,
                interrupt,
                pause,
            )
        } else {
            let mut ts = TimeSpec {
                tv_sec: 0,
                tv_nsec: 0,
            };
            let tsc = (*field_ptr::<CULong>(thread, offsets.thread_user_tsc_offset)).wrapping_add(
                *field_ptr::<CULong>(thread, offsets.thread_system_tsc_offset),
            );
            timespec_add_tsc(&mut ts, tsc, clocks_per_sec);
            ts
        };
        return copy_to(
            ts_addr,
            (&ts as *const TimeSpec).cast::<u8>(),
            size_of::<TimeSpec>(),
        );
    }

    let Some(syscall2) = syscall2_fn else {
        return -EFAULT as CLong;
    };
    syscall2(syscall_nr, clock_id as CULong, ts_addr)
}

#[no_mangle]
pub extern "C" fn gettimeofday_dispatch(has_tv: CInt, has_tz: CInt, local_support: CInt) -> CInt {
    if has_tv == 0 && has_tz == 0 {
        return TIME_DISPATCH_NOOP;
    }

    if has_tz == 0 && local_support != 0 {
        return TIME_DISPATCH_LOCAL_REALTIME;
    }

    TIME_DISPATCH_FORWARD
}

#[no_mangle]
pub unsafe extern "C" fn gettimeofday_body_result(
    tv_addr: CULong,
    tz_addr: CULong,
    local_support: CInt,
    syscall_nr: CInt,
    gettime_fn: Option<SyscallGettimeFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    syscall2_fn: Option<SyscallDoSyscall2Fn>,
) -> CLong {
    let dispatch = gettimeofday_dispatch(
        if tv_addr != 0 { 1 } else { 0 },
        if tz_addr != 0 { 1 } else { 0 },
        local_support,
    );
    if dispatch == TIME_DISPATCH_NOOP {
        return 0;
    }

    if dispatch == TIME_DISPATCH_LOCAL_REALTIME {
        let Some(gettime) = gettime_fn else {
            return -EFAULT as CLong;
        };
        let Some(copy_to) = copy_to_fn else {
            return -EFAULT as CLong;
        };
        let mut ts = MaybeUninit::<TimeSpec>::uninit();
        gettime(ts.as_mut_ptr());
        let ts = ts.assume_init();
        let tv = TimeVal {
            tv_sec: ts.tv_sec,
            tv_usec: ts.tv_nsec / 1000,
        };
        return copy_to(
            tv_addr,
            (&tv as *const TimeVal).cast::<u8>(),
            size_of::<TimeVal>(),
        );
    }

    let Some(syscall2) = syscall2_fn else {
        return -EFAULT as CLong;
    };
    syscall2(syscall_nr, tv_addr, tz_addr)
}

#[inline(always)]
unsafe fn settimeofday_log(
    log_fn: Option<SettimeofdayLogFn>,
    event: CInt,
    utv_addr: CULong,
    utz_addr: CULong,
    sec: CLong,
    nsec: CLong,
    error: CLong,
) {
    if let Some(log) = log_fn {
        log(event, utv_addr, utz_addr, sec, nsec, error);
    }
}

#[no_mangle]
pub unsafe extern "C" fn settimeofday_body_result(
    utv_addr: CULong,
    utz_addr: CULong,
    local_support: CInt,
    clocks_per_sec: CULong,
    syscall_nr: CInt,
    ctx: *mut c_void,
    lock_arg: *mut c_void,
    version_arg: *mut c_void,
    origin: *mut TimeSpec,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    rdtsc_fn: Option<SyscallRdtscFn>,
    forward_fn: Option<SyscallForwardContextFn>,
    atomic_read_fn: Option<SyscallAtomic64ReadFn>,
    atomic_inc_fn: Option<SyscallAtomic64IncFn>,
    wmb_fn: Option<SyscallWmbFn>,
    panic_fn: Option<SyscallPanicFn>,
    log_fn: Option<SettimeofdayLogFn>,
) -> CLong {
    settimeofday_log(log_fn, SETTIMEOFDAY_LOG_ENTER, utv_addr, utz_addr, 0, 0, 0);

    if let Some(lock) = lock_fn {
        lock(lock_arg);
    }

    let mut error: CLong;
    let mut update_origin = false;
    let mut newts = TimeSpec {
        tv_sec: 0,
        tv_nsec: 0,
    };

    let Some(atomic_read) = atomic_read_fn else {
        error = -EFAULT as CLong;
        goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
        return error;
    };

    if (atomic_read(version_arg) & 1) != 0 {
        if let Some(panic) = panic_fn {
            panic();
        }
    }

    if utv_addr != 0 && local_support != 0 {
        let Some(copy_from) = copy_from_fn else {
            error = -EFAULT as CLong;
            goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
            return error;
        };
        let Some(rdtsc) = rdtsc_fn else {
            error = -EFAULT as CLong;
            goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
            return error;
        };
        if clocks_per_sec == 0 {
            error = -EINVAL as CLong;
            goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
            return error;
        }
        let mut tv = MaybeUninit::<TimeVal>::uninit();
        if copy_from(tv.as_mut_ptr().cast::<u8>(), utv_addr, size_of::<TimeVal>()) != 0 {
            error = -EFAULT as CLong;
            goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
            return error;
        }

        let tv = tv.assume_init();
        newts.tv_sec = tv.tv_sec;
        newts.tv_nsec = tv.tv_usec.wrapping_mul(1000);

        let tsc = rdtsc();
        newts.tv_sec = newts.tv_sec.wrapping_sub((tsc / clocks_per_sec) as CLong);
        newts.tv_nsec = newts.tv_nsec.wrapping_sub(
            ((NS_PER_SEC as CULong).wrapping_mul(tsc % clocks_per_sec) / clocks_per_sec) as CLong,
        );
        if newts.tv_nsec < 0 {
            newts.tv_sec = newts.tv_sec.wrapping_sub(1);
            newts.tv_nsec = newts.tv_nsec.wrapping_add(NS_PER_SEC);
        }
        update_origin = true;
    }

    let Some(forward) = forward_fn else {
        error = -EFAULT as CLong;
        goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
        return error;
    };
    error = forward(syscall_nr, ctx);

    if error == 0 && update_origin {
        let Some(atomic_inc) = atomic_inc_fn else {
            error = -EFAULT as CLong;
            goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
            return error;
        };
        let Some(wmb) = wmb_fn else {
            error = -EFAULT as CLong;
            goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
            return error;
        };
        if origin.is_null() {
            error = -EFAULT as CLong;
            goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
            return error;
        }

        settimeofday_log(
            log_fn,
            SETTIMEOFDAY_LOG_ORIGIN,
            utv_addr,
            utz_addr,
            newts.tv_sec,
            newts.tv_nsec,
            0,
        );
        atomic_inc(version_arg);
        wmb();
        write(origin, newts);
        wmb();
        atomic_inc(version_arg);
    }

    goto_settimeofday_out(unlock_fn, lock_arg, log_fn, utv_addr, utz_addr, error);
    error
}

#[inline(always)]
unsafe fn goto_settimeofday_out(
    unlock_fn: Option<SyscallRwlockFn>,
    lock_arg: *mut c_void,
    log_fn: Option<SettimeofdayLogFn>,
    utv_addr: CULong,
    utz_addr: CULong,
    error: CLong,
) {
    if let Some(unlock) = unlock_fn {
        unlock(lock_arg);
    }
    settimeofday_log(
        log_fn,
        SETTIMEOFDAY_LOG_EXIT,
        utv_addr,
        utz_addr,
        0,
        0,
        error,
    );
}

#[no_mangle]
pub extern "C" fn nanosleep_validate_timespec(sec: CLong, nsec: CLong) -> CInt {
    if sec < 0 || nsec < 0 || nsec >= NS_PER_SEC {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn nanosleep_body_result(
    tv_addr: CULong,
    rem_addr: CULong,
    local_support: CInt,
    syscall_nr: CInt,
    thread: *mut c_void,
    monitor: *mut u8,
    monitor_status_offset: SizeT,
    heavy_status: CInt,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    syscall2_fn: Option<SyscallDoSyscall2Fn>,
    rdtsc_fn: Option<SyscallRdtscFn>,
    ns_per_tsc_fn: Option<SyscallNsPerTscFn>,
    has_sigpending_fn: Option<SyscallHasSigpendingFn>,
    cpu_pause_fn: Option<SyscallCpuPauseFn>,
) -> CLong {
    *field_ptr::<CInt>(monitor, monitor_status_offset) = heavy_status;

    if local_support == 0 {
        let Some(syscall2) = syscall2_fn else {
            return -EFAULT as CLong;
        };
        return syscall2(syscall_nr, tv_addr, rem_addr);
    }

    let Some(copy_from) = copy_from_fn else {
        return -EFAULT as CLong;
    };
    let Some(copy_to) = copy_to_fn else {
        return -EFAULT as CLong;
    };
    let Some(rdtsc) = rdtsc_fn else {
        return -EFAULT as CLong;
    };
    let Some(ns_per_tsc) = ns_per_tsc_fn else {
        return -EFAULT as CLong;
    };
    let Some(has_sigpending) = has_sigpending_fn else {
        return -EFAULT as CLong;
    };
    let Some(cpu_pause) = cpu_pause_fn else {
        return -EFAULT as CLong;
    };

    let start_tsc = rdtsc();
    let mut tv = MaybeUninit::<TimeSpec>::uninit();
    if copy_from(tv.as_mut_ptr().cast::<u8>(), tv_addr, size_of::<TimeSpec>()) != 0 {
        return -EFAULT as CLong;
    }
    let tv = tv.assume_init();

    let ret = nanosleep_validate_timespec(tv.tv_sec, tv.tv_nsec);
    if ret != 0 {
        return ret as CLong;
    }

    let nanosecs = (tv.tv_sec as CULong)
        .wrapping_mul(NS_PER_SEC as CULong)
        .wrapping_add(tv.tv_nsec as CULong);
    let ns_per_tsc_value = ns_per_tsc();
    if ns_per_tsc_value == 0 {
        return -EINVAL as CLong;
    }
    let tscs = nanosecs.wrapping_mul(1000) / ns_per_tsc_value;
    let mut ret = 0;

    while rdtsc().wrapping_sub(start_tsc) < tscs {
        if has_sigpending(thread) != 0 {
            ret = -EINTR;
            break;
        }
        cpu_pause();
    }

    if ret == -EINTR && rem_addr != 0 {
        let tscs_rem = tscs.wrapping_sub(rdtsc().wrapping_sub(start_tsc)) as CLong;
        let tscs_rem = if tscs_rem < 0 { 0 } else { tscs_rem as CULong };
        let nanosecs_rem = tscs_rem.wrapping_mul(ns_per_tsc_value) / 1000;
        let rem = TimeSpec {
            tv_sec: (nanosecs_rem / NS_PER_SEC as CULong) as CLong,
            tv_nsec: (nanosecs_rem % NS_PER_SEC as CULong) as CLong,
        };
        if copy_to(
            rem_addr,
            (&rem as *const TimeSpec).cast::<u8>(),
            size_of::<TimeSpec>(),
        ) != 0
        {
            ret = -EFAULT;
        }
    }

    ret as CLong
}

#[no_mangle]
pub extern "C" fn rt_sigtimedwait_prepare(
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
    has_set: CInt,
) -> CInt {
    if sigsetsize > expected_sigset_size {
        return -EINVAL;
    }

    if has_set == 0 {
        return -EFAULT;
    }

    0
}

#[no_mangle]
pub extern "C" fn rt_sigtimedwait_timeout_result(
    sec: CLong,
    nsec: CLong,
    local_support: CInt,
) -> CInt {
    if sec < 0 || nsec < 0 || nsec >= NS_PER_SEC {
        return -EINVAL;
    }

    if local_support == 0 && (sec != 0 || nsec != 0) {
        return -EOPNOTSUPP;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn rt_sigtimedwait_prepare_masks(
    raw_wait_mask: CULong,
    current_mask: CULong,
    wait_maskp: *mut CULong,
    blocked_maskp: *mut CULong,
    interrupt_maskp: *mut CULong,
) {
    let wait_mask = raw_wait_mask & !(SIGKILL_MASK | SIGSTOP_MASK);
    let blocked_mask = current_mask | wait_mask;

    write(wait_maskp, wait_mask);
    write(blocked_maskp, blocked_mask);
    write(interrupt_maskp, !blocked_mask);
}

#[no_mangle]
pub unsafe extern "C" fn rt_sigtimedwait_deadline(
    now_sec: CLong,
    now_nsec: CLong,
    timeout_sec: CLong,
    timeout_nsec: CLong,
    deadline_secp: *mut CLong,
    deadline_nsecp: *mut CLong,
) {
    let mut sec = now_sec.wrapping_add(timeout_sec);
    let mut nsec = now_nsec.wrapping_add(timeout_nsec);

    if nsec >= NS_PER_SEC {
        sec = sec.wrapping_add(1);
        nsec -= NS_PER_SEC;
    }

    write(deadline_secp, sec);
    write(deadline_nsecp, nsec);
}

#[no_mangle]
pub extern "C" fn rt_sigtimedwait_timeout_expired(
    now_sec: CLong,
    now_nsec: CLong,
    deadline_sec: CLong,
    deadline_nsec: CLong,
) -> CInt {
    if now_sec > deadline_sec || (now_sec == deadline_sec && now_nsec >= deadline_nsec) {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn sigmask_to_signal_number(mask: CULong) -> CInt {
    let mut signal = 0;
    let mut bits = mask;

    while bits != 0 {
        signal += 1;
        bits >>= 1;
    }

    signal
}

fn signal_is_default_ignored(sig: CInt) -> bool {
    sig == SIGCHLD || sig == SIGURG || sig == SIGCONT
}

#[no_mangle]
pub extern "C" fn signal_pending_deliverable_result(
    delflag: CInt,
    sig: CInt,
    handler_addr: CULong,
    pending_mask: CULong,
    blocked_mask: CULong,
) -> CInt {
    if delflag == 0
        && signal_is_default_ignored(sig)
        && (handler_addr == 0 || handler_addr == SIG_IGN_HANDLER)
    {
        return 0;
    }

    ((pending_mask & blocked_mask) == 0) as CInt
}

#[no_mangle]
pub extern "C" fn signal_pending_interrupt_action_result(
    sig: CInt,
    handler_addr: CULong,
    pending_mask: CULong,
    blocked_mask: CULong,
    interrupted: CInt,
) -> CInt {
    if signal_pending_deliverable_result(0, sig, handler_addr, pending_mask, blocked_mask) == 0 {
        return 0;
    }
    if interrupted != 0 {
        return 0;
    }
    if !signal_is_default_ignored(sig) && handler_addr == 0 {
        2
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn rt_sigqueueinfo_pid_result(pid: CInt) -> CInt {
    if pid <= 0 { -ESRCH } else { 0 }
}

#[no_mangle]
pub unsafe extern "C" fn rt_sigqueueinfo_body_result(
    pid: CInt,
    sig: CInt,
    info_addr: CULong,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    do_kill_fn: Option<SyscallDoKillFn>,
) -> CLong {
    let error = rt_sigqueueinfo_pid_result(pid);
    if error != 0 {
        return error as CLong;
    }

    let Some(copy_from) = copy_from_fn else {
        return -EFAULT as CLong;
    };
    let mut info = MaybeUninit::<SigInfo>::uninit();
    if copy_from(
        info.as_mut_ptr().cast::<u8>(),
        info_addr,
        size_of::<SigInfo>(),
    ) != 0
    {
        return -EFAULT as CLong;
    }
    let Some(do_kill) = do_kill_fn else {
        return -EFAULT as CLong;
    };
    do_kill(pid, sig, info.as_ptr())
}

#[no_mangle]
pub extern "C" fn sigsuspend_sigsetsize_result(
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
) -> CInt {
    if sigsetsize > expected_sigset_size {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn sigsuspend_prepare_mask(raw_mask: CULong) -> CULong {
    raw_mask & !(SIGKILL_MASK | SIGSTOP_MASK)
}

#[no_mangle]
pub extern "C" fn sigsuspend_pending_matches(pending_mask: CULong, suspend_mask: CULong) -> CInt {
    if (pending_mask & suspend_mask) == 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn pause_body_result(
    thread: *mut c_void,
    sigmask_offset: SizeT,
    suspend_fn: Option<SyscallSigsuspendFn>,
) -> CLong {
    if thread.is_null() {
        return -(EINVAL as CLong);
    }
    let Some(suspend) = suspend_fn else {
        return -(EFAULT as CLong);
    };
    let sigmask = thread.cast::<u8>().add(sigmask_offset).cast::<c_void>();
    suspend(thread, sigmask)
}

#[no_mangle]
pub unsafe extern "C" fn rt_sigsuspend_body_result(
    thread: *mut c_void,
    set_addr: CULong,
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
    scratch_sigset: *mut c_void,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    suspend_fn: Option<SyscallSigsuspendFn>,
) -> CLong {
    let error = sigsuspend_sigsetsize_result(sigsetsize, expected_sigset_size);
    if error != 0 {
        return error as CLong;
    }
    if thread.is_null() || set_addr == 0 || scratch_sigset.is_null() {
        return -(EFAULT as CLong);
    }
    let Some(copy_from) = copy_from_fn else {
        return -(EFAULT as CLong);
    };
    if copy_from(scratch_sigset.cast::<u8>(), set_addr, expected_sigset_size) != 0 {
        return -(EFAULT as CLong);
    }
    let Some(suspend) = suspend_fn else {
        return -(EFAULT as CLong);
    };
    suspend(thread, scratch_sigset)
}

#[no_mangle]
pub extern "C" fn sigaction_sigsetsize_result(
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
) -> CInt {
    if sigsetsize != expected_sigset_size {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn do_sigaction_body_result(
    sig: CInt,
    act: *const KSigAction,
    oact: *mut KSigAction,
    sigcommon: *mut c_void,
    action_offset: SizeT,
    action_stride: SizeT,
    lock_offset: SizeT,
    lock_node: *mut c_void,
    lock_fn: Option<SyscallSigcommonLockFn>,
    unlock_fn: Option<SyscallSigcommonLockFn>,
    forward_fn: Option<SyscallSigactionForwardFn>,
) -> CInt {
    let error = sigaction_validate(sig, (!act.is_null()) as CInt);
    if error != 0 {
        return error;
    }
    if sigcommon.is_null() || lock_node.is_null() || action_stride < size_of::<KSigAction>() {
        return -EFAULT;
    }

    let Some(lock) = lock_fn else {
        return -EFAULT;
    };
    let Some(unlock) = unlock_fn else {
        return -EFAULT;
    };
    let forward = if act.is_null() {
        None
    } else {
        match forward_fn {
            Some(callback) => Some(callback),
            None => return -EFAULT,
        }
    };

    let action_index = (sig - 1) as SizeT;
    let Some(action_delta) = action_stride
        .checked_mul(action_index)
        .and_then(|delta| action_offset.checked_add(delta))
    else {
        return -EINVAL;
    };

    let sigcommon_bytes = sigcommon.cast::<u8>();
    let action = sigcommon_bytes.add(action_delta).cast::<KSigAction>();
    let lock_ptr = sigcommon_bytes.add(lock_offset).cast::<c_void>();

    lock(lock_ptr, lock_node);
    if !oact.is_null() {
        copy_nonoverlapping(action.cast::<u8>(), oact.cast::<u8>(), action_stride);
    }
    if !act.is_null() {
        copy_nonoverlapping(act.cast::<u8>(), action.cast::<u8>(), action_stride);
    }
    unlock(lock_ptr, lock_node);

    if let Some(callback) = forward {
        callback(sig, act.cast::<c_void>());
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn rt_sigaction_body_result(
    sig: CInt,
    act_addr: CULong,
    oact_addr: CULong,
    sigsetsize: SizeT,
    expected_sigset_size: SizeT,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    sigaction_fn: Option<SyscallSigactionFn>,
) -> CLong {
    let error = sigaction_sigsetsize_result(sigsetsize, expected_sigset_size);
    if error != 0 {
        return error as CLong;
    }

    let mut new_sa = MaybeUninit::<KSigAction>::uninit();
    let actp = if act_addr != 0 {
        let Some(copy_from) = copy_from_fn else {
            return -EFAULT as CLong;
        };
        let new_sap = new_sa.as_mut_ptr();
        if copy_from(
            (&mut (*new_sap).sa as *mut SigAction).cast::<u8>(),
            act_addr,
            size_of::<SigAction>(),
        ) != 0
        {
            return -EFAULT as CLong;
        }
        new_sap
    } else {
        core::ptr::null_mut()
    };

    let mut old_sa = MaybeUninit::<KSigAction>::uninit();
    let oactp = if oact_addr != 0 {
        old_sa.as_mut_ptr()
    } else {
        core::ptr::null_mut()
    };

    let Some(do_sigaction) = sigaction_fn else {
        return -EFAULT as CLong;
    };
    let rc = do_sigaction(sig, actp, oactp);
    if rc == 0 && oact_addr != 0 {
        let Some(copy_to) = copy_to_fn else {
            return -EFAULT as CLong;
        };
        if copy_to(
            oact_addr,
            (&(*old_sa.as_ptr()).sa as *const SigAction).cast::<u8>(),
            size_of::<SigAction>(),
        ) != 0
        {
            return -EFAULT as CLong;
        }
    }

    rc as CLong
}

#[no_mangle]
pub extern "C" fn sigaltstack_validate(flags: CInt, size: SizeT) -> CInt {
    if flags != 0 && flags != SS_DISABLE {
        return -EINVAL;
    }

    if flags != SS_DISABLE && size < MINSIGSTKSZ {
        return -ENOMEM;
    }

    0
}

#[no_mangle]
pub extern "C" fn sigaltstack_is_disable(flags: CInt) -> CInt {
    if flags == SS_DISABLE { 1 } else { 0 }
}

#[no_mangle]
pub unsafe extern "C" fn sigaltstack_body_result(
    thread: *mut u8,
    sigstack_offset: SizeT,
    ss_addr: CULong,
    oss_addr: CULong,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    let thread_sigstack = field_ptr::<SigStack>(thread, sigstack_offset);
    let stack_size = size_of::<SigStack>();

    if oss_addr != 0 {
        let Some(copy_to) = copy_to_fn else {
            return -EFAULT as CLong;
        };
        if copy_to(oss_addr, thread_sigstack.cast::<u8>(), stack_size) != 0 {
            return -EFAULT as CLong;
        }
    }

    if ss_addr == 0 {
        return 0;
    }

    let Some(copy_from) = copy_from_fn else {
        return -EFAULT as CLong;
    };
    let mut new_stack = MaybeUninit::<SigStack>::uninit();
    if copy_from(new_stack.as_mut_ptr().cast::<u8>(), ss_addr, stack_size) != 0 {
        return -EFAULT as CLong;
    }

    let new_stack = new_stack.assume_init();
    let error = sigaltstack_validate(new_stack.ss_flags, new_stack.ss_size);
    if error != 0 {
        return error as CLong;
    }

    if sigaltstack_is_disable(new_stack.ss_flags) != 0 {
        (*thread_sigstack).ss_sp = core::ptr::null_mut();
        (*thread_sigstack).ss_flags = SS_DISABLE;
        (*thread_sigstack).padding = 0;
        (*thread_sigstack).ss_size = 0;
    } else {
        copy_nonoverlapping(&new_stack, thread_sigstack, 1);
    }

    0
}

#[no_mangle]
pub extern "C" fn process_vm_validate_args(
    flags: CULong,
    liovcnt: CULong,
    riovcnt: CULong,
) -> CInt {
    if flags != 0 {
        return -EINVAL;
    }

    if liovcnt > IOV_MAX || riovcnt > IOV_MAX {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn process_vm_op_is_write(op: CInt) -> CInt {
    if op == PROCESS_VM_WRITE { 1 } else { 0 }
}

#[no_mangle]
pub extern "C" fn process_vm_op_is_valid(op: CInt) -> CInt {
    if op == PROCESS_VM_READ || op == PROCESS_VM_WRITE {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_rw_body_result(
    pid: CInt,
    local_iov: *const c_void,
    liovcnt: CULong,
    remote_iov: *const c_void,
    riovcnt: CULong,
    flags: CULong,
    op: CInt,
    rw_fn: Option<ProcessVmRwFn>,
) -> CLong {
    let error = process_vm_validate_args(flags, liovcnt, riovcnt);
    if error != 0 {
        return error as CLong;
    }
    if process_vm_op_is_valid(op) == 0 {
        return -(EINVAL as CLong);
    }
    let Some(rw) = rw_fn else {
        return -(EFAULT as CLong);
    };

    rw(pid, local_iov, liovcnt, remote_iov, riovcnt, flags, op) as CLong
}

#[inline(always)]
unsafe fn process_vm_iov_base(iov: *const Iovec, index: usize) -> CULong {
    read_volatile(addr_of!((*iov.add(index)).iov_base)) as CULong
}

#[inline(always)]
unsafe fn process_vm_iov_len(iov: *const Iovec, index: usize) -> SizeT {
    read_volatile(addr_of!((*iov.add(index)).iov_len))
}

#[inline(always)]
fn process_vm_iov_end(iov: *const Iovec, count: CULong) -> CULong {
    (iov as CULong).wrapping_add(count.wrapping_mul(size_of::<Iovec>() as CULong))
}

#[inline(always)]
unsafe fn process_vm_field_ptr<T>(base: *mut c_void, offset: SizeT) -> *mut T {
    (base as *mut u8).add(offset).cast::<T>()
}

#[inline(always)]
unsafe fn process_vm_read_ptr(base: *mut c_void, offset: SizeT) -> *mut c_void {
    read_volatile(process_vm_field_ptr::<*mut c_void>(base, offset))
}

#[inline(always)]
unsafe fn process_vm_read_i32(base: *mut c_void, offset: SizeT) -> CInt {
    read_volatile(process_vm_field_ptr::<CInt>(base, offset))
}

#[inline(always)]
unsafe fn process_vm_log_iov(
    log_fn: Option<ArchProcessVmRwLogFn>,
    event: CInt,
    index: CInt,
    base: CULong,
    len: CULong,
) {
    let Some(log) = log_fn else {
        return;
    };
    let mut record = MaybeUninit::<ArchProcessVmRwLogRecord>::uninit();
    let record_ptr = record.as_mut_ptr();
    write(addr_of_mut!((*record_ptr).event), event);
    write(addr_of_mut!((*record_ptr).x), index);
    write(addr_of_mut!((*record_ptr).a), base);
    write(addr_of_mut!((*record_ptr).b), len);
    log(record_ptr.cast_const());
}

#[inline(always)]
unsafe fn process_vm_log_found(
    log_fn: Option<ArchProcessVmRwLogFn>,
    pid: CInt,
    op: CInt,
    liovcnt: CULong,
    riovcnt: CULong,
) {
    let Some(log) = log_fn else {
        return;
    };
    let mut record = MaybeUninit::<ArchProcessVmRwLogRecord>::uninit();
    let record_ptr = record.as_mut_ptr();
    write(addr_of_mut!((*record_ptr).event), 3);
    write(addr_of_mut!((*record_ptr).x), pid);
    write(addr_of_mut!((*record_ptr).y), op);
    write(addr_of_mut!((*record_ptr).a), liovcnt);
    write(addr_of_mut!((*record_ptr).b), riovcnt);
    log(record_ptr.cast_const());
}

#[inline(always)]
unsafe fn process_vm_log_copy(
    log_fn: Option<ArchProcessVmRwLogFn>,
    li: CInt,
    ri: CInt,
    op: CInt,
    local_addr: CULong,
    remote_addr: CULong,
    bytes: CULong,
    psize: CULong,
    rpage_left: CULong,
) {
    let Some(log) = log_fn else {
        return;
    };
    let mut record = MaybeUninit::<ArchProcessVmRwLogRecord>::uninit();
    let record_ptr = record.as_mut_ptr();
    write(addr_of_mut!((*record_ptr).event), 4);
    write(addr_of_mut!((*record_ptr).x), li);
    write(addr_of_mut!((*record_ptr).y), ri);
    write(addr_of_mut!((*record_ptr).z), op);
    write(addr_of_mut!((*record_ptr).a), local_addr);
    write(addr_of_mut!((*record_ptr).b), remote_addr);
    write(addr_of_mut!((*record_ptr).c), bytes);
    write(addr_of_mut!((*record_ptr).d), psize);
    write(addr_of_mut!((*record_ptr).e), rpage_left);
    log(record_ptr.cast_const());
}

#[no_mangle]
pub unsafe extern "C" fn arch_process_vm_read_writev_body_result(
    pid: CInt,
    local_iov: *const Iovec,
    liovcnt: CULong,
    remote_iov: *const Iovec,
    riovcnt: CULong,
    flags: CULong,
    op: CInt,
    lthread: *mut c_void,
    find_lock_node: *mut c_void,
    update_lock_node: *mut c_void,
    offsets: *const ArchProcessVmRwOffsets,
    vm_read_lock_fn: Option<ArchProcessVmRwLockFn>,
    vm_read_unlock_fn: Option<ArchProcessVmRwLockFn>,
    lookup_range_fn: Option<ArchProcessVmRwLookupRangeFn>,
    find_process_fn: Option<ArchProcessVmRwFindProcessFn>,
    process_unlock_fn: Option<ArchProcessVmRwProcessUnlockFn>,
    update_lock_fn: Option<ArchProcessVmRwProcessLockFn>,
    update_unlock_fn: Option<ArchProcessVmRwProcessLockFn>,
    hold_vm_fn: Option<ArchProcessVmRwVmVoidFn>,
    release_vm_fn: Option<ArchProcessVmRwVmVoidFn>,
    vtop_fn: Option<ArchProcessVmRwVtopFn>,
    page_fault_fn: Option<ArchProcessVmRwFaultFn>,
    phys_to_virt_fn: Option<ArchProcessVmRwPhysToVirtFn>,
    memcpy_fn: Option<ArchProcessVmRwMemcpyFn>,
    log_fn: Option<ArchProcessVmRwLogFn>,
) -> CInt {
    let error = process_vm_validate_args(flags, liovcnt, riovcnt);
    if error != 0 {
        return error;
    }

    if lthread.is_null()
        || find_lock_node.is_null()
        || update_lock_node.is_null()
        || offsets.is_null()
    {
        return -EFAULT;
    }

    let Some(vm_read_lock) = vm_read_lock_fn else {
        return -EFAULT;
    };
    let Some(vm_read_unlock) = vm_read_unlock_fn else {
        return -EFAULT;
    };
    let Some(lookup_range) = lookup_range_fn else {
        return -EFAULT;
    };
    let Some(find_process) = find_process_fn else {
        return -EFAULT;
    };
    let Some(process_unlock) = process_unlock_fn else {
        return -EFAULT;
    };
    let Some(update_lock) = update_lock_fn else {
        return -EFAULT;
    };
    let Some(update_unlock) = update_unlock_fn else {
        return -EFAULT;
    };
    let Some(hold_vm) = hold_vm_fn else {
        return -EFAULT;
    };
    let Some(release_vm) = release_vm_fn else {
        return -EFAULT;
    };
    let Some(vtop) = vtop_fn else {
        return -EFAULT;
    };
    let Some(page_fault) = page_fault_fn else {
        return -EFAULT;
    };
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return -EFAULT;
    };
    let Some(memcpy) = memcpy_fn else {
        return -EFAULT;
    };

    let offsets = &*offsets;
    let lproc = process_vm_read_ptr(lthread, offsets.thread_proc_offset);
    let lvm = process_vm_read_ptr(lthread, offsets.thread_vm_offset);
    if lproc.is_null() || lvm.is_null() {
        return -EFAULT;
    }

    vm_read_lock(lvm);
    let mut ret = 0;
    let mut range = lookup_range(
        lvm,
        local_iov as CULong,
        process_vm_iov_end(local_iov, liovcnt),
    );
    if range.is_null() {
        ret = -EFAULT;
    } else {
        range = lookup_range(
            lvm,
            remote_iov as CULong,
            process_vm_iov_end(remote_iov, riovcnt),
        );
        if range.is_null() {
            ret = -EFAULT;
        }
    }
    vm_read_unlock(lvm);
    if ret != 0 {
        return ret;
    }

    let mut llen: SizeT = 0;
    let mut rlen: SizeT = 0;
    for li in 0..(liovcnt as usize) {
        let base = process_vm_iov_base(local_iov, li);
        let len = process_vm_iov_len(local_iov, li);
        llen = llen.wrapping_add(len);
        process_vm_log_iov(log_fn, 1, li as CInt, base, len as CULong);
    }

    for ri in 0..(riovcnt as usize) {
        let base = process_vm_iov_base(remote_iov, ri);
        let len = process_vm_iov_len(remote_iov, ri);
        rlen = rlen.wrapping_add(len);
        process_vm_log_iov(log_fn, 2, ri as CInt, base, len as CULong);
    }

    if llen != rlen {
        return -EINVAL;
    }

    let rproc = find_process(pid, find_lock_node);
    if rproc.is_null() {
        return -ESRCH;
    }

    update_lock(rproc, update_lock_node);
    let rproc_status = process_vm_read_i32(rproc, offsets.proc_status_offset);
    if rproc_status == PS_EXITED || rproc_status == PS_ZOMBIE {
        update_unlock(rproc, update_lock_node);
        process_unlock(rproc, find_lock_node);
        return -ESRCH;
    }
    let rvm = process_vm_read_ptr(rproc, offsets.proc_vm_offset);
    if rvm.is_null() {
        update_unlock(rproc, update_lock_node);
        process_unlock(rproc, find_lock_node);
        return -EFAULT;
    }
    hold_vm(rvm);
    update_unlock(rproc, update_lock_node);
    process_unlock(rproc, find_lock_node);

    let lproc_euid = process_vm_read_i32(lproc, offsets.proc_euid_offset);
    let lproc_ruid = process_vm_read_i32(lproc, offsets.proc_ruid_offset);
    let lproc_rgid = process_vm_read_i32(lproc, offsets.proc_rgid_offset);
    if lproc_euid != 0
        && (lproc_ruid != process_vm_read_i32(rproc, offsets.proc_ruid_offset)
            || lproc_ruid != process_vm_read_i32(rproc, offsets.proc_euid_offset)
            || lproc_ruid != process_vm_read_i32(rproc, offsets.proc_suid_offset)
            || lproc_rgid != process_vm_read_i32(rproc, offsets.proc_rgid_offset)
            || lproc_rgid != process_vm_read_i32(rproc, offsets.proc_egid_offset)
            || lproc_rgid != process_vm_read_i32(rproc, offsets.proc_sgid_offset))
    {
        release_vm(rvm);
        return -EPERM;
    }

    process_vm_log_found(log_fn, pid, op, liovcnt, riovcnt);

    let mut pli = usize::MAX;
    let mut pri = usize::MAX;
    let mut li = 0usize;
    let mut ri = 0usize;
    let mut loff: SizeT = 0;
    let mut roff: SizeT = 0;
    let mut copied: SizeT = 0;

    while copied < llen {
        let mut faulted = false;

        if pli != li {
            vm_read_lock(lvm);
            let local_base = process_vm_iov_base(local_iov, li);
            let local_len = process_vm_iov_len(local_iov, li);
            range = lookup_range(lvm, local_base, local_base.wrapping_add(1));
            if range.is_null() {
                ret = -EFAULT;
            } else {
                range = lookup_range(
                    lvm,
                    local_base,
                    local_base.wrapping_add(local_len as CULong),
                );
                if range.is_null() {
                    ret = -EINVAL;
                } else {
                    let range_flag = read_volatile(process_vm_field_ptr::<CULong>(
                        range,
                        offsets.vm_range_flag_offset,
                    ));
                    let required = if op == PROCESS_VM_READ {
                        VR_PROT_WRITE
                    } else {
                        VR_PROT_READ
                    };
                    ret = if (range_flag & required) == 0 {
                        -EFAULT
                    } else {
                        0
                    };
                }
            }
            vm_read_unlock(lvm);
            if ret != 0 {
                break;
            }
            pli = li;
        }

        if pri != ri {
            vm_read_lock(rvm);
            let remote_check_index = li;
            let remote_base = process_vm_iov_base(remote_iov, remote_check_index);
            let remote_len = process_vm_iov_len(remote_iov, remote_check_index);
            range = lookup_range(rvm, remote_base, remote_base.wrapping_add(1));
            if range.is_null() {
                ret = -EFAULT;
            } else {
                range = lookup_range(
                    rvm,
                    remote_base,
                    remote_base.wrapping_add(remote_len as CULong),
                );
                if range.is_null() {
                    ret = -EINVAL;
                } else {
                    let range_flag = read_volatile(process_vm_field_ptr::<CULong>(
                        range,
                        offsets.vm_range_flag_offset,
                    ));
                    let required = if op == PROCESS_VM_READ {
                        VR_PROT_READ
                    } else {
                        VR_PROT_WRITE
                    };
                    ret = if (range_flag & required) == 0 {
                        -EFAULT
                    } else {
                        0
                    };
                }
            }
            vm_read_unlock(rvm);
            if ret != 0 {
                break;
            }
            pri = ri;
        }

        let local_base = process_vm_iov_base(local_iov, li);
        let local_len = process_vm_iov_len(local_iov, li);
        let remote_base = process_vm_iov_base(remote_iov, ri);
        let remote_len = process_vm_iov_len(remote_iov, ri);
        let mut to_copy = local_len.wrapping_sub(loff);
        let remote_left = remote_len.wrapping_sub(roff);
        if remote_left < to_copy {
            to_copy = remote_left;
        }

        let mut rphys: CULong = 0;
        let mut psize: CULong = 0;
        let remote_addr = remote_base.wrapping_add(roff as CULong);
        loop {
            let aspace = process_vm_read_ptr(rvm, offsets.process_vm_address_space_offset);
            let page_table = if aspace.is_null() {
                null_mut()
            } else {
                process_vm_read_ptr(aspace, offsets.address_space_page_table_offset)
            };
            ret = vtop(page_table, remote_addr, &mut rphys, &mut psize);
            if ret == 0 {
                break;
            }

            if faulted {
                ret = -EFAULT;
                break;
            }

            let mut addr = remote_addr & PAGE_MASK;
            let fault_end = remote_addr.wrapping_add(to_copy as CULong);
            while addr < fault_end {
                ret = page_fault(rvm, addr, PF_POPULATE | PF_WRITE | PF_USER);
                if ret != 0 {
                    ret = -EFAULT;
                    break;
                }
                addr = addr.wrapping_add(PAGE_SIZE);
            }
            if ret != 0 {
                break;
            }

            faulted = true;
        }
        if ret != 0 {
            break;
        }

        let rpage_left =
            ((remote_addr.wrapping_add(psize)) & !(psize - 1)).wrapping_sub(remote_addr);
        if rpage_left < to_copy as CULong {
            to_copy = rpage_left as SizeT;
        }

        let rva = phys_to_virt(rphys);
        let local_addr = local_base.wrapping_add(loff as CULong);
        if op == PROCESS_VM_READ {
            memcpy(local_addr as *mut c_void, rva as *const c_void, to_copy);
        } else {
            memcpy(rva, local_addr as *const c_void, to_copy);
        }

        copied = copied.wrapping_add(to_copy);
        process_vm_log_copy(
            log_fn,
            li as CInt,
            ri as CInt,
            op,
            local_addr,
            remote_addr,
            to_copy as CULong,
            psize,
            rpage_left,
        );

        loff = loff.wrapping_add(to_copy);
        roff = roff.wrapping_add(to_copy);

        if loff == local_len {
            li = li.wrapping_add(1);
            loff = 0;
        }

        if roff == remote_len {
            ri = ri.wrapping_add(1);
            roff = 0;
        }
    }

    if ret == 0 {
        release_vm(rvm);
        return copied as CInt;
    }

    release_vm(rvm);
    ret
}

#[no_mangle]
pub unsafe extern "C" fn prctl_body_result(
    option: CInt,
    arg2: CULong,
    arg3: CULong,
    arg4: CULong,
    arg5: CULong,
    proc: *mut c_void,
    thp_disable_offset: SizeT,
    syscall_nr: CInt,
    ctx: *mut c_void,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    if option == PR_SET_THP_DISABLE {
        if arg3 != 0 || arg4 != 0 || arg5 != 0 {
            return -(EINVAL as CLong);
        }
        if proc.is_null() {
            return -(EFAULT as CLong);
        }
        *field_ptr::<CInt>(proc.cast::<u8>(), thp_disable_offset) = arg2 as CInt;
        return 0;
    }

    if option == PR_GET_THP_DISABLE {
        if arg2 != 0 || arg3 != 0 || arg4 != 0 || arg5 != 0 {
            return -(EINVAL as CLong);
        }
        if proc.is_null() {
            return -(EFAULT as CLong);
        }
        return *field_ptr::<CInt>(proc.cast::<u8>(), thp_disable_offset) as CLong;
    }

    let Some(forward) = forward_fn else {
        return -(EFAULT as CLong);
    };
    forward(syscall_nr, ctx)
}

#[no_mangle]
pub extern "C" fn arch_prctl_type_result(code: CULong, typep: *mut CInt) -> CInt {
    let register_type = if code == ARCH_SET_FS || code == ARCH_GET_FS {
        IHK_ASR_X86_FS
    } else if code == ARCH_GET_GS {
        IHK_ASR_X86_GS
    } else if code == ARCH_SET_GS {
        return -ENOTSUPP;
    } else {
        return -EINVAL;
    };

    unsafe {
        if !typep.is_null() {
            write(typep, register_type);
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_prctl_body_result(
    code: CULong,
    address: CULong,
    thread: *mut c_void,
    tlsblock_base_offset: SizeT,
    get_cpu_fn: Option<SyscallGetCpuFn>,
    set_register_fn: Option<ArchPrctlSetRegisterFn>,
    get_register_fn: Option<ArchPrctlGetRegisterFn>,
    log_fn: Option<ArchPrctlLogFn>,
) -> CLong {
    let mut register_type = 0;
    let error = arch_prctl_type_result(code, &mut register_type);
    if error != 0 {
        return error as CLong;
    }

    if code == ARCH_SET_FS {
        if thread.is_null() {
            return -(EFAULT as CLong);
        }
        *field_ptr::<CULong>(thread.cast::<u8>(), tlsblock_base_offset) = address;
        if let Some(log) = log_fn {
            let cpu = get_cpu_fn.map_or(-1, |get_cpu| get_cpu());
            log(ARCH_SET_FS as CInt, cpu, address);
        }
        let Some(set_register) = set_register_fn else {
            return -(EFAULT as CLong);
        };
        return set_register(register_type, address) as CLong;
    }

    if code == ARCH_GET_FS || code == ARCH_GET_GS {
        let Some(get_register) = get_register_fn else {
            return -(EFAULT as CLong);
        };
        return get_register(register_type, address as *mut CULong) as CLong;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_clone_body_result(
    proc: *mut c_void,
    coredump_lock_offset: SizeT,
    lock_node: *mut c_void,
    clone_flags: CInt,
    newsp: CULong,
    parent_tidptr: CULong,
    child_tidptr: CULong,
    tls: CULong,
    pc: CULong,
    sp: CULong,
    lock_fn: Option<ArchCloneLockFn>,
    unlock_fn: Option<ArchCloneLockFn>,
    fork_fn: Option<ArchDoForkFn>,
) -> CULong {
    if proc.is_null() {
        return (-(EFAULT as CLong)) as CULong;
    }
    let Some(lock) = lock_fn else {
        return (-(EFAULT as CLong)) as CULong;
    };
    let Some(unlock) = unlock_fn else {
        return (-(EFAULT as CLong)) as CULong;
    };
    let Some(fork) = fork_fn else {
        return (-(EFAULT as CLong)) as CULong;
    };

    let coredump_lock = proc.cast::<u8>().add(coredump_lock_offset).cast::<c_void>();
    lock(coredump_lock, lock_node);
    let ret = fork(clone_flags, newsp, parent_tidptr, child_tidptr, tls, pc, sp);
    unlock(coredump_lock, lock_node);
    ret
}

#[no_mangle]
pub unsafe extern "C" fn arch_fork_body_result(
    pc: CULong,
    sp: CULong,
    fork_fn: Option<ArchDoForkFn>,
) -> CULong {
    let Some(fork) = fork_fn else {
        return (-(EFAULT as CLong)) as CULong;
    };
    fork(SIGCHLD, 0, 0, 0, 0, pc, sp)
}

#[no_mangle]
pub unsafe extern "C" fn arch_vfork_body_result(
    pc: CULong,
    sp: CULong,
    fork_fn: Option<ArchDoForkFn>,
) -> CULong {
    let Some(fork) = fork_fn else {
        return (-(EFAULT as CLong)) as CULong;
    };
    fork(CLONE_VFORK | SIGCHLD, 0, 0, 0, 0, pc, sp)
}

#[repr(C)]
struct RtSigreturnFrame {
    flags: CULong,
    link: *mut c_void,
    sigstack: SigStack,
    regs: [CULong; 23],
    fpregs: *mut c_void,
    reserve: [CULong; 8],
    sigrc: CULong,
    sigmask: CULong,
    num: CInt,
    restart: CInt,
    ss: CULong,
    info: SigInfo,
}

const RTSIG_REG_R8: usize = 0;
const RTSIG_REG_R9: usize = 1;
const RTSIG_REG_R10: usize = 2;
const RTSIG_REG_R11: usize = 3;
const RTSIG_REG_R12: usize = 4;
const RTSIG_REG_R13: usize = 5;
const RTSIG_REG_R14: usize = 6;
const RTSIG_REG_R15: usize = 7;
const RTSIG_REG_RDI: usize = 8;
const RTSIG_REG_RSI: usize = 9;
const RTSIG_REG_RBP: usize = 10;
const RTSIG_REG_RBX: usize = 11;
const RTSIG_REG_RDX: usize = 12;
const RTSIG_REG_RAX: usize = 13;
const RTSIG_REG_RCX: usize = 14;
const RTSIG_REG_RSP: usize = 15;
const RTSIG_REG_RIP: usize = 16;
const RTSIG_REG_RFLAGS: usize = 17;
const RTSIG_REG_ERROR: usize = 19;
const RTSIG_REG_OLDMASK: usize = 21;

unsafe fn rt_sigreturn_zero_siginfo(info: *mut SigInfo) {
    let dst = info.cast::<u8>();
    let mut offset = 0usize;

    while offset < size_of::<SigInfo>() {
        write_volatile(dst.add(offset), 0);
        offset += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_rt_sigreturn_body_result(
    thread: *mut u8,
    regs: *mut X86UserContext,
    sigmask_offset: SizeT,
    sigstack_offset: SizeT,
    sigstack_size: SizeT,
    frame_size: SizeT,
    xsave_size: CInt,
    nowait_flag: CULong,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    syscall_fn: Option<SyscallForwardContextFn>,
    set_signal_fn: Option<ArchRtSigreturnSetSignalFn>,
    check_need_resched_fn: Option<PtraceVoidFn>,
    check_signal_fn: Option<ArchRtSigreturnCheckSignalFn>,
    alloc_fn: Option<ArchPtraceAllocFn>,
    free_fn: Option<ArchRtSigreturnFreeFn>,
    xrstor_fn: Option<ArchRtSigreturnXrstorFn>,
) -> CLong {
    if thread.is_null() || regs.is_null() {
        return -(EFAULT as CLong);
    }
    if frame_size != size_of::<RtSigreturnFrame>() || sigstack_size != size_of::<SigStack>() {
        return -(EFAULT as CLong);
    }

    let Some(copy_from) = copy_from_fn else {
        return -(EFAULT as CLong);
    };

    let sigsp = (*regs).gpr.rsp as *const RtSigreturnFrame;
    if sigsp.is_null() {
        return -(EFAULT as CLong);
    }

    let mut frame_storage = MaybeUninit::<RtSigreturnFrame>::uninit();
    if copy_from(
        frame_storage.as_mut_ptr().cast::<u8>(),
        sigsp as CULong,
        frame_size,
    ) != 0
    {
        return -(EFAULT as CLong);
    }
    let frame = &*frame_storage.as_ptr();

    let gpr = &mut (*regs).gpr;
    gpr.r15 = frame.regs[RTSIG_REG_R15];
    gpr.r14 = frame.regs[RTSIG_REG_R14];
    gpr.r13 = frame.regs[RTSIG_REG_R13];
    gpr.r12 = frame.regs[RTSIG_REG_R12];
    gpr.rbp = frame.regs[RTSIG_REG_RBP];
    gpr.rbx = frame.regs[RTSIG_REG_RBX];
    gpr.r11 = frame.regs[RTSIG_REG_R11];
    gpr.r10 = frame.regs[RTSIG_REG_R10];
    gpr.r9 = frame.regs[RTSIG_REG_R9];
    gpr.r8 = frame.regs[RTSIG_REG_R8];
    gpr.rax = frame.regs[RTSIG_REG_RAX];
    gpr.rcx = frame.regs[RTSIG_REG_RCX];
    gpr.rdx = frame.regs[RTSIG_REG_RDX];
    gpr.rsi = frame.regs[RTSIG_REG_RSI];
    gpr.rdi = frame.regs[RTSIG_REG_RDI];
    gpr.orig_rax = frame.regs[RTSIG_REG_ERROR];
    gpr.rip = frame.regs[RTSIG_REG_RIP];
    gpr.rflags = frame.regs[RTSIG_REG_RFLAGS];
    gpr.rsp = frame.regs[RTSIG_REG_RSP];

    *thread.add(sigmask_offset).cast::<CULong>() = frame.regs[RTSIG_REG_OLDMASK];
    let sigstack_src = (&frame.sigstack as *const SigStack).cast::<u8>();
    let sigstack_dst = thread.add(sigstack_offset);
    let mut sigstack_byte = 0usize;
    while sigstack_byte < sigstack_size {
        write_volatile(
            sigstack_dst.add(sigstack_byte),
            read_volatile(sigstack_src.add(sigstack_byte)),
        );
        sigstack_byte += 1;
    }

    if (*sigsp).restart != 0 {
        let Some(call_syscall) = syscall_fn else {
            return -(EFAULT as CLong);
        };
        return call_syscall((*sigsp).num, regs.cast::<c_void>());
    }

    if ((*regs).gpr.rflags & RFLAGS_TF) != 0 {
        let Some(set_signal) = set_signal_fn else {
            return -(EFAULT as CLong);
        };
        let Some(check_need_resched) = check_need_resched_fn else {
            return -(EFAULT as CLong);
        };
        let Some(check_signal) = check_signal_fn else {
            return -(EFAULT as CLong);
        };
        let mut info_storage = MaybeUninit::<SigInfo>::uninit();
        let info = info_storage.as_mut_ptr();

        (*regs).gpr.rax = (*sigsp).sigrc;
        (*regs).gpr.rflags &= !RFLAGS_TF;
        rt_sigreturn_zero_siginfo(info);
        (*info).si_code = TRAP_TRACE;
        set_signal(SIGTRAP, regs.cast::<c_void>(), info as *const SigInfo);
        check_need_resched();
        check_signal(0, regs.cast::<c_void>(), -1);
    }

    if !frame.fpregs.is_null() && xsave_size != 0 {
        let Some(alloc) = alloc_fn else {
            return -(EFAULT as CLong);
        };
        let Some(free) = free_fn else {
            return -(EFAULT as CLong);
        };
        let Some(xrstor) = xrstor_fn else {
            return -(EFAULT as CLong);
        };

        let fpregs = alloc((xsave_size as SizeT).wrapping_add(64), nowait_flag);
        if !fpregs.is_null() {
            let aligned = (((fpregs as usize) + 63) & !63usize) as *mut c_void;

            if copy_from(
                aligned.cast::<u8>(),
                frame.fpregs as CULong,
                xsave_size as SizeT,
            ) != 0
            {
                return -(EFAULT as CLong);
            }
            xrstor(aligned);
            free(fpregs);
        }
    }

    (*sigsp).sigrc as CLong
}

#[no_mangle]
pub unsafe extern "C" fn arch_time_body_result(
    now: CLong,
    tloc_addr: CULong,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    if tloc_addr != 0 {
        let Some(copy_to) = copy_to_fn else {
            return -(EFAULT as CLong);
        };
        if copy_to(
            tloc_addr,
            (&now as *const CLong).cast::<u8>(),
            size_of::<CLong>(),
        ) != 0
        {
            return -(EFAULT as CLong);
        }
    }

    now
}

#[no_mangle]
pub unsafe extern "C" fn arch_shmget_body_result(
    key: CLong,
    size: SizeT,
    shmflg0: CInt,
    default_huge_shift_fn: Option<ArchShmgetDefaultHugeShiftFn>,
    do_shmget_fn: Option<ArchDoShmgetFn>,
    log_fn: Option<ArchShmgetLogFn>,
) -> CLong {
    if let Some(log) = log_fn {
        log(ARCH_SHMGET_LOG_ENTER, key, size, shmflg0, 0, -EINVAL);
    }

    let mut shmflg = shmflg0;
    let mut shmid = -EINVAL;

    if (shmflg & SHM_HUGETLB) != 0 {
        let hugeshift = shmflg & (0x3f << SHM_HUGE_SHIFT);

        if hugeshift == 0 {
            let Some(default_huge_shift) = default_huge_shift_fn else {
                let error = -EFAULT;
                if let Some(log) = log_fn {
                    log(ARCH_SHMGET_LOG_EXIT, key, size, shmflg0, error, shmid);
                }
                return error as CLong;
            };
            shmflg |= default_huge_shift() << MAP_HUGE_SHIFT;
        } else if hugeshift != SHM_HUGE_2MB && hugeshift != SHM_HUGE_1GB {
            let error = -EINVAL;
            if let Some(log) = log_fn {
                log(ARCH_SHMGET_LOG_EXIT, key, size, shmflg0, error, shmid);
            }
            return error as CLong;
        }
    }

    let Some(do_shmget) = do_shmget_fn else {
        let error = -EFAULT;
        if let Some(log) = log_fn {
            log(ARCH_SHMGET_LOG_EXIT, key, size, shmflg0, error, shmid);
        }
        return error as CLong;
    };

    shmid = do_shmget(key, size, shmflg);
    if let Some(log) = log_fn {
        log(ARCH_SHMGET_LOG_EXIT, key, size, shmflg0, 0, shmid);
    }
    shmid as CLong
}

#[no_mangle]
pub unsafe extern "C" fn arch_mmap_body_result(
    addr0: CULong,
    len0_arg: SizeT,
    prot: CInt,
    flags0: CInt,
    fd: CInt,
    off0: CLong,
    user_start: CULong,
    user_end: CULong,
    supported_flags: CInt,
    ignored_flags: CInt,
    error_flags: CInt,
    default_huge_shift_fn: Option<ArchMmapDefaultHugeShiftFn>,
    overmap_fn: Option<ArchMmapOvermapFn>,
    do_mmap_fn: Option<ArchDoMmapFn>,
    log_fn: Option<ArchMmapLogFn>,
) -> CLong {
    let mut len0 = len0_arg;
    let mut flags = flags0;
    let mut pgsize = PAGE_SIZE as SizeT;
    let mut addr = addr0;
    let mut result_addr = 0;

    if let Some(log) = log_fn {
        log(
            ARCH_MMAP_LOG_ENTER,
            addr0,
            len0,
            prot,
            flags0,
            fd,
            off0,
            0,
            result_addr,
            0,
        );
    }

    if (flags & MAP_HUGETLB) != 0 {
        if (flags & MAP_ANONYMOUS) == 0 {
            let error = -EINVAL;
            if let Some(log) = log_fn {
                log(
                    ARCH_MMAP_LOG_EXIT,
                    addr0,
                    len0,
                    prot,
                    flags0,
                    fd,
                    off0,
                    error,
                    result_addr,
                    0,
                );
            }
            return error as CLong;
        }

        let hugeshift = flags & MAP_HUGE_MASK;
        if hugeshift == 0 {
            let Some(default_huge_shift) = default_huge_shift_fn else {
                let error = -EFAULT;
                if let Some(log) = log_fn {
                    log(
                        ARCH_MMAP_LOG_EXIT,
                        addr0,
                        len0,
                        prot,
                        flags0,
                        fd,
                        off0,
                        error,
                        result_addr,
                        0,
                    );
                }
                return error as CLong;
            };
            flags |= default_huge_shift() << MAP_HUGE_SHIFT;
        } else if hugeshift != MAP_HUGE_2MB && hugeshift != MAP_HUGE_1GB {
            let error = -EINVAL;
            if let Some(log) = log_fn {
                log(
                    ARCH_MMAP_LOG_UNSUPPORTED_PGSIZE,
                    addr0,
                    len0,
                    prot,
                    flags0,
                    fd,
                    off0,
                    error,
                    result_addr,
                    0,
                );
                log(
                    ARCH_MMAP_LOG_EXIT,
                    addr0,
                    len0,
                    prot,
                    flags0,
                    fd,
                    off0,
                    error,
                    result_addr,
                    0,
                );
            }
            return error as CLong;
        }

        pgsize = 1usize << ((flags >> MAP_HUGE_SHIFT) & 0x3f) as usize;
        len0 = len0.wrapping_add(pgsize - 1) & !(pgsize - 1);

        let Some(overmap) = overmap_fn else {
            let error = -EFAULT;
            if let Some(log) = log_fn {
                log(
                    ARCH_MMAP_LOG_EXIT,
                    addr0,
                    len0,
                    prot,
                    flags0,
                    fd,
                    off0,
                    error,
                    result_addr,
                    0,
                );
            }
            return error as CLong;
        };
        if overmap(len0, (flags >> MAP_HUGE_SHIFT) & 0x3f) != 0 {
            let error = -ENOMEM;
            if let Some(log) = log_fn {
                log(
                    ARCH_MMAP_LOG_EXIT,
                    addr0,
                    len0,
                    prot,
                    flags0,
                    fd,
                    off0,
                    error,
                    result_addr,
                    0,
                );
            }
            return error as CLong;
        }
    }

    let valid_dummy_addr = user_start.wrapping_add(PTL3_SIZE - 1) & !(PTL3_SIZE - 1);
    let len = len0.wrapping_add(pgsize - 1) & !(pgsize - 1);
    loop {
        let invalid_args = (addr & (pgsize as CULong - 1)) != 0
            || len == 0
            || (flags & (MAP_SHARED | MAP_PRIVATE)) == 0
            || ((flags & MAP_SHARED) != 0 && (flags & MAP_PRIVATE) != 0)
            || (off0 as CULong & (pgsize as CULong - 1)) != 0;
        if invalid_args {
            if (flags & MAP_FIXED) == 0 && addr != valid_dummy_addr {
                addr = valid_dummy_addr;
                continue;
            }
            let error = -EINVAL;
            if let Some(log) = log_fn {
                log(
                    ARCH_MMAP_LOG_INVALID,
                    addr0,
                    len0,
                    prot,
                    flags0,
                    fd,
                    off0,
                    error,
                    result_addr,
                    0,
                );
                log(
                    ARCH_MMAP_LOG_EXIT,
                    addr0,
                    len0,
                    prot,
                    flags0,
                    fd,
                    off0,
                    error,
                    result_addr,
                    0,
                );
            }
            return error as CLong;
        }

        let out_of_range = addr < user_start
            || user_end <= addr
            || len as CULong > user_end.wrapping_sub(user_start);
        if out_of_range {
            if (flags & MAP_FIXED) == 0 && addr != valid_dummy_addr {
                addr = valid_dummy_addr;
                continue;
            }
            let error = -ENOMEM;
            if let Some(log) = log_fn {
                log(
                    ARCH_MMAP_LOG_NOMEM,
                    addr0,
                    len0,
                    prot,
                    flags0,
                    fd,
                    off0,
                    error,
                    result_addr,
                    0,
                );
                log(
                    ARCH_MMAP_LOG_EXIT,
                    addr0,
                    len0,
                    prot,
                    flags0,
                    fd,
                    off0,
                    error,
                    result_addr,
                    0,
                );
            }
            return error as CLong;
        }
        break;
    }

    let unknown_flags = flags & !(supported_flags | ignored_flags);
    if (flags & error_flags) != 0 || unknown_flags != 0 {
        let error = -EINVAL;
        if let Some(log) = log_fn {
            log(
                ARCH_MMAP_LOG_UNKNOWN_FLAGS,
                addr0,
                len0,
                prot,
                flags0,
                fd,
                off0,
                error,
                result_addr,
                unknown_flags,
            );
            log(
                ARCH_MMAP_LOG_EXIT,
                addr0,
                len0,
                prot,
                flags0,
                fd,
                off0,
                error,
                result_addr,
                0,
            );
        }
        return error as CLong;
    }

    let Some(do_mmap) = do_mmap_fn else {
        let error = -EFAULT;
        if let Some(log) = log_fn {
            log(
                ARCH_MMAP_LOG_EXIT,
                addr0,
                len0,
                prot,
                flags0,
                fd,
                off0,
                error,
                result_addr,
                0,
            );
        }
        return error as CLong;
    };

    result_addr = do_mmap(addr, len, prot, flags, fd, off0, 0, core::ptr::null_mut()) as CULong;
    if let Some(log) = log_fn {
        log(
            ARCH_MMAP_LOG_EXIT,
            addr0,
            len0,
            prot,
            flags0,
            fd,
            off0,
            0,
            result_addr,
            0,
        );
    }
    result_addr as CLong
}

#[repr(C)]
pub struct ArchVdso {
    busy: CLong,
    vdso_npages: CInt,
    vvar_is_global: i8,
    hpet_is_global: i8,
    pvti_is_global: i8,
    padding: i8,
    vdso_physlist: [CLong; 2],
    vvar_virt: *mut c_void,
    vvar_phys: CLong,
    hpet_virt: *mut c_void,
    hpet_phys: CLong,
    pvti_virt: *mut c_void,
    pvti_phys: CLong,
    vgtod_virt: *mut c_void,
}

type ArchVdsoGetInfoFn = unsafe extern "C" fn() -> CInt;
type ArchVdsoMapGlobalFn = unsafe extern "C" fn() -> CInt;
type ArchVdsoSetupLogFn = unsafe extern "C" fn(CInt, CInt);
type ArchVdsoAddRangeFn =
    unsafe extern "C" fn(*mut ProcessVm, CULong, CULong, CULong, *mut *mut VmRange) -> CInt;
type ArchVdsoSetRangeFn = unsafe extern "C" fn(
    *mut c_void,
    *mut ProcessVm,
    CULong,
    CULong,
    CULong,
    CULong,
    *mut VmRange,
) -> CInt;
type ArchVdsoMapLogFn =
    unsafe extern "C" fn(CInt, CInt, *mut ProcessVm, CULong, CULong, CULong, CULong, CInt);

const ARCH_VDSO_SETUP_LOG_GET_INFO_FAILED: CInt = 1;
const ARCH_VDSO_SETUP_LOG_LOCAL_GETTIME_DISABLED: CInt = 2;
const ARCH_VDSO_SETUP_LOG_VDSO_DISABLED: CInt = 3;
const ARCH_VDSO_SETUP_LOG_MAP_GLOBAL_FAILED: CInt = 4;
const ARCH_VDSO_MAP_LOG_NOT_AVAILABLE: CInt = 1;
const ARCH_VDSO_MAP_LOG_ADD_VDSO_FAILED: CInt = 2;
const ARCH_VDSO_MAP_LOG_MAPPED: CInt = 3;
const ARCH_VDSO_MAP_LOG_SET_RANGE_FAILED: CInt = 4;
const ARCH_VDSO_MAP_LOG_ADD_VVAR_FAILED: CInt = 5;

fn arch_vdso_container(vdso: &ArchVdso) -> (SizeT, isize) {
    let mut start: isize = 0;
    let mut end = (vdso.vdso_npages as isize).wrapping_mul(PAGE_SIZE as isize);

    if !vdso.vvar_virt.is_null() && vdso.vvar_is_global == 0 {
        let s = vdso.vvar_virt as isize;
        let e = s.wrapping_add(PAGE_SIZE as isize);
        if s < start {
            start = s;
        }
        if end < e {
            end = e;
        }
    }
    if !vdso.hpet_virt.is_null() && vdso.hpet_is_global == 0 {
        let s = vdso.hpet_virt as isize;
        let e = s.wrapping_add(PAGE_SIZE as isize);
        if s < start {
            start = s;
        }
        if end < e {
            end = e;
        }
    }
    if !vdso.pvti_virt.is_null() && vdso.pvti_is_global == 0 {
        let s = vdso.pvti_virt as isize;
        let e = s.wrapping_add(PAGE_SIZE as isize);
        if s < start {
            start = s;
        }
        if end < e {
            end = e;
        }
    }

    let vdso_offset = if start < 0 { start.wrapping_neg() } else { 0 };
    (end.wrapping_sub(start) as SizeT, vdso_offset)
}

fn arch_vdso_addr_add(base: CULong, offset: isize) -> CULong {
    base.wrapping_add(offset as CULong)
}

fn arch_vdso_maxprot(vrflag: CULong) -> CULong {
    (vrflag & VR_PROT_MASK) << 4
}

#[no_mangle]
pub unsafe extern "C" fn arch_vdso_calc_container_size_result(
    vdso: *const ArchVdso,
    container_size: *mut SizeT,
    vdso_offset: *mut isize,
) -> CInt {
    if vdso.is_null() || container_size.is_null() || vdso_offset.is_null() {
        return -EINVAL;
    }

    let (size, offset) = arch_vdso_container(&*vdso);
    *container_size = size;
    *vdso_offset = offset;
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_setup_vdso_body_result(
    vdso: *mut ArchVdso,
    container_size: *mut SizeT,
    vdso_offset: *mut isize,
    gettime_local_supportp: *mut CInt,
    tod_do_local: *mut c_void,
    get_info_fn: Option<ArchVdsoGetInfoFn>,
    map_global_fn: Option<ArchVdsoMapGlobalFn>,
    log_fn: Option<ArchVdsoSetupLogFn>,
) -> CInt {
    if vdso.is_null()
        || container_size.is_null()
        || vdso_offset.is_null()
        || gettime_local_supportp.is_null()
        || tod_do_local.is_null()
    {
        return -EFAULT;
    }

    let Some(get_info) = get_info_fn else {
        return -EFAULT;
    };

    let mut error = get_info();
    if error != 0 {
        if let Some(log) = log_fn {
            log(ARCH_VDSO_SETUP_LOG_GET_INFO_FAILED, error);
        }
        return error;
    }

    if *gettime_local_supportp != 0 && (*vdso).vgtod_virt.is_null() {
        if let Some(log) = log_fn {
            log(ARCH_VDSO_SETUP_LOG_LOCAL_GETTIME_DISABLED, 0);
        }
        *gettime_local_supportp = 0;
        *(tod_do_local.cast::<i8>()) = 0;
    }
    if (*vdso).vgtod_virt.is_null() && (*vdso).vdso_npages > 0 {
        if let Some(log) = log_fn {
            log(ARCH_VDSO_SETUP_LOG_VDSO_DISABLED, 0);
        }
        (*vdso).vdso_npages = 0;
        *container_size = 0;
        *vdso_offset = 0;
    }

    if (*vdso).vdso_npages <= 0 {
        return 0;
    }

    let Some(map_global) = map_global_fn else {
        return -EFAULT;
    };
    error = map_global();
    if error != 0 {
        if let Some(log) = log_fn {
            log(ARCH_VDSO_SETUP_LOG_MAP_GLOBAL_FAILED, error);
        }
        return error;
    }

    let (size, offset) = arch_vdso_container(&*vdso);
    *container_size = size;
    *vdso_offset = offset;

    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_map_vdso_body_result(
    vm: *mut ProcessVm,
    page_table: *mut c_void,
    vdso: *const ArchVdso,
    container_size: SizeT,
    vdso_offset: isize,
    add_range_fn: Option<ArchVdsoAddRangeFn>,
    set_range_fn: Option<ArchVdsoSetRangeFn>,
    log_fn: Option<ArchVdsoMapLogFn>,
) -> CInt {
    if container_size == 0 {
        if let Some(log) = log_fn {
            log(ARCH_VDSO_MAP_LOG_NOT_AVAILABLE, 0, vm, 0, 0, 0, 0, 0);
        }
        return 0;
    }
    if vm.is_null() || vdso.is_null() {
        return -EFAULT;
    }

    let Some(add_range) = add_range_fn else {
        return -EFAULT;
    };
    let Some(set_range) = set_range_fn else {
        return -EFAULT;
    };
    let vdso_ref = &*vdso;
    let container = (*vm).region.map_end;
    (*vm).region.map_end = (*vm).region.map_end.wrapping_add(container_size as CULong);

    let vdso_addr = arch_vdso_addr_add(container, vdso_offset);
    let vdso_page_bytes = (vdso_ref.vdso_npages as CULong).wrapping_mul(PAGE_SIZE);
    let vdso_end = vdso_addr.wrapping_add(vdso_page_bytes);
    let mut vrflags = VR_REMOTE | VR_PROT_READ | VR_PROT_EXEC;
    vrflags |= arch_vdso_maxprot(vrflags);
    let mut range: *mut VmRange = null_mut();

    let mut error = add_range(vm, vdso_addr, vdso_end, vrflags, &mut range);
    if error != 0 {
        if let Some(log) = log_fn {
            log(ARCH_VDSO_MAP_LOG_ADD_VDSO_FAILED, error, vm, 0, 0, 0, 0, 0);
        }
        return error;
    }
    (*vm).vdso_addr = vdso_addr as *mut c_void;
    if let Some(log) = log_fn {
        log(
            ARCH_VDSO_MAP_LOG_MAPPED,
            0,
            vm,
            container,
            vdso_addr,
            vdso_end,
            container_size as CULong,
            vdso_ref.vdso_npages,
        );
    }

    let attr = PTATTR_ACTIVE | PTATTR_USER;
    for i in 0..vdso_ref.vdso_npages {
        let s = vdso_addr.wrapping_add((i as CULong).wrapping_mul(PAGE_SIZE));
        let e = s.wrapping_add(PAGE_SIZE);
        error = set_range(
            page_table,
            vm,
            s,
            e,
            *vdso_ref.vdso_physlist.as_ptr().add(i as usize) as CULong,
            attr,
            range,
        );
        if error != 0 {
            if let Some(log) = log_fn {
                log(ARCH_VDSO_MAP_LOG_SET_RANGE_FAILED, error, vm, 0, 0, 0, 0, 0);
            }
            return error;
        }
    }

    if container_size > vdso_page_bytes as SizeT {
        let (vvar_start, vvar_end) = if vdso_offset != 0 {
            (container, container.wrapping_add(vdso_offset as CULong))
        } else {
            (
                container.wrapping_add(vdso_page_bytes),
                container.wrapping_add(container_size as CULong),
            )
        };
        vrflags = VR_REMOTE | VR_PROT_READ;
        vrflags |= arch_vdso_maxprot(vrflags);
        error = add_range(vm, vvar_start, vvar_end, vrflags, &mut range);
        if error != 0 {
            if let Some(log) = log_fn {
                log(ARCH_VDSO_MAP_LOG_ADD_VVAR_FAILED, error, vm, 0, 0, 0, 0, 0);
            }
            return error;
        }
        (*vm).vvar_addr = vvar_start as *mut c_void;

        if !vdso_ref.vvar_virt.is_null() && vdso_ref.vvar_is_global == 0 {
            let s = arch_vdso_addr_add((*vm).vdso_addr as CULong, vdso_ref.vvar_virt as isize);
            let e = s.wrapping_add(PAGE_SIZE);
            let attr = PTATTR_ACTIVE | PTATTR_USER | PTATTR_NO_EXECUTE;
            error = set_range(
                page_table,
                vm,
                s,
                e,
                vdso_ref.vvar_phys as CULong,
                attr,
                range,
            );
            if error != 0 {
                if let Some(log) = log_fn {
                    log(ARCH_VDSO_MAP_LOG_SET_RANGE_FAILED, error, vm, 0, 0, 0, 0, 0);
                }
                return error;
            }
        }
        if !vdso_ref.hpet_virt.is_null() && vdso_ref.hpet_is_global == 0 {
            let s = arch_vdso_addr_add((*vm).vdso_addr as CULong, vdso_ref.hpet_virt as isize);
            let e = s.wrapping_add(PAGE_SIZE);
            let attr = PTATTR_ACTIVE | PTATTR_USER | PTATTR_NO_EXECUTE | PTATTR_UNCACHABLE;
            error = set_range(
                page_table,
                vm,
                s,
                e,
                vdso_ref.hpet_phys as CULong,
                attr,
                range,
            );
            if error != 0 {
                if let Some(log) = log_fn {
                    log(ARCH_VDSO_MAP_LOG_SET_RANGE_FAILED, error, vm, 0, 0, 0, 0, 0);
                }
                return error;
            }
        }
        if !vdso_ref.pvti_virt.is_null() && vdso_ref.pvti_is_global == 0 {
            let s = arch_vdso_addr_add((*vm).vdso_addr as CULong, vdso_ref.pvti_virt as isize);
            let e = s.wrapping_add(PAGE_SIZE);
            let attr = PTATTR_ACTIVE | PTATTR_USER | PTATTR_NO_EXECUTE;
            error = set_range(
                page_table,
                vm,
                s,
                e,
                vdso_ref.pvti_phys as CULong,
                attr,
                range,
            );
            if error != 0 {
                if let Some(log) = log_fn {
                    log(ARCH_VDSO_MAP_LOG_SET_RANGE_FAILED, error, vm, 0, 0, 0, 0, 0);
                }
                return error;
            }
        }
    }

    0
}

#[no_mangle]
pub extern "C" fn migrate_pages_body_result() -> CLong {
    -(ENOSYS as CLong)
}

#[no_mangle]
pub extern "C" fn madvise_body_result(_start: CULong, _len: SizeT, _advice: CInt) -> CLong {
    0
}

#[no_mangle]
pub extern "C" fn get_system_body_result() -> CLong {
    0
}

#[no_mangle]
pub extern "C" fn perf_event_open_disabled_body_result() -> CLong {
    -(ENOSYS as CLong)
}

#[no_mangle]
pub unsafe extern "C" fn linux_mlock_body_result(
    addr: CULong,
    len: SizeT,
    syscall_nr: CInt,
    syscall2_fn: Option<SyscallDoSyscall2Fn>,
) -> CLong {
    let Some(syscall2) = syscall2_fn else {
        return -(EFAULT as CLong);
    };

    syscall2(syscall_nr, addr, len as CULong)
}

#[no_mangle]
pub unsafe extern "C" fn linux_spawn_body_result(
    syscall_nr: CInt,
    ctx: *mut c_void,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    let Some(forward) = forward_fn else {
        return -(EFAULT as CLong);
    };

    forward(syscall_nr, ctx)
}

#[no_mangle]
pub unsafe extern "C" fn swapout_body_result(
    filename: *const c_void,
    workarea: *mut c_void,
    size: SizeT,
    flag: CInt,
    syscall_nr: CInt,
    linux_ctx: *mut c_void,
    pageout_fn: Option<SwapoutPageoutFn>,
    pagein_fn: Option<SwapoutPageinFn>,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    if filename.is_null() || flag == 1 {
        let Some(forward) = forward_fn else {
            return -(EFAULT as CLong);
        };
        return forward(syscall_nr, linux_ctx);
    }

    let Some(pageout) = pageout_fn else {
        return -(EFAULT as CLong);
    };
    let pageout_rc = pageout(filename, workarea, size, flag);
    if pageout_rc < 0 {
        return pageout_rc as CLong;
    }

    if flag != 2 {
        let Some(forward) = forward_fn else {
            return -(EFAULT as CLong);
        };
        let _ = forward(syscall_nr, linux_ctx);
    }

    let Some(pagein) = pagein_fn else {
        return -(EFAULT as CLong);
    };

    pagein(flag) as CLong
}

unsafe fn c_bytes_eq(left: *const c_void, right: *const c_void, len: SizeT) -> bool {
    if left.is_null() || right.is_null() {
        return false;
    }
    let lhs = left.cast::<u8>();
    let rhs = right.cast::<u8>();
    let mut i = 0;

    while i < len {
        if *lhs.add(i) != *rhs.add(i) {
            return false;
        }
        i += 1;
    }

    true
}

#[no_mangle]
pub unsafe extern "C" fn open_common_body_result(
    pathname_addr: CULong,
    flags: CInt,
    syscall_nr: CInt,
    ctx: *mut c_void,
    xpmem_dev_path: *const c_void,
    alloc_flags: CULong,
    strlen_fn: Option<SyscallStrlenUserFn>,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    alloc_fn: Option<SyscallPolicyAllocFn>,
    free_fn: Option<SyscallMckfdFreeFn>,
    special_open_fn: Option<SyscallOpenSpecialFn>,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    let Some(strlen_user) = strlen_fn else {
        return -(EFAULT as CLong);
    };
    let len = strlen_user(pathname_addr as *const c_void);
    if len < 0 {
        return len;
    }

    let bytes = (len as SizeT).wrapping_add(1);
    if bytes == 0 {
        return -(EINVAL as CLong);
    }

    let Some(alloc) = alloc_fn else {
        return -(EFAULT as CLong);
    };
    let pathname = alloc(bytes, alloc_flags);
    if pathname.is_null() {
        return -(ENOMEM as CLong);
    }

    let rc: CLong;
    let Some(copy_from) = copy_from_fn else {
        if let Some(free) = free_fn {
            free(pathname);
        }
        return -(EFAULT as CLong);
    };
    if copy_from(pathname.cast::<u8>(), pathname_addr, bytes) != 0 {
        rc = -(EFAULT as CLong);
    } else if c_bytes_eq(pathname, xpmem_dev_path, bytes) {
        let Some(special_open) = special_open_fn else {
            if let Some(free) = free_fn {
                free(pathname);
            }
            return -(EFAULT as CLong);
        };
        rc = special_open(pathname, flags, ctx);
    } else {
        let Some(forward) = forward_fn else {
            if let Some(free) = free_fn {
                free(pathname);
            }
            return -(EFAULT as CLong);
        };
        rc = forward(syscall_nr, ctx);
    }

    if let Some(free) = free_fn {
        free(pathname);
    }

    rc
}

#[no_mangle]
pub unsafe extern "C" fn util_migrate_inter_kernel_body_result(
    arg_addr: CULong,
    scratch_attr: *mut c_void,
    attr_size: SizeT,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    util_thread_fn: Option<UtilThreadFn>,
) -> CLong {
    let Some(util_thread) = util_thread_fn else {
        return -(EFAULT as CLong);
    };

    let attr = if arg_addr == 0 {
        core::ptr::null_mut()
    } else {
        if scratch_attr.is_null() {
            return -(EFAULT as CLong);
        }
        let Some(copy_from) = copy_from_fn else {
            return -(EFAULT as CLong);
        };
        if copy_from(scratch_attr.cast::<u8>(), arg_addr, attr_size) != 0 {
            return -(EFAULT as CLong);
        }
        scratch_attr
    };

    util_thread(attr)
}

#[no_mangle]
pub unsafe extern "C" fn util_indicate_clone_body_result(
    thread: *mut c_void,
    mode: CInt,
    arg_addr: CULong,
    attr_size: SizeT,
    alloc_flags: CULong,
    thread_proc_offset: SizeT,
    proc_enable_uti_offset: SizeT,
    thread_mod_clone_offset: SizeT,
    thread_mod_clone_arg_offset: SizeT,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    alloc_fn: Option<SyscallPolicyAllocFn>,
    free_fn: Option<SyscallMckfdFreeFn>,
) -> CLong {
    if thread.is_null() {
        return -(EFAULT as CLong);
    }

    let proc = *thread
        .cast::<u8>()
        .add(thread_proc_offset)
        .cast::<*mut u8>();
    if proc.is_null() {
        return -(EFAULT as CLong);
    }
    if *proc.add(proc_enable_uti_offset).cast::<CInt>() == 0 {
        return -(EINVAL as CLong);
    }

    if mode != SPAWN_TO_LOCAL && mode != SPAWN_TO_REMOTE {
        return -(EINVAL as CLong);
    }

    let mut new_attr = core::ptr::null_mut::<c_void>();
    if arg_addr != 0 {
        let Some(alloc) = alloc_fn else {
            return -(EFAULT as CLong);
        };
        new_attr = alloc(attr_size, alloc_flags);
        if new_attr.is_null() {
            return -(ENOMEM as CLong);
        }

        let Some(copy_from) = copy_from_fn else {
            if let Some(free) = free_fn {
                free(new_attr);
            }
            return -(EFAULT as CLong);
        };
        if copy_from(new_attr.cast::<u8>(), arg_addr, attr_size) != 0 {
            if let Some(free) = free_fn {
                free(new_attr);
            }
            return -(EFAULT as CLong);
        }
    }

    *thread
        .cast::<u8>()
        .add(thread_mod_clone_offset)
        .cast::<CInt>() = mode;

    let mod_arg_slot = thread
        .cast::<u8>()
        .add(thread_mod_clone_arg_offset)
        .cast::<*mut c_void>();
    let old_attr = *mod_arg_slot;
    if !old_attr.is_null() {
        let Some(free) = free_fn else {
            if !new_attr.is_null() {
                return -(EFAULT as CLong);
            }
            return -(EFAULT as CLong);
        };
        free(old_attr);
        *mod_arg_slot = core::ptr::null_mut();
    }
    if !new_attr.is_null() {
        *mod_arg_slot = new_attr;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn util_register_desc_body_result(
    desc: CULong,
    desc_store: *mut CULong,
) -> CLong {
    if desc_store.is_null() {
        return -(EFAULT as CLong);
    }

    *desc_store = desc;
    0
}

#[no_mangle]
pub unsafe extern "C" fn threads_signal_body_result(
    current_thread: *mut c_void,
    signal: CInt,
    wait_stopped: CInt,
    thread_proc_offset: SizeT,
    proc_pid_offset: SizeT,
    proc_threads_list_offset: SizeT,
    thread_tid_offset: SizeT,
    thread_status_offset: SizeT,
    thread_siblings_list_offset: SizeT,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
    pause_fn: Option<SyscallCpuPauseFn>,
) -> CLong {
    if current_thread.is_null() {
        return -(EFAULT as CLong);
    }
    let Some(do_kill) = do_kill_fn else {
        return -(EFAULT as CLong);
    };

    let current = current_thread.cast::<u8>();
    let proc = *current.add(thread_proc_offset).cast::<*mut u8>();
    if proc.is_null() {
        return -(EFAULT as CLong);
    }
    let pid = *proc.add(proc_pid_offset).cast::<CInt>();
    let head = proc.add(proc_threads_list_offset).cast::<AbiListHead>();

    let mut pos = (*head).next;
    while pos != head {
        let target = pos.cast::<u8>().sub(thread_siblings_list_offset);
        if target != current {
            do_kill(
                current_thread,
                pid,
                *target.add(thread_tid_offset).cast::<CInt>(),
                signal,
                core::ptr::null(),
                0,
            );
        }
        pos = (*pos).next;
    }

    if wait_stopped == 0 {
        return 0;
    }

    let Some(pause) = pause_fn else {
        return -(EFAULT as CLong);
    };
    loop {
        let mut all_stopped = true;

        pos = (*head).next;
        while pos != head {
            let target = pos.cast::<u8>().sub(thread_siblings_list_offset);
            if target != current && *target.add(thread_status_offset).cast::<CInt>() != PS_STOPPED {
                all_stopped = false;
                break;
            }
            pos = (*pos).next;
        }

        if all_stopped {
            return 0;
        }
        pause();
    }
}

#[no_mangle]
pub extern "C" fn ptrace_signal_data_result(data: CLong) -> CInt {
    if data > NSIG as CLong || data < 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ptrace_detach_signal_result(data: CLong) -> CInt {
    if data > NSIG as CLong || data < 0 {
        -EIO
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ptrace_user_area_result(addr: CLong, user_struct_size: CULong) -> CInt {
    if addr < 0 || addr as CULong > user_struct_size.wrapping_sub(8) {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ptrace_status_allows_io(status: CInt) -> CInt {
    if (status & (PS_STOPPED | PS_TRACED)) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ptrace_setoptions_flags_result(flags: CInt) -> CInt {
    if (flags & !PTRACE_ALLOWED_OPTIONS) != 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ptrace_apply_options(current: CInt, flags: CInt) -> CInt {
    (current & !PTRACE_O_MASK) | flags
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_setoptions_apply_thread_result(
    thread_addr: CULong,
    ptrace_offset: CULong,
    flags: CInt,
) -> CInt {
    if thread_addr == 0 {
        return 0;
    }

    let ptracep = thread_addr.wrapping_add(ptrace_offset) as *mut CInt;
    let updated = ptrace_apply_options(unsafe { *ptracep }, flags);
    unsafe { write(ptracep, updated) };
    updated
}

#[no_mangle]
pub extern "C" fn ptrace_child_traced_result(
    has_child: CInt,
    has_proc: CInt,
    ptrace: CInt,
) -> CInt {
    if has_child == 0 || has_proc == 0 || (ptrace & PT_TRACED) == 0 {
        -ESRCH
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ptrace_attach_policy_result(
    tracer_pid: CInt,
    target_pid: CInt,
    target_ptrace: CInt,
    same_process: CInt,
) -> CInt {
    if tracer_pid == target_pid {
        return -EPERM;
    }

    if (target_ptrace & PT_TRACED) != 0 || same_process != 0 {
        return -EPERM;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_attach_mark_traced_result(
    thread_addr: CULong,
    ptrace_offset: CULong,
) -> CInt {
    if thread_addr == 0 {
        return 0;
    }

    let ptracep = thread_addr.wrapping_add(ptrace_offset) as *mut CInt;
    let traced = PT_TRACED | PT_TRACE_EXEC;
    unsafe { write(ptracep, traced) };
    traced
}

#[no_mangle]
pub extern "C" fn ptrace_detach_state_result(is_traced: CInt, same_report_proc: CInt) -> CInt {
    if is_traced == 0 || same_report_proc == 0 {
        -ESRCH
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ptrace_siginfo_state_result(status: CInt, has_siginfo: CInt) -> CInt {
    if ptrace_status_allows_io(status) == 0 {
        return -ESRCH;
    }

    if has_siginfo == 0 {
        return -ESRCH;
    }

    0
}

#[no_mangle]
pub extern "C" fn ptrace_eventmsg_state_result(status: CInt) -> CInt {
    if ptrace_status_allows_io(status) != 0 {
        0
    } else {
        -ESRCH
    }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_eventmsg_prepare_result(
    status: CInt,
    eventmsg: CULong,
    outp: *mut CULong,
) -> CInt {
    let rc = ptrace_eventmsg_state_result(status);
    if rc != 0 {
        return rc;
    }

    if !outp.is_null() {
        unsafe { write(outp, eventmsg) };
    }
    0
}

#[no_mangle]
pub extern "C" fn ptrace_wakeup_request_action_result(request: CLong) -> CInt {
    if request == PTRACE_KILL {
        PTRACE_WAKEUP_ACTION_KILL
    } else if request == PTRACE_CONT || request == PTRACE_SINGLESTEP || request == PTRACE_SYSCALL {
        PTRACE_WAKEUP_ACTION_RESUME
    } else {
        PTRACE_WAKEUP_ACTION_NONE
    }
}

#[no_mangle]
pub extern "C" fn ptrace_resume_single_step_result(request: CLong) -> CInt {
    (request == PTRACE_SINGLESTEP) as CInt
}

#[no_mangle]
pub extern "C" fn ptrace_resume_trace_syscall_result(request: CLong) -> CInt {
    (request == PTRACE_SYSCALL) as CInt
}

#[no_mangle]
pub extern "C" fn ptrace_resume_signal_needed_result(request: CLong, data: CLong) -> CInt {
    (ptrace_wakeup_request_action_result(request) == PTRACE_WAKEUP_ACTION_RESUME
        && data != 0
        && data != SIGSTOP as CLong) as CInt
}

#[no_mangle]
pub extern "C" fn ptrace_resume_signal_source_result(
    request: CLong,
    has_sendsig: CInt,
    has_recvsig: CInt,
) -> CInt {
    if request == PTRACE_CONT && has_sendsig != 0 {
        PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG
    } else if request == PTRACE_CONT && has_recvsig != 0 {
        PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG
    } else {
        PTRACE_RESUME_SIGNAL_SOURCE_USER
    }
}

#[no_mangle]
pub extern "C" fn ptrace_detach_forward_signal_needed_result(data: CInt) -> CInt {
    (data != 0) as CInt
}

#[no_mangle]
pub extern "C" fn ptrace_detach_exit_signal_needed_result(status: CInt) -> CInt {
    (status == PS_EXITED || status == PS_ZOMBIE) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_thread_body_result(
    thread: *mut c_void,
    data: CInt,
    current_thread: *mut c_void,
    current_proc: *mut c_void,
    pid1: *mut c_void,
    offsets: *const PtraceDetachOffsets,
    lock_fn: Option<WaitLockUnlockFn>,
    unlock_fn: Option<WaitLockUnlockFn>,
    list_detach_fn: Option<PtraceListDetachFn>,
    main_reparent_fn: Option<PtraceMainReparentFn>,
    report_detach_fn: Option<PtraceReportDetachFn>,
    cleanup_fn: Option<PtraceCleanupFn>,
    free_fn: Option<PtraceFreeFn>,
    clear_single_step_fn: Option<PtraceClearSingleStepFn>,
    report_attach_fn: Option<PtraceReportAttachFn>,
    exit_signal_fn: Option<PtraceThreadExitSignalFn>,
    do_kill_fn: Option<PtraceDoKillThreadFn>,
    wakeup_fn: Option<PtraceWakeupThreadFn>,
    release_fn: Option<WaitThreadSideEffectFn>,
    finalize_fn: Option<PtraceFinalizeProcessFn>,
    lock_node: *mut c_void,
) -> CInt {
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(list_detach_fn) = list_detach_fn else {
        return -EINVAL;
    };
    let Some(main_reparent_fn) = main_reparent_fn else {
        return -EINVAL;
    };
    let Some(report_detach_fn) = report_detach_fn else {
        return -EINVAL;
    };
    let Some(cleanup_fn) = cleanup_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    let Some(clear_single_step_fn) = clear_single_step_fn else {
        return -EINVAL;
    };
    let Some(report_attach_fn) = report_attach_fn else {
        return -EINVAL;
    };
    let Some(exit_signal_fn) = exit_signal_fn else {
        return -EINVAL;
    };
    let Some(do_kill_fn) = do_kill_fn else {
        return -EINVAL;
    };
    let Some(wakeup_fn) = wakeup_fn else {
        return -EINVAL;
    };
    let Some(release_fn) = release_fn else {
        return -EINVAL;
    };
    let Some(finalize_fn) = finalize_fn else {
        return -EINVAL;
    };
    if thread.is_null()
        || current_thread.is_null()
        || current_proc.is_null()
        || pid1.is_null()
        || offsets.is_null()
        || lock_node.is_null()
    {
        return -EINVAL;
    }

    let offsets = &*offsets;
    let thread_proc_offset = read_volatile(&offsets.thread_proc_offset);
    let thread_termsig_offset = read_volatile(&offsets.thread_termsig_offset);
    let thread_status_offset = read_volatile(&offsets.thread_status_offset);
    let thread_tid_offset = read_volatile(&offsets.thread_tid_offset);
    let thread_report_proc_offset = read_volatile(&offsets.thread_report_proc_offset);
    let thread_report_siblings_list_offset =
        read_volatile(&offsets.thread_report_siblings_list_offset);
    let thread_ptrace_offset = read_volatile(&offsets.thread_ptrace_offset);
    let thread_ptrace_saved_uctx_valid_offset =
        read_volatile(&offsets.thread_ptrace_saved_uctx_valid_offset);
    let thread_ptrace_debugreg_offset = read_volatile(&offsets.thread_ptrace_debugreg_offset);
    let proc_pid_offset = read_volatile(&offsets.proc_pid_offset);
    let proc_status_offset = read_volatile(&offsets.proc_status_offset);
    let proc_parent_offset = read_volatile(&offsets.proc_parent_offset);
    let proc_ppid_parent_offset = read_volatile(&offsets.proc_ppid_parent_offset);
    let proc_main_thread_offset = read_volatile(&offsets.proc_main_thread_offset);
    let proc_children_lock_offset = read_volatile(&offsets.proc_children_lock_offset);
    let proc_threads_lock_offset = read_volatile(&offsets.proc_threads_lock_offset);
    let proc_children_list_offset = read_volatile(&offsets.proc_children_list_offset);
    let proc_siblings_list_offset = read_volatile(&offsets.proc_siblings_list_offset);
    let proc_ptraced_siblings_list_offset =
        read_volatile(&offsets.proc_ptraced_siblings_list_offset);
    let proc_report_threads_list_offset = read_volatile(&offsets.proc_report_threads_list_offset);

    let thread_base = thread.cast::<u8>();
    let current_base = current_proc.cast::<u8>();
    let thread_proc = *field_ptr::<*mut u8>(thread_base, thread_proc_offset);
    if thread_proc.is_null() {
        return -EINVAL;
    }

    let mut actions = 0;
    let mut term_proc = core::ptr::null_mut::<u8>();
    let main_thread = *field_ptr::<*mut u8>(thread_proc, proc_main_thread_offset);
    if thread_base == main_thread {
        let parent = *field_ptr::<*mut u8>(thread_proc, proc_ppid_parent_offset);
        if parent.is_null() {
            return -EINVAL;
        }
        actions |= 1;
        let tracee_status = read_volatile(field_ptr::<CInt>(thread_proc, proc_status_offset));
        let parent_field = *field_ptr::<*mut u8>(thread_proc, proc_parent_offset);
        if tracee_status == PS_ZOMBIE && parent_field != parent {
            term_proc = thread_proc;
            actions |= 2;
        }

        let current_children_lock = field_ptr::<c_void>(current_base, proc_children_lock_offset);
        lock_fn(current_children_lock, lock_node);
        list_detach_fn(field_ptr::<c_void>(thread_proc, proc_siblings_list_offset));
        unlock_fn(current_children_lock, lock_node);

        let tracee_children_lock = field_ptr::<c_void>(thread_proc, proc_children_lock_offset);
        lock_fn(tracee_children_lock, lock_node);
        main_reparent_fn(
            thread_proc.cast::<c_void>(),
            proc_parent_offset as CULong,
            parent.cast::<c_void>(),
            field_ptr::<c_void>(thread_proc, proc_ptraced_siblings_list_offset),
            field_ptr::<c_void>(thread_proc, proc_siblings_list_offset),
            field_ptr::<c_void>(parent, proc_children_list_offset),
        );
        unlock_fn(tracee_children_lock, lock_node);
    }

    let termsig = read_volatile(field_ptr::<CInt>(thread_base, thread_termsig_offset));
    let mut report_proc = core::ptr::null_mut::<u8>();
    if termsig != 0 && termsig != SIGCHLD && thread_proc != pid1.cast::<u8>() {
        report_proc = thread_proc;
        actions |= 4;
    }

    let current_threads_lock = field_ptr::<c_void>(current_base, proc_threads_lock_offset);
    lock_fn(current_threads_lock, lock_node);
    report_detach_fn(
        thread,
        thread_report_proc_offset as CULong,
        report_proc.cast::<c_void>(),
        field_ptr::<c_void>(thread_base, thread_report_siblings_list_offset),
    );
    unlock_fn(current_threads_lock, lock_node);

    let debugreg = cleanup_fn(
        thread,
        thread_ptrace_offset as CULong,
        thread_ptrace_saved_uctx_valid_offset as CULong,
        thread_ptrace_debugreg_offset as CULong,
    );
    free_fn(debugreg);
    clear_single_step_fn(thread);
    actions |= 8;

    if !report_proc.is_null() {
        let report_threads_lock = field_ptr::<c_void>(report_proc, proc_threads_lock_offset);
        lock_fn(report_threads_lock, lock_node);
        report_attach_fn(
            thread,
            0,
            0,
            0,
            thread_report_proc_offset as CULong,
            report_proc.cast::<c_void>(),
            field_ptr::<c_void>(thread_base, thread_report_siblings_list_offset),
            field_ptr::<c_void>(report_proc, proc_report_threads_list_offset),
        );
        unlock_fn(report_threads_lock, lock_node);
        actions |= 16;

        let thread_status = read_volatile(field_ptr::<CInt>(thread_base, thread_status_offset));
        if ptrace_detach_exit_signal_needed_result(thread_status) != 0 {
            exit_signal_fn(thread);
            actions |= 32;
        }
    }

    if ptrace_detach_forward_signal_needed_result(data) != 0 {
        let mut info = MaybeUninit::<SigInfo>::uninit();
        let info_ptr = info.as_mut_ptr();
        let raw = info_ptr.cast::<u8>();
        let mut offset = 0;
        while offset < size_of::<SigInfo>() {
            raw.add(offset).write_volatile(0);
            offset += 1;
        }

        let info = &mut *info_ptr;
        info.si_signo = data;
        info.si_code = SI_USER;
        info.sifields.kill = ManuallyDrop::new(SigInfoKill {
            si_pid: read_volatile(field_ptr::<CInt>(current_base, proc_pid_offset)),
            si_uid: 0,
        });
        do_kill_fn(
            current_thread,
            read_volatile(field_ptr::<CInt>(thread_proc, proc_pid_offset)),
            read_volatile(field_ptr::<CInt>(thread_base, thread_tid_offset)),
            data,
            info as *const SigInfo,
            1,
        );
        actions |= 64;
    }

    wakeup_fn(thread, PS_TRACED | PS_STOPPED);
    release_fn(thread);
    actions |= 128;
    if !term_proc.is_null() {
        finalize_fn(term_proc.cast::<c_void>());
        actions |= 256;
    }

    actions
}

#[no_mangle]
pub extern "C" fn ptrace_setsiginfo_target_result(
    status: CInt,
    has_sendsig: CInt,
    has_recvsig: CInt,
) -> CInt {
    if ptrace_status_allows_io(status) == 0 {
        return -ESRCH;
    }

    let mut target = PTRACE_SIGINFO_STORE_SENDSIG;
    if has_sendsig == 0 {
        target |= PTRACE_SIGINFO_ALLOC_SENDSIG;
    }
    if has_recvsig != 0 {
        target |= PTRACE_SIGINFO_STORE_RECVSIG;
    }
    target
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_getsiginfo_prepare_result(
    status: CInt,
    pending_addr: CULong,
    info_offset: CULong,
    outp: *mut u8,
    info_size: SizeT,
) -> CInt {
    let rc = ptrace_siginfo_state_result(status, (pending_addr != 0) as CInt);
    if rc != 0 {
        return rc;
    }
    if outp.is_null() {
        return -EFAULT;
    }

    unsafe {
        copy_nonoverlapping(
            pending_addr.wrapping_add(info_offset) as *const u8,
            outp,
            info_size,
        );
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_setsiginfo_store_result(
    thread_addr: CULong,
    sendsig_offset: CULong,
    recvsig_offset: CULong,
    info_offset: CULong,
    target: CInt,
    allocated_sendsig: CULong,
    infop: *const u8,
    info_size: SizeT,
) -> CInt {
    if target < 0 {
        return target;
    }
    if thread_addr == 0 {
        return -ESRCH;
    }

    let sendsig_slot = thread_addr.wrapping_add(sendsig_offset) as *mut CULong;
    let recvsig_slot = thread_addr.wrapping_add(recvsig_offset) as *mut CULong;

    if (target & PTRACE_SIGINFO_ALLOC_SENDSIG) != 0 {
        if allocated_sendsig == 0 {
            return -ENOMEM;
        }
        unsafe { write(sendsig_slot, allocated_sendsig) };
    }

    if (target & (PTRACE_SIGINFO_STORE_SENDSIG | PTRACE_SIGINFO_STORE_RECVSIG)) != 0
        && infop.is_null()
    {
        return -EFAULT;
    }

    if (target & PTRACE_SIGINFO_STORE_SENDSIG) != 0 {
        let pending = unsafe { *sendsig_slot };
        if pending == 0 {
            return -ENOMEM;
        }
        unsafe {
            copy_nonoverlapping(
                infop,
                pending.wrapping_add(info_offset) as *mut u8,
                info_size,
            );
        }
    }

    if (target & PTRACE_SIGINFO_STORE_RECVSIG) != 0 {
        let pending = unsafe { *recvsig_slot };
        if pending == 0 {
            return -ESRCH;
        }
        unsafe {
            copy_nonoverlapping(
                infop,
                pending.wrapping_add(info_offset) as *mut u8,
                info_size,
            );
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_read_user_words_result(
    thread_addr: CULong,
    outp: *mut CULong,
    bytes: SizeT,
    read_fn: Option<PtraceReadUserWordFn>,
) -> CLong {
    if thread_addr == 0 || outp.is_null() {
        return -EFAULT as CLong;
    }
    let Some(read_word) = read_fn else {
        return -EFAULT as CLong;
    };

    let word_size = size_of::<CULong>();
    let mut offset = 0usize;
    let mut index = 0usize;
    while offset < bytes {
        let rc = unsafe { read_word(thread_addr, offset as CLong, outp.wrapping_add(index)) };
        if rc != 0 {
            return rc;
        }
        offset = offset.wrapping_add(word_size);
        index = index.wrapping_add(1);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_write_user_words_result(
    thread_addr: CULong,
    inp: *const CULong,
    bytes: SizeT,
    write_fn: Option<PtraceWriteUserWordFn>,
) -> CLong {
    if thread_addr == 0 || inp.is_null() {
        return -EFAULT as CLong;
    }
    let Some(write_word) = write_fn else {
        return -EFAULT as CLong;
    };

    let word_size = size_of::<CULong>();
    let mut offset = 0usize;
    let mut index = 0usize;
    while offset < bytes {
        let value = unsafe { *inp.wrapping_add(index) };
        let rc = unsafe { write_word(thread_addr, offset as CLong, value) };
        if rc != 0 {
            return rc;
        }
        offset = offset.wrapping_add(word_size);
        index = index.wrapping_add(1);
    }
    0
}

unsafe fn arch_ptrace_user_context(
    thread: *mut c_void,
    offsets: &ArchPtraceUserOffsets,
    lookup_fn: Option<ArchPtraceLookupUserContextFn>,
) -> *mut u8 {
    let thread_base = thread.cast::<u8>();
    let saved_valid = read_volatile(field_ptr::<CInt>(
        thread_base,
        offsets.thread_ptrace_saved_uctx_valid_offset,
    ));
    if saved_valid != 0 {
        return thread_base.add(offsets.thread_ptrace_saved_uctx_offset);
    }
    if let Some(lookup_user_context) = lookup_fn {
        return lookup_user_context(thread).cast::<u8>();
    }
    core::ptr::null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_read_user_body_result(
    thread: *mut c_void,
    addr: CLong,
    valuep: *mut CULong,
    word_size: SizeT,
    user_regs_size: SizeT,
    user_regs_fs_base_offset: SizeT,
    user_debugreg_start_offset: SizeT,
    user_debugreg_end_offset: SizeT,
    offsets: *const ArchPtraceUserOffsets,
    lookup_fn: Option<ArchPtraceLookupUserContextFn>,
    log_fn: Option<PtraceControlLogFn>,
) -> CLong {
    if thread.is_null() || valuep.is_null() || offsets.is_null() || word_size == 0 {
        return -(EFAULT as CLong);
    }
    let addr_u = addr as SizeT;
    if addr < 0 || (addr_u & (word_size - 1)) != 0 {
        return -(EIO as CLong);
    }

    let offsets = &*offsets;
    if addr_u < user_regs_size {
        let uctx = arch_ptrace_user_context(thread, offsets, lookup_fn);
        if uctx.is_null() {
            return -(EIO as CLong);
        }
        let src = if addr_u < user_regs_fs_base_offset {
            uctx.add(offsets.uctx_gpr_offset).add(addr_u)
        } else {
            uctx.add(offsets.uctx_sr_offset)
                .add(addr_u - user_regs_fs_base_offset)
        };
        write_volatile(valuep, read_volatile(src.cast::<CULong>()));
        return 0;
    }

    if user_debugreg_start_offset <= addr_u && addr_u < user_debugreg_end_offset {
        let thread_base = thread.cast::<u8>();
        let debugreg = read_volatile(field_ptr::<*mut CULong>(
            thread_base,
            offsets.thread_ptrace_debugreg_offset,
        ));
        if debugreg.is_null() {
            if let Some(log) = log_fn {
                log(ARCH_PTRACE_USER_LOG_READ_MISSING_DEBUGREG, 0, 0);
            }
            return -(EFAULT as CLong);
        }
        let index = (addr_u - user_debugreg_start_offset) / word_size;
        write_volatile(valuep, read_volatile(debugreg.add(index)));
        return 0;
    }

    if let Some(log) = log_fn {
        log(ARCH_PTRACE_USER_LOG_READ_OTHER, addr as CInt, 0);
    }
    write_volatile(valuep, 0);
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_write_user_body_result(
    thread: *mut c_void,
    addr: CLong,
    mut value: CULong,
    word_size: SizeT,
    user_regs_size: SizeT,
    user_regs_fs_base_offset: SizeT,
    user_regs_eflags_offset: SizeT,
    user_debugreg_start_offset: SizeT,
    user_debugreg_end_offset: SizeT,
    offsets: *const ArchPtraceUserOffsets,
    lookup_fn: Option<ArchPtraceLookupUserContextFn>,
    log_fn: Option<PtraceControlLogFn>,
) -> CLong {
    if thread.is_null() || offsets.is_null() || word_size == 0 {
        return -(EFAULT as CLong);
    }
    let addr_u = addr as SizeT;
    if addr < 0 || (addr_u & (word_size - 1)) != 0 {
        return -(EIO as CLong);
    }

    let offsets = &*offsets;
    if addr_u < user_regs_size {
        let uctx = arch_ptrace_user_context(thread, offsets, lookup_fn);
        if uctx.is_null() {
            return -(EIO as CLong);
        }
        if addr_u == user_regs_eflags_offset {
            let rflagsp = uctx
                .add(offsets.uctx_gpr_offset)
                .add(addr_u)
                .cast::<CULong>();
            let mut rflags = read_volatile(rflagsp);
            rflags &= !RFLAGS_MASK;
            rflags |= value & RFLAGS_MASK;
            write_volatile(rflagsp, rflags);
        } else if addr_u < user_regs_fs_base_offset {
            write_volatile(
                uctx.add(offsets.uctx_gpr_offset)
                    .add(addr_u)
                    .cast::<CULong>(),
                value,
            );
        } else {
            write_volatile(
                uctx.add(offsets.uctx_sr_offset)
                    .add(addr_u - user_regs_fs_base_offset)
                    .cast::<CULong>(),
                value,
            );
        }
        return 0;
    }

    if user_debugreg_start_offset <= addr_u && addr_u < user_debugreg_end_offset {
        let thread_base = thread.cast::<u8>();
        let debugreg = read_volatile(field_ptr::<*mut CULong>(
            thread_base,
            offsets.thread_ptrace_debugreg_offset,
        ));
        if debugreg.is_null() {
            if let Some(log) = log_fn {
                log(ARCH_PTRACE_USER_LOG_WRITE_MISSING_DEBUGREG, 0, 0);
            }
            return -(EFAULT as CLong);
        }
        if addr_u == user_debugreg_start_offset + 6 * word_size {
            value &= !DB6_RESERVED_MASK;
            value |= DB6_RESERVED_SET;
        }
        if addr_u == user_debugreg_start_offset + 7 * word_size {
            value &= !DB7_RESERVED_MASK;
            value |= DB7_RESERVED_SET;
        }
        let index = (addr_u - user_debugreg_start_offset) / word_size;
        write_volatile(debugreg.add(index), value);
        return 0;
    }

    if let Some(log) = log_fn {
        log(ARCH_PTRACE_USER_LOG_WRITE_OTHER, addr as CInt, 0);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_alloc_debugreg_body_result(
    thread: *mut c_void,
    debugreg_offset: SizeT,
    alloc_size: SizeT,
    alloc_flags: CULong,
    alloc_fn: Option<ArchPtraceAllocFn>,
    log_fn: Option<PtraceControlLogFn>,
) -> CLong {
    if thread.is_null() {
        return -(ENOMEM as CLong);
    }
    let Some(alloc) = alloc_fn else {
        return -(ENOMEM as CLong);
    };
    let thread_base = thread.cast::<u8>();
    let slot = field_ptr::<*mut CULong>(thread_base, debugreg_offset);
    let debugreg = alloc(alloc_size, alloc_flags).cast::<CULong>();
    write_volatile(slot, debugreg);
    if debugreg.is_null() {
        if let Some(log) = log_fn {
            log(ARCH_PTRACE_USER_LOG_ALLOC_FAILED, 0, 0);
        }
        return -(ENOMEM as CLong);
    }

    let mut index = 0;
    while index < 8 {
        write_volatile(debugreg.add(index), 0);
        index += 1;
    }
    write_volatile(debugreg.add(6), DB6_RESERVED_SET);
    write_volatile(debugreg.add(7), DB7_RESERVED_SET);
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_read_gpregs_body_result(
    thread_addr: CULong,
    regs: *mut u8,
    regs_size: SizeT,
    read_fn: Option<PtraceReadUserWordFn>,
) -> CLong {
    if regs.is_null() {
        return -(EFAULT as CLong);
    }
    unsafe { core::ptr::write_bytes(regs, 0, regs_size) };
    unsafe { ptrace_read_user_words_result(thread_addr, regs.cast::<CULong>(), regs_size, read_fn) }
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_write_gpregs_body_result(
    thread_addr: CULong,
    regs: *const u8,
    regs_size: SizeT,
    write_fn: Option<PtraceWriteUserWordFn>,
) -> CLong {
    unsafe {
        ptrace_write_user_words_result(thread_addr, regs.cast::<CULong>(), regs_size, write_fn)
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_fpregs_io_body_result(
    thread_addr: CULong,
    user_addr: CULong,
    fp_regs_offset: SizeT,
    fp_i387_offset: SizeT,
    fp_i387_size: SizeT,
    is_write: CInt,
    copy_to_fn: Option<PtraceUserCopyToFn>,
    copy_from_fn: Option<PtraceUserCopyFromFn>,
) -> CLong {
    if thread_addr == 0 {
        return -(EFAULT as CLong);
    }

    let fp_slot = (thread_addr as *mut u8)
        .wrapping_add(fp_regs_offset)
        .cast::<CULong>();
    let fp_regs = unsafe { *fp_slot };
    if fp_regs == 0 {
        return -(ENOMEM as CLong);
    }
    let fp_i387 = fp_regs.wrapping_add(fp_i387_offset as CULong);

    if is_write != 0 {
        let Some(copy_from_user) = copy_from_fn else {
            return -(EFAULT as CLong);
        };
        unsafe { copy_from_user(fp_i387 as *mut u8, user_addr, fp_i387_size) }
    } else {
        let Some(copy_to_user) = copy_to_fn else {
            return -(EFAULT as CLong);
        };
        unsafe { copy_to_user(user_addr, fp_i387 as *const u8, fp_i387_size) }
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_read_regset_body_result(
    thread_addr: CULong,
    regset_type: CLong,
    iovp: *mut u8,
    scratch: *mut u8,
    user_regs_size: SizeT,
    xstate_size: SizeT,
    iov_base_offset: SizeT,
    iov_len_offset: SizeT,
    read_gpregs_fn: Option<ArchPtraceGpregsReadFn>,
    copy_to_fn: Option<PtraceUserCopyToFn>,
    xstate_copy_to_fn: Option<ArchPtraceXstateIoFn>,
    log_fn: Option<ArchPtraceRegsetLogFn>,
) -> CLong {
    if thread_addr == 0 || iovp.is_null() {
        return -(EFAULT as CLong);
    }
    let basep = iovp.wrapping_add(iov_base_offset).cast::<CULong>();
    let lenp = iovp.wrapping_add(iov_len_offset).cast::<SizeT>();
    let mut len = unsafe { *lenp };

    if regset_type == NT_PRSTATUS {
        if scratch.is_null() {
            return -(EFAULT as CLong);
        }
        if len > user_regs_size {
            len = user_regs_size;
            unsafe { *lenp = len };
        }
        let Some(read_gpregs) = read_gpregs_fn else {
            return -(EFAULT as CLong);
        };
        let Some(copy_to_user) = copy_to_fn else {
            return -(EFAULT as CLong);
        };
        let rc = unsafe { read_gpregs(thread_addr, scratch) };
        if rc != 0 {
            return rc;
        }
        unsafe { copy_to_user(*basep, scratch.cast::<u8>(), len) }
    } else if regset_type == NT_X86_XSTATE {
        if len > xstate_size {
            len = xstate_size;
            unsafe { *lenp = len };
        }
        let Some(xstate_copy_to) = xstate_copy_to_fn else {
            return -(EFAULT as CLong);
        };
        unsafe { xstate_copy_to(thread_addr, *basep, len) }
    } else {
        if let Some(log) = log_fn {
            log(ARCH_PTRACE_REGSET_LOG_READ_UNSUPPORTED, regset_type);
        }
        -(EINVAL as CLong)
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_write_regset_body_result(
    thread_addr: CULong,
    regset_type: CLong,
    iovp: *mut u8,
    scratch: *mut u8,
    user_regs_size: SizeT,
    xstate_size: SizeT,
    iov_base_offset: SizeT,
    iov_len_offset: SizeT,
    read_gpregs_fn: Option<ArchPtraceGpregsReadFn>,
    write_gpregs_fn: Option<ArchPtraceGpregsWriteFn>,
    copy_from_fn: Option<PtraceUserCopyFromFn>,
    xstate_copy_from_fn: Option<ArchPtraceXstateIoFn>,
    log_fn: Option<ArchPtraceRegsetLogFn>,
) -> CLong {
    if thread_addr == 0 || iovp.is_null() {
        return -(EFAULT as CLong);
    }
    let basep = iovp.wrapping_add(iov_base_offset).cast::<CULong>();
    let lenp = iovp.wrapping_add(iov_len_offset).cast::<SizeT>();
    let mut len = unsafe { *lenp };

    if regset_type == NT_PRSTATUS {
        if scratch.is_null() {
            return -(EFAULT as CLong);
        }
        if len > user_regs_size {
            len = user_regs_size;
            unsafe { *lenp = len };
        }
        let Some(read_gpregs) = read_gpregs_fn else {
            return -(EFAULT as CLong);
        };
        let Some(write_gpregs) = write_gpregs_fn else {
            return -(EFAULT as CLong);
        };
        let Some(copy_from_user) = copy_from_fn else {
            return -(EFAULT as CLong);
        };
        let mut rc = unsafe { read_gpregs(thread_addr, scratch) };
        if rc != 0 {
            return rc;
        }
        rc = unsafe { copy_from_user(scratch, *basep, len) };
        if rc != 0 {
            return rc;
        }
        unsafe { write_gpregs(thread_addr, scratch.cast::<u8>()) }
    } else if regset_type == NT_X86_XSTATE {
        if len > xstate_size {
            len = xstate_size;
            unsafe { *lenp = len };
        }
        let Some(xstate_copy_from) = xstate_copy_from_fn else {
            return -(EFAULT as CLong);
        };
        unsafe { xstate_copy_from(thread_addr, *basep, len) }
    } else {
        if let Some(log) = log_fn {
            log(ARCH_PTRACE_REGSET_LOG_WRITE_UNSUPPORTED, regset_type);
        }
        -(EINVAL as CLong)
    }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_read_user_word_result(
    status: CInt,
    thread_addr: CULong,
    user_area_offset: CLong,
    outp: *mut CULong,
    read_fn: Option<PtraceReadUserWordFn>,
) -> CLong {
    if ptrace_status_allows_io(status) == 0 {
        return -EIO as CLong;
    }
    if thread_addr == 0 || outp.is_null() {
        return -EFAULT as CLong;
    }
    let Some(read_word) = read_fn else {
        return -EFAULT as CLong;
    };

    unsafe { read_word(thread_addr, user_area_offset, outp) }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_write_user_word_result(
    status: CInt,
    thread_addr: CULong,
    user_area_offset: CLong,
    value: CULong,
    write_fn: Option<PtraceWriteUserWordFn>,
) -> CLong {
    if ptrace_status_allows_io(status) == 0 {
        return -EIO as CLong;
    }
    if thread_addr == 0 {
        return -EFAULT as CLong;
    }
    let Some(write_word) = write_fn else {
        return -EFAULT as CLong;
    };

    unsafe { write_word(thread_addr, user_area_offset, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_read_vm_word_result(
    status: CInt,
    vm_addr: CULong,
    user_addr: CULong,
    outp: *mut CULong,
    read_fn: Option<PtraceReadVmWordFn>,
) -> CLong {
    if ptrace_status_allows_io(status) == 0 {
        return -EIO as CLong;
    }
    if vm_addr == 0 || outp.is_null() {
        return -EFAULT as CLong;
    }
    let Some(read_word) = read_fn else {
        return -EFAULT as CLong;
    };

    unsafe { read_word(vm_addr, user_addr, outp) }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_write_vm_word_result(
    status: CInt,
    vm_addr: CULong,
    user_addr: CULong,
    value: CULong,
    write_fn: Option<PtraceWriteVmWordFn>,
) -> CLong {
    if ptrace_status_allows_io(status) == 0 {
        return -EIO as CLong;
    }
    if vm_addr == 0 {
        return -EFAULT as CLong;
    }
    let Some(write_word) = write_fn else {
        return -EFAULT as CLong;
    };

    unsafe { write_word(vm_addr, user_addr, value) }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_fpregs_io_result(
    status: CInt,
    thread_addr: CULong,
    data_addr: CULong,
    io_fn: Option<PtraceFpregsIoFn>,
) -> CLong {
    if ptrace_status_allows_io(status) == 0 {
        return -EIO as CLong;
    }
    if thread_addr == 0 {
        return -EFAULT as CLong;
    }
    let Some(io) = io_fn else {
        return -EFAULT as CLong;
    };

    unsafe { io(thread_addr, data_addr) }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_regset_io_result(
    status: CInt,
    thread_addr: CULong,
    regset_type: CLong,
    user_iovec_addr: CULong,
    iovp: *mut u8,
    iov_size: SizeT,
    iov_len_offset: SizeT,
    iov_len_size: SizeT,
    copy_from_fn: Option<PtraceUserCopyFromFn>,
    io_fn: Option<PtraceRegsetIoFn>,
    copy_to_fn: Option<PtraceUserCopyToFn>,
) -> CLong {
    if ptrace_status_allows_io(status) == 0 {
        return -EIO as CLong;
    }
    if thread_addr == 0 || iovp.is_null() {
        return -EFAULT as CLong;
    }
    if iov_len_offset > iov_size || iov_len_size > iov_size.wrapping_sub(iov_len_offset) {
        return -EFAULT as CLong;
    }

    let Some(copy_from_user) = copy_from_fn else {
        return -EFAULT as CLong;
    };
    let Some(regset_io) = io_fn else {
        return -EFAULT as CLong;
    };
    let Some(copy_to_user) = copy_to_fn else {
        return -EFAULT as CLong;
    };

    let mut rc = unsafe { copy_from_user(iovp, user_iovec_addr, iov_size) };
    if rc != 0 {
        return rc;
    }

    rc = unsafe { regset_io(thread_addr, regset_type, iovp) };
    if rc != 0 {
        return rc;
    }

    unsafe {
        copy_to_user(
            user_iovec_addr.wrapping_add(iov_len_offset as CULong),
            iovp.wrapping_add(iov_len_offset) as *const u8,
            iov_len_size,
        )
    }
}

#[inline(always)]
unsafe fn ptrace_io_status(thread_addr: CULong, offsets: *const PtraceIoOffsets) -> CInt {
    let thread = thread_addr as *mut u8;
    unsafe { read_volatile(field_ptr::<CInt>(thread, (*offsets).thread_status_offset)) }
}

#[inline(always)]
unsafe fn ptrace_io_proc(thread_addr: CULong, offsets: *const PtraceIoOffsets) -> CULong {
    let thread = thread_addr as *mut u8;
    unsafe {
        read_volatile(field_ptr::<*mut c_void>(
            thread,
            (*offsets).thread_proc_offset,
        )) as CULong
    }
}

#[inline(always)]
unsafe fn ptrace_io_ptrace(thread_addr: CULong, offsets: *const PtraceIoOffsets) -> CInt {
    let thread = thread_addr as *mut u8;
    unsafe { read_volatile(field_ptr::<CInt>(thread, (*offsets).thread_ptrace_offset)) }
}

#[inline(always)]
unsafe fn ptrace_io_report_proc(thread_addr: CULong, offsets: *const PtraceIoOffsets) -> CULong {
    let thread = thread_addr as *mut u8;
    unsafe {
        read_volatile(field_ptr::<*mut c_void>(
            thread,
            (*offsets).thread_report_proc_offset,
        )) as CULong
    }
}

#[inline(always)]
unsafe fn ptrace_io_proc_pid(proc_addr: CULong, offsets: *const PtraceIoOffsets) -> CInt {
    let proc_ptr = proc_addr as *mut u8;
    unsafe { read_volatile(field_ptr::<CInt>(proc_ptr, (*offsets).proc_pid_offset)) }
}

#[inline(always)]
unsafe fn ptrace_io_proc_update_lock(proc_addr: CULong, offsets: *const PtraceIoOffsets) -> CULong {
    proc_addr.wrapping_add(unsafe { (*offsets).proc_update_lock_offset as CULong })
}

#[inline(always)]
unsafe fn ptrace_io_vm(thread_addr: CULong, offsets: *const PtraceIoOffsets) -> CULong {
    let thread = thread_addr as *mut u8;
    unsafe {
        read_volatile(field_ptr::<*mut c_void>(
            thread,
            (*offsets).thread_vm_offset,
        )) as CULong
    }
}

#[inline(always)]
unsafe fn ptrace_io_eventmsg(thread_addr: CULong, offsets: *const PtraceIoOffsets) -> CULong {
    let thread = thread_addr as *mut u8;
    unsafe {
        read_volatile(field_ptr::<CULong>(
            thread,
            (*offsets).thread_ptrace_eventmsg_offset,
        ))
    }
}

#[inline(always)]
unsafe fn ptrace_io_recvsig(thread_addr: CULong, offsets: *const PtraceIoOffsets) -> CULong {
    let thread = thread_addr as *mut u8;
    unsafe {
        read_volatile(field_ptr::<*mut c_void>(
            thread,
            (*offsets).thread_ptrace_recvsig_offset,
        )) as CULong
    }
}

#[inline(always)]
unsafe fn ptrace_io_sendsig(thread_addr: CULong, offsets: *const PtraceIoOffsets) -> CULong {
    let thread = thread_addr as *mut u8;
    unsafe {
        read_volatile(field_ptr::<*mut c_void>(
            thread,
            (*offsets).thread_ptrace_sendsig_offset,
        )) as CULong
    }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_pokeuser_body_result(
    pid: CInt,
    addr: CLong,
    data: CLong,
    user_struct_size: CULong,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    write_fn: Option<PtraceWriteUserWordFn>,
) -> CLong {
    let area_rc = ptrace_user_area_result(addr, user_struct_size);
    if area_rc != 0 {
        return area_rc as CLong;
    }
    if offsets.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let rc =
        unsafe { ptrace_write_user_word_result(status, child, addr, data as CULong, write_fn) };
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_peekuser_body_result(
    pid: CInt,
    addr: CLong,
    data: CLong,
    user_struct_size: CULong,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    read_fn: Option<PtraceReadUserWordFn>,
    copy_to_fn: Option<PtraceUserCopyToFn>,
) -> CLong {
    let area_rc = ptrace_user_area_result(addr, user_struct_size);
    if area_rc != 0 {
        return area_rc as CLong;
    }
    if offsets.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let mut value: CULong = 0;
    let mut rc = unsafe { ptrace_read_user_word_result(status, child, addr, &mut value, read_fn) };
    if rc == 0 {
        let Some(copy_to_user) = copy_to_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT as CLong;
        };
        rc = unsafe {
            copy_to_user(
                data as CULong,
                (&value as *const CULong).cast::<u8>(),
                core::mem::size_of::<CULong>(),
            )
        };
    }
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_getregs_body_result(
    pid: CInt,
    data: CLong,
    scratch: *mut u8,
    regs_size: SizeT,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    read_fn: Option<PtraceReadUserWordFn>,
    copy_to_fn: Option<PtraceUserCopyToFn>,
) -> CLong {
    if offsets.is_null() || scratch.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let mut rc = -EIO as CLong;
    if ptrace_status_allows_io(status) != 0 {
        unsafe { core::ptr::write_bytes(scratch, 0, regs_size) };
        rc = unsafe {
            ptrace_read_user_words_result(child, scratch.cast::<CULong>(), regs_size, read_fn)
        };
        if rc == 0 {
            let Some(copy_to_user) = copy_to_fn else {
                unsafe { unlock_thread(child) };
                return -EFAULT as CLong;
            };
            rc = unsafe { copy_to_user(data as CULong, scratch.cast::<u8>(), regs_size) };
        }
    }
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_setregs_body_result(
    pid: CInt,
    data: CLong,
    scratch: *mut u8,
    regs_size: SizeT,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    write_fn: Option<PtraceWriteUserWordFn>,
    copy_from_fn: Option<PtraceUserCopyFromFn>,
) -> CLong {
    if offsets.is_null() || scratch.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let mut rc = -EIO as CLong;
    if ptrace_status_allows_io(status) != 0 {
        let Some(copy_from_user) = copy_from_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT as CLong;
        };
        rc = unsafe { copy_from_user(scratch, data as CULong, regs_size) };
        if rc == 0 {
            rc = unsafe {
                ptrace_write_user_words_result(child, scratch.cast::<CULong>(), regs_size, write_fn)
            };
        }
    }
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_fpregs_body_result(
    pid: CInt,
    data: CLong,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    io_fn: Option<PtraceFpregsIoFn>,
) -> CLong {
    if offsets.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let rc = unsafe { ptrace_fpregs_io_result(status, child, data as CULong, io_fn) };
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_regset_body_result(
    pid: CInt,
    regset_type: CLong,
    data: CLong,
    iovp: *mut u8,
    iov_size: SizeT,
    iov_len_offset: SizeT,
    iov_len_size: SizeT,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    copy_from_fn: Option<PtraceUserCopyFromFn>,
    io_fn: Option<PtraceRegsetIoFn>,
    copy_to_fn: Option<PtraceUserCopyToFn>,
) -> CLong {
    if offsets.is_null() || iovp.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let rc = unsafe {
        ptrace_regset_io_result(
            status,
            child,
            regset_type,
            data as CULong,
            iovp,
            iov_size,
            iov_len_offset,
            iov_len_size,
            copy_from_fn,
            io_fn,
            copy_to_fn,
        )
    };
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_peektext_body_result(
    pid: CInt,
    addr: CLong,
    data: CLong,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    read_fn: Option<PtraceReadVmWordFn>,
    copy_to_fn: Option<PtraceUserCopyToFn>,
    log_fn: Option<PtraceTextLogFn>,
) -> CLong {
    if offsets.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let vm = unsafe { ptrace_io_vm(child, offsets) };
    let mut value: CULong = 0;
    let mut rc =
        unsafe { ptrace_read_vm_word_result(status, vm, addr as CULong, &mut value, read_fn) };
    if rc != 0 {
        if ptrace_status_allows_io(status) != 0 {
            if let Some(log) = log_fn {
                unsafe { log(PTRACE_TEXT_LOG_PEEK_BAD_AREA, addr as CULong) };
            }
        }
    } else {
        let Some(copy_to_user) = copy_to_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT as CLong;
        };
        rc = unsafe {
            copy_to_user(
                data as CULong,
                (&value as *const CULong).cast::<u8>(),
                core::mem::size_of::<CULong>(),
            )
        };
    }
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_poketext_body_result(
    pid: CInt,
    addr: CLong,
    data: CLong,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    write_fn: Option<PtraceWriteVmWordFn>,
    log_fn: Option<PtraceTextLogFn>,
) -> CLong {
    if offsets.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let vm = unsafe { ptrace_io_vm(child, offsets) };
    let rc = unsafe {
        ptrace_write_vm_word_result(status, vm, addr as CULong, data as CULong, write_fn)
    };
    if rc != 0 && ptrace_status_allows_io(status) != 0 {
        if let Some(log) = log_fn {
            unsafe { log(PTRACE_TEXT_LOG_POKE_BAD_ADDRESS, addr as CULong) };
        }
    }
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_geteventmsg_body_result(
    pid: CInt,
    data: CLong,
    word_size: SizeT,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    copy_to_fn: Option<PtraceUserCopyToFn>,
) -> CLong {
    if offsets.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let mut eventmsg = unsafe { ptrace_io_eventmsg(child, offsets) };
    let mut rc = ptrace_eventmsg_prepare_result(status, eventmsg, &mut eventmsg) as CLong;
    if rc == 0 {
        let Some(copy_to_user) = copy_to_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT as CLong;
        };
        let copy_rc = unsafe {
            copy_to_user(
                data as CULong,
                (&eventmsg as *const CULong).cast::<u8>(),
                word_size,
            )
        };
        if copy_rc != 0 {
            rc = -EFAULT as CLong;
        }
    }
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_getsiginfo_body_result(
    pid: CInt,
    data: CULong,
    scratch: *mut u8,
    info_size: SizeT,
    info_offset: CULong,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    copy_to_fn: Option<PtraceUserCopyToFn>,
) -> CLong {
    if offsets.is_null() || scratch.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let pending = unsafe { ptrace_io_recvsig(child, offsets) };
    let mut rc = unsafe {
        ptrace_getsiginfo_prepare_result(status, pending, info_offset, scratch, info_size)
    } as CLong;
    if rc == 0 {
        let Some(copy_to_user) = copy_to_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT as CLong;
        };
        let copy_rc = unsafe { copy_to_user(data, scratch.cast::<u8>(), info_size) };
        if copy_rc != 0 {
            rc = -EFAULT as CLong;
        }
    }
    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_setsiginfo_body_result(
    pid: CInt,
    data: CULong,
    scratch: *mut u8,
    info_size: SizeT,
    pending_size: SizeT,
    alloc_flags: CULong,
    info_offset: CULong,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    alloc_fn: Option<SyscallPolicyAllocFn>,
    copy_from_fn: Option<PtraceUserCopyFromFn>,
) -> CLong {
    if offsets.is_null() || scratch.is_null() {
        return -EFAULT as CLong;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT as CLong;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT as CLong;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH as CLong;
    }

    let status = unsafe { ptrace_io_status(child, offsets) };
    let sendsig = unsafe { ptrace_io_sendsig(child, offsets) };
    let recvsig = unsafe { ptrace_io_recvsig(child, offsets) };
    let target =
        ptrace_setsiginfo_target_result(status, (sendsig != 0) as CInt, (recvsig != 0) as CInt);
    let mut rc = target as CLong;

    if target >= 0 {
        rc = 0;
        let sendsig_offset = unsafe { (*offsets).thread_ptrace_sendsig_offset as CULong };
        let recvsig_offset = unsafe { (*offsets).thread_ptrace_recvsig_offset as CULong };

        if (target & PTRACE_SIGINFO_ALLOC_SENDSIG) != 0 {
            let Some(alloc) = alloc_fn else {
                unsafe { unlock_thread(child) };
                return -EFAULT as CLong;
            };
            let allocated = unsafe { alloc(pending_size, alloc_flags) } as CULong;
            if allocated == 0 {
                rc = -ENOMEM as CLong;
            } else {
                rc = unsafe {
                    ptrace_setsiginfo_store_result(
                        child,
                        sendsig_offset,
                        recvsig_offset,
                        info_offset,
                        PTRACE_SIGINFO_ALLOC_SENDSIG,
                        allocated,
                        core::ptr::null(),
                        0,
                    )
                } as CLong;
            }
        }

        if rc == 0 && (target & PTRACE_SIGINFO_STORE_SENDSIG) != 0 {
            let Some(copy_from_user) = copy_from_fn else {
                unsafe { unlock_thread(child) };
                return -EFAULT as CLong;
            };
            let copy_rc = unsafe { copy_from_user(scratch, data, info_size) };
            if copy_rc != 0 {
                rc = -EFAULT as CLong;
            } else {
                rc = unsafe {
                    ptrace_setsiginfo_store_result(
                        child,
                        sendsig_offset,
                        recvsig_offset,
                        info_offset,
                        PTRACE_SIGINFO_STORE_SENDSIG,
                        0,
                        scratch.cast::<u8>(),
                        info_size,
                    )
                } as CLong;
            }
        }

        if rc == 0 && (target & PTRACE_SIGINFO_STORE_RECVSIG) != 0 {
            let Some(copy_from_user) = copy_from_fn else {
                unsafe { unlock_thread(child) };
                return -EFAULT as CLong;
            };
            let copy_rc = unsafe { copy_from_user(scratch, data, info_size) };
            if copy_rc != 0 {
                rc = -EFAULT as CLong;
            } else {
                rc = unsafe {
                    ptrace_setsiginfo_store_result(
                        child,
                        sendsig_offset,
                        recvsig_offset,
                        info_offset,
                        PTRACE_SIGINFO_STORE_RECVSIG,
                        0,
                        scratch.cast::<u8>(),
                        info_size,
                    )
                } as CLong;
            }
        }
    }

    unsafe { unlock_thread(child) };
    rc
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_wakeup_sig_body_result(
    pid: CInt,
    request: CLong,
    data: CLong,
    current_thread: CULong,
    info_offset: CULong,
    offsets: *const PtraceIoOffsets,
    lock_node: *mut c_void,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    log_fn: Option<PtraceControlLogFn>,
    clear_saved_fn: Option<PtraceSavedContextClearFn>,
    set_single_step_fn: Option<PtraceSetSingleStepFn>,
    lock_fn: Option<PtraceRwlockFn>,
    trace_syscall_update_fn: Option<PtraceTraceSyscallUpdateFn>,
    unlock_lock_fn: Option<PtraceRwlockFn>,
    take_pending_fn: Option<PtracePendingSignalTakeFn>,
    free_fn: Option<PtraceFreeFn>,
    do_kill_fn: Option<PtraceDoKillThreadFn>,
    wakeup_fn: Option<PtraceWakeupThreadFn>,
) -> CInt {
    if let Some(log) = log_fn {
        unsafe { log(PTRACE_CONTROL_LOG_WAKEUP_ENTER, pid, data as CInt) };
    }
    if offsets.is_null() || current_thread == 0 {
        return -EFAULT;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT;
    };
    let child = unsafe { find_thread(pid, pid) };
    if child == 0 {
        return -ESRCH;
    }

    let mut error = ptrace_signal_data_result(data);
    if error != 0 {
        unsafe { unlock_thread(child) };
        return error;
    }

    let action = ptrace_wakeup_request_action_result(request);
    if action == PTRACE_WAKEUP_ACTION_KILL || action == PTRACE_WAKEUP_ACTION_RESUME {
        let Some(clear_saved) = clear_saved_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT;
        };
        unsafe {
            clear_saved(
                child,
                (*offsets).thread_ptrace_saved_uctx_valid_offset as CULong,
            );
        }
    }

    if action == PTRACE_WAKEUP_ACTION_KILL {
        let Some(do_kill) = do_kill_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT;
        };
        let mut info_storage = MaybeUninit::<SigInfo>::uninit();
        let info_ptr = info_storage.as_mut_ptr();
        let raw = info_ptr.cast::<u8>();
        let mut offset = 0;
        while offset < size_of::<SigInfo>() {
            unsafe { raw.add(offset).write_volatile(0) };
            offset += 1;
        }
        let info = unsafe { &mut *info_ptr };
        info.si_signo = SIGKILL;
        error = unsafe {
            do_kill(
                current_thread as *mut c_void,
                pid,
                -1,
                SIGKILL,
                info as *const SigInfo,
                0,
            )
        } as CInt;
        if error < 0 {
            unsafe { unlock_thread(child) };
            return error;
        }
    } else if action == PTRACE_WAKEUP_ACTION_RESUME {
        if ptrace_resume_single_step_result(request) != 0 {
            let Some(set_single_step) = set_single_step_fn else {
                unsafe { unlock_thread(child) };
                return -EFAULT;
            };
            unsafe { set_single_step(child) };
        }

        let child_proc = unsafe { ptrace_io_proc(child, offsets) };
        if child_proc == 0 || lock_node.is_null() {
            unsafe { unlock_thread(child) };
            return -EFAULT;
        }
        let update_lock = unsafe { ptrace_io_proc_update_lock(child_proc, offsets) };
        let Some(lock_update) = lock_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT;
        };
        let Some(update_trace_syscall) = trace_syscall_update_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT;
        };
        let Some(unlock_update) = unlock_lock_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT;
        };
        unsafe { lock_update(update_lock, lock_node) };
        unsafe {
            update_trace_syscall(
                child,
                (*offsets).thread_ptrace_offset as CULong,
                ptrace_resume_trace_syscall_result(request),
            );
        }
        unsafe { unlock_update(update_lock, lock_node) };

        if ptrace_resume_signal_needed_result(request, data) != 0 {
            let Some(take_pending) = take_pending_fn else {
                unsafe { unlock_thread(child) };
                return -EFAULT;
            };
            let Some(do_kill) = do_kill_fn else {
                unsafe { unlock_thread(child) };
                return -EFAULT;
            };
            let source = ptrace_resume_signal_source_result(
                request,
                (unsafe { ptrace_io_sendsig(child, offsets) } != 0) as CInt,
                (unsafe { ptrace_io_recvsig(child, offsets) } != 0) as CInt,
            );
            let pending = unsafe {
                take_pending(
                    child,
                    (*offsets).thread_ptrace_sendsig_offset as CULong,
                    (*offsets).thread_ptrace_recvsig_offset as CULong,
                    source,
                )
            };
            let mut info_storage = MaybeUninit::<SigInfo>::uninit();
            let info_ptr = info_storage.as_mut_ptr();
            let raw = info_ptr.cast::<u8>();
            let mut offset = 0;
            while offset < size_of::<SigInfo>() {
                unsafe { raw.add(offset).write_volatile(0) };
                offset += 1;
            }
            if pending != 0 {
                let src = pending.wrapping_add(info_offset) as *const u8;
                let dst = info_ptr.cast::<u8>();
                let mut copy_offset = 0;
                while copy_offset < size_of::<SigInfo>() {
                    let byte = unsafe { read_volatile(src.add(copy_offset)) };
                    unsafe { dst.add(copy_offset).write_volatile(byte) };
                    copy_offset += 1;
                }
                let Some(free_pending) = free_fn else {
                    unsafe { unlock_thread(child) };
                    return -EFAULT;
                };
                unsafe { free_pending(pending as *mut c_void) };
            } else {
                let current_proc = unsafe { ptrace_io_proc(current_thread, offsets) };
                let tracer_pid = if current_proc != 0 {
                    unsafe { ptrace_io_proc_pid(current_proc, offsets) }
                } else {
                    0
                };
                let info = unsafe { &mut *info_ptr };
                info.si_signo = data as CInt;
                info.si_code = SI_USER;
                info.sifields.kill = ManuallyDrop::new(SigInfoKill {
                    si_pid: tracer_pid,
                    si_uid: 0,
                });
            }
            error = unsafe {
                do_kill(
                    current_thread as *mut c_void,
                    pid,
                    -1,
                    data as CInt,
                    info_ptr as *const SigInfo,
                    1,
                )
            } as CInt;
            if error < 0 {
                unsafe { unlock_thread(child) };
                return error;
            }
        }
    }

    let Some(wakeup_thread) = wakeup_fn else {
        unsafe { unlock_thread(child) };
        return -EFAULT;
    };
    unsafe { wakeup_thread(child as *mut c_void, PS_TRACED | PS_STOPPED) };
    unsafe { unlock_thread(child) };
    error
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_setoptions_body_result(
    pid: CInt,
    flags: CInt,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    log_fn: Option<PtraceControlLogFn>,
) -> CInt {
    let ret = ptrace_setoptions_flags_result(flags);
    if ret != 0 {
        if let Some(log) = log_fn {
            unsafe { log(PTRACE_CONTROL_LOG_SETOPTIONS_UNSUPPORTED, flags, ret) };
        }
        return ret;
    }
    if offsets.is_null() {
        return -EFAULT;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT;
    };
    let child = unsafe { find_thread(0, pid) };
    let proc_addr = if child != 0 {
        unsafe { ptrace_io_proc(child, offsets) }
    } else {
        0
    };
    let ptrace = if child != 0 {
        unsafe { ptrace_io_ptrace(child, offsets) }
    } else {
        0
    };

    let ret = ptrace_child_traced_result((child != 0) as CInt, (proc_addr != 0) as CInt, ptrace);
    if ret != 0 {
        if child != 0 {
            unsafe { unlock_thread(child) };
        }
        return ret;
    }

    let updated = unsafe {
        ptrace_setoptions_apply_thread_result(
            child,
            (*offsets).thread_ptrace_offset as CULong,
            flags,
        )
    };
    if let Some(log) = log_fn {
        unsafe { log(PTRACE_CONTROL_LOG_SETOPTIONS_APPLIED, flags, updated) };
    }
    unsafe { unlock_thread(child) };
    0
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_body_result(
    pid: CInt,
    data: CInt,
    current_proc: CULong,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    detach_fn: Option<PtraceDetachCallFn>,
) -> CInt {
    let error = ptrace_detach_signal_result(data as CLong);
    if error != 0 {
        return error;
    }
    if offsets.is_null() {
        return -EFAULT;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT;
    };
    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        return -ESRCH;
    }

    let ptrace = unsafe { ptrace_io_ptrace(child, offsets) };
    let report_proc = unsafe { ptrace_io_report_proc(child, offsets) };
    let error = ptrace_detach_state_result(
        ((ptrace & PT_TRACED) != 0) as CInt,
        (report_proc == current_proc) as CInt,
    );
    if error == 0 {
        let Some(detach_thread) = detach_fn else {
            unsafe { unlock_thread(child) };
            return -EFAULT;
        };
        unsafe { detach_thread(child, data) };
    }
    unsafe { unlock_thread(child) };
    error
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_attach_body_result(
    pid: CInt,
    current_thread: CULong,
    current_proc: CULong,
    offsets: *const PtraceIoOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    attach_fn: Option<PtraceAttachThreadFn>,
    do_kill_fn: Option<PtraceDoKillThreadFn>,
    log_fn: Option<PtraceControlLogFn>,
) -> CInt {
    if offsets.is_null() || current_thread == 0 || current_proc == 0 {
        return -EFAULT;
    }
    let Some(find_thread) = find_fn else {
        return -EFAULT;
    };
    let Some(unlock_thread) = unlock_fn else {
        return -EFAULT;
    };

    let child = unsafe { find_thread(0, pid) };
    if child == 0 {
        if let Some(log) = log_fn {
            unsafe { log(PTRACE_CONTROL_LOG_ATTACH_RETURN, pid, -ESRCH) };
        }
        return -ESRCH;
    }

    let tracer_pid = unsafe { ptrace_io_proc_pid(current_proc, offsets) };
    let child_proc = unsafe { ptrace_io_proc(child, offsets) };
    let child_ptrace = unsafe { ptrace_io_ptrace(child, offsets) };
    let mut error = ptrace_attach_policy_result(
        tracer_pid,
        pid,
        child_ptrace,
        (child_proc == current_proc) as CInt,
    );
    if error != 0 {
        unsafe { unlock_thread(child) };
        if let Some(log) = log_fn {
            unsafe { log(PTRACE_CONTROL_LOG_ATTACH_RETURN, pid, error) };
        }
        return error;
    }

    unsafe {
        ptrace_attach_mark_traced_result(child, (*offsets).thread_ptrace_offset as CULong);
    }
    let Some(attach_thread) = attach_fn else {
        unsafe { unlock_thread(child) };
        return -EFAULT;
    };
    let _attach_error = unsafe { attach_thread(child, current_proc) };
    unsafe { unlock_thread(child) };

    let Some(do_kill) = do_kill_fn else {
        return -EFAULT;
    };
    let mut info_storage = MaybeUninit::<SigInfo>::uninit();
    let info_ptr = info_storage.as_mut_ptr();
    let raw = info_ptr.cast::<u8>();
    let mut offset = 0;
    while offset < size_of::<SigInfo>() {
        unsafe { raw.add(offset).write_volatile(0) };
        offset += 1;
    }
    let info = unsafe { &mut *info_ptr };
    info.si_signo = SIGSTOP;
    info.si_code = SI_USER;
    info.sifields.kill = ManuallyDrop::new(SigInfoKill {
        si_pid: tracer_pid,
        si_uid: 0,
    });
    error = unsafe {
        do_kill(
            current_thread as *mut c_void,
            -1,
            pid,
            SIGSTOP,
            info as *const SigInfo,
            2,
        )
    } as CInt;
    if let Some(log) = log_fn {
        unsafe { log(PTRACE_CONTROL_LOG_ATTACH_RETURN, pid, error) };
    }
    error
}

#[no_mangle]
pub extern "C" fn ptrace_request_dispatch_result(request: CLong) -> CInt {
    if request == PTRACE_TRACEME {
        PTRACE_DISPATCH_TRACEME
    } else if request == PTRACE_KILL
        || request == PTRACE_CONT
        || request == PTRACE_SINGLESTEP
        || request == PTRACE_SYSCALL
    {
        PTRACE_DISPATCH_WAKEUP
    } else if request == PTRACE_GETREGS {
        PTRACE_DISPATCH_GETREGS
    } else if request == PTRACE_SETREGS {
        PTRACE_DISPATCH_SETREGS
    } else if request == PTRACE_GETFPREGS {
        PTRACE_DISPATCH_GETFPREGS
    } else if request == PTRACE_SETFPREGS {
        PTRACE_DISPATCH_SETFPREGS
    } else if request == PTRACE_PEEKUSER {
        PTRACE_DISPATCH_PEEKUSER
    } else if request == PTRACE_POKEUSER {
        PTRACE_DISPATCH_POKEUSER
    } else if request == PTRACE_PEEKTEXT || request == PTRACE_PEEKDATA {
        PTRACE_DISPATCH_PEEKTEXT
    } else if request == PTRACE_POKETEXT || request == PTRACE_POKEDATA {
        PTRACE_DISPATCH_POKETEXT
    } else if request == PTRACE_SETOPTIONS {
        PTRACE_DISPATCH_SETOPTIONS
    } else if request == PTRACE_ATTACH {
        PTRACE_DISPATCH_ATTACH
    } else if request == PTRACE_DETACH {
        PTRACE_DISPATCH_DETACH
    } else if request == PTRACE_GETSIGINFO {
        PTRACE_DISPATCH_GETSIGINFO
    } else if request == PTRACE_SETSIGINFO {
        PTRACE_DISPATCH_SETSIGINFO
    } else if request == PTRACE_GETREGSET {
        PTRACE_DISPATCH_GETREGSET
    } else if request == PTRACE_SETREGSET {
        PTRACE_DISPATCH_SETREGSET
    } else if request == PTRACE_GETEVENTMSG {
        PTRACE_DISPATCH_GETEVENTMSG
    } else {
        PTRACE_DISPATCH_ARCH
    }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_syscall_body_result(
    request: CLong,
    pid: CInt,
    addr: CLong,
    data: CLong,
    ops: *const PtraceSyscallOps,
) -> CLong {
    if ops.is_null() {
        return -(EOPNOTSUPP as CLong);
    }

    let ops = unsafe { &*ops };
    match ptrace_request_dispatch_result(request) {
        PTRACE_DISPATCH_TRACEME => match ops.traceme_fn {
            Some(traceme) => unsafe { traceme() as CLong },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_WAKEUP => match ops.wakeup_fn {
            Some(wakeup) => unsafe { wakeup(pid, request, data) as CLong },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_GETREGS => match ops.getregs_fn {
            Some(getregs) => unsafe { getregs(pid, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_SETREGS => match ops.setregs_fn {
            Some(setregs) => unsafe { setregs(pid, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_GETFPREGS => match ops.getfpregs_fn {
            Some(getfpregs) => unsafe { getfpregs(pid, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_SETFPREGS => match ops.setfpregs_fn {
            Some(setfpregs) => unsafe { setfpregs(pid, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_PEEKUSER => match ops.peekuser_fn {
            Some(peekuser) => unsafe { peekuser(pid, addr, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_POKEUSER => match ops.pokeuser_fn {
            Some(pokeuser) => unsafe { pokeuser(pid, addr, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_PEEKTEXT => match ops.peektext_fn {
            Some(peektext) => unsafe { peektext(pid, addr, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_POKETEXT => match ops.poketext_fn {
            Some(poketext) => unsafe { poketext(pid, addr, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_SETOPTIONS => match ops.setoptions_fn {
            Some(setoptions) => unsafe { setoptions(pid, data as CInt) as CLong },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_ATTACH => match ops.attach_fn {
            Some(attach) => unsafe { attach(pid) as CLong },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_DETACH => match ops.detach_fn {
            Some(detach) => unsafe { detach(pid, data as CInt) as CLong },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_GETSIGINFO => match ops.getsiginfo_fn {
            Some(getsiginfo) => unsafe { getsiginfo(pid, data as *mut c_void) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_SETSIGINFO => match ops.setsiginfo_fn {
            Some(setsiginfo) => unsafe { setsiginfo(pid, data as *mut c_void) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_GETREGSET => match ops.getregset_fn {
            Some(getregset) => unsafe { getregset(pid, addr, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_SETREGSET => match ops.setregset_fn {
            Some(setregset) => unsafe { setregset(pid, addr, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        PTRACE_DISPATCH_GETEVENTMSG => match ops.geteventmsg_fn {
            Some(geteventmsg) => unsafe { geteventmsg(pid, data) },
            None => -(EOPNOTSUPP as CLong),
        },
        _ => match ops.arch_fn {
            Some(arch) => unsafe { arch(request, pid, addr, data) },
            None => -(EOPNOTSUPP as CLong),
        },
    }
}

#[no_mangle]
pub extern "C" fn wait4_options_result(options: CInt) -> CInt {
    let allowed = WNOHANG | WUNTRACED | WCONTINUED | __WCLONE | __WALL;

    if (options & !allowed) != 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn waitid_to_wait_pid_result(
    idtype: CInt,
    id: CInt,
    pidp: *mut CInt,
) -> CInt {
    let pid = if idtype == P_PID {
        id
    } else if idtype == P_PGID {
        id.wrapping_neg()
    } else if idtype == P_ALL {
        -1
    } else {
        return -EINVAL;
    };

    write(pidp, pid);
    0
}

#[no_mangle]
pub extern "C" fn waitid_options_result(options: CInt) -> CInt {
    let allowed = WEXITED | WSTOPPED | WCONTINUED | WNOHANG | WNOWAIT | __WCLONE | __WALL;

    if (options & !allowed) != 0 {
        return -EINVAL;
    }

    if (options & (WEXITED | WSTOPPED | WCONTINUED)) == 0 {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn wait_should_scan_process_result(options: CInt) -> CInt {
    if (options & __WCLONE) == 0 { 1 } else { 0 }
}

#[no_mangle]
pub extern "C" fn wait_should_scan_thread_result(pid: CInt, options: CInt) -> CInt {
    if (pid == -1 || pid > 0) && (options & (__WCLONE | __WALL)) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_process_pid_matches_result(
    pid: CInt,
    parent_pgid: CInt,
    child_pgid: CInt,
    child_pid: CInt,
) -> CInt {
    if pid == -1 {
        return 1;
    }

    if pid < 0 {
        return if pid.wrapping_neg() == child_pgid {
            1
        } else {
            0
        };
    }

    if pid == 0 {
        return if parent_pgid == child_pgid { 1 } else { 0 };
    }

    if pid == child_pid { 1 } else { 0 }
}

#[no_mangle]
pub extern "C" fn wait_thread_tid_matches_result(
    tid: CInt,
    child_tid: CInt,
    is_main_thread: CInt,
) -> CInt {
    if is_main_thread != 0 {
        return 0;
    }

    if tid == -1 || child_tid == tid { 1 } else { 0 }
}

#[no_mangle]
pub extern "C" fn wait_process_exited_candidate_result(options: CInt, child_status: CInt) -> CInt {
    if (options & WEXITED) != 0 && child_status == PS_ZOMBIE {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_thread_exited_candidate_result(options: CInt, child_status: CInt) -> CInt {
    if (options & WEXITED) != 0 && (child_status == PS_EXITED || child_status == PS_ZOMBIE) {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_nonptraced_stop_candidate_result(
    ptrace: CInt,
    signal_flags: CInt,
    options: CInt,
) -> CInt {
    if (ptrace & PT_TRACED) == 0
        && (signal_flags & SIGNAL_STOP_STOPPED) != 0
        && (options & WUNTRACED) != 0
    {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_ptraced_stop_candidate_result(ptrace: CInt, status: CInt) -> CInt {
    if (ptrace & PT_TRACED) != 0 && (status & (PS_STOPPED | PS_TRACED | PS_DELAY_TRACED)) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_continued_candidate_result(signal_flags: CInt, options: CInt) -> CInt {
    if (signal_flags & SIGNAL_STOP_CONTINUED) != 0 && (options & WCONTINUED) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_reap_needed_result(options: CInt) -> CInt {
    if (options & WNOWAIT) == 0 { 1 } else { 0 }
}

#[no_mangle]
pub extern "C" fn wait_nohang_result(options: CInt) -> CInt {
    if (options & WNOHANG) != 0 { 1 } else { 0 }
}

#[no_mangle]
pub extern "C" fn wait_empty_result(empty: CInt) -> CInt {
    if empty != 0 { -ECHILD } else { 0 }
}

#[no_mangle]
pub extern "C" fn wait_stopped_status_result(exit_status: CInt) -> CInt {
    (exit_status << 8) | 0x7f
}

#[no_mangle]
pub extern "C" fn wait_continued_status_result() -> CInt {
    0xffff
}

#[no_mangle]
pub unsafe extern "C" fn wait_continued_body_result(
    c_thread: *mut c_void,
    child: *mut c_void,
    status: *mut CInt,
    options: CInt,
    child_pid_offset: CULong,
    child_main_thread_offset: CULong,
    thread_tid_offset: CULong,
    thread_signal_flags_offset: CULong,
    reap_fn: WaitSignalFlagsReapFn,
) -> CInt {
    if !status.is_null() {
        write(status, wait_continued_status_result());
    }

    let target_thread = if c_thread.is_null() {
        *child
            .cast::<u8>()
            .wrapping_add(child_main_thread_offset as usize)
            .cast::<*mut c_void>()
    } else {
        c_thread
    };
    reap_fn(
        target_thread,
        thread_signal_flags_offset,
        options,
        SIGNAL_STOP_CONTINUED,
    );

    if c_thread.is_null() {
        *child
            .cast::<u8>()
            .wrapping_add(child_pid_offset as usize)
            .cast::<CInt>()
    } else {
        *c_thread
            .cast::<u8>()
            .wrapping_add(thread_tid_offset as usize)
            .cast::<CInt>()
    }
}

#[no_mangle]
pub unsafe extern "C" fn wait_stopped_body_result(
    c_thread: *mut c_void,
    child: *mut c_void,
    status: *mut CInt,
    options: CInt,
    child_pid_offset: CULong,
    child_status_offset: CULong,
    child_group_exit_status_offset: CULong,
    child_main_thread_offset: CULong,
    thread_tid_offset: CULong,
    thread_exit_status_offset: CULong,
    reap_fn: Option<WaitExitStatusReapFn>,
) -> CInt {
    if child.is_null() {
        return -EINVAL;
    }

    let c_thread_exit_status = if c_thread.is_null() {
        0
    } else {
        read_volatile(
            c_thread
                .cast::<u8>()
                .wrapping_add(thread_exit_status_offset as usize)
                .cast::<CInt>(),
        )
    };
    let child_status = read_volatile(
        child
            .cast::<u8>()
            .wrapping_add(child_status_offset as usize)
            .cast::<CInt>(),
    );
    let child_group_exit_status = read_volatile(
        child
            .cast::<u8>()
            .wrapping_add(child_group_exit_status_offset as usize)
            .cast::<CInt>(),
    );
    let main_thread = read_volatile(
        child
            .cast::<u8>()
            .wrapping_add(child_main_thread_offset as usize)
            .cast::<*mut c_void>(),
    );
    let main_thread_exit_status = if main_thread.is_null() {
        0
    } else {
        read_volatile(
            main_thread
                .cast::<u8>()
                .wrapping_add(thread_exit_status_offset as usize)
                .cast::<CInt>(),
        )
    };
    let source = wait_stopped_source_result(
        (!c_thread.is_null()) as CInt,
        c_thread_exit_status,
        child_status,
        child_group_exit_status,
        main_thread_exit_status,
    );
    if source == WAIT_STOP_SOURCE_NONE {
        return 0;
    }

    let exit_status = wait_stopped_exit_status_result(
        source,
        c_thread_exit_status,
        child_group_exit_status,
        main_thread_exit_status,
    );
    if !status.is_null() {
        write(status, wait_stopped_status_result(exit_status));
    }

    let Some(reap_fn) = reap_fn else {
        return -EINVAL;
    };
    match source {
        WAIT_STOP_SOURCE_THREAD => {
            reap_fn(c_thread, thread_exit_status_offset, options);
        }
        WAIT_STOP_SOURCE_PROCESS => {
            reap_fn(child, child_group_exit_status_offset, options);
        }
        WAIT_STOP_SOURCE_MAIN_THREAD => {
            reap_fn(main_thread, thread_exit_status_offset, options);
        }
        _ => {}
    }

    let child_pid = read_volatile(
        child
            .cast::<u8>()
            .wrapping_add(child_pid_offset as usize)
            .cast::<CInt>(),
    );
    let c_thread_tid = if c_thread.is_null() {
        0
    } else {
        read_volatile(
            c_thread
                .cast::<u8>()
                .wrapping_add(thread_tid_offset as usize)
                .cast::<CInt>(),
        )
    };
    wait_report_id_result(source, child_pid, c_thread_tid)
}

#[no_mangle]
pub unsafe extern "C" fn do_wait_body_result(
    mut pid: CInt,
    status: *mut CInt,
    options: CInt,
    rusage: *mut c_void,
    thread: *mut c_void,
    wait_entry: *mut c_void,
    thread_proc_offset: CULong,
    proc_pid_offset: CULong,
    proc_waitpid_q_offset: CULong,
    interruptible_status: CInt,
    wait_proc_fn: Option<WaitScanFn>,
    wait_thread_fn: Option<WaitScanFn>,
    init_fn: Option<WaitEntryInitFn>,
    prepare_fn: Option<WaitPrepareFn>,
    finish_fn: Option<WaitFinishFn>,
    has_signal_fn: Option<WaitHasSignalFn>,
    schedule_fn: Option<WaitScheduleFn>,
    log_fn: Option<WaitLogFn>,
) -> CInt {
    if thread.is_null() || wait_entry.is_null() || status.is_null() {
        return -EINVAL;
    }

    let Some(wait_proc_fn) = wait_proc_fn else {
        return -EINVAL;
    };
    let Some(wait_thread_fn) = wait_thread_fn else {
        return -EINVAL;
    };
    let Some(init_fn) = init_fn else {
        return -EINVAL;
    };
    let Some(prepare_fn) = prepare_fn else {
        return -EINVAL;
    };
    let Some(finish_fn) = finish_fn else {
        return -EINVAL;
    };
    let Some(has_signal_fn) = has_signal_fn else {
        return -EINVAL;
    };
    let Some(schedule_fn) = schedule_fn else {
        return -EINVAL;
    };
    let Some(log_fn) = log_fn else {
        return -EINVAL;
    };

    let proc = *thread
        .cast::<u8>()
        .wrapping_add(thread_proc_offset as usize)
        .cast::<*mut c_void>();
    if proc.is_null() {
        return -EINVAL;
    }

    let waitq = proc
        .cast::<u8>()
        .wrapping_add(proc_waitpid_q_offset as usize)
        .cast::<c_void>();
    let current_pid = *proc
        .cast::<u8>()
        .wrapping_add(proc_pid_offset as usize)
        .cast::<CInt>();
    let orgpid = pid;
    let mut empty: CInt = 1;

    log_fn(WAIT_LOG_ENTER, current_pid, pid);

    loop {
        init_fn(wait_entry, thread);
        prepare_fn(waitq, wait_entry, interruptible_status);
        pid = orgpid;

        if wait_should_scan_process_result(options) != 0 {
            let ret = wait_proc_fn(pid, status, options, rusage, &mut empty as *mut CInt);
            if ret != 0 {
                log_fn(WAIT_LOG_FOUND, current_pid, pid);
                finish_fn(waitq, wait_entry);
                return ret;
            }
        }

        if wait_should_scan_thread_result(pid, options) != 0 {
            let ret = wait_thread_fn(pid, status, options, rusage, &mut empty as *mut CInt);
            if ret != 0 {
                log_fn(WAIT_LOG_FOUND, current_pid, pid);
                finish_fn(waitq, wait_entry);
                return ret;
            }
        }

        let ret = wait_empty_result(empty);
        if ret != 0 {
            log_fn(WAIT_LOG_NOTFOUND, current_pid, pid);
            finish_fn(waitq, wait_entry);
            return ret;
        }

        if wait_nohang_result(options) != 0 {
            write(status, 0);
            log_fn(WAIT_LOG_NOTFOUND, current_pid, pid);
            finish_fn(waitq, wait_entry);
            return 0;
        }

        log_fn(WAIT_LOG_SLEEPING, current_pid, pid);

        if has_signal_fn(thread) != 0 {
            finish_fn(waitq, wait_entry);
            return -EINTR;
        }

        schedule_fn();
        log_fn(WAIT_LOG_WOKEN, current_pid, pid);
        finish_fn(waitq, wait_entry);
    }
}

#[no_mangle]
pub unsafe extern "C" fn wait_process_candidate_body_result(
    current_ret: CInt,
    pid: CInt,
    status: *mut CInt,
    options: CInt,
    thread: *mut c_void,
    child_proc: *mut c_void,
    child_thread: *mut c_void,
    parent_children_lock: *mut c_void,
    parent_children_lock_node: *mut c_void,
    child_threads_lock: *mut c_void,
    child_threads_lock_node: *mut c_void,
    child_pid_offset: CULong,
    child_status_offset: CULong,
    thread_tid_offset: CULong,
    thread_ptrace_offset: CULong,
    thread_signal_flags_offset: CULong,
    stopped_fn: Option<WaitStatusFn>,
    continued_fn: Option<WaitStatusFn>,
    reap_fn: Option<WaitSignalFlagsReapFn>,
    unlock_fn: Option<WaitLockUnlockFn>,
    foundp: *mut CInt,
) -> CInt {
    if foundp.is_null() {
        return -EINVAL;
    }
    write(foundp, 0);
    if thread.is_null() || child_proc.is_null() || child_thread.is_null() || status.is_null() {
        return current_ret;
    }
    let Some(stopped_fn) = stopped_fn else {
        return -EINVAL;
    };
    let Some(continued_fn) = continued_fn else {
        return -EINVAL;
    };
    let Some(reap_fn) = reap_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };

    let child_pid = *child_proc
        .cast::<u8>()
        .wrapping_add(child_pid_offset as usize)
        .cast::<CInt>();
    let child_status = *child_proc
        .cast::<u8>()
        .wrapping_add(child_status_offset as usize)
        .cast::<CInt>();
    let child_tid = *child_thread
        .cast::<u8>()
        .wrapping_add(thread_tid_offset as usize)
        .cast::<CInt>();
    let child_ptrace = *child_thread
        .cast::<u8>()
        .wrapping_add(thread_ptrace_offset as usize)
        .cast::<CInt>();
    let signal_flags = *child_thread
        .cast::<u8>()
        .wrapping_add(thread_signal_flags_offset as usize)
        .cast::<CInt>();

    if wait_nonptraced_stop_candidate_result(child_ptrace, signal_flags, options) != 0 {
        let ret = stopped_fn(thread, child_proc, core::ptr::null_mut(), status, options);
        reap_fn(
            child_thread,
            thread_signal_flags_offset,
            options,
            SIGNAL_STOP_STOPPED,
        );
        unlock_fn(parent_children_lock, parent_children_lock_node);
        unlock_fn(child_threads_lock, child_threads_lock_node);
        write(foundp, 1);
        return ret;
    }

    let mut ret = current_ret;
    if wait_ptraced_stop_candidate_result(child_ptrace, child_status) != 0 {
        ret = stopped_fn(thread, child_proc, core::ptr::null_mut(), status, options);
        if ret == child_pid {
            let out = if pid == child_tid { child_tid } else { ret };
            reap_fn(
                child_thread,
                thread_signal_flags_offset,
                options,
                SIGNAL_STOP_STOPPED,
            );
            unlock_fn(parent_children_lock, parent_children_lock_node);
            unlock_fn(child_threads_lock, child_threads_lock_node);
            write(foundp, 1);
            return out;
        }
    }

    if wait_continued_candidate_result(signal_flags, options) != 0 {
        ret = continued_fn(thread, child_proc, core::ptr::null_mut(), status, options);
        reap_fn(
            child_thread,
            thread_signal_flags_offset,
            options,
            SIGNAL_STOP_CONTINUED,
        );
        unlock_fn(parent_children_lock, parent_children_lock_node);
        unlock_fn(child_threads_lock, child_threads_lock_node);
        write(foundp, 1);
    }

    ret
}

#[no_mangle]
pub unsafe extern "C" fn wait_thread_candidate_body_result(
    current_ret: CInt,
    _tid: CInt,
    status: *mut CInt,
    options: CInt,
    thread: *mut c_void,
    child_thread: *mut c_void,
    threads_lock: *mut c_void,
    threads_lock_node: *mut c_void,
    thread_proc_offset: CULong,
    thread_tid_offset: CULong,
    thread_status_offset: CULong,
    thread_ptrace_offset: CULong,
    thread_signal_flags_offset: CULong,
    stopped_fn: Option<WaitStatusFn>,
    continued_fn: Option<WaitStatusFn>,
    reap_fn: Option<WaitSignalFlagsReapFn>,
    unlock_fn: Option<WaitLockUnlockFn>,
    report_detach_fn: Option<WaitThreadReportDetachFn>,
    ptrace_detach_fn: Option<WaitThreadSideEffectFn>,
    release_fn: Option<WaitThreadSideEffectFn>,
    foundp: *mut CInt,
) -> CInt {
    if foundp.is_null() {
        return -EINVAL;
    }
    write(foundp, 0);
    if thread.is_null() || child_thread.is_null() || status.is_null() {
        return current_ret;
    }
    let Some(stopped_fn) = stopped_fn else {
        return -EINVAL;
    };
    let Some(continued_fn) = continued_fn else {
        return -EINVAL;
    };
    let Some(reap_fn) = reap_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(report_detach_fn) = report_detach_fn else {
        return -EINVAL;
    };
    let Some(ptrace_detach_fn) = ptrace_detach_fn else {
        return -EINVAL;
    };
    let Some(release_fn) = release_fn else {
        return -EINVAL;
    };

    let child_proc = *child_thread
        .cast::<u8>()
        .wrapping_add(thread_proc_offset as usize)
        .cast::<*mut c_void>();
    let child_tid = *child_thread
        .cast::<u8>()
        .wrapping_add(thread_tid_offset as usize)
        .cast::<CInt>();
    let child_status = *child_thread
        .cast::<u8>()
        .wrapping_add(thread_status_offset as usize)
        .cast::<CInt>();
    let child_ptrace = *child_thread
        .cast::<u8>()
        .wrapping_add(thread_ptrace_offset as usize)
        .cast::<CInt>();
    let signal_flags = *child_thread
        .cast::<u8>()
        .wrapping_add(thread_signal_flags_offset as usize)
        .cast::<CInt>();

    if wait_thread_exited_candidate_result(options, child_status) != 0 {
        let action = wait_thread_reap_action_result(options, child_ptrace);
        if action == WAIT_THREAD_REAP_ACTION_PTRACE_DETACH {
            unlock_fn(threads_lock, threads_lock_node);
            ptrace_detach_fn(child_thread);
        } else if action == WAIT_THREAD_REAP_ACTION_RELEASE {
            report_detach_fn(child_thread);
            unlock_fn(threads_lock, threads_lock_node);
            release_fn(child_thread);
        } else {
            unlock_fn(threads_lock, threads_lock_node);
        }
        write(foundp, 1);
        return child_tid;
    }

    if wait_nonptraced_stop_candidate_result(child_ptrace, signal_flags, options) != 0 {
        let ret = stopped_fn(thread, child_proc, child_thread, status, options);
        reap_fn(
            child_thread,
            thread_signal_flags_offset,
            options,
            SIGNAL_STOP_STOPPED,
        );
        unlock_fn(threads_lock, threads_lock_node);
        write(foundp, 1);
        return ret;
    }

    let mut ret = current_ret;
    if wait_ptraced_stop_candidate_result(child_ptrace, child_status) != 0 {
        ret = stopped_fn(thread, child_proc, child_thread, status, options);
        if ret == child_tid {
            reap_fn(
                child_thread,
                thread_signal_flags_offset,
                options,
                SIGNAL_STOP_STOPPED,
            );
            unlock_fn(threads_lock, threads_lock_node);
            write(foundp, 1);
            return ret;
        }
    }

    if wait_continued_candidate_result(signal_flags, options) != 0 {
        ret = continued_fn(thread, child_proc, child_thread, status, options);
        reap_fn(
            child_thread,
            thread_signal_flags_offset,
            options,
            SIGNAL_STOP_CONTINUED,
        );
        unlock_fn(threads_lock, threads_lock_node);
        write(foundp, 1);
    }

    ret
}

unsafe fn wait_process_fill_rusage(
    child_proc: *mut u8,
    usage: *mut c_void,
    offsets: &WaitZombieOffsets,
) {
    if usage.is_null() {
        return;
    }
    let utime = read_timespec(child_proc, offsets.proc_utime_offset);
    let stime = read_timespec(child_proc, offsets.proc_stime_offset);
    let maxrss = read_volatile(field_ptr::<CLong>(child_proc, offsets.proc_maxrss_offset));
    getrusage_fill_timespec_result(
        usage.cast::<RUsage>(),
        utime.tv_sec,
        utime.tv_nsec,
        stime.tv_sec,
        stime.tv_nsec,
        maxrss,
    );
}

unsafe fn wait_process_accumulate_child_rusage(
    parent_proc: *mut u8,
    child_proc: *mut u8,
    offsets: &WaitZombieOffsets,
) {
    let mut stime_children = read_timespec(parent_proc, offsets.proc_stime_children_offset);
    let child_stime = read_timespec(child_proc, offsets.proc_stime_offset);
    let child_stime_children = read_timespec(child_proc, offsets.proc_stime_children_offset);
    timespec_add(&mut stime_children, &child_stime);
    timespec_add(&mut stime_children, &child_stime_children);
    write_timespec(
        parent_proc,
        offsets.proc_stime_children_offset,
        &stime_children,
    );

    let mut utime_children = read_timespec(parent_proc, offsets.proc_utime_children_offset);
    let child_utime = read_timespec(child_proc, offsets.proc_utime_offset);
    let child_utime_children = read_timespec(child_proc, offsets.proc_utime_children_offset);
    timespec_add(&mut utime_children, &child_utime);
    timespec_add(&mut utime_children, &child_utime_children);
    write_timespec(
        parent_proc,
        offsets.proc_utime_children_offset,
        &utime_children,
    );

    let maxrss_ptr = field_ptr::<CLong>(parent_proc, offsets.proc_maxrss_children_offset);
    let mut maxrss_children = read_volatile(maxrss_ptr);
    let child_maxrss = read_volatile(field_ptr::<CLong>(child_proc, offsets.proc_maxrss_offset));
    if child_maxrss > maxrss_children {
        maxrss_children = child_maxrss;
        write_volatile(maxrss_ptr, maxrss_children);
    }
    let child_maxrss_children = read_volatile(field_ptr::<CLong>(
        child_proc,
        offsets.proc_maxrss_children_offset,
    ));
    if child_maxrss_children > maxrss_children {
        write_volatile(maxrss_ptr, child_maxrss_children);
    }
}

#[no_mangle]
pub unsafe extern "C" fn wait_process_zombie_body_result(
    thread: *mut c_void,
    parent_proc: *mut c_void,
    child_proc: *mut c_void,
    status: *mut CInt,
    options: CInt,
    rusage: *mut c_void,
    parent_children_lock: *mut c_void,
    parent_children_lock_node: *mut c_void,
    pid1: *mut c_void,
    offsets: *const WaitZombieOffsets,
    host_wait4_fn: Option<WaitHostWait4Fn>,
    lock_fn: Option<WaitLockUnlockFn>,
    unlock_fn: Option<WaitLockUnlockFn>,
    list_detach_fn: Option<WaitListDetachFn>,
    list_add_tail_fn: Option<WaitListAddTailFn>,
    ptrace_detach_fn: Option<WaitThreadSideEffectFn>,
    release_process_fn: Option<WaitThreadSideEffectFn>,
    log_fn: Option<WaitZombieLogFn>,
    parent_update_lock_node: *mut c_void,
    child_update_lock_node: *mut c_void,
    pid1_children_lock_node: *mut c_void,
    child_threads_lock_node: *mut c_void,
) -> CInt {
    let Some(host_wait4_fn) = host_wait4_fn else {
        return -EINVAL;
    };
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(list_detach_fn) = list_detach_fn else {
        return -EINVAL;
    };
    let Some(list_add_tail_fn) = list_add_tail_fn else {
        return -EINVAL;
    };
    let Some(ptrace_detach_fn) = ptrace_detach_fn else {
        return -EINVAL;
    };
    let Some(release_process_fn) = release_process_fn else {
        return -EINVAL;
    };
    let Some(log_fn) = log_fn else {
        return -EINVAL;
    };
    if thread.is_null()
        || parent_proc.is_null()
        || child_proc.is_null()
        || offsets.is_null()
        || parent_children_lock.is_null()
        || parent_children_lock_node.is_null()
        || child_threads_lock_node.is_null()
    {
        return -EINVAL;
    }

    let offsets = &*offsets;
    let parent = parent_proc.cast::<u8>();
    let child = child_proc.cast::<u8>();
    let child_pid = read_volatile(field_ptr::<CInt>(child, offsets.proc_pid_offset));
    let group_exit_status = read_volatile(field_ptr::<CInt>(
        child,
        offsets.proc_group_exit_status_offset,
    ));
    let nowait = read_volatile(field_ptr::<CInt>(child, offsets.proc_nowait_offset));
    let current_pid = read_volatile(field_ptr::<CInt>(parent, offsets.proc_pid_offset));
    let ppid_parent = *field_ptr::<*mut u8>(child, offsets.proc_ppid_parent_offset);
    let parent_field = *field_ptr::<*mut u8>(child, offsets.proc_parent_offset);
    let ppid_parent_pid = if ppid_parent.is_null() {
        0
    } else {
        read_volatile(field_ptr::<CInt>(ppid_parent, offsets.proc_pid_offset))
    };

    log_fn(WAIT_ZOMBIE_LOG_FOUND, child_pid, 0, 0);
    if !status.is_null() {
        write_volatile(status, group_exit_status);
    }

    let ret = if wait_zombie_skip_host_result(ppid_parent_pid, current_pid, nowait) != 0 {
        child_pid
    } else {
        host_wait4_fn(child_pid, options)
    };
    if ret != child_pid {
        log_fn(WAIT_ZOMBIE_LOG_WARNING, child_pid, 0, ret);
    }
    log_fn(
        WAIT_ZOMBIE_LOG_STATUS,
        child_pid,
        if status.is_null() {
            -1
        } else {
            read_volatile(status)
        },
        ret,
    );

    let reparent_needed =
        wait_process_reparent_needed_result(options, (parent_field == ppid_parent) as CInt) != 0;
    if reparent_needed {
        if pid1.is_null()
            || parent_update_lock_node.is_null()
            || child_update_lock_node.is_null()
            || pid1_children_lock_node.is_null()
        {
            return -EINVAL;
        }
        let pid1 = pid1.cast::<u8>();
        let parent_update_lock = field_ptr::<c_void>(parent, offsets.proc_update_lock_offset);
        let child_update_lock = field_ptr::<c_void>(child, offsets.proc_update_lock_offset);
        let pid1_children_lock = field_ptr::<c_void>(pid1, offsets.proc_children_lock_offset);
        let child_threads_lock = field_ptr::<c_void>(child, offsets.proc_threads_lock_offset);
        let child_siblings = field_ptr::<c_void>(child, offsets.proc_siblings_list_offset);
        let pid1_children = field_ptr::<c_void>(pid1, offsets.proc_children_list_offset);

        lock_fn(parent_update_lock, parent_update_lock_node);
        wait_process_accumulate_child_rusage(parent, child, offsets);
        wait_process_fill_rusage(child, rusage, offsets);
        unlock_fn(parent_update_lock, parent_update_lock_node);

        list_detach_fn(child_siblings);
        unlock_fn(parent_children_lock, parent_children_lock_node);

        lock_fn(child_update_lock, child_update_lock_node);
        write_volatile(
            field_ptr::<*mut u8>(child, offsets.proc_parent_offset),
            pid1,
        );
        write_volatile(
            field_ptr::<*mut u8>(child, offsets.proc_ppid_parent_offset),
            pid1,
        );
        lock_fn(pid1_children_lock, pid1_children_lock_node);
        list_add_tail_fn(child_siblings, pid1_children);
        unlock_fn(pid1_children_lock, pid1_children_lock_node);
        unlock_fn(child_update_lock, child_update_lock_node);

        lock_fn(child_threads_lock, child_threads_lock_node);
        let main_thread = *field_ptr::<*mut u8>(child, offsets.proc_main_thread_offset);
        if !main_thread.is_null()
            && wait_main_thread_ptrace_detach_needed_result(
                options,
                read_volatile(field_ptr::<CInt>(main_thread, offsets.thread_ptrace_offset)),
            ) != 0
        {
            unlock_fn(child_threads_lock, child_threads_lock_node);
            ptrace_detach_fn(main_thread.cast::<c_void>());
        } else {
            unlock_fn(child_threads_lock, child_threads_lock_node);
        }
        release_process_fn(child_proc);
    } else {
        let child_threads_lock = field_ptr::<c_void>(child, offsets.proc_threads_lock_offset);

        lock_fn(child_threads_lock, child_threads_lock_node);
        let main_thread = *field_ptr::<*mut u8>(child, offsets.proc_main_thread_offset);
        if !main_thread.is_null()
            && wait_main_thread_ptrace_detach_needed_result(
                options,
                read_volatile(field_ptr::<CInt>(main_thread, offsets.thread_ptrace_offset)),
            ) != 0
        {
            unlock_fn(child_threads_lock, child_threads_lock_node);
            unlock_fn(parent_children_lock, parent_children_lock_node);
            ptrace_detach_fn(main_thread.cast::<c_void>());
        } else {
            unlock_fn(child_threads_lock, child_threads_lock_node);
            unlock_fn(parent_children_lock, parent_children_lock_node);
        }
    }

    ret
}

unsafe fn wait_list_head(base: *mut u8, offset: SizeT) -> *mut AbiListHead {
    field_ptr::<AbiListHead>(base, offset)
}

unsafe fn wait_list_entry(node: *mut AbiListHead, offset: SizeT) -> *mut u8 {
    (node as *mut u8).wrapping_sub(offset)
}

#[no_mangle]
pub unsafe extern "C" fn wait_process_scan_body_result(
    pid: CInt,
    status: *mut CInt,
    options: CInt,
    rusage: *mut c_void,
    empty: *mut CInt,
    thread: *mut c_void,
    proc: *mut c_void,
    pid1: *mut c_void,
    scan_offsets: *const WaitScanOffsets,
    zombie_offsets: *const WaitZombieOffsets,
    lock_fn: Option<WaitLockUnlockFn>,
    unlock_fn: Option<WaitLockUnlockFn>,
    host_wait4_fn: Option<WaitHostWait4Fn>,
    list_detach_fn: Option<WaitListDetachFn>,
    list_add_tail_fn: Option<WaitListAddTailFn>,
    ptrace_detach_fn: Option<WaitThreadSideEffectFn>,
    release_process_fn: Option<WaitThreadSideEffectFn>,
    zombie_log_fn: Option<WaitZombieLogFn>,
    stopped_fn: Option<WaitStatusFn>,
    continued_fn: Option<WaitStatusFn>,
    reap_fn: Option<WaitSignalFlagsReapFn>,
    parent_children_lock_node: *mut c_void,
    child_threads_lock_node: *mut c_void,
    parent_update_lock_node: *mut c_void,
    child_update_lock_node: *mut c_void,
    pid1_children_lock_node: *mut c_void,
) -> CInt {
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    if empty.is_null()
        || thread.is_null()
        || proc.is_null()
        || pid1.is_null()
        || scan_offsets.is_null()
        || zombie_offsets.is_null()
        || host_wait4_fn.is_none()
        || list_detach_fn.is_none()
        || list_add_tail_fn.is_none()
        || ptrace_detach_fn.is_none()
        || release_process_fn.is_none()
        || zombie_log_fn.is_none()
        || stopped_fn.is_none()
        || continued_fn.is_none()
        || reap_fn.is_none()
        || parent_children_lock_node.is_null()
        || child_threads_lock_node.is_null()
    {
        return -EINVAL;
    }

    let offsets = &*scan_offsets;
    let parent = proc.cast::<u8>();
    let pgid = read_volatile(field_ptr::<CInt>(parent, offsets.proc_pgid_offset));
    let parent_children_lock = field_ptr::<c_void>(parent, offsets.proc_children_lock_offset);
    lock_fn(parent_children_lock, parent_children_lock_node);

    let child_head = wait_list_head(parent, offsets.proc_children_list_offset);
    let mut node = (*child_head).next;
    let mut ret = 0;
    while !node.is_null() && node != child_head {
        let next = (*node).next;
        let child = wait_list_entry(node, offsets.proc_siblings_list_offset);
        let child_pgid = read_volatile(field_ptr::<CInt>(child, offsets.proc_pgid_offset));
        let child_pid = read_volatile(field_ptr::<CInt>(child, offsets.proc_pid_offset));

        if wait_process_pid_matches_result(pid, pgid, child_pgid, child_pid) == 0 {
            node = next;
            continue;
        }
        write_volatile(empty, 0);

        let child_status = read_volatile(field_ptr::<CInt>(child, offsets.proc_status_offset));
        if wait_process_exited_candidate_result(options, child_status) != 0 {
            return wait_process_zombie_body_result(
                thread,
                proc,
                child.cast::<c_void>(),
                status,
                options,
                rusage,
                parent_children_lock,
                parent_children_lock_node,
                pid1,
                zombie_offsets,
                host_wait4_fn,
                Some(lock_fn),
                Some(unlock_fn),
                list_detach_fn,
                list_add_tail_fn,
                ptrace_detach_fn,
                release_process_fn,
                zombie_log_fn,
                parent_update_lock_node,
                child_update_lock_node,
                pid1_children_lock_node,
                child_threads_lock_node,
            );
        }

        let child_threads_lock = field_ptr::<c_void>(child, offsets.proc_threads_lock_offset);
        lock_fn(child_threads_lock, child_threads_lock_node);
        let child_thread = *field_ptr::<*mut c_void>(child, offsets.proc_main_thread_offset);
        let mut found = 0;
        ret = wait_process_candidate_body_result(
            ret,
            pid,
            status,
            options,
            thread,
            child.cast::<c_void>(),
            child_thread,
            parent_children_lock,
            parent_children_lock_node,
            child_threads_lock,
            child_threads_lock_node,
            offsets.proc_pid_offset as CULong,
            offsets.proc_status_offset as CULong,
            offsets.thread_tid_offset as CULong,
            offsets.thread_ptrace_offset as CULong,
            offsets.thread_signal_flags_offset as CULong,
            stopped_fn,
            continued_fn,
            reap_fn,
            Some(unlock_fn),
            &mut found,
        );
        if found != 0 {
            return ret;
        }
        unlock_fn(child_threads_lock, child_threads_lock_node);
        node = next;
    }

    if read_volatile(empty) != 0 {
        let ptraced_head = wait_list_head(parent, offsets.proc_ptraced_children_list_offset);
        let mut pnode = (*ptraced_head).next;
        while !pnode.is_null() && pnode != ptraced_head {
            let child = wait_list_entry(pnode, offsets.proc_ptraced_siblings_list_offset);
            let child_pgid = read_volatile(field_ptr::<CInt>(child, offsets.proc_pgid_offset));
            let child_pid = read_volatile(field_ptr::<CInt>(child, offsets.proc_pid_offset));
            if wait_process_pid_matches_result(pid, pgid, child_pgid, child_pid) != 0 {
                write_volatile(empty, 0);
                break;
            }
            pnode = (*pnode).next;
        }
    }

    unlock_fn(parent_children_lock, parent_children_lock_node);
    ret
}

#[no_mangle]
pub unsafe extern "C" fn wait_thread_scan_body_result(
    tid: CInt,
    status: *mut CInt,
    options: CInt,
    rusage: *mut c_void,
    empty: *mut CInt,
    thread: *mut c_void,
    proc: *mut c_void,
    offsets: *const WaitScanOffsets,
    lock_fn: Option<WaitLockUnlockFn>,
    unlock_fn: Option<WaitLockUnlockFn>,
    stopped_fn: Option<WaitStatusFn>,
    continued_fn: Option<WaitStatusFn>,
    reap_fn: Option<WaitSignalFlagsReapFn>,
    report_detach_fn: Option<WaitThreadReportDetachFn>,
    ptrace_detach_fn: Option<WaitThreadSideEffectFn>,
    release_fn: Option<WaitThreadSideEffectFn>,
    threads_lock_node: *mut c_void,
) -> CInt {
    let _ = rusage;
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    if empty.is_null()
        || thread.is_null()
        || proc.is_null()
        || offsets.is_null()
        || stopped_fn.is_none()
        || continued_fn.is_none()
        || reap_fn.is_none()
        || report_detach_fn.is_none()
        || ptrace_detach_fn.is_none()
        || release_fn.is_none()
        || threads_lock_node.is_null()
    {
        return -EINVAL;
    }

    let offsets = &*offsets;
    let thread_proc_offset = read_volatile(&offsets.thread_proc_offset);
    let thread_tid_offset = read_volatile(&offsets.thread_tid_offset);
    let thread_status_offset = read_volatile(&offsets.thread_status_offset);
    let thread_ptrace_offset = read_volatile(&offsets.thread_ptrace_offset);
    let thread_signal_flags_offset = read_volatile(&offsets.thread_signal_flags_offset);
    let thread_termsig_offset = read_volatile(&offsets.thread_termsig_offset);
    let thread_report_siblings_list_offset =
        read_volatile(&offsets.thread_report_siblings_list_offset);
    let thread_siblings_list_offset = read_volatile(&offsets.thread_siblings_list_offset);
    let proc_threads_lock_offset = read_volatile(&offsets.proc_threads_lock_offset);
    let proc_report_threads_list_offset = read_volatile(&offsets.proc_report_threads_list_offset);
    let proc_threads_list_offset = read_volatile(&offsets.proc_threads_list_offset);
    let proc_main_thread_offset = read_volatile(&offsets.proc_main_thread_offset);
    let parent = proc.cast::<u8>();
    let threads_lock = field_ptr::<c_void>(parent, proc_threads_lock_offset);
    lock_fn(threads_lock, threads_lock_node);

    let report_head = wait_list_head(parent, proc_report_threads_list_offset);
    let mut node = (*report_head).next;
    let mut ret = 0;
    while !node.is_null() && node != report_head {
        let next = (*node).next;
        let child = wait_list_entry(node, thread_report_siblings_list_offset);
        let child_tid = read_volatile(field_ptr::<CInt>(child, thread_tid_offset));
        let child_proc = *field_ptr::<*mut u8>(child, thread_proc_offset);
        let main_thread = if child_proc.is_null() {
            core::ptr::null_mut()
        } else {
            *field_ptr::<*mut u8>(child_proc, proc_main_thread_offset)
        };

        if wait_thread_tid_matches_result(tid, child_tid, (child == main_thread) as CInt) == 0 {
            node = next;
            continue;
        }
        write_volatile(empty, 0);

        let mut found = 0;
        ret = wait_thread_candidate_body_result(
            ret,
            tid,
            status,
            options,
            thread,
            child.cast::<c_void>(),
            threads_lock,
            threads_lock_node,
            thread_proc_offset as CULong,
            thread_tid_offset as CULong,
            thread_status_offset as CULong,
            thread_ptrace_offset as CULong,
            thread_signal_flags_offset as CULong,
            stopped_fn,
            continued_fn,
            reap_fn,
            Some(unlock_fn),
            report_detach_fn,
            ptrace_detach_fn,
            release_fn,
            &mut found,
        );
        if found != 0 {
            return ret;
        }
        node = next;
    }

    if read_volatile(empty) != 0 {
        let threads_head = wait_list_head(parent, proc_threads_list_offset);
        let mut tnode = (*threads_head).next;
        while !tnode.is_null() && tnode != threads_head {
            let child = wait_list_entry(tnode, thread_siblings_list_offset);
            let child_proc = *field_ptr::<*mut u8>(child, thread_proc_offset);
            let main_thread = if child_proc.is_null() {
                core::ptr::null_mut()
            } else {
                *field_ptr::<*mut u8>(child_proc, proc_main_thread_offset)
            };
            let termsig = read_volatile(field_ptr::<CInt>(child, thread_termsig_offset));
            if wait_thread_empty_candidate_result((child == main_thread) as CInt, termsig) != 0 {
                write_volatile(empty, 0);
                break;
            }
            tnode = (*tnode).next;
        }
    }

    unlock_fn(threads_lock, threads_lock_node);
    ret
}

#[no_mangle]
pub extern "C" fn wait_zombie_skip_host_result(
    ppid_parent_pid: CInt,
    current_pid: CInt,
    nowait: CInt,
) -> CInt {
    if ppid_parent_pid != current_pid || nowait != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_thread_empty_candidate_result(is_main_thread: CInt, termsig: CInt) -> CInt {
    if is_main_thread == 0 && termsig != 0 && termsig != SIGCHLD {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn waitid_status_code_result(status: CInt) -> CInt {
    if (status & 0x000000ff) == 0x0000007f {
        CLD_STOPPED
    } else if (status & 0x0000ffff) == 0x0000ffff {
        CLD_CONTINUED
    } else if (status & 0x000000ff) != 0 {
        CLD_KILLED
    } else {
        CLD_EXITED
    }
}

#[no_mangle]
pub extern "C" fn wait_stopped_source_result(
    has_c_thread: CInt,
    c_thread_exit_status: CInt,
    child_status: CInt,
    child_group_exit_status: CInt,
    main_thread_exit_status: CInt,
) -> CInt {
    if has_c_thread != 0 {
        if c_thread_exit_status != 0 {
            WAIT_STOP_SOURCE_THREAD
        } else {
            WAIT_STOP_SOURCE_NONE
        }
    } else if (child_status & (PS_STOPPED | PS_DELAY_STOPPED)) != 0 {
        if child_group_exit_status != 0 {
            WAIT_STOP_SOURCE_PROCESS
        } else {
            WAIT_STOP_SOURCE_NONE
        }
    } else if main_thread_exit_status != 0 {
        WAIT_STOP_SOURCE_MAIN_THREAD
    } else {
        WAIT_STOP_SOURCE_NONE
    }
}

#[no_mangle]
pub extern "C" fn wait_stopped_exit_status_result(
    source: CInt,
    c_thread_exit_status: CInt,
    child_group_exit_status: CInt,
    main_thread_exit_status: CInt,
) -> CInt {
    if source == WAIT_STOP_SOURCE_THREAD {
        c_thread_exit_status
    } else if source == WAIT_STOP_SOURCE_PROCESS {
        child_group_exit_status
    } else if source == WAIT_STOP_SOURCE_MAIN_THREAD {
        main_thread_exit_status
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_report_id_result(source: CInt, child_pid: CInt, c_thread_tid: CInt) -> CInt {
    if source == WAIT_STOP_SOURCE_THREAD {
        c_thread_tid
    } else {
        child_pid
    }
}

#[no_mangle]
pub extern "C" fn wait_reaped_exit_status_result(options: CInt, exit_status: CInt) -> CInt {
    if wait_reap_needed_result(options) != 0 {
        0
    } else {
        exit_status
    }
}

#[no_mangle]
pub extern "C" fn wait_reaped_signal_flags_result(
    options: CInt,
    signal_flags: CInt,
    clear_mask: CInt,
) -> CInt {
    if wait_reap_needed_result(options) != 0 {
        signal_flags & !clear_mask
    } else {
        signal_flags
    }
}

#[no_mangle]
pub extern "C" fn wait_process_reparent_needed_result(options: CInt, parent_is_ppid: CInt) -> CInt {
    (wait_reap_needed_result(options) != 0 && parent_is_ppid != 0) as CInt
}

#[no_mangle]
pub extern "C" fn wait_main_thread_ptrace_detach_needed_result(
    options: CInt,
    ptrace: CInt,
) -> CInt {
    (wait_reap_needed_result(options) != 0 && (ptrace & PT_TRACED) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn wait_thread_reap_action_result(options: CInt, ptrace: CInt) -> CInt {
    if wait_reap_needed_result(options) == 0 {
        WAIT_THREAD_REAP_ACTION_NONE
    } else if (ptrace & PT_TRACED) != 0 {
        WAIT_THREAD_REAP_ACTION_PTRACE_DETACH
    } else {
        WAIT_THREAD_REAP_ACTION_RELEASE
    }
}

#[no_mangle]
pub extern "C" fn wait_status_copy_needed_result(rc: CInt, has_status: CInt) -> CInt {
    (rc >= 0 && has_status != 0) as CInt
}

#[no_mangle]
pub extern "C" fn wait_rusage_copy_needed_result(has_rusage: CInt) -> CInt {
    (has_rusage != 0) as CInt
}

unsafe fn zero_rusage(usage: *mut RUsage) {
    let raw = usage as *mut u8;
    let mut offset = 0;
    while offset < size_of::<RUsage>() {
        raw.add(offset).write_volatile(0);
        offset += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn wait4_body_result(
    pid: CInt,
    status_addr: CULong,
    options: CInt,
    rusage_addr: CULong,
    do_wait_fn: Wait4DoWaitFn,
    copy_to_fn: SyscallCopyToUserFn,
) -> CLong {
    let valid = wait4_options_result(options);
    if valid != 0 {
        return valid as CLong;
    }

    let mut status: CInt = 0;
    let mut usage = MaybeUninit::<RUsage>::uninit();
    let usage_ptr = usage.as_mut_ptr();
    zero_rusage(usage_ptr);

    let rc = do_wait_fn(pid, &mut status as *mut CInt, WEXITED | options, usage_ptr);
    if wait_status_copy_needed_result(rc, (status_addr != 0) as CInt) != 0 {
        let src = &status as *const CInt as *const u8;
        copy_to_fn(status_addr, src, size_of::<CInt>());
    }
    if wait_rusage_copy_needed_result((rusage_addr != 0) as CInt) != 0 {
        copy_to_fn(rusage_addr, usage_ptr as *const u8, size_of::<RUsage>());
    }
    rc as CLong
}

#[no_mangle]
pub extern "C" fn waitid_siginfo_needed_result(rc: CInt, has_infop: CInt) -> CInt {
    (rc > 0 && has_infop != 0) as CInt
}

fn timeval_to_jiffy_result(sec: CLong, usec: CLong) -> CLong {
    sec * 100 + usec / 10000
}

#[no_mangle]
pub unsafe extern "C" fn waitid_copy_siginfo_result(
    rc: CInt,
    infop_addr: CULong,
    status: CInt,
    utime_sec: CLong,
    utime_usec: CLong,
    stime_sec: CLong,
    stime_usec: CLong,
    copy_to_fn: SyscallCopyToUserFn,
) {
    if waitid_siginfo_needed_result(rc, (infop_addr != 0) as CInt) == 0 {
        return;
    }

    let mut info = MaybeUninit::<SigInfo>::uninit();
    let info_ptr = info.as_mut_ptr();
    unsafe {
        let raw = info_ptr as *mut u8;
        let mut offset = 0;
        while offset < size_of::<SigInfo>() {
            raw.add(offset).write_volatile(0);
            offset += 1;
        }

        let info = &mut *info_ptr;
        info.si_signo = SIGCHLD;
        info.si_code = waitid_status_code_result(status);
        info.sifields.sigchld = ManuallyDrop::new(SigInfoChild {
            si_pid: rc,
            si_uid: 0,
            si_status: status,
            padding: 0,
            si_utime: timeval_to_jiffy_result(utime_sec, utime_usec),
            si_stime: timeval_to_jiffy_result(stime_sec, stime_usec),
        });
        let src = info as *const SigInfo as *const u8;
        copy_to_fn(infop_addr, src, size_of::<SigInfo>());
    }
}

#[no_mangle]
pub unsafe extern "C" fn waitid_body_result(
    idtype: CInt,
    id: CInt,
    infop_addr: CULong,
    options: CInt,
    do_wait_fn: Wait4DoWaitFn,
    copy_to_fn: SyscallCopyToUserFn,
) -> CLong {
    let mut pid: CInt = 0;
    let mut rc = waitid_to_wait_pid_result(idtype, id, &mut pid as *mut CInt);
    if rc != 0 {
        return rc as CLong;
    }

    rc = waitid_options_result(options);
    if rc != 0 {
        return rc as CLong;
    }

    let mut status: CInt = 0;
    let mut usage = MaybeUninit::<RUsage>::uninit();
    let usage_ptr = usage.as_mut_ptr();
    zero_rusage(usage_ptr);

    rc = do_wait_fn(pid, &mut status as *mut CInt, options, usage_ptr);
    if rc < 0 {
        return rc as CLong;
    }

    let usage = &*usage_ptr;
    waitid_copy_siginfo_result(
        rc,
        infop_addr,
        status,
        usage.ru_utime.tv_sec,
        usage.ru_utime.tv_usec,
        usage.ru_stime.tv_sec,
        usage.ru_stime.tv_usec,
        copy_to_fn,
    );
    0
}

#[no_mangle]
pub extern "C" fn exit_code_status_result(code: CInt) -> CInt {
    (code >> 8) & 255
}

#[no_mangle]
pub extern "C" fn exit_code_signal_result(code: CInt) -> CInt {
    code & 255
}

#[no_mangle]
pub extern "C" fn exit_syscall_code_result(status: CInt) -> CInt {
    (status & 255) << 8
}

#[no_mangle]
pub unsafe extern "C" fn exit_body_result(status: CInt, exit_fn: Option<SyscallExitFn>) -> CLong {
    if let Some(exit_fn) = exit_fn {
        exit_fn(exit_syscall_code_result(status));
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn exit_group_body_result(
    status: CInt,
    pid: CInt,
    log_fn: Option<SyscallExitGroupLogFn>,
    terminate_fn: Option<SyscallTerminateFn>,
) -> CLong {
    if let Some(log) = log_fn {
        log(pid);
    }
    if let Some(terminate) = terminate_fn {
        terminate(status, 0);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn sched_yield_body_result(
    cpu_local: *mut c_void,
    flags_offset: SizeT,
    runq_len_offset: SizeT,
    runq_lock_offset: SizeT,
    need_resched_flag: u32,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
    schedule_fn: Option<SyscallScheduleFn>,
) -> CLong {
    let base = cpu_local.cast::<u8>();
    let flags = field_ptr::<u32>(base, flags_offset);
    let runq_len = field_ptr::<SizeT>(base, runq_len_offset);
    let runq_lock = base.add(runq_lock_offset).cast::<c_void>();
    let mut irqstate = 0;
    let mut do_schedule = 0;

    if let Some(lock) = lock_fn {
        irqstate = lock(runq_lock);
    }
    if (*flags & need_resched_flag) != 0 || *runq_len > 1 {
        *flags &= !need_resched_flag;
        do_schedule = 1;
    }
    if let Some(unlock) = unlock_fn {
        unlock(runq_lock, irqstate);
    }
    if do_schedule != 0 {
        if let Some(schedule) = schedule_fn {
            schedule();
        }
    }
    0
}

#[no_mangle]
pub extern "C" fn thread_exit_signal_result(ptrace: CInt, termsig: CInt) -> CInt {
    if ptrace != 0 { SIGCHLD } else { termsig }
}

#[no_mangle]
pub extern "C" fn thread_exit_signal_report_needed_result(report_proc: *const c_void) -> CInt {
    (!report_proc.is_null()) as CInt
}

#[no_mangle]
pub extern "C" fn sigchld_code_result(exit_status: CInt) -> CInt {
    if (exit_status & 0x7f) != 0 {
        if (exit_status & 0x80) != 0 {
            CLD_DUMPED
        } else {
            CLD_KILLED
        }
    } else {
        CLD_EXITED
    }
}

#[no_mangle]
pub unsafe extern "C" fn thread_exit_signal_body_result(
    thread: *mut c_void,
    thread_report_proc_offset: SizeT,
    thread_ptrace_offset: SizeT,
    thread_termsig_offset: SizeT,
    thread_exit_status_offset: SizeT,
    thread_tid_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    proc_pid_offset: SizeT,
    proc_waitpid_q_offset: SizeT,
    tsc_to_ts_fn: Option<SyscallTscToTsFn>,
    timespec_to_jiffy_fn: Option<SyscallTimespecToJiffyFn>,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
    wake_fn: Option<ThreadExitWakeFn>,
    log_fn: Option<ThreadExitLogFn>,
) -> CLong {
    if thread.is_null() {
        return -EINVAL as CLong;
    }

    let thread_base = thread.cast::<u8>();
    let report_proc = read_volatile(field_ptr::<*mut c_void>(
        thread_base,
        thread_report_proc_offset,
    ));
    if thread_exit_signal_report_needed_result(report_proc) == 0 {
        return 0;
    }

    let Some(tsc_to_ts) = tsc_to_ts_fn else {
        return -EINVAL as CLong;
    };
    let Some(timespec_to_jiffy) = timespec_to_jiffy_fn else {
        return -EINVAL as CLong;
    };
    let Some(do_kill) = do_kill_fn else {
        return -EINVAL as CLong;
    };
    let Some(wake) = wake_fn else {
        return -EINVAL as CLong;
    };

    let report_base = report_proc.cast::<u8>();
    let ptrace = read_volatile(field_ptr::<CInt>(thread_base, thread_ptrace_offset));
    let termsig = read_volatile(field_ptr::<CInt>(thread_base, thread_termsig_offset));
    let exit_status = read_volatile(field_ptr::<CInt>(thread_base, thread_exit_status_offset));
    let tid = read_volatile(field_ptr::<CInt>(thread_base, thread_tid_offset));
    let user_tsc = read_volatile(field_ptr::<CULong>(thread_base, thread_user_tsc_offset));
    let system_tsc = read_volatile(field_ptr::<CULong>(thread_base, thread_system_tsc_offset));
    let report_pid = read_volatile(field_ptr::<CInt>(report_base, proc_pid_offset));
    let sig = thread_exit_signal_result(ptrace, termsig);

    let mut info = MaybeUninit::<SigInfo>::uninit();
    let info_ptr = info.as_mut_ptr();
    let raw = info_ptr.cast::<u8>();
    let mut offset = 0;
    while offset < size_of::<SigInfo>() {
        raw.add(offset).write_volatile(0);
        offset += 1;
    }

    let mut ats = MaybeUninit::<TimeSpec>::uninit();
    tsc_to_ts(user_tsc, ats.as_mut_ptr());
    let utime = timespec_to_jiffy(ats.as_ptr()) as CLong;
    tsc_to_ts(system_tsc, ats.as_mut_ptr());
    let stime = timespec_to_jiffy(ats.as_ptr()) as CLong;

    let info_ref = &mut *info_ptr;
    info_ref.si_signo = sig;
    info_ref.si_code = sigchld_code_result(exit_status);
    info_ref.sifields.sigchld = ManuallyDrop::new(SigInfoChild {
        si_pid: tid,
        si_uid: 0,
        si_status: exit_status,
        padding: 0,
        si_utime: utime,
        si_stime: stime,
    });

    let error = do_kill(
        core::ptr::null_mut(),
        report_pid,
        -1,
        sig,
        info_ref as *const SigInfo,
        0,
    );
    if let Some(log) = log_fn {
        log(sig, error);
    }
    wake(report_base.add(proc_waitpid_q_offset).cast::<c_void>());
    error
}

#[no_mangle]
pub unsafe extern "C" fn finalize_process_parent_notify_body_result(
    proc: *mut c_void,
    proc_parent_offset: SizeT,
    proc_pid_offset: SizeT,
    proc_group_exit_status_offset: SizeT,
    proc_termsig_offset: SizeT,
    proc_utime_offset: SizeT,
    proc_stime_offset: SizeT,
    proc_waitpid_q_offset: SizeT,
    timespec_to_jiffy_fn: Option<SyscallTimespecToJiffyFn>,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
    wake_fn: Option<ThreadExitWakeFn>,
    log_fn: Option<ThreadExitLogFn>,
) -> CLong {
    if proc.is_null() {
        return -EINVAL as CLong;
    }

    let proc_base = proc.cast::<u8>();
    let parent = read_volatile(field_ptr::<*mut c_void>(proc_base, proc_parent_offset));
    if parent.is_null() {
        return -EINVAL as CLong;
    }

    let Some(wake) = wake_fn else {
        return -EINVAL as CLong;
    };
    let termsig = read_volatile(field_ptr::<CInt>(proc_base, proc_termsig_offset));
    let mut error = 0;
    if finalize_process_parent_signal_needed_result(termsig) != 0 {
        let Some(timespec_to_jiffy) = timespec_to_jiffy_fn else {
            return -EINVAL as CLong;
        };
        let Some(do_kill) = do_kill_fn else {
            return -EINVAL as CLong;
        };

        let exit_status =
            read_volatile(field_ptr::<CInt>(proc_base, proc_group_exit_status_offset));
        let pid = read_volatile(field_ptr::<CInt>(proc_base, proc_pid_offset));
        let parent_pid = read_volatile(field_ptr::<CInt>(parent.cast::<u8>(), proc_pid_offset));

        let mut info = MaybeUninit::<SigInfo>::uninit();
        let info_ptr = info.as_mut_ptr();
        let raw = info_ptr.cast::<u8>();
        let mut offset = 0;
        while offset < size_of::<SigInfo>() {
            raw.add(offset).write_volatile(0);
            offset += 1;
        }

        let info_ref = &mut *info_ptr;
        info_ref.si_signo = SIGCHLD;
        info_ref.si_code = sigchld_code_result(exit_status);
        info_ref.sifields.sigchld = ManuallyDrop::new(SigInfoChild {
            si_pid: pid,
            si_uid: 0,
            si_status: exit_status,
            padding: 0,
            si_utime: timespec_to_jiffy(field_ptr::<TimeSpec>(proc_base, proc_utime_offset))
                as CLong,
            si_stime: timespec_to_jiffy(field_ptr::<TimeSpec>(proc_base, proc_stime_offset))
                as CLong,
        });
        error = do_kill(
            core::ptr::null_mut(),
            parent_pid,
            -1,
            SIGCHLD,
            info_ref as *const SigInfo,
            0,
        );
        if let Some(log) = log_fn {
            log(termsig, error);
        }
    }

    wake(
        parent
            .cast::<u8>()
            .add(proc_waitpid_q_offset)
            .cast::<c_void>(),
    );
    error
}

#[no_mangle]
pub unsafe extern "C" fn finalize_process_body_result(
    proc: *mut c_void,
    pid1: *const c_void,
    lock_node: *mut c_void,
    proc_parent_offset: SizeT,
    proc_status_offset: SizeT,
    proc_update_lock_offset: SizeT,
    proc_pid_offset: SizeT,
    proc_group_exit_status_offset: SizeT,
    proc_termsig_offset: SizeT,
    proc_utime_offset: SizeT,
    proc_stime_offset: SizeT,
    proc_waitpid_q_offset: SizeT,
    lock_fn: Option<WaitLockUnlockFn>,
    unlock_fn: Option<WaitLockUnlockFn>,
    release_fn: Option<WaitThreadSideEffectFn>,
    wakeup_log_fn: Option<FinalizeWakeupLogFn>,
    timespec_to_jiffy_fn: Option<SyscallTimespecToJiffyFn>,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
    wake_fn: Option<ThreadExitWakeFn>,
    log_fn: Option<ThreadExitLogFn>,
) -> CLong {
    if proc.is_null() || lock_node.is_null() {
        return -EINVAL as CLong;
    }
    let Some(lock) = lock_fn else {
        return -EINVAL as CLong;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL as CLong;
    };
    let Some(release) = release_fn else {
        return -EINVAL as CLong;
    };

    let proc_base = proc.cast::<u8>();
    let update_lock = proc_base.add(proc_update_lock_offset).cast::<c_void>();

    lock(update_lock, lock_node);
    let parent = read_volatile(field_ptr::<*mut c_void>(proc_base, proc_parent_offset));
    write_volatile(field_ptr::<CInt>(proc_base, proc_status_offset), PS_ZOMBIE);
    let parent_is_pid1 = finalize_process_parent_is_pid1_result(parent, pid1) != 0;
    unlock(update_lock, lock_node);

    if parent_is_pid1 {
        release(proc);
        return 0;
    }

    if let Some(log_wakeup) = wakeup_log_fn {
        log_wakeup();
    }
    finalize_process_parent_notify_body_result(
        proc,
        proc_parent_offset,
        proc_pid_offset,
        proc_group_exit_status_offset,
        proc_termsig_offset,
        proc_utime_offset,
        proc_stime_offset,
        proc_waitpid_q_offset,
        timespec_to_jiffy_fn,
        do_kill_fn,
        wake_fn,
        log_fn,
    )
}

#[no_mangle]
pub extern "C" fn exit_group_status_claimed_result(old_exit_status: CULong) -> CInt {
    ((old_exit_status & EXIT_GROUP_STATUS_CONFIRMED) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_group_status_update_failed_result(
    observed_status: CULong,
    expected_status: CULong,
) -> CInt {
    (observed_status != expected_status) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_host_exit_needed_result(nohost: CInt) -> CInt {
    (nohost == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn terminate_mcexec_body_result(
    proc: *mut c_void,
    request: *mut SyscallRequest,
    rc: CInt,
    sig: CInt,
    cpu: CInt,
    exit_group_nr: CInt,
    proc_group_exit_status_offset: SizeT,
    proc_nohost_offset: SizeT,
    cmpxchg_fn: Option<TerminateMcexecCmpxchgFn>,
    syscall_fn: Option<TerminateMcexecSyscallFn>,
) -> CLong {
    if proc.is_null() || request.is_null() {
        return -EINVAL as CLong;
    }
    let Some(cmpxchg) = cmpxchg_fn else {
        return -EINVAL as CLong;
    };

    let proc_base = proc.cast::<u8>();
    let status_ptr = field_ptr::<CULong>(proc_base, proc_group_exit_status_offset);
    let old_exit_status = read_volatile(status_ptr);
    if exit_group_status_claimed_result(old_exit_status) != 0 {
        return 0;
    }

    let exit_status = exit_group_status_result(rc, sig);
    let observed = cmpxchg(status_ptr, old_exit_status, exit_status);
    if terminate_group_status_update_failed_result(observed, old_exit_status) != 0 {
        return 0;
    }

    let nohost_ptr = field_ptr::<CInt>(proc_base, proc_nohost_offset);
    if terminate_host_exit_needed_result(read_volatile(nohost_ptr)) == 0 {
        return 0;
    }
    let Some(syscall) = syscall_fn else {
        return -EINVAL as CLong;
    };

    write(
        core::ptr::addr_of_mut!((*request).number),
        exit_group_nr as CULong,
    );
    write(
        core::ptr::addr_of_mut!((*request).args[0]),
        read_volatile(status_ptr),
    );
    write_volatile(nohost_ptr, 1);
    syscall(request, cpu)
}

#[no_mangle]
pub extern "C" fn sync_child_event_needed_result(
    has_event: CInt,
    inherit: CInt,
    pid: CInt,
) -> CInt {
    (has_event != 0 && (inherit != 0 || pid != 0)) as CInt
}

#[no_mangle]
pub extern "C" fn sync_child_event_pid_action_result(pid: CInt) -> CInt {
    if pid == 0 {
        SYNC_CHILD_EVENT_ACTION_CHILD_TOTAL
    } else if pid > 0 {
        SYNC_CHILD_EVENT_ACTION_SET_COUNT
    } else {
        SYNC_CHILD_EVENT_ACTION_NONE
    }
}

unsafe fn sync_child_event_apply_action(
    event: *mut u8,
    action: CInt,
    counter_id_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    read_fn: SyncChildPerfReadFn,
    set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    if action == SYNC_CHILD_EVENT_ACTION_CHILD_TOTAL {
        let counter_id = read_volatile(field_ptr::<CInt>(event, counter_id_offset));
        let count = read_fn(counter_id);
        let total_ptr = field_ptr::<CULong>(event, child_count_total_offset);
        let total = read_volatile(total_ptr).wrapping_add(count);
        write_volatile(total_ptr, total);
        return 0;
    }

    if action == SYNC_CHILD_EVENT_ACTION_SET_COUNT {
        let Some(set_count) = set_fn else {
            return -EINVAL as CLong;
        };
        let counter_id = read_volatile(field_ptr::<CInt>(event, counter_id_offset));
        let count = read_fn(counter_id);
        set_count(field_ptr::<c_void>(event, count_offset), count as CLong);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn sync_child_event_body_result(
    event: *mut c_void,
    inherit: CInt,
    pid: CInt,
    group_leader_offset: SizeT,
    event_pid_offset: SizeT,
    counter_id_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    read_fn: Option<SyncChildPerfReadFn>,
    set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    if sync_child_event_needed_result(!event.is_null() as CInt, inherit, pid) == 0 {
        return 0;
    }
    let Some(read) = read_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let leader_pid = read_volatile(field_ptr::<CInt>(leader_base, event_pid_offset));
    let leader_action = sync_child_event_pid_action_result(leader_pid);
    if leader_action == SYNC_CHILD_EVENT_ACTION_NONE {
        return 0;
    }

    let rc = sync_child_event_apply_action(
        leader_base,
        leader_action,
        counter_id_offset,
        count_offset,
        child_count_total_offset,
        read,
        set_fn,
    );
    if rc != 0 {
        return rc;
    }

    let sub_action = sync_child_event_pid_action_result(pid);
    if sub_action == SYNC_CHILD_EVENT_ACTION_NONE {
        return 0;
    }

    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset);
        let rc = sync_child_event_apply_action(
            sub,
            sub_action,
            counter_id_offset,
            count_offset,
            child_count_total_offset,
            read,
            set_fn,
        );
        if rc != 0 {
            return rc;
        }
        node = next;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_read_value_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    exclude_user: CInt,
    exclude_kernel: CInt,
    inherit: CInt,
    event_pid_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    update_fn: Option<PerfEventUpdateFn>,
    atomic_read_fn: Option<SyscallAtomic64ReadFn>,
) -> CULong {
    if event.is_null() || thread.is_null() {
        return 0;
    }
    let Some(atomic_read) = atomic_read_fn else {
        return 0;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let stopped_user = read_volatile(field_ptr::<CLong>(event_base, stopped_user_tsc_offset));
    let cur_user = if stopped_user != 0 {
        stopped_user as CULong
    } else {
        read_volatile(field_ptr::<CULong>(thread_base, thread_user_tsc_offset))
    };
    let stopped_system = read_volatile(field_ptr::<CLong>(event_base, stopped_system_tsc_offset));
    let cur_system = if stopped_system != 0 {
        stopped_system as CULong
    } else {
        read_volatile(field_ptr::<CULong>(thread_base, thread_system_tsc_offset))
    };

    let mut pmc_count = 0u64;
    let pid = read_volatile(field_ptr::<CInt>(event_base, event_pid_offset));
    if pid == 0 {
        let use_invariant = read_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset));
        if use_invariant != 0 {
            if exclude_user == 0 {
                let base = read_volatile(field_ptr::<CLong>(event_base, base_user_tsc_offset));
                let accum = read_volatile(field_ptr::<CLong>(event_base, user_accum_count_offset));
                pmc_count = pmc_count
                    .wrapping_add(cur_user.wrapping_sub(base as CULong))
                    .wrapping_add(accum as CULong);
            }
            if exclude_kernel == 0 {
                let base = read_volatile(field_ptr::<CLong>(event_base, base_system_tsc_offset));
                let accum =
                    read_volatile(field_ptr::<CLong>(event_base, system_accum_count_offset));
                pmc_count = pmc_count
                    .wrapping_add(cur_system.wrapping_sub(base as CULong))
                    .wrapping_add(accum as CULong);
            }
        } else if let Some(update) = update_fn {
            let _ = update(event);
        }
    }

    let mut rtn_count = (atomic_read(field_ptr::<c_void>(event_base, count_offset)) as CULong)
        .wrapping_add(pmc_count);
    if inherit != 0 {
        rtn_count = rtn_count.wrapping_add(read_volatile(field_ptr::<CULong>(
            event_base,
            child_count_total_offset,
        )));
    }

    rtn_count
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_read_value_entry_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    event_attr_offset: SizeT,
    event_pid_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    attr_flags_fn: Option<PerfReadAttrFlagsFn>,
    update_fn: Option<PerfEventUpdateFn>,
    atomic_read_fn: Option<SyscallAtomic64ReadFn>,
) -> CULong {
    if event.is_null() || thread.is_null() {
        return 0;
    }
    let Some(attr_flags) = attr_flags_fn else {
        return 0;
    };

    let event_base = event.cast::<u8>();
    let mut exclude_user = 0;
    let mut exclude_kernel = 0;
    let mut inherit = 0;
    let attr_rc = attr_flags(
        field_ptr::<c_void>(event_base, event_attr_offset).cast_const(),
        core::ptr::addr_of_mut!(exclude_user),
        core::ptr::addr_of_mut!(exclude_kernel),
        core::ptr::addr_of_mut!(inherit),
    );
    if attr_rc != 0 {
        return 0;
    }

    perf_event_read_value_body_result(
        event,
        thread,
        exclude_user,
        exclude_kernel,
        inherit,
        event_pid_offset,
        use_invariant_tsc_offset,
        count_offset,
        child_count_total_offset,
        base_user_tsc_offset,
        stopped_user_tsc_offset,
        user_accum_count_offset,
        base_system_tsc_offset,
        stopped_system_tsc_offset,
        system_accum_count_offset,
        thread_user_tsc_offset,
        thread_system_tsc_offset,
        update_fn,
        atomic_read_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_read_one_body_result(
    event: *mut c_void,
    buf_addr: CULong,
    read_value_fn: Option<PerfReadValueFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }
    let Some(read_value) = read_value_fn else {
        return -EINVAL as CLong;
    };
    let Some(copy_to) = copy_to_fn else {
        return -EINVAL as CLong;
    };

    let values = [read_value(event)];
    let size = size_of::<CULong>();
    if copy_to(buf_addr, values.as_ptr().cast::<u8>(), size) != 0 {
        return -EFAULT as CLong;
    }

    size as CLong
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_read_group_body_result(
    event: *mut c_void,
    buf_addr: CULong,
    group_leader_offset: SizeT,
    nr_siblings_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    read_value_fn: Option<PerfReadValueFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }
    let Some(read_value) = read_value_fn else {
        return -EINVAL as CLong;
    };
    let Some(copy_to) = copy_to_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let leader_count = read_value(leader);
    let nr_siblings = read_volatile(field_ptr::<CInt>(leader_base, nr_siblings_offset));
    let values = [1u64.wrapping_add(nr_siblings as CULong), leader_count];
    let mut ret = 2 * size_of::<CULong>();
    if copy_to(buf_addr, values.as_ptr().cast::<u8>(), ret) != 0 {
        return -EFAULT as CLong;
    }

    let value_size = size_of::<CULong>();
    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset).cast::<c_void>();
        let value = [read_value(sub)];
        if copy_to(
            buf_addr.wrapping_add(ret as CULong),
            value.as_ptr().cast::<u8>(),
            value_size,
        ) != 0
        {
            return -EFAULT as CLong;
        }
        ret = ret.wrapping_add(value_size);
        node = next;
    }

    ret as CLong
}

#[no_mangle]
pub unsafe extern "C" fn perf_read_body_result(
    event: *mut c_void,
    buf_addr: CULong,
    read_format: CULong,
    group_flag: CULong,
    read_group_fn: Option<PerfReadDispatchFn>,
    read_one_fn: Option<PerfReadDispatchFn>,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }

    if (read_format & group_flag) != 0 {
        let Some(read_group) = read_group_fn else {
            return -EINVAL as CLong;
        };
        return read_group(event, read_format, buf_addr);
    }

    let Some(read_one) = read_one_fn else {
        return -EINVAL as CLong;
    };
    read_one(event, read_format, buf_addr)
}

#[no_mangle]
pub unsafe extern "C" fn perf_counter_set_body_result(
    event: *mut c_void,
    exclude_kernel: CInt,
    exclude_user: CInt,
    counter_id: CInt,
    hw_config: CULong,
    extra_reg_reg_offset: SizeT,
    kernel_mode: CInt,
    user_mode: CInt,
    set_extra_fn: Option<PerfCounterExtraSetFn>,
    init_raw_fn: Option<PerfCounterInitRawFn>,
) -> CInt {
    if event.is_null() {
        return -EINVAL;
    }
    let Some(init_raw) = init_raw_fn else {
        return -EINVAL;
    };

    let mut mode = 0;
    if exclude_kernel == 0 {
        mode |= kernel_mode;
    }
    if exclude_user == 0 {
        mode |= user_mode;
    }

    let event_base = event.cast::<u8>();
    let extra_reg = read_volatile(field_ptr::<u32>(event_base, extra_reg_reg_offset));
    if extra_reg != 0 {
        let Some(set_extra) = set_extra_fn else {
            return -EINVAL;
        };
        if set_extra(event) != 0 {
            return -1;
        }
    }

    init_raw(counter_id, hw_config, mode)
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_counter_set_entry_body_result(
    event: *mut c_void,
    event_attr_offset: SizeT,
    event_counter_id_offset: SizeT,
    event_hw_config_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    kernel_mode: CInt,
    user_mode: CInt,
    attr_flags_fn: Option<PerfCounterAttrFlagsFn>,
    set_extra_fn: Option<PerfCounterExtraSetFn>,
    init_raw_fn: Option<PerfCounterInitRawFn>,
) -> CInt {
    if event.is_null() {
        return -EINVAL;
    }
    let Some(attr_flags) = attr_flags_fn else {
        return -EINVAL;
    };

    let event_base = event.cast::<u8>();
    let mut exclude_kernel = 0;
    let mut exclude_user = 0;
    let attr_rc = attr_flags(
        field_ptr::<c_void>(event_base, event_attr_offset).cast_const(),
        core::ptr::addr_of_mut!(exclude_kernel),
        core::ptr::addr_of_mut!(exclude_user),
    );
    if attr_rc != 0 {
        return attr_rc;
    }

    let counter_id = read_volatile(field_ptr::<CInt>(event_base, event_counter_id_offset));
    let hw_config = read_volatile(field_ptr::<CULong>(event_base, event_hw_config_offset));
    perf_counter_set_body_result(
        event,
        exclude_kernel,
        exclude_user,
        counter_id,
        hw_config,
        extra_reg_reg_offset,
        kernel_mode,
        user_mode,
        set_extra_fn,
        init_raw_fn,
    )
}

#[allow(clippy::too_many_arguments)]
unsafe fn perf_start_apply_event_result(
    event_base: *mut u8,
    thread_base: *mut u8,
    counter_mask: &mut CULong,
    counter_id_offset: SizeT,
    state_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    inactive_state: CInt,
    active_state: CInt,
    mask_check: PerfCounterMaskCheckFn,
    set_period_fn: Option<PerfEventIntFn>,
    counter_set_fn: Option<PerfEventIntFn>,
) -> CLong {
    let counter_id = read_volatile(field_ptr::<CInt>(event_base, counter_id_offset));
    let bit = perf_event_bit_result(counter_id);
    let state = read_volatile(field_ptr::<CInt>(event_base, state_offset));
    if bit == 0 || mask_check(bit) == 0 || state != inactive_state {
        return 0;
    }

    let use_invariant = read_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset));
    if use_invariant != 0 {
        let stopped_user_ptr = field_ptr::<CLong>(event_base, stopped_user_tsc_offset);
        let base_user_ptr = field_ptr::<CLong>(event_base, base_user_tsc_offset);
        let user_accum_ptr = field_ptr::<CLong>(event_base, user_accum_count_offset);
        let stopped_user = read_volatile(stopped_user_ptr);
        if stopped_user != 0 {
            let base_user = read_volatile(base_user_ptr);
            let accum = read_volatile(user_accum_ptr);
            write_volatile(
                user_accum_ptr,
                accum.wrapping_add(stopped_user.wrapping_sub(base_user)),
            );
            write_volatile(stopped_user_ptr, 0);
        }
        write_volatile(
            base_user_ptr,
            read_volatile(field_ptr::<CLong>(thread_base, thread_user_tsc_offset)),
        );

        let stopped_system_ptr = field_ptr::<CLong>(event_base, stopped_system_tsc_offset);
        let base_system_ptr = field_ptr::<CLong>(event_base, base_system_tsc_offset);
        let system_accum_ptr = field_ptr::<CLong>(event_base, system_accum_count_offset);
        let stopped_system = read_volatile(stopped_system_ptr);
        if stopped_system != 0 {
            let base_system = read_volatile(base_system_ptr);
            let accum = read_volatile(system_accum_ptr);
            write_volatile(
                system_accum_ptr,
                accum.wrapping_add(stopped_system.wrapping_sub(base_system)),
            );
            write_volatile(stopped_system_ptr, 0);
        }
        write_volatile(
            base_system_ptr,
            read_volatile(field_ptr::<CLong>(thread_base, thread_system_tsc_offset)),
        );
    } else {
        let Some(set_period) = set_period_fn else {
            return -EINVAL as CLong;
        };
        let Some(counter_set) = counter_set_fn else {
            return -EINVAL as CLong;
        };
        set_period(event_base.cast::<c_void>());
        counter_set(event_base.cast::<c_void>());
        *counter_mask |= bit;
    }

    write_volatile(field_ptr::<CInt>(event_base, state_offset), active_state);
    0
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_start_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    group_leader_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    counter_id_offset: SizeT,
    state_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    thread_proc_offset: SizeT,
    proc_perf_status_offset: SizeT,
    inactive_state: CInt,
    active_state: CInt,
    pp_count: CInt,
    mask_check_fn: Option<PerfCounterMaskCheckFn>,
    set_period_fn: Option<PerfEventIntFn>,
    counter_set_fn: Option<PerfEventIntFn>,
    counter_start_fn: Option<PerfCounterStartFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(mask_check) = mask_check_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let mut counter_mask = 0;
    let rc = perf_start_apply_event_result(
        leader_base,
        thread_base,
        &mut counter_mask,
        counter_id_offset,
        state_offset,
        use_invariant_tsc_offset,
        base_user_tsc_offset,
        stopped_user_tsc_offset,
        user_accum_count_offset,
        base_system_tsc_offset,
        stopped_system_tsc_offset,
        system_accum_count_offset,
        thread_user_tsc_offset,
        thread_system_tsc_offset,
        inactive_state,
        active_state,
        mask_check,
        set_period_fn,
        counter_set_fn,
    );
    if rc != 0 {
        return rc;
    }

    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset);
        let rc = perf_start_apply_event_result(
            sub,
            thread_base,
            &mut counter_mask,
            counter_id_offset,
            state_offset,
            use_invariant_tsc_offset,
            base_user_tsc_offset,
            stopped_user_tsc_offset,
            user_accum_count_offset,
            base_system_tsc_offset,
            stopped_system_tsc_offset,
            system_accum_count_offset,
            thread_user_tsc_offset,
            thread_system_tsc_offset,
            inactive_state,
            active_state,
            mask_check,
            set_period_fn,
            counter_set_fn,
        );
        if rc != 0 {
            return rc;
        }
        node = next;
    }

    if counter_mask != 0 {
        let Some(counter_start) = counter_start_fn else {
            return -EINVAL as CLong;
        };
        counter_start(counter_mask);
    }

    let proc = read_volatile(field_ptr::<*mut c_void>(thread_base, thread_proc_offset));
    if proc.is_null() {
        return -EINVAL as CLong;
    }
    write_volatile(
        field_ptr::<CInt>(proc.cast::<u8>(), proc_perf_status_offset),
        pp_count,
    );

    0
}

#[allow(clippy::too_many_arguments)]
unsafe fn perf_reset_apply_event_result(
    event_base: *mut u8,
    thread_base: *mut u8,
    counter_id_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    mask_check: PerfCounterMaskCheckFn,
    read_value_fn: Option<PerfReadValueFn>,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    let counter_id = read_volatile(field_ptr::<CInt>(event_base, counter_id_offset));
    let bit = perf_event_bit_result(counter_id);
    if bit == 0 || mask_check(bit) == 0 {
        return 0;
    }

    let use_invariant = read_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset));
    if use_invariant != 0 {
        let stopped_user = read_volatile(field_ptr::<CLong>(event_base, stopped_user_tsc_offset));
        let user_base = if stopped_user != 0 {
            stopped_user
        } else {
            read_volatile(field_ptr::<CLong>(thread_base, thread_user_tsc_offset))
        };
        write_volatile(
            field_ptr::<CLong>(event_base, base_user_tsc_offset),
            user_base,
        );
        write_volatile(field_ptr::<CLong>(event_base, user_accum_count_offset), 0);

        let stopped_system =
            read_volatile(field_ptr::<CLong>(event_base, stopped_system_tsc_offset));
        let system_base = if stopped_system != 0 {
            stopped_system
        } else {
            read_volatile(field_ptr::<CLong>(thread_base, thread_system_tsc_offset))
        };
        write_volatile(
            field_ptr::<CLong>(event_base, base_system_tsc_offset),
            system_base,
        );
        write_volatile(field_ptr::<CLong>(event_base, system_accum_count_offset), 0);
    } else {
        let Some(read_value) = read_value_fn else {
            return -EINVAL as CLong;
        };
        let Some(atomic_set) = atomic_set_fn else {
            return -EINVAL as CLong;
        };
        read_value(event_base.cast::<c_void>());
        atomic_set(field_ptr::<c_void>(event_base, count_offset), 0);
    }

    0
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_reset_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    group_leader_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    counter_id_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    mask_check_fn: Option<PerfCounterMaskCheckFn>,
    read_value_fn: Option<PerfReadValueFn>,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(mask_check) = mask_check_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let rc = perf_reset_apply_event_result(
        leader_base,
        thread_base,
        counter_id_offset,
        use_invariant_tsc_offset,
        base_user_tsc_offset,
        stopped_user_tsc_offset,
        user_accum_count_offset,
        base_system_tsc_offset,
        stopped_system_tsc_offset,
        system_accum_count_offset,
        count_offset,
        thread_user_tsc_offset,
        thread_system_tsc_offset,
        mask_check,
        read_value_fn,
        atomic_set_fn,
    );
    if rc != 0 {
        return rc;
    }

    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset);
        let rc = perf_reset_apply_event_result(
            sub,
            thread_base,
            counter_id_offset,
            use_invariant_tsc_offset,
            base_user_tsc_offset,
            stopped_user_tsc_offset,
            user_accum_count_offset,
            base_system_tsc_offset,
            stopped_system_tsc_offset,
            system_accum_count_offset,
            count_offset,
            thread_user_tsc_offset,
            thread_system_tsc_offset,
            mask_check,
            read_value_fn,
            atomic_set_fn,
        );
        if rc != 0 {
            return rc;
        }
        node = next;
    }

    0
}

#[allow(clippy::too_many_arguments)]
unsafe fn perf_stop_apply_event_result(
    event_base: *mut u8,
    thread_base: *mut u8,
    counter_mask: &mut CULong,
    stop_events: &mut [*mut c_void; PERF_STOP_EVENT_CAPACITY],
    stop_event_idx: &mut usize,
    counter_id_offset: SizeT,
    state_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    active_state: CInt,
    inactive_state: CInt,
    mask_check: PerfCounterMaskCheckFn,
) -> CLong {
    let counter_id = read_volatile(field_ptr::<CInt>(event_base, counter_id_offset));
    let bit = perf_event_bit_result(counter_id);
    let state = read_volatile(field_ptr::<CInt>(event_base, state_offset));
    if bit == 0 || mask_check(bit) == 0 || state != active_state {
        return 0;
    }

    let use_invariant = read_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset));
    if use_invariant != 0 {
        let stopped_user_ptr = field_ptr::<CLong>(event_base, stopped_user_tsc_offset);
        if read_volatile(stopped_user_ptr) == 0 {
            write_volatile(
                stopped_user_ptr,
                read_volatile(field_ptr::<CLong>(thread_base, thread_user_tsc_offset)),
            );
        }

        let stopped_system_ptr = field_ptr::<CLong>(event_base, stopped_system_tsc_offset);
        if read_volatile(stopped_system_ptr) == 0 {
            write_volatile(
                stopped_system_ptr,
                read_volatile(field_ptr::<CLong>(thread_base, thread_system_tsc_offset)),
            );
        }
    } else {
        if *stop_event_idx >= PERF_STOP_EVENT_CAPACITY {
            return -EINVAL as CLong;
        }
        *counter_mask |= bit;
        stop_events[*stop_event_idx] = event_base.cast::<c_void>();
        *stop_event_idx += 1;
    }

    write_volatile(field_ptr::<CInt>(event_base, state_offset), inactive_state);
    0
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_stop_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    group_leader_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    counter_id_offset: SizeT,
    state_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    thread_proc_offset: SizeT,
    proc_monitoring_event_offset: SizeT,
    proc_perf_status_offset: SizeT,
    active_state: CInt,
    inactive_state: CInt,
    pp_none: CInt,
    stop_flags: CInt,
    mask_check_fn: Option<PerfCounterMaskCheckFn>,
    counter_stop_fn: Option<PerfCounterStopFn>,
    update_fn: Option<PerfEventUpdateFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(mask_check) = mask_check_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let mut counter_mask = 0;
    let mut stop_events = [core::ptr::null_mut::<c_void>(); PERF_STOP_EVENT_CAPACITY];
    let mut stop_event_idx = 0usize;
    let rc = perf_stop_apply_event_result(
        leader_base,
        thread_base,
        &mut counter_mask,
        &mut stop_events,
        &mut stop_event_idx,
        counter_id_offset,
        state_offset,
        use_invariant_tsc_offset,
        stopped_user_tsc_offset,
        stopped_system_tsc_offset,
        thread_user_tsc_offset,
        thread_system_tsc_offset,
        active_state,
        inactive_state,
        mask_check,
    );
    if rc != 0 {
        return rc;
    }

    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset);
        let rc = perf_stop_apply_event_result(
            sub,
            thread_base,
            &mut counter_mask,
            &mut stop_events,
            &mut stop_event_idx,
            counter_id_offset,
            state_offset,
            use_invariant_tsc_offset,
            stopped_user_tsc_offset,
            stopped_system_tsc_offset,
            thread_user_tsc_offset,
            thread_system_tsc_offset,
            active_state,
            inactive_state,
            mask_check,
        );
        if rc != 0 {
            return rc;
        }
        node = next;
    }

    if counter_mask != 0 {
        let Some(counter_stop) = counter_stop_fn else {
            return -EINVAL as CLong;
        };
        let Some(update) = update_fn else {
            return -EINVAL as CLong;
        };
        counter_stop(counter_mask, stop_flags);
        for stop_event in stop_events.iter().take(stop_event_idx) {
            if !stop_event.is_null() {
                update(*stop_event);
            }
        }
    }

    let proc = read_volatile(field_ptr::<*mut c_void>(thread_base, thread_proc_offset));
    if proc.is_null() {
        return -EINVAL as CLong;
    }
    let proc_base = proc.cast::<u8>();
    write_volatile(
        field_ptr::<*mut c_void>(proc_base, proc_monitoring_event_offset),
        core::ptr::null_mut(),
    );
    write_volatile(
        field_ptr::<CInt>(proc_base, proc_perf_status_offset),
        pp_none,
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn perf_ioctl_body_result(
    event: *mut c_void,
    current_proc: *mut c_void,
    lock_arg: *mut c_void,
    cmd: CULong,
    inherit: CInt,
    enable_cmd: CULong,
    disable_cmd: CULong,
    reset_cmd: CULong,
    refresh_cmd: CULong,
    pp_reset: CInt,
    event_pid_offset: SizeT,
    proc_monitoring_event_offset: SizeT,
    proc_perf_status_offset: SizeT,
    start_fn: Option<PerfEventVoidFn>,
    stop_fn: Option<PerfEventVoidFn>,
    reset_fn: Option<PerfEventVoidFn>,
    find_fn: Option<SyscallFindProcessFn>,
    unlock_fn: Option<SyscallProcessUnlockFn>,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }

    let event_base = event.cast::<u8>();
    let pid = read_volatile(field_ptr::<CInt>(event_base, event_pid_offset));

    if cmd == enable_cmd {
        if pid == 0 {
            if current_proc.is_null() {
                return -EINVAL as CLong;
            }
            let Some(start) = start_fn else {
                return -EINVAL as CLong;
            };
            let proc_base = current_proc.cast::<u8>();
            write_volatile(
                field_ptr::<*mut c_void>(proc_base, proc_monitoring_event_offset),
                event,
            );
            start(event);
        } else if pid > 0 {
            let Some(find) = find_fn else {
                return -EINVAL as CLong;
            };
            let Some(unlock) = unlock_fn else {
                return -EINVAL as CLong;
            };
            let proc = find(pid, lock_arg);
            if proc.is_null() {
                return -EINVAL as CLong;
            }
            let proc_base = proc.cast::<u8>();
            let monitoring = field_ptr::<*mut c_void>(proc_base, proc_monitoring_event_offset);
            if read_volatile(monitoring).is_null() {
                write_volatile(monitoring, event);
                write_volatile(
                    field_ptr::<CInt>(proc_base, proc_perf_status_offset),
                    pp_reset,
                );
            }
            unlock(proc, lock_arg);
        }
        return 0;
    }

    if cmd == disable_cmd {
        if pid == 0 {
            let Some(stop) = stop_fn else {
                return -EINVAL as CLong;
            };
            stop(event);
        }
        return 0;
    }

    if cmd == reset_cmd {
        let Some(reset) = reset_fn else {
            return -EINVAL as CLong;
        };
        reset(event);
        return 0;
    }

    if cmd == refresh_cmd {
        if inherit != 0 {
            return -EINVAL as CLong;
        }
        return 0;
    }

    -1
}

fn perf_event_bit_result(index: CInt) -> CULong {
    if index < 0 || index >= (size_of::<CULong>() * 8) as CInt {
        0
    } else {
        1u64 << (index as u32)
    }
}

#[no_mangle]
pub unsafe extern "C" fn perf_close_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    counter_id_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    extra_reg_idx_offset: SizeT,
    thread_pmc_alloc_map_offset: SizeT,
    thread_extra_reg_alloc_map_offset: SizeT,
    free_fn: Option<SyscallMckfdFreeFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(free) = free_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let counter_id = read_volatile(field_ptr::<CInt>(event_base, counter_id_offset));
    let pmc_map = field_ptr::<CULong>(thread_base, thread_pmc_alloc_map_offset);
    let pmc_mask = !perf_event_bit_result(counter_id);
    write_volatile(pmc_map, read_volatile(pmc_map) & pmc_mask);

    if read_volatile(field_ptr::<CInt>(event_base, extra_reg_reg_offset)) != 0 {
        let idx = read_volatile(field_ptr::<CInt>(event_base, extra_reg_idx_offset));
        let extra_map = field_ptr::<CULong>(thread_base, thread_extra_reg_alloc_map_offset);
        let extra_mask = !perf_event_bit_result(idx);
        write_volatile(extra_map, read_volatile(extra_map) & extra_mask);
    }

    free(event);
    0
}

#[no_mangle]
pub unsafe extern "C" fn perf_fcntl_body_result(
    sfd: *mut c_void,
    ctx: *mut c_void,
    cmd: CInt,
    arg: CLong,
    fcntl_nr: CInt,
    set_sig_cmd: CInt,
    _setown_ex_cmd: CInt,
    mckfd_sig_no_offset: SizeT,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    if sfd.is_null() {
        return -EINVAL as CLong;
    }
    let Some(forward) = forward_fn else {
        return -EINVAL as CLong;
    };

    if cmd == set_sig_cmd {
        write_volatile(
            field_ptr::<CInt>(sfd.cast::<u8>(), mckfd_sig_no_offset),
            arg as CInt,
        );
    }

    forward(fcntl_nr, ctx)
}

#[no_mangle]
pub unsafe extern "C" fn perf_mmap_body_result(
    addr0: CULong,
    len0: SizeT,
    prot: CInt,
    flags: CInt,
    fd: CInt,
    off0: CLong,
    map_anonymous: CInt,
    prot_write: CInt,
    data_head_offset: SizeT,
    capabilities_offset: SizeT,
    cap_user_rdpmc_mask: CULong,
    do_mmap_fn: Option<PerfDoMmapFn>,
) -> CLong {
    let Some(do_mmap) = do_mmap_fn else {
        return -EINVAL as CLong;
    };

    let rc = do_mmap(
        addr0,
        len0,
        prot | prot_write,
        flags | map_anonymous,
        fd,
        off0,
        0,
        core::ptr::null_mut(),
    );

    let page = rc as CULong as *mut u8;
    write_volatile(field_ptr::<CULong>(page, data_head_offset), 16);
    let capabilities = field_ptr::<CULong>(page, capabilities_offset);
    write_volatile(
        capabilities,
        read_volatile(capabilities) | cap_user_rdpmc_mask,
    );

    rc
}

#[no_mangle]
pub extern "C" fn perf_event_open_validate_body_result(
    cpu: CInt,
    flags: CULong,
    attr_type: CULong,
    read_format: CULong,
    freq: CInt,
    sample_period: CULong,
    raw_type: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    unsupported_read_format_mask: CULong,
    sample_period_sign_bit: CULong,
) -> CInt {
    let mut unsupported = cpu > 0 || flags > 0;

    if attr_type != raw_type && attr_type != hardware_type && attr_type != hw_cache_type {
        unsupported = true;
    }
    if (read_format & unsupported_read_format_mask) != 0 {
        unsupported = true;
    }

    if freq != 0 {
        unsupported = true;
    } else if (sample_period & sample_period_sign_bit) != 0 {
        return -EINVAL;
    }

    if unsupported { -ENOENT } else { 0 }
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_alloc_init_body_result(
    event: *mut c_void,
    attr: *const c_void,
    event_size: SizeT,
    attr_size: SizeT,
    event_attr_offset: SizeT,
    group_entry_offset: SizeT,
    sibling_list_offset: SizeT,
    sample_freq_offset: SizeT,
    nr_siblings_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    parent_offset: SizeT,
    hw_sample_period_offset: SizeT,
    hw_last_period_offset: SizeT,
    hw_period_left_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    attr_type: CULong,
    attr_config: CULong,
    attr_freq: CInt,
    attr_sample_freq: CULong,
    attr_sample_period: CULong,
    hardware_type: CULong,
    ref_cpu_cycles_config: CULong,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    if event.is_null() || attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(atomic_set) = atomic_set_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let attr_base = attr.cast::<u8>();
    let mut i = 0;
    while i < event_size {
        write_volatile(event_base.add(i), 0);
        i += 1;
    }

    i = 0;
    let attr_dst = event_base.add(event_attr_offset);
    while i < attr_size {
        write_volatile(attr_dst.add(i), read_volatile(attr_base.add(i)));
        i += 1;
    }

    let group_entry = field_ptr::<AbiListHead>(event_base, group_entry_offset);
    write_volatile(core::ptr::addr_of_mut!((*group_entry).next), group_entry);
    write_volatile(core::ptr::addr_of_mut!((*group_entry).prev), group_entry);
    let sibling_list = field_ptr::<AbiListHead>(event_base, sibling_list_offset);
    write_volatile(core::ptr::addr_of_mut!((*sibling_list).next), sibling_list);
    write_volatile(core::ptr::addr_of_mut!((*sibling_list).prev), sibling_list);

    write_volatile(
        field_ptr::<CULong>(event_base, sample_freq_offset),
        attr_sample_freq,
    );
    write_volatile(field_ptr::<CInt>(event_base, nr_siblings_offset), 0);
    atomic_set(event_base.add(count_offset).cast::<c_void>(), 0);
    write_volatile(field_ptr::<CULong>(event_base, child_count_total_offset), 0);
    write_volatile(
        field_ptr::<*mut c_void>(event_base, parent_offset),
        core::ptr::null_mut(),
    );

    let sample_period = if attr_freq != 0 && attr_sample_freq != 0 {
        1
    } else {
        attr_sample_period
    };
    write_volatile(
        field_ptr::<CULong>(event_base, hw_sample_period_offset),
        sample_period,
    );
    write_volatile(
        field_ptr::<CULong>(event_base, hw_last_period_offset),
        sample_period,
    );
    atomic_set(
        event_base.add(hw_period_left_offset).cast::<c_void>(),
        sample_period as CLong,
    );

    if attr_type == hardware_type && attr_config == ref_cpu_cycles_config {
        write_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset), 1);
        return 1;
    }

    0
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_alloc_map_body_result(
    event_out: *mut *mut c_void,
    event: *mut c_void,
    hw_config_offset: SizeT,
    hw_config_ext_offset: SizeT,
    extra_reg_config_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    extra_reg_idx_offset: SizeT,
    attr_type: CULong,
    attr_config: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    raw_type: CULong,
    hw_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_extra_reg_map_fn: Option<PerfEventMapFn>,
    raw_event_map_fn: Option<PerfEventMapFn>,
    validate_event_fn: Option<PerfEventValidateFn>,
    extra_reg_id_fn: Option<PerfExtraRegIdFn>,
    extra_reg_msr_fn: Option<PerfExtraRegMsrFn>,
    extra_reg_idx_fn: Option<PerfExtraRegIdxFn>,
    hw_event_init_fn: Option<PerfHwEventInitFn>,
) -> CLong {
    if event_out.is_null() || event.is_null() {
        return -EINVAL as CLong;
    }
    let Some(validate_event) = validate_event_fn else {
        return -EINVAL as CLong;
    };
    let Some(extra_reg_id) = extra_reg_id_fn else {
        return -EINVAL as CLong;
    };
    let Some(extra_reg_msr) = extra_reg_msr_fn else {
        return -EINVAL as CLong;
    };
    let Some(extra_reg_idx) = extra_reg_idx_fn else {
        return -EINVAL as CLong;
    };
    let Some(hw_event_init) = hw_event_init_fn else {
        return -EINVAL as CLong;
    };

    let mut extra_config = 0;
    let val = if attr_type == hardware_type {
        let Some(hw_event_map) = hw_event_map_fn else {
            return -EINVAL as CLong;
        };
        hw_event_map(attr_config)
    } else if attr_type == hw_cache_type {
        let Some(hw_cache_event_map) = hw_cache_event_map_fn else {
            return -EINVAL as CLong;
        };
        let Some(hw_cache_extra_reg_map) = hw_cache_extra_reg_map_fn else {
            return -EINVAL as CLong;
        };
        extra_config = hw_cache_extra_reg_map(attr_config);
        hw_cache_event_map(attr_config)
    } else if attr_type == raw_type {
        let Some(raw_event_map) = raw_event_map_fn else {
            return -EINVAL as CLong;
        };
        raw_event_map(attr_config)
    } else {
        return -EINVAL as CLong;
    };

    if validate_event(val) == 0 {
        return -ENOENT as CLong;
    }

    let event_base = event.cast::<u8>();
    write_volatile(field_ptr::<CULong>(event_base, hw_config_offset), val);
    write_volatile(
        field_ptr::<CULong>(event_base, hw_config_ext_offset),
        extra_config,
    );

    let ereg_id = extra_reg_id(val, extra_config);
    if ereg_id >= 0 {
        write_volatile(
            field_ptr::<CULong>(event_base, extra_reg_config_offset),
            extra_config,
        );
        write_volatile(
            field_ptr::<u32>(event_base, extra_reg_reg_offset),
            extra_reg_msr(ereg_id),
        );
        write_volatile(
            field_ptr::<CInt>(event_base, extra_reg_idx_offset),
            extra_reg_idx(ereg_id),
        );
    }

    let ret = hw_event_init(event);
    if ret == 0 {
        write_volatile(event_out, event);
    }
    ret as CLong
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_alloc_body_result(
    event_out: *mut *mut c_void,
    attr: *const c_void,
    event_size: SizeT,
    attr_size: SizeT,
    alloc_flags: CULong,
    event_attr_offset: SizeT,
    group_entry_offset: SizeT,
    sibling_list_offset: SizeT,
    sample_freq_offset: SizeT,
    nr_siblings_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    parent_offset: SizeT,
    hw_sample_period_offset: SizeT,
    hw_last_period_offset: SizeT,
    hw_period_left_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    hw_config_offset: SizeT,
    hw_config_ext_offset: SizeT,
    extra_reg_config_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    extra_reg_idx_offset: SizeT,
    attr_type: CULong,
    attr_config: CULong,
    attr_freq: CInt,
    attr_sample_freq: CULong,
    attr_sample_period: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    raw_type: CULong,
    ref_cpu_cycles_config: CULong,
    alloc_fn: Option<SyscallPolicyAllocFn>,
    free_fn: Option<SyscallMckfdFreeFn>,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
    hw_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_extra_reg_map_fn: Option<PerfEventMapFn>,
    raw_event_map_fn: Option<PerfEventMapFn>,
    validate_event_fn: Option<PerfEventValidateFn>,
    extra_reg_id_fn: Option<PerfExtraRegIdFn>,
    extra_reg_msr_fn: Option<PerfExtraRegMsrFn>,
    extra_reg_idx_fn: Option<PerfExtraRegIdxFn>,
    hw_event_init_fn: Option<PerfHwEventInitFn>,
) -> CLong {
    if event_out.is_null() || attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(alloc) = alloc_fn else {
        return -EINVAL as CLong;
    };
    let Some(free) = free_fn else {
        return -EINVAL as CLong;
    };

    let event = alloc(event_size, alloc_flags);
    if event.is_null() {
        return -ENOMEM as CLong;
    }

    let init = perf_event_alloc_init_body_result(
        event,
        attr,
        event_size,
        attr_size,
        event_attr_offset,
        group_entry_offset,
        sibling_list_offset,
        sample_freq_offset,
        nr_siblings_offset,
        count_offset,
        child_count_total_offset,
        parent_offset,
        hw_sample_period_offset,
        hw_last_period_offset,
        hw_period_left_offset,
        use_invariant_tsc_offset,
        attr_type,
        attr_config,
        attr_freq,
        attr_sample_freq,
        attr_sample_period,
        hardware_type,
        ref_cpu_cycles_config,
        atomic_set_fn,
    );
    if init < 0 {
        free(event);
        return init;
    }
    if init > 0 {
        write_volatile(event_out, event);
        return 0;
    }

    let ret = perf_event_alloc_map_body_result(
        event_out,
        event,
        hw_config_offset,
        hw_config_ext_offset,
        extra_reg_config_offset,
        extra_reg_reg_offset,
        extra_reg_idx_offset,
        attr_type,
        attr_config,
        hardware_type,
        hw_cache_type,
        raw_type,
        hw_event_map_fn,
        hw_cache_event_map_fn,
        hw_cache_extra_reg_map_fn,
        raw_event_map_fn,
        validate_event_fn,
        extra_reg_id_fn,
        extra_reg_msr_fn,
        extra_reg_idx_fn,
        hw_event_init_fn,
    );
    if ret != 0 {
        free(event);
    }
    ret
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_open_group_body_result(
    event: *mut c_void,
    proc: *mut c_void,
    group_fd: CInt,
    counter_idx: CInt,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_data_offset: SizeT,
    event_group_leader_offset: SizeT,
    event_sibling_list_offset: SizeT,
    event_group_entry_offset: SizeT,
    event_nr_siblings_offset: SizeT,
    event_pmc_status_offset: SizeT,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }

    let event_base = event.cast::<u8>();
    let leader = if group_fd == -1 {
        write_volatile(
            field_ptr::<*mut c_void>(event_base, event_group_leader_offset),
            event,
        );
        write_volatile(field_ptr::<CULong>(event_base, event_pmc_status_offset), 0);
        event
    } else {
        if proc.is_null() {
            return -EINVAL as CLong;
        }

        let mut cur = read_volatile(field_ptr::<*mut c_void>(
            proc.cast::<u8>(),
            proc_mckfd_offset,
        ));
        let mut found = core::ptr::null_mut::<c_void>();
        while !cur.is_null() {
            let cur_base = cur.cast::<u8>();
            if read_volatile(field_ptr::<CInt>(cur_base, mckfd_fd_offset)) == group_fd {
                let data = read_volatile(field_ptr::<CLong>(cur_base, mckfd_data_offset));
                found = data as usize as *mut c_void;
                break;
            }
            cur = read_volatile(field_ptr::<*mut c_void>(cur_base, mckfd_next_offset));
        }
        if found.is_null() {
            return -EINVAL as CLong;
        }

        write_volatile(
            field_ptr::<*mut c_void>(event_base, event_group_leader_offset),
            found,
        );

        let leader_base = found.cast::<u8>();
        let entry = field_ptr::<AbiListHead>(event_base, event_group_entry_offset);
        let head = field_ptr::<AbiListHead>(leader_base, event_sibling_list_offset);
        let prev = read_volatile(core::ptr::addr_of!((*head).prev));
        if prev.is_null() {
            return -EINVAL as CLong;
        }
        write_volatile(core::ptr::addr_of_mut!((*entry).next), head);
        write_volatile(core::ptr::addr_of_mut!((*entry).prev), prev);
        write_volatile(core::ptr::addr_of_mut!((*prev).next), entry);
        write_volatile(core::ptr::addr_of_mut!((*head).prev), entry);

        let nr_siblings = field_ptr::<CInt>(leader_base, event_nr_siblings_offset);
        write_volatile(nr_siblings, read_volatile(nr_siblings).wrapping_add(1));
        found
    };

    let leader_base = leader.cast::<u8>();
    let pmc_status = field_ptr::<CULong>(leader_base, event_pmc_status_offset);
    write_volatile(
        pmc_status,
        read_volatile(pmc_status) | perf_event_bit_result(counter_idx),
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_counter_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    pid: CInt,
    event_pid_offset: SizeT,
    event_counter_id_offset: SizeT,
    counter_alloc_fn: Option<PerfCounterAllocFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(counter_alloc) = counter_alloc_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    write_volatile(field_ptr::<CInt>(event_base, event_pid_offset), pid);
    let counter_idx = counter_alloc(thread, event);
    if counter_idx < 0 {
        return counter_idx as CLong;
    }
    write_volatile(
        field_ptr::<CInt>(event_base, event_counter_id_offset),
        counter_idx,
    );

    counter_idx as CLong
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_linux_fd_body_result(
    request: *mut SyscallRequest,
    thread: *mut c_void,
    counter_idx: CInt,
    perf_event_open_nr: CInt,
    cpu: CInt,
    thread_pmc_alloc_map_offset: SizeT,
    syscall_fn: Option<PerfOpenSyscallFn>,
) -> CLong {
    if request.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(syscall) = syscall_fn else {
        return -EINVAL as CLong;
    };

    write_volatile(
        core::ptr::addr_of_mut!((*request).number),
        perf_event_open_nr as CULong,
    );
    write_volatile(core::ptr::addr_of_mut!((*request).args[0]), 0);
    let fd = syscall(request, cpu);
    if fd < 0 {
        return fd;
    }

    let thread_base = thread.cast::<u8>();
    let pmc_map = field_ptr::<CULong>(thread_base, thread_pmc_alloc_map_offset);
    write_volatile(
        pmc_map,
        read_volatile(pmc_map) | perf_event_bit_result(counter_idx),
    );

    fd
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_open_mckfd_publish_body_result(
    sfd: *mut c_void,
    event: *mut c_void,
    proc: *mut c_void,
    fd: CInt,
    proc_mckfd_lock_offset: SizeT,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_sig_no_offset: SizeT,
    mckfd_data_offset: SizeT,
    mckfd_read_cb_offset: SizeT,
    mckfd_ioctl_cb_offset: SizeT,
    mckfd_mmap_cb_offset: SizeT,
    mckfd_close_cb_offset: SizeT,
    mckfd_fcntl_cb_offset: SizeT,
    read_fn: Option<SyscallMckfdLongFn>,
    ioctl_fn: Option<SyscallMckfdIntFn>,
    mmap_fn: Option<SyscallMckfdLongFn>,
    close_fn: Option<SyscallMckfdIntFn>,
    fcntl_fn: Option<SyscallMckfdIntFn>,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    if sfd.is_null() || event.is_null() || proc.is_null() {
        return -EINVAL as CLong;
    }
    if read_fn.is_none()
        || ioctl_fn.is_none()
        || mmap_fn.is_none()
        || close_fn.is_none()
        || fcntl_fn.is_none()
    {
        return -EINVAL as CLong;
    }
    let Some(lock) = lock_fn else {
        return -EINVAL as CLong;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL as CLong;
    };

    let sfd_base = sfd.cast::<u8>();
    write_volatile(field_ptr::<CInt>(sfd_base, mckfd_fd_offset), fd);
    write_volatile(field_ptr::<CInt>(sfd_base, mckfd_sig_no_offset), -1);
    write_volatile(
        field_ptr::<CLong>(sfd_base, mckfd_data_offset),
        event as isize as CLong,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdLongFn>>(sfd_base, mckfd_read_cb_offset),
        read_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdIntFn>>(sfd_base, mckfd_ioctl_cb_offset),
        ioctl_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdLongFn>>(sfd_base, mckfd_mmap_cb_offset),
        mmap_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdIntFn>>(sfd_base, mckfd_close_cb_offset),
        close_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdIntFn>>(sfd_base, mckfd_fcntl_cb_offset),
        fcntl_fn,
    );

    let proc_base = proc.cast::<u8>();
    let lock_ptr = field_ptr::<c_void>(proc_base, proc_mckfd_lock_offset);
    let irqstate = lock(lock_ptr);
    let headp = field_ptr::<*mut c_void>(proc_base, proc_mckfd_offset);
    let old_head = read_volatile(headp);
    write_volatile(
        field_ptr::<*mut c_void>(sfd_base, mckfd_next_offset),
        old_head,
    );
    write_volatile(headp, sfd);
    unlock(lock_ptr, irqstate);

    fd as CLong
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_open_body_result(
    request: *mut SyscallRequest,
    thread: *mut c_void,
    proc: *mut c_void,
    attr: *mut c_void,
    pid: CInt,
    group_fd: CInt,
    perf_event_open_nr: CInt,
    cpu: CInt,
    mckfd_size: SizeT,
    mckfd_alloc_flags: CULong,
    event_pid_offset: SizeT,
    event_counter_id_offset: SizeT,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_data_offset: SizeT,
    event_group_leader_offset: SizeT,
    event_sibling_list_offset: SizeT,
    event_group_entry_offset: SizeT,
    event_nr_siblings_offset: SizeT,
    event_pmc_status_offset: SizeT,
    thread_pmc_alloc_map_offset: SizeT,
    proc_mckfd_lock_offset: SizeT,
    mckfd_sig_no_offset: SizeT,
    mckfd_read_cb_offset: SizeT,
    mckfd_ioctl_cb_offset: SizeT,
    mckfd_mmap_cb_offset: SizeT,
    mckfd_close_cb_offset: SizeT,
    mckfd_fcntl_cb_offset: SizeT,
    event_alloc_fn: Option<PerfOpenAllocEventFn>,
    counter_alloc_fn: Option<PerfCounterAllocFn>,
    syscall_fn: Option<PerfOpenSyscallFn>,
    mckfd_alloc_fn: Option<SyscallPolicyAllocFn>,
    read_fn: Option<SyscallMckfdLongFn>,
    ioctl_fn: Option<SyscallMckfdIntFn>,
    mmap_fn: Option<SyscallMckfdLongFn>,
    close_fn: Option<SyscallMckfdIntFn>,
    fcntl_fn: Option<SyscallMckfdIntFn>,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    if request.is_null() || thread.is_null() || proc.is_null() || attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(event_alloc) = event_alloc_fn else {
        return -EINVAL as CLong;
    };
    let Some(mckfd_alloc) = mckfd_alloc_fn else {
        return -EINVAL as CLong;
    };

    let mut event = core::ptr::null_mut::<c_void>();
    let mut ret = event_alloc(core::ptr::addr_of_mut!(event), attr);
    if ret != 0 {
        return ret as CLong;
    }

    let counter_idx = perf_event_open_counter_body_result(
        event,
        thread,
        pid,
        event_pid_offset,
        event_counter_id_offset,
        counter_alloc_fn,
    );
    if counter_idx < 0 {
        return counter_idx;
    }

    let group_rc = perf_event_open_group_body_result(
        event,
        proc,
        group_fd,
        counter_idx as CInt,
        proc_mckfd_offset,
        mckfd_next_offset,
        mckfd_fd_offset,
        mckfd_data_offset,
        event_group_leader_offset,
        event_sibling_list_offset,
        event_group_entry_offset,
        event_nr_siblings_offset,
        event_pmc_status_offset,
    );
    if group_rc != 0 {
        return group_rc;
    }

    let fd = perf_event_open_linux_fd_body_result(
        request,
        thread,
        counter_idx as CInt,
        perf_event_open_nr,
        cpu,
        thread_pmc_alloc_map_offset,
        syscall_fn,
    );
    if fd < 0 {
        return fd;
    }

    let sfd = mckfd_alloc(mckfd_size, mckfd_alloc_flags);
    if sfd.is_null() {
        return -ENOMEM as CLong;
    }

    ret = perf_event_open_mckfd_publish_body_result(
        sfd,
        event,
        proc,
        fd as CInt,
        proc_mckfd_lock_offset,
        proc_mckfd_offset,
        mckfd_next_offset,
        mckfd_fd_offset,
        mckfd_sig_no_offset,
        mckfd_data_offset,
        mckfd_read_cb_offset,
        mckfd_ioctl_cb_offset,
        mckfd_mmap_cb_offset,
        mckfd_close_cb_offset,
        mckfd_fcntl_cb_offset,
        read_fn,
        ioctl_fn,
        mmap_fn,
        close_fn,
        fcntl_fn,
        lock_fn,
        unlock_fn,
    ) as CInt;
    ret as CLong
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_open_entry_body_result(
    request: *mut SyscallRequest,
    thread: *mut c_void,
    proc: *mut c_void,
    attr: *mut c_void,
    user_attr_addr: CULong,
    attr_size: SizeT,
    attr_type_offset: SizeT,
    attr_read_format_offset: SizeT,
    attr_sample_period_offset: SizeT,
    pid: CInt,
    validation_cpu: CInt,
    group_fd: CInt,
    flags: CULong,
    linux_cpu: CInt,
    raw_type: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    unsupported_read_format_mask: CULong,
    sample_period_sign_bit: CULong,
    perf_event_open_nr: CInt,
    mckfd_size: SizeT,
    mckfd_alloc_flags: CULong,
    event_pid_offset: SizeT,
    event_counter_id_offset: SizeT,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_data_offset: SizeT,
    event_group_leader_offset: SizeT,
    event_sibling_list_offset: SizeT,
    event_group_entry_offset: SizeT,
    event_nr_siblings_offset: SizeT,
    event_pmc_status_offset: SizeT,
    thread_pmc_alloc_map_offset: SizeT,
    proc_mckfd_lock_offset: SizeT,
    mckfd_sig_no_offset: SizeT,
    mckfd_read_cb_offset: SizeT,
    mckfd_ioctl_cb_offset: SizeT,
    mckfd_mmap_cb_offset: SizeT,
    mckfd_close_cb_offset: SizeT,
    mckfd_fcntl_cb_offset: SizeT,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    attr_freq_fn: Option<PerfAttrFreqFn>,
    event_alloc_fn: Option<PerfOpenAllocEventFn>,
    counter_alloc_fn: Option<PerfCounterAllocFn>,
    syscall_fn: Option<PerfOpenSyscallFn>,
    mckfd_alloc_fn: Option<SyscallPolicyAllocFn>,
    read_fn: Option<SyscallMckfdLongFn>,
    ioctl_fn: Option<SyscallMckfdIntFn>,
    mmap_fn: Option<SyscallMckfdLongFn>,
    close_fn: Option<SyscallMckfdIntFn>,
    fcntl_fn: Option<SyscallMckfdIntFn>,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    if attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(copy_from_user) = copy_from_fn else {
        return -EINVAL as CLong;
    };
    let Some(attr_freq) = attr_freq_fn else {
        return -EINVAL as CLong;
    };

    if copy_from_user(attr.cast::<u8>(), user_attr_addr, attr_size) != 0 {
        return -EFAULT as CLong;
    }

    let attr_base = attr.cast::<u8>();
    let attr_type = read_volatile(field_ptr::<u32>(attr_base, attr_type_offset)) as CULong;
    let read_format = read_volatile(field_ptr::<CULong>(attr_base, attr_read_format_offset));
    let sample_period = read_volatile(field_ptr::<CULong>(attr_base, attr_sample_period_offset));
    let freq = attr_freq(attr.cast_const());

    let ret = perf_event_open_validate_body_result(
        validation_cpu,
        flags,
        attr_type,
        read_format,
        freq,
        sample_period,
        raw_type,
        hardware_type,
        hw_cache_type,
        unsupported_read_format_mask,
        sample_period_sign_bit,
    );
    if ret != 0 {
        return ret as CLong;
    }

    perf_event_open_body_result(
        request,
        thread,
        proc,
        attr,
        pid,
        group_fd,
        perf_event_open_nr,
        linux_cpu,
        mckfd_size,
        mckfd_alloc_flags,
        event_pid_offset,
        event_counter_id_offset,
        proc_mckfd_offset,
        mckfd_next_offset,
        mckfd_fd_offset,
        mckfd_data_offset,
        event_group_leader_offset,
        event_sibling_list_offset,
        event_group_entry_offset,
        event_nr_siblings_offset,
        event_pmc_status_offset,
        thread_pmc_alloc_map_offset,
        proc_mckfd_lock_offset,
        mckfd_sig_no_offset,
        mckfd_read_cb_offset,
        mckfd_ioctl_cb_offset,
        mckfd_mmap_cb_offset,
        mckfd_close_cb_offset,
        mckfd_fcntl_cb_offset,
        event_alloc_fn,
        counter_alloc_fn,
        syscall_fn,
        mckfd_alloc_fn,
        read_fn,
        ioctl_fn,
        mmap_fn,
        close_fn,
        fcntl_fn,
        lock_fn,
        unlock_fn,
    )
}

#[no_mangle]
pub extern "C" fn exit_group_status_result(rc: CInt, sig: CInt) -> CULong {
    EXIT_GROUP_STATUS_CONFIRMED | (((rc as CULong) & 0xff) << 8) | ((sig as CULong) & 0xff)
}

#[no_mangle]
pub extern "C" fn terminate_thread_active_result(status: CInt) -> CInt {
    (status != PS_EXITED && status != PS_ZOMBIE) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_process_exited_result(status: CInt) -> CInt {
    (status == PS_EXITED) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_thread_is_other_result(
    thread: *const c_void,
    current_thread: *const c_void,
) -> CInt {
    (thread != current_thread) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_report_thread_ptrace_result(ptrace: CInt) -> CInt {
    (ptrace != 0) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_child_cleanup_needed_result(
    children_empty: CInt,
    ptraced_children_empty: CInt,
) -> CInt {
    (children_empty == 0 || ptraced_children_empty == 0) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_release_child_needed_result(free_child: CInt) -> CInt {
    (free_child != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_lookup_missing_result(process: *const c_void) -> CInt {
    process.is_null() as CInt
}

#[no_mangle]
pub extern "C" fn process_cleanup_tofu_needed_result(enable_tofu: CInt) -> CInt {
    (enable_tofu != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_cleanup_fd_path_free_needed_result(path: *const c_void) -> CInt {
    (!path.is_null()) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_cleanup_fd_body_result(
    pid: CInt,
    fd: CInt,
    lock_arg: *mut c_void,
    find_fn: Option<SyscallFindProcessFn>,
    unlock_fn: Option<SyscallProcessUnlockFn>,
    cleanup_fn: Option<ProcessCleanupFdFn>,
    missing_log_fn: Option<ProcessCleanupMissingLogFn>,
) -> CLong {
    let Some(find) = find_fn else {
        return -EINVAL as CLong;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL as CLong;
    };

    let proc = find(pid, lock_arg);
    if process_lookup_missing_result(proc) != 0 {
        if let Some(log) = missing_log_fn {
            log(pid);
        }
        return 0;
    }

    let Some(cleanup) = cleanup_fn else {
        unlock(proc, lock_arg);
        return -EINVAL as CLong;
    };

    let _ = cleanup(proc, fd);
    unlock(proc, lock_arg);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_cleanup_before_terminate_body_result(
    pid: CInt,
    lock_arg: *mut c_void,
    enable_tofu: CInt,
    first_fd: CInt,
    max_fd: CInt,
    find_fn: Option<SyscallFindProcessFn>,
    unlock_fn: Option<SyscallProcessUnlockFn>,
    cleanup_fn: Option<ProcessCleanupFdFn>,
) -> CLong {
    let Some(find) = find_fn else {
        return -EINVAL as CLong;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL as CLong;
    };

    let proc = find(pid, lock_arg);
    if process_lookup_missing_result(proc) != 0 {
        return 0;
    }

    if process_cleanup_tofu_needed_result(enable_tofu) != 0 {
        let Some(cleanup) = cleanup_fn else {
            unlock(proc, lock_arg);
            return -EINVAL as CLong;
        };

        let mut fd = first_fd;
        while fd < max_fd {
            let _ = cleanup(proc, fd);
            fd += 1;
        }
    }

    unlock(proc, lock_arg);
    0
}

#[no_mangle]
pub extern "C" fn terminate_host_detached_thread_release_needed_result(
    process: *const c_void,
    thread: *const c_void,
) -> CInt {
    (process.is_null() && !thread.is_null()) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_host_kill_needed_result(nohost: CInt) -> CInt {
    (nohost != 1) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn terminate_host_body_result(
    pid: CInt,
    detached_thread: *mut c_void,
    current_thread: *mut c_void,
    lock_arg: *mut c_void,
    proc_nohost_offset: SizeT,
    thread_proc_offset: SizeT,
    thread_refcount_offset: SizeT,
    find_fn: Option<SyscallFindProcessFn>,
    unlock_fn: Option<SyscallProcessUnlockFn>,
    ref_set_fn: Option<TerminateHostRefSetFn>,
    release_thread_fn: Option<WaitThreadSideEffectFn>,
    release_process_fn: Option<WaitThreadSideEffectFn>,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
) -> CLong {
    let Some(find) = find_fn else {
        return -EINVAL as CLong;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL as CLong;
    };

    let proc = find(pid, lock_arg);
    if process_lookup_missing_result(proc) != 0 {
        if terminate_host_detached_thread_release_needed_result(proc, detached_thread) != 0 {
            let Some(ref_set) = ref_set_fn else {
                return -EINVAL as CLong;
            };
            let Some(release_thread) = release_thread_fn else {
                return -EINVAL as CLong;
            };
            let Some(release_process) = release_process_fn else {
                return -EINVAL as CLong;
            };

            let thread_base = detached_thread.cast::<u8>();
            let thread_proc =
                read_volatile(field_ptr::<*mut c_void>(thread_base, thread_proc_offset));
            ref_set(thread_base.add(thread_refcount_offset).cast::<c_void>(), 1);
            release_thread(detached_thread);
            release_process(thread_proc);
        }
        return 0;
    }

    let proc_base = proc.cast::<u8>();
    let nohost = field_ptr::<CInt>(proc_base, proc_nohost_offset);
    if terminate_host_kill_needed_result(read_volatile(nohost)) == 0 {
        unlock(proc, lock_arg);
        return 0;
    }

    let Some(do_kill) = do_kill_fn else {
        unlock(proc, lock_arg);
        return -EINVAL as CLong;
    };
    write_volatile(nohost, 1);
    unlock(proc, lock_arg);
    do_kill(current_thread, pid, -1, SIGKILL, core::ptr::null(), 0)
}

#[no_mangle]
pub extern "C" fn finalize_process_parent_is_pid1_result(
    parent: *const c_void,
    pid1: *const c_void,
) -> CInt {
    (parent == pid1) as CInt
}

#[no_mangle]
pub extern "C" fn finalize_process_parent_signal_needed_result(termsig: CInt) -> CInt {
    (termsig != 0) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_status_result(rc: CInt, sig: CInt) -> CInt {
    ((rc & 0x00ff) << 8) | (sig & 0xff)
}

#[no_mangle]
pub extern "C" fn terminate_report_thread_release_needed_result(
    same_process: CInt,
    termsig: CInt,
) -> CInt {
    (same_process != 0 && termsig != 0 && termsig != SIGCHLD) as CInt
}

#[no_mangle]
pub extern "C" fn terminate_child_action_result(
    ppid_is_exiting: CInt,
    parent_is_exiting: CInt,
    child_status: CInt,
) -> CInt {
    if ppid_is_exiting == 0 {
        TERMINATE_CHILD_ACTION_NONE
    } else if child_status == PS_ZOMBIE {
        TERMINATE_CHILD_ACTION_FREE_ZOMBIE
    } else if parent_is_exiting != 0 {
        TERMINATE_CHILD_ACTION_REPARENT_CHILD
    } else {
        TERMINATE_CHILD_ACTION_REPARENT_PTRACED
    }
}

#[no_mangle]
pub extern "C" fn clone_pthread_marker_result(
    clone_flags: CInt,
    newsp: CULong,
    parent_tidptr: CULong,
) -> CInt {
    if (clone_flags & CLONE_VM) != 0 && newsp == parent_tidptr {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_prctl_body_result(
    pid: CInt,
    code: CLong,
    addr: CLong,
    word_size: SizeT,
    user_regs_fs_base_offset: SizeT,
    user_regs_gs_base_offset: SizeT,
    offsets: *const ArchPtraceUserOffsets,
    find_fn: Option<PtraceFindThreadFn>,
    unlock_fn: Option<PtraceThreadUnlockFn>,
    read_user_fn: Option<PtraceReadUserWordFn>,
    write_user_fn: Option<PtraceWriteUserWordFn>,
    copy_to_fn: Option<PtraceUserCopyToFn>,
) -> CLong {
    if offsets.is_null() {
        return -(EFAULT as CLong);
    }
    let Some(find_thread) = find_fn else {
        return -(EFAULT as CLong);
    };
    let Some(unlock_thread) = unlock_fn else {
        return -(EFAULT as CLong);
    };
    let child = find_thread(pid, pid);
    if child == 0 {
        return -(ESRCH as CLong);
    }

    let offsets = &*offsets;
    let thread_base = child as *mut u8;
    let proc = read_volatile(field_ptr::<*mut c_void>(
        thread_base,
        offsets.thread_proc_offset,
    ));
    let mut rc = -(EIO as CLong);
    if !proc.is_null() {
        let status = read_volatile(field_ptr::<CInt>(
            proc.cast::<u8>(),
            offsets.proc_status_offset,
        ));
        if (status & (PS_TRACED | PS_STOPPED)) != 0 {
            if code == ARCH_GET_FS as CLong || code == ARCH_GET_GS as CLong {
                let Some(read_user) = read_user_fn else {
                    unlock_thread(child);
                    return -(EFAULT as CLong);
                };
                let Some(copy_to_user) = copy_to_fn else {
                    unlock_thread(child);
                    return -(EFAULT as CLong);
                };
                let mut value = 0;
                let reg_offset = if code == ARCH_GET_FS as CLong {
                    user_regs_fs_base_offset
                } else {
                    user_regs_gs_base_offset
                };
                rc = read_user(child, reg_offset as CLong, &mut value);
                if rc == 0 {
                    rc = copy_to_user(
                        addr as CULong,
                        (&value as *const CULong).cast::<u8>(),
                        word_size,
                    );
                }
            } else if code == ARCH_SET_FS as CLong || code == ARCH_SET_GS as CLong {
                let Some(write_user) = write_user_fn else {
                    unlock_thread(child);
                    return -(EFAULT as CLong);
                };
                let reg_offset = if code == ARCH_SET_FS as CLong {
                    user_regs_fs_base_offset
                } else {
                    user_regs_gs_base_offset
                };
                rc = write_user(child, reg_offset as CLong, addr as CULong);
            } else {
                rc = -(EINVAL as CLong);
            }
        }
    }
    unlock_thread(child);
    rc
}

#[no_mangle]
pub extern "C" fn clone_flags_result(clone_flags: CInt, coredump_barrier_count: CInt) -> CInt {
    let termsig = clone_flags & CSIGNAL;

    if ((clone_flags & CLONE_VM) != 0 && (clone_flags & CLONE_THREAD) == 0)
        || ((clone_flags & CLONE_VM) == 0 && (clone_flags & CLONE_THREAD) != 0)
    {
        return -EINVAL;
    }

    if termsig < 0 || NSIG < termsig {
        return -EINVAL;
    }

    if (clone_flags & CLONE_SIGHAND) != 0 && (clone_flags & CLONE_VM) == 0 {
        return -EINVAL;
    }

    if (clone_flags & CLONE_THREAD) != 0 && (clone_flags & CLONE_SIGHAND) == 0 {
        return -EINVAL;
    }

    if (clone_flags & CLONE_FS) != 0 && (clone_flags & CLONE_NEWNS) != 0 {
        return -EINVAL;
    }

    if (clone_flags & CLONE_NEWIPC) != 0 && (clone_flags & CLONE_SYSVSEM) != 0 {
        return -EINVAL;
    }

    if (clone_flags & CLONE_NEWPID) != 0 && (clone_flags & CLONE_THREAD) != 0 {
        return -EINVAL;
    }

    if coredump_barrier_count != 0 {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn clone_host_parent_flags_result(clone_flags: CInt, ppid_parent_pid: CInt) -> CInt {
    if (clone_flags & CLONE_PARENT) != 0 && ppid_parent_pid != 1 {
        clone_flags
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn clone_report_thread_result(clone_flags: CInt, termsig: CInt) -> CInt {
    if (clone_flags & CLONE_VM) != 0 && termsig != 0 && termsig != SIGCHLD {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn clone_parent_tid_store_needed_result(clone_flags: CInt) -> CInt {
    if (clone_flags & CLONE_PARENT_SETTID) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn clone_child_cleartid_needed_result(clone_flags: CInt) -> CInt {
    if (clone_flags & CLONE_CHILD_CLEARTID) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn clone_child_tid_store_needed_result(clone_flags: CInt) -> CInt {
    if (clone_flags & CLONE_CHILD_SETTID) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn clone_tls_source_result(clone_flags: CInt) -> CInt {
    if (clone_flags & CLONE_SETTLS) != 0 {
        CLONE_TLS_SOURCE_ARGUMENT
    } else {
        CLONE_TLS_SOURCE_INHERIT
    }
}

#[no_mangle]
pub extern "C" fn clone_use_last_cpu_result(mod_clone: CInt, uti_use_last_cpu: CInt) -> CInt {
    if mod_clone == SPAWN_TO_REMOTE && uti_use_last_cpu != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn clone_remote_spawn_result(previous_mod_clone: CInt) -> CInt {
    if previous_mod_clone == SPAWN_TO_REMOTE {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn clone_parent_use_pid1_result(parent_status: CInt) -> CInt {
    if parent_status == PS_EXITED || parent_status == PS_ZOMBIE {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ptrace_exec_event_signal_result(ptrace: CInt) -> CInt {
    if (ptrace & (PT_TRACE_EXEC | PTRACE_O_TRACEEXEC)) != 0 {
        SIGTRAP | (PTRACE_EVENT_EXEC << 8)
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn ptrace_syscall_event_signal_result(ptrace: CInt) -> CInt {
    if (ptrace & PT_TRACE_SYSCALL) != 0 {
        SIGTRAP
            | if (ptrace & PTRACE_O_TRACESYSGOOD) != 0 {
                0x80
            } else {
                0
            }
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_syscall_event_body_result(
    thread: *mut c_void,
    ptrace_offset: SizeT,
    report_signal_fn: Option<PtraceReportSignalFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let thread_base = thread.cast::<u8>();
    let ptrace = read_volatile(field_ptr::<CInt>(thread_base, ptrace_offset));
    let sig = ptrace_syscall_event_signal_result(ptrace);
    if sig != 0 {
        let Some(report_signal) = report_signal_fn else {
            return -EINVAL;
        };
        report_signal(thread, sig);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_report_exec_body_result(
    thread: *mut c_void,
    syscall_ctx: *mut c_void,
    offsets: *const PtraceReportExecOffsets,
    kernel_context_size: SizeT,
    user_context_size: SizeT,
    kernel_context_scratch: *mut c_void,
    preempt_enable_fn: Option<PtraceVoidFn>,
    preempt_disable_fn: Option<PtraceVoidFn>,
    report_signal_fn: Option<PtraceReportSignalFn>,
    arch_syscall_event_fn: Option<PtraceArchSyscallEventFn>,
) -> CInt {
    if thread.is_null()
        || syscall_ctx.is_null()
        || offsets.is_null()
        || kernel_context_scratch.is_null()
        || kernel_context_size == 0
        || user_context_size == 0
    {
        return -EINVAL;
    }

    let offsets = &*offsets;
    let thread_base = thread.cast::<u8>();
    let ctx_ptr = thread_base.add(offsets.thread_ctx_offset);
    let ptrace = read_volatile(field_ptr::<CInt>(thread_base, offsets.thread_ptrace_offset));
    let sig = ptrace_exec_event_signal_result(ptrace);
    if sig != 0 {
        let Some(preempt_enable) = preempt_enable_fn else {
            return -EINVAL;
        };
        let Some(preempt_disable) = preempt_disable_fn else {
            return -EINVAL;
        };
        let Some(report_signal) = report_signal_fn else {
            return -EINVAL;
        };

        ptrace_copy_bytes(
            kernel_context_scratch.cast::<u8>(),
            ctx_ptr.cast::<u8>(),
            kernel_context_size,
        );
        preempt_enable();
        report_signal(thread, sig);
        preempt_disable();
        ptrace_copy_bytes(
            ctx_ptr.cast::<u8>(),
            kernel_context_scratch.cast::<u8>(),
            kernel_context_size,
        );
    }

    let current_ptrace =
        read_volatile(field_ptr::<CInt>(thread_base, offsets.thread_ptrace_offset));
    if (current_ptrace & PT_TRACE_SYSCALL) != 0 {
        let Some(arch_syscall_event) = arch_syscall_event_fn else {
            return -EINVAL;
        };
        let uctx_slot = field_ptr::<*mut c_void>(thread_base, offsets.thread_uctx_offset);
        let old_uctx = read_volatile(uctx_slot);
        let saved_uctx = thread_base
            .add(offsets.thread_ptrace_saved_uctx_offset)
            .cast::<c_void>();

        ptrace_copy_bytes(
            kernel_context_scratch.cast::<u8>(),
            ctx_ptr.cast::<u8>(),
            kernel_context_size,
        );
        ptrace_copy_bytes(
            saved_uctx.cast::<u8>(),
            syscall_ctx.cast::<u8>(),
            user_context_size,
        );
        write_volatile(
            field_ptr::<CInt>(thread_base, offsets.thread_ptrace_saved_uctx_valid_offset),
            1,
        );
        write_volatile(uctx_slot, saved_uctx);
        arch_syscall_event(thread, saved_uctx, 0);
        write_volatile(uctx_slot, old_uctx);
        ptrace_copy_bytes(
            ctx_ptr.cast::<u8>(),
            kernel_context_scratch.cast::<u8>(),
            kernel_context_size,
        );
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_report_signal_body_result(
    thread: *mut c_void,
    sig: CInt,
    current_thread: *mut c_void,
    offsets: *const PtraceReportSignalOffsets,
    lock_node: *mut c_void,
    lock_fn: Option<PtraceSignalLockFn>,
    unlock_fn: Option<PtraceSignalLockFn>,
    save_debugreg_fn: Option<PtraceSaveDebugregFn>,
    wake_fn: Option<ThreadExitWakeFn>,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
    schedule_fn: Option<PtraceVoidFn>,
    log_fn: Option<PtraceControlLogFn>,
) -> CInt {
    if thread.is_null() || current_thread.is_null() || offsets.is_null() || lock_node.is_null() {
        return -EINVAL;
    }
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };
    let Some(save_debugreg) = save_debugreg_fn else {
        return -EINVAL;
    };
    let Some(wake) = wake_fn else {
        return -EINVAL;
    };
    let Some(do_kill) = do_kill_fn else {
        return -EINVAL;
    };
    let Some(schedule) = schedule_fn else {
        return -EINVAL;
    };

    let offsets = &*offsets;
    let thread_base = thread.cast::<u8>();
    let proc = read_volatile(field_ptr::<*mut c_void>(
        thread_base,
        offsets.thread_proc_offset,
    ));
    if proc.is_null() {
        return -EINVAL;
    }
    let proc_base = proc.cast::<u8>();
    let tid = read_volatile(field_ptr::<CInt>(thread_base, offsets.thread_tid_offset));
    let proc_pid = read_volatile(field_ptr::<CInt>(proc_base, offsets.proc_pid_offset));
    if let Some(log) = log_fn {
        log(PTRACE_REPORT_SIGNAL_LOG_ENTER, tid, proc_pid);
    }

    let parent_pid;
    let parent_waitq;
    let wake_parent;
    let update_lock = field_ptr::<c_void>(proc_base, offsets.proc_update_lock_offset);
    lock(update_lock, lock_node);
    let ptrace = read_volatile(field_ptr::<CInt>(thread_base, offsets.thread_ptrace_offset));
    if (ptrace & PT_TRACED) == 0 {
        unlock(update_lock, lock_node);
        return 0;
    }

    write_volatile(
        field_ptr::<CInt>(thread_base, offsets.thread_exit_status_offset),
        sig,
    );
    write_volatile(
        field_ptr::<CInt>(thread_base, offsets.thread_status_offset),
        PS_TRACED,
    );
    write_volatile(
        field_ptr::<CInt>(thread_base, offsets.thread_ptrace_offset),
        ptrace & !PT_TRACE_SYSCALL,
    );
    let debugreg = read_volatile(field_ptr::<*mut c_void>(
        thread_base,
        offsets.thread_ptrace_debugreg_offset,
    ));
    save_debugreg(debugreg);

    let signal_flags_ptr = field_ptr::<CInt>(thread_base, offsets.thread_signal_flags_offset);
    let mut signal_flags = read_volatile(signal_flags_ptr);
    if sig == SIGSTOP || sig == SIGTSTP || sig == SIGTTIN || sig == SIGTTOU {
        signal_flags |= SIGNAL_STOP_STOPPED;
    } else {
        signal_flags &= !SIGNAL_STOP_STOPPED;
    }
    write_volatile(signal_flags_ptr, signal_flags);

    let main_thread = read_volatile(field_ptr::<*mut c_void>(
        proc_base,
        offsets.proc_main_thread_offset,
    ));
    if thread == main_thread {
        let parent = read_volatile(field_ptr::<*mut c_void>(
            proc_base,
            offsets.proc_parent_offset,
        ));
        if parent.is_null() {
            unlock(update_lock, lock_node);
            return -EINVAL;
        }
        let parent_base = parent.cast::<u8>();
        write_volatile(
            field_ptr::<CInt>(proc_base, offsets.proc_status_offset),
            PS_TRACED,
        );
        wake_parent = true;
        parent_pid = read_volatile(field_ptr::<CInt>(parent_base, offsets.proc_pid_offset));
        parent_waitq = field_ptr::<c_void>(parent_base, offsets.proc_waitpid_q_offset);
    } else {
        let report_proc = read_volatile(field_ptr::<*mut c_void>(
            thread_base,
            offsets.thread_report_proc_offset,
        ));
        if report_proc.is_null() {
            unlock(update_lock, lock_node);
            return -EINVAL;
        }
        let report_base = report_proc.cast::<u8>();
        parent_pid = read_volatile(field_ptr::<CInt>(report_base, offsets.proc_pid_offset));
        parent_waitq = core::ptr::null_mut::<c_void>();
        wake_parent = false;
        wake(field_ptr::<c_void>(
            report_base,
            offsets.proc_waitpid_q_offset,
        ));
    }
    unlock(update_lock, lock_node);

    if wake_parent {
        wake(parent_waitq);
    }

    let mut info = MaybeUninit::<SigInfo>::uninit();
    let info_ptr = info.as_mut_ptr();
    let raw = info_ptr.cast::<u8>();
    let mut offset = 0;
    while offset < size_of::<SigInfo>() {
        raw.add(offset).write_volatile(0);
        offset += 1;
    }
    let info_ref = &mut *info_ptr;
    info_ref.si_signo = SIGCHLD;
    info_ref.si_code = CLD_TRAPPED;
    let sigchld = (&mut info_ref.sifields as *mut crate::abi::SigInfoFields).cast::<SigInfoChild>();
    write_volatile(core::ptr::addr_of_mut!((*sigchld).si_pid), tid);
    write_volatile(
        core::ptr::addr_of_mut!((*sigchld).si_status),
        read_volatile(field_ptr::<CInt>(
            thread_base,
            offsets.thread_exit_status_offset,
        )),
    );
    do_kill(
        current_thread,
        parent_pid,
        -1,
        SIGCHLD,
        info_ref as *const SigInfo,
        0,
    );

    if let Some(log) = log_fn {
        log(PTRACE_REPORT_SIGNAL_LOG_SLEEPING, tid, sig);
    }
    schedule();
    if let Some(log) = log_fn {
        log(PTRACE_REPORT_SIGNAL_LOG_WAKE, tid, sig);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_syscall_event_body_result(
    thread: *mut c_void,
    ctx: *mut c_void,
    setret: CLong,
    syscall_ret_offset: SizeT,
    event_fn: Option<PtraceReportSignalFn>,
) -> CLong {
    if ctx.is_null() {
        return -(EFAULT as CLong);
    }
    let retp = field_ptr::<CULong>(ctx.cast::<u8>(), syscall_ret_offset);
    write_volatile(retp, setret as CULong);
    let Some(event) = event_fn else {
        return -(EFAULT as CLong);
    };
    event(thread, 0);
    read_volatile(retp) as CLong
}

#[no_mangle]
pub extern "C" fn ptrace_clone_event_result(ptrace: CInt, clone_flags: CInt) -> CInt {
    let mut event = 0;

    if (clone_flags & CLONE_VFORK) != 0 {
        if (ptrace & PTRACE_O_TRACEVFORK) != 0 {
            event = PTRACE_EVENT_VFORK;
        }
        if (ptrace & PTRACE_O_TRACEVFORKDONE) != 0 {
            event = PTRACE_EVENT_VFORK_DONE;
        }
    } else if (clone_flags & CSIGNAL) == SIGCHLD {
        if (ptrace & PTRACE_O_TRACEFORK) != 0 {
            event = PTRACE_EVENT_FORK;
        }
    } else if (ptrace & PTRACE_O_TRACECLONE) != 0 {
        event = PTRACE_EVENT_CLONE;
    }

    event
}

#[no_mangle]
pub extern "C" fn ptrace_clone_reparent_result(event: CInt) -> CInt {
    if event != PTRACE_EVENT_VFORK_DONE {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_report_clone_body_result(
    thread: *mut c_void,
    new_thread: *mut c_void,
    event: CInt,
    current_thread: *mut c_void,
    offsets: *const PtraceReportCloneOffsets,
    lock_node: *mut c_void,
    new_lock_node: *mut c_void,
    lock_fn: Option<PtraceRwlockFn>,
    unlock_fn: Option<PtraceRwlockFn>,
    attach_fn: Option<PtraceAttachThreadFn>,
    do_kill_fn: Option<SyscallDoKillThreadFn>,
    wake_fn: Option<ThreadExitWakeFn>,
    log_fn: Option<PtraceControlLogFn>,
) -> CInt {
    if thread.is_null()
        || new_thread.is_null()
        || offsets.is_null()
        || lock_node.is_null()
        || new_lock_node.is_null()
    {
        return -EINVAL;
    }
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };
    let Some(attach) = attach_fn else {
        return -EINVAL;
    };
    let Some(do_kill) = do_kill_fn else {
        return -EINVAL;
    };
    let Some(wake) = wake_fn else {
        return -EINVAL;
    };
    let offsets = &*offsets;
    let thread_base = thread.cast::<u8>();
    let new_base = new_thread.cast::<u8>();
    let proc = read_volatile(field_ptr::<*mut c_void>(
        thread_base,
        offsets.thread_proc_offset,
    ));
    let new_proc = read_volatile(field_ptr::<*mut c_void>(
        new_base,
        offsets.thread_proc_offset,
    ));
    if proc.is_null() || new_proc.is_null() {
        return -EINVAL;
    }
    let proc_base = proc.cast::<u8>();
    let new_proc_base = new_proc.cast::<u8>();
    let parent = read_volatile(field_ptr::<*mut c_void>(
        proc_base,
        offsets.proc_parent_offset,
    ));
    if parent.is_null() {
        return -EINVAL;
    }
    let parent_base = parent.cast::<u8>();

    if let Some(log) = log_fn {
        log(PTRACE_REPORT_CLONE_LOG_ENTER, 0, 0);
    }

    let update_lock = (proc as CULong).wrapping_add(offsets.proc_update_lock_offset as CULong);
    lock(update_lock, lock_node);
    let exit_status = SIGTRAP | (event << 8);
    write_volatile(
        field_ptr::<CInt>(thread_base, offsets.thread_exit_status_offset),
        exit_status,
    );
    write_volatile(
        field_ptr::<CInt>(proc_base, offsets.proc_status_offset),
        PS_TRACED,
    );
    write_volatile(
        field_ptr::<CInt>(thread_base, offsets.thread_status_offset),
        PS_TRACED,
    );
    let new_tid = read_volatile(field_ptr::<CInt>(new_base, offsets.thread_tid_offset));
    write_volatile(
        field_ptr::<CULong>(thread_base, offsets.thread_ptrace_eventmsg_offset),
        new_tid as CULong,
    );
    let ptrace = read_volatile(field_ptr::<CInt>(thread_base, offsets.thread_ptrace_offset))
        & !PT_TRACE_SYSCALL;
    write_volatile(
        field_ptr::<CInt>(thread_base, offsets.thread_ptrace_offset),
        ptrace,
    );
    let parent_pid = read_volatile(field_ptr::<CInt>(parent_base, offsets.proc_pid_offset));
    unlock(update_lock, lock_node);

    if ptrace_clone_reparent_result(event) != 0 {
        let new_update_lock =
            (new_proc as CULong).wrapping_add(offsets.proc_update_lock_offset as CULong);
        lock(new_update_lock, new_lock_node);
        write_volatile(
            field_ptr::<CInt>(new_base, offsets.thread_ptrace_offset),
            ptrace,
        );
        attach(new_thread as CULong, parent as CULong);
        write_volatile(
            field_ptr::<CInt>(new_base, offsets.thread_exit_status_offset),
            SIGSTOP,
        );
        write_volatile(
            field_ptr::<CInt>(new_proc_base, offsets.proc_status_offset),
            PS_TRACED,
        );
        write_volatile(
            field_ptr::<CInt>(new_base, offsets.thread_status_offset),
            PS_TRACED,
        );
        unlock(new_update_lock, new_lock_node);
    }

    if let Some(log) = log_fn {
        log(PTRACE_REPORT_CLONE_LOG_KILL_SIGCHLD, parent_pid, 0);
    }

    let mut info = MaybeUninit::<SigInfo>::uninit();
    let info_ptr = info.as_mut_ptr();
    let raw = info_ptr.cast::<u8>();
    let mut offset = 0;
    while offset < size_of::<SigInfo>() {
        raw.add(offset).write_volatile(0);
        offset += 1;
    }
    let info_ref = &mut *info_ptr;
    info_ref.si_signo = SIGCHLD;
    info_ref.si_code = CLD_TRAPPED;
    let sigchld = (&mut info_ref.sifields as *mut crate::abi::SigInfoFields).cast::<SigInfoChild>();
    write_volatile(
        core::ptr::addr_of_mut!((*sigchld).si_pid),
        read_volatile(field_ptr::<CInt>(proc_base, offsets.proc_pid_offset)),
    );
    write_volatile(core::ptr::addr_of_mut!((*sigchld).si_status), exit_status);
    let rc = do_kill(
        current_thread,
        parent_pid,
        -1,
        SIGCHLD,
        info_ref as *const SigInfo,
        0,
    );
    if rc < 0 {
        if let Some(log) = log_fn {
            log(
                PTRACE_REPORT_CLONE_LOG_DO_KILL_FAILED,
                parent_pid,
                rc as CInt,
            );
        }
    }

    wake(
        parent_base
            .add(offsets.proc_waitpid_q_offset)
            .cast::<c_void>(),
    );
    0
}

#[no_mangle]
pub extern "C" fn execveat_policy_result(flags: CInt, dirfd: CInt, filename_first: CInt) -> CInt {
    if (flags & !(AT_SYMLINK_NOFOLLOW | AT_EMPTY_PATH)) != 0 {
        return -EINVAL;
    }

    if filename_first == '/' as CInt || dirfd == AT_FDCWD {
        return 0;
    }

    if dirfd < 0 {
        return -EBADF;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn execveat_body_result(
    ctx: *mut c_void,
    dirfd: CInt,
    filename: *const c_void,
    argv: *mut *mut c_void,
    envp: *mut *mut c_void,
    flags: CInt,
    filename_first: CInt,
    execveat_fn: Option<ExecveatFn>,
) -> CLong {
    let error = execveat_policy_result(flags, dirfd, filename_first);
    if error != 0 {
        return error as CLong;
    }
    let Some(execveat) = execveat_fn else {
        return -(EFAULT as CLong);
    };

    execveat(ctx, dirfd, filename, argv, envp, flags) as CLong
}

#[no_mangle]
pub unsafe extern "C" fn execve_body_result(
    ctx: *mut c_void,
    filename: *const c_void,
    argv: *mut *mut c_void,
    envp: *mut *mut c_void,
    execveat_fn: Option<ExecveatFn>,
) -> CLong {
    let Some(execveat) = execveat_fn else {
        return -(EFAULT as CLong);
    };

    execveat(ctx, AT_FDCWD, filename, argv, envp, 0) as CLong
}

#[no_mangle]
pub unsafe extern "C" fn futex_decode_flags_result(
    flags: CInt,
    opp: *mut CInt,
    fsharedp: *mut CInt,
) -> CInt {
    write(
        fsharedp,
        if (flags & FUTEX_PRIVATE_FLAG) != 0 {
            0
        } else {
            1
        },
    );
    write(opp, flags & FUTEX_CMD_MASK);
    0
}

#[no_mangle]
pub extern "C" fn futex_wait_timeout_needed_result(op: CInt, has_utime: CInt) -> CInt {
    if has_utime != 0 && (op == FUTEX_WAIT || op == FUTEX_WAIT_BITSET) {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn futex_timeout_is_absolute_result(op: CInt) -> CInt {
    if op == FUTEX_WAIT_BITSET { 1 } else { 0 }
}

#[no_mangle]
pub extern "C" fn futex_clock_id_result(flags: CInt) -> CInt {
    if (flags & FUTEX_CLOCK_REALTIME) != 0 {
        CLOCK_REALTIME
    } else {
        CLOCK_MONOTONIC
    }
}

#[no_mangle]
pub extern "C" fn futex_requeue_val2_result(op: CInt, arg3: CULong) -> u32 {
    if op == FUTEX_CMP_REQUEUE || op == FUTEX_WAKE_OP {
        arg3 as u32
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn futex_timeout_ns_result(
    op: CInt,
    timeout_sec: CLong,
    timeout_nsec: CLong,
    now_sec: CLong,
    now_nsec: CLong,
) -> CULong {
    let target = (timeout_sec as CULong)
        .wrapping_mul(NS_PER_SEC as CULong)
        .wrapping_add(timeout_nsec as CULong);

    if op == FUTEX_WAIT_BITSET {
        let now = (now_sec as CULong)
            .wrapping_mul(NS_PER_SEC as CULong)
            .wrapping_add(now_nsec as CULong);
        target.wrapping_sub(now)
    } else {
        target
    }
}

#[inline(always)]
unsafe fn do_futex_log(
    log: Option<FutexLogFn>,
    event: CInt,
    flags: CInt,
    op: CInt,
    uaddr: CULong,
    val: u32,
    utime: CULong,
    uaddr2: CULong,
    val3: u32,
    fshared: CInt,
    ret: CInt,
    sec: CLong,
    nsec: CLong,
) {
    let Some(log) = log else {
        return;
    };

    let mut record = MaybeUninit::<FutexLogRecord>::uninit();
    let ptr = record.as_mut_ptr();
    write_volatile(&raw mut (*ptr).event, event);
    write_volatile(&raw mut (*ptr).flags, flags);
    write_volatile(&raw mut (*ptr).op, op);
    write_volatile(&raw mut (*ptr).uaddr, uaddr);
    write_volatile(&raw mut (*ptr).val, val);
    write_volatile(&raw mut (*ptr).utime, utime);
    write_volatile(&raw mut (*ptr).uaddr2, uaddr2);
    write_volatile(&raw mut (*ptr).val3, val3);
    write_volatile(&raw mut (*ptr).fshared, fshared);
    write_volatile(&raw mut (*ptr).ret, ret);
    write_volatile(&raw mut (*ptr).sec, sec);
    write_volatile(&raw mut (*ptr).nsec, nsec);
    log(ptr as *const FutexLogRecord);
}

#[no_mangle]
pub unsafe extern "C" fn do_futex_body_result(
    n: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
    arg3: CULong,
    arg4: CULong,
    arg5: CULong,
    has_uti_clv: CInt,
    local_gettime_support: CInt,
    syscall_time_fn: Option<FutexSyscallTimeFn>,
    local_time_fn: Option<FutexLocalTimeFn>,
    linux_time_fn: Option<FutexLinuxTimeFn>,
    ns_per_tsc_fn: Option<FutexNsPerTscFn>,
    futex_fn: Option<FutexDispatchFn>,
    log_fn: Option<FutexLogFn>,
) -> CLong {
    let mut timeout: u64 = 0;
    let mut fshared: CInt = 1;
    let mut op = arg1 as CInt;
    let flags = op;
    let uaddr = arg0;
    let val = arg2 as u32;
    let utime_addr = arg3;
    let utime = utime_addr as *const TimeSpec;
    let uaddr2 = arg4;
    let val3 = arg5 as u32;

    futex_decode_flags_result(flags, &mut op as *mut CInt, &mut fshared as *mut CInt);

    do_futex_log(
        log_fn,
        DO_FUTEX_LOG_ENTER,
        flags,
        op,
        uaddr,
        val,
        utime_addr,
        uaddr2,
        val3,
        fshared,
        0,
        0,
        0,
    );

    if futex_wait_timeout_needed_result(op, (!utime.is_null()) as CInt) != 0 {
        let time_sec = read_volatile(&(*utime).tv_sec);
        let time_nsec = read_volatile(&(*utime).tv_nsec);
        do_futex_log(
            log_fn,
            DO_FUTEX_LOG_TIMEOUT,
            flags,
            op,
            uaddr,
            val,
            utime_addr,
            uaddr2,
            val3,
            fshared,
            0,
            time_sec,
            time_nsec,
        );

        if has_uti_clv == 0 {
            let nsec_timeout = if futex_timeout_is_absolute_result(op) != 0 {
                let mut ats = MaybeUninit::<TimeSpec>::uninit();
                let ats_ptr = ats.as_mut_ptr();
                if local_gettime_support == 0 || (flags & FUTEX_CLOCK_REALTIME) == 0 {
                    let Some(syscall_time) = syscall_time_fn else {
                        return -(EFAULT as CLong);
                    };
                    if syscall_time(n, futex_clock_id_result(flags), ats_ptr) < 0 {
                        return -(EFAULT as CLong);
                    }
                } else {
                    let Some(local_time) = local_time_fn else {
                        return -(EFAULT as CLong);
                    };
                    local_time(ats_ptr);
                }
                let ats_sec = read_volatile(&(*ats_ptr).tv_sec);
                let ats_nsec = read_volatile(&(*ats_ptr).tv_nsec);
                futex_timeout_ns_result(op, time_sec, time_nsec, ats_sec, ats_nsec)
            } else {
                futex_timeout_ns_result(op, time_sec, time_nsec, 0, 0)
            };

            let Some(ns_per_tsc_fn) = ns_per_tsc_fn else {
                return -(EINVAL as CLong);
            };
            let ns_per_tsc = ns_per_tsc_fn();
            if ns_per_tsc == 0 {
                return -(EINVAL as CLong);
            }
            timeout = nsec_timeout.wrapping_mul(1000) / ns_per_tsc;
        } else if futex_timeout_is_absolute_result(op) != 0 {
            let Some(linux_time) = linux_time_fn else {
                return -(EFAULT as CLong);
            };
            let mut ats = MaybeUninit::<TimeSpec>::uninit();
            let ats_ptr = ats.as_mut_ptr();
            let ret = linux_time(futex_clock_id_result(flags), ats_ptr);
            if ret != 0 {
                return ret as CLong;
            }
            let ats_sec = read_volatile(&(*ats_ptr).tv_sec);
            let ats_nsec = read_volatile(&(*ats_ptr).tv_nsec);
            do_futex_log(
                log_fn,
                DO_FUTEX_LOG_ABSOLUTE_TIME,
                flags,
                op,
                uaddr,
                val,
                utime_addr,
                uaddr2,
                val3,
                fshared,
                0,
                ats_sec,
                ats_nsec,
            );
            timeout = futex_timeout_ns_result(op, time_sec, time_nsec, ats_sec, ats_nsec);
        } else {
            timeout = futex_timeout_ns_result(op, time_sec, time_nsec, 0, 0);
        }
    }

    let val2 = futex_requeue_val2_result(op, arg3);
    let Some(futex) = futex_fn else {
        return -(EINVAL as CLong);
    };
    let ret = futex(uaddr, op, val, timeout, uaddr2, val2, val3, fshared);
    do_futex_log(
        log_fn,
        DO_FUTEX_LOG_EXIT,
        flags,
        op,
        uaddr,
        val,
        utime_addr,
        uaddr2,
        val3,
        fshared,
        ret,
        0,
        0,
    );
    ret as CLong
}

const fn prot_to_vr_flag(prot: CInt) -> CULong {
    ((prot as CULong) << 16) & VR_PROT_MASK
}

const fn vrflag_prot_to_maxprot(vrflag: CULong) -> CULong {
    (vrflag & VR_PROT_MASK) << 4
}

#[no_mangle]
pub extern "C" fn brk_prepare_result(
    address: CULong,
    brk_start: CULong,
    brk_end: CULong,
    brk_end_allocated: CULong,
    resultp: *mut CULong,
    extend_neededp: *mut CInt,
) -> CInt {
    unsafe {
        if address < brk_start || address < brk_end {
            write(resultp, brk_end);
            write(extend_neededp, 0);
            return 0;
        }

        if address <= brk_end_allocated {
            write(resultp, address);
            write(extend_neededp, 0);
            return 0;
        }

        write(resultp, brk_end);
        write(extend_neededp, 1);
    }

    0
}

#[no_mangle]
pub extern "C" fn brk_default_vrflags() -> CULong {
    let vrflag = VR_PROT_READ | VR_PROT_WRITE | VR_PRIVATE;
    vrflag | vrflag_prot_to_maxprot(vrflag)
}

#[no_mangle]
pub unsafe extern "C" fn brk_body_result(
    vm: *mut c_void,
    region: *mut c_void,
    range_lock: *mut c_void,
    address: CULong,
    cpu: CInt,
    brk_start_offset: SizeT,
    brk_end_offset: SizeT,
    brk_end_allocated_offset: SizeT,
    flush_fn: Option<BrkFlushFn>,
    lock_fn: Option<SyscallRwlockFn>,
    unlock_fn: Option<SyscallRwlockFn>,
    extend_fn: Option<BrkExtendFn>,
    log_fn: Option<BrkLogFn>,
) -> CULong {
    if vm.is_null() || region.is_null() {
        return 0;
    }

    let region = region.cast::<u8>();
    let brk_startp = region.add(brk_start_offset).cast::<CULong>();
    let brk_endp = region.add(brk_end_offset).cast::<CULong>();
    let brk_end_allocatedp = region.add(brk_end_allocated_offset).cast::<CULong>();

    let brk_start = read_volatile(brk_startp);
    let brk_end = read_volatile(brk_endp);
    let brk_end_allocated = read_volatile(brk_end_allocatedp);

    if let Some(log) = log_fn {
        log(BRK_LOG_ENTER, cpu, brk_start, brk_end, 0);
    }
    if let Some(flush) = flush_fn {
        flush();
    }

    let mut result = 0;
    let mut extend_needed = 0;
    brk_prepare_result(
        address,
        brk_start,
        brk_end,
        brk_end_allocated,
        &mut result as *mut CULong,
        &mut extend_needed as *mut CInt,
    );
    if extend_needed == 0 {
        write_volatile(brk_endp, result);
        return result;
    }

    let old_brk_end_allocated = brk_end_allocated;
    if let Some(lock) = lock_fn {
        lock(range_lock);
    }
    if let Some(extend) = extend_fn {
        let new_end = extend(vm, old_brk_end_allocated, address, brk_default_vrflags());
        write_volatile(brk_end_allocatedp, new_end);
    }
    if let Some(unlock) = unlock_fn {
        unlock(range_lock);
    }

    let new_brk_end_allocated = read_volatile(brk_end_allocatedp);
    if old_brk_end_allocated == new_brk_end_allocated {
        return old_brk_end_allocated;
    }

    write_volatile(brk_endp, address);
    result = read_volatile(brk_endp);
    if let Some(log) = log_fn {
        log(BRK_LOG_SET_END, cpu, brk_start, result, result);
    }
    result
}

#[no_mangle]
pub unsafe extern "C" fn mincore_prepare_range(
    start: CULong,
    len: SizeT,
    user_start: CULong,
    user_end: CULong,
    endp: *mut CULong,
) -> CInt {
    write(endp, start.wrapping_add(len as CULong));

    if (start & (PAGE_SIZE - 1)) != 0 {
        return -EINVAL;
    }

    if start < user_start || user_end <= start || user_end.wrapping_sub(start) < len as CULong {
        return -ENOMEM;
    }

    0
}

#[inline(always)]
unsafe fn mincore_range_ulong(range: *mut c_void, offset: SizeT) -> CULong {
    *field_ptr::<CULong>(range.cast::<u8>(), offset)
}

#[inline(always)]
unsafe fn mincore_range_ptr(range: *mut c_void, offset: SizeT) -> *mut c_void {
    *field_ptr::<*mut c_void>(range.cast::<u8>(), offset)
}

#[inline(always)]
unsafe fn mincore_range_objoff(range: *mut c_void, offset: SizeT) -> CULong {
    *field_ptr::<CLong>(range.cast::<u8>(), offset) as CULong
}

#[no_mangle]
pub unsafe extern "C" fn mincore_body_result(
    vm: *mut c_void,
    range_lock: *mut c_void,
    pte_lock: *mut c_void,
    page_table: *mut c_void,
    start: CULong,
    len: SizeT,
    vec_addr: CULong,
    user_start: CULong,
    user_end: CULong,
    range_start_offset: SizeT,
    range_end_offset: SizeT,
    range_memobj_offset: SizeT,
    range_objoff_offset: SizeT,
    range_lock_fn: Option<SyscallRwlockFn>,
    range_unlock_fn: Option<SyscallRwlockFn>,
    pte_lock_fn: Option<SyscallRwlockFn>,
    pte_unlock_fn: Option<SyscallRwlockFn>,
    lookup_fn: Option<MsyncLookupRangeFn>,
    pte_lookup_fn: Option<MincorePteLookupFn>,
    pte_present_fn: Option<MincorePtePresentFn>,
    memobj_lookup_fn: Option<MincoreMemobjLookupFn>,
    copy_byte_fn: Option<MincoreCopyByteFn>,
    log_fn: Option<MincoreLogFn>,
) -> CLong {
    let mut end: CULong = 0;
    let mut error = mincore_prepare_range(start, len, user_start, user_end, &mut end);
    if error != 0 {
        if let Some(log) = log_fn {
            log(MINCORE_LOG_INVALID, start, len, vec_addr, error);
        }
        return error as CLong;
    }

    let mut addr = start;
    let mut up = vec_addr;
    while addr < end {
        if let Some(lock) = range_lock_fn {
            lock(range_lock);
        }
        let range = if let Some(lookup) = lookup_fn {
            lookup(vm, addr, addr.wrapping_add(1))
        } else {
            core::ptr::null_mut()
        };
        if range.is_null() {
            if let Some(unlock) = range_unlock_fn {
                unlock(range_lock);
            }
            if let Some(log) = log_fn {
                log(MINCORE_LOG_LOOKUP_FAILED, start, len, vec_addr, -ENOMEM);
            }
            return -ENOMEM as CLong;
        }

        if let Some(lock) = pte_lock_fn {
            lock(pte_lock);
        }
        let ptep = if let Some(lookup_pte) = pte_lookup_fn {
            lookup_pte(page_table, addr)
        } else {
            core::ptr::null_mut()
        };

        let mut value: u8 = 0;
        if !ptep.is_null() && pte_present_fn.map_or(false, |present| present(ptep) != 0) {
            value = 1;
        } else {
            let memobj = mincore_range_ptr(range, range_memobj_offset);
            if !memobj.is_null() {
                let objoff = mincore_range_objoff(range, range_objoff_offset).wrapping_add(
                    addr.wrapping_sub(mincore_range_ulong(range, range_start_offset)),
                );
                let rc = if let Some(lookup_page) = memobj_lookup_fn {
                    lookup_page(memobj, objoff)
                } else {
                    -ENOMEM
                };
                if rc == 0 {
                    value = 1;
                }
            }
        }
        let _ = mincore_range_ulong(range, range_end_offset);
        if let Some(unlock) = pte_unlock_fn {
            unlock(pte_lock);
        }
        if let Some(unlock) = range_unlock_fn {
            unlock(range_lock);
        }

        error = if let Some(copy_byte) = copy_byte_fn {
            copy_byte(up, value) as CInt
        } else {
            -EFAULT
        };
        if error != 0 {
            if let Some(log) = log_fn {
                log(MINCORE_LOG_COPY_FAILED, start, len, vec_addr, error);
            }
            return error as CLong;
        }

        addr = addr.wrapping_add(PAGE_SIZE);
        up = up.wrapping_add(1);
    }

    if let Some(log) = log_fn {
        log(MINCORE_LOG_EXIT, start, len, vec_addr, 0);
    }
    0
}

#[no_mangle]
pub extern "C" fn mmap_base_vrflags(
    prot: CInt,
    flags: CInt,
    vrf0: CULong,
    anon_on_demand: CInt,
) -> CULong {
    let mut vrflags = vrf0 | prot_to_vr_flag(prot) | VR_DEMAND_PAGING;

    if (flags & MAP_PRIVATE) != 0 {
        vrflags |= VR_PRIVATE;
    }
    if (flags & MAP_LOCKED) != 0 {
        vrflags |= VR_LOCKED;
    }
    if (flags & MAP_ANONYMOUS) != 0 && anon_on_demand == 0 && (flags & MAP_PRIVATE) != 0 {
        vrflags &= !VR_DEMAND_PAGING;
    }

    vrflags
}

#[no_mangle]
pub extern "C" fn mmap_populated_mapping_result(flags: CInt) -> CInt {
    if (flags & (MAP_POPULATE | MAP_LOCKED)) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn mmap_should_set_host_ro(flags: CInt, prot: CInt, anonymous_only: CInt) -> CInt {
    if anonymous_only != 0 && (flags & MAP_ANONYMOUS) == 0 {
        return 0;
    }

    if (prot & PROT_WRITE) == 0 { 1 } else { 0 }
}

#[no_mangle]
pub extern "C" fn mmap_update_private_maxprot(flags: CInt, maxprot: CInt) -> CInt {
    if (flags & MAP_PRIVATE) != 0 && (maxprot & PROT_READ) != 0 {
        maxprot | PROT_WRITE
    } else {
        maxprot
    }
}

#[no_mangle]
pub unsafe extern "C" fn mmap_prot_denied_result(
    prot: CInt,
    maxprot: CInt,
    deniedp: *mut CInt,
) -> CInt {
    let denied = prot & !maxprot;
    write(deniedp, denied);

    if denied == 0 {
        return 0;
    }

    if denied == PROT_EXEC { -EPERM } else { -EACCES }
}

#[no_mangle]
pub extern "C" fn mmap_maxprot_to_vrflags(maxprot: CInt) -> CULong {
    vrflag_prot_to_maxprot(prot_to_vr_flag(maxprot))
}

#[no_mangle]
pub extern "C" fn mmap_should_force_straight(
    flags: CInt,
    straight_map: CInt,
    phys: CULong,
    len: SizeT,
    threshold: SizeT,
) -> CInt {
    if (flags & MAP_ANONYMOUS) != 0
        && straight_map != 0
        && (flags & MAP_FIXED) == 0
        && phys != 0
        && len >= threshold
    {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn mmap_is_shared(flags: CInt) -> CInt {
    if (flags & MAP_SHARED) != 0 { 1 } else { 0 }
}
