// Exact finite current production policy slices; test-only imports below.
use core::{ffi::c_void, mem::{ManuallyDrop,MaybeUninit,offset_of,size_of}, ptr::{read_volatile,write}};
use crate::abi::{CInt,CLong,CULong,SizeT,Thread,Process,SigInfo,SigInfoKill};
unsafe extern "C" {
 fn do_kill(thread:*mut Thread,pid:CInt,tid:CInt,sig:CInt,info:*mut SigInfo,ptracecont:CInt)->CULong;
 fn syscall_do_kill_thread_bridge(thread:*mut c_void,pid:CInt,tid:CInt,sig:CInt,info:*const SigInfo,ptracecont:CInt)->CLong;
 fn set_single_step(thread:*mut Thread);
}
const EINVAL: CInt = 22;

const EFAULT: CInt = 14;

const ESRCH: CInt = 3;

const SIGKILL: CInt = 9;

const SIGSTOP: CInt = 19;

const NSIG: CInt = 64;

const SI_USER: CInt = 0;

const PS_TRACED: CInt = 0x40;

const PS_STOPPED: CInt = 0x20;

const PTRACE_CONT: CLong = 7;

const PTRACE_KILL: CLong = 8;

const PTRACE_SINGLESTEP: CLong = 9;

const PTRACE_SYSCALL: CLong = 24;

const PTRACE_WAKEUP_ACTION_NONE: CInt = 0;

const PTRACE_WAKEUP_ACTION_KILL: CInt = 1;

const PTRACE_WAKEUP_ACTION_RESUME: CInt = 2;

const PTRACE_RESUME_SIGNAL_SOURCE_USER: CInt = 0;

const PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG: CInt = 1;

const PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG: CInt = 2;

const PTRACE_CONTROL_LOG_WAKEUP_ENTER: CInt = 4;

type PtraceArchFn = unsafe extern "C" fn(CLong, CInt, CLong, CLong) -> CLong;

type PtraceAttachFn = unsafe extern "C" fn(CInt) -> CInt;

type PtraceControlLogFn = unsafe extern "C" fn(CInt, CInt, CInt);

type PtraceDetachFn = unsafe extern "C" fn(CInt, CInt) -> CInt;

type PtraceDoKillThreadFn =
    unsafe extern "C" fn(*mut c_void, CInt, CInt, CInt, *const SigInfo, CInt) -> CLong;

type PtraceFindThreadFn = unsafe extern "C" fn(CInt, CInt) -> CULong;

type PtraceFreeFn = unsafe extern "C" fn(*mut c_void);

type PtracePendingSignalTakeFn = unsafe extern "C" fn(CULong, CULong, CULong, CInt) -> CULong;

type PtracePidAddrDataFn = unsafe extern "C" fn(CInt, CLong, CLong) -> CLong;

type PtracePidDataFn = unsafe extern "C" fn(CInt, CLong) -> CLong;

type PtraceRwlockFn = unsafe extern "C" fn(CULong, *mut c_void);

type PtraceSavedContextClearFn = unsafe extern "C" fn(CULong, CULong) -> CInt;

type PtraceSetSingleStepFn = unsafe extern "C" fn(CULong);

type PtraceSetoptionsFn = unsafe extern "C" fn(CInt, CInt) -> CInt;

type PtraceSiginfoFn = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;

type PtraceThreadUnlockFn = unsafe extern "C" fn(CULong);

type PtraceTraceSyscallUpdateFn = unsafe extern "C" fn(CULong, CULong, CInt) -> CInt;

type PtraceTracemeFn = unsafe extern "C" fn() -> CInt;

type PtraceWakeupSigFn = unsafe extern "C" fn(CInt, CLong, CLong) -> CInt;

type PtraceWakeupThreadFn = unsafe extern "C" fn(*mut c_void, CInt);

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

#[inline(always)]
unsafe fn field_ptr<T>(base: *mut u8, offset: SizeT) -> *mut T {
    base.add(offset).cast::<T>()
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
unsafe fn ptrace_io_proc_pid(proc_addr: CULong, offsets: *const PtraceIoOffsets) -> CInt {
    let proc_ptr = proc_addr as *mut u8;
    unsafe { read_volatile(field_ptr::<CInt>(proc_ptr, (*offsets).proc_pid_offset)) }
}

#[inline(always)]
unsafe fn ptrace_io_proc_update_lock(proc_addr: CULong, offsets: *const PtraceIoOffsets) -> CULong {
    proc_addr.wrapping_add(unsafe { (*offsets).proc_update_lock_offset as CULong })
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

#[cfg_attr(f03_ptrace_io_find_selected_candidate,no_mangle)]
pub unsafe extern "C" fn f03_ptrace_io_find(tgid: CInt, tid: CInt) -> CULong {
    unsafe { crate::process_helpers::find_thread(tgid, tid) as CULong }
}

#[cfg_attr(f03_ptrace_io_unlock_selected_candidate,no_mangle)]
pub unsafe extern "C" fn f03_ptrace_io_unlock(thread: CULong) {
    unsafe { crate::process_helpers::thread_unlock(thread as *mut Thread) };
}

static F03_PTRACE_IO_OFFSETS: PtraceIoOffsets = PtraceIoOffsets {
    thread_proc_offset: offset_of!(Thread, proc),
    thread_status_offset: offset_of!(Thread, status),
    thread_vm_offset: offset_of!(Thread, vm),
    thread_ptrace_offset: offset_of!(Thread, ptrace),
    thread_ptrace_eventmsg_offset: offset_of!(Thread, ptrace_eventmsg),
    thread_ptrace_recvsig_offset: offset_of!(Thread, ptrace_recvsig),
    thread_ptrace_sendsig_offset: offset_of!(Thread, ptrace_sendsig),
    thread_report_proc_offset: offset_of!(Thread, report_proc),
    thread_ptrace_saved_uctx_valid_offset: offset_of!(Thread, ptrace_saved_uctx_valid),
    proc_pid_offset: offset_of!(Process, pid),
    proc_update_lock_offset: offset_of!(Process, update_lock),
};

#[cfg(f03_ptrace_entry_candidate)]
mod ptrace_wakeup_state_callbacks {
    use core::ffi::c_void;

    use crate::abi::{CInt, CULong};
    use crate::process_helpers;

    use super::{
        PtracePendingSignalTakeFn, PtraceSavedContextClearFn, PtraceTraceSyscallUpdateFn,
    };

    /// Forward the original saved-context clear through its integer-address ABI.
    ///
    /// # Safety
    /// A nonzero thread address names live storage with an aligned writable C int
    /// at offset. The ptrace caller retains the original exclusion and lifetime.
    #[no_mangle]
    pub unsafe extern "C" fn ptrace_wakeup_clear_saved_bridge(
        thread_addr: CULong,
        offset: CULong,
    ) -> CInt {
        // SAFETY: Preserve the C address cast and pass through null to the provider.
        unsafe {
            process_helpers::process_thread_ptrace_saved_context_clear_result(
                thread_addr as *mut c_void,
                offset,
            )
        }
    }

    /// Forward the trace-syscall update under the caller's existing update lock.
    ///
    /// # Safety
    /// A nonzero thread address names live storage with an aligned writable C int
    /// at ptrace_offset. The caller holds the original update-lock exclusion.
    #[no_mangle]
    pub unsafe extern "C" fn ptrace_wakeup_trace_syscall_bridge(
        thread_addr: CULong,
        ptrace_offset: CULong,
        trace_syscall: CInt,
    ) -> CInt {
        // SAFETY: Forward the unchanged address, offset and signed flag once.
        unsafe {
            process_helpers::process_thread_ptrace_trace_syscall_update_result(
                thread_addr as *mut c_void,
                ptrace_offset,
                trace_syscall,
            )
        }
    }

    /// Return the existing provider's taken node through the unsigned-long ABI.
    ///
    /// # Safety
    /// A nonzero thread address remains live under the original ptrace exclusion.
    /// The selected offset names an aligned writable pointer slot. The caller
    /// retains the original delivery/free responsibility for the returned node.
    #[no_mangle]
    pub unsafe extern "C" fn ptrace_wakeup_pending_take_bridge(
        thread_addr: CULong,
        sendsig_offset: CULong,
        recvsig_offset: CULong,
        source: CInt,
    ) -> CULong {
        // SAFETY: Preserve source/offset routing and the original pointer-to-long cast.
        unsafe {
            process_helpers::process_thread_ptrace_pending_signal_take_result(
                thread_addr as *mut c_void,
                sendsig_offset,
                recvsig_offset,
                source,
            ) as CULong
        }
    }

    const _: PtraceSavedContextClearFn = ptrace_wakeup_clear_saved_bridge;
    const _: PtraceTraceSyscallUpdateFn = ptrace_wakeup_trace_syscall_bridge;
    const _: PtracePendingSignalTakeFn = ptrace_wakeup_pending_take_bridge;
}

#[cfg(f03_ptrace_entry_candidate)]
mod ptrace_wakeup_step_callback {
    use crate::abi::{CULong, Thread};
    use super::{set_single_step, PtraceSetSingleStepFn};

    /// Forward the existing integer-address callback to the selected Rust provider.
    ///
    /// # Safety
    /// The original ptrace caller owns thread/context lifetime and exclusion.
    /// Null is passed through to the existing provider, which retains its checks.
    #[no_mangle]
    pub unsafe extern "C" fn ptrace_wakeup_set_single_step_bridge(thread_addr: CULong) {
        // SAFETY: Preserve the original address cast; no direct context access here.
        unsafe { set_single_step(thread_addr as *mut Thread) };
    }
    const _: PtraceSetSingleStepFn = ptrace_wakeup_set_single_step_bridge;
}

mod actual_typed_kill_bridge {
 use super::*;
    #[export_name = "syscall_do_kill_thread_bridge"]
    pub unsafe extern "C" fn kill_thread(
        thread: *mut c_void, pid: CInt, tid: CInt, sig: CInt,
        info: *const SigInfo, ptracecont: CInt,
    ) -> CLong {
        // C returns unsigned long from do_kill through a signed-long bridge.
        unsafe { do_kill(thread.cast(), pid, tid, sig, info.cast_mut(), ptracecont) as CLong }
    }
}

#[path="production_entry.rs"]
pub(crate) mod entry;
