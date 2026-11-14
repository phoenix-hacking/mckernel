// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Separate source module supports bounded checks without compiling held policy
// bodies. The production recipe still includes this module in its kernel object.
use super::*;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Reuse existing context entry independently of unqualified whole-signal bodies.
#[cfg(all(
    f06_signal_context_candidate,
    f06_do_signal_whole_candidate,
    not(f06_do_signal_reuse_qualified_context),
))]
compile_error!("select independent context OR whole-signal context, never duplicate exports");

#[cfg(f06_signal_context_candidate)]
mod f06_signal_context_candidate {
    use core::mem::offset_of;

    use crate::abi::{CInt, CULong, Thread, X86UserContext};

/// Existing null-regs architecture boundary: current TSS stack context minus one.
///
/// # Safety
/// Native kernel GS base and current TSS/rsp0 must be installed, with the complete
/// saved X86UserContext immediately below rsp0. Never call this HOST-side. The
/// original C used this same GS load and context subtraction, without recovery.
unsafe extern "C" fn f06_signal_syscall_context() -> *mut X86UserContext {
    let top: CULong;
    let offset = offset_of!(crate::abi::X86CpuLocalVariables, tss)
        + offset_of!(crate::abi::Tss64, rsp0);
    // SAFETY: exact original GS memory load; MOV preserves flags and does not
    // touch stack. No privileged instruction is executed during preparation.
    unsafe {
        core::arch::asm!(
            "mov {top}, gs:[{offset}]",
            top = out(reg) top,
            offset = in(reg) offset,
            options(nostack, readonly, preserves_flags),
        );
        (top as *mut X86UserContext).sub(1)
    }
}

type F06ContextCurrentThread = unsafe extern "C" fn() -> *mut Thread;
type F06ContextXsaveSize = unsafe extern "C" fn() -> CInt;
type F06ContextKernelRegs = unsafe extern "C" fn() -> *mut X86UserContext;

unsafe extern "C" fn f06_context_current_thread() -> *mut Thread {
    // SAFETY: same current CPU/thread lookup as original, no extra held reference.
    unsafe { (*crate::cls::get_this_cpu_local_var()).current }
}

/// Fill only requested outputs, preserving original provider-read/write order.
///
/// # Safety
/// Nonnull output slots cover their actual pointer/int types and retain original
/// C lifetime/aliasing preconditions. Providers have the original current CPU,
/// boot XSAVE-size and GS/TSS context contracts. A controlled HOST body fixture
/// may replace those explicit effects only; production always binds genuine ones.
#[no_mangle]
pub unsafe extern "C" fn arch_rt_sigreturn_context_body_result(
    thread_out: *mut *mut Thread,
    regs_out: *mut *mut X86UserContext,
    size_out: *mut CInt,
    current: F06ContextCurrentThread,
    xsave_size: F06ContextXsaveSize,
    kernel_regs: F06ContextKernelRegs,
) {
    if !thread_out.is_null() {
        // SAFETY: original first optional output and its synchronous provider.
        unsafe { thread_out.write(current()) };
    }
    if !size_out.is_null() {
        // SAFETY: size getter is intentionally after the thread output store.
        unsafe { size_out.write(xsave_size()) };
    }
    if !regs_out.is_null() {
        // SAFETY: actual existing GS context read/subtraction happens last and
        // only when regs output is requested; no shared cached value is added.
        unsafe { regs_out.write(kernel_regs()) };
    }
}

/// # Safety
/// Exact existing public sigreturn context contract. The shared GS/TSS provider
/// is the byte-identical helper already used by whole do_signal; never HOST-run.
#[no_mangle]
pub unsafe extern "C" fn arch_rt_sigreturn_context_bridge(
    thread_out: *mut *mut Thread,
    regs_out: *mut *mut X86UserContext,
    size_out: *mut CInt,
) {
    // SAFETY: genuine current CPU, actual boot getter and SAME reviewed-ASM source,
    // with optional outputs controlling which mechanisms are invoked.
    unsafe {
        arch_rt_sigreturn_context_body_result(
            thread_out, regs_out, size_out, f06_context_current_thread,
            crate::x86_cpu_helpers::get_xsave_size, f06_signal_syscall_context,
        );
    }
}


    // Same actual public C ABI; no new output/storage representation is introduced.
    const _: unsafe extern "C" fn(
        *mut *mut Thread,
        *mut *mut X86UserContext,
        *mut CInt,
    ) = arch_rt_sigreturn_context_bridge;
}

// Reuse the separately qualified context implementation; never define a second export.
#[cfg(all(
    f06_do_signal_whole_candidate,
    not(all(f06_signal_context_candidate, f06_do_signal_reuse_qualified_context)),
))]
compile_error!("whole signal successor requires the qualified context cohort and reuse marker");

#[cfg(all(f06_do_signal_whole_candidate, not(f06_signal_trap_info_candidate)))]
compile_error!("whole signal successor requires initialized traced-SIGTRAP notification storage");

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Whole signal source is selected only by its paired supported-profile recipe.
#[cfg(all(f06_do_signal_whole_candidate, any(
    f06_handler_commit_candidate, f06_xsave_copy_candidate, f06_frame_copy_candidate,
    f06_core_termination_candidate, f06_trap_stop_candidate,
)))]
compile_error!("select whole do_signal OR its partial modules, never duplicate exports");

#[cfg(f06_do_signal_whole_candidate)]
mod f06_do_signal_whole_candidate {
    include!(env!("MCKERNEL_F06_SIGNAL_METADATA_RS"));

    use core::ffi::c_void;
    use core::mem::{offset_of, size_of, MaybeUninit};
    use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile};

    use crate::abi::{
        CInt, CLong, CULong, KSigAction, Process, SigCommon, SigInfo, SizeT, Thread,
        X86UserContext,
    };
    // Existing Thread ABI deliberately stores sigcommon as an opaque raw pointer.
    // Each local SigCommon cast below repeats the original load at the same use;
    // no cached pointer/reference extends its lifetime across free or unlock.
    // SAFETY: the existing caller must still establish the genuine allocation,
    // writer-guard and node lifetime required by the corresponding C operation.
    // These casts neither establish that contract nor close its pending-slot races.

    use crate::lock_helpers::McsRwlockNodeIrqsave;
    use crate::waitq::Waitq as RuntimeWaitq;

    use super::{
        arch_copy_from_user_bridge, arch_copy_to_user_bridge, kprintf,
        ptrace_report_signal, rt_sigreturn_zero_siginfo, schedule, sigmask_to_signal_number,
        CLD_STOPPED, EBUSY, EFAULT, ENOMEM, IHK_MC_AP_NOWAIT, PS_DELAY_STOPPED,
        PS_DELAY_TRACED, PS_STOPPED, PS_TRACED, PT_TRACED, RFLAGS_TF, SIGCHLD, SIGCONT,
        SIGKILL, SIGNAL_STOP_STOPPED, SIGSTOP, SIGTRAP, SIGTSTP, SIGTTIN, SIGTTOU, SIGURG,
        TRAP_TRACE,
    };

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: handler register/action-mask commit, pending consume/unlock and TF followup.
const F06_HANDLER_SA_RESETHAND:CULong=0x80000000;
const F06_HANDLER_SA_NODEFER:CULong=0x40000000;
unsafe extern "C" {
    #[link_name="set_signal"]
    fn f06_handler_commit_set_signal(sig:CInt,regs:*mut c_void,info:*mut SigInfo);
    #[link_name="check_signal"]
    fn f06_handler_commit_check_signal(rc:CULong,regs:*mut c_void,num:CInt);
}

/// Frame has ALREADY passed the existing stack/context/XSAVE/user-copy/publication
/// path. This does not dereference any user-frame address. info_offset is the
/// compiler's real offsetof(struct sigsp,info) for the matching C native/legacy
/// profile; frame and user_sp preserve the original virtual address bits.
/// The caller holds sigcommon writer lock and its pending node. Consume exactly
/// that node before the original unlock, then process single-step outside lock.
/// Rust native cfg MUST match C MCKERNEL_NATIVE_SIGNAL_STACK in the real recipe.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_handler_commit_result(
    thread:*mut Thread,regs:*mut X86UserContext,k:*mut KSigAction,
    pending:*mut crate::abi::SigPending,sig:CInt,frame:CULong,
    info_offset:SizeT,user_sp:CULong,lock_node:*mut McsRwlockNodeIrqsave,
) {
    (*regs).gpr.rdi=sig as CULong;
    (*regs).gpr.rsi=frame.wrapping_add(info_offset as CULong);
    (*regs).gpr.rdx=frame;
    (*regs).gpr.rip=(*k).sa.sa_handler as CULong;
    (*regs).gpr.rsp=user_sp;
    if ((*k).sa.sa_flags & F06_HANDLER_SA_RESETHAND) != 0 {
        (*k).sa.sa_handler=null_mut();
    }
    #[cfg(native_linux_irq_work_v6_12)]
    {
        (*thread).sigmask.val[0]=crate::native_signal::native_signal_action_mask_result(
            (*thread).sigmask.val[0],(*k).sa.sa_mask.val[0],sig,(*k).sa.sa_flags);
    }
    #[cfg(not(native_linux_irq_work_v6_12))]
    {
        if ((*k).sa.sa_flags & F06_HANDLER_SA_NODEFER) == 0 {
            (*thread).sigmask.val[0] |= (*pending).sigmask.val[0];
        }
    }
    crate::mem_helpers::kfree_tracked(pending.cast(),
        F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),F06_SIGNAL_HANDLER_PENDING_FREE_LINE);
    crate::lock_helpers::__mcs_rwlock_writer_unlock(
        core::ptr::addr_of_mut!((*(*thread).sigcommon.cast::<SigCommon>()).lock).cast(),lock_node);
    if ((*regs).gpr.rflags & RFLAGS_TF) != 0 {
        let mut info_storage=MaybeUninit::<SigInfo>::uninit();
        let info=info_storage.as_mut_ptr();
        // Existing genuine byte-exact Rust primitive, no fake signal initializer.
        rt_sigreturn_zero_siginfo(info);
        (*regs).gpr.rflags &= !RFLAGS_TF;
        (*info).si_code=TRAP_TRACE;
        f06_handler_commit_set_signal(SIGTRAP,regs.cast(),info);
        crate::sched_helpers::check_need_resched();
        f06_handler_commit_check_signal(0,regs.cast(),-1);
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: complete temporary XSAVE allocation/capture/usercopy/cleanup orchestration.
type F06SignalSaveXstate=unsafe extern "C" fn(*mut c_void,CULong);
type F06SignalCopyXstate=unsafe extern "C" fn(*mut c_void,*const c_void,SizeT)->CInt;
unsafe extern "C" {
    #[link_name="copy_to_user"]
    fn f06_signal_xsave_copy_to_user(dst:*mut c_void,src:*const c_void,n:SizeT)->CInt;
}
unsafe extern "C" fn f06_signal_xsave_capture(buffer:*mut c_void,mask:CULong) {
    // Existing exact EDX:EAX standard-XSAVE instruction body; visibility-only
    // private Rust fragment supplied separately for central integration.
    crate::x86_cpu_helpers::x86_save_xstate(buffer,mask);
}

/// Shared actual orchestration body. Its production entry always binds genuine
/// XSAVE and public usercopy adapters below. A HOST controlled fixture may drive
/// only these two explicit architectural effect endpoints, never claim native
/// instruction/usercopy execution or replace allocator/free/panic providers.
/// Return zero continues; errors release only the private FP buffer and retain
/// pending/lock ownership for the caller to free and unlock before termination.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_xsave_copy_body_result(
    size:CInt,user_fp:CULong,_pending:*mut crate::abi::SigPending,_sig:CInt,
    frame_fpregs:*mut *mut c_void,save:F06SignalSaveXstate,copy:F06SignalCopyXstate,
)->CInt {
    if size == 0 {return 0;}
    // Boot stable positive CPUID size and no signed size+64 overflow retain the
    // C/hardware preconditions; malformed/negative geometries are not credited.
    let mask=crate::x86_cpu_helpers::get_xsave_mask();
    let base=crate::mem_helpers::kmalloc_tracked(size.wrapping_add(64),IHK_MC_AP_NOWAIT,
        F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),F06_SIGNAL_XSAVE_ALLOC_LINE);
    if base.is_null() {
        return -ENOMEM;
    }
    let aligned=((base as CULong).wrapping_add(63)&!63) as *mut c_void;
    crate::string::__inline_memset(aligned,0,size as SizeT);
    save(aligned,mask);
    if copy(user_fp as *mut c_void,aligned.cast_const(),size as SizeT) != 0 {
        crate::mem_helpers::kfree_tracked(base,
            F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),if cfg!(native_linux_irq_work_v6_12) { F06_SIGNAL_NATIVE_XSAVE_COPY_FREE_LINE } else { F06_SIGNAL_LEGACY_XSAVE_COPY_FREE_LINE });
        return -EFAULT;
    }
    *frame_fpregs=user_fp as *mut c_void;
    crate::mem_helpers::kfree_tracked(base,
        F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),F06_SIGNAL_XSAVE_SUCCESS_FREE_LINE);
    0
}

/// Caller already owns pending/sigcommon lock and CPU exclusion from do_signal.
/// The temporary allocation remains private from zero through instruction/copy,
/// and only the ORIGINAL base is freed. Published slot contains user address,
/// never a borrowed aligned kernel buffer. Hardware failure retains the same
/// baseline synchronous fault behavior; no invented instruction recovery exists.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_xsave_copy_result(
    size:CInt,user_fp:CULong,pending:*mut crate::abi::SigPending,sig:CInt,
    frame_fpregs:*mut *mut c_void,
)->CInt {
    arch_do_signal_xsave_copy_body_result(size,user_fp,pending,sig,frame_fpregs,
        f06_signal_xsave_capture,f06_signal_xsave_copy_to_user)
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: complete full-siginfo/full-frame copy and exact copy-failure ownership.
type F06SignalFrameCopy=unsafe extern "C" fn(*mut c_void,*const c_void,SizeT)->CInt;
unsafe extern "C" {
    #[link_name="copy_to_user"]
    fn f06_signal_frame_copy_to_user(dst:*mut c_void,src:*const c_void,n:SizeT)->CInt;
    #[link_name="terminate"]
    fn f06_signal_frame_copy_terminate(status:CInt,sig:CInt);
}

/// Actual orchestration body: private kernel frame and detached pending are owned
/// by the caller holding sigcommon writer lock and its actual IRQ-save node.
/// info_offset/frame_bytes come from genuine C offsetof/sizeof for that profile;
/// they are not read from user memory and do not add an unchecked input ABI.
/// The production entry binds actual usercopy. A controlled HOST fixture may
/// test this explicit copy endpoint without claiming real kernel fault fixup.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_frame_copy_body_result(
    thread:*mut Thread,pending:*mut crate::abi::SigPending,sig:CInt,
    kernel_frame:*mut c_void,frame_bytes:SizeT,info_offset:SizeT,
    user_frame:CULong,lock_node:*mut McsRwlockNodeIrqsave,copy:F06SignalFrameCopy,
)->CInt {
    crate::string::memcpy(kernel_frame.cast::<u8>().add(info_offset).cast(),
        core::ptr::addr_of!((*pending).info).cast(),size_of::<SigInfo>());
    if copy(user_frame as *mut c_void,kernel_frame.cast_const(),frame_bytes) != 0 {
        #[cfg(native_linux_irq_work_v6_12)]
        {return -EFAULT;}
        #[cfg(not(native_linux_irq_work_v6_12))]
        {
            crate::mem_helpers::kfree_tracked(pending.cast(),
                F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),F06_SIGNAL_LEGACY_FRAME_COPY_PENDING_FREE_LINE);
            crate::lock_helpers::__mcs_rwlock_writer_unlock(
                core::ptr::addr_of_mut!((*(*thread).sigcommon.cast::<SigCommon>()).lock).cast(),lock_node);
            kprintf(b"do_signal,write_process_vm failed\n\0".as_ptr().cast());
            f06_signal_frame_copy_terminate(0,sig);
            // Actual terminate provider is declared void, not noreturn. Preserve
            // original goto-out even when a controlled termination returns.
            return 1;
        }
    }
    // Success retains pending+writerlock for restorer publish/handler commit.
    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_frame_copy_result(
    thread:*mut Thread,pending:*mut crate::abi::SigPending,sig:CInt,
    kernel_frame:*mut c_void,frame_bytes:SizeT,info_offset:SizeT,
    user_frame:CULong,lock_node:*mut McsRwlockNodeIrqsave,
)->CInt {
    arch_do_signal_frame_copy_body_result(thread,pending,sig,kernel_frame,
        frame_bytes,info_offset,user_frame,lock_node,f06_signal_frame_copy_to_user)
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: complete default core-signal allocation, dump result and termination body.

unsafe extern "C" {
    #[link_name = "coredump"]
    fn f06_signal_core_dump(thread: *mut Thread, regs: *mut c_void, sig: CInt) -> CInt;

    #[link_name = "terminate"]
    fn f06_signal_core_terminate(status: CInt, sig: CInt);
}

// The exact original diagnostic is shared by the caller-private body and the
// production atomic budget. No count or kernel ownership is changed here.
unsafe fn f06_signal_core_print(
    thread: *mut Thread, regs: *mut X86UserContext, sig: CInt,
    pid: CInt, fault_address: CULong,
) {
    unsafe {
            kprintf(
                concat!(
                    "mcexec_v10: signal_default pid=%d tid=%d sig=%d ",
                    "rip=0x%lx sp=0x%lx si_addr=0x%lx\n\0",
                )
                .as_ptr()
                .cast(),
                pid,
                if thread.is_null() { -1 } else { (*thread).tid },
                sig,
                (*regs).gpr.rip,
                (*regs).gpr.rsp,
                fault_address,
            );
    }
}

// Exact original allocation/copy/dump/result/void-termination tail. Keeping it
// separate lets production diagnostics use atomic sharing without a fake log
// counter, duplicated teardown, new cleanup rule or changed public helper ABI.
unsafe fn f06_signal_core_after_log(
    thread: *mut Thread, regs: *mut X86UserContext, sig: CInt,
) {
    // SAFETY: allocation retains the caller's original kernel class/ownership.
    // No IRQ/lock policy or allocation extent is changed.
    let saved_context = unsafe {
        crate::mem_helpers::kmalloc_tracked(
            size_of::<X86UserContext>() as CInt,
            IHK_MC_AP_NOWAIT,
            F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),
            F06_SIGNAL_CORE_ALLOC_LINE,
        )
    };

    // SAFETY: this is the current thread's original publication slot. The C body
    // overwrites it even on allocation failure; it does not release an old slot.
    // Do not silently add free/rollback semantics for that existing lifecycle.
    unsafe { (*thread).coredump_regs = saved_context };
    let mut core_status = 0;
    if saved_context.is_null() {
        // SAFETY: exact existing diagnostic; no access to the failed allocation.
        unsafe {
            kprintf(
                b"%s: Out of memory\n\0".as_ptr().cast(),
                b"do_signal\0".as_ptr().cast::<i8>(),
            );
        }
    } else {
        // SAFETY: the private allocation covers the complete context and cannot
        // overlap the current kernel context. Ownership has moved to the thread
        // slot and stays there through dump/termination; it is not a temporary.
        let dump_result = unsafe {
            crate::string::memcpy(
                saved_context,
                regs.cast::<c_void>().cast_const(),
                size_of::<X86UserContext>(),
            );
            f06_signal_core_dump(thread, regs.cast(), sig)
        };
        match dump_result {
            value if value == -EBUSY => {
                // SAFETY: original EBUSY diagnostic; it adds no core-status bit.
                unsafe {
                    kprintf(
                        concat!(
                            "%s: INFO: coredump not performed, ",
                            "try ulimit -c <non-zero>\n\0",
                        )
                        .as_ptr()
                        .cast(),
                        b"do_signal\0".as_ptr().cast::<i8>(),
                    );
                }
            }
            0 => core_status = 0x80,
            value => {
                // SAFETY: the complete C-int result is preserved in the log.
                unsafe {
                    kprintf(
                        b"%s: ERROR: coredump failed (%d)\n\0".as_ptr().cast(),
                        b"do_signal\0".as_ptr().cast::<i8>(),
                        value,
                    );
                }
            }
        }
    }

    // SAFETY: this is the original unconditional termination endpoint. It is
    // declared void, not noreturn: if it returns, the caller's switch breaks and
    // preserves the existing outer restart return. No saved-context free occurs.
    unsafe { f06_signal_core_terminate(0, sig | core_status) };
}

/// Retain the default signal's context and pass its result to termination.
///
/// # Safety
/// The caller has already consumed/transferred pending and released sigcommon.
/// `thread` is the current live thread and `regs` its readable, complete kernel
/// context. Their existing lifecycle remains valid through the synchronous dump
/// call. `log_count` addresses the original initialized C diagnostic counter;
/// it is caller-owned and must not be accessed concurrently without its own
/// synchronization. The production entry uses the atomic-sharing wrapper below,
/// rather than passing a shared mutable C-int counter to this body.
/// `pid` and `fault_address` are the caller's snapshots taken before pending free.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_core_terminate_result(
    thread: *mut Thread,
    regs: *mut X86UserContext,
    sig: CInt,
    pid: CInt,
    fault_address: CULong,
    log_count: *mut CInt,
) {
    // Original caller-private counter contract and post-formatter reread.
    if unsafe { *log_count } < 64 {
        unsafe {
            f06_signal_core_print(thread, regs, sig, pid, fault_address);
            *log_count = (*log_count).wrapping_add(1);
        }
    }
    unsafe { f06_signal_core_after_log(thread, regs, sig) };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: complete default SIGTRAP traced state/notify/sleep body, no info repair.

unsafe extern "C" {
    #[link_name = "do_kill"]
    fn f06_signal_trap_notify(
        thread: *mut Thread,
        pid: CInt,
        tid: CInt,
        sig: CInt,
        info: *mut SigInfo,
        ptracecont: CInt,
    ) -> CULong;
}

#[used]
#[link_section = "__verbose"]
static mut F06_SIGNAL_TRAP_ENTER_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: F06_SIGNAL_ORIGIN.as_ptr().cast(),
    func: b"do_signal\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: F06_SIGNAL_TRAP_ENTER_LINE_FLAGS,
};

#[used]
#[link_section = "__verbose"]
static mut F06_SIGNAL_TRAP_SLEEP_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: F06_SIGNAL_ORIGIN.as_ptr().cast(),
    func: b"do_signal\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: F06_SIGNAL_TRAP_SLEEP_LINE_FLAGS,
};

#[used]
#[link_section = "__verbose"]
static mut F06_SIGNAL_TRAP_WAKE_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: F06_SIGNAL_ORIGIN.as_ptr().cast(),
    func: b"do_signal\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: F06_SIGNAL_TRAP_WAKE_LINE_FLAGS,
};

/// Return zero for the original untraced `goto core`, one after traced sleep.
///
/// # Safety
/// The live thread and process are the caller's original borrowed inputs; their
/// process/parent/report references remain valid through synchronous notify,
/// waitq wake and schedule. Pending is already consumed and sigcommon unlocked.
/// `info` is writable, aligned SigInfo storage. Its full notification is
/// initialized before either do_kill consumer and is not retained here. The
/// traced branch still needs matching full-image/native qualification.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_trap_stop_result(
    thread: *mut Thread,
    proc: *mut Process,
    info: *mut SigInfo,
) -> CInt {
    // SAFETY: descriptors are retained dynamic-debug metadata; inspect only their
    // existing enable byte, with no exclusive references to mutable statics.
    if unsafe {
        core::ptr::read_volatile(core::ptr::addr_of!(F06_SIGNAL_TRAP_ENTER_DEBUG.line_flags))
    } >> 24 != 0
    {
        // SAFETY: exact original no-argument debug diagnostic.
        unsafe { kprintf(b"do_signal,SIGTRAP\n\0".as_ptr().cast()) };
    }
    // SAFETY: caller provides the original live current thread.
    if unsafe { (*thread).ptrace } & PT_TRACED == 0 {
        return 0;
    }

    // SAFETY: these two stores intentionally precede process update locking,
    // matching the C fork-tree publication order rather than widening its lock.
    unsafe {
        (*thread).exit_status = SIGTRAP;
        (*thread).status = PS_TRACED;
        crate::f06_signal_trap_info::arch_do_signal_trap_info_bridge(
            info,
            (*thread).tid,
            (*thread).exit_status,
        );
    }
    // SAFETY: proc remains live across the borrowed main-thread comparison.
    if thread == unsafe { (*proc).main_thread } {
        let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
        // SAFETY: actual typed update-lock geometry and genuine stack lock-node
        // are valid until matching unlock; no callback retains the node pointer.
        unsafe {
            let update = core::ptr::addr_of_mut!((*proc).update_lock);
            crate::lock_helpers::__mcs_rwlock_writer_lock(update.cast(), node.as_mut_ptr());
            (*proc).group_exit_status = SIGTRAP as CULong;
            (*proc).status = PS_DELAY_TRACED;
            crate::lock_helpers::__mcs_rwlock_writer_unlock(update.cast(), node.as_mut_ptr());
            // Re-read thread->proc->parent AFTER unlock, exactly as original C.
            let parent_pid = (*(*(*thread).proc).parent).pid;
            let _ = f06_signal_trap_notify(thread, parent_pid, -1, SIGCHLD, info, 0);
        }
    } else {
        // SAFETY: report process has the caller's existing reference/lifetime.
        // Ignore original do_kill result and re-read report_proc for waitq after
        // its callback; do not cache either pointer across an externally visible
        // effect or invent a parent-waitq wake on the main-thread branch.
        unsafe {
            let report_pid = (*(*thread).report_proc).pid;
            let _ = f06_signal_trap_notify(thread, report_pid, -1, SIGCHLD, info, 0);
            crate::waitq::waitq_wakeup(
                core::ptr::addr_of_mut!((*(*thread).report_proc).waitpid_q)
                    .cast::<RuntimeWaitq>(),
            );
        }
    }

    // SAFETY: unchanged debug enable read; no node or borrowed info reference
    // survives into scheduler ownership. This helper does not free pending.
    if unsafe {
        core::ptr::read_volatile(core::ptr::addr_of!(F06_SIGNAL_TRAP_SLEEP_DEBUG.line_flags))
    } >> 24 != 0
    {
        // SAFETY: exact original diagnostic.
        unsafe { kprintf(b"do_signal,SIGTRAP,sleeping\n\0".as_ptr().cast()) };
    }
    // SAFETY: original scheduling endpoint retains its kernel/IRQ preconditions.
    unsafe { schedule() };
    // SAFETY: unchanged post-schedule debug enable check.
    if unsafe {
        core::ptr::read_volatile(core::ptr::addr_of!(F06_SIGNAL_TRAP_WAKE_DEBUG.line_flags))
    } >> 24 != 0
    {
        // SAFETY: exact original wake diagnostic, after scheduler returns.
        unsafe { kprintf(b"SIGTRAP(): woken up\n\0".as_ptr().cast()) };
    }
    1
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete default-action STOP/TSTP/TTIN/TTOU state/notification/schedule body.
unsafe extern "C" {
    #[link_name = "do_kill"]
    fn f06_signal_stop_do_kill(thread:*mut Thread,pid:CInt,tid:CInt,sig:CInt,
        info:*mut SigInfo,ptracecont:CInt)->CULong;
}
#[used]
#[link_section = "__verbose"]
static mut F06_SIGNAL_STOP_WAKE_DEBUG: crate::debug::Ddebug=crate::debug::Ddebug {
    file:F06_SIGNAL_ORIGIN.as_ptr().cast(),
    func:b"do_signal\0".as_ptr().cast(),fmt:core::ptr::null(),
    line_flags:F06_SIGNAL_STOP_WAKE_LINE_FLAGS,
};

/// Called only for the four original default stop-action switch labels, AFTER
/// pending ownership transfer/free and sigcommon unlock. No pending node is
/// touched here. `proc` is the caller's original process snapshot; thread/process
/// references and their schedule lifetime retain the existing caller ownership.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_stop_result(
    thread:*mut Thread,proc:*mut Process,sig:CInt,orgsig:CInt,
    ptraceflag:CInt,ptracecont:CInt,
) {
    if ptraceflag != 0 {
        // Existing public Rust port owns its exact notify/schedule semantics.
        ptrace_report_signal(thread,orgsig);
        return;
    }
    let mut storage=MaybeUninit::<SigInfo>::uninit();
    crate::string::__inline_memset(storage.as_mut_ptr().cast(),0,size_of::<SigInfo>());
    let mut info=storage.assume_init();
    info.si_signo=SIGCHLD;
    info.si_code=CLD_STOPPED;
    let child=core::ptr::addr_of_mut!(info.sifields.sigchld).cast::<crate::abi::SigInfoChild>();
    (*child).si_pid=(*(*thread).proc).pid;
    (*child).si_status=(sig<<8)|0x7f;
    if ptracecont == 2 && thread != (*(*thread).proc).main_thread {
        (*thread).signal_flags=SIGNAL_STOP_STOPPED;
        (*thread).status=PS_STOPPED;
        (*thread).exit_status=SIGSTOP;
        let _=f06_signal_stop_do_kill(thread,(*(*thread).report_proc).pid,
            -1,SIGCHLD,&mut info,0);
        crate::waitq::waitq_wakeup(
            core::ptr::addr_of_mut!((*(*thread).report_proc).waitpid_q).cast::<RuntimeWaitq>());
    } else {
        let mut lock=MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
        let update=core::ptr::addr_of_mut!((*proc).update_lock);
        crate::lock_helpers::__mcs_rwlock_writer_lock(update.cast(),lock.as_mut_ptr());
        (*proc).group_exit_status=SIGSTOP as CULong;
        (*(*proc).main_thread).signal_flags=SIGNAL_STOP_STOPPED;
        (*proc).status=PS_DELAY_STOPPED;
        (*thread).status=PS_STOPPED;
        crate::lock_helpers::__mcs_rwlock_writer_unlock(update.cast(),lock.as_mut_ptr());
        // Notify only AFTER writer unlock/IRQ restore, like the selected C.
        let _=f06_signal_stop_do_kill(thread,(*(*(*thread).proc).parent).pid,
            -1,SIGCHLD,&mut info,0);
    }
    schedule();
    if read_volatile(addr_of!(F06_SIGNAL_STOP_WAKE_DEBUG.line_flags))>>24 != 0 {
        kprintf(b"SIGSTOP(): woken up\n\0".as_ptr().cast());
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: complete default-action pending transfer/free + original lock release.

/// Existing caller owns sigcommon writer lock/IRQ-save node and the detached
/// pending node. Return its original ptracecont captured BEFORE any free.
/// On ptrace stop, ownership transfers to thread.ptrace_recvsig and old receive/
/// send nodes are released in the exact C order; otherwise consume pending.
/// All nodes are independently allocated live nodes, or NULL old slots. Aliased
/// old receive/send/current allocations violate the original free contract and
/// are explicitly outside this port's defined domain, not silently repaired.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_default_pending_transfer_result(
    thread:*mut Thread,pending:*mut crate::abi::SigPending,ptraceflag:CInt,
    lock_node:*mut McsRwlockNodeIrqsave,
)->CInt {
    let ptracecont=(*pending).ptracecont;
    if ptraceflag != 0 {
        if !(*thread).ptrace_recvsig.is_null() {
            crate::mem_helpers::kfree_tracked((*thread).ptrace_recvsig,
                F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),F06_SIGNAL_PTRACE_RECV_FREE_LINE);
        }
        (*thread).ptrace_recvsig=pending.cast();
        if !(*thread).ptrace_sendsig.is_null() {
            crate::mem_helpers::kfree_tracked((*thread).ptrace_sendsig,
                F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),F06_SIGNAL_PTRACE_SEND_FREE_LINE);
        }
        (*thread).ptrace_sendsig=null_mut();
    } else {
        crate::mem_helpers::kfree_tracked(pending.cast(),
            F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),F06_SIGNAL_DEFAULT_PENDING_FREE_LINE);
    }
    // Original unlock follows all ownership writes/frees and restores IRQs.
    crate::lock_helpers::__mcs_rwlock_writer_unlock(
        core::ptr::addr_of_mut!((*(*thread).sigcommon.cast::<SigCommon>()).lock).cast(),lock_node);
    ptracecont
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete legacy stack-placement/context/restart stage; native layout excluded.
#[repr(C)]
pub struct F06LegacySignalFrame {
    flags: CULong,
    link: *mut c_void,
    sigstack: crate::abi::SigStack,
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

const _: () = {
    assert!(size_of::<F06LegacySignalFrame>() == 456);
    assert!(offset_of!(F06LegacySignalFrame, regs) == 40);
    assert!(offset_of!(F06LegacySignalFrame, fpregs) == 224);
    assert!(offset_of!(F06LegacySignalFrame, sigrc) == 296);
    assert!(offset_of!(F06LegacySignalFrame, info) == 328);
};
const F06_LEGACY_SA_ONSTACK: CULong = 0x0800_0000;
const F06_LEGACY_SA_RESTART: CULong = 0x1000_0000;
const F06_LEGACY_SS_ONSTACK: CInt = 1;
const F06_LEGACY_SS_DISABLE: CInt = 2;

unsafe extern "C" {
    #[link_name = "arch_signal_restart_result"]
    fn f06_legacy_context_restart(
        number: CInt, result: CULong, signal: CInt, restart: CInt, native: CInt,
    ) -> CInt;
}

/// Preserve complete legacy frame setup and immediate alternate-stack mutation.
///
/// # Safety
/// Legacy frame profile only: frame is full aligned private kernel storage of
/// the genuine sigsp layout. Current thread/context/action/pending are live under
/// the caller's writer lock. Outputs are distinct valid C stack locals, disjoint
/// from inputs/frame. Virtual stack geometry is in the original C-defined domain;
/// this legacy path adds no canonical/range/overflow policy. No user address is
/// dereferenced by this helper. Actual boot XSAVE size/profile assumptions remain.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_legacy_frame_prepare_result(
    thread: *mut Thread,
    regs: *const X86UserContext,
    action: *const KSigAction,
    pending: *const crate::abi::SigPending,
    xsave_size: CInt,
    result: CULong,
    number: CInt,
    signal: CInt,
    frame: *mut F06LegacySignalFrame,
    user_frame: *mut CULong,
    user_fpregs: *mut CULong,
    restart_out: *mut CInt,
) {
    // SAFETY: exact complete initial memset of the private original stack frame.
    unsafe { crate::string::__inline_memset(frame.cast(), 0, size_of::<F06LegacySignalFrame>()) };
    // SAFETY: original typed inputs and flag checks. The alternate flag store
    // happens NOW, before any context/restart/XSAVE/user-copy failure, unlike the
    // native deferred publication algorithm. No rollback is invented later.
    let top = unsafe {
        if ((*action).sa.sa_flags & F06_LEGACY_SA_ONSTACK) != 0
            && ((*thread).sigstack.ss_flags & F06_LEGACY_SS_DISABLE) == 0
            && ((*thread).sigstack.ss_flags & F06_LEGACY_SS_ONSTACK) == 0
        {
            let top = ((*thread).sigstack.ss_sp as CULong)
                .wrapping_add((*thread).sigstack.ss_size as CULong)
                & !7;
            (*thread).sigstack.ss_flags |= F06_LEGACY_SS_ONSTACK;
            top
        } else {
            (*regs).gpr.rsp
        }
    };
    // Preserve unsigned-long arithmetic and sizeof(sigsp) subtraction in its
    // defined geometry; no native red-zone reservation is added to this path.
    let fpregs = top.wrapping_sub(xsave_size as CULong);
    let selected_frame = fpregs.wrapping_sub(size_of::<F06LegacySignalFrame>() as CULong) & !15;
    // SAFETY: trusted distinct caller output slots, published at the same stack
    // selection stage. They are integer addresses, never dereferenced here.
    unsafe {
        *user_fpregs = fpregs;
        *user_frame = selected_frame;
        (*frame).regs[7] = (*regs).gpr.r15;
        (*frame).regs[6] = (*regs).gpr.r14;
        (*frame).regs[5] = (*regs).gpr.r13;
        (*frame).regs[4] = (*regs).gpr.r12;
        (*frame).regs[10] = (*regs).gpr.rbp;
        (*frame).regs[11] = (*regs).gpr.rbx;
        (*frame).regs[3] = (*regs).gpr.r11;
        (*frame).regs[2] = (*regs).gpr.r10;
        (*frame).regs[1] = (*regs).gpr.r9;
        (*frame).regs[0] = (*regs).gpr.r8;
        (*frame).regs[13] = (*regs).gpr.rax;
        (*frame).regs[14] = (*regs).gpr.rcx;
        (*frame).regs[12] = (*regs).gpr.rdx;
        (*frame).regs[9] = (*regs).gpr.rsi;
        (*frame).regs[8] = (*regs).gpr.rdi;
        (*frame).regs[19] = (*regs).gpr.orig_rax;
        (*frame).regs[16] = (*regs).gpr.rip;
        (*frame).regs[17] = (*regs).gpr.rflags;
        (*frame).regs[15] = (*regs).gpr.rsp;
        // SAFETY: this original read point owns a live aligned pending allocation
        // with initialized pointer bytes. Project storage without ManuallyDrop
        // Deref or a reference to the pending, union, or fault record.
        let sigfault = core::ptr::addr_of!((*pending).info.sifields.sigfault)
            .cast::<crate::abi::SigInfoFault>();
        let fault_addr = core::ptr::read(core::ptr::addr_of!((*sigfault).si_addr)) as CULong;
        (*frame).regs[22] = fault_addr;
        (*frame).regs[21] = (*thread).sigmask.val[0];
        // Complete representation copy, including any original stack_t padding.
        crate::string::memcpy(
            core::ptr::addr_of_mut!((*frame).sigstack).cast(),
            core::ptr::addr_of!((*thread).sigstack).cast(),
            size_of::<crate::abi::SigStack>(),
        );
        (*frame).sigrc = result;
        (*frame).num = number;
    }
    // SAFETY: accepted same restart algorithm with explicit legacy=0. Do not
    // accidentally apply the native rt_sigreturn exclusion to this profile.
    let restart = unsafe {
        f06_legacy_context_restart(
            number, result, signal,
            ((*action).sa.sa_flags & F06_LEGACY_SA_RESTART) as CInt, 0,
        )
    };
    // SAFETY: exact original local restart store followed by frame restart store.
    unsafe {
        *restart_out = restart;
        (*frame).restart = restart;
    }
}


    // Native-only child avoids absent native_signal references in legacy crate.
    #[cfg(native_linux_irq_work_v6_12)]
    mod native_stage {
        use core::ffi::c_void;

        use super::{
            arch_copy_from_user_bridge, arch_copy_to_user_bridge, kprintf, CInt, CLong,
            CULong, KSigAction, McsRwlockNodeIrqsave, SizeT, Thread, X86UserContext, SIGSEGV,
            F06_SIGNAL_ORIGIN, F06_SIGNAL_NATIVE_BAD_FRAME_PENDING_FREE_LINE,
        };

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: complete native frame-zero/target-check/stack-placement orchestration.

/// Prepare native frame storage and its user addresses with existing providers.
///
/// # Safety
/// The caller holds the current thread's sigcommon writer lock and owns its
/// pending node. `thread`, `regs` and `action` are the original live inputs.
/// `frame` points to the caller's private kernel sigsp, covering frame_bytes;
/// stack_offset is its genuine offsetof(sigsp, sigstack), with enough aligned
/// space for SigStack. The two output slots are distinct initialized storage
/// with the original C lifetime, not user pointers. Frame storage is disjoint
/// from inputs/output slots, exactly as the original stack local. This entry is
/// selected only with the matching native frame layout and native_signal cfg.
/// No user memory is dereferenced and no pending/IRQ/lock ownership changes.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_native_frame_prepare_result(
    thread: *mut Thread,
    regs: *const X86UserContext,
    action: *const KSigAction,
    xsave_size: CInt,
    frame: *mut c_void,
    frame_bytes: SizeT,
    stack_offset: SizeT,
    user_frame: *mut CULong,
    user_fpregs: *mut CULong,
) -> CInt {
    // SAFETY: original complete private frame extent. Zeroing intentionally
    // precedes even invalid target detection; do not delay it until success.
    unsafe { crate::string::__inline_memset(frame, 0, frame_bytes) };
    // SAFETY: the caller's original action and VM snapshot remain live. Keep
    // individual reads here, as in the C call, with no cross-call cached bounds.
    let result = unsafe {
        crate::native_signal::native_signal_entry_targets_result(
            (*action).sa.sa_handler as CULong,
            (*action).sa.sa_restorer as CULong,
            (*(*thread).vm).region.user_start,
            (*(*thread).vm).region.user_end,
        ) as CInt
    };
    if result != 0 {
        return result;
    }

    // SAFETY: genuine C frame offset yields aligned saved-stack storage inside
    // the already-zeroed private frame. Existing stack helper alone validates
    // virtual geometry and publishes saved stack/user-frame/FP addresses. Keep
    // those helper error and partial-write semantics; no rollback is added.
    unsafe {
        crate::native_signal::native_signal_stack_prepare_result(
            core::ptr::addr_of!((*thread).sigstack),
            frame.cast::<u8>().add(stack_offset).cast::<crate::abi::SigStack>(),
            (*regs).gpr.rsp,
            (*action).sa.sa_flags,
            xsave_size,
            frame_bytes,
            (*(*thread).vm).region.user_start,
            (*(*thread).vm).region.user_end,
            user_frame,
            user_fpregs,
        ) as CInt
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete native bad-frame ownership disposal at the existing error label.

unsafe extern "C" {
    #[link_name = "terminate"]
    fn f06_native_bad_frame_terminate(status: CInt, sig: CInt);
}

/// Consume the original native bad-frame pending owner and leave its writer lock.
///
/// # Safety
/// Only the original native_bad_signal_frame label may select this entry. The
/// current live thread owns its sigcommon; the caller holds that exact writer
/// lock with `node` and still owns the detached `pending` allocation. Each native
/// target/stack/context/XSAVE/copy/restorer error must retain those obligations.
/// No previous failure path may already have consumed pending or unlocked it.
/// All inputs keep their original C lifetime; the node is not retained beyond
/// unlock. `error` is the original C-int failure snapshot. External terminate is
/// genuinely void: a HOST controlled endpoint may return, then C must goto out.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_native_bad_frame_result(
    thread: *mut Thread,
    pending: *mut crate::abi::SigPending,
    node: *mut McsRwlockNodeIrqsave,
    error: CInt,
) {
    // SAFETY: caller transfers its one detached allocation here. Preserve free
    // BEFORE unlock, with the original tracked allocator and no rollback owner.
    unsafe {
        crate::mem_helpers::kfree_tracked(
            pending.cast(),
            F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(),
            F06_SIGNAL_NATIVE_BAD_FRAME_PENDING_FREE_LINE,
        );
    }
    // SAFETY: original current sigcommon lock is still held with this real node.
    // Re-read it AFTER free, exactly where the C source reads thread->sigcommon.
    unsafe {
        crate::lock_helpers::__mcs_rwlock_writer_unlock(
            core::ptr::addr_of_mut!((*(*thread).sigcommon.cast::<crate::abi::SigCommon>()).lock).cast(),
            node,
        );
    }
    // SAFETY: synchronous formatter and void termination use original widths;
    // both effects occur only after pending free and IRQ/preemption restoration.
    unsafe {
        kprintf(b"do_signal: invalid native signal frame: %d\n\0".as_ptr().cast(), error);
        f06_native_bad_frame_terminate(0, SIGSEGV);
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Native context/restart and restorer publication, existing complete Rust rules.
const F06_NATIVE_CONTEXT_SA_RESTART: CULong = 0x1000_0000;
type F06NativeContextCopy = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;
type F06NativeRestorerCopy = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;

unsafe extern "C" {
    #[link_name = "arch_signal_restart_result"]
    fn f06_native_context_restart(
        number: CInt,
        result: CULong,
        signal: CInt,
        restart: CInt,
        native: CInt,
    ) -> CInt;
}

/// Prepare the native context with the actual restart and frame algorithms.
///
/// # Safety
/// Native frame layout only. The caller owns the full zeroed, aligned kernel
/// sigsp and holds its original pending/sigcommon writer lock. All typed inputs
/// and restart output are live and disjoint as in the original stack locals.
/// Copy synchronously implements the existing instruction user-copy contract;
/// it may be controlled only for a scoped HOST body fixture. No pointer survives
/// a call and no pending allocation or lock is consumed on helper failure.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_native_context_body_result(
    thread: *mut Thread,
    regs: *const X86UserContext,
    action: *const KSigAction,
    pending: *const crate::abi::SigPending,
    result: CULong,
    number: CInt,
    signal: CInt,
    frame: *mut crate::native_signal::Frame,
    restart_out: *mut CInt,
    copy: F06NativeContextCopy,
) -> CInt {
    // SAFETY: same selected action flags and accepted restart policy. Explicit
    // native=1 retains the original rt_sigreturn exception for this C branch.
    let restart = unsafe {
        f06_native_context_restart(
            number, result, signal,
            ((*action).sa.sa_flags & F06_NATIVE_CONTEXT_SA_RESTART) as CInt, 1,
        )
    };
    // SAFETY: original local restart assignment precedes context validation and
    // remains visible even when its instruction probe later reports an error.
    unsafe { *restart_out = restart };
    // SAFETY: existing full native algorithm owns instruction/restart validation,
    // register/error metadata, packed segments and unblockable-mask semantics.
    let error = unsafe {
        crate::native_signal::native_signal_context_prepare_result(
            regs, (*thread).sigmask.val[0], result, number, restart, frame, Some(copy),
        ) as CInt
    };
    if error != 0 {
        return error;
    }
    // SAFETY: exact final C assignment AFTER synchronous context/copy callback.
    // Do not pre-cache pending's fault address across that visible effect.
    unsafe {
        // SAFETY: re-read only initialized pointer bytes from the still-live
        // pending AFTER the synchronous callback and successful error check.
        // No projected pointer or fault value is cached across that callback.
        let sigfault = core::ptr::addr_of!((*pending).info.sifields.sigfault)
            .cast::<crate::abi::SigInfoFault>();
        let fault_addr = core::ptr::read(core::ptr::addr_of!((*sigfault).si_addr)) as CULong;
        (*frame).regs[22] = fault_addr;
    };
    0
}

/// # Safety
/// Same native context ownership as the body entry; production always binds the
/// real selected arch copy-from-user bridge, never a HOST controlled substitute.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_native_context_result(
    thread: *mut Thread,
    regs: *const X86UserContext,
    action: *const KSigAction,
    pending: *const crate::abi::SigPending,
    result: CULong,
    number: CInt,
    signal: CInt,
    frame: *mut crate::native_signal::Frame,
    restart_out: *mut CInt,
) -> CInt {
    // SAFETY: production effect is the exact existing public user-copy ABI.
    unsafe {
        arch_do_signal_native_context_body_result(
            thread, regs, action, pending, result, number, signal, frame, restart_out,
            arch_copy_from_user_bridge,
        )
    }
}

/// Publish the already-copied native frame's restorer, then stack snapshot.
///
/// # Safety
/// Current thread/action and its sigstack stay live while caller holds the
/// original writer lock/pending. Frame is the selected user address from the
/// actual prepare helper, not dereferenced by this wrapper. Copy has the native
/// synchronous checked user-copy contract; HOST controls qualify only this body.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_native_publish_body_result(
    thread: *mut Thread,
    action: *const KSigAction,
    frame: CULong,
    copy: F06NativeRestorerCopy,
) -> CInt {
    // SAFETY: reuse complete checked alignment/address/copy and snapshot order.
    // The actual helper mutates sigstack only after successful restorer copy.
    unsafe {
        crate::native_signal::native_signal_stack_publish_result(
            core::ptr::addr_of_mut!((*thread).sigstack), frame,
            (*action).sa.sa_restorer as CULong, Some(copy),
        ) as CInt
    }
}

/// # Safety
/// Production ownership matches the native publish body; binds genuine checked
/// user-copy and retains the original error's native_bad_signal_frame path.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_native_publish_result(
    thread: *mut Thread,
    action: *const KSigAction,
    frame: CULong,
) -> CInt {
    // SAFETY: exact actual copy-to-user bridge, no HOST runtime substitution.
    unsafe {
        arch_do_signal_native_publish_body_result(thread, action, frame, arch_copy_to_user_bridge)
    }
}

    }
    #[cfg(native_linux_irq_work_v6_12)]
    use native_stage::{
        arch_do_signal_native_bad_frame_result, arch_do_signal_native_context_result,
        arch_do_signal_native_frame_prepare_result, arch_do_signal_native_publish_result,
    };

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete entry orchestration; existing frozen sub-bodies retain every effect.
#[cfg(native_linux_irq_work_v6_12)]
type F06SignalFrame = crate::native_signal::Frame;
#[cfg(not(native_linux_irq_work_v6_12))]
type F06SignalFrame = F06LegacySignalFrame;

const SIGSEGV: CInt = 11;

// PID/count is diagnostic state shared by different processes/CPUs, whose
// sigcommon writer locks do not serialize one another (the entry reset is also
// before that lock). A packed atomic makes that existing shared state defined.
// Relaxed ordering coordinates ONLY the budget; it publishes no signal, process,
// pending, frame or hardware state. Preserve C's entry reset, pre-print check,
// and post-formatter fresh reread/increment; do not turn this into a pre-call
// ticket or promise a strict64-print limit under overlapping formatters.
use core::sync::atomic::{AtomicU64, Ordering};
static F06_SIGNAL_LOG_STATE: AtomicU64 = AtomicU64::new((u32::MAX as u64) << 32);

fn f06_signal_log_begin(pid: CInt) {
    let pid_bits = (pid as u32 as u64) << 32;
    let mut observed = F06_SIGNAL_LOG_STATE.load(Ordering::Relaxed);
    while observed & 0xffff_ffff_0000_0000 != pid_bits {
        match F06_SIGNAL_LOG_STATE.compare_exchange_weak(
            observed, pid_bits, Ordering::Relaxed, Ordering::Relaxed,
        ) {
            Ok(_) => return,
            Err(actual) => observed = actual,
        }
    }
}

fn f06_signal_log_allowed() -> bool {
    (F06_SIGNAL_LOG_STATE.load(Ordering::Relaxed) as u32 as CInt) < 64
}

fn f06_signal_log_after_print() {
    let mut observed = F06_SIGNAL_LOG_STATE.load(Ordering::Relaxed);
    loop {
        let next = (observed & 0xffff_ffff_0000_0000)
            | u64::from((observed as u32).wrapping_add(1));
        match F06_SIGNAL_LOG_STATE.compare_exchange_weak(
            observed, next, Ordering::Relaxed, Ordering::Relaxed,
        ) {
            Ok(_) => return,
            Err(actual) => observed = actual,
        }
    }
}

unsafe fn f06_signal_core_terminate_current(
    thread: *mut Thread, regs: *mut X86UserContext, sig: CInt,
    pid: CInt, fault_address: CULong,
) {
    if f06_signal_log_allowed() {
        unsafe { f06_signal_core_print(thread, regs, sig, pid, fault_address) };
        f06_signal_log_after_print();
    }
    unsafe { f06_signal_core_after_log(thread, regs, sig) };
}

#[used]
#[link_section = "__verbose"]
static mut F06_SIGNAL_ENTRY_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: F06_SIGNAL_ORIGIN.as_ptr().cast(),
    func: b"do_signal\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: F06_SIGNAL_ENTRY_LINE_FLAGS,
};
#[used]
#[link_section = "__verbose"]
static mut F06_SIGNAL_TERMINATE_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: F06_SIGNAL_ORIGIN.as_ptr().cast(),
    func: b"do_signal\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: F06_SIGNAL_TERMINATE_LINE_FLAGS,
};
unsafe extern "C" {
    #[link_name = "terminate"]
    fn f06_signal_dispatch_terminate(status: CInt, sig: CInt);
}

/// Existing null-regs architecture boundary: current TSS stack context minus one.
///
/// # Safety
/// Native kernel GS base and current TSS/rsp0 must be installed, with the complete
/// saved X86UserContext immediately below rsp0. Never call this HOST-side. The
/// original C used this same GS load and context subtraction, without recovery.
unsafe extern "C" fn f06_signal_syscall_context() -> *mut X86UserContext {
    let top: CULong;
    let offset = offset_of!(crate::abi::X86CpuLocalVariables, tss)
        + offset_of!(crate::abi::Tss64, rsp0);
    // SAFETY: exact original GS memory load; MOV preserves flags and does not
    // touch stack. No privileged instruction is executed during preparation.
    unsafe {
        core::arch::asm!(
            "mov {top}, gs:[{offset}]",
            top = out(reg) top,
            offset = in(reg) offset,
            options(nostack, readonly, preserves_flags),
        );
        (top as *mut X86UserContext).sub(1)
    }
}

/// Deliver one detached pending node with the original complete C entry rules.
///
/// # Safety
/// Current thread/sigcommon and detached pending are live. Any process snapshot
/// dereferenced by an original branch has that branch's original lifetime. Its nonzero
/// mask selects a valid action in the actual64-entry table. Original object and
/// callback lifetimes/IRQ/scheduling preconditions apply, including XSAVE CPU
/// exclusion. Kernel and frame layouts must match native_linux_irq_work_v6_12.
/// The traced default-SIGTRAP notification is initialized before consumption.
/// The supported selector chooses this Rust body; complete matching native
/// qualification remains open. Diagnostic sharing uses the atomic budget above;
/// overwritten old core slots retain the original ownership behavior. This
/// source repair does not clear any runtime hold.
#[no_mangle]
pub unsafe extern "C" fn do_signal(
    mut result: CULong,
    regs0: *mut c_void,
    thread: *mut Thread,
    pending: *mut crate::abi::SigPending,
    number: CInt,
) -> CInt {
    // SAFETY: original process snapshot then highest-set-bit pending decoding.
    let proc = unsafe { (*thread).proc };
    let mut signal = unsafe { sigmask_to_signal_number((*pending).sigmask.val[0]) };
    // SAFETY: retained original debug descriptor and live process/thread inputs.
    if unsafe { read_volatile(addr_of!(F06_SIGNAL_ENTRY_DEBUG.line_flags)) } >> 24 != 0 {
        unsafe {
            kprintf(b"do_signal(): tid=%d, pid=%d, sig=%d\n\0".as_ptr().cast(),
                (*thread).tid, (*proc).pid, signal);
        }
    }
    let original_signal = signal;
    // SAFETY: fault info snapshot precedes every pending transfer/free.
    let fault = unsafe {
        // SAFETY: retain this snapshot BEFORE every pending transfer/free.
        // Only the original initialized pointer-sized bytes are read; no whole
        // union value or additional pending lifetime is inferred by this load.
        let sigfault = core::ptr::addr_of!((*pending).info.sifields.sigfault)
            .cast::<crate::abi::SigInfoFault>();
        let fault_addr = core::ptr::read(core::ptr::addr_of!((*sigfault).si_addr)) as CULong;
        fault_addr
    };
    let pid = if proc.is_null() { -1 } else { unsafe { (*proc).pid } };
    // Preserve the original reset even if this entry produces no diagnostic.
    f06_signal_log_begin(pid);
    let mut ptraceflag = 0;
    // SAFETY: original ptrace remap before context acquisition and action lookup.
    if unsafe { ((*thread).ptrace & PT_TRACED) != 0 && (*pending).ptracecont == 0 }
        && signal != SIGKILL
    {
        ptraceflag = 1;
        signal = SIGSTOP;
    }
    let regs = if regs0.is_null() {
        // SAFETY: original syscall-origin kernel context acquisition; no HOST run.
        unsafe { f06_signal_syscall_context() }
    } else {
        let regs = regs0.cast::<X86UserContext>();
        // SAFETY: nonnull interrupt input supplies actual saved return bits.
        result = unsafe { (*regs).gpr.rax };
        regs
    };
    let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    // SAFETY: actual writer lock/node lifetime through one selected ownership path.
    unsafe {
        crate::lock_helpers::__mcs_rwlock_writer_lock(
            addr_of_mut!((*(*thread).sigcommon.cast::<SigCommon>()).lock).cast(), node.as_mut_ptr(),
        );
    }
    // SAFETY: original action address computed from the valid signal, no new
    // bounds policy/panic or native pointer validation is introduced here.
    let action = unsafe {
        addr_of_mut!((*(*thread).sigcommon.cast::<SigCommon>()).action)
            .cast::<KSigAction>().add((signal - 1) as usize)
    };
    let handler = unsafe { (*action).sa.sa_handler };
    let mut restart = 0;
    if handler as CULong == 1 { // actual SIG_IGN
        // SAFETY: consume exactly caller pending before unlock, then original out.
        unsafe {
            crate::mem_helpers::kfree_tracked(pending.cast(),
                F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(), F06_SIGNAL_IGNORE_FREE_LINE);
            crate::lock_helpers::__mcs_rwlock_writer_unlock(
                addr_of_mut!((*(*thread).sigcommon.cast::<SigCommon>()).lock).cast(), node.as_mut_ptr(),
            );
        }
        return restart;
    }
    if !handler.is_null() {
        // SAFETY: same boot-stable size query before frame memset/stack checks.
        let xsave_size = unsafe { crate::x86_cpu_helpers::get_xsave_size() };
        let mut storage = MaybeUninit::<F06SignalFrame>::uninit();
        let frame = storage.as_mut_ptr();
        let mut user_frame = 0;
        let mut user_fpregs = 0;
        #[cfg(native_linux_irq_work_v6_12)]
        {
            // SAFETY: actual native552-byte frame offsets, original private locals.
            let error = unsafe {
                arch_do_signal_native_frame_prepare_result(thread, regs, action, xsave_size,
                    frame.cast(), size_of::<F06SignalFrame>(),
                    offset_of!(F06SignalFrame, sigstack), &mut user_frame, &mut user_fpregs)
            };
            if error != 0 {
                // SAFETY: original native error retains pending and this writer node.
                unsafe {
                    arch_do_signal_native_bad_frame_result(
                        thread, pending, node.as_mut_ptr(), error,
                    );
                }
                return restart;
            }
            let error = unsafe {
                arch_do_signal_native_context_result(thread, regs, action, pending,
                    result, number, signal, frame, &mut restart)
            };
            if error != 0 {
                // SAFETY: original native error retains pending and this writer node.
                unsafe {
                    arch_do_signal_native_bad_frame_result(
                        thread, pending, node.as_mut_ptr(), error,
                    );
                }
                return restart;
            }
        }
        #[cfg(not(native_linux_irq_work_v6_12))]
        unsafe {
            arch_do_signal_legacy_frame_prepare_result(thread, regs, action, pending,
                xsave_size, result, number, signal, frame,
                &mut user_frame, &mut user_fpregs, &mut restart);
        }
        // SAFETY: matching native/legacy shared frame prefix and exact ownership.
        let error = unsafe {
            arch_do_signal_xsave_copy_result(xsave_size, user_fpregs, pending, signal,
                addr_of_mut!((*frame).fpregs))
        };
        if error != 0 {
            #[cfg(native_linux_irq_work_v6_12)]
            // SAFETY: original native error retains pending and this writer node.
            unsafe {
                arch_do_signal_native_bad_frame_result(
                    thread, pending, node.as_mut_ptr(), error,
                );
            }
            #[cfg(not(native_linux_irq_work_v6_12))]
            unsafe {
                // The caller still owns pending and the signal writer lock.
                crate::mem_helpers::kfree_tracked(pending.cast(),
                    F06_SIGNAL_ORIGIN.as_ptr().cast_mut().cast(), if error == -ENOMEM { F06_SIGNAL_LEGACY_XSAVE_OOM_PENDING_FREE_LINE } else { F06_SIGNAL_LEGACY_XSAVE_COPY_PENDING_FREE_LINE });
                crate::lock_helpers::__mcs_rwlock_writer_unlock(
                    addr_of_mut!((*(*thread).sigcommon.cast::<SigCommon>()).lock).cast(),
                    node.as_mut_ptr(),
                );
                if error == -ENOMEM {
                    kprintf(b"do_signal,no space available\n\0".as_ptr().cast());
                } else {
                    kprintf(b"do_signal,write_process_vm failed\n\0".as_ptr().cast());
                }
                f06_signal_dispatch_terminate(0, signal);
            }
            return restart;
        }
        let error = unsafe {
            arch_do_signal_frame_copy_result(thread, pending, signal, frame.cast(),
                size_of::<F06SignalFrame>(), offset_of!(F06SignalFrame, info),
                user_frame, node.as_mut_ptr())
        };
        if error != 0 {
            #[cfg(native_linux_irq_work_v6_12)]
            // SAFETY: original native error retains pending and this writer node.
            unsafe {
                arch_do_signal_native_bad_frame_result(
                    thread, pending, node.as_mut_ptr(), error,
                );
            }
            return restart;
        }
        let user_sp = user_frame.wrapping_sub(size_of::<CULong>() as CULong);
        #[cfg(native_linux_irq_work_v6_12)]
        {
            let error = unsafe { arch_do_signal_native_publish_result(thread, action, user_frame) };
            if error != 0 {
                // SAFETY: original native error retains pending and this writer node.
                unsafe {
                    arch_do_signal_native_bad_frame_result(
                        thread, pending, node.as_mut_ptr(), error,
                    );
                }
                return restart;
            }
        }
        #[cfg(not(native_linux_irq_work_v6_12))]
        // SAFETY: original legacy raw user restorer store, deliberately not
        // converted into a newly checked usercopy/fault recovery mechanism.
        unsafe { (user_sp as *mut CULong).write((*action).sa.sa_restorer as CULong) };
        // SAFETY: original handler diagnostic before register/action commit.
        unsafe {
            if f06_signal_log_allowed() {
                kprintf(concat!("mcexec_v10: signal_handler pid=%d tid=%d sig=%d ",
                    "handler=0x%lx restorer=0x%lx old_rip=0x%lx old_sp=0x%lx ",
                    "new_sp=0x%lx si_addr=0x%lx\n\0").as_ptr().cast(), pid,
                    if thread.is_null() { -1 } else { (*thread).tid }, signal,
                    (*action).sa.sa_handler as CULong, (*action).sa.sa_restorer as CULong,
                    (*regs).gpr.rip, (*regs).gpr.rsp, user_sp, fault);
                f06_signal_log_after_print();
            }
            arch_do_signal_handler_commit_result(thread, regs, action, pending, signal,
                user_frame, offset_of!(F06SignalFrame, info), user_sp, node.as_mut_ptr());
        }
        return restart;
    }

    // The traced-SIGTRAP helper initializes all bytes before either consumer.
    // No other branch reads this storage; no assume_init is needed here.
    let mut trap_info = MaybeUninit::<SigInfo>::uninit();
    // SAFETY: complete default ownership helper caches ptracecont before free,
    // transfers ptrace nodes or consumes pending, then releases the original lock.
    let ptracecont = unsafe {
        arch_do_signal_default_pending_transfer_result(
            thread, pending, ptraceflag, node.as_mut_ptr(),
        )
    };
    match signal {
        SIGSTOP | SIGTSTP | SIGTTIN | SIGTTOU => unsafe {
            arch_do_signal_stop_result(
                thread, proc, signal, original_signal, ptraceflag, ptracecont,
            );
        },
        SIGTRAP => {
            // SAFETY: live thread/process and writable aligned storage. The
            // traced branch initializes it before notify; the untraced branch
            // returns without reading it. Full native qualification remains open.
            let handled = unsafe {
                arch_do_signal_trap_stop_result(thread, proc, trap_info.as_mut_ptr())
            };
            if handled == 0 {
                unsafe { f06_signal_core_terminate_current(thread, regs, signal, pid, fault) };
            }
        }
        // SIGQUIT/ILL/ABRT/FPE/SEGV/BUS/SYS/XCPU/XFSZ: original nine core labels.
        3 | 4 | 6 | 8 | 11 | 7 | 31 | 24 | 25 => unsafe {
            f06_signal_core_terminate_current(thread, regs, signal, pid, fault);
        },
        // SIGCONT, SIGCHLD, SIGURG, SIGWINCH: exact original no-action labels.
        SIGCONT | SIGCHLD | SIGURG | 28 => {}
        _ => unsafe {
            if read_volatile(addr_of!(F06_SIGNAL_TERMINATE_DEBUG.line_flags)) >> 24 != 0 {
                kprintf(b"do_signal,default,terminate,sig=%d\n\0".as_ptr().cast(), signal);
            }
            f06_signal_dispatch_terminate(0, signal);
        },
    }
    restart
}

    // These compile-time bindings consume the actual separately qualified entries.
    // No call executes here, and no Thread/common lifetime or native GS fact is created.
    const _: unsafe extern "C" fn(
        *mut *mut Thread,
        *mut *mut X86UserContext,
        *mut CInt,
    ) = super::f06_signal_context_candidate::arch_rt_sigreturn_context_bridge;

    const _: unsafe extern "C" fn(
        *mut *mut Thread,
        *mut *mut X86UserContext,
        *mut CInt,
        unsafe extern "C" fn() -> *mut Thread,
        unsafe extern "C" fn() -> CInt,
        unsafe extern "C" fn() -> *mut X86UserContext,
    ) = super::f06_signal_context_candidate::arch_rt_sigreturn_context_body_result;

}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Checked restart policy, selected only with its whole-signal consumer.
#[cfg(f06_do_signal_whole_candidate)]
mod f06_whole_signal_restart_provider {
    use crate::abi::{CInt, CLong, CULong};

    use super::{EINTR, SIGKILL, SIGSTOP, SYS_EPOLL_WAIT, SYS_NANOSLEEP,
                SYS_PPOLL, SYS_PSELECT6};

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: checked signal restart policy; retain the legacy/native config
// distinction at the existing C call sites through an explicit literal flag.
const F06_SIGNAL_RESTART_NEVER: [CInt; 16] = [
    34, // __NR_pause,
    130, // __NR_rt_sigsuspend,
    128, // __NR_rt_sigtimedwait,
    SYS_EPOLL_WAIT as CInt, // __NR_epoll_wait,
    281, // __NR_epoll_pwait,
    7, // __NR_poll,
    SYS_PPOLL, // __NR_ppoll,
    23, // __NR_select,
    SYS_PSELECT6, // __NR_pselect6,
    70, // __NR_msgrcv,
    69, // __NR_msgsnd,
    65, // __NR_semop,
    220, // __NR_semtimedop,
    230, // __NR_clock_nanosleep,
    SYS_NANOSLEEP, // __NR_nanosleep,
    208, // __NR_io_getevents
];

/// Pure policy only: no signal ownership, user-register or handler-state changes.
/// `rc` is the original unsigned-long return bits, not a narrowed signed errno.
/// The native flag is selected by the same MCKERNEL_NATIVE_SIGNAL_STACK C macro
/// as the original early-return guard; callers evaluate each argument once.
#[no_mangle]
pub extern "C" fn arch_signal_restart_result(
    num: CInt, rc: CULong, sig: CInt, restart: CInt, native_signal_stack: CInt,
) -> CInt {
    // A pending native handler observes an already-restored user continuation.
    if native_signal_stack != 0 && num == 15 { // __NR_rt_sigreturn
        return 0;
    }
    if sig == SIGKILL || sig == SIGSTOP {
        return 0;
    }
    if num < 0 || rc != (-(EINTR as CLong)) as CULong {
        return 0;
    }
    if F06_SIGNAL_RESTART_NEVER.contains(&num) {
        return 0;
    }
    (restart != 0) as CInt
}

    const _: extern "C" fn(CInt, CULong, CInt, CInt, CInt) -> CInt =
        arch_signal_restart_result;
}
