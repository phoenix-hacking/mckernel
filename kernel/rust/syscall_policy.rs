use core::ptr::write;

use crate::abi::{CInt, CLong, CULong, SizeT};

const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const EACCES: CInt = 13;
const EPERM: CInt = 1;
const EFAULT: CInt = 14;
const EBUSY: CInt = 16;
const ESRCH: CInt = 3;
const EIO: CInt = 5;
const EBADF: CInt = 9;
const ECHILD: CInt = 10;
const EOPNOTSUPP: CInt = 95;

const ROBUST_LIST_HEAD_SIZE: SizeT = 24;
const SIGKILL: CInt = 9;
const SIGSTOP: CInt = 19;
const NSIG: CInt = 64;
const SIG_BLOCK: CInt = 0;
const SIG_UNBLOCK: CInt = 1;
const SIG_SETMASK: CInt = 2;
const SIGKILL_MASK: CULong = 1 << 8;
const SIGSTOP_MASK: CULong = 1 << 18;
const PAGE_SIZE: CULong = 1 << 12;
const PAGE_SHIFT: CULong = 12;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);
const PGOFF_LIMIT: SizeT = 1usize << (63 - PAGE_SHIFT as usize);
const VR_RESERVED: CULong = 0x2;
const VR_IO_NOCACHE: CULong = 0x100;
const VR_REMOTE: CULong = 0x200;
const VR_DEMAND_PAGING: CULong = 0x1000;
const VR_PRIVATE: CULong = 0x2000;
const VR_LOCKED: CULong = 0x4000;
const VR_PROT_READ: CULong = 0x00010000;
const VR_PROT_WRITE: CULong = 0x00020000;
const VR_PROT_MASK: CULong = 0x00070000;

const MCL_CURRENT: CInt = 0x01;
const MCL_FUTURE: CInt = 0x02;

const PROT_READ: CInt = 0x01;
const PROT_WRITE: CInt = 0x02;
const PROT_EXEC: CInt = 0x04;

const MAP_SHARED: CInt = 0x01;
const MAP_PRIVATE: CInt = 0x02;
const MAP_FIXED: CInt = 0x10;
const MAP_ANONYMOUS: CInt = 0x20;
const MAP_LOCKED: CInt = 0x2000;
const MAP_POPULATE: CInt = 0x8000;

const SFD_CLOEXEC: CInt = 0o2000000;
const SFD_NONBLOCK: CInt = 0o4000;
const MINSIGSTKSZ: SizeT = 2048;
const SS_DISABLE: CInt = 2;

const IOV_MAX: CULong = 1024;
const PROCESS_VM_READ: CInt = 0;
const PROCESS_VM_WRITE: CInt = 1;

const SIGTRAP: CInt = 5;
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
const PTRACE_EVENT_FORK: CInt = 1;
const PTRACE_EVENT_VFORK: CInt = 2;
const PTRACE_EVENT_CLONE: CInt = 3;
const PTRACE_EVENT_EXEC: CInt = 4;
const PTRACE_EVENT_VFORK_DONE: CInt = 5;
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

#[no_mangle]
pub extern "C" fn robust_list_len_result(len: SizeT) -> CInt {
    if len == ROBUST_LIST_HEAD_SIZE {
        0
    } else {
        -EINVAL
    }
}

#[no_mangle]
pub extern "C" fn tkill_tid_result(tid: CInt) -> CInt {
    if tid <= 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn tgkill_target_result(tgid: CInt, tid: CInt) -> CInt {
    if tgid <= 0 || tid <= 0 {
        -EINVAL
    } else {
        0
    }
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

#[no_mangle]
pub extern "C" fn syscall_use_requester_tid_result(
    syscall_nr: CInt,
    arg0: CULong,
    sched_setaffinity_nr: CInt,
) -> CInt {
    (syscall_nr == sched_setaffinity_nr && arg0 == 0) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_preempt_disable_needed_result(rtid: CInt) -> CInt {
    (rtid == -1) as CInt
}

#[no_mangle]
pub extern "C" fn setpgid_normalize_pid(current_pid: CInt, pid: CInt) -> CInt {
    if pid == 0 {
        current_pid
    } else {
        pid
    }
}

#[no_mangle]
pub extern "C" fn setpgid_normalize_pgid(pid: CInt, pgid: CInt) -> CInt {
    if pgid == 0 {
        pid
    } else {
        pgid
    }
}

#[no_mangle]
pub extern "C" fn setpgid_execed_result(execed: CInt) -> CInt {
    if execed != 0 {
        -EACCES
    } else {
        0
    }
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
pub extern "C" fn getrusage_maxrss_kb_result(maxrss: CLong) -> CLong {
    maxrss / 1024
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
    if which == ITIMER_REAL {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn itimer_should_start(value_sec: CLong, value_usec: CLong) -> CInt {
    if value_sec == 0 && value_usec == 0 {
        0
    } else {
        1
    }
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
pub extern "C" fn nanosleep_validate_timespec(sec: CLong, nsec: CLong) -> CInt {
    if sec < 0 || nsec < 0 || nsec >= NS_PER_SEC {
        -EINVAL
    } else {
        0
    }
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
    if pid <= 0 {
        -ESRCH
    } else {
        0
    }
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
    if flags == SS_DISABLE {
        1
    } else {
        0
    }
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
    if op == PROCESS_VM_WRITE {
        1
    } else {
        0
    }
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
    if (options & __WCLONE) == 0 {
        1
    } else {
        0
    }
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

    if pid == child_pid {
        1
    } else {
        0
    }
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

    if tid == -1 || child_tid == tid {
        1
    } else {
        0
    }
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
    if (options & WNOWAIT) == 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_nohang_result(options: CInt) -> CInt {
    if (options & WNOHANG) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn wait_empty_result(empty: CInt) -> CInt {
    if empty != 0 {
        -ECHILD
    } else {
        0
    }
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

#[no_mangle]
pub extern "C" fn waitid_siginfo_needed_result(rc: CInt, has_infop: CInt) -> CInt {
    (rc > 0 && has_infop != 0) as CInt
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
pub extern "C" fn thread_exit_signal_result(ptrace: CInt, termsig: CInt) -> CInt {
    if ptrace != 0 {
        SIGCHLD
    } else {
        termsig
    }
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
pub extern "C" fn exit_group_status_claimed_result(old_exit_status: CULong) -> CInt {
    ((old_exit_status & EXIT_GROUP_STATUS_CONFIRMED) != 0) as CInt
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
    if op == FUTEX_WAIT_BITSET {
        1
    } else {
        0
    }
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

    if (prot & PROT_WRITE) == 0 {
        1
    } else {
        0
    }
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

    if denied == PROT_EXEC {
        -EPERM
    } else {
        -EACCES
    }
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
    if (flags & MAP_SHARED) != 0 {
        1
    } else {
        0
    }
}
