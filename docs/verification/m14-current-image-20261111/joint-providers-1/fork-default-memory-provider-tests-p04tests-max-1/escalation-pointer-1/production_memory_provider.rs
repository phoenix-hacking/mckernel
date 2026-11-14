//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Genuine current memory-host callbacks and three-argument offload adapters.
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use crate::abi::{CInt, CLong, CULong, SizeT, SyscallRequest, X86UserContext};

#[cfg(any(not(target_arch = "x86_64"), not(native_linux_irq_work_v6_12),
    not(enable_profile), not(enable_perf), not(enable_rusage), enable_tofu,
    enable_fugaku_hacks, f03_forward_adapters_candidate))]
compile_error!("memory-host offload requires its paired qualified ordinary profile");

unsafe extern "C" {
    fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;
    // This is the already selected complete Rust entry in syscall_policy, whose
    // immutable genuine-header binding now resolves forward/log to this module.
    fn clear_host_pte(addr: CULong, len: SizeT, holding_lock: CInt) -> CLong;
}

/// Preserve the actual three-argument synchronous request and signed long result.
///
/// # Safety
/// Original live current-thread/CPU/offload contracts apply through the blocking
/// provider. Its actual consumers are munmap and setitimer and consume at most
/// args0..2. The original upper argument/TID/valid bytes were unspecified here;
/// zero defines the complete private72-byte storage before the genuine existing
/// builder writes number/all six arguments. The real do_syscall still owns TIDs,
/// publication, monitor/accounting, preemption, nested work and response handling.
/// No reference or request pointer is retained across this function's return.
#[no_mangle]
pub unsafe extern "C" fn syscall_do_syscall3_bridge(
    number: CInt, arg0: CULong, arg1: CULong, arg2: CULong,
) -> CLong {
    let mut request = MaybeUninit::<SyscallRequest>::zeroed();
    let cpu = unsafe { crate::x86_local::ihk_mc_get_processor_id() };
    unsafe {
        crate::syscall_policy::syscall_generic_forwarding_body_result(
            request.as_mut_ptr(), number, arg0, arg1, arg2, 0, 0, 0, cpu,
            Some(do_syscall),
        )
    }
}

/// Preserve the actual public policy ABI with one genuine offload transaction.
/// # Safety
/// Same live three-argument consumer and synchronous ownership contract above.
#[no_mangle]
pub unsafe extern "C" fn syscall_policy_do_syscall3_bridge(
    number: CInt, arg0: CULong, arg1: CULong, arg2: CULong,
) -> CLong {
    unsafe { syscall_do_syscall3_bridge(number, arg0, arg1, arg2) }
}

/// Preserve the original nonzero-result error diagnostic, including signed long.
#[no_mangle]
pub unsafe extern "C" fn clear_host_pte_log_bridge(error: CLong) {
    unsafe { crate::debug::kprintf(b"clear_host_pte failed. %ld\n\0".as_ptr().cast(), error) };
}

/// Call the real complete Rust clear-host entry through the original callback ABI.
/// # Safety
/// The original process/VM is borrowed for the full synchronous operation. The
/// caller retains the original range-lock contract when holding_lock is nonzero.
/// Existing clear_host_pte_body_result publishes current CPU before forwarding,
/// restores -1 before error logging, and returns the unmodified signed long.
/// This entry acquires/releases no lock or reference and fabricates no reply.
#[no_mangle]
pub unsafe extern "C" fn do_munmap_clear_host_bridge(
    addr: CULong, len: SizeT, holding_lock: CInt,
) -> CLong {
    unsafe { clear_host_pte(addr, len, holding_lock) }
}

/// Preserve the actual reachable set_host_vma body and its signed-int result.
/// # Safety
/// Original current-thread/VM/range-lock/offload contract applies. As in C, the
/// three argument setters target a disjoint private all-integer context. Zero
/// initializes it before the real setters form references to its u64 GPR fields.
/// The context is not forwarded/read as a whole; preserve all three typed calls
/// and the initial CPU/current lookup. The real helpers perform volatile writes
/// through initialized field references; retain all three calls and their order.
/// No returned/offloaded argument is changed.
/// The C function returns set_host_vma_body_result unconditionally; its later
/// mprotect/debug block is unreachable. The selected existing native body keeps
/// host mirror protection, forwards munmap for PFN invalidation, restores the
/// borrowed lock-state flag and deliberately has no error log at this edge.
#[no_mangle]
pub unsafe extern "C" fn do_munmap_set_host_bridge(
    addr: CULong, len: SizeT, prot: CInt, holding_lock: CInt,
) -> CInt {
    let mut context = MaybeUninit::<X86UserContext>::zeroed();
    let _thread = unsafe { (*crate::cls::get_this_cpu_local_var()).current };
    unsafe {
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg0(context.as_mut_ptr(), addr);
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg1(context.as_mut_ptr(), len as CULong);
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg2(context.as_mut_ptr(), prot as CULong);
    }
    crate::syscall_policy::set_host_vma_body_result(addr, len, prot, holding_lock)
}

const _: unsafe extern "C" fn(CInt,CULong,CULong,CULong)->CLong = syscall_do_syscall3_bridge;
const _: unsafe extern "C" fn(CInt,CULong,CULong,CULong)->CLong = syscall_policy_do_syscall3_bridge;
const _: unsafe extern "C" fn(CLong) = clear_host_pte_log_bridge;
const _: unsafe extern "C" fn(CULong,SizeT,CInt)->CLong = do_munmap_clear_host_bridge;
const _: unsafe extern "C" fn(CULong,SizeT,CInt,CInt)->CInt = do_munmap_set_host_bridge;
const _: () = {
    assert!(size_of::<CInt>() == 4 && size_of::<CLong>() == 8);
    assert!(size_of::<CULong>() == 8 && size_of::<SizeT>() == 8);
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(offset_of!(SyscallRequest, rtid) == 0 && offset_of!(SyscallRequest, ttid) == 4);
    assert!(offset_of!(SyscallRequest, valid) == 8 && offset_of!(SyscallRequest, number) == 16);
    assert!(offset_of!(SyscallRequest, args) == 24);
};
